<template>
  <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
    <div class="flex items-center justify-between px-5 py-4" style="border-bottom:1px solid #f1f5f9">
      <div class="flex items-center gap-2">
        <span class="font-semibold text-gray-800">交易记录</span>
        <span class="text-xs px-2 py-0.5 rounded-full font-medium"
              style="background:#f5f3ff;color:#6d28d9">
          {{ transactions.length }} 笔
        </span>
      </div>
      <button class="text-sm font-medium px-4 py-2 rounded-xl text-white transition shadow-sm"
              style="background:linear-gradient(135deg,#3b0764,#7c3aed)"
              @click="openAdd">+ 新增交易</button>
    </div>

    <table class="w-full text-sm">
      <thead style="background:#f8fafc">
        <tr>
          <th class="px-5 py-3 text-left text-xs font-semibold text-gray-400">日期</th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-gray-400">方向</th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-gray-400">标的</th>
          <th class="px-5 py-3 text-right text-xs font-semibold text-gray-400">数量</th>
          <th class="px-5 py-3 text-right text-xs font-semibold text-gray-400">成交价</th>
          <th class="px-5 py-3 text-right text-xs font-semibold text-gray-400">金额</th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-gray-400">备注</th>
          <th class="px-5 py-3"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!transactions.length">
          <td colspan="8" class="text-center py-14 text-gray-400">
            <div class="text-4xl mb-3">📋</div>
            <p class="font-medium">暂无交易记录</p>
            <p class="text-xs mt-1">点击「新增交易」添加</p>
          </td>
        </tr>
        <tr v-for="tx in transactions" :key="tx.id"
            class="transition-colors" :style="{ borderTop: '1px solid #f8fafc' }"
            @mouseenter="$event.currentTarget.style.background='#fafbff'"
            @mouseleave="$event.currentTarget.style.background=''">
          <td class="px-5 py-3.5">
            <span class="text-xs px-2 py-1 rounded-md" style="background:#f1f5f9;color:#64748b">{{ tx.date }}</span>
          </td>
          <td class="px-5 py-3.5">
            <span class="text-xs font-bold px-2.5 py-1 rounded-full"
                  :style="tx.action === 'buy' ? 'background:#d1fae5;color:#065f46' : 'background:#ffe4e6;color:#9f1239'">
              {{ tx.action === 'buy' ? '▲ 买入' : '▼ 卖出' }}
            </span>
          </td>
          <td class="px-5 py-3.5">
            <div class="font-semibold text-gray-800">{{ tx.etf_code }}</div>
            <div class="text-xs text-gray-400">{{ tx.etf_name }}</div>
          </td>
          <td class="px-5 py-3.5 text-right text-gray-700">{{ tx.shares.toLocaleString() }}</td>
          <td class="px-5 py-3.5 text-right text-gray-600">¥{{ tx.price.toFixed(3) }}</td>
          <td class="px-5 py-3.5 text-right font-semibold"
              :style="tx.action === 'sell' ? 'color:#059669' : 'color:#1e293b'">
            {{ tx.action === 'sell' ? '+' : '' }}{{ fmtCash(tx.amount) }}
          </td>
          <td class="px-5 py-3.5 text-xs text-gray-400 max-w-32 truncate">{{ tx.note || '—' }}</td>
          <td class="px-5 py-3.5 text-right">
            <button class="text-xs font-medium" style="color:#f43f5e" @click="deleteTx(tx)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- 新增交易 Modal -->
  <Teleport to="body">
    <div v-if="showModal" class="modal-overlay">
      <div class="modal-box" style="width:420px" @click.stop>
        <div class="flex items-center justify-between mb-4">
          <h3 class="modal-title" style="margin-bottom:0">新增交易记录</h3>
          <button class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all text-lg font-light"
                  @click="showModal = false">✕</button>
        </div>

        <div class="space-y-3">
          <!-- 方向 -->
          <div>
            <label class="field-label">交易方向</label>
            <div class="flex gap-2">
              <button v-for="opt in [{v:'buy',label:'▲ 买入'},{v:'sell',label:'▼ 卖出'}]" :key="opt.v"
                      class="flex-1 py-2 rounded-xl text-sm font-semibold border transition"
                      :style="form.action === opt.v
                        ? (opt.v === 'buy' ? 'background:#059669;color:white;border-color:#059669' : 'background:#e11d48;color:white;border-color:#e11d48')
                        : 'background:white;color:#64748b;border-color:#e2e8f0'"
                      @click="form.action = opt.v">{{ opt.label }}</button>
            </div>
          </div>

          <!-- 标的快捷 -->
          <div>
            <label class="field-label">ETF 标的 *</label>
            <div v-if="pf?.positions?.length || todaySignals.length" class="mb-2">
              <div v-if="pf?.positions?.length" class="mb-1.5">
                <span class="text-xs text-gray-400 mr-1.5">持仓中：</span>
                <button v-for="p in pf.positions" :key="p.code"
                        class="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full mr-1 mb-1 border transition"
                        :style="form.etf_code === p.code
                          ? 'background:#1e3a8a;color:white;border-color:#1e3a8a'
                          : 'background:#eff6ff;color:#1e3a8a;border-color:#bfdbfe'"
                        @click="quickPick(p.code, p.name)">
                  {{ p.name }}
                </button>
              </div>
              <div v-if="todaySignals.length">
                <span class="text-xs text-gray-400 mr-1.5">今日推荐：</span>
                <button v-for="s in todaySignals" :key="s.code"
                        class="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full mr-1 mb-1 border transition"
                        :style="form.etf_code === s.code
                          ? 'background:#059669;color:white;border-color:#059669'
                          : 'background:#f0fdf4;color:#065f46;border-color:#bbf7d0'"
                        @click="quickPick(s.code, s.name)">
                  {{ s.name }}
                  <span class="opacity-70">{{ (s.prob_up * 100).toFixed(0) }}%</span>
                </button>
              </div>
            </div>
            <EtfSearch v-model="form.etf_code" v-model:name="form.etf_name"
                       placeholder="输入代码或名称搜索" />
          </div>

          <!-- 日期 / 数量 / 价格 -->
          <div>
            <label class="field-label">交易日期</label>
            <input v-model="form.date" type="date" class="input" />
          </div>
          <div class="flex gap-3">
            <div class="flex-1">
              <label class="field-label">数量（股）*</label>
              <input v-model.number="form.shares" type="number" placeholder="例：1000" class="input" />
            </div>
            <div class="flex-1">
              <label class="field-label">
                成交价（元）*
                <span v-if="priceLoading" class="ml-1 text-blue-400 font-normal text-xs">拉取中…</span>
                <span v-else-if="priceSource === 'realtime'" class="ml-1 font-normal text-xs" style="color:#059669">● 实时价</span>
                <span v-else-if="priceSource === 'local_close'" class="ml-1 font-normal text-xs text-gray-400">昨收价</span>
              </label>
              <input v-model.number="form.price" type="number" step="0.001" placeholder="例：4.250" class="input" />
            </div>
          </div>

          <!-- 金额合计 -->
          <div class="flex justify-between items-center text-sm px-1 py-1 rounded-lg" style="background:#f8fafc">
            <span class="text-gray-500 text-xs">金额合计</span>
            <span class="font-bold"
                  :style="txAmount !== '—'
                    ? (form.action === 'sell' ? 'color:#059669' : 'color:#1e293b')
                    : 'color:#94a3b8'">
              {{ txAmount === '—' ? '—' : (form.action === 'sell' ? '+' : '') + '¥' + Number(txAmount).toLocaleString('zh-CN') }}
            </span>
          </div>

          <div>
            <label class="field-label">备注（可选）</label>
            <input v-model="form.note" type="text" placeholder="例：按信号买入" class="input" />
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-cancel" @click="showModal = false">取消</button>
          <button class="btn-primary"
                  :style="form.action === 'sell' ? 'background:linear-gradient(135deg,#9f1239,#e11d48);border:none' : ''"
                  @click="submit">
            确认{{ form.action === 'buy' ? '买入' : '卖出' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { api, fmtCash, todayStr, fetchRealtimePrice } from '../api.js'
import { store } from '../store.js'
import EtfSearch from './EtfSearch.vue'

const props = defineProps({
  transactions: { type: Array, required: true },
  pf:           { type: Object, required: true },
  selId:        { type: String, required: true },
  todaySignals: { type: Array, default: () => [] },
})
const emit = defineEmits(['refresh'])

const showModal   = ref(false)
const priceLoading = ref(false)
const priceSource  = ref('')
const form = reactive({
  date: todayStr(), action: 'buy',
  etf_code: '', etf_name: '', shares: '', price: '', note: '',
})

const txAmount = computed(() => {
  const s = Number(form.shares), p = Number(form.price)
  return (!isNaN(s) && !isNaN(p) && s > 0 && p > 0) ? (s * p).toFixed(2) : '—'
})

// 自动拉实时价
watch(() => form.etf_code, async (code) => {
  if (!code || !showModal.value) return
  priceSource.value  = ''
  priceLoading.value = true
  const rt = await fetchRealtimePrice(code)
  priceLoading.value = false
  if (rt?.price) { form.price = rt.price; priceSource.value = rt.source }
})

async function quickPick(code, name) {
  form.etf_code = code
  form.etf_name = name || store.etfList[code] || code
}

function openAdd() {
  Object.assign(form, {
    date: todayStr(), action: 'buy',
    etf_code: '', etf_name: '', shares: '', price: '', note: '',
  })
  priceSource.value = ''
  showModal.value   = true
}

async function submit() {
  if (!form.etf_code || !form.shares || !form.price) {
    alert('请填写 ETF、数量和成交价'); return
  }
  try {
    store.status = '保存中…'
    await api('POST', `/api/transactions/${props.selId}`, {
      date:     form.date,
      action:   form.action,
      etf_code: form.etf_code.trim(),
      etf_name: form.etf_name || store.etfList[form.etf_code] || form.etf_code,
      shares:   Number(form.shares),
      price:    Number(form.price),
      note:     form.note,
    })
    showModal.value = false
    store.status = form.action === 'buy' ? '买入已记录 ✓' : '卖出已记录 ✓'
    emit('refresh')
  } catch (e) { store.status = '保存失败: ' + e.message }
}

async function deleteTx(tx) {
  if (!confirm('确认删除这笔交易记录？')) return
  try {
    await api('DELETE', `/api/transactions/${props.selId}/${tx.id}`)
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
.modal-box    { @apply bg-white rounded-2xl shadow-2xl p-6; }
.modal-title  { @apply text-base font-bold text-gray-800 mb-5; }
.modal-actions { @apply flex gap-2 mt-5; }
</style>
