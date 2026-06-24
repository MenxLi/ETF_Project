<template>
  <div>
    <!-- 管理员操作栏 -->
    <div v-if="store.isAdmin" class="flex gap-2 mb-5">
      <button class="text-sm font-medium px-4 py-2 rounded-xl text-white transition shadow-sm flex items-center gap-2"
              style="background:linear-gradient(135deg,#7f1d1d,#dc2626)"
              :disabled="runningSellGen"
              @click="runSellGenerator">
        <span v-if="runningSellGen" class="animate-spin inline-block">⟳</span>
        {{ runningSellGen ? '生成中…' : '⚡ 重新生成卖出信号' }}
      </button>
      <button class="text-sm font-medium px-4 py-2 rounded-xl text-white transition shadow-sm flex items-center gap-2"
              style="background:linear-gradient(135deg,#78350f,#d97706)"
              :disabled="runningMonitor"
              @click="runPriceMonitor">
        <span v-if="runningMonitor" class="animate-spin inline-block">⟳</span>
        {{ runningMonitor ? '监控中…' : '📡 立即盘中监控' }}
      </button>
    </div>

    <!-- 收盘卖出建议 -->
    <div class="mb-8">
      <div class="flex items-center gap-3 mb-4">
        <h2 class="font-bold text-gray-800 text-base">📋 收盘卖出建议</h2>
        <span v-if="sellSignals.trade_date" class="text-xs px-2 py-0.5 rounded-full"
              style="background:#fef2f2;color:#b91c1c">
          {{ sellSignals.trade_date }}
        </span>
        <span class="text-xs px-2 py-0.5 rounded-full" style="background:#f1f5f9;color:#64748b">
          {{ sellSignals.signals?.length ?? 0 }} 条
        </span>
        <span v-if="sellSignals.generated_at" class="text-xs text-gray-400 ml-auto">
          生成于 {{ sellSignals.generated_at?.slice(11, 16) }}
        </span>
      </div>

      <div v-if="loadingSell" class="py-10 text-center text-gray-400">加载中…</div>
      <div v-else-if="errSell" class="py-6 text-center text-red-500 text-sm">{{ errSell }}</div>
      <div v-else-if="!sellSignals.signals?.length"
           class="text-center py-14 rounded-2xl"
           style="background:#f8fafc;border:1px solid #f1f5f9">
        <div class="text-4xl mb-3">✅</div>
        <p class="text-gray-500 font-semibold">暂无卖出建议</p>
        <p class="text-xs text-gray-400 mt-1">所有持仓均未触及止损/止盈/模型看空阈值</p>
      </div>
      <div v-else class="space-y-3">
        <div v-for="sig in sellSignals.signals" :key="sig.code + sig.user_id"
             class="rounded-2xl p-4 bg-white shadow-sm"
             :style="TRIGGER_CARD[sig.trigger] ?? 'border-l:4px solid #94a3b8'">
          <div class="flex items-start gap-3">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold text-white flex-shrink-0 shadow-sm"
                 style="background:linear-gradient(135deg,#7f1d1d,#dc2626)">
              {{ sig.code?.slice(-2) }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-semibold text-gray-800 text-sm">{{ sig.name }}</span>
                <span class="text-xs text-gray-400">{{ sig.code }}</span>
                <span v-if="sig.user_name" class="text-xs px-2 py-0.5 rounded-full"
                      style="background:#eff6ff;color:#1e3a8a">
                  {{ sig.user_name }}
                </span>
                <span class="text-xs px-2.5 py-0.5 rounded-full font-semibold"
                      :style="TRIGGER_STYLE[sig.trigger] ?? TRIGGER_STYLE.MODEL_SELL">
                  {{ TRIGGER_LABEL[sig.trigger] ?? sig.trigger }}
                </span>
              </div>
              <p class="text-xs text-gray-500 mt-1.5 leading-relaxed">{{ sig.trigger_reason }}</p>
              <div class="flex gap-4 mt-2">
                <div class="text-xs">
                  <span class="text-gray-400">成本价 </span>
                  <span class="font-medium text-gray-700">¥{{ sig.cost_price?.toFixed(3) ?? '—' }}</span>
                </div>
                <div class="text-xs">
                  <span class="text-gray-400">参考价 </span>
                  <span class="font-medium text-gray-700">¥{{ sig.current_price?.toFixed(3) ?? '—' }}</span>
                </div>
                <div class="text-xs font-bold"
                     :style="(sig.unrealized_pct ?? 0) >= 0 ? 'color:#059669' : 'color:#e11d48'">
                  {{ (sig.unrealized_pct ?? 0) >= 0 ? '+' : '' }}{{ ((sig.unrealized_pct ?? 0) * 100).toFixed(2) }}%
                </div>
                <div v-if="sig.tech_warnings?.length" class="text-xs text-amber-600 flex items-center gap-1">
                  ⚠ {{ sig.tech_warnings.join(' · ') }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 盘中价格告警 -->
    <div>
      <div class="flex items-center gap-3 mb-4">
        <h2 class="font-bold text-gray-800 text-base">🔔 盘中价格告警</h2>
        <span class="text-xs px-2 py-0.5 rounded-full"
              :style="activeAlerts.length ? 'background:#fef2f2;color:#b91c1c' : 'background:#f1f5f9;color:#64748b'">
          {{ activeAlerts.length }} 条未读
        </span>
        <button v-if="activeAlerts.length > 1"
                class="ml-auto text-xs px-3 py-1.5 rounded-xl border transition"
                style="border-color:#e2e8f0;color:#64748b"
                :disabled="dismissingAll"
                @click="dismissAllAlerts">
          {{ dismissingAll ? '处理中…' : '全部标记已读' }}
        </button>
      </div>

      <div v-if="loadingAlerts" class="py-10 text-center text-gray-400">加载中…</div>
      <div v-else-if="!activeAlerts.length"
           class="text-center py-14 rounded-2xl"
           style="background:#f8fafc;border:1px solid #f1f5f9">
        <div class="text-4xl mb-3">🔕</div>
        <p class="text-gray-500 font-semibold">暂无盘中告警</p>
        <p class="text-xs text-gray-400 mt-1">价格监控每 30 分钟运行一次，盘中触发后此处显示</p>
      </div>
      <div v-else class="space-y-3">
        <div v-for="alert in activeAlerts" :key="alert.id"
             class="rounded-2xl p-4 bg-white shadow-sm"
             :style="TRIGGER_CARD[alert.trigger] ?? 'border-l:4px solid #94a3b8'">
          <div class="flex items-start gap-3">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold text-white flex-shrink-0 shadow-sm"
                 style="background:linear-gradient(135deg,#78350f,#d97706)">
              {{ alert.code?.slice(-2) }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-semibold text-gray-800 text-sm">{{ alert.name }}</span>
                <span class="text-xs text-gray-400">{{ alert.code }}</span>
                <span v-if="alert.user_name" class="text-xs px-2 py-0.5 rounded-full"
                      style="background:#eff6ff;color:#1e3a8a">
                  {{ alert.user_name }}
                </span>
                <span class="text-xs px-2.5 py-0.5 rounded-full font-semibold"
                      :style="TRIGGER_STYLE[alert.trigger] ?? TRIGGER_STYLE.MODEL_SELL">
                  {{ TRIGGER_LABEL[alert.trigger] ?? alert.trigger }}
                </span>
                <span class="text-xs text-gray-400 ml-auto">{{ alert.timestamp?.slice(11, 16) }}</span>
              </div>
              <p class="text-xs text-gray-500 mt-1.5 leading-relaxed">{{ alert.trigger_reason }}</p>
              <div class="flex items-center gap-4 mt-2">
                <div class="text-xs">
                  <span class="text-gray-400">成本价 </span>
                  <span class="font-medium text-gray-700">¥{{ alert.cost_price?.toFixed(3) ?? '—' }}</span>
                </div>
                <div class="text-xs">
                  <span class="text-gray-400">实时价 </span>
                  <span class="font-medium text-gray-700">¥{{ alert.current_price?.toFixed(3) ?? '—' }}</span>
                </div>
                <div class="text-xs font-bold"
                     :style="(alert.unrealized_pct ?? 0) >= 0 ? 'color:#059669' : 'color:#e11d48'">
                  {{ (alert.unrealized_pct ?? 0) >= 0 ? '+' : '' }}{{ ((alert.unrealized_pct ?? 0) * 100).toFixed(2) }}%
                </div>
                <div class="text-xs text-gray-400">
                  {{ alert.shares?.toLocaleString() }} 股
                  · {{ alert.unrealized_pnl >= 0 ? '+' : '' }}¥{{ alert.unrealized_pnl?.toFixed(0) }}
                </div>
                <button class="ml-auto text-xs px-3 py-1 rounded-lg border transition"
                        style="border-color:#e2e8f0;color:#94a3b8"
                        :disabled="dismissingId === alert.id"
                        @click="dismissAlert(alert.id)">
                  {{ dismissingId === alert.id ? '…' : '已读' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
import { store } from '../store.js'

const TRIGGER_LABEL = { STOP_LOSS: '止损', TAKE_PROFIT: '止盈', MODEL_SELL: '模型看空' }
const TRIGGER_STYLE = {
  STOP_LOSS:   'background:#fef2f2;color:#b91c1c;border:1px solid #fecaca',
  TAKE_PROFIT: 'background:#fff7ed;color:#c2410c;border:1px solid #fed7aa',
  MODEL_SELL:  'background:#f5f3ff;color:#6d28d9;border:1px solid #ddd6fe',
}
const TRIGGER_CARD = {
  STOP_LOSS:   'border-left:4px solid #ef4444',
  TAKE_PROFIT: 'border-left:4px solid #f97316',
  MODEL_SELL:  'border-left:4px solid #8b5cf6',
}

// ── 卖出信号 ──────────────────────────────────────────────────
const sellSignals    = ref({ signals: [], count: 0, trade_date: '', generated_at: '' })
const loadingSell    = ref(false)
const errSell        = ref('')
const runningSellGen = ref(false)

async function loadSellSignals() {
  loadingSell.value = true; errSell.value = ''
  try { sellSignals.value = await api('GET', '/api/sell-signals') }
  catch (e) { errSell.value = e.message }
  finally { loadingSell.value = false }
}

async function runSellGenerator() {
  runningSellGen.value = true
  try {
    await api('POST', '/api/sell-signals/run', {})
    await loadSellSignals()
    store.status = '卖出信号已重新生成 ✓'
  } catch (e) { store.status = '生成失败: ' + e.message }
  finally { runningSellGen.value = false }
}

// ── 价格告警 ──────────────────────────────────────────────────
const sellAlerts    = ref({ alerts: [], count: 0 })
const loadingAlerts = ref(false)
const dismissingId  = ref('')
const dismissingAll = ref(false)
const runningMonitor = ref(false)

const activeAlerts = computed(() => (sellAlerts.value.alerts ?? []).filter(a => !a.dismissed))

async function loadAlerts() {
  loadingAlerts.value = true
  try { sellAlerts.value = await api('GET', '/api/alerts') }
  catch {} finally { loadingAlerts.value = false }
}

async function dismissAlert(id) {
  dismissingId.value = id
  try {
    await api('POST', `/api/alerts/${id}/dismiss`, {})
    const a = (sellAlerts.value.alerts ?? []).find(x => x.id === id)
    if (a) a.dismissed = true
  } catch (e) { store.status = '操作失败: ' + e.message }
  finally { dismissingId.value = '' }
}

async function dismissAllAlerts() {
  dismissingAll.value = true
  try {
    await api('POST', '/api/alerts/dismiss-all', {});
    (sellAlerts.value.alerts ?? []).forEach(a => { a.dismissed = true })
  } catch (e) { store.status = '操作失败: ' + e.message }
  finally { dismissingAll.value = false }
}

async function runPriceMonitor() {
  runningMonitor.value = true
  try {
    await api('POST', '/api/alerts/run', {})
    await loadAlerts()
    store.status = '盘中监控已执行 ✓'
  } catch (e) { store.status = '执行失败: ' + e.message }
  finally { runningMonitor.value = false }
}

onMounted(() => { loadSellSignals(); loadAlerts() })
</script>
