<template>
  <div class="flex flex-col h-full overflow-hidden">

    <!-- Tab bar -->
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

    <!-- Content -->
    <div class="flex-1 overflow-y-auto bg-white p-6" style="border-top:1px solid #e2e8f0">

      <!-- 今日信号 -->
      <TodaySignalTab v-if="tab === 'today'" ref="todayTabRef"
                      @open-trade="openTradeModal" />

      <!-- 卖出信号 -->
      <SellSignalTab v-else-if="tab === 'sell'" />

      <!-- 历史档案 -->
      <div v-else-if="tab === 'history'" class="flex gap-5 h-full min-h-0">
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
              <span v-if="d === todayDateStr" class="ml-1 text-xs text-blue-400">今</span>
            </div>
          </div>
        </div>
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
              <span class="text-xs px-2 py-0.5 rounded-full" style="background:#eff6ff;color:#1e3a8a">
                {{ histSignals.length }} 只
              </span>
              <span class="text-xs text-gray-400">生成于 {{ histMeta.generated_at?.slice(11,16) }}</span>
            </div>
            <div v-if="!histSignals.length" class="text-center py-16 text-gray-400">该日无信号</div>
            <div v-else class="space-y-4">
              <SignalCard v-for="s in histSignals" :key="s.code" :signal="s" :historical="true" />
            </div>
          </template>
        </div>
      </div>

      <!-- 模拟盘胜率 -->
      <PaperTradeTab v-else-if="tab === 'paper'" />

      <!-- 算法说明 -->
      <div v-else-if="tab === 'algo'" class="min-h-full flex justify-center py-2 px-4">
        <div class="w-full" style="max-width:720px">
          <AlgoExplainer />
        </div>
      </div>

    </div>
  </div>

  <!-- 快速交易 Modal -->
  <Teleport to="body">
    <div v-if="showTradeModal" class="modal-overlay" @click.self="showTradeModal = false">
      <div class="modal-box" @click.stop>
        <div class="flex items-center justify-between mb-4">
          <h3 class="modal-title" style="margin-bottom:0">
            {{ tradeMode === 'buy' ? '📈 买入记录' : '📂 加入持仓' }}
          </h3>
          <button class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all text-lg font-light"
                  @click="showTradeModal = false">✕</button>
        </div>

        <!-- ETF 信息 -->
        <div class="flex items-center gap-3 p-3 rounded-xl mb-4"
             style="background:#f0fdf4;border:1px solid #bbf7d0">
          <div class="w-9 h-9 rounded-xl flex items-center justify-center text-xs font-bold text-white shadow-sm"
               style="background:linear-gradient(135deg,#059669,#047857)">
            {{ tradeSignal?.code?.slice(-2) }}
          </div>
          <div>
            <div class="font-semibold text-gray-800 text-sm">{{ tradeSignal?.name }}</div>
            <div class="text-xs text-gray-400">{{ tradeSignal?.code }} · 昨收 ¥{{ tradeSignal?.close?.toFixed(3) }}</div>
          </div>
          <div class="ml-auto text-right">
            <div class="text-sm font-bold" style="color:#059669">{{ ((tradeSignal?.prob_up ?? 0) * 100).toFixed(1) }}%</div>
            <div class="text-xs text-gray-400">做多概率</div>
          </div>
        </div>

        <!-- 买入记录 -->
        <div v-if="tradeMode === 'buy'" class="space-y-3">
          <div class="flex gap-2">
            <button v-for="opt in [{v:'buy',label:'▲ 买入'},{v:'sell',label:'▼ 卖出'}]" :key="opt.v"
                    class="flex-1 py-2 rounded-xl text-sm font-semibold border transition"
                    :style="tradeForm.action === opt.v
                      ? (opt.v === 'buy' ? 'background:#059669;color:white;border-color:#059669' : 'background:#e11d48;color:white;border-color:#e11d48')
                      : 'background:white;color:#64748b;border-color:#e2e8f0'"
                    @click="tradeForm.action = opt.v">{{ opt.label }}</button>
          </div>
          <div>
            <label class="field-label">交易日期</label>
            <input v-model="tradeForm.date" type="date" class="input" />
          </div>
          <div class="flex gap-3">
            <div class="flex-1">
              <label class="field-label">数量（股）*</label>
              <input v-model.number="tradeForm.shares" type="number" placeholder="例：1000" class="input" />
            </div>
            <div class="flex-1">
              <label class="field-label">
                成交价（元）*
                <span v-if="tradePriceLoading" class="ml-1 text-blue-400 font-normal text-xs">拉取中…</span>
                <span v-else-if="tradePriceSource === 'realtime'" class="ml-1 font-normal text-xs" style="color:#059669">● 实时价</span>
                <span v-else-if="tradePriceSource === 'local_close'" class="ml-1 font-normal text-xs text-gray-400">昨收价</span>
              </label>
              <input v-model.number="tradeForm.price" type="number" step="0.001" class="input" />
            </div>
          </div>
          <div class="flex justify-between items-center text-sm px-1 py-1 rounded-lg" style="background:#f8fafc">
            <span class="text-gray-500 text-xs">金额合计</span>
            <span class="font-bold" style="color:#1e293b">
              {{ tradeForm.shares > 0 && tradeForm.price > 0
                  ? '¥' + (tradeForm.shares * tradeForm.price).toLocaleString('zh-CN') : '—' }}
            </span>
          </div>
          <div>
            <label class="field-label">备注（可选）</label>
            <input v-model="tradeForm.note" type="text" placeholder="例：按信号买入" class="input" />
          </div>
        </div>

        <!-- 加入持仓 -->
        <div v-else class="space-y-3">
          <div class="flex gap-3">
            <div class="flex-1">
              <label class="field-label">股数 *</label>
              <input v-model.number="tradeForm.shares" type="number" placeholder="例：1000" class="input" />
            </div>
            <div class="flex-1">
              <label class="field-label">
                成本价（元）*
                <span v-if="tradePriceLoading" class="ml-1 text-blue-400 font-normal text-xs">拉取中…</span>
                <span v-else-if="tradePriceSource === 'realtime'" class="ml-1 font-normal text-xs" style="color:#059669">● 实时价</span>
                <span v-else-if="tradePriceSource === 'local_close'" class="ml-1 font-normal text-xs text-gray-400">昨收价</span>
              </label>
              <input v-model.number="tradeForm.price" type="number" step="0.001" class="input" />
            </div>
          </div>
          <div>
            <label class="field-label">买入日期</label>
            <input v-model="tradeForm.date" type="date" class="input" />
          </div>
        </div>

        <div v-if="tradeMsgErr" class="mt-2 text-xs text-red-500">{{ tradeMsgErr }}</div>

        <div class="flex gap-2 mt-5">
          <button class="flex-1 border border-gray-200 text-gray-600 rounded-xl py-2.5 text-sm hover:bg-gray-50 cursor-pointer bg-white transition"
                  @click="showTradeModal = false">取消</button>
          <button class="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white transition cursor-pointer border-0"
                  style="background:linear-gradient(135deg,#064e3b,#059669)"
                  :disabled="tradeSaving"
                  @click="submitTrade">
            {{ tradeSaving ? '保存中…' : (tradeMode === 'buy' ? '确认记录' : '加入持仓') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api, todayStr, fetchRealtimePrice } from '../api.js'
import { store } from '../store.js'
import SignalCard     from '../components/SignalCard.vue'
import AlgoExplainer  from '../components/AlgoExplainer.vue'
import TodaySignalTab from '../components/TodaySignalTab.vue'
import SellSignalTab  from '../components/SellSignalTab.vue'
import PaperTradeTab  from '../components/PaperTradeTab.vue'

// #A1 已修复：卖出信号移至今日信号后面
const TABS = [
  { key: 'today',   label: '📡 今日信号' },
  { key: 'sell',    label: '🔴 卖出信号' },
  { key: 'history', label: '🗂 历史档案' },
  { key: 'paper',   label: '📊 模拟盘胜率' },
  { key: 'algo',    label: '📖 算法说明' },
]
const tab = ref('today')
const todayTabRef  = ref(null)
const todayDateStr = new Date().toISOString().slice(0, 10)

// ── 历史档案 ──────────────────────────────────────────────────
const histDates    = ref([])
const loadingDates = ref(false)
const selectedDate = ref('')
const histMeta     = ref({})
const histSignals  = ref([])
const loadingHist  = ref(false)
const errHist      = ref('')

async function loadHistDate(date) {
  selectedDate.value = date
  loadingHist.value  = true
  errHist.value      = ''
  histSignals.value  = []
  try {
    const d = await api('GET', `/api/signal-history/${date}`)
    histMeta.value    = d
    histSignals.value = d.signals ?? []
  } catch (e) { errHist.value = e.message }
  finally { loadingHist.value = false }
}

onMounted(async () => {
  loadingDates.value = true
  try { histDates.value = await api('GET', '/api/signal-history') }
  catch {} finally { loadingDates.value = false }
})

// ── 快速交易 Modal ─────────────────────────────────────────────
const showTradeModal    = ref(false)
const tradeMode         = ref('buy')
const tradeSignal       = ref(null)
const tradeSaving       = ref(false)
const tradeMsgErr       = ref('')
const tradePriceLoading = ref(false)
const tradePriceSource  = ref('')
const tradeForm = reactive({ date: todayStr(), action: 'buy', shares: '', price: '', note: '' })

async function openTradeModal(sig) {
  tradeSignal.value      = sig
  tradeMode.value        = sig.action === 'position' ? 'position' : 'buy'
  tradeMsgErr.value      = ''
  tradeSaving.value      = false
  tradePriceSource.value = ''
  Object.assign(tradeForm, {
    date:   todayStr(),
    action: 'buy',
    shares: '',
    price:  sig.close ?? '',
    note:   `按信号买入 ${sig.date}`,
  })
  showTradeModal.value = true

  tradePriceLoading.value = true
  const rt = await fetchRealtimePrice(sig.code)
  tradePriceLoading.value = false
  if (rt?.price) { tradeForm.price = rt.price; tradePriceSource.value = rt.source }
}

async function submitTrade() {
  const uid = store.currentUser?.id
  if (!uid)                                  { tradeMsgErr.value = '未登录'; return }
  if (!tradeForm.shares || !tradeForm.price) { tradeMsgErr.value = '请填写数量和价格'; return }
  tradeSaving.value = true
  tradeMsgErr.value = ''
  try {
    if (tradeMode.value === 'buy') {
      await api('POST', `/api/transactions/${uid}`, {
        date:     tradeForm.date,
        action:   tradeForm.action,
        etf_code: tradeSignal.value.code,
        etf_name: tradeSignal.value.name,
        shares:   Number(tradeForm.shares),
        price:    Number(tradeForm.price),
        note:     tradeForm.note,
      })
    } else {
      await api('POST', `/api/portfolio/${uid}/positions`, {
        code:       tradeSignal.value.code,
        name:       tradeSignal.value.name,
        shares:     Number(tradeForm.shares),
        cost_price: Number(tradeForm.price),
        buy_date:   tradeForm.date,
      })
    }
    showTradeModal.value = false
    store.status = `已记录 ${tradeSignal.value.name} ✓`
  } catch (e) { tradeMsgErr.value = e.message }
  finally { tradeSaving.value = false }
}
</script>

<style scoped>
.input {
  @apply w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm
         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
         transition bg-white;
}
.field-label { @apply block text-xs font-medium text-gray-500 mb-1.5; }
.modal-overlay {
  @apply fixed inset-0 flex items-center justify-center z-50;
  background: rgba(15,23,42,.6);
  backdrop-filter: blur(4px);
}
.modal-box   { @apply bg-white rounded-2xl shadow-2xl w-96 p-6; }
.modal-title { @apply text-base font-bold text-gray-800 mb-5; }
</style>
