<template>
  <div class="model-page">

    <!-- Header -->
    <div class="page-header">
      <div class="header-inner">
        <div>
          <h1 class="page-title">模型参数调整</h1>
          <p class="page-subtitle">调整候选池阈值 & 盘中确认参数</p>
        </div>
        <button class="btn-save"
                :class="saving ? 'opacity-50 cursor-not-allowed' : ''"
                :disabled="saving"
                @click="saveAll">
          {{ saving ? '保存中…' : '💾 保存所有设置' }}
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="content-wrap">

      <!-- Status banners -->
      <div v-if="errMsg" class="banner banner-error">⚠ {{ errMsg }}</div>
      <div v-if="okMsg"  class="banner banner-ok">✓ {{ okMsg }}</div>

      <!-- SECTION 1: Candidate Filter -->
      <div class="card">
        <div class="card-header">
          <span class="section-num">01</span>
          <div>
            <div class="section-title">候选池设置</div>
            <div class="section-sub">信号进入候选池的门槛</div>
          </div>
        </div>

        <div class="card-body space-y-6">

          <!-- Prob threshold -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <div>
                <div class="param-label">做多概率门槛</div>
                <div class="param-desc">模型输出的做多概率须超过此值才进入候选池</div>
              </div>
              <div class="big-value">
                {{ (cfg.prob_threshold * 100).toFixed(0) }}<span class="big-value-unit">%</span>
              </div>
            </div>
            <input type="range" v-model.number="cfg.prob_threshold"
                   min="0.30" max="0.95" step="0.01"
                   class="range-input w-full" />
            <div class="flex justify-between text-xs mt-1 text-gray-400">
              <span>30% 宽松</span>
              <span>默认 50%</span>
              <span>95% 严格</span>
            </div>

            <!-- Prob bands -->
            <div class="flex gap-2 mt-3">
              <div v-for="band in probBands" :key="band.label"
                   class="flex-1 py-1.5 px-1 rounded-lg text-center text-xs font-medium transition-all"
                   :class="cfg.prob_threshold >= band.min && cfg.prob_threshold < band.max
                     ? 'band-active' : 'band-inactive'">
                {{ band.label }}
              </div>
            </div>
          </div>

          <hr class="divider" />

          <!-- Stop loss -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <div>
                <div class="param-label">止损线</div>
                <div class="param-desc">持仓浮亏超过此比例时，生成卖出建议</div>
              </div>
              <div class="big-value" style="color:#dc2626">
                {{ (cfg.stop_loss * 100).toFixed(0) }}<span class="big-value-unit">%</span>
              </div>
            </div>
            <input type="range" v-model.number="cfg.stop_loss"
                   min="0.01" max="0.20" step="0.01"
                   class="range-input range-red w-full" />
            <div class="flex justify-between text-xs mt-1 text-gray-400">
              <span>1% 紧止损</span>
              <span>默认 5%</span>
              <span>20% 宽止损</span>
            </div>
          </div>

          <hr class="divider" />

          <!-- Take profit -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <div>
                <div class="param-label">止盈线</div>
                <div class="param-desc">持仓浮盈超过此比例时，生成卖出建议</div>
              </div>
              <div class="big-value" style="color:#059669">
                {{ (cfg.take_profit * 100).toFixed(0) }}<span class="big-value-unit">%</span>
              </div>
            </div>
            <input type="range" v-model.number="cfg.take_profit"
                   min="0.03" max="0.50" step="0.01"
                   class="range-input range-green w-full" />
            <div class="flex justify-between text-xs mt-1 text-gray-400">
              <span>3% 保守</span>
              <span>默认 8%</span>
              <span>50% 宽松</span>
            </div>
          </div>

          <hr class="divider" />

          <!-- Blacklist -->
          <div>
            <div class="param-label mb-0.5">ETF 黑名单</div>
            <div class="param-desc mb-3">黑名单内的品种不参与信号生成</div>
            <div class="flex flex-wrap gap-2 mb-3">
              <div v-for="code in cfg.blacklist" :key="code" class="chip">
                {{ code }}
                <button class="chip-remove" @click="removeBlacklist(code)">×</button>
              </div>
              <div v-if="!cfg.blacklist.length" class="text-xs text-gray-400 py-1">
                暂无黑名单项
              </div>
            </div>
            <div class="flex gap-2">
              <input v-model="newCode" type="text" maxlength="8"
                     placeholder="输入 6 位代码，例：159869"
                     class="input flex-1 px-3 py-2 text-sm"
                     @keydown.enter="addBlacklist" />
              <button class="btn-danger" @click="addBlacklist">+ 加入黑名单</button>
            </div>
          </div>

        </div>
      </div>

      <!-- SECTION 2: Intraday Confirmation -->
      <div class="card">
        <div class="card-header">
          <span class="section-num" style="background:#ede9fe;color:#7c3aed">02</span>
          <div class="flex-1 min-w-0">
            <div class="section-title">盘中确认阈值</div>
            <div class="section-sub">4 个交易节点的过滤参数</div>
          </div>
          <div class="flex items-center gap-3">
            <div v-if="calibrated.calibrated_at" class="text-xs text-gray-400">
              上次校准：{{ calibrated.calibrated_at }}
            </div>
            <button class="btn-outline"
                    :class="calibrating ? 'opacity-50 cursor-not-allowed' : ''"
                    :disabled="calibrating"
                    @click="recalibrate">
              {{ calibrating ? '⏳ 校准中…' : '🔄 重新自动校准' }}
            </button>
          </div>
        </div>

        <!-- Market stats -->
        <div v-if="calibrated._market_vol_std" class="market-stats">
          <div class="market-stat">
            <span class="stat-label">市场波动率</span>
            <span class="stat-val">{{ calibrated._market_vol_std?.toFixed(2) }}%</span>
          </div>
          <div class="stat-divider"></div>
          <div class="market-stat">
            <span class="stat-label">ATR 均值</span>
            <span class="stat-val">{{ calibrated._market_atr_mean?.toFixed(2) }}%</span>
          </div>
          <div class="stat-divider"></div>
          <div class="market-stat">
            <span class="stat-label">量比 P50</span>
            <span class="stat-val">{{ calibrated._vol_ratio_p50?.toFixed(2) }}</span>
          </div>
          <div class="stat-divider"></div>
          <div class="market-stat">
            <span class="stat-label">回望周期</span>
            <span class="stat-val">{{ calibrated.lookback_days || 20 }}天</span>
          </div>
        </div>
        <div v-else class="warn-bar">
          ⚠ 尚未进行自动校准，当前使用默认值。建议点击「重新自动校准」。
        </div>

        <!-- Threshold node groups -->
        <div class="divide-y divide-gray-100">
          <div v-for="group in thresholdGroups" :key="group.node" class="node-group">
            <div class="node-header">
              <span class="node-badge" :style="`background:${group.badgeBg};color:${group.color}`">
                {{ group.time }}
              </span>
              <span class="node-label">{{ group.label }}</span>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div v-for="param in group.params" :key="param.key" class="param-card">
                <div class="flex-1 min-w-0">
                  <div class="param-card-label">{{ param.label }}</div>
                  <div class="param-card-desc">{{ param.desc }}</div>
                  <div class="param-auto" v-if="calibrated[param.key] != null">
                    自动值：<span class="font-semibold text-blue-600">{{ calibrated[param.key].toFixed(2) }}</span>
                    <span class="text-gray-400"> {{ param.unit }}</span>
                  </div>
                </div>
                <div class="flex flex-col items-end gap-2">
                  <label class="flex items-center gap-1.5 cursor-pointer select-none">
                    <span class="text-xs text-gray-400">手动覆盖</span>
                    <div class="toggle" :class="hasOverride(param.key) ? 'toggle-on' : ''"
                         @click="toggleOverride(param.key)">
                      <div class="toggle-thumb"></div>
                    </div>
                  </label>
                  <input v-if="hasOverride(param.key)"
                         :value="cfg.threshold_overrides[param.key]"
                         @input="setOverride(param.key, $event.target.value)"
                         type="number" :step="param.step || 0.01"
                         class="input w-24 px-2 py-1.5 text-sm text-right" />
                  <div v-else class="text-xs text-gray-400">自动</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- SECTION 3: Lookback -->
      <div class="card">
        <div class="card-body">
          <div class="flex items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <span class="section-num" style="background:#dcfce7;color:#16a34a">03</span>
              <div>
                <div class="param-label">自动校准回望周期</div>
                <div class="param-desc">校准时参考最近多少个交易日的市场数据</div>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <input v-model.number="lookback" type="number" min="5" max="120"
                     class="input w-20 px-3 py-2 text-sm text-center" />
              <span class="text-sm text-gray-400">个交易日</span>
            </div>
          </div>
        </div>
      </div>

      <!-- SECTION 4: Model Version Management -->
      <div class="card">
        <div class="card-header">
          <span class="section-num" style="background:#fef9c3;color:#a16207">04</span>
          <div class="flex-1 min-w-0">
            <div class="section-title">模型版本管理</div>
            <div class="section-sub">每次训练后自动留存历史版本，支持一键回滚</div>
          </div>
          <button class="btn-outline" @click="loadVersions" :disabled="versionsLoading">
            {{ versionsLoading ? '⏳' : '🔄 刷新' }}
          </button>
        </div>

        <!-- Empty state -->
        <div v-if="!versionsLoading && versions.length === 0"
             class="card-body text-sm text-gray-400">
          暂无版本记录（模型训练后将自动保存版本文件）
        </div>

        <!-- Version list -->
        <div v-else class="divide-y divide-gray-100">
          <div v-for="v in versions" :key="v.filename"
               class="version-row" :class="v.is_active ? 'version-row-active' : ''">
            <div class="flex-1 min-w-0">
              <div class="version-name">
                {{ v.filename }}
                <span v-if="v.is_legacy" class="version-tag">旧格式</span>
              </div>
              <div class="version-meta">{{ v.size_kb }} KB · 保存于 {{ v.saved_at }}</div>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <span v-if="v.is_active" class="badge-active">当前激活</span>
              <button v-else
                      class="btn-outline py-1 px-3 text-xs"
                      :disabled="activating === v.filename"
                      @click="activateVersion(v.filename)">
                {{ activating === v.filename ? '⏳' : '激活' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Rollback shortcut -->
        <div v-if="prevVersion" class="card-body border-t border-gray-100">
          <button class="rollback-btn" :disabled="activating !== null"
                  @click="rollback">
            ↩ 回滚到上一版本：{{ prevVersion.filename }}
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../api.js'

const cfg = reactive({
  prob_threshold: 0.50,
  blacklist: [],
  threshold_overrides: {},
  stop_loss:   0.05,
  take_profit: 0.08,
})
const calibrated  = reactive({})
const lookback    = ref(20)
const newCode     = ref('')
const saving      = ref(false)
const calibrating = ref(false)
const errMsg      = ref('')
const okMsg       = ref('')

// ── 模型版本管理 ──────────────────────────────────────────────
const versions        = ref([])
const versionsLoading = ref(false)
const activating      = ref(null)    // 正在激活的 filename

const prevVersion = computed(() => {
  const activeIdx = versions.value.findIndex(v => v.is_active)
  if (activeIdx === 0 && versions.value.length > 1) return versions.value[1]
  return null
})

const thresholdGroups = [
  {
    node: 'open', label: '开盘竞价', time: '09:25',
    color: '#0284c7', badgeBg: '#e0f2fe',
    params: [
      { key: 'open_vol_ratio_min', label: '量比下限', desc: '开盘量比须超过此值',  unit: 'x',  step: 0.05 },
      { key: 'open_pct_min',       label: '涨幅下限', desc: '开盘涨幅须超过此值',  unit: '%',  step: 0.1  },
    ],
  },
  {
    node: 'amend', label: '午盘收盘前', time: '11:25',
    color: '#7c3aed', badgeBg: '#ede9fe',
    params: [
      { key: 'amend_pct_min', label: '涨幅下限', desc: '午盘有效涨幅下限',         unit: '%', step: 0.05 },
      { key: 'amend_pct_max', label: '涨幅上限', desc: '午盘过热上限，超过则不追', unit: '%', step: 0.1  },
    ],
  },
  {
    node: 'pm', label: '下午开盘', time: '13:05',
    color: '#16a34a', badgeBg: '#dcfce7',
    params: [
      { key: 'pm_pct_min', label: '涨幅下限', desc: '下午开盘涨幅须超过此值', unit: '%', step: 0.05 },
      { key: 'pm_pct_max', label: '涨幅上限', desc: '下午开盘过热上限',       unit: '%', step: 0.1  },
    ],
  },
  {
    node: 'close', label: '尾盘', time: '14:50',
    color: '#b45309', badgeBg: '#fef3c7',
    params: [
      { key: 'close_strong_pct',   label: '强势门槛', desc: '尾盘涨幅超过此值视为强势',  unit: '%', step: 0.1 },
      { key: 'close_dd_threshold', label: '回落警告', desc: '从高点回落超过此值发出警告', unit: '%', step: 0.1 },
    ],
  },
]

const probBands = [
  { label: '宽松 30~49%', min: 0.30, max: 0.50 },
  { label: '适中 50~64%', min: 0.50, max: 0.65 },
  { label: '严格 65~79%', min: 0.65, max: 0.80 },
  { label: '极严 80%+',   min: 0.80, max: 1.00 },
]

function hasOverride(key) {
  return key in cfg.threshold_overrides && cfg.threshold_overrides[key] !== null
}
function toggleOverride(key) {
  if (hasOverride(key)) { delete cfg.threshold_overrides[key] }
  else { cfg.threshold_overrides[key] = calibrated[key] ?? null }
}
function setOverride(key, val) {
  const n = parseFloat(val)
  cfg.threshold_overrides[key] = isNaN(n) ? null : n
}
function addBlacklist() {
  const c = newCode.value.trim().replace(/\D/g, '')
  if (!c) return
  if (!cfg.blacklist.includes(c)) cfg.blacklist.push(c)
  newCode.value = ''
}
function removeBlacklist(code) {
  cfg.blacklist = cfg.blacklist.filter(c => c !== code)
}

async function load() {
  try {
    const data = await api('GET', '/api/model-config')
    Object.assign(cfg, data.config)
    if (!cfg.threshold_overrides) cfg.threshold_overrides = {}
    if (!cfg.blacklist) cfg.blacklist = []
    Object.assign(calibrated, data.calibrated)
    if (calibrated.lookback_days) lookback.value = calibrated.lookback_days
  } catch (e) {
    errMsg.value = '加载配置失败：' + e.message
  }
}

async function saveAll() {
  errMsg.value = ''; okMsg.value = ''; saving.value = true
  try {
    const cleanOverrides = Object.fromEntries(
      Object.entries(cfg.threshold_overrides).filter(([, v]) => v !== null)
    )
    await api('PUT', '/api/model-config', {
      prob_threshold: cfg.prob_threshold,
      blacklist: cfg.blacklist,
      threshold_overrides: cleanOverrides,
      stop_loss:   cfg.stop_loss,
      take_profit: cfg.take_profit,
    })
    okMsg.value = '设置已保存 ✓  下次信号生成时生效'
    setTimeout(() => { okMsg.value = '' }, 4000)
  } catch (e) {
    errMsg.value = e.message
  } finally {
    saving.value = false
  }
}

async function recalibrate() {
  errMsg.value = ''; okMsg.value = ''; calibrating.value = true
  try {
    const res = await api('POST', '/api/model-config/recalibrate', { lookback: lookback.value })
    Object.assign(calibrated, res.thresholds)
    okMsg.value = `自动校准完成 ✓  基于近 ${lookback.value} 个交易日数据`
    setTimeout(() => { okMsg.value = '' }, 5000)
  } catch (e) {
    errMsg.value = '校准失败：' + e.message
  } finally {
    calibrating.value = false
  }
}

async function loadVersions() {
  versionsLoading.value = true
  try {
    const data = await api('GET', '/api/model-versions')
    versions.value = data.versions || []
  } catch (e) {
    errMsg.value = '加载模型版本失败：' + e.message
  } finally {
    versionsLoading.value = false
  }
}

async function activateVersion(filename) {
  activating.value = filename
  errMsg.value = ''; okMsg.value = ''
  try {
    await api('POST', '/api/model-versions/activate', { filename })
    await loadVersions()
    okMsg.value = `已激活：${filename}`
    setTimeout(() => { okMsg.value = '' }, 4000)
  } catch (e) {
    errMsg.value = '激活失败：' + e.message
  } finally {
    activating.value = null
  }
}

async function rollback() {
  if (prevVersion.value) await activateVersion(prevVersion.value.filename)
}

onMounted(() => { load(); loadVersions() })
</script>

<style scoped>
.model-page {
  min-height: 100%;
  background: #f8fafc;
}

/* ── Header ── */
.page-header {
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 24px;
}
.header-inner {
  max-width: 860px;
  margin: 0 auto;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}
.page-subtitle {
  font-size: 13px;
  color: #64748b;
  margin-top: 2px;
}

/* ── Content ── */
.content-wrap {
  max-width: 860px;
  margin: 0 auto;
  padding: 0 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Banners ── */
.banner {
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
}
.banner-error { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.banner-ok    { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }

/* ── Card ── */
.card {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  flex-wrap: wrap;
}
.card-body { padding: 20px; }
.section-num {
  width: 32px; height: 32px;
  border-radius: 8px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.section-title { font-size: 14px; font-weight: 600; color: #1e293b; }
.section-sub   { font-size: 12px; color: #94a3b8; margin-top: 1px; }

/* ── Prob threshold ── */
.big-value {
  font-size: 32px;
  font-weight: 700;
  color: #2563eb;
  line-height: 1;
}
.big-value-unit { font-size: 18px; font-weight: 500; color: #94a3b8; }
.range-input {
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  cursor: pointer;
}
.range-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px; height: 18px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(37,99,235,0.3);
}
.range-red::-webkit-slider-thumb  { background: #dc2626; box-shadow: 0 1px 4px rgba(220,38,38,0.3); }
.range-green::-webkit-slider-thumb { background: #059669; box-shadow: 0 1px 4px rgba(5,150,105,0.3); }
.band-active   { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
.band-inactive { background: #f8fafc; color: #94a3b8; border: 1px solid #e2e8f0; }

/* ── Divider ── */
.divider { border: none; border-top: 1px solid #f1f5f9; margin: 0; }

/* ── Blacklist chips ── */
.chip {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 10px;
  background: #f1f5f9;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #475569;
}
.chip-remove {
  color: #94a3b8;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  margin-left: 2px;
}
.chip-remove:hover { color: #dc2626; }

/* ── Inputs / buttons ── */
.input {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  outline: none;
  color: #1e293b;
  background: #fff;
  transition: border-color 0.15s;
}
.input:focus { border-color: #2563eb; }
.btn-save {
  padding: 9px 20px;
  border-radius: 9px;
  background: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-save:hover:not(:disabled) { background: #1d4ed8; }
.btn-outline {
  padding: 7px 14px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.btn-outline:hover:not(:disabled) { border-color: #94a3b8; color: #1e293b; }
.btn-danger {
  padding: 8px 14px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid #fecaca;
  transition: background 0.15s;
}
.btn-danger:hover { background: #fee2e2; }

/* ── Market stats ── */
.market-stats {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 10px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #f1f5f9;
}
.market-stat { display: flex; flex-direction: column; gap: 2px; padding: 0 16px; }
.market-stat:first-child { padding-left: 0; }
.stat-divider { width: 1px; height: 30px; background: #e2e8f0; }
.stat-label { font-size: 10px; color: #94a3b8; font-weight: 500; }
.stat-val   { font-size: 14px; font-weight: 700; color: #1e293b; }
.warn-bar {
  padding: 10px 20px;
  background: #fffbeb;
  color: #b45309;
  font-size: 12px;
  border-bottom: 1px solid #fef3c7;
}

/* ── Node groups ── */
.node-group { padding: 16px 20px; }
.node-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.node-badge {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}
.node-label { font-size: 13px; font-weight: 600; color: #1e293b; }

/* ── Param cards ── */
.param-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
}
.param-card-label { font-size: 12px; font-weight: 600; color: #334155; }
.param-card-desc  { font-size: 11px; color: #94a3b8; margin-top: 1px; }
.param-auto { font-size: 11px; color: #64748b; margin-top: 4px; }
.param-label { font-size: 13px; font-weight: 600; color: #1e293b; }
.param-desc  { font-size: 12px; color: #64748b; margin-top: 1px; }

/* ── Model version list ── */
.version-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  transition: background 0.1s;
}
.version-row:hover { background: #f8fafc; }
.version-row-active { background: #eff6ff; }
.version-row-active:hover { background: #dbeafe; }
.version-name {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
  font-family: ui-monospace, monospace;
  display: flex;
  align-items: center;
  gap: 6px;
}
.version-meta { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.version-tag {
  font-size: 10px;
  font-family: inherit;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;
}
.badge-active {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 6px;
  background: #eff6ff;
  color: #2563eb;
  border: 1px solid #bfdbfe;
}
.rollback-btn {
  width: 100%;
  padding: 9px 16px;
  border-radius: 9px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: center;
  transition: background 0.15s, border-color 0.15s;
}
.rollback-btn:hover:not(:disabled) {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #1e293b;
}
.rollback-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Toggle ── */
.toggle {
  width: 34px; height: 20px;
  border-radius: 10px;
  background: #e2e8f0;
  position: relative;
  cursor: pointer;
  transition: background 0.2s;
}
.toggle-on { background: #2563eb; }
.toggle-thumb {
  position: absolute;
  top: 3px; left: 3px;
  width: 14px; height: 14px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.toggle-on .toggle-thumb { transform: translateX(14px); }
</style>
