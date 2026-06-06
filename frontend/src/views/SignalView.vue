<template>
  <div class="flex flex-col h-full overflow-hidden">

    <!-- ── Tab bar ─────────────────────────────────────────── -->
    <div class="flex-shrink-0 flex items-center gap-1 px-6 pt-5 pb-0">
      <button v-for="t in TABS" :key="t.key"
              class="px-5 py-2.5 rounded-t-xl text-sm font-medium transition-all border-b-2"
              :style="tab === t.key
                ? 'background:white;border-color:#3b82f6;color:#1e3a8a;font-weight:700'
                : 'background:transparent;border-color:transparent;color:#64748b'"
              @click="tab = t.key">
        {{ t.label }}
      </button>
    </div>

    <!-- Tab content area (scrollable) -->
    <div class="flex-1 overflow-y-auto bg-white rounded-none p-6" style="border-top:1px solid #e2e8f0">

      <!-- ══════════════ Tab: 今日信号 ══════════════ -->
      <div v-if="tab === 'today'">
        <div v-if="loadingToday" class="py-24 text-center text-gray-400">加载中…</div>
        <div v-else-if="errToday" class="py-10 text-center text-red-500">{{ errToday }}</div>
        <template v-else>
          <!-- Summary cards -->
          <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="rounded-2xl p-4 text-white shadow-md"
                 style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)">
              <div class="text-xs opacity-70 mb-1">信号日期</div>
              <div class="font-bold">{{ today.trade_date || '—' }}</div>
            </div>
            <div class="rounded-2xl p-4 text-white shadow-md"
                 style="background:linear-gradient(135deg,#064e3b,#059669)">
              <div class="text-xs opacity-70 mb-1">做多信号数</div>
              <div class="font-bold text-2xl">{{ todaySignals.length }}</div>
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

          <!-- No signals -->
          <div v-if="!todaySignals.length" class="text-center py-20 text-gray-400">
            <div class="text-5xl mb-4">⚪</div>
            <p class="text-lg font-semibold text-gray-500">今日无做多信号</p>
            <p class="text-sm mt-1">候选池为空或尚未生成，请等待收盘后自动运行</p>
          </div>

          <!-- Signal cards -->
          <div v-else class="space-y-4">
            <SignalCard v-for="s in todaySignals" :key="s.code" :signal="s" />
          </div>
        </template>
      </div>

      <!-- ══════════════ Tab: 历史档案 ══════════════ -->
      <div v-else-if="tab === 'history'" class="flex gap-5 h-full min-h-0">
        <!-- Date list -->
        <div class="w-40 flex-shrink-0">
          <div class="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wide">历史记录</div>
          <div v-if="loadingDates" class="text-xs text-gray-400">加载中…</div>
          <div v-else-if="!histDates.length" class="text-xs text-gray-400">暂无历史数据</div>
          <div v-else class="space-y-1">
            <div v-for="d in histDates" :key="d"
                 class="px-3 py-2 rounded-xl text-sm cursor-pointer transition-all"
                 :style="selectedDate === d
                   ? 'background:rgba(59,130,246,0.1);color:#1e3a8a;font-weight:600;border:1px solid rgba(59,130,246,0.25)'
                   : 'color:#64748b;border:1px solid transparent'"
                 @click="loadHistDate(d)">
              {{ d.slice(5) }}
              <span v-if="d === today.trade_date"
                    class="ml-1 text-xs text-blue-400">今</span>
            </div>
          </div>
        </div>

        <!-- History signals -->
        <div class="flex-1 overflow-y-auto">
          <div v-if="!selectedDate" class="py-20 text-center text-gray-400">
            <div class="text-3xl mb-3">👈</div>
            <p>从左侧选择日期查看历史推荐</p>
          </div>
          <div v-else-if="loadingHist" class="py-20 text-center text-gray-400">加载中…</div>
          <div v-else-if="errHist" class="py-10 text-center text-red-500">{{ errHist }}</div>
          <template v-else>
            <div class="flex items-center gap-3 mb-4">
              <h3 class="font-bold text-gray-800">{{ selectedDate }} 的推荐</h3>
              <span class="text-xs px-2 py-0.5 rounded-full"
                    style="background:#eff6ff;color:#1e3a8a">
                {{ histSignals.length }} 只
              </span>
              <span class="text-xs text-gray-400">生成于 {{ histMeta.generated_at?.slice(11,16) }}</span>
            </div>
            <div v-if="!histSignals.length" class="text-center py-16 text-gray-400">
              该日无信号
            </div>
            <div v-else class="space-y-4">
              <SignalCard v-for="s in histSignals" :key="s.code" :signal="s" :historical="true" />
            </div>
          </template>
        </div>
      </div>

      <!-- ══════════════ Tab: 算法说明 ══════════════ -->
      <div v-else-if="tab === 'algo'"
           class="min-h-full flex justify-center py-2 px-4">
        <div class="w-full" style="max-width:720px">
          <AlgoExplainer />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
import SignalCard   from '../components/SignalCard.vue'
import AlgoExplainer from '../components/AlgoExplainer.vue'

const TABS = [
  { key: 'today',   label: '📡 今日信号' },
  { key: 'history', label: '🗂 历史档案' },
  { key: 'algo',    label: '📖 算法说明' },
]
const tab = ref('today')

// ── Today ─────────────────────────────────────────────────────
const today       = ref({})
const loadingToday = ref(true)
const errToday    = ref('')

const todaySignals = computed(() => today.value?.signals ?? [])
const avgProb = computed(() =>
  todaySignals.value.length
    ? (todaySignals.value.reduce((s, x) => s + x.prob_up, 0) / todaySignals.value.length * 100).toFixed(1)
    : '0'
)
const genTime = computed(() => (today.value?.generated_at ?? '').slice(11, 16) || '—')

// ── History ───────────────────────────────────────────────────
const histDates   = ref([])
const loadingDates = ref(false)
const selectedDate = ref('')
const histMeta    = ref({})
const histSignals = ref([])
const loadingHist = ref(false)
const errHist     = ref('')

async function loadHistDate(date) {
  selectedDate.value = date
  loadingHist.value  = true
  errHist.value      = ''
  histSignals.value  = []
  try {
    const d = await api('GET', `/api/signal-history/${date}`)
    histMeta.value   = d
    histSignals.value = d.signals ?? []
  } catch (e) {
    errHist.value = e.message
  } finally {
    loadingHist.value = false
  }
}

// ── Load ──────────────────────────────────────────────────────
onMounted(async () => {
  // Load today's signals
  try { today.value = await api('GET', '/api/signals') }
  catch (e) { errToday.value = e.message }
  finally   { loadingToday.value = false }

  // Load history dates (background)
  loadingDates.value = true
  try { histDates.value = await api('GET', '/api/signal-history') }
  catch {}
  finally { loadingDates.value = false }
})
</script>
