<template>
  <div>
    <div v-if="loading" class="py-24 text-center text-gray-400">加载中…</div>
    <div v-else-if="err" class="py-10 text-center text-red-500">{{ err }}</div>
    <template v-else>

      <!-- 顶部操作栏 -->
      <div class="flex items-center justify-between mb-5">
        <div>
          <h2 class="font-bold text-gray-800 text-base">
            模拟盘追踪
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
                :disabled="refreshing"
                @click="refreshPaper">
          {{ refreshing ? '计算中…' : '🔄 重新计算' }}
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
        <div class="rounded-2xl p-4 text-white shadow-md" :style="winRateColor">
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
        <div class="rounded-2xl p-4 text-white shadow-md" :style="avgRetColor">
          <div class="text-xs opacity-70 mb-1">平均收益</div>
          <div class="font-bold text-2xl">
            {{ ps.avg_ret_pct >= 0 ? '+' : '' }}{{ ps.avg_ret_pct ?? 0 }}%
          </div>
          <div class="text-xs opacity-60 mt-1">
            最优 +{{ ps.best_ret_pct ?? 0 }}% / 最差 {{ ps.worst_ret_pct ?? 0 }}%
          </div>
        </div>
      </div>

      <!-- 逐笔明细 -->
      <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
        <div class="flex items-center gap-3 px-5 py-4" style="border-bottom:1px solid #f1f5f9">
          <span class="font-semibold text-gray-800">逐笔明细</span>
          <div class="flex gap-1 ml-auto">
            <button v-for="f in FILTERS" :key="f.v"
                    class="text-xs px-3 py-1 rounded-full border transition"
                    :style="filter === f.v
                      ? 'background:#1e3a8a;color:white;border-color:#1e3a8a'
                      : 'background:white;color:#64748b;border-color:#e2e8f0'"
                    @click="filter = f.v">
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
                class="transition-colors" :style="{ borderTop: '1px solid #f8fafc' }"
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
                      :style="STATUS_STYLE[t.status] || STATUS_STYLE.pending">
                  {{ STATUS_LABEL[t.status] }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
import { store } from '../store.js'

const FILTERS = [
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

const paper     = ref({ summary: {}, trades: [], updated_at: null })
const loading   = ref(false)
const err       = ref('')
const refreshing = ref(false)
const filter    = ref('all')

const ps = computed(() => paper.value.summary ?? {})
const winRateColor = computed(() => {
  const r = ps.value.win_rate_pct ?? 0
  if (r >= 60) return 'background:linear-gradient(135deg,#064e3b,#059669)'
  if (r >= 50) return 'background:linear-gradient(135deg,#78350f,#d97706)'
  return 'background:linear-gradient(135deg,#7f1d1d,#ef4444)'
})
const avgRetColor = computed(() => {
  const r = ps.value.avg_ret_pct ?? 0
  return r >= 0
    ? 'background:linear-gradient(135deg,#064e3b,#059669)'
    : 'background:linear-gradient(135deg,#7f1d1d,#ef4444)'
})
const filteredTrades = computed(() => {
  const all = paper.value.trades ?? []
  return filter.value === 'all' ? all : all.filter(t => t.status === filter.value)
})

async function loadPaper() {
  loading.value = true; err.value = ''
  try { paper.value = await api('GET', '/api/paper-trades') }
  catch (e) { err.value = e.message }
  finally { loading.value = false }
}

async function refreshPaper() {
  refreshing.value = true
  try { paper.value = await api('POST', '/api/paper-trades/refresh', {}) }
  catch (e) { err.value = e.message }
  finally { refreshing.value = false }
}

onMounted(loadPaper)
</script>
