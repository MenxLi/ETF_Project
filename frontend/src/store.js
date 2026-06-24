import { reactive } from 'vue'
import { api } from './api.js'

export const store = reactive({
  users:          [],
  etfList:        {},   // code → name
  etfCategories:  {},   // code → category
  status:         '加载中…',
  currentUser:    null, // { id, name, role, email }

  get isAdmin() {
    return this.currentUser?.role === 'admin'
  },
  get isLoggedIn() {
    return !!this.currentUser
  },

  // Called once on app mount — checks session, then loads data
  async init() {
    // Use raw fetch so a 401 here doesn't fire the global session:expired event
    // (it's normal to be unauthenticated on first load)
    try {
      const r = await fetch('/api/auth/me', { credentials: 'include' })
      if (!r.ok) {
        this.currentUser = null
        this.status = '未登录'
        return
      }
      this.currentUser = await r.json()
    } catch {
      this.currentUser = null
      this.status = '未登录'
      return
    }
    try {
      const [u, e] = await Promise.all([
        api('GET', '/api/users'),
        api('GET', '/api/etf-list'),
      ])
      this.users         = u
      this.etfList       = e.names      ?? e   // 兼容旧格式（纯 code→name 字典）
      this.etfCategories = e.categories ?? {}
      this.status        = '就绪'
    } catch (e) {
      this.status = '加载失败'
    }
  },

  async login(username, password) {
    // Use raw fetch — the global api() turns any 401 into a "session expired"
    // message, but here a 401 just means wrong credentials.
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!r.ok) {
      let msg = '登录失败'
      try { msg = (await r.json()).error || msg } catch {}
      throw new Error(msg)
    }
    this.currentUser = await r.json()
    await this.init()
  },

  async logout() {
    try { await api('POST', '/api/auth/logout') } catch {}
    this.currentUser   = null
    this.users         = []
    this.etfList       = {}
    this.etfCategories = {}
    this.status        = '未登录'
  },

  async refreshUsers() {
    try { this.users = await api('GET', '/api/users') } catch {}
  },
})
