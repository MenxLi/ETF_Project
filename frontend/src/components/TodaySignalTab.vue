<template>
  <div>
    <!-- 手动触发器（管理员） -->
    <div v-if="store.isAdmin"
         class="mb-5 rounded-2xl p-4 flex items-center gap-4"
         :style="triggerBannerStyle">
      <div class="flex-1 min-w-0">
        <div class="font-semibold text-sm" :style="triggerTextStyle">{{ triggerTitle }}</div>
        <div class="text-xs mt-0.5 opacity-70" :style="triggerTextStyle">{{ triggerSub }}</div>
        <div v-if="job.status === 'running' && job.log?.length"
             class="mt-2 text-xs font-mono opacity-60" :style="triggerTextStyle">
          {{ job.log[job.log.length - 1] }}
        </div>
      </div>
      <button class="flex-shrink-0 px-4 py-2 rounded-xl text-sm font-semibold transition shadow-sm flex items-center gap-2"
              :style="triggerBtnStyle"
              :disabled="job.status === 'running'"
              @click="runSignals">
        <span v-if="job.status === 'running'" class="animate-spin inline-block">⟳</span>
        {{ triggerBtnLabel }}
      </button>
    </div>

    <div v-if="loading" class="py-24 text-center text-gray-400">加载中…</div>
    <div v-else-if="err" class="py-10 text-center text-red-500">{{ err }}</div>
    <template v-else>
      <!-- 汇总卡片 -->
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="rounded-2xl p-4 text-white shadow-md"
             style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)">
          <div class="text-xs opacity-70 mb-1">信号日期</div>
          <div class="font-bold">{{ today.trade_date || '—' }}</div>
        </div>
        <div class="rounded-2xl p-4 text-white shadow-md"
             style="background:linear-gradient(135deg,#064e3b,#059669)">
          <div class="text-xs opacity-70 mb-1">做多信号数</div>
          <div class="font-bold text-2xl">{{ signals.length }}</div>
        </div>
        <div class="rounded-2xl p-4 text-white shadow-md"
             style="background:linear-gradient(135deg,#3b0764,#7c3aed)">
          <div class="text-xs opacity-70 mb-1">平均做多概率</div>
          <div class="font-bold text-2xl">{{ avgProb }}%</div>
        </div>
        <div class="rounded-2xl p-4 text-white shadow-md"
             style="background:linear-gradient(135deg,#78350f,#d97706)">
          <div class="text-xs opacity-70 mb-1">生成时间</div>
          <div class="font-bold">{{ genTime }}</div>
        </div>
      </div>

      <div v-if="!signals.length" class="text-center py-20 text-gray-400">
        <div class="text-5xl mb-4">⚪</div>
        <p class="text-lg font-semibold text-gray-500">今日无做多信号</p>
        <p class="text-sm mt-1">候选池为空或尚未生成，请等待收盘后自动运行</p>
      </div>
      <template v-else>
        <!-- 分类筛选条 -->
        <div class="flex flex-wrap gap-2 mb-4">
          <button class="px-3 py-1 rounded-full text-xs font-semibold transition-all"
                  :style="catFilter === ''
                    ? 'background:#3b82f6;color:white'
                    : 'background:#f1f5f9;color:#64748b'"
                  @click="catFilter = ''">
            全部 ({{ signals.length }})
          </button>
          <button v-for="cat in signalCats" :key="cat"
                  class="px-3 py-1 rounded-full text-xs font-semibold transition-all"
                  :style="catFilter === cat
                    ? 'background:#3b82f6;color:white'
                    : 'background:#f1f5f9;color:#64748b'"
                  @click="catFilter = cat">
            {{ cat }} ({{ catCount(cat) }})
          </button>
        </div>
        <div v-if="filteredSignals.length" class="space-y-4">
          <SignalCard v-for="s in filteredSignals" :key="s.code" :signal="s"
                      @trade="$emit('open-trade', $event)" />
        </div>
        <div v-else class="text-center py-10 text-gray-400 text-sm">
          「{{ catFilter }}」板块今日无信号
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api, fetchRealtimePrice } from '../api.js'
import { store } from '../store.js'
import SignalCard from './SignalCard.vue'

const emit = defineEmits(['open-trade'])

// ── 任务状态 ──────────────────────────────────────────────────
const job = ref({ status: 'idle', signal_count: 0, started_at: null, finished_at: null, log: [], error: null })
let _pollTimer = null

const triggerBannerStyle = computed(() => {
  const s = job.value.status
  if (s === 'running') return 'background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:white'
  if (s === 'done')    return 'background:linear-gradient(135deg,#064e3b,#059669);color:white'
  if (s === 'error')   return 'background:linear-gradient(135deg,#7f1d1d,#ef4444);color:white'
  return 'background:#f1f5f9;border:1px solid #e2e8f0'
})
const triggerTextStyle = computed(() =>
  ['running', 'done', 'error'].includes(job.value.status) ? 'color:white' : 'color:#374151'
)
const triggerTitle = computed(() => {
  const s = job.value.status
  if (s === 'running') return '⟳ 正在生成信号，更新行情数据中…'
  if (s === 'done')    return `✓ 生成完成，共 ${job.value.signal_count} 个做多信号`
  if (s === 'error')   return '✗ 生成失败：' + job.value.error
  return '手动触发信号生成'
})
const triggerSub = computed(() => {
  const s = job.value.status
  if (s === 'running') return `开始于 ${job.value.started_at}`
  if (s === 'done')    return `完成于 ${job.value.finished_at}，数据已同步`
  if (s === 'error')   return `失败于 ${job.value.finished_at}`
  return '更新所有 ETF 行情数据并重新生成今日做多信号'
})
const triggerBtnStyle = computed(() => {
  const s = job.value.status
  if (s === 'running') return 'background:rgba(255,255,255,0.2);color:white;cursor:not-allowed'
  if (['done', 'error'].includes(s)) return 'background:rgba(255,255,255,0.2);color:white'
  return 'background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:white'
})
const triggerBtnLabel = computed(() => {
  const s = job.value.status
  if (s === 'running') return '生成中…'
  if (s === 'done')    return '再次触发'
  if (s === 'error')   return '重试'
  return '🚀 立即生成'
})

async function runSignals() {
  try {
    await api('POST', '/api/run-signals', {})
    job.value.status = 'running'
    _startPolling()
  } catch (e) {
    store.status = '触发失败: ' + e.message
  }
}

function _startPolling() {
  if (_pollTimer) clearInterval(_pollTimer)
  _pollTimer = setInterval(async () => {
    try {
      const s = await api('GET', '/api/run-signals/status')
      job.value = s
      if (s.status !== 'running') {
        clearInterval(_pollTimer)
        _pollTimer = null
        if (s.status === 'done') {
          loading.value = true
          try { today.value = await api('GET', '/api/signals') }
          catch (e) { err.value = e.message }
          finally { loading.value = false }
        }
      }
    } catch {}
  }, 2000)
}

// ── 信号数据 ──────────────────────────────────────────────────
const today   = ref({})
const loading = ref(true)
const err     = ref('')
const catFilter = ref('')

const signals = computed(() => today.value?.signals ?? [])

// 信号中出现的分类（按 CATEGORY_ORDER 排序）
const CAT_ORDER = ['宽基', '海外', '金融', '医疗', '科技', '能源', '消费', '周期', '地产', '债券', '商品']
const signalCats = computed(() => {
  const cats = new Set(signals.value.map(s => store.etfCategories?.[s.code]).filter(Boolean))
  return CAT_ORDER.filter(c => cats.has(c))
})
const catCount = (cat) => signals.value.filter(s => store.etfCategories?.[s.code] === cat).length
const filteredSignals = computed(() =>
  catFilter.value
    ? signals.value.filter(s => store.etfCategories?.[s.code] === catFilter.value)
    : signals.value
)
const avgProb = computed(() =>
  signals.value.length
    ? (signals.value.reduce((s, x) => s + x.prob_up, 0) / signals.value.length * 100).toFixed(1)
    : '0'
)
const genTime = computed(() => (today.value?.generated_at ?? '').slice(11, 16) || '—')

async function _refreshPctChg(sigs) {
  for (const sig of sigs) {
    try {
      const rt = await fetchRealtimePrice(sig.code)
      if (rt?.price && rt.price > 0) {
        sig.close   = rt.price
        sig.pct_chg = rt.pct_chg ?? sig.pct_chg ?? 0
      }
    } catch {}
  }
}

onMounted(async () => {
  if (store.isAdmin) {
    try {
      const s = await api('GET', '/api/run-signals/status')
      job.value = s
      if (s.status === 'running') _startPolling()
    } catch {}
  }
  try {
    today.value = await api('GET', '/api/signals')
    _refreshPctChg(today.value?.signals ?? [])
  } catch (e) { err.value = e.message }
  finally     { loading.value = false }
})

onBeforeUnmount(() => {
  if (_pollTimer) clearInterval(_pollTimer)
})

// 供父组件取 tradeDate（用于历史档案高亮今日）
defineExpose({ tradeDate: computed(() => today.value?.trade_date ?? '') })
</script>
