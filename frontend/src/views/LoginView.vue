<template>
  <div class="min-h-screen flex items-center justify-center relative overflow-hidden"
       style="background:radial-gradient(ellipse at 30% 20%, #1e3a8a 0%, #0f172a 50%, #080f1e 100%)">

    <!-- Background glows -->
    <div class="absolute top-1/4 left-1/3 w-96 h-96 rounded-full pointer-events-none opacity-10"
         style="background:#3b82f6;filter:blur(80px)"></div>
    <div class="absolute bottom-1/4 right-1/4 w-72 h-72 rounded-full pointer-events-none opacity-10"
         style="background:#8b5cf6;filter:blur(70px)"></div>

    <div class="relative w-full max-w-sm mx-4">
      <!-- Logo + title -->
      <div class="text-center mb-7">
        <div class="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4 shadow-2xl"
             style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)">📊</div>
        <h1 class="text-2xl font-bold text-white tracking-tight">ETF 量化管理</h1>
        <p class="text-sm mt-1" style="color:#334155">内部交易系统 · 请登录</p>
      </div>

      <!-- Login card -->
      <div class="rounded-2xl overflow-hidden shadow-2xl"
           style="background:#111827;border:1px solid rgba(255,255,255,0.07)">
        <div class="px-7 py-7">
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-semibold mb-1.5"
                     style="color:#475569;letter-spacing:.06em;text-transform:uppercase">用户名</label>
              <input v-model="form.username" type="text" placeholder="输入用户名"
                     class="w-full px-4 py-2.5 text-sm rounded-xl outline-none transition"
                     style="background:#0f172a;border:1px solid rgba(255,255,255,0.08);color:#e2e8f0;caret-color:#3b82f6"
                     @focus="e => e.target.style.borderColor = 'rgba(59,130,246,0.5)'"
                     @blur="e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'"
                     @keydown.enter="submit"
                     autocomplete="username" />
            </div>
            <div>
              <label class="block text-xs font-semibold mb-1.5"
                     style="color:#475569;letter-spacing:.06em;text-transform:uppercase">密码</label>
              <input v-model="form.password" type="password" placeholder="输入密码"
                     class="w-full px-4 py-2.5 text-sm rounded-xl outline-none transition"
                     style="background:#0f172a;border:1px solid rgba(255,255,255,0.08);color:#e2e8f0;caret-color:#3b82f6"
                     @focus="e => e.target.style.borderColor = 'rgba(59,130,246,0.5)'"
                     @blur="e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'"
                     @keydown.enter="submit"
                     autocomplete="current-password" />
            </div>

            <!-- Error -->
            <div v-if="error"
                 class="flex items-center gap-2 px-3.5 py-2.5 rounded-xl text-sm"
                 style="background:rgba(244,63,94,0.08);border:1px solid rgba(244,63,94,0.2);color:#fb7185">
              <span>⚠</span> {{ error }}
            </div>

            <!-- Submit button -->
            <button class="w-full py-2.5 rounded-xl text-sm font-semibold text-white transition mt-1"
                    :style="loading
                      ? 'opacity:.6;cursor:not-allowed;background:linear-gradient(135deg,#1e3a8a,#3b82f6)'
                      : 'cursor:pointer;background:linear-gradient(135deg,#1e3a8a,#3b82f6)'"
                    :disabled="loading"
                    @click="submit">
              <span v-if="loading" class="flex items-center justify-center gap-2">
                <svg class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="white" stroke-width="3" stroke-opacity=".25"/>
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="white" stroke-width="3" stroke-linecap="round"/>
                </svg>
                登录中…
              </span>
              <span v-else>登 录</span>
            </button>
          </div>
        </div>

        <div class="px-7 py-3 text-center text-xs"
             style="background:rgba(0,0,0,0.25);border-top:1px solid rgba(255,255,255,0.04);color:#1e3a5f">
          © ETF 量化系统 · 仅供内部使用
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { store } from '../store.js'

const form    = reactive({ username: '', password: '' })
const error   = ref('')
const loading = ref(false)

async function submit() {
  if (!form.username || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  error.value   = ''
  try {
    await store.login(form.username, form.password)
  } catch (e) {
    error.value = e.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
