<template>
  <div class="rounded-2xl overflow-hidden shadow-sm transition-all"
       style="border:1px solid #e2e8f0">
    <!-- Card header -->
    <div class="flex items-center justify-between px-5 py-4"
         :style="`background:${headerBg}`">
      <div class="flex items-center gap-3">
        <!-- ETF tile -->
        <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold text-white shadow-sm"
             style="background:rgba(255,255,255,0.2)">
          {{ s.code.slice(-2) }}
        </div>
        <div>
          <div class="font-bold text-white text-base">{{ s.name }}</div>
          <div class="text-xs" style="color:rgba(255,255,255,0.65)">{{ s.code }}</div>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <!-- Advice badge -->
        <span class="px-3 py-1.5 rounded-xl text-sm font-bold"
              :style="adviceBadgeStyle">
          {{ ADV_EMOJI[s.advice] }} {{ ADV_LABEL[s.advice] || s.advice }}
        </span>
        <!-- Probability -->
        <div class="text-right">
          <div class="text-2xl font-bold text-white">{{ (s.prob_up * 100).toFixed(1) }}%</div>
          <div class="text-xs" style="color:rgba(255,255,255,0.6)">做多置信度</div>
        </div>
      </div>
    </div>

    <!-- Card body -->
    <div class="bg-white px-5 py-4">
      <!-- Probability bars -->
      <div class="flex gap-4 mb-4 items-stretch">
        <div class="flex-1">
          <div class="flex items-center justify-between text-xs mb-1">
            <span class="text-gray-400">做多</span>
            <span class="font-bold" style="color:#059669">{{ pct(s.prob_up) }}</span>
          </div>
          <div class="h-2 rounded-full bg-gray-100">
            <div class="h-2 rounded-full transition-all" style="background:#059669"
                 :style="{width: pct(s.prob_up)}"></div>
          </div>
        </div>
        <div class="flex-1">
          <div class="flex items-center justify-between text-xs mb-1">
            <span class="text-gray-400">震荡</span>
            <span class="font-medium text-gray-500">{{ pct(s.prob_flat) }}</span>
          </div>
          <div class="h-2 rounded-full bg-gray-100">
            <div class="h-2 rounded-full transition-all" style="background:#94a3b8"
                 :style="{width: pct(s.prob_flat)}"></div>
          </div>
        </div>
        <div class="flex-1">
          <div class="flex items-center justify-between text-xs mb-1">
            <span class="text-gray-400">做空</span>
            <span class="font-medium" style="color:#f43f5e">{{ pct(s.prob_down) }}</span>
          </div>
          <div class="h-2 rounded-full bg-gray-100">
            <div class="h-2 rounded-full transition-all" style="background:#f43f5e"
                 :style="{width: pct(s.prob_down)}"></div>
          </div>
        </div>
        <!-- Price info -->
        <div class="border-l border-gray-100 pl-4 flex flex-col justify-center text-right flex-shrink-0">
          <div class="font-bold text-gray-800">¥{{ s.close?.toFixed(3) ?? '—' }}</div>
          <div class="text-xs font-medium mt-0.5"
               :style="(s.pct_chg ?? 0) >= 0 ? 'color:#059669' : 'color:#f43f5e'">
            {{ (s.pct_chg ?? 0) >= 0 ? '▲' : '▼' }}{{ Math.abs(s.pct_chg ?? 0).toFixed(2) }}%
          </div>
          <div class="text-xs text-gray-300 mt-0.5">{{ s.date }} 收盘</div>
        </div>
      </div>

      <!-- Indicator tags -->
      <div v-if="s.indicator_tags?.length" class="flex flex-wrap gap-1.5 mb-4">
        <span v-for="tag in s.indicator_tags" :key="tag"
              class="text-xs px-2.5 py-1 rounded-full font-medium"
              :style="tagStyle(tag)">
          {{ tag }}
        </span>
      </div>

      <!-- Advice reason -->
      <div class="rounded-xl px-4 py-3 text-sm leading-relaxed"
           :style="`background:${reasonBg};border-left:3px solid ${reasonBorder}`">
        <div class="text-xs font-semibold mb-1" :style="`color:${reasonBorder}`">
          💼 {{ historical ? '当日建议' : '当前建议' }}：{{ ADV_LABEL[s.advice] || s.advice }}
        </div>
        <div style="color:#374151">{{ s.advice_reason }}</div>
      </div>

      <!-- Holding info (if any) -->
      <div v-if="s.holding" class="mt-3 flex items-center gap-4 text-xs text-gray-500"
           style="border-top:1px solid #f1f5f9;padding-top:12px">
        <span>成本价 <span class="font-bold text-gray-700">¥{{ s.cost_price?.toFixed(3) }}</span></span>
        <span>浮盈亏
          <span class="font-bold" :style="(s.unrealized_pct ?? 0) >= 0 ? 'color:#059669' : 'color:#f43f5e'">
            {{ ((s.unrealized_pct ?? 0) * 100).toFixed(1) }}%
          </span>
        </span>
        <span v-if="s.pos_weight">仓位占比 <span class="font-bold text-gray-700">{{ (s.pos_weight * 100).toFixed(1) }}%</span></span>
        <span v-if="s.sector" class="text-gray-400">板块：{{ s.sector }}</span>
      </div>

      <!-- Quick trade actions -->
      <div v-if="!historical" class="mt-3 flex items-center gap-2"
           style="border-top:1px solid #f1f5f9;padding-top:12px">
        <button class="flex-1 py-1.5 rounded-xl text-xs font-semibold text-white transition shadow-sm"
                style="background:linear-gradient(135deg,#064e3b,#059669)"
                @click.stop="$emit('trade', { ...s, action: 'buy' })">
          📈 买入记录
        </button>
        <button class="flex-1 py-1.5 rounded-xl text-xs font-semibold transition shadow-sm"
                style="background:#f0fdf4;color:#059669;border:1px solid #bbf7d0"
                @click.stop="$emit('trade', { ...s, action: 'position' })">
          📂 加入持仓
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  signal:     { type: Object, required: true },
  historical: { type: Boolean, default: false },
})
defineEmits(['trade'])
const s = computed(() => props.signal)

const ADV_LABEL = { OPEN: '建议开仓', ADD: '建议加仓', HOLD: '维持持有', REDUCE: '建议减仓', SKIP: '暂时跳过' }
const ADV_EMOJI = { OPEN: '🟢', ADD: '🔵', HOLD: '🟡', REDUCE: '🔴', SKIP: '⚪' }

// Header gradient by advice
const HEADER_COLORS = {
  OPEN:   'linear-gradient(135deg,#064e3b,#059669)',
  ADD:    'linear-gradient(135deg,#1e3a8a,#3b82f6)',
  HOLD:   'linear-gradient(135deg,#78350f,#d97706)',
  REDUCE: 'linear-gradient(135deg,#7f1d1d,#ef4444)',
  SKIP:   'linear-gradient(135deg,#1e293b,#475569)',
}
const headerBg = computed(() => HEADER_COLORS[s.value.advice] || HEADER_COLORS.SKIP)

// Advice badge
const BADGE_STYLES = {
  OPEN:   'background:rgba(255,255,255,0.2);color:white',
  ADD:    'background:rgba(255,255,255,0.2);color:white',
  HOLD:   'background:rgba(255,255,255,0.2);color:white',
  REDUCE: 'background:rgba(255,255,255,0.2);color:white',
  SKIP:   'background:rgba(255,255,255,0.15);color:rgba(255,255,255,0.8)',
}
const adviceBadgeStyle = computed(() => BADGE_STYLES[s.value.advice] || BADGE_STYLES.SKIP)

// Reason box
const REASON_STYLES = {
  OPEN:   { bg: '#f0fdf4', border: '#059669' },
  ADD:    { bg: '#eff6ff', border: '#3b82f6' },
  HOLD:   { bg: '#fffbeb', border: '#d97706' },
  REDUCE: { bg: '#fff1f2', border: '#ef4444' },
  SKIP:   { bg: '#f8fafc', border: '#94a3b8' },
}
const reasonBg     = computed(() => (REASON_STYLES[s.value.advice] || REASON_STYLES.SKIP).bg)
const reasonBorder = computed(() => (REASON_STYLES[s.value.advice] || REASON_STYLES.SKIP).border)

function pct(v) { return ((v ?? 0) * 100).toFixed(1) + '%' }

// Tag color by content keywords
function tagStyle(tag) {
  if (tag.includes('超卖') || tag.includes('偏低') || tag.includes('多头') || tag.includes('翻正') || tag.includes('放量'))
    return 'background:#f0fdf4;color:#14532d;border:1px solid #bbf7d0'
  if (tag.includes('超买') || tag.includes('偏高') || tag.includes('追高') || tag.includes('为负') || tag.includes('缩量'))
    return 'background:#fff1f2;color:#9f1239;border:1px solid #fecdd3'
  return 'background:#f1f5f9;color:#334155;border:1px solid #e2e8f0'
}
</script>
