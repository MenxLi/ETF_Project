<template>
  <div class="space-y-6 text-gray-700">

    <!-- Intro -->
    <div class="rounded-2xl p-5" style="background:linear-gradient(135deg,#0f172a,#1e3a8a)">
      <h2 class="text-white text-lg font-bold mb-2">📖 系统是怎么给你推荐 ETF 的？</h2>
      <p class="text-blue-200 text-sm leading-relaxed">
        这个系统每个交易日收盘后，会自动分析所有 ETF 的历史价格和成交量，用机器学习模型预测第二天哪些 ETF
        更可能上涨，再结合你的持仓情况给出个性化建议。下面用最通俗的语言解释每一步。
      </p>
    </div>

    <!-- Step 1 -->
    <div>
      <h3 class="flex items-center gap-2 text-base font-bold text-gray-800 mb-3">
        <span>📊</span><span>第一步：收集数据</span>
      </h3>
      <p class="text-sm leading-relaxed">
        每天收盘后，系统从 <strong>Yahoo Finance</strong> 自动拉取所有监控 ETF 的日线行情，
        包括开盘价、最高价、最低价、收盘价和成交量（简称 OHLCV）。
        这些数据会累积保存，最远可追溯 3 年，是后续一切分析的原材料。
      </p>
    </div>

    <!-- Step 2 -->
    <div>
      <h3 class="flex items-center gap-2 text-base font-bold text-gray-800 mb-3">
        <span>🧮</span><span>第二步：计算技术指标（特征工程）</span>
      </h3>
      <p class="text-sm leading-relaxed mb-3">
        原始的价格数字对机器来说意义不大，就像你看一堆体温数字，不如直接告诉你"发烧了"更直观。
        系统会把价格变成 <strong>20 多个有意义的技术指标</strong>，共分 5 类：
      </p>
      <div class="grid grid-cols-1 gap-3">
        <div v-for="feat in features" :key="feat.title"
             class="flex gap-3 p-3 rounded-xl" style="background:#f8fafc;border:1px solid #f1f5f9">
          <div class="w-1 rounded-full flex-shrink-0" :style="{background: feat.color}"></div>
          <div>
            <div class="text-sm font-semibold mb-0.5" :style="{color: feat.color}">{{ feat.title }}</div>
            <div class="text-xs text-gray-500 mb-1">包含：{{ feat.items }}</div>
            <div class="text-xs text-gray-600 leading-relaxed">{{ feat.desc }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 3 -->
    <div>
      <h3 class="flex items-center gap-2 text-base font-bold text-gray-800 mb-3">
        <span>🤖</span><span>第三步：机器学习模型预测</span>
      </h3>
      <p class="text-sm leading-relaxed mb-3">
        系统用 <strong>随机森林 / 梯度提升（Gradient Boosting）</strong> 这类"集成学习"模型，
        对每只 ETF 做 <strong>三分类预测</strong>：
      </p>
      <div class="flex gap-3 mb-3">
        <div class="flex-1 p-3 rounded-xl text-center text-sm font-medium"
             style="background:#f0fdf4;border:1px solid #bbf7d0;color:#14532d">
          ▲ 未来 N 日涨幅超过 2%<br>
          <span class="text-xs font-normal text-green-700">做多信号</span>
        </div>
        <div class="flex-1 p-3 rounded-xl text-center text-sm font-medium"
             style="background:#f1f5f9;border:1px solid #e2e8f0;color:#475569">
          ↔ 涨跌幅在 ±2% 内<br>
          <span class="text-xs font-normal text-gray-500">震荡 / 观望</span>
        </div>
        <div class="flex-1 p-3 rounded-xl text-center text-sm font-medium"
             style="background:#fff1f2;border:1px solid #fecdd3;color:#9f1239">
          ▼ 未来 N 日跌幅超过 2%<br>
          <span class="text-xs font-normal text-red-700">做空 / 回避</span>
        </div>
      </div>
      <p class="text-sm leading-relaxed">
        模型用过去 3 年的历史数据训练，每次预测都输出 <strong>三个概率值</strong>（三者之和 = 100%）。
        只有当"做多概率"超过你在模型调参页面设定的门槛（默认 50%），这只 ETF 才会出现在推荐列表里。
        门槛越高，推荐越少但越精准；门槛越低，推荐更多但误报也更多。
      </p>
    </div>

    <!-- Step 4 -->
    <div>
      <h3 class="flex items-center gap-2 text-base font-bold text-gray-800 mb-3">
        <span>⏰</span><span>第四步：盘中四节点二次确认</span>
      </h3>
      <p class="text-sm leading-relaxed mb-3">
        收盘后的模型信号是基于历史规律的"预判"，第二天需要在盘中进一步验证。
        系统会在 <strong>四个关键时间点</strong> 检查实时行情，只有实盘也符合预期才推送确认信号：
      </p>
      <div class="space-y-2">
        <div v-for="node in nodes" :key="node.time"
             class="flex items-start gap-3 p-3 rounded-xl" style="background:#f8fafc">
          <span class="text-xs font-bold px-2 py-1 rounded-lg text-white flex-shrink-0"
                :style="{background: node.color}">{{ node.time }}</span>
          <div>
            <div class="text-sm font-semibold text-gray-700">{{ node.label }}</div>
            <div class="text-xs text-gray-500 mt-0.5 leading-relaxed">{{ node.desc }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 5 -->
    <div>
      <h3 class="flex items-center gap-2 text-base font-bold text-gray-800 mb-3">
        <span>💼</span><span>第五步：结合你的持仓，给出个性化建议</span>
      </h3>
      <p class="text-sm leading-relaxed mb-3">
        同一只 ETF 对不同的人建议可能完全不同，因为每个人的持仓和风控参数不一样。系统会综合考虑：
      </p>
      <div class="space-y-2">
        <div v-for="adv in advices" :key="adv.badge"
             class="flex items-start gap-3 p-3 rounded-xl" style="background:#f8fafc">
          <span class="text-sm font-bold flex-shrink-0 w-28" :style="{color: adv.color}">{{ adv.badge }}</span>
          <div class="text-sm text-gray-600 leading-relaxed">{{ adv.desc }}</div>
        </div>
      </div>
    </div>

    <!-- Disclaimer -->
    <div class="rounded-2xl p-4 text-sm"
         style="background:#fffbeb;border:1px solid #fde68a;color:#92400e">
      <strong>⚠ 风险提示：</strong>
      本系统的推荐基于历史规律的统计分析，不构成任何投资建议。
      ETF 的历史表现不代表未来，市场存在不可预测的系统性风险。
      所有建议仅供参考，最终的投资决策需由您本人负责，请务必根据自身风险承受能力进行操作。
    </div>

  </div>
</template>

<script setup>
const features = [
  {
    title: '动量指标',
    color: '#059669',
    items: '5日/10日/20日/60日涨跌幅、RSI 超买超卖指数',
    desc:  '衡量价格的上涨或下跌速度。就像看一辆车的时速表——是在加速还是减速？RSI 还能告诉你：这只 ETF 是否涨得太猛、是否有"透支"的风险。',
  },
  {
    title: '均线偏离',
    color: '#3b82f6',
    items: '相对5日/10日/20日/60日均线的偏差、EMA5与EMA20金叉/死叉',
    desc:  '均线是价格的"平均水位"。当前价格明显高于或低于均线，往往预示着回归的力量。金叉（短线从下穿越长线向上）通常是做多信号，死叉则相反。',
  },
  {
    title: '波动率',
    color: '#7c3aed',
    items: 'ATR 真实波动范围、历史波动率、布林带位置',
    desc:  '衡量价格的"脾气"。布林带就像价格的"合理通道"：当价格跌到通道下轨附近，说明当前价格处于历史低位区，反弹概率更高。',
  },
  {
    title: '量价关系',
    color: '#d97706',
    items: '量比（当日成交量 / 20日均量）、OBV能量潮变化、价量背离',
    desc:  '成交量是"资金意愿"的晴雨表。量价齐升是最健康的上涨；如果价涨但量缩（价量背离），可能是无人接盘的虚涨，需要谨慎。',
  },
  {
    title: 'MACD趋势',
    color: '#0e7490',
    items: 'MACD 主线、信号线、柱状线',
    desc:  'MACD 综合了两条不同周期均线的差距。柱状线由负转正（翻红）是经典的多头启动信号；反之柱状线由正转负，趋势可能走弱。',
  },
]

const nodes = [
  {
    time: '09:25', label: '开盘竞价', color: '#1e3a8a',
    desc: '集合竞价结束时，检查量比是否活跃、开盘方向是否向上。量比过低说明市场不感兴趣，跳过。',
  },
  {
    time: '11:25', label: '午盘收盘前', color: '#7c3aed',
    desc: '上午交易尾声，确认涨幅在合理区间内（不追高，也不是无效小涨）。涨太多可能已过热，涨不够说明信号在衰减。',
  },
  {
    time: '13:05', label: '下午开盘', color: '#0e7490',
    desc: '午休后开盘，看下午资金是否继续跟进，判断上午的涨势能否延续。',
  },
  {
    time: '14:50', label: '尾盘', color: '#b45309',
    desc: '接近收盘，判断全天走势是否强势收官。如果尾盘大幅回落（主力出货迹象），发出减仓/止盈提醒。',
  },
]

const advices = [
  { badge: '🟢 开仓', color: '#059669', desc: '你尚未持有该ETF，资金充足，且你的该板块仓位未满。这是最干净的信号——从零开始建仓。' },
  { badge: '🔵 加仓', color: '#3b82f6', desc: '你已经持有这只ETF，而且今天模型再次看多。只要仓位还没到你设定的上限，可以适量加仓摊低成本或扩大收益。' },
  { badge: '🟡 维持持有', color: '#d97706', desc: '你已持有，但仓位已达上限，或该板块整体仓位已满。信号仍有效，但不适合继续加仓，维持现有仓位即可。' },
  { badge: '🔴 减仓/止损', color: '#ef4444', desc: '你的持仓浮盈超过止盈线（默认20%），或浮亏超过止损线（默认10%）。无论信号多好，先保住本金或锁定收益。' },
  { badge: '⚪ 跳过', color: '#94a3b8', desc: '信号本身不错，但你的账户状态不适合操作：可能是现金不足、某板块集中度过高，或整体仓位接近满仓。等待机会。' },
]
</script>
