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

        <!-- 手动触发器（管理员） -->
        <div v-if="store.isAdmin"
             class="mb-5 rounded-2xl p-4 flex items-center gap-4"
             :style="triggerBannerStyle">
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-sm" :style="triggerTextStyle">
              {{ triggerTitle }}
            </div>
            <div class="text-xs mt-0.5 opacity-70" :style="triggerTextStyle">
              {{ triggerSub }}
            </div>
            <!-- 进度日志 -->
            <div v-if="job.status === 'running' && job.log?.length"
                 class="mt-2 text-xs font-mono opacity-60" :style="triggerTextStyle">
              {{ job.log[job.log.length - 1] }}
            </div>
          </div>
          <button
            class="flex-shrink-0 px-4 py-2 rounded-xl text-sm font-semibold transition shadow-sm flex items-center gap-2"
            :style="triggerBtnStyle"
            :disabled="job.status === 'running'"
            @click="runSignals">
            <span v-if="job.status === 'running'" class="animate-spin inline-block">⟳</span>
            {{ triggerBtnLabel }}
          </button>
        </div>

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
            <SignalCard v-for="s in todaySignals" :key="s.code" :signal="s"
                        @trade="openTradeModal" />
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

      <!-- ══════════════ Tab: 模拟盘胜率 ══════════════ -->
      <div v-else-if="tab === 'paper'">
        <div v-if="loadingPaper" class="py-24 text-center text-gray-400">加载中…</div>
        <div v-else-if="errPaper" class="py-10 text-center text-red-500">{{ errPaper }}</div>
        <template v-else>

          <!-- 顶部操作栏 -->
          <div class="flex items-center justify-between mb-5">
            <div>
              <h2 class="font-bold text-gray-800 text-base">模拟盘追踪
                <span class="text-xs font-normal text-gray-400 ml-2">
                  入场价 = T+1 开盘，出场价 = T+{{ paper.trades?.[0]?.forward ?? 5 }}+1 开盘
                </span>
              </h2>
              <p v-if="paper.updated_at" class="text-xs text-gray-400 mt-0.5">
                上次更新：{{ paper.updated_at }}
              </p>
            </div>
            <button v-if="store.isAdmin"
                    class="text-sm font-medium px-4 py-2 rounded-xl text-white transition shadow-sm"
                    style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)"
                    :disabled="refreshingPaper"
                    @click="refreshPaper">
              {{ refreshingPaper ? '计算中…' : '🔄 重新计算' }}
            </button>
          </div>

          <!-- 汇总卡片 -->
          <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="rounded-2xl p-4 text-white shadow-md"
                 style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)">
              <div class="text-xs opacity-70 mb-1">已结束交易</div>
              <div class="font-bold text-2xl">{{ ps.total ?? 0 }}</div>
              <div class="text-xs opacity-60 mt-1">笔</div>
            </div>
            <div class="rounded-2xl p-4 text-white shadow-md"
                 :style="winRateColor">
              <div class="text-xs opacity-70 mb-1">整体胜率</div>
              <div class="font-bold text-2xl">{{ ps.win_rate_pct ?? 0 }}%</div>
              <div class="text-xs opacity-60 mt-1">{{ ps.wins ?? 0 }}胜 {{ ps.losses ?? 0 }}败</div>
            </div>
            <div class="rounded-2xl p-4 text-white shadow-md"
                 style="background:linear-gradient(135deg,#3b0764,#7c3aed)">
              <div class="text-xs opacity-70 mb-1">近30条胜率</div>
              <div class="font-bold text-2xl">{{ ps.recent30_win_rate_pct ?? 0 }}%</div>
              <div class="text-xs opacity-60 mt-1">样本 {{ ps.recent30_total ?? 0 }} 笔</div>
            </div>
            <div class="rounded-2xl p-4 text-white shadow-md"
                 :style="avgRetColor">
              <div class="text-xs opacity-70 mb-1">平均收益</div>
              <div class="font-bold text-2xl">
                {{ ps.avg_ret_pct >= 0 ? '+' : '' }}{{ ps.avg_ret_pct ?? 0 }}%
              </div>
              <div class="text-xs opacity-60 mt-1">
                最优 +{{ ps.best_ret_pct ?? 0 }}% / 最差 {{ ps.worst_ret_pct ?? 0 }}%
              </div>
            </div>
          </div>

          <!-- 交易明细表 -->
          <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
            <div class="flex items-center gap-3 px-5 py-4"
                 style="border-bottom:1px solid #f1f5f9">
              <span class="font-semibold text-gray-800">逐笔明细</span>
              <!-- 状态筛选 -->
              <div class="flex gap-1 ml-auto">
                <button v-for="f in PAPER_FILTERS" :key="f.v"
                        class="text-xs px-3 py-1 rounded-full border transition"
                        :style="paperFilter === f.v
                          ? 'background:#1e3a8a;color:white;border-color:#1e3a8a'
                          : 'background:white;color:#64748b;border-color:#e2e8f0'"
                        @click="paperFilter = f.v">
                  {{ f.label }}
                </button>
              </div>
            </div>

            <div v-if="!filteredTrades.length" class="text-center py-14 text-gray-400">
              <div class="text-4xl mb-3">📋</div>
              <p>暂无记录</p>
            </div>

            <table v-else class="w-full text-sm">
              <thead style="background:#f8fafc">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-gray-400">信号日</th>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-gray-400">标的</th>
                  <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">做多概率</th>
                  <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">入场价</th>
                  <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">出场价</th>
                  <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">收益</th>
                  <th class="px-4 py-3 text-center text-xs font-semibold text-gray-400">状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in filteredTrades" :key="t.signal_date + t.code"
                    class="transition-colors"
                    :style="{ borderTop: '1px solid #f8fafc' }"
                    @mouseenter="$event.currentTarget.style.background='#fafbff'"
                    @mouseleave="$event.currentTarget.style.background=''">
                  <td class="px-4 py-3 text-xs text-gray-500">{{ t.signal_date }}</td>
                  <td class="px-4 py-3">
                    <div class="font-semibold text-gray-800">{{ t.name }}</div>
                    <div class="text-xs text-gray-400">{{ t.code }}</div>
                  </td>
                  <td class="px-4 py-3 text-right">
                    <span class="text-xs font-bold" style="color:#059669">
                      {{ (t.prob_up * 100).toFixed(1) }}%
                    </span>
                  </td>
                  <td class="px-4 py-3 text-right text-gray-600 text-xs">
                    <div>{{ t.entry_price ? '¥' + t.entry_price : '—' }}</div>
                    <div class="text-gray-400">{{ t.entry_date ?? '' }}</div>
                  </td>
                  <td class="px-4 py-3 text-right text-gray-600 text-xs">
                    <div>{{ t.exit_price ? '¥' + t.exit_price : '—' }}</div>
                    <div class="text-gray-400">{{ t.exit_date ?? '' }}</div>
                  </td>
                  <td class="px-4 py-3 text-right font-bold text-sm">
                    <span v-if="t.ret !== null"
                          :style="t.ret >= 0 ? 'color:#059669' : 'color:#f43f5e'">
                      {{ t.ret >= 0 ? '+' : '' }}{{ (t.ret * 100).toFixed(2) }}%
                    </span>
                    <span v-else class="text-gray-300">—</span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="text-xs px-2.5 py-1 rounded-full font-semibold"
                          :style="statusStyle(t.status)">
                      {{ STATUS_LABEL[t.status] }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

        </template>
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

  <!-- ── 快速交易 / 持仓 Modal ──────────────────────────────── -->
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

        <!-- ETF info banner -->
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

        <!-- 买入记录表单 -->
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
                <span v-else-if="tradePriceSource === 'realtime'"
                      class="ml-1 font-normal text-xs" style="color:#059669">● 实时价</span>
                <span v-else-if="tradePriceSource === 'local_close'"
                      class="ml-1 font-normal text-xs text-gray-400">昨收价</span>
              </label>
              <input v-model.number="tradeForm.price" type="number" step="0.001" class="input" />
            </div>
          </div>
          <div class="flex justify-between items-center text-sm px-1 py-1 rounded-lg"
               style="background:#f8fafc">
            <span class="text-gray-500 text-xs">金额合计</span>
            <span class="font-bold" style="color:#1e293b">
              {{ tradeForm.shares > 0 && tradeForm.price > 0
                  ? '¥' + (tradeForm.shares * tradeForm.price).toLocaleString('zh-CN')
                  : '—' }}
            </span>
          </div>
          <div>
            <label class="field-label">备注（可选）</label>
            <input v-model="tradeForm.note" type="text" placeholder="例：按信号买入" class="input" />
          </div>
        </div>

        <!-- 加入持仓表单 -->
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
                <span v-else-if="tradePriceSource === 'realtime'"
                      class="ml-1 font-normal text-xs" style="color:#059669">● 实时价</span>
                <span v-else-if="tradePriceSource === 'local_close'"
                      class="ml-1 font-normal text-xs text-gray-400">昨收价</span>
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
import { ref, computed, reactive, onMounted } from 'vue'
import { api, todayStr, fetchRealtimePrice } from '../api.js'
import { store } from '../store.js'
import SignalCard   from '../components/SignalCard.vue'
import AlgoExplainer from '../components/AlgoExplainer.vue'

const TABS = [
  { key: 'today',  label: '📡 今日信号' },
  { key: 'history',label: '🗂 历史档案' },
  { key: 'paper',  label: '📊 模拟盘胜率' },
  { key: 'algo',   label: '📖 算法说明' },
]
const tab = ref('today')

// ── Signal trigger ────────────────────────────────────────────
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
  ['running','done','error'].includes(job.value.status) ? 'color:white' : 'color:#374151'
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
  if (['done','error'].includes(s)) return 'background:rgba(255,255,255,0.2);color:white'
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
          // 刷新今日信号
          loadingToday.value = true
          try { today.value = await api('GET', '/api/signals') }
          catch (e) { errToday.value = e.message }
          finally { loadingToday.value = false }
        }
      }
    } catch {}
  }, 2000)
}

// ── Paper trades ──────────────────────────────────────────────
const paper          = ref({ summary: {}, trades: [], updated_at: null })
const loadingPaper   = ref(false)
const errPaper       = ref('')
const refreshingPaper = ref(false)
const paperFilter    = ref('all')   // 'all' | 'closed' | 'open' | 'pending'

const PAPER_FILTERS = [
  { v: 'all',     label: '全部' },
  { v: 'closed',  label: '已结束' },
  { v: 'open',    label: '持仓中' },
  { v: 'pending', label: '待入场' },
]
const STATUS_LABEL = { closed: '已结束', open: '持仓中', pending: '待入场' }
const STATUS_STYLE = {
  closed:  'background:#f0fdf4;color:#065f46',
  open:    'background:#eff6ff;color:#1e3a8a',
  pending: 'background:#f8fafc;color:#64748b',
}
function statusStyle(s) { return STATUS_STYLE[s] || STATUS_STYLE.pending }

const ps = computed(() => paper.value.summary ?? {})
const winRateColor = computed(() => {
  const r = ps.value.win_rate_pct ?? 0
  if (r >= 60) return 'background:linear-gradient(135deg,#064e3b,#059669)'
  if (r >= 50) return 'background:linear-gradient(135deg,#78350f,#d97706)'
  return 'background:linear-gradient(135deg,#7f1d1d,#ef4444)'
})
const avgRetColor = computed(() => {
  const r = ps.value.avg_ret_pct ?? 0
  if (r >= 0) return 'background:linear-gradient(135deg,#064e3b,#059669)'
  return 'background:linear-gradient(135deg,#7f1d1d,#ef4444)'
})
const filteredTrades = computed(() => {
  const all = paper.value.trades ?? []
  if (paperFilter.value === 'all') return all
  return all.filter(t => t.status === paperFilter.value)
})

async function loadPaper() {
  loadingPaper.value = true
  errPaper.value = ''
  try {
    paper.value = await api('GET', '/api/paper-trades')
  } catch (e) {
    errPaper.value = e.message
  } finally {
    loadingPaper.value = false
  }
}

async function refreshPaper() {
  refreshingPaper.value = true
  try {
    paper.value = await api('POST', '/api/paper-trades/refresh', {})
  } catch (e) {
    errPaper.value = e.message
  } finally {
    refreshingPaper.value = false
  }
}

// ── Quick trade modal ──────────────────────────────────────────
const showTradeModal  = ref(false)
const tradeMode       = ref('buy')   // 'buy' | 'position'
const tradeSignal     = ref(null)
const tradeSaving     = ref(false)
const tradeMsgErr     = ref('')
const tradePriceLoading = ref(false)
const tradePriceSource  = ref('')    // 'realtime' | 'local_close' | ''
const tradeForm = reactive({ date: todayStr(), action: 'buy', shares: '', price: '', note: '' })

async function openTradeModal(sig) {
  tradeSignal.value     = sig
  tradeMode.value       = sig.action === 'position' ? 'position' : 'buy'
  tradeMsgErr.value     = ''
  tradeSaving.value     = false
  tradePriceSource.value = ''
  Object.assign(tradeForm, {
    date:   todayStr(),
    action: 'buy',
    shares: '',
    price:  sig.close ?? '',   // 先用昨收兜底
    note:   `按信号买入 ${sig.date}`,
  })
  showTradeModal.value = true

  // 异步拉取实时价，拉到了再更新
  tradePriceLoading.value = true
  const rt = await fetchRealtimePrice(sig.code)
  tradePriceLoading.value = false
  if (rt?.price) {
    tradeForm.price        = rt.price
    tradePriceSource.value = rt.source   // 'realtime' or 'local_close'
  }
}

async function submitTrade() {
  const uid = store.currentUser?.id
  if (!uid) { tradeMsgErr.value = '未登录'; return }
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
  } catch (e) {
    tradeMsgErr.value = e.message
  } finally {
    tradeSaving.value = false
  }
}

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
  // Restore trigger job status
  if (store.isAdmin) {
    try {
      const s = await api('GET', '/api/run-signals/status')
      job.value = s
      if (s.status === 'running') _startPolling()
    } catch {}
  }

  // Load today's signals
  try { today.value = await api('GET', '/api/signals') }
  catch (e) { errToday.value = e.message }
  finally   { loadingToday.value = false }

  // Load history dates (background)
  loadingDates.value = true
  try { histDates.value = await api('GET', '/api/signal-history') }
  catch {}
  finally { loadingDates.value = false }

  // Load paper trades (background)
  loadPaper()
})
</script>

<style scoped>
.input {
  @apply w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm
         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
         transition bg-white;
}
.field-label {
  @apply block text-xs font-medium text-gray-500 mb-1.5;
}
.modal-overlay {
  @apply fixed inset-0 flex items-center justify-center z-50;
  background: rgba(15,23,42,.6);
  backdrop-filter: blur(4px);
}
.modal-box {
  @apply bg-white rounded-2xl shadow-2xl w-96 p-6;
}
.modal-title {
  @apply text-base font-bold text-gray-800 mb-5;
}
</style>
