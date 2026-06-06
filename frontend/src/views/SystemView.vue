<template>
  <div class="p-6">
    <h2 class="text-xl font-bold text-gray-800 mb-5">⚙️ 系统状态</h2>

    <div v-if="loading" class="text-center text-gray-400 py-20">加载中…</div>
    <div v-else-if="!status" class="text-center text-red-500 py-10">状态加载失败</div>

    <div v-else class="grid grid-cols-2 gap-4">
      <div
        v-for="c in cards" :key="c.key"
        class="bg-white rounded-xl shadow-sm border p-5"
      >
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-center gap-2">
              <span>{{ c.icon }}</span>
              <span class="font-semibold text-gray-800">{{ c.label }}</span>
            </div>
            <div class="text-xs text-gray-400 mt-1">{{ c.desc }}</div>
          </div>
          <span
            class="badge flex-shrink-0"
            :class="status[c.key]?.exists ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'"
          >
            {{ status[c.key]?.exists ? '正常' : '缺失' }}
          </span>
        </div>
        <div class="mt-3 text-xs" :class="status[c.key]?.exists ? 'text-gray-400' : 'text-yellow-600'">
          {{ status[c.key]?.last_modified
              ? '最后更新：' + status[c.key].last_modified
              : '文件不存在，功能可能受限' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const status  = ref(null)
const loading = ref(true)

const cards = [
  { label: '今日信号候选池', key: 'signals',    desc: '每日收盘后由 generator.py 生成', icon: '📡' },
  { label: '动态阈值校准',   key: 'thresholds', desc: '由 calibrator.py 维护',          icon: '🎯' },
  { label: '用户注册表',     key: 'users',      desc: 'portfolios/users.json',           icon: '👥' },
  { label: '邮件发送日志',   key: 'email_log',  desc: 'logs/email_log.jsonl',            icon: '📧' },
  { label: '模型文件',       key: 'models',     desc: 'quant/models/',                    icon: '🤖' },
]

onMounted(async () => {
  try { status.value = await api('GET', '/api/system-status') }
  catch {}
  finally { loading.value = false }
})
</script>
