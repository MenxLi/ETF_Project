<template>
  <div class="flex h-full overflow-hidden" style="background:#f1f5f9">

    <!-- ── Left sidebar ─────────────────────────────────────── -->
    <aside class="w-56 flex-shrink-0 flex flex-col overflow-hidden"
           style="background:#0f172a;border-right:1px solid rgba(255,255,255,0.05)">

      <!-- Search -->
      <div class="px-3 pt-3 pb-2 flex-shrink-0"
           style="border-bottom:1px solid rgba(255,255,255,0.06)">
        <div class="text-xs font-semibold uppercase tracking-widest mb-2"
             style="color:#1e3a5f;letter-spacing:.08em">ETF 行情</div>
        <input v-model="query" placeholder="搜索代码 / 名称"
               class="w-full px-3 py-1.5 text-sm rounded-xl outline-none"
               style="background:#1e293b;border:1px solid rgba(255,255,255,0.08);color:#e2e8f0;caret-color:#3b82f6"
               @focus="e => e.target.style.borderColor='rgba(59,130,246,0.5)'"
               @blur="e => e.target.style.borderColor='rgba(255,255,255,0.08)'" />
      </div>

      <!-- ETF list (grouped) -->
      <div class="flex-1 overflow-y-auto py-1 px-2">

        <!-- ⭐ 自选 -->
        <template v-if="groups.watch.length">
          <div class="flex items-center gap-1.5 px-2 pt-3 pb-1">
            <span class="text-xs" style="color:#f59e0b">⭐</span>
            <span class="text-xs font-semibold" style="color:#78716c">自选</span>
            <span class="text-xs ml-auto" style="color:#44403c">{{ groups.watch.length }}</span>
          </div>
          <div v-for="item in groups.watch" :key="item.code"
             class="px-3 py-2 rounded-xl cursor-pointer transition-all mb-0.5"
             :style="selCode === item.code
               ? 'background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.3)'
               : 'border:1px solid transparent'"
             @click="loadEtf(item.code)">
            <div class="flex items-center justify-between">
              <div class="text-sm font-medium" style="color:#e2e8f0">{{ item.code }}</div>
              <div class="flex gap-1">
                <span class="text-xs" style="color:#f59e0b">⭐</span>
                <span v-if="item.tags.includes('hold')" class="text-xs px-1.5 py-0.5 rounded-md font-semibold leading-none" style="background:rgba(59,130,246,0.15);color:#60a5fa">持</span>
                <span v-if="item.tags.includes('signal')" class="text-xs px-1.5 py-0.5 rounded-md font-semibold leading-none" style="background:rgba(5,150,105,0.15);color:#34d399">荐</span>
              </div>
            </div>
            <div class="text-xs truncate mt-0.5" style="color:#475569">{{ item.name }}</div>
          </div>
        </template>

        <!-- 📊 持仓 -->
        <template v-if="groups.hold.length">
          <div class="flex items-center gap-1.5 px-2 pt-3 pb-1">
            <span class="text-xs" style="color:#3b82f6">📊</span>
            <span class="text-xs font-semibold" style="color:#334155">持仓</span>
            <span class="text-xs ml-auto" style="color:#475569">{{ groups.hold.length }}</span>
          </div>
          <div v-for="item in groups.hold" :key="item.code"
             class="px-3 py-2 rounded-xl cursor-pointer transition-all mb-0.5"
             :style="selCode === item.code
               ? 'background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.3)'
               : 'border:1px solid transparent'"
             @click="loadEtf(item.code)">
            <div class="flex items-center justify-between">
              <div class="text-sm font-medium" style="color:#e2e8f0">{{ item.code }}</div>
              <div class="flex gap-1">
                <span class="text-xs px-1.5 py-0.5 rounded-md font-semibold leading-none" style="background:rgba(59,130,246,0.15);color:#60a5fa">持</span>
                <span v-if="item.tags.includes('signal')" class="text-xs px-1.5 py-0.5 rounded-md font-semibold leading-none" style="background:rgba(5,150,105,0.15);color:#34d399">荐</span>
              </div>
            </div>
            <div class="text-xs truncate mt-0.5" style="color:#475569">{{ item.name }}</div>
          </div>
        </template>

        <!-- 📡 今日推荐 -->
        <template v-if="groups.signal.length">
          <div class="flex items-center gap-1.5 px-2 pt-3 pb-1">
            <span class="text-xs" style="color:#059669">📡</span>
            <span class="text-xs font-semibold" style="color:#334155">今日推荐</span>
            <span class="text-xs ml-auto" style="color:#475569">{{ groups.signal.length }}</span>
          </div>
          <div v-for="item in groups.signal" :key="item.code"
             class="px-3 py-2 rounded-xl cursor-pointer transition-all mb-0.5"
             :style="selCode === item.code
               ? 'background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.3)'
               : 'border:1px solid transparent'"
             @click="loadEtf(item.code)">
            <div class="flex items-center justify-between">
              <div class="text-sm font-medium" style="color:#e2e8f0">{{ item.code }}</div>
              <span class="text-xs px-1.5 py-0.5 rounded-md font-semibold leading-none" style="background:rgba(5,150,105,0.15);color:#34d399">荐</span>
            </div>
            <div class="text-xs truncate mt-0.5" style="color:#475569">{{ item.name }}</div>
          </div>
        </template>

        <!-- 搜索结果（有搜索词时显示扁平列表） -->
        <template v-if="query && groups.other.length">
          <div class="flex items-center gap-1.5 px-2 pt-3 pb-1">
            <span class="text-xs font-semibold" style="color:#334155">搜索结果</span>
            <span class="text-xs ml-auto" style="color:#475569">{{ groups.other.length }}</span>
          </div>
          <div v-for="item in groups.other" :key="item.code"
             class="px-3 py-2 rounded-xl cursor-pointer transition-all mb-0.5"
             :style="selCode === item.code
               ? 'background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.3)'
               : 'border:1px solid transparent'"
             @click="loadEtf(item.code)">
            <div class="text-sm font-medium" style="color:#e2e8f0">{{ item.code }}</div>
            <div class="text-xs truncate mt-0.5" style="color:#475569">{{ item.name }}</div>
          </div>
        </template>

        <!-- 分类折叠分组（无搜索词时显示） -->
        <template v-if="!query">
          <template v-for="group in categoryGroups" :key="group.name">
            <button class="w-full flex items-center gap-1 px-2 pt-3 pb-1 text-left"
                    @click="toggleCat(group.name)">
              <span class="text-xs font-semibold" style="color:#475569">{{ group.name }}</span>
              <span class="text-xs ml-auto" style="color:#334155">{{ group.items.length }}</span>
              <span class="text-xs ml-1" style="color:#475569">
                {{ collapsedCats.has(group.name) ? '▶' : '▼' }}
              </span>
            </button>
            <template v-if="!collapsedCats.has(group.name)">
              <div v-for="item in group.items" :key="item.code"
                   class="px-3 py-2 rounded-xl cursor-pointer transition-all mb-0.5"
                   :style="selCode === item.code
                     ? 'background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.3)'
                     : 'border:1px solid transparent'"
                   @click="loadEtf(item.code)">
                <div class="text-sm font-medium" style="color:#e2e8f0">{{ item.code }}</div>
                <div class="text-xs truncate mt-0.5" style="color:#475569">{{ item.name }}</div>
              </div>
            </template>
          </template>
        </template>

        <!-- 搜索无结果 -->
        <div v-if="query && !hasAnyGroup"
             class="py-8 text-center text-xs" style="color:#475569">
          未找到「{{ query }}」
        </div>
      </div>
    </aside>

    <!-- ── Right chart area ─────────────────────────────────── -->
    <div class="flex-1 overflow-y-auto p-4 space-y-3">

      <!-- Empty state -->
      <div v-if="!selCode" class="flex flex-col items-center justify-center h-full gap-3 text-gray-400">
        <div class="text-6xl">📈</div>
        <p class="text-base font-semibold text-gray-400">从左侧选择一只 ETF</p>
        <p class="text-xs text-gray-300">可点击 ⭐ 将常用 ETF 加入自选</p>
      </div>

      <!-- Loading -->
      <div v-else-if="loading" class="flex flex-col items-center justify-center h-full gap-3 text-gray-400">
        <div class="text-4xl animate-pulse">⏳</div>
        <p>加载行情数据…</p>
      </div>

      <template v-else-if="hist.length">

        <!-- ── Header card ── -->
        <div class="bg-white rounded-2xl px-5 py-4 shadow-sm">
          <div class="flex items-center gap-4 flex-wrap">
            <!-- Icon + name -->
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 rounded-xl flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
                   style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)">
                {{ selCode.slice(-2) }}
              </div>
              <div>
                <div class="flex items-center gap-2 flex-wrap">
                  <h3 class="text-lg font-bold text-gray-800">{{ etfName }}</h3>
                  <span class="text-sm font-mono text-gray-400">{{ selCode }}</span>
                  <!-- Tag badges -->
                  <span v-if="holdSet.has(selCode)"
                        class="text-xs px-1.5 py-0.5 rounded-md font-semibold"
                        style="background:#eff6ff;color:#1e3a8a">持仓</span>
                  <span v-if="signalSet.has(selCode)"
                        class="text-xs px-1.5 py-0.5 rounded-md font-semibold"
                        style="background:#f0fdf4;color:#065f46">今日推荐</span>
                </div>
                <div class="flex items-center gap-3 mt-0.5">
                  <span class="text-2xl font-bold text-gray-800">¥{{ latest?.close.toFixed(3) }}</span>
                  <span class="text-sm font-semibold px-2 py-0.5 rounded-lg"
                        :style="latestChg >= 0
                          ? 'background:#f0fdf4;color:#059669'
                          : 'background:#fff1f2;color:#ef4444'">
                    {{ latestChg >= 0 ? '▲' : '▼' }} {{ Math.abs(latestChg).toFixed(2) }}%
                  </span>
                  <span class="text-xs text-gray-400">{{ latest?.date }}</span>
                </div>
              </div>
            </div>

            <!-- Stats -->
            <div class="flex gap-5 ml-auto text-sm flex-wrap">
              <div class="text-center">
                <div class="text-xs text-gray-400 mb-0.5">区间最高</div>
                <div class="font-bold" style="color:#ef4444">¥{{ hiPrice }}</div>
              </div>
              <div class="text-center">
                <div class="text-xs text-gray-400 mb-0.5">区间最低</div>
                <div class="font-bold" style="color:#059669">¥{{ loPrice }}</div>
              </div>
              <div class="text-center">
                <div class="text-xs text-gray-400 mb-0.5">区间涨跌</div>
                <div class="font-bold" :style="rangeChg >= 0 ? 'color:#059669' : 'color:#ef4444'">
                  {{ rangeChg >= 0 ? '+' : '' }}{{ rangeChg.toFixed(2) }}%
                </div>
              </div>
              <div class="text-center">
                <div class="text-xs text-gray-400 mb-0.5">MA20</div>
                <div class="font-bold text-gray-700">{{ ma20Latest }}</div>
              </div>
              <div class="text-center">
                <div class="text-xs text-gray-400 mb-0.5">RSI(14)</div>
                <div class="font-bold"
                     :style="rsi14Latest > 70 ? 'color:#ef4444' : rsi14Latest < 30 ? 'color:#059669' : 'color:#374151'">
                  {{ rsi14Latest }}
                </div>
              </div>
              <div class="text-center">
                <div class="text-xs text-gray-400 mb-0.5">年化波动</div>
                <div class="font-bold text-gray-700">{{ annualVol }}%</div>
              </div>
            </div>

            <!-- Star (watchlist) toggle -->
            <button class="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-xl transition-all"
                    :style="watchSet.has(selCode)
                      ? 'background:#fef3c7;color:#f59e0b'
                      : 'background:#f1f5f9;color:#94a3b8'"
                    :title="watchSet.has(selCode) ? '取消自选' : '加入自选'"
                    @click="toggleWatch(selCode)">
              {{ watchSet.has(selCode) ? '⭐' : '☆' }}
            </button>
          </div>
        </div>

        <!-- ── Controls ── -->
        <div class="bg-white rounded-2xl px-5 py-3 shadow-sm flex items-center justify-between flex-wrap gap-3">
          <div class="flex gap-1">
            <button v-for="p in PERIODS" :key="p.key"
                    class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
                    :style="period === p.key
                      ? 'background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:white;box-shadow:0 2px 8px rgba(59,130,246,0.3)'
                      : 'color:#64748b;background:#f1f5f9'"
                    @click="setPeriod(p.key)">
              {{ p.label }}
            </button>
          </div>
          <div class="flex gap-2 flex-wrap">
            <button v-for="ind in INDICATORS" :key="ind.key"
                    class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                    :style="indOn[ind.key]
                      ? `background:${ind.color}18;color:${ind.color};border:1.5px solid ${ind.color}55`
                      : 'background:#f1f5f9;color:#94a3b8;border:1.5px solid #e2e8f0'"
                    @click="toggleInd(ind.key)">
              {{ ind.label }}
            </button>
          </div>
        </div>

        <!-- ── Main price chart ── -->
        <div class="bg-white rounded-2xl shadow-sm p-4">
          <div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">价格走势</div>
          <div style="height:340px;position:relative">
            <canvas ref="mainCanvas" style="width:100%;height:100%" />
          </div>
        </div>

        <!-- ── Volume chart ── -->
        <div class="bg-white rounded-2xl shadow-sm p-4">
          <div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">成交量</div>
          <div style="height:100px;position:relative">
            <canvas ref="volCanvas" style="width:100%;height:100%" />
          </div>
        </div>

        <!-- ── RSI chart ── -->
        <div v-if="indOn.rsi" class="bg-white rounded-2xl shadow-sm p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-gray-400 uppercase tracking-wide">RSI (14)</span>
            <div class="flex gap-4 text-xs">
              <span style="color:#ef4444">── 超买 70</span>
              <span style="color:#059669">── 超卖 30</span>
            </div>
          </div>
          <div style="height:100px;position:relative">
            <canvas ref="rsiCanvas" style="width:100%;height:100%" />
          </div>
        </div>

        <!-- ── Legend + guide toggle ── -->
        <div class="bg-white rounded-2xl shadow-sm px-5 py-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-gray-500">
          <div class="flex items-center gap-1.5">
            <div class="w-5 h-0.5 rounded" style="background:#3b82f6"></div><span>收盘价</span>
          </div>
          <template v-if="indOn.ma">
            <div class="flex items-center gap-1.5">
              <div class="w-5 h-0.5 rounded" style="background:#f59e0b"></div><span>MA5</span>
            </div>
            <div class="flex items-center gap-1.5">
              <div class="w-5 h-0.5 rounded" style="background:#f43f5e"></div><span>MA20</span>
            </div>
            <div class="flex items-center gap-1.5">
              <div class="w-5 h-0.5 rounded" style="background:#8b5cf6"></div><span>MA60</span>
            </div>
          </template>
          <div v-if="indOn.boll" class="flex items-center gap-1.5">
            <div class="w-5 h-3 rounded opacity-40" style="background:#94a3b8"></div><span>布林带(20,2)</span>
          </div>
          <div v-if="indOn.trend" class="flex items-center gap-1.5">
            <svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke="#0e7490" stroke-width="1.5" stroke-dasharray="4,3"/></svg>
            <span>趋势线</span>
          </div>
          <div v-if="hasBuyMarkers" class="flex items-center gap-1.5">
            <span style="color:#059669;font-size:10px">▲</span><span>您的买入点</span>
          </div>
          <div v-if="hasSellMarkers" class="flex items-center gap-1.5">
            <span style="color:#ef4444;font-size:10px">▼</span><span>您的卖出点</span>
          </div>
          <div v-if="modelSignalSet.size" class="flex items-center gap-1.5">
            <div class="w-3 h-3 rounded-full" style="background:#f59e0b;opacity:0.8"></div>
            <span>模型信号日（{{ modelSignalSet.size }}次）</span>
          </div>
          <!-- Guide toggle -->
          <button class="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                  :style="showGuide
                    ? 'background:#eff6ff;color:#1e3a8a;border:1px solid #bfdbfe'
                    : 'background:#f1f5f9;color:#64748b;border:1px solid #e2e8f0'"
                  @click="showGuide = !showGuide">
            <span>📖</span>
            <span>{{ showGuide ? '收起说明' : '指标说明' }}</span>
          </button>
        </div>

        <!-- ── Indicator guide panel ── -->
        <div v-if="showGuide" class="bg-white rounded-2xl shadow-sm overflow-hidden">
          <!-- Header -->
          <div class="px-6 py-4" style="background:linear-gradient(135deg,#0f172a,#1e3a8a)">
            <h3 class="text-white font-bold text-base">📖 图表指标说明</h3>
            <p class="text-blue-300 text-xs mt-1">了解每个指标的含义，帮助你更好地判断行情走势</p>
          </div>

          <div class="p-5 grid grid-cols-2 gap-4">

            <!-- MA均线 -->
            <div class="rounded-xl p-4" style="background:#fafbff;border:1px solid #f1f5f9">
              <div class="flex items-center gap-2 mb-2">
                <div class="flex gap-1">
                  <div class="w-3 h-3 rounded-full" style="background:#f59e0b"></div>
                  <div class="w-3 h-3 rounded-full" style="background:#f43f5e"></div>
                  <div class="w-3 h-3 rounded-full" style="background:#8b5cf6"></div>
                </div>
                <span class="font-bold text-gray-800 text-sm">移动均线 MA5 / MA20 / MA60</span>
              </div>
              <p class="text-xs text-gray-600 leading-relaxed mb-2">
                均线是过去 N 个交易日收盘价的平均值，代表市场的"平均持仓成本"。MA5 反映近一周趋势，MA20 反映近一个月，MA60 反映近三个月的中期走向。
              </p>
              <div class="space-y-1 text-xs">
                <div class="flex gap-2"><span class="text-green-600 font-semibold flex-shrink-0">利多 ▶</span><span class="text-gray-600">价格在均线上方运行，说明持仓者整体盈利，趋势偏强</span></div>
                <div class="flex gap-2"><span class="text-red-500 font-semibold flex-shrink-0">利空 ▶</span><span class="text-gray-600">价格跌破均线，特别是跌破 MA60，往往是趋势走弱的信号</span></div>
                <div class="flex gap-2"><span class="text-blue-600 font-semibold flex-shrink-0">金叉 ▶</span><span class="text-gray-600">短期均线从下方穿越长期均线向上，是经典买入参考</span></div>
                <div class="flex gap-2"><span class="text-gray-500 font-semibold flex-shrink-0">死叉 ▶</span><span class="text-gray-600">短期均线从上方跌破长期均线，是卖出或减仓的参考</span></div>
              </div>
            </div>

            <!-- 布林带 -->
            <div class="rounded-xl p-4" style="background:#fafbff;border:1px solid #f1f5f9">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-5 h-4 rounded opacity-50" style="background:#94a3b8"></div>
                <span class="font-bold text-gray-800 text-sm">布林带 Bollinger Bands (20, 2)</span>
              </div>
              <p class="text-xs text-gray-600 leading-relaxed mb-2">
                布林带由三条线组成：中轨是 20 日均线，上下轨是在中轨基础上各加减 2 倍标准差。它构成了价格在统计意义上的"合理波动通道"，约 95% 的时间价格会在带内运行。
              </p>
              <div class="space-y-1 text-xs">
                <div class="flex gap-2"><span class="text-green-600 font-semibold flex-shrink-0">下轨附近 ▶</span><span class="text-gray-600">价格处于历史相对低位，超跌反弹概率较高，可关注做多机会</span></div>
                <div class="flex gap-2"><span class="text-red-500 font-semibold flex-shrink-0">上轨附近 ▶</span><span class="text-gray-600">价格处于历史相对高位，注意追高风险，可能出现回调</span></div>
                <div class="flex gap-2"><span class="text-amber-600 font-semibold flex-shrink-0">带宽收窄 ▶</span><span class="text-gray-600">价格长期盘整，波动率低，往往预示即将发生方向性突破</span></div>
              </div>
            </div>

            <!-- 趋势线 -->
            <div class="rounded-xl p-4" style="background:#fafbff;border:1px solid #f1f5f9">
              <div class="flex items-center gap-2 mb-2">
                <svg width="20" height="12"><line x1="0" y1="6" x2="20" y2="6" stroke="#0e7490" stroke-width="2" stroke-dasharray="5,3"/></svg>
                <span class="font-bold text-gray-800 text-sm">线性回归趋势线</span>
              </div>
              <p class="text-xs text-gray-600 leading-relaxed mb-2">
                用所选时间段内所有收盘价做线性回归，得到一条最能代表整体价格方向的直线。它过滤了日常噪音，直接显示"大方向"。
              </p>
              <div class="space-y-1 text-xs">
                <div class="flex gap-2"><span class="text-green-600 font-semibold flex-shrink-0">向上倾斜 ▶</span><span class="text-gray-600">所选周期内整体处于上升趋势</span></div>
                <div class="flex gap-2"><span class="text-red-500 font-semibold flex-shrink-0">向下倾斜 ▶</span><span class="text-gray-600">所选周期内整体处于下降趋势，谨慎操作</span></div>
                <div class="flex gap-2"><span class="text-amber-600 font-semibold flex-shrink-0">价格偏离 ▶</span><span class="text-gray-600">价格大幅偏离趋势线时，往往会向趋势线方向回归（均值回归）</span></div>
                <div class="flex gap-2"><span class="text-blue-600 font-semibold flex-shrink-0">注意 ▶</span><span class="text-gray-600">切换时间段后趋势线会重新计算，短周期和长周期得出的方向可能不同</span></div>
              </div>
            </div>

            <!-- RSI -->
            <div class="rounded-xl p-4" style="background:#fafbff;border:1px solid #f1f5f9">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-4 h-4 rounded-full" style="background:#7c3aed"></div>
                <span class="font-bold text-gray-800 text-sm">相对强弱指数 RSI (14)</span>
              </div>
              <p class="text-xs text-gray-600 leading-relaxed mb-2">
                RSI 衡量过去 14 个交易日内"涨的力量"和"跌的力量"的对比，数值在 0 到 100 之间。它回答的问题是：这只 ETF 最近涨/跌得是否过于极端？
              </p>
              <div class="space-y-1 text-xs">
                <div class="flex gap-2">
                  <span class="font-bold flex-shrink-0" style="color:#ef4444">RSI &gt; 70 ▶</span>
                  <span class="text-gray-600">超买区，短期涨幅过猛，注意可能出现调整，不宜追高</span>
                </div>
                <div class="flex gap-2">
                  <span class="font-bold flex-shrink-0" style="color:#059669">RSI &lt; 30 ▶</span>
                  <span class="text-gray-600">超卖区，短期跌幅过大，往往出现技术性反弹，可关注做多机会</span>
                </div>
                <div class="flex gap-2">
                  <span class="text-gray-500 font-semibold flex-shrink-0">RSI 40–60 ▶</span>
                  <span class="text-gray-600">多空相对平衡，趋势不明显，观望为主</span>
                </div>
              </div>
            </div>

            <!-- 成交量 -->
            <div class="rounded-xl p-4" style="background:#fafbff;border:1px solid #f1f5f9">
              <div class="flex items-center gap-2 mb-2">
                <div class="flex gap-0.5 items-end h-4">
                  <div class="w-2 rounded-sm" style="height:60%;background:rgba(59,130,246,0.6)"></div>
                  <div class="w-2 rounded-sm" style="height:100%;background:rgba(59,130,246,0.6)"></div>
                  <div class="w-2 rounded-sm" style="height:40%;background:rgba(239,68,68,0.6)"></div>
                  <div class="w-2 rounded-sm" style="height:80%;background:rgba(59,130,246,0.6)"></div>
                </div>
                <span class="font-bold text-gray-800 text-sm">成交量（蓝涨 / 红跌）</span>
              </div>
              <p class="text-xs text-gray-600 leading-relaxed mb-2">
                成交量代表当天实际买卖了多少份额，是"市场参与度"的直接体现。蓝色柱为当日收涨，红色柱为收跌。
              </p>
              <div class="space-y-1 text-xs">
                <div class="flex gap-2"><span class="text-green-600 font-semibold flex-shrink-0">量价齐升 ▶</span><span class="text-gray-600">价格上涨同时成交量放大，资金积极跟进，是最健康的上涨形态</span></div>
                <div class="flex gap-2"><span class="text-amber-600 font-semibold flex-shrink-0">价涨量缩 ▶</span><span class="text-gray-600">价格上涨但成交量萎缩，上涨动力不足，小心无量虚涨</span></div>
                <div class="flex gap-2"><span class="text-red-500 font-semibold flex-shrink-0">价跌量增 ▶</span><span class="text-gray-600">价格下跌同时成交量放大，说明抛压较重，卖盘积极</span></div>
                <div class="flex gap-2"><span class="text-gray-500 font-semibold flex-shrink-0">地量 ▶</span><span class="text-gray-600">成交量极度萎缩，市场高度观望，往往是阶段性底部或变盘前的信号</span></div>
              </div>
            </div>

            <!-- 个人标记 + 模型信号 -->
            <div class="rounded-xl p-4" style="background:#fafbff;border:1px solid #f1f5f9">
              <div class="flex items-center gap-3 mb-2">
                <span class="font-bold text-gray-800 text-sm">个人标记 &amp; 模型信号</span>
              </div>
              <p class="text-xs text-gray-600 leading-relaxed mb-3">
                图表上叠加了你的历史操作记录和模型的历史信号，方便你复盘过往决策的效果。
              </p>
              <div class="space-y-2 text-xs">
                <div class="flex gap-2 items-start">
                  <span class="flex-shrink-0 font-bold mt-0.5" style="color:#059669">▲ 买入点</span>
                  <span class="text-gray-600">绿色三角显示在您记录的买入日期对应的价格下方。可以对照均线和布林带，判断当时的买入时机是否合理。</span>
                </div>
                <div class="flex gap-2 items-start">
                  <span class="flex-shrink-0 font-bold mt-0.5" style="color:#ef4444">▼ 卖出点</span>
                  <span class="text-gray-600">红色三角显示在您记录的卖出日期对应的价格上方，方便评估卖出时机与市场走势的关系。</span>
                </div>
                <div class="flex gap-2 items-start">
                  <span class="flex-shrink-0 flex items-center gap-1 mt-0.5"><div class="w-3 h-3 rounded-full flex-shrink-0" style="background:#f59e0b"></div><span class="font-bold" style="color:#d97706">模型信号</span></span>
                  <span class="text-gray-600">橙色圆点标记模型历史上对该ETF发出做多信号的日期，可以结合后续走势评估模型准确率。</span>
                </div>
              </div>
            </div>

          </div>

          <!-- Footer tip -->
          <div class="mx-5 mb-5 px-4 py-3 rounded-xl text-xs leading-relaxed"
               style="background:#fffbeb;border:1px solid #fde68a;color:#92400e">
            <strong>💡 实战小提示：</strong>
            单一指标容易出现误判，建议将多个指标结合使用。例如：RSI 进入超卖区 + 价格触碰布林带下轨 + 成交量放量，三者共振时做多胜率往往更高。模型信号也是基于多指标综合判断的结果。
          </div>
        </div>

      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import Chart from 'chart.js/auto'
import { api } from '../api.js'
import { store } from '../store.js'

// ── Constants ───────────────────────────────────────────────────
const PERIODS = [
  { key: '1M', label: '1月', days: 22 },
  { key: '3M', label: '3月', days: 66 },
  { key: '6M', label: '6月', days: 130 },
  { key: '1Y', label: '1年', days: 252 },
  { key: 'ALL', label: '全部', days: 99999 },
]
const INDICATORS = [
  { key: 'ma',    label: 'MA均线', color: '#f59e0b' },
  { key: 'boll',  label: '布林带', color: '#64748b' },
  { key: 'trend', label: '趋势线', color: '#0e7490' },
  { key: 'rsi',   label: 'RSI',   color: '#7c3aed' },
]

// ── State ───────────────────────────────────────────────────────
const query    = ref('')
const selCode  = ref('')
const hist     = ref([])
const loading  = ref(false)
const period    = ref('3M')
const indOn     = ref({ ma: true, boll: true, trend: false, rsi: false })
const showGuide = ref(false)

// Enrichment data
const watchlist     = ref([])    // user's watchlist codes
const positions     = ref([])    // user's current portfolio positions
const todaySignals  = ref([])    // today's recommended ETF codes
const userTxs       = ref([])    // all transactions for current user
const modelSignals  = ref([])    // [{date, prob_up, close}]

// Canvas refs
const mainCanvas = ref(null)
const volCanvas  = ref(null)
const rsiCanvas  = ref(null)
let mainChart = null, volChart = null, rsiChart = null

// ── Derived sets for fast lookup ────────────────────────────────
const watchSet  = computed(() => new Set(watchlist.value))
const holdSet   = computed(() => new Set(positions.value.map(p => p.code)))
const signalSet = computed(() => new Set(todaySignals.value))

// ── Grouped sidebar items ────────────────────────────────────────
const groups = computed(() => {
  const q   = query.value.toLowerCase().trim()
  const all = Object.entries(store.etfList || {})
  const ws  = watchSet.value
  const hs  = holdSet.value
  const ss  = signalSet.value

  const matches = q
    ? ([code, name]) => code.includes(q) || name.toLowerCase().includes(q)
    : () => true

  // Tags helper
  const tags = (code) => {
    const t = []
    if (ws.has(code)) t.push('watch')
    if (hs.has(code)) t.push('hold')
    if (ss.has(code)) t.push('signal')
    return t
  }

  // ⭐ Watchlist: preserves user's ordering
  const watch = watchlist.value
    .filter(code => store.etfList[code] && matches([code, store.etfList[code]]))
    .map(code => ({ code, name: store.etfList[code], tags: tags(code) }))

  // 📊 Holdings (not already in watchlist)
  const hold = positions.value
    .filter(p => store.etfList[p.code] && !ws.has(p.code) && matches([p.code, store.etfList[p.code]]))
    .map(p => ({ code: p.code, name: store.etfList[p.code], tags: tags(p.code) }))

  // 📡 Signals (not in watchlist or holdings)
  const signal = [...ss]
    .filter(code => store.etfList[code] && !ws.has(code) && !hs.has(code) && matches([code, store.etfList[code]]))
    .map(code => ({ code, name: store.etfList[code], tags: tags(code) }))

  // 搜索时显示扁平搜索结果；非搜索时 other 为空，由 categoryGroups 接管
  const exclude = new Set([...ws, ...hs, ...ss])
  const other = q
    ? all
        .filter(([code, name]) => !exclude.has(code) && matches([code, name]))
        .slice(0, 50)
        .map(([code, name]) => ({ code, name, tags: [] }))
    : []

  return { watch, hold, signal, other }
})

// ── 分类分组（非搜索模式）───────────────────────────────────────
const CAT_ORDER = ['宽基', '海外', '金融', '医疗', '科技', '能源', '消费', '周期', '地产', '债券', '商品']
const collapsedCats = ref(new Set())

function toggleCat(cat) {
  const s = new Set(collapsedCats.value)
  s.has(cat) ? s.delete(cat) : s.add(cat)
  collapsedCats.value = s
}

const categoryGroups = computed(() => {
  if (query.value) return []
  const exclude = new Set([...watchSet.value, ...holdSet.value, ...signalSet.value])
  const map = {}
  for (const [code, name] of Object.entries(store.etfList || {})) {
    if (exclude.has(code)) continue
    const cat = store.etfCategories?.[code] ?? '其他'
    if (!map[cat]) map[cat] = []
    map[cat].push({ code, name })
  }
  return [...CAT_ORDER, '其他'].filter(c => map[c]).map(c => ({ name: c, items: map[c] }))
})

const hasAnyGroup = computed(() =>
  groups.value.watch.length || groups.value.hold.length ||
  groups.value.signal.length || groups.value.other.length ||
  categoryGroups.value.length
)

// ── ETF info ────────────────────────────────────────────────────
const etfName = computed(() => store.etfList?.[selCode.value] ?? selCode.value)

// ── Period slice ─────────────────────────────────────────────────
const displayHist = computed(() => {
  const days = PERIODS.find(p => p.key === period.value)?.days ?? 66
  return hist.value.slice(-days)
})

// ── Raw arrays ──────────────────────────────────────────────────
const labels  = computed(() => displayHist.value.map(d => d.date))
const closes  = computed(() => displayHist.value.map(d => d.close))
const volumes = computed(() => displayHist.value.map(d => d.volume))

// ── Header stats ────────────────────────────────────────────────
const latest    = computed(() => displayHist.value.at(-1) ?? null)
const latestChg = computed(() =>
  displayHist.value.length > 1
    ? (displayHist.value.at(-1).close - displayHist.value.at(-2).close) / displayHist.value.at(-2).close * 100
    : 0
)
const hiPrice  = computed(() => closes.value.length ? Math.max(...closes.value).toFixed(3) : '—')
const loPrice  = computed(() => closes.value.length ? Math.min(...closes.value).toFixed(3) : '—')
const rangeChg = computed(() => closes.value.length > 1
  ? (closes.value.at(-1) - closes.value[0]) / closes.value[0] * 100 : 0)

// ── Technical indicators ─────────────────────────────────────────
function calcMA(arr, n) {
  return arr.map((_, i) =>
    i < n - 1 ? null : arr.slice(i - n + 1, i + 1).reduce((s, v) => s + v, 0) / n
  )
}
function calcBoll(arr, n = 20, k = 2) {
  return arr.map((_, i) => {
    if (i < n - 1) return { upper: null, lower: null }
    const sl = arr.slice(i - n + 1, i + 1)
    const mid = sl.reduce((s, v) => s + v, 0) / n
    const std = Math.sqrt(sl.reduce((s, v) => s + (v - mid) ** 2, 0) / n)
    return { upper: +(mid + k * std).toFixed(4), lower: +(mid - k * std).toFixed(4) }
  })
}
function calcRSI(arr, n = 14) {
  return arr.map((_, i) => {
    if (i < n) return null
    const ch = arr.slice(i - n, i + 1).map((v, j, a) => j === 0 ? 0 : v - a[j - 1])
    const gains  = ch.filter(v => v > 0).reduce((s, v) => s + v, 0) / n
    const losses = ch.filter(v => v < 0).map(v => -v).reduce((s, v) => s + v, 0) / n
    return losses === 0 ? 100 : +(100 - 100 / (1 + gains / losses)).toFixed(1)
  })
}
function calcTrend(arr) {
  const n = arr.length
  if (n < 2) return arr.slice()
  let sx = 0, sy = 0, sxy = 0, sx2 = 0
  arr.forEach((v, i) => { sx += i; sy += v; sxy += i * v; sx2 += i * i })
  const slope = (n * sxy - sx * sy) / (n * sx2 - sx * sx)
  const b = (sy - slope * sx) / n
  return arr.map((_, i) => +(b + slope * i).toFixed(4))
}

const ma5   = computed(() => calcMA(closes.value, 5))
const ma20  = computed(() => calcMA(closes.value, 20))
const ma60  = computed(() => calcMA(closes.value, 60))
const boll  = computed(() => calcBoll(closes.value, 20, 2))
const rsi14 = computed(() => calcRSI(closes.value, 14))
const trend = computed(() => calcTrend(closes.value))

const ma20Latest = computed(() => {
  const v = [...ma20.value].reverse().find(x => x !== null)
  return v != null ? v.toFixed(3) : '—'
})
const rsi14Latest = computed(() => {
  const v = [...rsi14.value].reverse().find(x => x !== null)
  return v != null ? +v : '—'
})
const annualVol = computed(() => {
  if (closes.value.length < 5) return '—'
  const ret = closes.value.slice(1).map((c, i) => Math.log(c / closes.value[i]))
  const mean = ret.reduce((s, v) => s + v, 0) / ret.length
  const variance = ret.reduce((s, v) => s + (v - mean) ** 2, 0) / ret.length
  return (Math.sqrt(variance * 252) * 100).toFixed(1)
})

// ── User transaction markers ─────────────────────────────────────
// Note: transaction fields are action ("buy"/"sell") and date
const userBuyDates = computed(() => new Set(
  userTxs.value
    .filter(t => t.etf_code === selCode.value && t.action === 'buy')
    .map(t => t.date)
))
const userSellDates = computed(() => new Set(
  userTxs.value
    .filter(t => t.etf_code === selCode.value && t.action === 'sell')
    .map(t => t.date)
))
const hasBuyMarkers  = computed(() => labels.value.some(d => userBuyDates.value.has(d)))
const hasSellMarkers = computed(() => labels.value.some(d => userSellDates.value.has(d)))

// ── Model signal markers ─────────────────────────────────────────
const modelSignalSet = computed(() => new Set(modelSignals.value.map(x => x.date)))

// ── Watchlist toggle ────────────────────────────────────────────
async function toggleWatch(code) {
  const current = [...watchlist.value]
  let next
  if (watchSet.value.has(code)) {
    next = current.filter(c => c !== code)
  } else {
    next = [code, ...current]  // prepend so it appears first
  }
  watchlist.value = next
  try { await api('PUT', '/api/watchlist', next) } catch {}
}

// ── Load ETF data ────────────────────────────────────────────────
async function loadEtf(code) {
  if (selCode.value === code) return
  selCode.value = code
  loading.value = true
  hist.value    = []
  userTxs.value = []
  modelSignals.value = []
  destroyCharts()
  try {
    const uid = store.currentUser?.id ?? ''
    const [h, tx, sig] = await Promise.allSettled([
      api('GET', `/api/etf-history/${code}`),
      api('GET', `/api/transactions/${uid}`),
      api('GET', `/api/signal-history/etf/${code}`),
    ])
    if (h.status === 'fulfilled')   hist.value = h.value ?? []
    if (tx.status === 'fulfilled')  userTxs.value = tx.value ?? []
    if (sig.status === 'fulfilled') modelSignals.value = sig.value ?? []
  } finally {
    loading.value = false
  }
  await nextTick()
  redraw()
}

// ── Initial load ─────────────────────────────────────────────────
async function initSidebarData() {
  const uid = store.currentUser?.id ?? ''
  const [wl, pf, sigs] = await Promise.allSettled([
    api('GET', '/api/watchlist'),
    api('GET', `/api/portfolio/${uid}`),
    api('GET', '/api/signals'),
  ])
  if (wl.status  === 'fulfilled') watchlist.value    = wl.value ?? []
  if (pf.status  === 'fulfilled') positions.value    = pf.value?.positions ?? []
  if (sigs.status === 'fulfilled') todaySignals.value = (sigs.value?.signals ?? []).map(s => s.code)
}
initSidebarData()

// ── Period / indicator controls ──────────────────────────────────
function setPeriod(key) { period.value = key; redraw() }
function toggleInd(key) { indOn.value = { ...indOn.value, [key]: !indOn.value[key] }; redraw() }

// ── Charts ───────────────────────────────────────────────────────
function destroyCharts() {
  if (mainChart) { mainChart.destroy(); mainChart = null }
  if (volChart)  { volChart.destroy();  volChart  = null }
  if (rsiChart)  { rsiChart.destroy();  rsiChart  = null }
}

async function redraw() {
  await nextTick()
  destroyCharts()
  if (!displayHist.value.length) return
  drawMain()
  drawVol()
  if (indOn.value.rsi) { await nextTick(); drawRsi() }
}

function drawMain() {
  if (!mainCanvas.value) return
  const lbs  = labels.value
  const cl   = closes.value
  const on   = indOn.value
  const cm   = Object.fromEntries(displayHist.value.map(d => [d.date, d.close]))
  const range = (Math.max(...cl) - Math.min(...cl)) || 0.01
  const ds   = []

  // Bollinger fill
  if (on.boll) {
    const bo = boll.value
    ds.push({
      label: '布林上轨', data: bo.map(b => b.upper),
      borderColor: 'rgba(148,163,184,0.45)', borderWidth: 1,
      pointRadius: 0, fill: '+1', backgroundColor: 'rgba(148,163,184,0.07)',
      tension: 0.2, spanGaps: false,
    })
    ds.push({
      label: '布林下轨', data: bo.map(b => b.lower),
      borderColor: 'rgba(148,163,184,0.45)', borderWidth: 1,
      pointRadius: 0, fill: false, tension: 0.2, spanGaps: false,
    })
  }

  // Trend line
  if (on.trend) {
    ds.push({
      label: '趋势线', data: trend.value,
      borderColor: '#0e7490', borderWidth: 1.5, borderDash: [6, 3],
      pointRadius: 0, fill: false, tension: 0,
    })
  }

  // MA lines
  if (on.ma) {
    ds.push({ label: 'MA60', data: ma60.value, borderColor: '#8b5cf6', borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1, spanGaps: false })
    ds.push({ label: 'MA20', data: ma20.value, borderColor: '#f43f5e', borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1, spanGaps: false })
    ds.push({ label: 'MA5',  data: ma5.value,  borderColor: '#f59e0b', borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1, spanGaps: false })
  }

  // Close price (main)
  ds.push({
    label: '收盘价', data: cl,
    borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.06)',
    borderWidth: 2, pointRadius: 0, fill: true, tension: 0.15, order: 1,
  })

  // Model signal markers
  const sigData = lbs.map(d => modelSignalSet.value.has(d) ? (cm[d] ?? null) + range * 0.025 : null)
  if (sigData.some(v => v !== null)) {
    ds.push({
      label: '模型信号', data: sigData,
      showLine: false, spanGaps: false,
      pointStyle: 'circle',
      pointRadius: lbs.map(d => modelSignalSet.value.has(d) ? 5 : 0),
      pointBackgroundColor: 'rgba(245,158,11,0.85)',
      pointBorderColor: '#fff', pointBorderWidth: 1.5, order: 0,
    })
  }

  // Buy markers (triangle up, below price)
  const buyData = lbs.map(d => userBuyDates.value.has(d) ? (cm[d] ?? null) - range * 0.03 : null)
  if (buyData.some(v => v !== null)) {
    ds.push({
      label: '您的买入', data: buyData,
      showLine: false, spanGaps: false,
      pointStyle: 'triangle',
      pointRadius: lbs.map(d => userBuyDates.value.has(d) ? 9 : 0),
      pointRotation: 0,
      pointBackgroundColor: '#059669', pointBorderColor: '#fff', pointBorderWidth: 1.5, order: 0,
    })
  }

  // Sell markers (triangle down, above price)
  const sellData = lbs.map(d => userSellDates.value.has(d) ? (cm[d] ?? null) + range * 0.03 : null)
  if (sellData.some(v => v !== null)) {
    ds.push({
      label: '您的卖出', data: sellData,
      showLine: false, spanGaps: false,
      pointStyle: 'triangle',
      pointRadius: lbs.map(d => userSellDates.value.has(d) ? 9 : 0),
      pointRotation: 180,
      pointBackgroundColor: '#ef4444', pointBorderColor: '#fff', pointBorderWidth: 1.5, order: 0,
    })
  }

  mainChart = new Chart(mainCanvas.value, {
    type: 'line',
    data: { labels: lbs, datasets: ds },
    options: {
      responsive: true, maintainAspectRatio: false, animation: { duration: 300 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15,23,42,0.92)', titleColor: '#94a3b8',
          bodyColor: '#e2e8f0', borderColor: 'rgba(59,130,246,0.3)', borderWidth: 1, padding: 10,
          callbacks: {
            title: items => items[0]?.label ?? '',
            label: item => item.raw == null ? null : ` ${item.dataset.label}：¥${Number(item.raw).toFixed(4)}`,
          },
        },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 8, font: { size: 11 }, color: '#94a3b8' }, grid: { color: 'rgba(226,232,240,0.4)' } },
        y: { ticks: { font: { size: 11 }, color: '#94a3b8', callback: v => '¥' + v.toFixed(2) }, grid: { color: 'rgba(226,232,240,0.4)' } },
      },
    },
  })
}

function drawVol() {
  if (!volCanvas.value) return
  const lbs = labels.value
  const cl  = closes.value
  volChart = new Chart(volCanvas.value, {
    type: 'bar',
    data: {
      labels: lbs,
      datasets: [{
        label: '成交量',
        data: volumes.value,
        backgroundColor: lbs.map((_, i) =>
          i === 0 || cl[i] >= cl[i - 1] ? 'rgba(59,130,246,0.5)' : 'rgba(239,68,68,0.5)'
        ),
        borderWidth: 0, barPercentage: 0.85,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: { duration: 0 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15,23,42,0.92)', titleColor: '#94a3b8', bodyColor: '#e2e8f0',
          callbacks: {
            label: item => {
              const v = item.raw
              return v >= 1e8 ? ` 成交量：${(v / 1e8).toFixed(2)} 亿手` : ` 成交量：${(v / 1e4).toFixed(0)} 万手`
            },
          },
        },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 8, font: { size: 10 }, color: '#94a3b8' }, grid: { display: false } },
        y: {
          ticks: { font: { size: 10 }, color: '#94a3b8', maxTicksLimit: 4, callback: v => v >= 1e8 ? (v / 1e8).toFixed(1) + '亿' : (v / 1e4).toFixed(0) + '万' },
          grid: { color: 'rgba(226,232,240,0.4)' },
        },
      },
    },
  })
}

function drawRsi() {
  if (!rsiCanvas.value) return
  const lbs = labels.value
  rsiChart = new Chart(rsiCanvas.value, {
    type: 'line',
    data: {
      labels: lbs,
      datasets: [
        { label: '超买线', data: lbs.map(() => 70), borderColor: 'rgba(239,68,68,0.45)', borderWidth: 1, borderDash: [4, 3], pointRadius: 0, fill: false },
        { label: '中轴',   data: lbs.map(() => 50), borderColor: 'rgba(148,163,184,0.3)', borderWidth: 1, borderDash: [4, 3], pointRadius: 0, fill: false },
        { label: '超卖线', data: lbs.map(() => 30), borderColor: 'rgba(5,150,105,0.45)',  borderWidth: 1, borderDash: [4, 3], pointRadius: 0, fill: false },
        {
          label: 'RSI(14)', data: rsi14.value,
          borderColor: '#7c3aed', backgroundColor: 'rgba(124,58,237,0.08)',
          borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.2, spanGaps: false,
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: { duration: 0 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15,23,42,0.92)', titleColor: '#94a3b8', bodyColor: '#e2e8f0',
          filter: item => item.dataset.label === 'RSI(14)',
          callbacks: { label: item => ` RSI：${item.raw}` },
        },
      },
      scales: {
        x: { ticks: { maxTicksLimit: 8, font: { size: 10 }, color: '#94a3b8' }, grid: { display: false } },
        y: { min: 0, max: 100, ticks: { maxTicksLimit: 5, font: { size: 10 }, color: '#94a3b8' }, grid: { color: 'rgba(226,232,240,0.4)' } },
      },
    },
  })
}

onBeforeUnmount(destroyCharts)
</script>
