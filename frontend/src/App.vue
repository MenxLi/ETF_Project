<template>
  <!-- Login page -->
  <LoginView v-if="!store.isLoggedIn" />

  <!-- Main app -->
  <template v-else>

    <!-- ── Header ───────────────────────────────────────── -->
    <header class="flex-shrink-0 flex items-center justify-between px-5 py-0"
            style="height:52px;background:#080f1e;border-bottom:1px solid rgba(255,255,255,0.06)">
      <!-- Logo -->
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-xl flex items-center justify-center text-base font-bold text-white"
             style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)">📊</div>
        <div>
          <h1 class="text-white font-bold text-sm leading-tight tracking-wide">ETF 量化管理</h1>
          <p class="text-xs" style="color:#334155;line-height:1">持仓 · 信号 · 回测</p>
        </div>
      </div>

      <!-- Right: status + user -->
      <div class="flex items-center gap-3">
        <!-- Status pill -->
        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
             :style="statusStyle">
          <span class="w-1.5 h-1.5 rounded-full" :style="{background: statusDot}"></span>
          {{ store.status }}
        </div>

        <!-- Divider -->
        <div class="h-4 w-px" style="background:rgba(255,255,255,0.08)"></div>

        <!-- User -->
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold"
               :style="{background: avatarColor(store.currentUser?.name)}">
            {{ store.currentUser?.name?.[0]?.toUpperCase() }}
          </div>
          <span class="text-sm font-medium text-white">{{ store.currentUser?.name }}</span>
          <span v-if="store.isAdmin"
                class="text-xs px-1.5 py-0.5 rounded-full font-semibold"
                style="background:rgba(251,191,36,0.15);color:#fbbf24;border:1px solid rgba(251,191,36,0.25)">
            管理员
          </span>
          <button class="text-xs px-2.5 py-1 rounded-lg font-medium transition ml-1"
                  style="background:rgba(255,255,255,0.06);color:#94a3b8;border:1px solid rgba(255,255,255,0.08)"
                  @click="logout">退出</button>
        </div>
      </div>
    </header>

    <!-- ── Body ─────────────────────────────────────────── -->
    <div class="flex flex-1 overflow-hidden">

      <!-- Sidebar nav -->
      <nav class="flex-shrink-0 flex flex-col py-3 px-2"
           style="width:180px;background:#0f172a;border-right:1px solid rgba(255,255,255,0.05)">

        <!-- Nav items -->
        <div class="space-y-0.5">
          <div v-for="item in visibleNav" :key="item.key"
               class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm cursor-pointer transition-all select-none"
               :style="page === item.key
                 ? 'background:rgba(59,130,246,0.14);border:1px solid rgba(59,130,246,0.28);color:#93c5fd;font-weight:600'
                 : 'border:1px solid transparent;color:#64748b'"
               @click="page = item.key"
               @mouseenter="e => { if (page !== item.key) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = page !== item.key ? '#94a3b8' : '' }"
               @mouseleave="e => { if (page !== item.key) e.currentTarget.style.background = ''; e.currentTarget.style.color = page !== item.key ? '#64748b' : '' }">
            <span class="text-base leading-none">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </div>
        </div>

        <!-- Spacer -->
        <div class="flex-1"></div>

        <!-- Admin section label -->
        <div v-if="store.isAdmin" class="px-3 mb-2">
          <div class="text-xs font-semibold tracking-widest uppercase"
               style="color:#1e3a5f;letter-spacing:.08em">管理</div>
        </div>

        <!-- Bottom: date -->
        <div class="px-3 py-3 text-xs" style="color:#1e3a5f;border-top:1px solid rgba(255,255,255,0.04)">
          {{ dateStr }}
        </div>
      </nav>

      <!-- Main content -->
      <main class="flex-1 overflow-hidden flex flex-col" style="background:#f1f5f9">
        <PortfolioView v-if="page === 'portfolio'" class="flex-1 min-h-0" />
        <EtfView v-else-if="page === 'market'" class="flex-1 min-h-0" />
        <div v-else class="flex-1 overflow-y-auto">
          <SignalView   v-if="page === 'signals'" />
          <ModelView    v-if="page === 'model'  && store.isAdmin" />
          <BacktestView v-if="page === 'backtest' && store.isAdmin" />
          <EmailView    v-if="page === 'emails'   && store.isAdmin" />
          <SystemView   v-if="page === 'system'   && store.isAdmin" />
        </div>
      </main>

    </div>
  </template>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { store } from './store.js'
import LoginView     from './views/LoginView.vue'
import PortfolioView from './views/PortfolioView.vue'
import SignalView    from './views/SignalView.vue'
import EtfView       from './views/EtfView.vue'
import BacktestView  from './views/BacktestView.vue'
import EmailView     from './views/EmailView.vue'
import SystemView    from './views/SystemView.vue'
import ModelView     from './views/ModelView.vue'

const page = ref('portfolio')

const allNav = [
  { key: 'portfolio', icon: '💼', label: '持仓管理', adminOnly: false },
  { key: 'signals',   icon: '📡', label: '信号看板', adminOnly: false },
  { key: 'market',    icon: '📈', label: 'ETF 行情', adminOnly: false },
  { key: 'model',     icon: '🎛️', label: '模型调参', adminOnly: true  },
  { key: 'backtest',  icon: '🔬', label: '回测结果', adminOnly: true  },
  { key: 'emails',    icon: '📧', label: '邮件记录', adminOnly: true  },
  { key: 'system',    icon: '⚙️',  label: '系统状态', adminOnly: true  },
]

const visibleNav = computed(() =>
  allNav.filter(item => !item.adminOnly || store.isAdmin)
)

const dateStr = new Date().toLocaleDateString('zh-CN', {
  month: 'long', day: 'numeric', weekday: 'short',
})

// Avatar color
const AVATAR_COLORS = ['#3b82f6','#8b5cf6','#ec4899','#f59e0b','#10b981','#06b6d4','#f43f5e','#84cc16']
function avatarColor(name) {
  return AVATAR_COLORS[(name?.charCodeAt(0) ?? 0) % AVATAR_COLORS.length]
}

// Status pill appearance
const statusStyle = computed(() => {
  const s = store.status
  if (s === '就绪' || s.includes('✓'))
    return 'background:rgba(16,185,129,0.1);color:#10b981;border:1px solid rgba(16,185,129,0.2)'
  if (s === '未登录')
    return 'background:rgba(100,116,139,0.1);color:#64748b;border:1px solid rgba(100,116,139,0.2)'
  if (s.includes('失败') || s.includes('错误'))
    return 'background:rgba(244,63,94,0.1);color:#f43f5e;border:1px solid rgba(244,63,94,0.2)'
  return 'background:rgba(251,191,36,0.1);color:#fbbf24;border:1px solid rgba(251,191,36,0.2)'
})

const statusDot = computed(() => {
  const s = store.status
  if (s === '就绪' || s.includes('✓')) return '#10b981'
  if (s.includes('失败') || s.includes('错误')) return '#f43f5e'
  return '#fbbf24'
})

async function logout() {
  await store.logout()
  page.value = 'portfolio'
}

onMounted(() => {
  store.init().catch(() => {})
  window.addEventListener('session:expired', () => {
    store.currentUser = null
    page.value = 'portfolio'
  })
})
</script>
