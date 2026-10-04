<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { streamAgentChat, type ChatMessage } from '@/api/agent'

interface ToolStep {
  name: string
  label: string
  status: 'running' | 'done'
  summary: string
}

interface DisplayMessage {
  role: 'user' | 'assistant'
  content: string
  tools: ToolStep[]
  error: boolean
}

const TOOL_LABELS: Record<string, string> = {
  search_available_rooms: '查询可用客房',
  create_booking: '创建预订',
  list_my_bookings: '查询我的订单',
  confirm_payment: '支付确认',
  cancel_booking: '取消订单',
  admin_list_bookings: '查询全部订单',
  admin_confirm_booking: '确认订单',
  admin_check_in_booking: '办理入住',
  admin_check_out_booking: '办理退房',
  admin_list_rooms: '查询客房',
  admin_create_room: '新增客房',
  admin_update_room: '更新客房',
  admin_list_room_types: '查询房型',
  admin_create_room_type: '新增房型',
  admin_update_room_type: '更新房型',
  admin_list_users: '查询用户',
  admin_disable_user: '禁用用户',
}

const QUICK_PROMPTS = [
  '帮我查一下明天的空房',
  '我想预订一间大床房',
  '查看我的订单',
]

const router = useRouter()
const auth = useAuthStore()

const messages = ref<DisplayMessage[]>([])
const input = ref('')
const loading = ref(false)
const chatBody = ref<HTMLElement | null>(null)
let abortController: AbortController | null = null

function scrollToBottom() {
  nextTick(() => {
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  })
}

function summarizeResult(result: string): string {
  try {
    const data = JSON.parse(result)
    if (data.error) return String(data.error)
    if (Array.isArray(data.rooms)) {
      return data.rooms.length ? `找到 ${data.rooms.length} 间客房` : '暂无客房'
    }
    if (Array.isArray(data.bookings)) {
      return data.bookings.length ? `共 ${data.bookings.length} 笔订单` : '暂无订单'
    }
    if (Array.isArray(data.room_types)) {
      return data.room_types.length ? `共 ${data.room_types.length} 个房型` : '暂无房型'
    }
    if (Array.isArray(data.users)) {
      return data.users.length ? `共 ${data.users.length} 个用户` : '暂无用户'
    }
    if (data.message) return String(data.message)
    if (data.booking_id !== undefined) return `订单 #${data.booking_id}（${data.status ?? ''}）`
    return '完成'
  } catch {
    return '完成'
  }
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  input.value = ''

  const history: ChatMessage[] = messages.value
    .filter((m) => m.content)
    .map((m) => ({ role: m.role, content: m.content }))
  history.push({ role: 'user', content: text })

  messages.value.push({ role: 'user', content: text, tools: [], error: false })
  const assistantMsg: DisplayMessage = { role: 'assistant', content: '', tools: [], error: false }
  messages.value.push(assistantMsg)
  scrollToBottom()

  loading.value = true
  abortController = new AbortController()

  try {
    await streamAgentChat(
      history,
      (event) => {
        if (event.type === 'text') {
          assistantMsg.content += event.content
        } else if (event.type === 'tool_call') {
          assistantMsg.tools.push({
            name: event.name,
            label: TOOL_LABELS[event.name] ?? event.name,
            status: 'running',
            summary: '',
          })
        } else if (event.type === 'tool_result') {
          const running = assistantMsg.tools.find((t) => t.status === 'running')
          if (running) {
            running.status = 'done'
            running.summary = summarizeResult(event.result)
          }
        } else if (event.type === 'error') {
          assistantMsg.error = true
          assistantMsg.content = assistantMsg.content
            ? `${assistantMsg.content}\n\n${event.message}`
            : event.message
        }
        scrollToBottom()
      },
      abortController.signal,
    )
  } catch (err) {
    if (abortController?.signal.aborted) return
    assistantMsg.error = true
    const reason = err instanceof Error ? err.message : '请求失败'
    assistantMsg.content = assistantMsg.content ? `${assistantMsg.content}\n\n${reason}` : reason
  } finally {
    loading.value = false
    for (const tool of assistantMsg.tools) {
      if (tool.status === 'running') tool.status = 'done'
    }
    abortController = null
    scrollToBottom()
  }
}

function stop() {
  abortController?.abort()
}

function clearChat() {
  if (loading.value) return
  messages.value = []
}

function usePrompt(prompt: string) {
  input.value = prompt
  send()
}
</script>

<template>
  <div class="agent">
    <header class="agent__header">
      <div>
        <h1 class="agent__title">智能助手</h1>
        <p class="agent__subtitle">用自然语言预订客房、查询订单，AI 助手替您执行操作</p>
      </div>
      <el-button text @click="clearChat" :disabled="messages.length === 0">清空对话</el-button>
    </header>

    <div class="chat">
      <div ref="chatBody" class="chat__body">
        <div v-if="!auth.user" class="chat__notice">
          <span>未登录状态下仅可查询客房；预订、订单等操作需先登录。</span>
          <el-button text type="primary" @click="router.push('/login')">去登录</el-button>
        </div>

        <div v-if="messages.length === 0" class="chat__empty">
          <div class="chat__empty-mark">
            <el-icon :size="28"><ChatDotRound /></el-icon>
          </div>
          <p class="chat__empty-title">您好，我是 AetherStay 智能助手</p>
          <p class="chat__empty-desc">试试下面这些，或直接说出您的需求</p>
          <div class="chat__presets">
            <button
              v-for="prompt in QUICK_PROMPTS"
              :key="prompt"
              type="button"
              class="chat__preset"
              @click="usePrompt(prompt)"
            >
              {{ prompt }}
            </button>
          </div>
        </div>

        <div v-for="(msg, i) in messages" :key="i" class="msg" :class="`msg--${msg.role}`">
          <div class="msg__bubble">
            <div v-if="msg.tools.length" class="msg__tools">
              <span
                v-for="(tool, j) in msg.tools"
                :key="j"
                class="tool-chip"
                :class="{ 'is-done': tool.status === 'done' }"
              >
                <el-icon v-if="tool.status === 'running'" class="tool-chip__icon spin"><Loading /></el-icon>
                <el-icon v-else class="tool-chip__icon"><CircleCheck /></el-icon>
                <span class="tool-chip__label">{{ tool.label }}</span>
                <span v-if="tool.summary" class="tool-chip__summary">{{ tool.summary }}</span>
              </span>
            </div>
            <p v-if="msg.content" class="msg__text">{{ msg.content }}</p>
            <p v-else-if="msg.role === 'assistant' && loading" class="msg__thinking">
              正在思考<span class="dots"><i>.</i><i>.</i><i>.</i></span>
            </p>
          </div>
        </div>
      </div>

      <footer class="chat__footer">
        <div class="chat__input">
          <textarea
            v-model="input"
            class="chat__textarea"
            rows="1"
            placeholder="输入您的需求，例如：帮我查一下明晚到后晚的空房"
            :disabled="loading"
            @keydown.enter.exact.prevent="send"
          ></textarea>
          <el-button
            v-if="loading"
            class="chat__send"
            type="primary"
            @click="stop"
          >
            停止
          </el-button>
          <el-button
            v-else
            class="chat__send"
            type="primary"
            :disabled="!input.trim()"
            @click="send"
          >
            发送
          </el-button>
        </div>
        <p class="chat__hint">Enter 发送，Shift + Enter 换行</p>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.agent {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: calc(100vh - var(--header-h) - 80px);
  min-height: 480px;
}

.agent__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.agent__title {
  font-size: 24px;
}

.agent__subtitle {
  margin-top: 4px;
  font-size: 14px;
  color: var(--text-secondary);
}

.chat {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.chat__body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.chat__notice {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  background: var(--brand-50);
  color: var(--brand-800);
  font-size: 13px;
}

.chat__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0 24px;
  text-align: center;
}

.chat__empty-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-full);
  background: var(--brand-50);
  color: var(--brand-600);
}

.chat__empty-title {
  margin-top: 16px;
  font-size: 16px;
  font-weight: 600;
}

.chat__empty-desc {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.chat__presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 20px;
  justify-content: center;
}

.chat__preset {
  padding: 8px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.chat__preset:hover {
  border-color: var(--brand-400);
  color: var(--brand-700);
}

.msg {
  display: flex;
  margin-bottom: 16px;
}

.msg--user {
  justify-content: flex-end;
}

.msg--assistant {
  justify-content: flex-start;
}

.msg__bubble {
  max-width: 76%;
}

.msg--user .msg__bubble {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  border-bottom-right-radius: 4px;
  background: var(--brand-600);
  color: #ffffff;
}

.msg--assistant .msg__bubble {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  border-bottom-left-radius: 4px;
  background: var(--gray-100);
}

.msg__tools {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.tool-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  font-size: 12px;
  color: var(--text-secondary);
}

.tool-chip.is-done .tool-chip__icon {
  color: var(--brand-600);
}

.tool-chip__summary {
  color: var(--text-tertiary);
}

.spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.msg__text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  color: var(--text-primary);
}

.msg--user .msg__text {
  color: #ffffff;
}

.msg__thinking {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--text-secondary);
}

.dots i {
  font-style: normal;
  animation: blink 1.2s infinite;
}

.dots i:nth-child(2) {
  animation-delay: 0.2s;
}

.dots i:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes blink {
  0%,
  100% {
    opacity: 0.2;
  }
  50% {
    opacity: 1;
  }
}

.chat__footer {
  padding: 12px 16px 10px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.chat__input {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast);
}

.chat__input:focus-within {
  border-color: var(--brand-500);
}

.chat__textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  max-height: 120px;
  background: transparent;
  font: inherit;
  color: var(--text-primary);
  line-height: 1.6;
}

.chat__send {
  flex-shrink: 0;
}

.chat__hint {
  margin-top: 8px;
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
}

@media (max-width: 768px) {
  .agent {
    height: calc(100vh - var(--header-h) - 56px);
  }

  .msg__bubble {
    max-width: 88%;
  }

  .chat__body {
    padding: 16px;
  }
}
</style>