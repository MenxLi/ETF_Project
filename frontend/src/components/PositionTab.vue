<template>
  <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
    <div class="flex items-center justify-between px-5 py-4" style="border-bottom:1px solid #f1f5f9">
      <div class="flex items-center gap-2">
        <span class="font-semibold text-gray-800">持仓明细</span>
        <span class="text-xs px-2 py-0.5 rounded-full font-medium"
              style="background:#eff6ff;color:#1d4ed8">
          {{ pf.positions?.length ?? 0 }} 只
        </span>
      </div>
      <button class="text-sm font-medium px-4 py-2 rounded-xl text-white transition shadow-sm"
              style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)"
              @click="openAdd">📥 导入初始持仓</button>
    </div>

    <table class="w-full text-sm">
      <thead style="background:#f8fafc">
        <tr>
          <th class="px-4 py-3 text-left text-xs font-semibold text-gray-400">标的</th>
          <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">股数</th>
          <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">成本价</th>
          <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">成本市值</th>
          <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">现价</th>
          <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">现值</th>
          <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">浮盈</th>
          <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">浮盈%</th>
          <th class="px-4 py-3 text-center text-xs font-semibold text-gray-400">买入日期</th>
          <th class="px-4 py-3 text-right text-xs font-semibold text-gray-400">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!pf.positions?.length">
          <td colspan="10" class="text-center py-14 text-gray-400">
            <div class="text-4xl mb-3">📭</div>
            <p class="font-medium">暂无持仓</p>
            <p class="text-xs mt-1">点击「导入初始持仓」添加使用平台前的已有持仓</p>
          </td>
        </tr>
        <template v-for="p in pf.positions" :key="p.code">
        <tr class="transition-colors" :style="{ borderTop: '1px solid #f8fafc' }"
            @mouseenter="$event.currentTarget.style.background='#fafbff'"
            @mouseleave="$event.currentTarget.style.background=''">
          <td class="px-4 py-4">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-xl flex items-center justify-center text-xs font-bold text-white shadow-sm"
                   style="background:linear-gradient(135deg,#3b82f6,#1d4ed8)">
                {{ p.code.slice(-2) }}
              </div>
              <div>
                <div class="flex items-center gap-1.5 font-semibold text-gray-800">
                  {{ p.name }}
                  <span v-if="sellSigs[p.code]"
                        class="text-xs px-1.5 py-0.5 rounded font-semibold"
                        :style="TRIGGER_BADGE[sellSigs[p.code]]?.style">
                    {{ TRIGGER_BADGE[sellSigs[p.code]]?.label }}
                  </span>
                </div>
                <div class="text-xs text-gray-400">{{ p.code }}</div>
              </div>
            </div>
          </td>
          <td class="px-4 py-4 text-right text-gray-700 font-medium">{{ p.shares.toLocaleString() }}</td>
          <td class="px-4 py-4 text-right text-gray-700">¥{{ p.cost_price.toFixed(3) }}</td>
          <td class="px-4 py-4 text-right font-semibold text-gray-800">
            {{ fmtCash(p.shares * p.cost_price) }}
          </td>
          <td class="px-4 py-4 text-right">
            <span v-if="pricesLoading" class="text-xs text-gray-300">…</span>
            <span v-else-if="marketPrices[p.code]" class="text-gray-700">
              ¥{{ marketPrices[p.code].toFixed(3) }}
            </span>
            <span v-else class="text-xs text-gray-300">--</span>
          </td>
          <td class="px-4 py-4 text-right font-semibold text-gray-800">
            <span v-if="marketPrices[p.code]">{{ fmtCash(p.shares * marketPrices[p.code]) }}</span>
            <span v-else class="text-xs text-gray-300">--</span>
          </td>
          <td class="px-4 py-4 text-right font-semibold">
            <template v-if="marketPrices[p.code]">
              <span :style="{ color: profitColor(p.shares * (marketPrices[p.code] - p.cost_price)) }">
                {{ fmtProfit(p.shares * (marketPrices[p.code] - p.cost_price)) }}
              </span>
            </template>
            <span v-else class="text-xs text-gray-300">--</span>
          </td>
          <td class="px-4 py-4 text-right font-semibold">
            <template v-if="marketPrices[p.code]">
              <span :style="{ color: profitColor(marketPrices[p.code] - p.cost_price) }">
                {{ fmtPct2((marketPrices[p.code] - p.cost_price) / p.cost_price * 100) }}
              </span>
            </template>
            <span v-else class="text-xs text-gray-300">--</span>
          </td>
          <td class="px-4 py-4 text-center">
            <span class="text-xs px-2.5 py-1 rounded-full" style="background:#f1f5f9;color:#64748b">
              {{ p.buy_date }}
            </span>
          </td>
          <td class="px-4 py-4 text-right">
            <div class="flex items-center justify-end gap-2">
              <button class="text-xs font-semibold px-2 py-1 rounded-lg transition"
                      :style="activeQuick?.code===p.code&&activeQuick.action==='buy'
                        ?'background:#059669;color:white'
                        :'background:#f0fdf4;color:#059669'"
                      @click="openQuick(p.code,'buy')">+加仓</button>
              <button class="text-xs font-semibold px-2 py-1 rounded-lg transition"
                      :style="activeQuick?.code===p.code&&activeQuick.action==='sell'
                        ?'background:#f43f5e;color:white'
                        :'background:#fff1f2;color:#f43f5e'"
                      @click="openQuick(p.code,'sell')">-减持</button>
              <span class="text-gray-200 select-none text-xs">|</span>
              <button class="text-xs font-medium" style="color:#3b82f6"
                      @click="openEdit(p.code)">编辑</button>
              <button class="text-xs font-medium" style="color:#94a3b8"
                      @click="deletePos(p.code)">删除</button>
            </div>
          </td>
        </tr>
        <tr v-if="activeQuick?.code === p.code" style="background:#f0fdf4">
          <td colspan="10" class="px-6 py-3">
            <div class="flex items-center gap-4 flex-wrap">
              <span class="text-sm font-semibold flex-shrink-0"
                    :style="activeQuick.action==='buy'?'color:#059669':'color:#f43f5e'">
                {{ activeQuick.action==='buy' ? '+ 加仓' : '- 减持' }} · {{ p.name }}
              </span>
              <div class="flex items-center gap-1.5">
                <label class="text-xs text-gray-400 flex-shrink-0">股数</label>
                <input v-model.number="quickForm.shares" type="number" min="100" step="100"
                       class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-400"
                       placeholder="100 股" @keyup.enter="submitQuick(p)" />
              </div>
              <div class="flex items-center gap-1.5">
                <label class="text-xs text-gray-400 flex-shrink-0">价格（元）</label>
                <input v-model.number="quickForm.price" type="number" step="0.001"
                       class="border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-blue-400"
                       placeholder="0.000" @keyup.enter="submitQuick(p)" />
              </div>
              <div v-if="quickQuota > 0" class="text-xs text-gray-500 flex-shrink-0">
                {{ activeQuick.action==='buy' ? '扣款' : '到账' }}
                <span class="font-semibold text-gray-700">{{ fmtCash(quickQuota) }}</span>
                <span class="mx-1.5 text-gray-300">·</span>
                现金将变为
                <span :style="activeQuick.action==='buy'&&pf.cash-quickQuota<0
                              ?'color:#ef4444;font-weight:600':'color:#374151'">
                  {{ fmtCash(activeQuick.action==='buy' ? pf.cash-quickQuota : pf.cash+quickQuota) }}
                </span>
              </div>
              <div class="ml-auto flex items-center gap-2 flex-shrink-0">
                <button @click="submitQuick(p)"
                        class="px-3 py-1.5 rounded-lg text-xs font-semibold text-white transition"
                        :style="activeQuick.action==='buy'
                          ?'background:linear-gradient(135deg,#064e3b,#059669)'
                          :'background:linear-gradient(135deg,#9f1239,#f43f5e)'">
                  确认
                </button>
                <button @click="activeQuick = null"
                        class="px-3 py-1.5 rounded-lg text-xs font-medium border border-gray-200 text-gray-500 transition">
                  取消
                </button>
              </div>
            </div>
          </td>
        </tr>
        </template>
      </tbody>
    </table>
  </div>

  <!-- 导入/编辑持仓 Modal -->
  <Teleport to="body">
    <div v-if="showModal" class="modal-overlay">
      <div class="modal-box" @click.stop>
        <div class="flex items-center justify-between mb-4">
          <h3 class="modal-title" style="margin-bottom:0">{{ modalTitle }}</h3>
          <button class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all text-lg font-light"
                  @click="showModal = false">✕</button>
        </div>

        <div v-if="editCode === null"
             class="flex items-start gap-2 text-xs text-blue-700 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2 mb-3">
          <span class="mt-0.5">ℹ️</span>
          <span>仅用于导入使用平台前的已有持仓，<strong>不扣减现金余额</strong>。日常交易请使用「新增交易」按钮。</span>
        </div>

        <div class="space-y-3">
          <div>
            <label class="field-label">ETF 代码 *</label>
            <div v-if="editCode === null && todaySignals.length" class="mb-2">
              <span class="text-xs text-gray-400 mr-1.5">今日推荐：</span>
              <button v-for="s in todaySignals" :key="s.code"
                      class="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full mr-1 mb-1 border transition"
                      :style="form.code === s.code
                        ? 'background:#059669;color:white;border-color:#059669'
                        : 'background:#f0fdf4;color:#065f46;border-color:#bbf7d0'"
                      @click="form.code = s.code; form.name = s.name">
                {{ s.name }}
                <span class="opacity-70">{{ (s.prob_up * 100).toFixed(0) }}%</span>
              </button>
            </div>
            <EtfSearch v-model="form.code" v-model:name="form.name"
                       :readonly="editCode !== null"
                       placeholder="输入代码或名称搜索，例：沪深300" />
          </div>
          <div>
            <label class="field-label">名称</label>
            <input v-model="form.name" type="text" readonly class="input bg-gray-50 text-gray-400" />
          </div>
          <div class="flex gap-3">
            <div class="flex-1">
              <label class="field-label">股数 *</label>
              <input v-model.number="form.shares" type="number" placeholder="例：1000" class="input" />
            </div>
            <div class="flex-1">
              <label class="field-label">成本价（元）*</label>
              <input v-model.number="form.cost_price" type="number" step="0.001"
                     placeholder="例：3.250" class="input" />
            </div>
          </div>
          <div>
            <label class="field-label">买入日期</label>
            <input v-model="form.buy_date" type="date" class="input" />
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-cancel" @click="showModal = false">取消</button>
          <button class="btn-primary" @click="submit">保存</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { api, fmtCash, todayStr } from '../api.js'
import { store } from '../store.js'
import EtfSearch from './EtfSearch.vue'

const props = defineProps({
  pf:            { type: Object,  required: true },
  selId:         { type: String,  required: true },
  todaySignals:  { type: Array,   default: () => [] },
  marketPrices:  { type: Object,  default: () => ({}) },
  pricesLoading: { type: Boolean, default: false },
  sellSigs:      { type: Object,  default: () => ({}) },
})
const emit = defineEmits(['refresh'])

const TRIGGER_BADGE = {
  STOP_LOSS:   { label: '止损', style: 'background:#fef2f2;color:#dc2626;border:1px solid #fecaca' },
  TAKE_PROFIT: { label: '止盈', style: 'background:#fffbeb;color:#b45309;border:1px solid #fde68a' },
  MODEL_SELL:  { label: '看空', style: 'background:#fff1f2;color:#e11d48;border:1px solid #fecdd3' },
}

const activeQuick = ref(null)       // { code, action: 'buy'|'sell' }
const quickForm   = reactive({ shares: '', price: '' })
const quickQuota  = computed(() =>
  (!quickForm.shares || !quickForm.price) ? 0
  : Math.round(Number(quickForm.shares) * Number(quickForm.price) * 100) / 100
)

function openQuick(code, action) {
  if (activeQuick.value?.code === code && activeQuick.value?.action === action) {
    activeQuick.value = null; return
  }
  activeQuick.value = { code, action }
  quickForm.shares  = ''
  const pos = props.pf.positions.find(p => p.code === code)
  quickForm.price   = String(props.marketPrices[code] ?? pos?.cost_price ?? '')
}

async function submitQuick(pos) {
  if (!quickForm.shares || !quickForm.price) { alert('请填写股数和价格'); return }
  const { code, action } = activeQuick.value
  if (action === 'sell' && Number(quickForm.shares) > pos.shares) {
    alert(`最多可减持 ${pos.shares.toLocaleString()} 股`); return
  }
  try {
    store.status = action === 'buy' ? '加仓中…' : '减持中…'
    await api('POST', `/api/transactions/${props.selId}`, {
      action,
      etf_code: pos.code,
      etf_name: pos.name,
      shares:   Number(quickForm.shares),
      price:    Number(quickForm.price),
      date:     todayStr(),
      note:     action === 'buy' ? '快速加仓' : '快速减持',
    })
    activeQuick.value = null
    store.status = action === 'buy' ? '加仓成功 ✓' : '减持成功 ✓'
    emit('refresh')
  } catch (e) {
    store.status = (action === 'buy' ? '加仓' : '减持') + '失败: ' + e.message
  }
}

function profitColor(v) {
  return v > 0 ? '#059669' : v < 0 ? '#ef4444' : '#94a3b8'
}
function fmtProfit(v) {
  const abs = Math.abs(Math.round(v || 0))
  return (v >= 0 ? '+¥' : '-¥') + abs.toLocaleString('zh-CN')
}
function fmtPct2(v) {
  return (v >= 0 ? '+' : '') + (v || 0).toFixed(2) + '%'
}

const showModal  = ref(false)
const editCode   = ref(null)
const modalTitle = ref('导入初始持仓')
const form = reactive({ code: '', name: '', shares: '', cost_price: '', buy_date: todayStr() })

function openAdd() {
  editCode.value   = null
  modalTitle.value = '导入初始持仓'
  Object.assign(form, { code: '', name: '', shares: '', cost_price: '', buy_date: todayStr() })
  showModal.value  = true
}

function openEdit(code) {
  const pos = props.pf?.positions?.find(p => p.code === code)
  if (!pos) return
  editCode.value   = code
  modalTitle.value = '编辑持仓'
  Object.assign(form, {
    code: pos.code, name: pos.name,
    shares: pos.shares, cost_price: pos.cost_price, buy_date: pos.buy_date,
  })
  showModal.value = true
}

async function submit() {
  const code = form.code.trim()
  const name = form.name || store.etfList[code] || code
  if (!code || isNaN(form.shares) || isNaN(form.cost_price)) {
    alert('请填写代码、股数和成本价'); return
  }
  try {
    store.status = '保存中…'
    await api('POST', `/api/portfolio/${props.selId}/positions`, {
      code, name,
      shares:     Number(form.shares),
      cost_price: Number(form.cost_price),
      buy_date:   form.buy_date,
    })
    showModal.value = false
    store.status = '已保存 ✓'
    emit('refresh')
  } catch (e) { store.status = '保存失败: ' + e.message }
}

async function deletePos(code) {
  if (!confirm(`确认删除持仓 ${code}？`)) return
  try {
    await api('DELETE', `/api/portfolio/${props.selId}/positions/${code}`)
    store.status = '已删除 ✓'
    emit('refresh')
  } catch (e) { store.status = '删除失败: ' + e.message }
}
</script>

<style scoped>
.input { @apply w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition bg-white; }
.field-label { @apply block text-xs font-medium text-gray-500 mb-1.5; }
.btn-primary { @apply flex-1 py-2.5 rounded-xl text-sm font-semibold text-white transition cursor-pointer border-0; background: linear-gradient(135deg, #1e3a8a, #3b82f6); }
.btn-cancel  { @apply flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-xl text-sm font-semibold transition cursor-pointer; }
.modal-overlay { @apply fixed inset-0 flex items-center justify-center z-50; background: rgba(15,23,42,.6); backdrop-filter: blur(4px); }
.modal-box    { @apply bg-white rounded-2xl shadow-2xl w-96 p-6; }
.modal-title  { @apply text-base font-bold text-gray-800 mb-5; }
.modal-actions { @apply flex gap-2 mt-5; }
</style>
