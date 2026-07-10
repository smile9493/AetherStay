<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import { Timer, Wallet, CircleClose, List, ArrowRight, InfoFilled, Search } from '@element-plus/icons-vue'

interface Booking {
  id: number
  room_id: number
  check_in: string
  check_out: string
  total_price: string
  status: string
  created_at: string
  held_until?: string | null
  room?: { 
    room_number: string; 
    room_type?: { id: number; name: string; capacity: number; image_url?: string } 
  }
}

const router = useRouter()
const auth = useAuthStore()
const bookings = ref<Booking[]>([])
const loading = ref(false)

// Active Tab Filter
const activeTab = ref('all')

// Timer countdown tracking
const nowTime = ref(Date.now())
let tickerInterval: any = null

// Payment Modal state
const payDialogVisible = ref(false)
const payingBooking = ref<Booking | null>(null)
const paying = ref(false)

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchUser()
    if (!auth.user) {
      router.push('/login')
      return
    }
  }
  await loadBookings()
  
  // Start ticks to refresh countdowns every second
  tickerInterval = setInterval(() => {
    nowTime.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (tickerInterval) clearInterval(tickerInterval)
})

async function loadBookings() {
  loading.value = true
  try {
    const { data } = await api.get<Booking[]>('/bookings/my')
    bookings.value = data
  } catch {
    ElMessage.error('加载订单失败')
  } finally {
    loading.value = false
  }
}

async function cancelBooking(id: number) {
  try {
    await ElMessageBox.confirm('确定要取消此房间预订吗？取消后库存将立即释放。', '确认取消', { 
      type: 'warning',
      confirmButtonText: '确定取消',
      cancelButtonText: '暂不取消',
      confirmButtonClass: 'el-button--danger'
    })
    await api.post(`/bookings/${id}/cancel`)
    ElMessage.success('订单已成功取消')
    loadBookings()
  } catch {
    // dismissed
  }
}

// Re-book shortcut
function reBook(booking: Booking) {
  const roomTypeId = booking.room?.room_type?.id
  if (!roomTypeId) {
    router.push('/rooms')
    return
  }
  router.push({ path: '/rooms', query: { room_type_id: String(roomTypeId) } })
}

// Payment trigger
function openPayDialog(booking: Booking) {
  payingBooking.value = booking
  payDialogVisible.value = true
}

async function handleConfirmPayment() {
  if (!payingBooking.value) return
  paying.value = true
  try {
    await api.post(`/bookings/${payingBooking.value.id}/pay`)
    ElMessage.success('支付成功，订单已确认为 CONFIRMED 状态')
    payDialogVisible.value = false
    loadBookings()
  } catch (err: any) {
    const msg = err.response?.data?.detail || '付款失败，预订锁房可能已超时释放'
    ElMessage.error(msg)
  } finally {
    paying.value = false
  }
}

// Countdown based on server-held_until, fallback to created_at + 15min
function getRemainingSeconds(booking: Booking) {
  let expireTime: number
  if (booking.held_until) {
    expireTime = new Date(booking.held_until).getTime()
  } else {
    const createdTime = new Date(booking.created_at).getTime()
    expireTime = createdTime + 15 * 60 * 1000
  }
  return Math.max(0, Math.floor((expireTime - nowTime.value) / 1000))
}

function getCountdownText(booking: Booking) {
  const seconds = getRemainingSeconds(booking)
  if (seconds <= 0) return '已超时释放'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// Filters bookings based on tab selection
const filteredBookings = computed(() => {
  if (activeTab.value === 'all') return bookings.value
  
  return bookings.value.filter(booking => {
    if (activeTab.value === 'pending') return booking.status === 'pending'
    if (activeTab.value === 'confirmed') return booking.status === 'confirmed'
    if (activeTab.value === 'active') {
      return booking.status === 'checked_in' || booking.status === 'checked_out'
    }
    if (activeTab.value === 'cancelled') return booking.status === 'cancelled'
    return true
  })
})

const statusMap: Record<string, { text: string; type: 'warning' | 'success' | 'primary' | 'info' | 'danger' }> = {
  pending: { text: '待支付锁定', type: 'warning' },
  confirmed: { text: '已支付确认', type: 'success' },
  checked_in: { text: '已办理入住', type: 'primary' },
  checked_out: { text: '已办理退房', type: 'info' },
  cancelled: { text: '已取消释放', type: 'danger' },
}
</script>

<template>
  <div class="bookings-page-wrapper">
    <div class="bookings-header">
      <h2>我的订单中心</h2>
      <p>管理您的历史行程预订，完成待支付锁定房间，或取消未使用的预订</p>
    </div>

    <!-- Booking tabs filter -->
    <div class="bookings-tabs-panel glass-panel">
      <el-tabs v-model="activeTab" class="custom-bookings-tabs">
        <el-tab-pane label="全部订单" name="all" />
        <el-tab-pane label="待付款锁定" name="pending" />
        <el-tab-pane label="已付款确认" name="confirmed" />
        <el-tab-pane label="已入住/退房" name="active" />
        <el-tab-pane label="已取消" name="cancelled" />
      </el-tabs>
    </div>

    <!-- Bookings Cards list -->
    <div v-loading="loading" class="bookings-list-container">
      <div v-if="filteredBookings.length > 0" class="cards-stack">
        <div 
          v-for="booking in filteredBookings" 
          :key="booking.id" 
          class="booking-card glass-panel glass-panel-hover"
        >
          <!-- Card Header -->
          <div class="card-top-header">
            <div class="order-id-group">
              <el-icon><List /></el-icon>
              <span class="order-id-lbl">订单号 #{{ booking.id }}</span>
              <span class="order-time-lbl">创建于 {{ new Date(booking.created_at).toLocaleString() }}</span>
            </div>
            
            <div class="status-indicator">
              <el-tag :type="statusMap[booking.status]?.type || 'info'" size="large" class="status-badge">
                {{ statusMap[booking.status]?.text || booking.status }}
              </el-tag>
            </div>
          </div>

          <!-- Card Body details -->
          <div class="card-details-body">
            <div class="room-details-left">
              <div
                class="room-symbol"
                :style="booking.room?.room_type?.image_url
                  ? { backgroundImage: `url(${booking.room.room_type.image_url})`, backgroundSize: 'cover', backgroundPosition: 'center', color: 'transparent' }
                  : {}"
              >
                <span v-if="!booking.room?.room_type?.image_url">{{ booking.room?.room_number ?? booking.room_id }}</span>
              </div>
              <div class="room-text-info">
                <h4>{{ booking.room?.room_type?.name ?? '标准客房' }}</h4>
                <p class="capacity-desc">最多容纳 {{ booking.room?.room_type?.capacity ?? 2 }} 人 | 严禁携带宠物</p>
              </div>
            </div>

            <div class="stay-date-center">
              <div class="date-node">
                <span class="lbl">入住日期</span>
                <span class="val">{{ booking.check_in }}</span>
              </div>
              <el-icon class="arrow-sep"><ArrowRight /></el-icon>
              <div class="date-node">
                <span class="lbl">退房日期</span>
                <span class="val">{{ booking.check_out }}</span>
              </div>
            </div>

            <div class="price-right">
              <span class="lbl">订单总额</span>
              <span class="val">¥{{ booking.total_price }}</span>
            </div>
          </div>

          <!-- Card Footer Actions -->
          <div class="card-actions-footer" v-if="['pending', 'confirmed'].includes(booking.status)">
            <!-- Pending Hold Countdown -->
            <div class="hold-timer-area" v-if="booking.status === 'pending'">
              <template v-if="getRemainingSeconds(booking) > 0">
                <el-icon color="#ef4444"><Timer /></el-icon>
                <span class="timer-warning">
                  锁房倒计时：<strong class="timer-countdown">{{ getCountdownText(booking) }}</strong>
                </span>
              </template>
              <template v-else>
                <el-icon color="#94a3b8"><InfoFilled /></el-icon>
                <span class="timer-expired">资源已锁定超时，刷新后将被释放</span>
              </template>
            </div>
            
            <div class="buttons-area">
              <!-- Pay Button -->
              <el-button 
                v-if="booking.status === 'pending' && getRemainingSeconds(booking) > 0" 
                type="primary" 
                size="default" 
                class="pay-trigger-btn"
                @click="openPayDialog(booking)"
              >
                <el-icon><Wallet /></el-icon> 立即支付
              </el-button>
              
              <!-- Cancel Button -->
              <el-button 
                type="danger" 
                plain
                size="default"
                class="cancel-trigger-btn"
                @click="cancelBooking(booking.id)"
              >
                <el-icon><CircleClose /></el-icon> 取消预订
              </el-button>
            </div>
          </div>

          <!-- Re-book shortcut for finished/cancelled orders -->
          <div class="card-actions-footer" v-else-if="['checked_out', 'cancelled'].includes(booking.status)">
            <div class="hold-timer-area">
              <el-icon color="#94a3b8"><InfoFilled /></el-icon>
              <span class="timer-expired">{{ booking.status === 'checked_out' ? '已完成住宿，期待再次光临' : '该预订已取消' }}</span>
            </div>
            <div class="buttons-area">
              <el-button 
                type="primary"
                size="default"
                class="pay-trigger-btn"
                @click="reBook(booking)"
              >
                <el-icon><Search /></el-icon> 再次预订
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else class="empty-state-wrapper glass-panel">
        <el-empty description="当前暂无该类别下的预订订单" />
      </div>
    </div>

    <!-- Separate Payment Dialog -->
    <el-dialog
      v-model="payDialogVisible"
      title="订单付款"
      width="440px"
      align-center
      class="inline-payment-dialog"
    >
      <div v-if="payingBooking" class="pay-dialog-inner">
        <div class="pay-icon-bg">
          <el-icon :size="36" color="#6366f1"><Wallet /></el-icon>
        </div>
        <h3>确认支付款项</h3>
        <p class="desc">您将通过安全网关为订单 #{{ payingBooking.id }} 模拟支付房费。</p>
        
        <div class="pay-summary">
          <div class="pay-row">
            <span>预订房型</span>
            <span>{{ payingBooking.room?.room_type?.name ?? '标准客房' }}</span>
          </div>
          <div class="pay-row">
            <span>入住天数</span>
            <span>{{ payingBooking.check_in }} 至 {{ payingBooking.check_out }}</span>
          </div>
          <div class="pay-row grand">
            <span>应付总价</span>
            <span>¥{{ payingBooking.total_price }}</span>
          </div>
        </div>

        <div class="dialog-actions mt-4">
          <el-button 
            type="primary" 
            size="large" 
            class="pay-btn" 
            :loading="paying" 
            @click="handleConfirmPayment"
          >
            确认付款
          </el-button>
          <el-button size="large" @click="payDialogVisible = false">
            取消
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.bookings-page-wrapper {
  padding: 12px 0 48px;
}

.bookings-header {
  margin-bottom: 32px;
}

.bookings-header h2 {
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 6px;
}

.bookings-header p {
  font-size: 14px;
  color: var(--text-secondary);
}

/* Tabs panel */
.bookings-tabs-panel {
  padding: 12px 24px;
  background: rgba(255, 255, 255, 0.7);
  margin-bottom: 32px;
}

.custom-bookings-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  border-bottom: none;
}

.custom-bookings-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 0;
}

.custom-bookings-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
  padding: 0 20px;
}

/* Cards Stack */
.cards-stack {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.booking-card {
  background: rgba(255, 255, 255, 0.6);
  border-radius: var(--radius-md) !important;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-top-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--card-border);
  padding-bottom: 16px;
}

.order-id-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.order-id-lbl {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.order-time-lbl {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 8px;
}

.status-badge {
  font-weight: 600;
  border-radius: 6px;
}

/* Card details body */
.card-details-body {
  display: grid;
  grid-template-columns: 1.2fr 1.3fr 0.9fr;
  align-items: center;
  gap: 24px;
}

@media (max-width: 768px) {
  .card-details-body {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

.room-details-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.room-symbol {
  width: 54px;
  height: 54px;
  border-radius: var(--radius-sm);
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  font-family: var(--font-title);
  font-weight: 800;
  font-size: 20px;
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.room-text-info h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.capacity-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

.stay-date-center {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  background: #f8fafc;
  padding: 10px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--card-border);
}

.date-node {
  display: flex;
  flex-direction: column;
  text-align: center;
}

.date-node .lbl {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 2px;
}

.date-node .val {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.arrow-sep {
  color: var(--text-muted);
  font-size: 16px;
}

.price-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.price-right .lbl {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.price-right .val {
  font-size: 22px;
  font-weight: 800;
  color: var(--primary-color);
  font-family: var(--font-title);
}

/* Card Actions Footer */
.card-actions-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fffdf5;
  border: 1px solid #fef3c7;
  padding: 12px 18px;
  border-radius: var(--radius-sm);
  margin-top: 4px;
}

@media (max-width: 600px) {
  .card-actions-footer {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  .buttons-area {
    width: 100%;
    display: flex;
    justify-content: flex-end;
  }
}

.hold-timer-area {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.timer-warning {
  color: #b45309;
}

.timer-countdown {
  font-family: monospace;
  font-size: 15px;
  font-weight: 700;
  color: #ef4444;
}

.timer-expired {
  color: var(--text-muted);
}

.buttons-area {
  display: flex;
  gap: 12px;
}

.pay-trigger-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 10px -2px rgba(99, 102, 241, 0.4);
}

.pay-trigger-btn:hover {
  opacity: 0.95;
}

.cancel-trigger-btn {
  font-weight: 500;
}

.empty-state-wrapper {
  padding: 56px;
  background: rgba(255, 255, 255, 0.4);
}

/* Payment dialog */
.inline-payment-dialog :deep(.el-dialog) {
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--card-border);
}

.pay-dialog-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.pay-icon-bg {
  padding: 16px;
  background: var(--primary-light);
  border-radius: 50%;
  margin-bottom: 16px;
}

.pay-dialog-inner h3 {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 6px;
}

.pay-dialog-inner .desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.pay-summary {
  width: 100%;
  background: #f8fafc;
  border-radius: var(--radius-md);
  padding: 16px;
  border: 1px solid var(--card-border);
  margin-bottom: 8px;
}

.pay-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.pay-row.grand {
  border-top: 1px solid var(--card-border);
  padding-top: 10px;
  margin-top: 10px;
  font-weight: 700;
  color: var(--text-primary);
  font-size: 15px;
}

.pay-row.grand span:last-child {
  color: var(--primary-color);
}

.dialog-actions {
  display: flex;
  gap: 12px;
  width: 100%;
}

.dialog-actions .el-button {
  flex: 1;
}

.dialog-actions .pay-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
}
</style>
