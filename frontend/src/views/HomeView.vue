<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import { Calendar, Cpu, Lock, Timer, ChatLineRound, Promotion, InfoFilled } from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

// AI Agent Simulator State
const aiInput = ref('帮我订一间 2026-07-15 到 2026-07-17 的标准双人房')
const simulating = ref(false)
const simSteps = ref<Array<{ type: 'user' | 'agent' | 'system'; text: string; action?: any }>>([])

const mcpConfigCode = `{
  "mcpServers": {
    "aetherstay": {
      "command": "uv",
      "args": [
        "run",
        "--github",
        "smile9493/AetherStay",
        "mcp-server"
      ]
    }
  }
}`

async function runAiSimulation() {
  if (!aiInput.value.trim()) return
  
  simulating.value = true
  simSteps.value = []
  
  // Step 1: User request
  simSteps.value.push({ type: 'user', text: aiInput.value })
  
  // Step 2: AI Parsing
  await delay(1200)
  simSteps.value.push({ type: 'system', text: '🤖 AI Agent: 正在解析自然语言指令...' })
  
  // Simple NLP parser in JS for demo
  const dateRegex = /(\d{4}-\d{2}-\d{2})/g
  const dates = aiInput.value.match(dateRegex)
  let checkIn = dates?.[0] || '2026-07-15'
  let checkOut = dates?.[1] || '2026-07-17'
  
  await delay(1000)
  simSteps.value.push({ 
    type: 'system', 
    text: `🔍 AI Agent: 提取到预订参数 -> 入住: \`${checkIn}\`, 退房: \`${checkOut}\`。正在调用 MCP 工具 \`get_available_rooms\` 检索可用房态...` 
  })
  
  try {
    // Call real search endpoint
    const { data: availableRooms } = await api.get<any[]>('/rooms/search', {
      params: { check_in: checkIn, check_out: checkOut }
    })
    
    await delay(1200)
    if (!availableRooms || availableRooms.length === 0) {
      simSteps.value.push({ 
        type: 'agent', 
        text: `抱歉，在 ${checkIn} 至 ${checkOut} 期间暂无可用客房。您可以尝试更换日期再吩咐我。` 
      })
      simulating.value = false
      return
    }
    
    // Choose the first room
    const targetRoom = availableRooms[0]
    simSteps.value.push({ 
      type: 'system', 
      text: `✨ AI Agent: 发现可用客房: ${targetRoom.room_number} (${targetRoom.room_type.name})，每晚价格: ¥${targetRoom.room_type.base_price}。`
    })
    
    await delay(1000)
    simSteps.value.push({ 
      type: 'system', 
      text: `🔒 AI Agent: 正在通过 MCP 工具 \`create_booking\` 发送两阶段锁定预订请求...` 
    })
    
    if (!auth.user) {
      await delay(1000)
      simSteps.value.push({ 
        type: 'agent', 
        text: `检测到您尚未登录，MCP 接口需要用户凭证。请在右侧先进行登录或注册，然后重试模拟！` 
      })
      simulating.value = false
      return
    }
    
    // Create actual booking
    const { data: newBooking } = await api.post('/bookings', {
      room_id: targetRoom.id,
      check_in: checkIn,
      check_out: checkOut
    })
    
    await delay(1500)
    simSteps.value.push({
      type: 'agent',
      text: `🎉 预订操作成功！我已为您锁定了客房 **${targetRoom.room_number}**（订单号: **#${newBooking.id}**，总价: **¥${newBooking.total_price}**）。

> ⚠️ **锁房时效提示**：根据系统 **Hold-then-Confirm** 两阶段锁定机制，房态当前处于 \`held\`（锁定）状态，系统为您保留 15 分钟（至 ${formatExpireTime()}）。请前往【我的订单】或点击下方按钮，在倒计时结束前完成模拟支付。若超时未付，库存将自动释放归还。`,
      action: {
        text: '前往支付订单',
        handler: () => router.push('/bookings')
      }
    })
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || '系统调度异常或网络超时。'
    simSteps.value.push({ 
      type: 'agent', 
      text: `❌ 预订失败。原因: ${errorMsg}` 
    })
  } finally {
    simulating.value = false
  }
}

function delay(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function formatExpireTime() {
  const d = new Date()
  d.setMinutes(d.getMinutes() + 15)
  return d.toTimeString().split(' ')[0]
}
</script>

<template>
  <div class="home-page">
    <!-- Hero Banner Section -->
    <div class="hero-section glass-panel">
      <div class="hero-content">
        <h1 class="hero-title">未来已来，智享栖息</h1>
        <p class="hero-subtitle">
          AetherStay — 首款融合 **RESTful Web 浏览器** 与 **AI Agent (MCP 协议)** 双模交互的高性能酒店客房预订管理系统。
        </p>
        <div class="hero-actions">
          <el-button type="primary" size="large" class="glow-btn" @click="router.push('/rooms')">
            浏览与预订客房
          </el-button>
          <el-button size="large" class="outline-btn" @click="router.push('/register')" v-if="!auth.user">
            加入会员
          </el-button>
          <el-button size="large" class="outline-btn" @click="router.push('/bookings')" v-else>
            管理我的订单
          </el-button>
        </div>
      </div>
      <div class="hero-visual">
        <div class="visual-card glass-panel">
          <div class="card-glow"></div>
          <div class="console-header">
            <span class="dot red"></span>
            <span class="dot yellow"></span>
            <span class="dot green"></span>
            <span class="title">AetherStay MCP Console</span>
          </div>
          <div class="console-body">
            <p class="c-line"><span class="c-prompt">$</span> mcp-server --port 8000</p>
            <p class="c-line success">✓ MCP Server successfully initialized on port 8000/mcp</p>
            <p class="c-line">✓ Tools exposed: [get_available_rooms, create_booking, confirm_booking_payment, cancel_booking]</p>
            <p class="c-line info">ℹ Ready to accept natural language actions from LLM Agents.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Core Features Grid -->
    <div class="features-section">
      <h2 class="section-title">核心设计架构</h2>
      <el-row :gutter="24" class="features-row">
        <el-col :xs="24" :sm="12" :md="6" class="col-feature">
          <div class="feature-card glass-panel glass-panel-hover">
            <el-icon class="f-icon purple"><Cpu /></el-icon>
            <h3>双模接口发布</h3>
            <p>基于 FastAPI-MCP 双模架构，提供人类 GUI 控制台的同时，自动向 AI 客户端暴露结构化 Tool 集合。</p>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" class="col-feature">
          <div class="feature-card glass-panel glass-panel-hover">
            <el-icon class="f-icon blue"><Timer /></el-icon>
            <h3>两阶段锁房机制</h3>
            <p>预订启动 Hold 机制锁定房态，提供 15 分钟的支付缓冲。超时后台任务静默自动回滚释放库存。</p>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" class="col-feature">
          <div class="feature-card glass-panel glass-panel-hover">
            <el-icon class="f-icon orange"><Lock /></el-icon>
            <h3>并发安全隔离</h3>
            <p>采用 MySQL 悲观锁（SELECT FOR UPDATE NOWAIT）实现防雪崩抢购隔离，保障库存精确一致。</p>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" class="col-feature">
          <div class="feature-card glass-panel glass-panel-hover">
            <el-icon class="f-icon green"><Calendar /></el-icon>
            <h3>每日房态库存</h3>
            <p>基于日期区间的前闭后开库存检索体系，轻松应对跨月、长周期酒店客房销售与精准占用计算。</p>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- AI Agent Sandbox (Simulator) & MCP Guide -->
    <el-row :gutter="24" class="sandbox-section">
      <!-- AI Simulator -->
      <el-col :xs="24" :md="14" class="sandbox-col">
        <div class="sandbox-card glass-panel">
          <div class="card-header-with-icon">
            <el-icon class="header-icon"><ChatLineRound /></el-icon>
            <div>
              <h3>AI Agent 订房模拟沙箱</h3>
              <p class="subtitle">模拟 AI 助手读取您的自然语言要求，并直接操作后端接口</p>
            </div>
          </div>

          <div class="simulator-chat-box">
            <div v-if="simSteps.length === 0" class="chat-placeholder">
              <el-icon :size="40"><InfoFilled /></el-icon>
              <p>在此输入订房需求（支持日期解析），AI 会直接帮您调用后端锁房！</p>
            </div>
            
            <div v-else class="chat-messages">
              <div 
                v-for="(step, idx) in simSteps" 
                :key="idx" 
                :class="['chat-bubble', step.type]"
              >
                <div class="bubble-content">
                  <span v-if="step.type === 'user'" class="avatar">👤</span>
                  <span v-if="step.type === 'agent'" class="avatar">🤖</span>
                  <span v-if="step.type === 'system'" class="avatar">⚙️</span>
                  <div class="msg-text">
                    <span v-if="step.type === 'system'" class="system-log">{{ step.text }}</span>
                    <p v-else style="white-space: pre-wrap;">{{ step.text }}</p>
                    
                    <div v-if="step.action" class="bubble-action">
                      <el-button type="primary" size="small" @click="step.action.handler">
                        {{ step.action.text }}
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="simulator-input-area">
            <el-input
              v-model="aiInput"
              placeholder="请输入您的订房意图..."
              :disabled="simulating"
              @keyup.enter="runAiSimulation"
              class="ai-input"
            >
              <template #append>
                <el-button :loading="simulating" @click="runAiSimulation">
                  <el-icon><Promotion /></el-icon> 解析并执行
                </el-button>
              </template>
            </el-input>
          </div>
        </div>
      </el-col>

      <!-- MCP Configuration Guide -->
      <el-col :xs="24" :md="10" class="sandbox-col">
        <div class="guide-card glass-panel">
          <div class="card-header-with-icon">
            <el-icon class="header-icon"><Cpu /></el-icon>
            <div>
              <h3>智能体 (MCP) 接入配置</h3>
              <p class="subtitle">将本系统作为工具挂载给您的 Claude Desktop 或 Cursor</p>
            </div>
          </div>
          
          <div class="guide-content">
            <p class="step-desc">
              在本地编辑器或客户端配置文件中加入以下 JSON 配置项。即可直接在对话框中用自然语言对本系统发起真实客房查询与预订：
            </p>
            <pre class="code-block"><code>{{ mcpConfigCode }}</code></pre>
            <div class="tips-box">
              <el-icon><InfoFilled /></el-icon>
              <span>通过将本节点加入配置，大语言模型可直接将您的语句转换成底层高并发 SQL 持久化事务。</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.home-page {
  padding: 24px 0 48px;
}

/* Hero Section */
.hero-section {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 40px;
  padding: 48px 40px;
  background: radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.08) 0%, rgba(255, 255, 255, 0.4) 90%);
  border-radius: var(--radius-lg);
  align-items: center;
  margin-bottom: 56px;
}

@media (max-width: 992px) {
  .hero-section {
    grid-template-columns: 1fr;
    padding: 36px 24px;
    gap: 32px;
  }
}

.hero-content {
  display: flex;
  flex-direction: column;
}

.hero-title {
  font-size: 44px;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #1e1b4b, #312e81, #4f46e5);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 36px;
}

.hero-actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.glow-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  box-shadow: 0 8px 20px -4px rgba(99, 102, 241, 0.4);
  transition: all 0.3s;
}

.glow-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px -3px rgba(99, 102, 241, 0.5);
}

.outline-btn {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--card-border);
  font-weight: 500;
  color: var(--text-secondary);
}

.outline-btn:hover {
  background: rgba(255, 255, 255, 0.8);
  color: var(--primary-color);
  border-color: var(--primary-color);
}

/* Console card */
.visual-card {
  background: #020617;
  border-radius: var(--radius-md);
  box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  position: relative;
}

.card-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100px;
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.15) 0%, transparent 100%);
  pointer-events: none;
}

.console-header {
  height: 36px;
  background: #0f172a;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.console-header .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.console-header .dot.red { background: #ef4444; }
.console-header .dot.yellow { background: #f59e0b; }
.console-header .dot.green { background: #10b981; }

.console-header .title {
  color: #64748b;
  font-size: 11px;
  font-family: monospace;
  margin-left: 8px;
}

.console-body {
  padding: 20px;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #cbd5e1;
  min-height: 180px;
}

.c-prompt {
  color: var(--primary-color);
  font-weight: bold;
}

.c-line {
  margin-bottom: 8px;
}

.c-line.success { color: #10b981; }
.c-line.info { color: #38bdf8; }

/* Features Grid */
.features-section {
  margin-bottom: 56px;
}

.section-title {
  text-align: center;
  font-size: 28px;
  margin-bottom: 36px;
  position: relative;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 3px;
  background: var(--accent-gradient);
  border-radius: 2px;
}

.features-row {
  margin-bottom: -24px;
}

.col-feature {
  margin-bottom: 24px;
}

.feature-card {
  padding: 32px 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  background: rgba(255, 255, 255, 0.4);
}

.f-icon {
  font-size: 32px;
  padding: 12px;
  border-radius: var(--radius-md);
  margin-bottom: 20px;
}

.f-icon.purple { background: #f5f3ff; color: #8b5cf6; }
.f-icon.blue { background: #eff6ff; color: #3b82f6; }
.f-icon.orange { background: #fff7ed; color: #f97316; }
.f-icon.green { background: #ecfdf5; color: #10b981; }

.feature-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 10px;
}

.feature-card p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* Sandbox & Guide */
.sandbox-section {
  margin-bottom: 24px;
}

.sandbox-col {
  margin-bottom: 24px;
}

.sandbox-card, .guide-card {
  padding: 32px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.55);
}

.card-header-with-icon {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
}

.header-icon {
  font-size: 24px;
  color: var(--primary-color);
  background: var(--primary-light);
  padding: 10px;
  border-radius: var(--radius-sm);
}

.card-header-with-icon h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.card-header-with-icon .subtitle {
  font-size: 13px;
  color: var(--text-secondary);
}

.simulator-chat-box {
  flex: 1;
  background: rgba(15, 23, 42, 0.03);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);
  min-height: 260px;
  max-height: 320px;
  overflow-y: auto;
  padding: 16px;
  margin-bottom: 16px;
}

.chat-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  text-align: center;
  gap: 12px;
}

.chat-placeholder p {
  font-size: 13px;
  max-width: 240px;
  line-height: 1.4;
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chat-bubble {
  display: flex;
  max-width: 85%;
}

.chat-bubble.user {
  align-self: flex-end;
}

.chat-bubble.agent, .chat-bubble.system {
  align-self: flex-start;
}

.bubble-content {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.chat-bubble.user .bubble-content {
  flex-direction: row-reverse;
}

.chat-bubble .avatar {
  font-size: 18px;
  padding: 6px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
}

.msg-text {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  line-height: 1.5;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.chat-bubble.user .msg-text {
  background: var(--primary-color);
  color: #fff;
  border-top-right-radius: 2px;
}

.chat-bubble.agent .msg-text {
  background: #fff;
  color: var(--text-primary);
  border-top-left-radius: 2px;
  border: 1px solid var(--card-border);
}

.chat-bubble.system .msg-text {
  background: transparent;
  color: var(--text-secondary);
  box-shadow: none;
  padding: 4px 8px;
}

.system-log {
  font-family: monospace;
  font-size: 11px;
  color: var(--text-muted);
}

.bubble-action {
  margin-top: 10px;
}

.simulator-input-area :deep(.el-input-group__append) {
  background-color: var(--primary-color);
  color: #fff;
  border: none;
  font-weight: 600;
  cursor: pointer;
  padding: 0 20px;
}

.simulator-input-area :deep(.el-input-group__append:hover) {
  background-color: var(--primary-hover);
}

.ai-input :deep(.el-input__wrapper) {
  box-shadow: none !important;
  border: 1px solid var(--card-border);
  border-right: none;
}

/* Guide Content */
.guide-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}

.step-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.code-block {
  background: #0f172a;
  color: #cbd5e1;
  padding: 16px;
  border-radius: var(--radius-md);
  font-family: monospace;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  border: 1px solid rgba(255, 255, 255, 0.05);
  max-height: 200px;
}

.tips-box {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  padding: 12px;
  border-radius: var(--radius-sm);
  color: #15803d;
  font-size: 12px;
  line-height: 1.4;
}

.tips-box .el-icon {
  margin-top: 2px;
  font-size: 14px;
}
</style>
