<template>
  <div class="p-6">
    <h2 class="text-xl font-bold text-gray-800 mb-5">🔬 回测结果</h2>

    <div v-if="loading" class="text-center text-gray-400 py-20">加载中…</div>

    <div v-else-if="!results.length" class="text-center py-24 text-gray-400">
      <div class="text-5xl">🔬</div>
      <p class="mt-3 text-lg">暂无回测结果</p>
      <p class="text-sm mt-1">
        运行
        <code class="bg-gray-100 px-1.5 py-0.5 rounded text-gray-600">
          python -m quant.backtest.backtester
        </code>
        生成结果
      </p>
    </div>

    <div v-else class="bg-white rounded-xl shadow-sm border overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-xs text-gray-400">
          <tr>
            <th class="px-4 py-3 text-left">代码</th>
            <th class="px-4 py-3 text-right">总收益</th>
            <th class="px-4 py-3 text-right">年化收益</th>
            <th class="px-4 py-3 text-right">胜率</th>
            <th class="px-4 py-3 text-right">最大回撤</th>
            <th class="px-4 py-3 text-right">交易次数</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in results" :key="r.code ?? r.etf_code"
            class="border-t border-gray-50 hover:bg-gray-50"
          >
            <td class="px-4 py-3 font-semibold text-gray-800">{{ r.code ?? r.etf_code ?? '—' }}</td>
            <td
              class="px-4 py-3 text-right font-medium"
              :class="(r.total_return ?? 0) >= 0 ? 'text-green-600' : 'text-red-500'"
            >{{ pct(r.total_return) }}</td>
            <td
              class="px-4 py-3 text-right font-medium"
              :class="(r.annual_return ?? 0) >= 0 ? 'text-green-600' : 'text-red-500'"
            >{{ pct(r.annual_return) }}</td>
            <td class="px-4 py-3 text-right">{{ pct(r.win_rate) }}</td>
            <td class="px-4 py-3 text-right text-red-500">{{ pct(r.max_drawdown) }}</td>
            <td class="px-4 py-3 text-right text-gray-500">{{ r.trade_count ?? r.n_trades ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const results = ref([])
const loading = ref(true)

const pct = v => v != null ? ((v * 100).toFixed(2) + '%') : '—'

onMounted(async () => {
  try { results.value = await api('GET', '/api/backtest') }
  catch {}
  finally { loading.value = false }
})
</script>
