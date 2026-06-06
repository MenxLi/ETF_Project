export async function api(method, url, body) {
  const r = await fetch(url, {
    method,
    credentials: 'include',   // send session cookie
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  // Session expired — tell the app to show login
  if (r.status === 401) {
    window.dispatchEvent(new CustomEvent('session:expired'))
    throw new Error('会话已过期，请重新登录')
  }
  if (!r.ok) {
    let msg
    try { msg = (await r.json()).error } catch { msg = await r.text() }
    throw new Error(msg || r.statusText)
  }
  if (r.status === 204) return null
  return r.json()
}

export const fmtCash = v => '¥' + Math.round(v || 0).toLocaleString('zh-CN')
export const fmtPct  = v => ((v || 0) * 100).toFixed(0) + '%'
export const todayStr = () => new Date().toISOString().split('T')[0]
