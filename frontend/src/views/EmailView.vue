<template>
  <div class="p-6">
    <h2 class="text-xl font-bold text-gray-800 mb-5">📧 邮件发送记录</h2>

    <div v-if="loading" class="text-center text-gray-400 py-20">加载中…</div>

    <template v-else>
      <div v-if="logs.length" class="grid grid-cols-3 gap-4 mb-6">
        <div class="bg-white rounded-xl p-4 shadow-sm border">
          <div class="text-gray-400 text-xs mb-1">总发送</div>
          <div class="font-bold text-2xl text-gray-800">{{ logs.length }}</div>
        </div>
        <div class="bg-white rounded-xl p-4 shadow-sm border">
          <div class="text-gray-400 text-xs mb-1">成功</div>
          <div class="font-bold text-2xl text-green-600">{{ successCount }}</div>
        </div>
        <div class="bg-white rounded-xl p-4 shadow-sm border">
          <div class="text-gray-400 text-xs mb-1">失败</div>
          <div class="font-bold text-2xl text-red-500">{{ failCount }}</div>
        </div>
      </div>

      <div v-if="!logs.length" class="text-center py-24 text-gray-400">
        <div class="text-5xl">📭</div>
        <p class="mt-3 text-lg">暂无邮件记录</p>
        <p class="text-sm mt-1">发送邮件后会自动记录在这里</p>
      </div>

      <div v-else class="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-xs text-gray-400">
            <tr>
              <th class="px-4 py-3 text-left">时间</th>
              <th class="px-4 py-3 text-left">收件人</th>
              <th class="px-4 py-3 text-left">主题</th>
              <th class="px-4 py-3 text-center">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(log, i) in logs" :key="i"
              class="border-t border-gray-50 hover:bg-gray-50"
            >
              <td class="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">{{ log.timestamp }}</td>
              <td class="px-4 py-3 text-gray-700">{{ log.to }}</td>
              <td class="px-4 py-3 text-gray-700 max-w-sm truncate">{{ log.subject }}</td>
              <td class="px-4 py-3 text-center">
                <span v-if="log.success" class="badge bg-green-100 text-green-700">✓ 成功</span>
                <span v-else class="badge bg-red-100 text-red-700" :title="log.error ?? ''">✗ 失败</span>
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

const logs    = ref([])
const loading = ref(true)

const successCount = computed(() => logs.value.filter(l => l.success).length)
const failCount    = computed(() => logs.value.filter(l => !l.success).length)

onMounted(async () => {
  try { logs.value = await api('GET', '/api/email-log') }
  catch {}
  finally { loading.value = false }
})
</script>
