<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import { User, Search, Refresh, Timer, Wallet, CircleCheck } from '@element-plus/icons-vue'

interface Room {
  id: number
  room_number: string
  room_type_id: number
  status: string
  room_type: {
    id: number
    name: string
    base_price: string
    capacity: number
  }
}

interface Booking {
  id: number
  room_id: number
  check_in: string
  check_out: string
  total_price: string
  status: string
  created_at: string
}

const router = useRouter()
const auth = useAuthStore()
const rooms = ref<Room[]>([])
const loading = ref(false)
const bookingLoading = ref(false)

const searchForm = ref({
  check_in: '',
  check_out: '',
  room_type_id: undefined as number | undefined,
})

// Booking Hold Dialog state
const holdDialogVisible = ref(false)
const currentBooking = ref<Booking | null>(null)
const currentRoom = ref<Room | null>(null)
const countdownSeconds = ref(900) // 15 minutes
let countdownInterval: any = null

// Payment Screen state
const paying = ref(false)
const paySuccess = ref(false)

// Get unique room types for the dropdown
const roomTypes = computed(() => {
  const typesMap = new Map<number, { id: number; name: string }>()
  rooms.value.forEach(room => {
    if (room.room_type && !typesMap.has(room.room_type.id)) {
      typesMap.set(room.room_type.id, {
        id: room.room_type.id,
        name: room.room_type.name,
      })
    }
  })
  return Array.from(typesMap.values())
})

onMounted(loadAllRooms)

async function loadAllRooms() {
  loading.value = true
  try {
    const { data } = await api.get<Room[]>('/rooms')
    rooms.value = data
  } catch {
    ElMessage.error('加载客房失败')
  } finally {
    loading.value = false
  }
}

async function searchRooms() {
  if (!searchForm.value.check_in || !searchForm.value.check_out) {
    ElMessage.warning('请选择入住和退房日期')
    return
  }
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      check_in: searchForm.value.check_in,
      check_out: searchForm.value.check_out,
    }
    if (searchForm.value.room_type_id) {
      params.room_type_id = searchForm.value.room_type_id
    }
    const { data } = await api.get<Room[]>('/rooms/search', { params })
    rooms.value = data
    if (data.length === 0) ElMessage.info('该日期段暂无可用客房')
  } catch {
    ElMessage.error('搜索可用客房失败，请重试')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  searchForm.value.check_in = ''
  searchForm.value.check_out = ''
  searchForm.value.room_type_id = undefined
  loadAllRooms()
}

async function bookRoom(room: Room) {
  if (!auth.user) {
    ElMessage.warning('请先登录您的账户')
    router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  if (!searchForm.value.check_in || !searchForm.value.check_out) {
    ElMessage.warning('请先选择入住和退房日期')
    return
  }
  
  bookingLoading.value = true
  try {
    const { data } = await api.post<Booking>('/bookings', {
      room_id: room.id,
      check_in: searchForm.value.check_in,
      check_out: searchForm.value.check_out,
    })
    
    // Setup dialog
    currentBooking.value = data
    currentRoom.value = room
    paySuccess.value = false
    paying.value = false
    
    // Hold timer (15 minutes from now)
    countdownSeconds.value = 900
    startHoldTimer()
    
    holdDialogVisible.value = true
    ElMessage.success(`房间 ${room.room_number} 已成功提交，已为您锁房 15 分钟！`)
  } catch (err: any) {
    const msg = err.response?.data?.detail || '预订锁房失败，可能已被占用或时间段冲突'
    ElMessage.error(msg)
  } finally {
    bookingLoading.value = false
  }
}

function startHoldTimer() {
  if (countdownInterval) clearInterval(countdownInterval)
  countdownInterval = setInterval(() => {
    if (countdownSeconds.value > 0) {
      countdownSeconds.value--
    } else {
      clearInterval(countdownInterval)
      ElMessage.warning('锁定超时，锁定资源已释放，请重新创建预订')
      holdDialogVisible.value = false
    }
  }, 1000)
}

const formattedCountdown = computed(() => {
  const mins = Math.floor(countdownSeconds.value / 60)
  const secs = countdownSeconds.value % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
})

async function handleConfirmPayment() {
  if (!currentBooking.value) return
  paying.value = true
  try {
    await api.post(`/bookings/${currentBooking.value.id}/pay`)
    paySuccess.value = true
    if (countdownInterval) clearInterval(countdownInterval)
    ElMessage.success('模拟支付成功，订单已确认！')
  } catch (err: any) {
    const msg = err.response?.data?.detail || '支付失败，订单可能已被释放'
    ElMessage.error(msg)
  } finally {
    paying.value = false
  }
}

function closeHoldDialog() {
  holdDialogVisible.value = false
  if (countdownInterval) clearInterval(countdownInterval)
  router.push('/bookings')
}

// Generate stylized card visual based on room type name
function getRoomTypeColor(typeName: string) {
  if (typeName.includes('Suite') || typeName.includes('套房')) {
    return 'linear-gradient(135deg, #a855f7 0%, #1e1b4b 100%)' // purple dark
  } else if (typeName.includes('Double') || typeName.includes('大床')) {
    return 'linear-gradient(135deg, #6366f1 0%, #312e81 100%)' // indigo dark
  } else {
    return 'linear-gradient(135deg, #14b8a6 0%, #115e59 100%)' // teal dark
  }
}
</script>

<template>
  <div class="rooms-page-wrapper">
    <!-- Top banner / header -->
    <div class="rooms-header-banner">
      <h2>客房预订空间</h2>
      <p>选择理想的下榻日期，寻找适合您的奢华或尊贵房型</p>
    </div>

    <!-- Search workspace -->
    <div class="search-panel glass-panel">
      <el-form :inline="true" :model="searchForm" class="search-form-layout">
        <el-form-item label="入住时间">
          <el-date-picker 
            v-model="searchForm.check_in" 
            type="date" 
            value-format="YYYY-MM-DD" 
            placeholder="请选择入住日期" 
            size="large"
            class="full-date-picker"
          />
        </el-form-item>
        <el-form-item label="退房时间">
          <el-date-picker 
            v-model="searchForm.check_out" 
            type="date" 
            value-format="YYYY-MM-DD" 
            placeholder="请选择退房日期" 
            size="large"
            class="full-date-picker"
          />
        </el-form-item>
        <el-form-item label="客房类型">
          <el-select 
            v-model="searchForm.room_type_id" 
            placeholder="所有房型" 
            clearable 
            size="large"
            style="width: 180px"
          >
            <el-option 
              v-for="item in roomTypes" 
              :key="item.id" 
              :label="item.name" 
              :value="item.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item class="actions-item">
          <el-button type="primary" size="large" class="search-btn" :loading="loading" @click="searchRooms">
            <el-icon><Search /></el-icon> 搜索可用房态
          </el-button>
          <el-button size="large" class="reset-btn" @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- Room Cards Grid -->
    <div v-loading="loading" class="rooms-grid-container">
      <el-row :gutter="24" v-if="rooms.length > 0">
        <el-col 
          v-for="room in rooms" 
          :key="room.id" 
          :xs="24" 
          :sm="12" 
          :md="8" 
          :lg="6" 
          class="room-card-col"
        >
          <div class="room-card-wrapper glass-panel glass-panel-hover">
            <!-- Room Image visual placeholder -->
            <div class="room-thumbnail" :style="{ background: getRoomTypeColor(room.room_type?.name || '') }">
              <span class="room-number-tag">NO.{{ room.room_number }}</span>
              <div class="room-avatar-center">
                <el-icon :size="48" style="color: rgba(255,255,255,0.7)"><House /></el-icon>
              </div>
            </div>
            
            <div class="room-info-body">
              <div class="room-type-row">
                <span class="room-type-title">{{ room.room_type?.name ?? '标准客房' }}</span>
                <el-tag size="small" :type="room.status === 'active' ? 'success' : 'info'">
                  {{ room.status === 'active' ? '营业中' : '维护中' }}
                </el-tag>
              </div>
              
              <div class="room-stats-row">
                <div class="stat-item">
                  <el-icon><User /></el-icon>
                  <span>最多容纳 {{ room.room_type?.capacity ?? 2 }} 人</span>
                </div>
              </div>
              
              <div class="room-footer-row">
                <div class="room-price">
                  <span class="price-val">¥{{ room.room_type?.base_price ?? '0.00' }}</span>
                  <span class="price-unit">/ 晚</span>
                </div>
                <el-button 
                  type="primary" 
                  class="book-action-btn"
                  :disabled="room.status !== 'active'"
                  @click="bookRoom(room)"
                >
                  立即预订
                </el-button>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
      
      <div v-else class="empty-state-wrapper glass-panel">
        <el-empty description="此日期段或筛选条件下无空闲客房" />
      </div>
    </div>

    <!-- Booking Hold Modal Dialog -->
    <el-dialog
      v-model="holdDialogVisible"
      title="订单锁定与支付确认"
      width="480px"
      :before-close="closeHoldDialog"
      align-center
      class="hold-booking-dialog"
    >
      <div v-if="currentBooking && currentRoom" class="dialog-body-holder">
        
        <!-- Payment Success View -->
        <div v-if="paySuccess" class="payment-success-screen animate-fade-in">
          <el-icon class="success-icon" :size="72" color="#10b981"><CircleCheck /></el-icon>
          <h3>订单支付成功</h3>
          <p>恭喜，您已成功确认入住预订，房态已锁定！</p>
          <div class="summary-details shadow-sm">
            <div class="s-row"><span>订单编号</span><span>#{{ currentBooking.id }}</span></div>
            <div class="s-row"><span>预订房间</span><span>{{ currentRoom.room_number }} ({{ currentRoom.room_type.name }})</span></div>
            <div class="s-row"><span>入住日期</span><span>{{ currentBooking.check_in }}</span></div>
            <div class="s-row"><span>退房日期</span><span>{{ currentBooking.check_out }}</span></div>
            <div class="s-row highlight"><span>实付总价</span><span>¥{{ currentBooking.total_price }}</span></div>
          </div>
          <el-button type="primary" size="large" class="w-full mt-4" @click="closeHoldDialog">
            完成，进入我的订单
          </el-button>
        </div>

        <!-- Timer / Payment Form View -->
        <div v-else class="booking-hold-screen">
          <div class="timer-badge">
            <el-icon><Timer /></el-icon>
            <span class="time-text">{{ formattedCountdown }}</span>
          </div>
          <p class="hold-notice">
            系统已激活 <strong>Hold 房态锁定</strong>。客房库存已为您专属保留 15 分钟，请在倒计时结束前完成模拟付款，否则订单将被系统自动取消。
          </p>

          <div class="summary-details">
            <div class="s-row"><span>房间分配</span><span>Room {{ currentRoom.room_number }}</span></div>
            <div class="s-row"><span>房间类型</span><span>{{ currentRoom.room_type.name }}</span></div>
            <div class="s-row"><span>入住时间</span><span>{{ currentBooking.check_in }}</span></div>
            <div class="s-row"><span>退房时间</span><span>{{ currentBooking.check_out }}</span></div>
            <div class="s-row highlight"><span>应付总价</span><span>¥{{ currentBooking.total_price }}</span></div>
          </div>

          <div class="payment-actions">
            <el-button 
              type="primary" 
              size="large" 
              class="pay-btn" 
              :loading="paying" 
              @click="handleConfirmPayment"
            >
              <el-icon><Wallet /></el-icon> 确认模拟支付
            </el-button>
            <el-button size="large" class="cancel-btn" @click="closeHoldDialog">
              稍后付款
            </el-button>
          </div>
        </div>

      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.rooms-page-wrapper {
  padding: 12px 0 48px;
}

.rooms-header-banner {
  margin-bottom: 32px;
}

.rooms-header-banner h2 {
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 6px;
}

.rooms-header-banner p {
  font-size: 14px;
  color: var(--text-secondary);
}

/* Search panel */
.search-panel {
  padding: 24px;
  background: rgba(255, 255, 255, 0.7);
  margin-bottom: 40px;
}

.search-form-layout {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 20px;
}

.search-form-layout :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.search-form-layout :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
  justify-content: flex-start;
}

.full-date-picker {
  width: 200px !important;
}

.actions-item {
  align-self: flex-end;
}

.search-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 12px -3px rgba(99, 102, 241, 0.3);
}

.search-btn:hover {
  opacity: 0.95;
  transform: translateY(-1px);
}

.reset-btn {
  background: transparent;
  border: 1px solid var(--card-border);
  color: var(--text-secondary);
}

.reset-btn:hover {
  background: rgba(0, 0, 0, 0.02);
  color: var(--primary-color);
  border-color: var(--primary-color);
}

/* Room card col */
.room-card-col {
  margin-bottom: 24px;
}

.room-card-wrapper {
  background: rgba(255, 255, 255, 0.6);
  border-radius: var(--radius-md) !important;
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.room-thumbnail {
  height: 160px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.room-number-tag {
  position: absolute;
  top: 12px;
  left: 12px;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  font-family: monospace;
  font-weight: 600;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 20px;
  backdrop-filter: blur(4px);
}

.room-avatar-center {
  padding: 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  backdrop-filter: blur(8px);
}

.room-info-body {
  padding: 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 16px;
}

.room-type-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.room-type-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.room-stats-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.room-footer-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--card-border);
  padding-top: 16px;
  margin-top: 4px;
}

.room-price {
  display: flex;
  align-items: baseline;
}

.price-val {
  font-size: 20px;
  font-weight: 800;
  color: var(--primary-color);
  font-family: var(--font-title);
}

.price-unit {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 2px;
}

.book-action-btn {
  font-weight: 600;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
}

.empty-state-wrapper {
  padding: 56px;
  background: rgba(255, 255, 255, 0.4);
}

/* Hold Booking Dialog */
.hold-booking-dialog :deep(.el-dialog) {
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--card-border);
  box-shadow: 0 30px 60px -15px rgba(0, 0, 0, 0.15);
}

.dialog-body-holder {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.timer-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #ef4444;
  padding: 8px 16px;
  border-radius: 20px;
  margin-bottom: 16px;
}

.timer-badge .time-text {
  font-size: 20px;
  font-weight: 700;
  font-family: monospace;
}

.hold-notice {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 24px;
  padding: 0 16px;
}

.summary-details {
  width: 100%;
  background: #f8fafc;
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 24px;
  border: 1px solid var(--card-border);
}

.s-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.s-row:last-child {
  margin-bottom: 0;
}

.s-row.highlight {
  border-top: 1px solid var(--card-border);
  padding-top: 10px;
  margin-top: 10px;
  font-weight: 700;
  color: var(--text-primary);
  font-size: 15px;
}

.s-row.highlight span:last-child {
  color: var(--primary-color);
}

.payment-actions {
  display: flex;
  gap: 12px;
  width: 100%;
}

.pay-btn {
  flex: 1.3;
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 12px -3px rgba(99, 102, 241, 0.4);
}

.pay-btn:hover {
  opacity: 0.95;
}

.cancel-btn {
  flex: 0.7;
  background: transparent;
  border: 1px solid var(--card-border);
  color: var(--text-secondary);
}

/* Success screen */
.payment-success-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.success-icon {
  margin-bottom: 16px;
  filter: drop-shadow(0 4px 12px rgba(16, 185, 129, 0.2));
}

.payment-success-screen h3 {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--text-primary);
}

.payment-success-screen p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.w-full {
  width: 100%;
}
.mt-4 {
  margin-top: 16px;
}
</style>
