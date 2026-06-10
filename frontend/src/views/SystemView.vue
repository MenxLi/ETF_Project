<template>
  <div class="p-6">
    <h2 class="text-xl font-bold text-gray-800 mb-5">⚙️ 系统状态</h2>

    <!-- 信号生成触发器 -->
    <div class="mb-5 bg-white rounded-2xl shadow-sm border p-5">
      <div class="flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span>🚀</span>
            <span class="font-semibold text-gray-800">手动触发信号生成</span>
            <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                  :style="jobBadgeStyle">{{ jobBadgeLabel }}</span>
          </div>
          <div class="text-xs text-gray-400">
            <template v-if="job.status === 'running'">
              开始于 {{ job.started_at }} — {{ job.log?.[job.log.length-1] ?? '处理中…' }}
            </template>
            <template v-else-if="job.status === 'done'">
              完成于 {{ job.finished_at }}，生成 {{ job.signal_count }} 个做多信号
            </template>
            <template v-else-if="job.status === 'error'">
              失败：{{ job.error }}
            </template>
            <template v-else>更新所有 ETF 行情并重新生成今日信号</template>
          </div>
        </div>
        <button class="text-sm font-medium px-4 py-2 rounded-xl text-white transition shadow-sm"
                style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)"
                :disabled="job.status === 'running'"
                @click="runSignals">
          {{ job.status === 'running' ? '生成中…' : '立即触发' }}
        </button>
      </div>
    </div>

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
import { ref, computed, onMounted } from 'vue'
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

// ── Signal trigger ────────────────────────────────────────────
const job = ref({ status: 'idle', signal_count: 0, started_at: null, finished_at: null, log: [], error: null })
let _pollTimer = null

const JOB_BADGE = {
  idle:    { label: '空闲',   style: 'background:#f1f5f9;color:#64748b' },
  running: { label: '运行中', style: 'background:#dbeafe;color:#1e3a8a' },
  done:    { label: '完成',   style: 'background:#dcfce7;color:#14532d' },
  error:   { label: '失败',   style: 'background:#ffe4e6;color:#9f1239' },
}
const jobBadgeLabel = computed(() => JOB_BADGE[job.value.status]?.label ?? '空闲')
const jobBadgeStyle = computed(() => JOB_BADGE[job.value.status]?.style ?? JOB_BADGE.idle.style)

async function runSignals() {
  try {
    await api('POST', '/api/run-signals', {})
    job.value.status = 'running'
    _startPolling()
  } catch (e) {
    alert('触发失败：' + e.message)
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
        // 刷新系统状态卡片
        status.value = await api('GET', '/api/system-status')
      }
    } catch {}
  }, 2000)
}

onMounted(async () => {
  try { status.value = await api('GET', '/api/system-status') }
  catch {}
  finally { loading.value = false }

  // 同步触发器状态
  try {
    const s = await api('GET', '/api/run-signals/status')
    job.value = s
    if (s.status === 'running') _startPolling()
  } catch {}
})
</script>
