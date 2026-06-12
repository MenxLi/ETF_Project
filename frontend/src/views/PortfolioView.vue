<template>
  <div class="flex h-full overflow-hidden">

    <!-- ── Left sidebar (dark) ───────────────────────────── -->
    <aside class="w-56 flex-shrink-0 flex flex-col"
           style="background:#0f172a;border-right:1px solid rgba(255,255,255,0.05)">
      <div class="px-4 py-4 flex items-center justify-between flex-shrink-0"
           style="border-bottom:1px solid rgba(255,255,255,0.05)">
        <span class="text-xs font-semibold tracking-widest uppercase"
              style="color:#475569;letter-spacing:.1em">账户</span>
        <button v-if="store.isAdmin"
                class="text-xs px-2.5 py-1 rounded-lg font-medium transition"
                style="background:rgba(59,130,246,0.12);color:#60a5fa;border:1px solid rgba(59,130,246,0.25)"
                @click="openAddUser">+ 新增</button>
      </div>

      <div class="flex-1 overflow-y-auto py-2 px-2 space-y-0.5">
        <p v-if="!store.users.length" class="text-center py-8 text-sm" style="color:#334155">暂无用户</p>
        <div v-for="u in store.users" :key="u.id"
             class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer transition-all"
             :style="selId === u.id
               ? 'background:rgba(59,130,246,0.14);border:1px solid rgba(59,130,246,0.3)'
               : 'border:1px solid transparent;'"
             style="transition:all .15s"
             @click="selectUser(u.id)">
          <div class="w-8 h-8 rounded-xl flex items-center justify-center text-white text-sm font-bold flex-shrink-0"
               :style="{background: avatarColor(u.name)}">
            {{ u.name[0]?.toUpperCase() }}
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-sm font-medium truncate" style="color:#e2e8f0">{{ u.name }}</div>
            <div class="text-xs truncate" style="color:#475569">
              {{ u.email ? u.email.split('@')[0] + '@…' : '未设置邮箱' }}
            </div>
          </div>
          <div class="w-1.5 h-1.5 rounded-full flex-shrink-0"
               :style="u.active ? 'background:#10b981' : 'background:#334155'"></div>
        </div>
      </div>
    </aside>

    <!-- ── Main area ──────────────────────────────────────── -->
    <div class="flex-1 overflow-y-auto" style="background:#f1f5f9">

      <!-- Empty state -->
      <div v-if="!selId" class="flex flex-col items-center justify-center h-full gap-3"
           style="color:#94a3b8">
        <div class="text-6xl">👈</div>
        <p class="text-lg font-semibold" style="color:#64748b">从左侧选择账户</p>
        <p v-if="store.isAdmin" class="text-sm">或点击「+ 新增」创建用户</p>
      </div>

      <!-- Dashboard -->
      <template v-else-if="selUser && pf">
        <!-- User header banner -->
        <div class="px-6 py-5 flex items-center justify-between"
             style="background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 60%,#1d4ed8 100%)">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 rounded-2xl flex items-center justify-center text-white text-2xl font-bold shadow-xl"
                 :style="{background: avatarColor(selUser.name)}">
              {{ selUser.name[0]?.toUpperCase() }}
            </div>
            <div>
              <div class="flex items-center gap-2 mb-0.5">
                <h2 class="text-xl font-bold text-white">{{ selUser.name }}</h2>
                <span v-if="selUser.role === 'admin'"
                      class="text-xs px-2 py-0.5 rounded-full font-semibold"
                      style="background:rgba(251,191,36,0.18);color:#fbbf24;border:1px solid rgba(251,191,36,0.35)">
                  管理员
                </span>
              </div>
              <p class="text-sm" style="color:#93c5fd">{{ selUser.email || '未设置邮箱' }}</p>
            </div>
          </div>
          <div v-if="store.isAdmin" class="flex gap-2">
            <button v-if="selId !== store.currentUser?.id"
                    class="text-xs px-3 py-1.5 rounded-lg font-medium transition"
                    style="background:rgba(251,191,36,0.12);color:#fbbf24;border:1px solid rgba(251,191,36,0.3)"
                    @click="resetPassword(selUser.id)">重置密码</button>
            <button class="text-xs px-3 py-1.5 rounded-lg font-medium transition"
                    style="background:rgba(248,113,113,0.12);color:#f87171;border:1px solid rgba(248,113,113,0.3)"
                    @click="deleteUser(selUser.id)">删除账户</button>
          </div>
        </div>

        <!-- Metric cards -->
        <div class="grid grid-cols-4 gap-4 px-6 pt-5">
          <div class="rounded-2xl p-4 text-white shadow-lg"
               style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)">
            <div class="text-xs font-medium mb-2 opacity-70">总资产</div>
            <div class="text-2xl font-bold">{{ fmtCash(totalAssets) }}</div>
            <div class="text-xs mt-1 opacity-60">现金 + 持仓估值</div>
          </div>

          <div class="rounded-2xl p-4 text-white shadow-lg relative overflow-hidden"
               style="background:linear-gradient(135deg,#064e3b,#059669)">
            <div class="text-xs font-medium mb-2 opacity-70">可用现金</div>
            <div class="text-2xl font-bold">{{ fmtCash(pf.cash) }}</div>
            <button class="absolute top-3.5 right-3.5 text-xs px-2.5 py-1 rounded-lg font-semibold transition"
                    style="background:rgba(255,255,255,0.18);backdrop-filter:blur(4px)"
                    @click="showDepositModal = true">+ 入金</button>
            <div class="text-xs mt-1 opacity-60">可投资资金</div>
          </div>

          <div class="rounded-2xl p-4 text-white shadow-lg"
               style="background:linear-gradient(135deg,#3b0764,#7c3aed)">
            <div class="text-xs font-medium mb-2 opacity-70">持仓估值</div>
            <div class="text-2xl font-bold">{{ fmtCash(totalCost) }}</div>
            <div class="text-xs mt-1 opacity-60">按成本价估算</div>
          </div>

          <div class="rounded-2xl p-4 text-white shadow-lg"
               style="background:linear-gradient(135deg,#78350f,#d97706)">
            <div class="text-xs font-medium mb-2 opacity-70">持仓品种</div>
            <div class="text-2xl font-bold">
              {{ pf.positions?.length ?? 0 }}
              <span class="text-base font-normal opacity-70">只</span>
            </div>
            <div class="text-xs mt-1 opacity-60">ETF 标的数量</div>
          </div>
        </div>

        <!-- Tab bar + content -->
        <div class="px-6 pt-5 pb-6">
          <!-- Pill tab selector -->
          <div class="inline-flex gap-1 bg-white rounded-xl p-1 mb-5 shadow-sm">
            <button v-for="t in tabs" :key="t.key"
                    class="px-5 py-2 rounded-lg text-sm font-medium transition-all"
                    :class="tab === t.key ? 'text-white shadow' : 'text-gray-500 hover:text-gray-700'"
                    :style="tab === t.key
                      ? `background:${t.color || 'linear-gradient(135deg,#1e3a8a,#3b82f6)'}`
                      : ''"
                    @click="tab = t.key">
              {{ t.label }}
            </button>
          </div>

          <!-- ── 持仓明细 ── -->
          <div v-if="tab === 'positions'" class="bg-white rounded-2xl shadow-sm overflow-hidden">
            <div class="flex items-center justify-between px-5 py-4"
                 style="border-bottom:1px solid #f1f5f9">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-gray-800">持仓明细</span>
                <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                      style="background:#eff6ff;color:#1d4ed8">
                  {{ pf.positions?.length ?? 0 }} 只
                </span>
              </div>
              <button class="text-sm font-medium px-4 py-2 rounded-xl text-white transition shadow-sm"
                      style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)"
                      @click="openAddPos">📥 导入初始持仓</button>
            </div>
            <table class="w-full text-sm">
              <thead style="background:#f8fafc">
                <tr>
                  <th class="px-5 py-3 text-left text-xs font-semibold text-gray-400">标的</th>
                  <th class="px-5 py-3 text-right text-xs font-semibold text-gray-400">股数</th>
                  <th class="px-5 py-3 text-right text-xs font-semibold text-gray-400">成本价</th>
                  <th class="px-5 py-3 text-right text-xs font-semibold text-gray-400">成本市值</th>
                  <th class="px-5 py-3 text-center text-xs font-semibold text-gray-400">买入日期</th>
                  <th class="px-5 py-3 text-right text-xs font-semibold text-gray-400">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!pf.positions?.length">
                  <td colspan="6" class="text-center py-14 text-gray-400">
                    <div class="text-4xl mb-3">📭</div>
                    <p class="font-medium">暂无持仓</p>
                    <p class="text-xs mt-1">点击「导入初始持仓」添加使用平台前的已有持仓</p>
                  </td>
                </tr>
                <tr v-for="p in pf.positions" :key="p.code"
                    class="transition-colors"
                    :style="{ borderTop: '1px solid #f8fafc' }"
                    @mouseenter="$event.currentTarget.style.background='#fafbff'"
                    @mouseleave="$event.currentTarget.style.background=''"
                    >
                  <td class="px-5 py-4">
                    <div class="flex items-center gap-3">
                      <div class="w-9 h-9 rounded-xl flex items-center justify-center text-xs font-bold text-white shadow-sm"
                           style="background:linear-gradient(135deg,#3b82f6,#1d4ed8)">
                        {{ p.code.slice(-2) }}
                      </div>
                      <div>
                        <div class="font-semibold text-gray-800">{{ p.name }}</div>
                        <div class="text-xs text-gray-400">{{ p.code }}</div>
                      </div>
                    </div>
                  </td>
                  <td class="px-5 py-4 text-right text-gray-700 font-medium">
                    {{ p.shares.toLocaleString() }}
                  </td>
                  <td class="px-5 py-4 text-right text-gray-700">¥{{ p.cost_price.toFixed(3) }}</td>
                  <td class="px-5 py-4 text-right font-semibold text-gray-800">
                    {{ fmtCash(p.shares * p.cost_price) }}
                  </td>
                  <td class="px-5 py-4 text-center">
                    <span class="text-xs px-2.5 py-1 rounded-full" style="background:#f1f5f9;color:#64748b">
                      {{ p.buy_date }}
                    </span>
                  </td>
                  <td class="px-5 py-4 text-right">
                    <button class="text-xs font-medium mr-3" style="color:#3b82f6"
                            @click="openEditPos(p.code)">编辑</button>
                    <button class="text-xs font-medium" style="color:#f43f5e"
                            @click="deletePos(p.code)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ── 交易记录 ── -->
          <div v-else-if="tab === 'transactions'" class="bg-white rounded-2xl shadow-sm overflow-hidden">
            <div class="flex items-center justify-between px-5 py-4"
                 style="border-bottom:1px solid #f1f5f9">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-gray-800">交易记录</span>
                <span class="text-xs px-2 py-0.5 rounded-full font-medium"
                      style="background:#f5f3ff;color:#6d28d9">
                  {{ transactions.length }} 笔
                </span>
              </div>
              <button class="text-sm font-medium px-4 py-2 rounded-xl text-white transition shadow-sm"
                      style="background:linear-gradient(135deg,#3b0764,#7c3aed)"
                      @click="openAddTx">+ 新增交易</button>
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
                    class="transition-colors"
                    :style="{ borderTop: '1px solid #f8fafc' }"
                    @mouseenter="$event.currentTarget.style.background='#fafbff'"
                    @mouseleave="$event.currentTarget.style.background=''"
                    >
                  <td class="px-5 py-3.5">
                    <span class="text-xs px-2 py-1 rounded-md" style="background:#f1f5f9;color:#64748b">
                      {{ tx.date }}
                    </span>
                  </td>
                  <td class="px-5 py-3.5">
                    <span class="text-xs font-bold px-2.5 py-1 rounded-full"
                          :style="tx.action === 'buy'
                            ? 'background:#d1fae5;color:#065f46'
                            : 'background:#ffe4e6;color:#9f1239'">
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
                    <button class="text-xs font-medium" style="color:#f43f5e"
                            @click="deleteTx(tx)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- ── 账号设置 ── -->
          <div v-else-if="tab === 'settings'" class="grid grid-cols-2 gap-4">
            <div class="bg-white rounded-2xl shadow-sm p-5">
              <h3 class="font-semibold text-gray-700 text-sm mb-4 pb-3"
                  style="border-bottom:1px solid #f1f5f9">基本信息</h3>
              <div class="space-y-4">
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">姓名</label>
                  <input v-model="cfg.name" type="text" class="input" />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">邮箱（信号推送）</label>
                  <input v-model="cfg.email" type="email" class="input" />
                </div>
                <label class="flex items-center gap-2.5 text-sm text-gray-600 cursor-pointer select-none">
                  <input v-model="cfg.active" type="checkbox" class="w-4 h-4 rounded accent-blue-600" />
                  接收每日推送邮件
                </label>
              </div>
            </div>

            <div class="bg-white rounded-2xl shadow-sm p-5">
              <h3 class="font-semibold text-gray-700 text-sm mb-4 pb-3"
                  style="border-bottom:1px solid #f1f5f9">风控参数</h3>
              <div class="space-y-5">
                <div>
                  <div class="flex justify-between items-center mb-2">
                    <label class="text-xs font-medium text-gray-500">单只最大仓位</label>
                    <span class="text-sm font-bold" style="color:#3b82f6">{{ fmtPct(cfg.max_position_pct) }}</span>
                  </div>
                  <input v-model.number="cfg.max_position_pct" type="range"
                         min="0.05" max="0.5" step="0.05"
                         class="w-full h-1.5 rounded-full cursor-pointer accent-blue-600" />
                  <div class="flex justify-between text-xs text-gray-300 mt-1">
                    <span>5%</span><span>50%</span>
                  </div>
                </div>
                <div>
                  <div class="flex justify-between items-center mb-2">
                    <label class="text-xs font-medium text-gray-500">板块最大仓位</label>
                    <span class="text-sm font-bold" style="color:#3b82f6">{{ fmtPct(cfg.max_sector_pct) }}</span>
                  </div>
                  <input v-model.number="cfg.max_sector_pct" type="range"
                         min="0.1" max="0.8" step="0.05"
                         class="w-full h-1.5 rounded-full cursor-pointer accent-blue-600" />
                  <div class="flex justify-between text-xs text-gray-300 mt-1">
                    <span>10%</span><span>80%</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="col-span-2 flex justify-end">
              <button class="px-6 py-2.5 rounded-xl text-sm font-semibold text-white shadow-sm transition"
                      style="background:linear-gradient(135deg,#1e3a8a,#3b82f6)"
                      @click="saveSettings">保存设置</button>
            </div>

            <!-- Change password -->
            <div v-if="selId === store.currentUser?.id"
                 class="col-span-2 bg-white rounded-2xl shadow-sm p-5">
              <h3 class="font-semibold text-gray-700 text-sm mb-4 pb-3"
                  style="border-bottom:1px solid #f1f5f9">修改密码</h3>
              <div class="grid grid-cols-3 gap-4">
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">当前密码</label>
                  <input v-model="pwForm.old" type="password" class="input" autocomplete="current-password" />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">新密码</label>
                  <input v-model="pwForm.new1" type="password" class="input" autocomplete="new-password" />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1.5">确认新密码</label>
                  <input v-model="pwForm.new2" type="password" class="input" autocomplete="new-password" />
                </div>
              </div>
              <div class="flex items-center justify-between mt-4">
                <span v-if="pwMsg" class="text-sm"
                      :style="pwMsg.ok ? 'color:#059669' : 'color:#f43f5e'">{{ pwMsg.text }}</span>
                <span v-else class="text-xs text-gray-400">密码至少 4 位</span>
                <button class="px-5 py-2 rounded-xl text-sm font-semibold text-white shadow-sm transition"
                        style="background:linear-gradient(135deg,#3b0764,#7c3aed)"
                        @click="changePassword">修改密码</button>
              </div>
            </div>
          </div>

        </div><!-- /px-6 -->
      </template>
    </div><!-- /main -->

    <!-- ── Modals ─────────────────────────────────────────── -->

    <!-- Add User -->
    <Teleport to="body">
      <div v-if="showUserModal" class="modal-overlay">
        <div class="modal-box" @click.stop>
          <div class="flex items-center justify-between mb-4">
            <h3 class="modal-title" style="margin-bottom:0">新增用户</h3>
            <button class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all text-lg font-light"
                    @click="showUserModal = false">✕</button>
          </div>
          <div class="space-y-3">
            <div><label class="field-label">姓名 *</label>
              <input v-model="newUser.name" type="text" placeholder="例：张三" class="input" /></div>
            <div><label class="field-label">邮箱 *</label>
              <input v-model="newUser.email" type="email" placeholder="例：user@163.com" class="input" /></div>
            <div><label class="field-label">初始现金（元）</label>
              <input v-model.number="newUser.cash" type="number" class="input" /></div>
            <label class="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
              <input v-model="newUser.active" type="checkbox" /> 立即启用
            </label>
            <p class="text-xs text-gray-400">初始密码 = 用户名（登录后请通知用户修改）</p>
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showUserModal = false">取消</button>
            <button class="btn-primary" @click="submitAddUser">创建账户</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Deposit (入金) -->
    <Teleport to="body">
      <div v-if="showDepositModal" class="modal-overlay">
        <div class="modal-box" style="width:340px" @click.stop>
          <div class="flex items-center justify-between mb-4">
            <h3 class="modal-title" style="margin-bottom:0">增加可用资金</h3>
            <button class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all text-lg font-light"
                    @click="showDepositModal = false">✕</button>
          </div>
          <div class="space-y-3">
            <div>
              <label class="field-label">当前余额</label>
              <div class="input bg-gray-50 text-gray-500">{{ fmtCash(pf?.cash ?? 0) }}</div>
            </div>
            <div>
              <label class="field-label">入金金额（元）*</label>
              <input v-model.number="depositAmt" type="number" min="1" step="1000"
                     placeholder="例：50000" class="input" ref="depositInput" />
            </div>
            <div v-if="depositAmt > 0" class="flex items-center justify-between text-sm px-1">
              <span class="text-gray-500">入金后余额</span>
              <span class="font-bold" style="color:#059669">
                {{ fmtCash((pf?.cash ?? 0) + Number(depositAmt)) }}
              </span>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showDepositModal = false">取消</button>
            <button class="btn-primary" style="background:linear-gradient(135deg,#064e3b,#059669);border:none"
                    @click="submitDeposit">确认入金</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Add/Edit Position -->
    <Teleport to="body">
      <div v-if="showPosModal" class="modal-overlay">
        <div class="modal-box" @click.stop>
          <div class="flex items-center justify-between mb-4">
            <h3 class="modal-title" style="margin-bottom:0">{{ posTitle }}</h3>
            <button class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all text-lg font-light"
                    @click="showPosModal = false">✕</button>
          </div>
          <!-- 导入说明（仅新增时显示） -->
          <div v-if="editCode === null"
               class="flex items-start gap-2 text-xs text-blue-700 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2 mb-3">
            <span class="mt-0.5">ℹ️</span>
            <span>仅用于导入使用平台前的已有持仓，<strong>不扣减现金余额</strong>。日常交易请使用「新增交易」按钮。</span>
          </div>
          <div class="space-y-3">
            <div>
              <label class="field-label">ETF 代码 *</label>
              <!-- 快捷选择（仅新增时显示） -->
              <div v-if="editCode === null && todaySignals.length" class="mb-2">
                <span class="text-xs text-gray-400 mr-1.5">今日推荐：</span>
                <button v-for="s in todaySignals" :key="s.code"
                        class="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full mr-1 mb-1 border transition"
                        :style="posForm.code === s.code
                          ? 'background:#059669;color:white;border-color:#059669'
                          : 'background:#f0fdf4;color:#065f46;border-color:#bbf7d0'"
                        @click="quickPickPos(s.code, s.name)">
                  {{ s.name }}
                  <span class="opacity-70">{{ (s.prob_up * 100).toFixed(0) }}%</span>
                </button>
              </div>
              <EtfSearch v-model="posForm.code" v-model:name="posForm.name"
                         :readonly="editCode !== null"
                         placeholder="输入代码或名称搜索，例：沪深300" />
            </div>
            <div><label class="field-label">名称</label>
              <input v-model="posForm.name" type="text" readonly class="input bg-gray-50 text-gray-400" /></div>
            <div class="flex gap-3">
              <div class="flex-1"><label class="field-label">股数 *</label>
                <input v-model.number="posForm.shares" type="number" placeholder="例：1000" class="input" /></div>
              <div class="flex-1"><label class="field-label">成本价（元）*</label>
                <input v-model.number="posForm.cost_price" type="number" step="0.001"
                       placeholder="例：3.250" class="input" /></div>
            </div>
            <div><label class="field-label">买入日期</label>
              <input v-model="posForm.buy_date" type="date" class="input" /></div>
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showPosModal = false">取消</button>
            <button class="btn-primary" @click="submitPos">保存</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- New Transaction -->
    <Teleport to="body">
      <div v-if="showTxModal" class="modal-overlay">
        <div class="modal-box" style="width:420px" @click.stop>
          <div class="flex items-center justify-between mb-4">
            <h3 class="modal-title" style="margin-bottom:0">新增交易记录</h3>
            <button class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-all text-lg font-light"
                    @click="showTxModal = false">✕</button>
          </div>
          <div class="space-y-3">
            <div>
              <label class="field-label">交易方向</label>
              <div class="flex gap-2">
                <button v-for="opt in [{v:'buy',label:'▲ 买入'},{v:'sell',label:'▼ 卖出'}]" :key="opt.v"
                        class="flex-1 py-2 rounded-xl text-sm font-semibold border transition"
                        :style="txForm.action === opt.v
                          ? (opt.v === 'buy'
                              ? 'background:#059669;color:white;border-color:#059669'
                              : 'background:#e11d48;color:white;border-color:#e11d48')
                          : 'background:white;color:#64748b;border-color:#e2e8f0'"
                        @click="txForm.action = opt.v">{{ opt.label }}</button>
              </div>
            </div>
            <div>
              <label class="field-label">ETF 标的 *</label>
              <!-- 快捷选择 -->
              <div v-if="pf?.positions?.length || todaySignals.length" class="mb-2">
                <!-- 持仓中 -->
                <div v-if="pf?.positions?.length" class="mb-1.5">
                  <span class="text-xs text-gray-400 mr-1.5">持仓中：</span>
                  <button v-for="p in pf.positions" :key="p.code"
                          class="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full mr-1 mb-1 border transition"
                          :style="txForm.etf_code === p.code
                            ? 'background:#1e3a8a;color:white;border-color:#1e3a8a'
                            : 'background:#eff6ff;color:#1e3a8a;border-color:#bfdbfe'"
                          @click="quickPickTx(p.code, p.name)">
                    {{ p.name }}
                  </button>
                </div>
                <!-- 今日推荐 -->
                <div v-if="todaySignals.length">
                  <span class="text-xs text-gray-400 mr-1.5">今日推荐：</span>
                  <button v-for="s in todaySignals" :key="s.code"
                          class="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full mr-1 mb-1 border transition"
                          :style="txForm.etf_code === s.code
                            ? 'background:#059669;color:white;border-color:#059669'
                            : 'background:#f0fdf4;color:#065f46;border-color:#bbf7d0'"
                          @click="quickPickTx(s.code, s.name)">
                    {{ s.name }}
                    <span class="opacity-70">{{ (s.prob_up * 100).toFixed(0) }}%</span>
                  </button>
                </div>
              </div>
              <EtfSearch v-model="txForm.etf_code" v-model:name="txForm.etf_name"
                         placeholder="输入代码或名称搜索" />
            </div>
            <div><label class="field-label">交易日期</label>
              <input v-model="txForm.date" type="date" class="input" /></div>
            <div class="flex gap-3">
              <div class="flex-1"><label class="field-label">数量（股）*</label>
                <input v-model.number="txForm.shares" type="number" placeholder="例：1000" class="input" /></div>
              <div class="flex-1">
                <label class="field-label">
                  成交价（元）*
                  <span v-if="txPriceLoading" class="ml-1 text-blue-400 font-normal text-xs">拉取中…</span>
                  <span v-else-if="txPriceSource === 'realtime'"
                        class="ml-1 font-normal text-xs" style="color:#059669">● 实时价</span>
                  <span v-else-if="txPriceSource === 'local_close'"
                        class="ml-1 font-normal text-xs text-gray-400">昨收价</span>
                </label>
                <input v-model.number="txForm.price" type="number" step="0.001"
                       placeholder="例：4.250" class="input" />
              </div>
            </div>
            <div class="flex justify-between items-center text-sm px-1 py-1 rounded-lg"
                 style="background:#f8fafc">
              <span class="text-gray-500 text-xs">金额合计</span>
              <span class="font-bold"
                    :style="txAmount !== '—'
                      ? (txForm.action === 'sell' ? 'color:#059669' : 'color:#1e293b')
                      : 'color:#94a3b8'">
                {{ txAmount === '—' ? '—' : (txForm.action === 'sell' ? '+' : '') + '¥' + Number(txAmount).toLocaleString('zh-CN') }}
              </span>
            </div>
            <div><label class="field-label">备注（可选）</label>
              <input v-model="txForm.note" type="text" placeholder="例：按信号买入" class="input" /></div>
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showTxModal = false">取消</button>
            <button class="btn-primary"
                    :style="txForm.action === 'sell'
                      ? 'background:linear-gradient(135deg,#9f1239,#e11d48);border:none' : ''"
                    @click="submitTx">
              确认{{ txForm.action === 'buy' ? '买入' : '卖出' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { store } from '../store.js'
import EtfSearch from '../components/EtfSearch.vue'
import { api, fmtCash, fmtPct, todayStr, fetchRealtimePrice } from '../api.js'

// ── Avatar ────────────────────────────────────────────────────
const AVATAR_COLORS = ['#3b82f6','#8b5cf6','#ec4899','#f59e0b','#10b981','#06b6d4','#f43f5e','#84cc16']
function avatarColor(name) {
  return AVATAR_COLORS[(name?.charCodeAt(0) ?? 0) % AVATAR_COLORS.length]
}

// ── Tabs ──────────────────────────────────────────────────────
const tabs = [
  { key: 'positions',    label: '持仓明细',  color: 'linear-gradient(135deg,#1e3a8a,#3b82f6)' },
  { key: 'transactions', label: '交易记录',  color: 'linear-gradient(135deg,#3b0764,#7c3aed)' },
  { key: 'settings',     label: '账号设置',  color: 'linear-gradient(135deg,#1e293b,#475569)' },
]

// ── State ─────────────────────────────────────────────────────
const selId  = ref(null)
const tab    = ref('positions')
const pf     = ref(null)
const transactions  = ref([])

const showUserModal    = ref(false)
const showDepositModal = ref(false)
const showPosModal     = ref(false)
const showTxModal      = ref(false)

const editCode   = ref(null)
const posTitle   = ref('导入初始持仓')
const depositAmt = ref('')

const cfg = reactive({
  name: '', email: '', cash: 0,
  max_position_pct: 0.3, max_sector_pct: 0.5, active: true,
})
const newUser = reactive({ name: '', email: '', cash: 100000, active: true })
const posForm = reactive({ code: '', name: '', shares: '', cost_price: '', buy_date: todayStr() })
const pwForm  = reactive({ old: '', new1: '', new2: '' })
const pwMsg   = ref(null)

const txForm = reactive({
  date: todayStr(), action: 'buy',
  etf_code: '', etf_name: '', shares: '', price: '', note: '',
})
const txPriceLoading = ref(false)
const txPriceSource  = ref('')   // 'realtime' | 'local_close' | ''

// ── Computed ──────────────────────────────────────────────────
const selUser = computed(() => store.users.find(u => u.id === selId.value))
const totalAssets = computed(() =>
  (pf.value?.cash ?? 0) + (pf.value?.positions ?? []).reduce((s, p) => s + p.shares * p.cost_price, 0)
)
const totalCost = computed(() =>
  (pf.value?.positions ?? []).reduce((s, p) => s + p.shares * p.cost_price, 0)
)
const txAmount = computed(() => {
  const s = Number(txForm.shares)
  const p = Number(txForm.price)
  return (!isNaN(s) && !isNaN(p) && s > 0 && p > 0) ? (s * p).toFixed(2) : '—'
})

// Sync cfg when user / portfolio changes
watch(selUser, u => {
  if (!u) return
  cfg.name   = u.name
  cfg.email  = u.email ?? ''
  cfg.active = u.active
  Object.assign(pwForm, { old: '', new1: '', new2: '' })
  pwMsg.value = null
})
watch(pf, p => {
  if (!p) return
  cfg.cash             = p.cash
  cfg.max_position_pct = p.max_position_pct
  cfg.max_sector_pct   = p.max_sector_pct
})

// ── Today's signals (for quick-pick) ─────────────────────────
const todaySignals = ref([])
onMounted(async () => {
  if (store.currentUser && !store.isAdmin) {
    await selectUser(store.currentUser.id)
  }
  try {
    const d = await api('GET', '/api/signals')
    todaySignals.value = (d.signals ?? []).slice(0, 8)  // 最多显示8条
  } catch {}
})

// 快捷填入 ETF（交易弹窗）并自动拉实时价
async function quickPickTx(code, name) {
  txForm.etf_code    = code
  txForm.etf_name    = name || store.etfList[code] || code
  txPriceSource.value = ''
  txPriceLoading.value = true
  const rt = await fetchRealtimePrice(code)
  txPriceLoading.value = false
  if (rt?.price) {
    txForm.price        = rt.price
    txPriceSource.value = rt.source
  }
}

// 快捷填入 ETF（持仓弹窗）
function quickPickPos(code, name) {
  posForm.code = code
  posForm.name = name || store.etfList[code] || code
}

// ── Data loading ──────────────────────────────────────────────
async function selectUser(id) {
  selId.value        = id
  tab.value          = 'positions'
  transactions.value = []
  pf.value           = null
  try {
    [pf.value, transactions.value] = await Promise.all([
      api('GET', `/api/portfolio/${id}`),
      api('GET', `/api/transactions/${id}`),
    ])
  } catch (e) {
    store.status = '加载失败: ' + e.message
  }
}

async function loadTransactions() {
  try { transactions.value = await api('GET', `/api/transactions/${selId.value}`) } catch {}
}

// ── User management ───────────────────────────────────────────
function openAddUser() {
  Object.assign(newUser, { name: '', email: '', cash: 100000, active: true })
  showUserModal.value = true
}

async function submitAddUser() {
  if (!newUser.name || !newUser.email) { alert('姓名和邮箱不能为空'); return }
  try {
    store.status = '创建中…'
    const u = await api('POST', '/api/users', { ...newUser })
    showUserModal.value = false
    await store.refreshUsers()
    store.status = '账户已创建 ✓'
    await selectUser(u.id)
  } catch (e) { store.status = '创建失败: ' + e.message }
}

async function deleteUser(id) {
  const u = store.users.find(u => u.id === id)
  if (!confirm(`确认删除用户「${u.name}」及其所有持仓和交易记录？此操作不可撤销。`)) return
  try {
    await api('DELETE', `/api/users/${id}`)
    selId.value = null
    pf.value    = null
    await store.refreshUsers()
    store.status = '已删除 ✓'
  } catch (e) { store.status = '删除失败: ' + e.message }
}

async function resetPassword(id) {
  const pw = prompt('为该用户设置新密码（留空则重置为用户名）:')
  if (pw === null) return
  try {
    await api('POST', `/api/users/${id}/reset-password`, { password: pw.trim() || id })
    store.status = '密码已重置 ✓'
  } catch (e) { store.status = '重置失败: ' + e.message }
}

// ── Settings ──────────────────────────────────────────────────
async function saveSettings() {
  try {
    store.status = '保存中…'
    await api('PUT', `/api/users/${selId.value}`,
      { name: cfg.name, email: cfg.email, active: cfg.active })
    pf.value = await api('PUT', `/api/portfolio/${selId.value}`, {
      cash: cfg.cash, max_position_pct: cfg.max_position_pct, max_sector_pct: cfg.max_sector_pct,
    })
    await store.refreshUsers()
    store.status = '已保存 ✓'
  } catch (e) { store.status = '保存失败: ' + e.message }
}

async function changePassword() {
  pwMsg.value = null
  if (pwForm.new1 !== pwForm.new2) { pwMsg.value = { ok: false, text: '两次新密码不一致' }; return }
  if (pwForm.new1.length < 4)      { pwMsg.value = { ok: false, text: '新密码至少 4 位' };   return }
  try {
    await api('POST', '/api/auth/change-password',
      { old_password: pwForm.old, new_password: pwForm.new1 })
    Object.assign(pwForm, { old: '', new1: '', new2: '' })
    pwMsg.value = { ok: true, text: '密码已修改 ✓' }
  } catch (e) { pwMsg.value = { ok: false, text: e.message } }
}

// ── Deposit ───────────────────────────────────────────────────
async function submitDeposit() {
  const amt = Number(depositAmt.value)
  if (!amt || amt <= 0) { alert('请输入有效金额'); return }
  try {
    store.status = '入金中…'
    pf.value = await api('PUT', `/api/portfolio/${selId.value}`, {
      cash: (pf.value?.cash ?? 0) + amt,
    })
    cfg.cash = pf.value.cash
    depositAmt.value = ''
    showDepositModal.value = false
    store.status = '入金成功 ✓'
  } catch (e) { store.status = '入金失败: ' + e.message }
}

// ── Positions ─────────────────────────────────────────────────
function openAddPos() {
  editCode.value = null
  posTitle.value = '导入初始持仓'
  Object.assign(posForm, { code: '', name: '', shares: '', cost_price: '', buy_date: todayStr() })
  showPosModal.value = true
}

function openEditPos(code) {
  const pos = pf.value?.positions?.find(p => p.code === code)
  if (!pos) return
  editCode.value = code
  posTitle.value = '编辑持仓'
  Object.assign(posForm, {
    code: pos.code, name: pos.name,
    shares: pos.shares, cost_price: pos.cost_price, buy_date: pos.buy_date,
  })
  showPosModal.value = true
}

async function submitPos() {
  const code = posForm.code.trim()
  const name = posForm.name || store.etfList[code] || code
  if (!code || isNaN(posForm.shares) || isNaN(posForm.cost_price)) {
    alert('请填写代码、股数和成本价'); return
  }
  try {
    store.status = '保存中…'
    await api('POST', `/api/portfolio/${selId.value}/positions`, {
      code, name,
      shares:     Number(posForm.shares),
      cost_price: Number(posForm.cost_price),
      buy_date:   posForm.buy_date,
    })
    pf.value = await api('GET', `/api/portfolio/${selId.value}`)
    showPosModal.value = false
    store.status = '已保存 ✓'
  } catch (e) { store.status = '保存失败: ' + e.message }
}

async function deletePos(code) {
  if (!confirm(`确认删除持仓 ${code}？`)) return
  try {
    await api('DELETE', `/api/portfolio/${selId.value}/positions/${code}`)
    pf.value = await api('GET', `/api/portfolio/${selId.value}`)
    store.status = '已删除 ✓'
  } catch (e) { store.status = '删除失败: ' + e.message }
}

// ── Transactions ──────────────────────────────────────────────
function openAddTx() {
  Object.assign(txForm, {
    date: todayStr(), action: 'buy',
    etf_code: '', etf_name: '', shares: '', price: '', note: '',
  })
  showTxModal.value = true
}

async function submitTx() {
  if (!txForm.etf_code || !txForm.shares || !txForm.price) {
    alert('请填写 ETF、数量和成交价'); return
  }
  try {
    store.status = '保存中…'
    await api('POST', `/api/transactions/${selId.value}`, {
      date: txForm.date, action: txForm.action,
      etf_code: txForm.etf_code.trim(),
      etf_name: txForm.etf_name || store.etfList[txForm.etf_code] || txForm.etf_code,
      shares: Number(txForm.shares),
      price:  Number(txForm.price),
      note:   txForm.note,
    })
    showTxModal.value = false
    // 刷新交易记录 + 持仓 + 现金
    ;[pf.value, transactions.value] = await Promise.all([
      api('GET', `/api/portfolio/${selId.value}`),
      api('GET', `/api/transactions/${selId.value}`),
    ])
    store.status = txForm.action === 'buy' ? '买入已记录 ✓' : '卖出已记录 ✓'
  } catch (e) { store.status = '保存失败: ' + e.message }
}

async function deleteTx(tx) {
  if (!confirm('确认删除这笔交易记录？')) return
  try {
    await api('DELETE', `/api/transactions/${selId.value}/${tx.id}`)
    await loadTransactions()
    store.status = '已删除 ✓'
  } catch (e) { store.status = '删除失败: ' + e.message }
}
</script>

<style scoped>
.input {
  @apply w-full border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm
         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
         transition bg-white;
}
.btn-primary {
  @apply flex-1 py-2.5 rounded-xl text-sm font-semibold text-white transition cursor-pointer border-0;
  background: linear-gradient(135deg, #1e3a8a, #3b82f6);
}
.btn-cancel {
  @apply flex-1 border border-gray-200 text-gray-600 
  py-2.5 rounded-xl text-sm font-semibold transition cursor-pointer;
}
.btn-cancel:hover {
  @apply bg-gray-50;
}
.field-label {
  @apply block text-xs font-medium text-gray-500 mb-1.5;
}
.modal-overlay {
  @apply fixed inset-0 flex items-center justify-center z-50;
  background: rgba(15,23,42,.6);
  backdrop-filter: blur(4px);
}
.modal-box {
  @apply bg-white rounded-2xl shadow-2xl w-96 p-6;
}
.modal-title {
  @apply text-base font-bold text-gray-800 mb-5;
}
.modal-actions {
  @apply flex gap-2 mt-5;
}
</style>
