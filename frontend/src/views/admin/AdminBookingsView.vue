<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { Search, Refresh, Calendar, Avatar, Operation, Plus, Edit, Switch } from '@element-plus/icons-vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import { usePagination, type PaginatedResult } from '@/composables/usePagination'
import { handleApiError } from '@/utils/handleError'

interface UserItem {
  id: number
  username: string
}

interface RoomOption {
  id: number
  room_number: string
  room_type?: { name: string; base_price: string }
}

interface Booking {
  id: number
  user_id: number
  room_id: number
  check_in: string
  check_out: string
  total_price: string
  status: string
  notes?: string | null
  created_at: string
  room?: {
    room_number: string
    room_type?: { name: string }
  }
}

interface PaginatedBookings extends PaginatedResult<Booking> {}

const EDITABLE_STATUSES = ['pending', 'confirmed', 'checked_in']

const bookings = ref<Booking[]>([])
const loading = ref(false)
const { currentPage, pageSize, total, pageStart, pageEnd, applyPageResult, resetPage } = usePagination(20)

const filterForm = ref({
  status: '' as string,
  check_in_from: '' as string,
  check_in_to: '' as string,
})

const users = ref<UserItem[]>([])
const availableRooms = ref<RoomOption[]>([])
const roomSearchLoading = ref(false)

const walkInVisible = ref(false)
const walkInSubmitting = ref(false)
const walkInForm = ref({
  user_id: null as number | null,
  check_in: '',
  check_out: '',
  room_id: null as number | null,
  notes: '',
  auto_confirm: true,
})

const editVisible = ref(false)
const editSubmitting = ref(false)
const editingBooking = ref<Booking | null>(null)
const editForm = ref({
  check_in: '',
  check_out: '',
  notes: '',
})

const changeRoomVisible = ref(false)
const changeRoomSubmitting = ref(false)
const changingBooking = ref<Booking | null>(null)
const changeRoomForm = ref({
  room_id: null as number | null,
})

onMounted(async () => {
  await Promise.all([loadBookings(), loadUsers()])
})

async function loadUsers() {
  try {
    const { data } = await api.get<PaginatedResult<UserItem>>('/admin/users', {
      params: { page: 1, page_size: 100 },
    })
    users.value = data.items
  } catch {
    console.warn('Failed to load users for booking dropdown (non-blocking)')
  }
}

async function searchAvailableRooms(checkIn: string, checkOut: string) {
  if (!checkIn || !checkOut || checkOut <= checkIn) {
    availableRooms.value = []
    return
  }
  roomSearchLoading.value = true
  try {
    const { data } = await api.get<RoomOption[]>('/rooms/search', {
      params: { check_in: checkIn, check_out: checkOut },
    })
    availableRooms.value = data
  } catch {
    availableRooms.value = []
    ElMessage.error('查询可用客房失败')
  } finally {
    roomSearchLoading.value = false
  }
}

watch(
  () => [walkInForm.value.check_in, walkInForm.value.check_out],
  ([checkIn, checkOut]) => {
    walkInForm.value.room_id = null
    if (checkIn && checkOut) searchAvailableRooms(checkIn, checkOut)
  },
)

watch(
  () => [editForm.value.check_in, editForm.value.check_out],
  ([checkIn, checkOut]) => {
    if (editVisible.value && checkIn && checkOut) searchAvailableRooms(checkIn, checkOut)
  },
)

watch(
  () => changingBooking.value,
  (booking) => {
    if (booking) searchAvailableRooms(booking.check_in, booking.check_out)
  },
)

async function loadBookings() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (filterForm.value.status) params.status = filterForm.value.status
    if (filterForm.value.check_in_from) params.check_in_from = filterForm.value.check_in_from
    if (filterForm.value.check_in_to) params.check_in_to = filterForm.value.check_in_to

    const { data } = await api.get<PaginatedBookings>('/admin/bookings', { params })
    bookings.value = data.items
    applyPageResult(data)
  } catch {
    ElMessage.error('加载全局订单失败')
  } finally {
    loading.value = false
  }
}

function openWalkInDialog() {
  walkInForm.value = {
    user_id: null,
    check_in: '',
    check_out: '',
    room_id: null,
    notes: '',
    auto_confirm: true,
  }
  availableRooms.value = []
  walkInVisible.value = true
}

async function submitWalkIn() {
  if (!walkInForm.value.user_id || !walkInForm.value.room_id || !walkInForm.value.check_in || !walkInForm.value.check_out) {
    ElMessage.warning('请完整填写客户、日期与客房')
    return
  }
  walkInSubmitting.value = true
  try {
    await api.post('/admin/bookings', {
      user_id: walkInForm.value.user_id,
      room_id: walkInForm.value.room_id,
      check_in: walkInForm.value.check_in,
      check_out: walkInForm.value.check_out,
      notes: walkInForm.value.notes || null,
      auto_confirm: walkInForm.value.auto_confirm,
    })
    ElMessage.success('代客下单成功')
    walkInVisible.value = false
    loadBookings()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '代客下单失败')
  } finally {
    walkInSubmitting.value = false
  }
}

function openEditDialog(row: Booking) {
  editingBooking.value = row
  editForm.value = {
    check_in: row.check_in,
    check_out: row.check_out,
    notes: row.notes ?? '',
  }
  editVisible.value = true
}

async function submitEdit() {
  if (!editingBooking.value) return
  editSubmitting.value = true
  try {
    await api.put(`/admin/bookings/${editingBooking.value.id}`, {
      check_in: editForm.value.check_in,
      check_out: editForm.value.check_out,
      notes: editForm.value.notes || null,
    })
    ElMessage.success('订单已更新')
    editVisible.value = false
    loadBookings()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '更新订单失败')
  } finally {
    editSubmitting.value = false
  }
}

function openChangeRoomDialog(row: Booking) {
  changingBooking.value = row
  changeRoomForm.value = { room_id: null }
  changeRoomVisible.value = true
}

async function submitChangeRoom() {
  if (!changingBooking.value || !changeRoomForm.value.room_id) {
    ElMessage.warning('请选择目标客房')
    return
  }
  changeRoomSubmitting.value = true
  try {
    await api.put(`/admin/bookings/${changingBooking.value.id}/room`, {
      room_id: changeRoomForm.value.room_id,
    })
    ElMessage.success('换房成功')
    changeRoomVisible.value = false
    loadBookings()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '换房失败')
  } finally {
    changeRoomSubmitting.value = false
  }
}

function handleSearch() {
  resetPage()
  loadBookings()
}

function handleReset() {
  filterForm.value.status = ''
  filterForm.value.check_in_from = ''
  filterForm.value.check_in_to = ''
  resetPage()
  loadBookings()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadBookings()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadBookings()
}

async function confirmPayment(id: number) {
  try {
    await ElMessageBox.confirm('是否手工确认该订单的付款状态？此操作将确认分配房间库存。', '确认付款', {
      type: 'warning',
      confirmButtonText: '确认付款',
      cancelButtonText: '取消',
    })
    loading.value = true
    await api.post(`/admin/bookings/${id}/confirm`)
    ElMessage.success('订单付款确认成功')
    loadBookings()
  } catch {
    // dismissed
  } finally {
    loading.value = false
  }
}

async function handleCheckIn(id: number) {
  try {
    await ElMessageBox.confirm('确认办理入住登记？', '入住办理', {
      type: 'success',
      confirmButtonText: '确认入住',
      cancelButtonText: '取消',
    })
  } catch {
    return // user cancelled
  }
  loading.value = true
  try {
    await api.post(`/admin/bookings/${id}/check-in`)
    ElMessage.success('已成功办理入住登记')
    loadBookings()
  } catch (err) {
    handleApiError(err, '入住登记失败')
  } finally {
    loading.value = false
  }
}

async function handleCheckOut(id: number) {
  try {
    await ElMessageBox.confirm('确认办理退房结算？退房后库存将自动标记为 AVAILABLE。', '退房办理', {
      type: 'warning',
      confirmButtonText: '确认退房',
      cancelButtonText: '取消',
    })
  } catch {
    return // user cancelled
  }
  loading.value = true
  try {
    await api.post(`/admin/bookings/${id}/check-out`)
    ElMessage.success('已成功办理退房，客房已清扫归还')
    loadBookings()
  } catch (err) {
    handleApiError(err, '退房办理失败')
  } finally {
    loading.value = false
  }
}

async function cancelOrder(id: number) {
  try {
    await ElMessageBox.confirm('确认强制取消该订单？取消后占用库存将立即退还。', '强制取消订单', {
      type: 'warning',
      confirmButtonText: '强制取消',
      cancelButtonText: '保留订单',
      confirmButtonClass: 'el-button--danger',
    })
  } catch {
    return // user cancelled
  }
  loading.value = true
  try {
    await api.post(`/bookings/${id}/cancel`)
    ElMessage.success('订单已取消并归还锁定的库存')
    loadBookings()
  } catch (err) {
    handleApiError(err, '取消订单失败')
  } finally {
    loading.value = false
  }
}

function roomLabel(room: RoomOption) {
  const typeName = room.room_type?.name ?? ''
  const price = room.room_type?.base_price ?? ''
  return `${room.room_number}${typeName ? ` · ${typeName}` : ''}${price ? ` · ¥${price}/晚` : ''}`
}

const statusMap: Record<string, { text: string; type: 'warning' | 'success' | 'primary' | 'info' | 'danger' }> = {
  pending: { text: '待付款', type: 'warning' },
  confirmed: { text: '已确认', type: 'success' },
  checked_in: { text: '已入住', type: 'primary' },
  checked_out: { text: '已退房', type: 'info' },
  cancelled: { text: '已取消', type: 'danger' },
}
</script>

<template>
  <div class="admin-bookings-panel admin-table-page">
    <div class="panel-header">
      <div class="header-icon">
        <el-icon><Operation /></el-icon>
      </div>
      <div class="header-info">
        <h3>全局订单调度中心</h3>
        <p>管理系统中所有客户生成的入住预订单，进行支付核实、入住登记及退房释放。</p>
      </div>
      <span v-if="total > 0" class="stat-chip">共 {{ total }} 笔订单</span>
      <el-button type="primary" class="header-action walk-in-btn" :icon="Plus" @click="openWalkInDialog">
        代客下单
      </el-button>
    </div>

    <!-- Filter Form -->
    <div class="filter-bar glass-panel-inner">
      <el-form :inline="true" :model="filterForm" class="filter-form" @submit.prevent="handleSearch">
        <el-form-item label="订单状态">
          <el-select v-model="filterForm.status" placeholder="全部状态" clearable style="width: 140px">
            <el-option label="待付款" value="pending" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已入住" value="checked_in" />
            <el-option label="已退房" value="checked_out" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="入住日起">
          <el-date-picker
            v-model="filterForm.check_in_from"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始日期"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="入住日止">
          <el-date-picker
            v-model="filterForm.check_in_to"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束日期"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item class="filter-actions">
          <el-button type="primary" class="query-btn" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button class="reset-btn" :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- Table List -->
    <div class="table-wrapper">
      <el-table
        v-loading="loading"
        :data="bookings"
        style="width: 100%"
        class="admin-table-premium"
        height="100%"
        empty-text="暂无符合条件的订单"
      >
        <el-table-column label="订单号" width="90">
          <template #default="{ row }">
            <span class="booking-id-tag">#{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="客户" min-width="110">
          <template #default="{ row }">
            <div class="cell-user">
              <el-avatar :size="24" class="user-avatar-mini">
                <el-icon><Avatar /></el-icon>
              </el-avatar>
              <span class="user-id">ID {{ row.user_id }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="客房" width="100">
          <template #default="{ row }">
            <span class="room-num">{{ row.room?.room_number ?? row.room_id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="房型" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="room-type-text">{{ row.room?.room_type?.name ?? '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="入住周期" width="210">
          <template #default="{ row }">
            <div class="cell-dates">
              <el-icon><Calendar /></el-icon>
              <span>{{ row.check_in }} → {{ row.check_out }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="总价" width="100" align="right">
          <template #default="{ row }">
            <span class="price-text">¥{{ row.total_price }}</span>
          </template>
        </el-table-column>

        <el-table-column label="备注" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="notes-text">{{ row.notes || '—' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="status-badge-inline" :class="row.status">
              {{ statusMap[row.status]?.text || row.status }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="调度操作" min-width="280" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button
                v-if="EDITABLE_STATUSES.includes(row.status)"
                size="small"
                class="action-btn edit"
                :icon="Edit"
                @click="openEditDialog(row)"
              >
                编辑
              </el-button>
              <el-button
                v-if="EDITABLE_STATUSES.includes(row.status)"
                size="small"
                class="action-btn change-room"
                :icon="Switch"
                @click="openChangeRoomDialog(row)"
              >
                换房
              </el-button>
              <el-button
                v-if="row.status === 'pending'"
                type="success"
                size="small"
                class="action-btn pay"
                @click="confirmPayment(row.id)"
              >
                确认支付
              </el-button>
              <el-button
                v-if="row.status === 'confirmed'"
                type="primary"
                size="small"
                class="action-btn checkin"
                @click="handleCheckIn(row.id)"
              >
                办理入住
              </el-button>
              <el-button
                v-if="row.status === 'checked_in'"
                type="warning"
                size="small"
                class="action-btn checkout"
                @click="handleCheckOut(row.id)"
              >
                办理退房
              </el-button>
              <el-button
                v-if="['pending', 'confirmed'].includes(row.status)"
                type="danger"
                plain
                size="small"
                class="action-btn cancel"
                @click="cancelOrder(row.id)"
              >
                取消
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <AdminPagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-start="pageStart"
        :page-end="pageEnd"
        @page-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- Walk-in booking dialog -->
    <el-dialog v-model="walkInVisible" title="代客下单" width="520px" destroy-on-close>
      <el-form label-width="96px">
        <el-form-item label="客户账户" required>
          <el-select v-model="walkInForm.user_id" placeholder="选择客户" filterable style="width: 100%">
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="`${u.username} (ID ${u.id})`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="入住日期" required>
          <el-date-picker
            v-model="walkInForm.check_in"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="入住日"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="退房日期" required>
          <el-date-picker
            v-model="walkInForm.check_out"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="退房日"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="指定客房" required>
          <el-select
            v-model="walkInForm.room_id"
            placeholder="先选日期后查询可用房"
            filterable
            :loading="roomSearchLoading"
            style="width: 100%"
          >
            <el-option
              v-for="room in availableRooms"
              :key="room.id"
              :label="roomLabel(room)"
              :value="room.id"
            />
          </el-select>
          <span v-if="walkInForm.check_in && walkInForm.check_out" class="form-hint">
            所选日期可订 {{ availableRooms.length }} 间（全店运营客房以房态为准，已被预订/锁定的房间不会出现在列表中）
          </span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="walkInForm.notes" type="textarea" :rows="2" maxlength="512" show-word-limit />
        </el-form-item>
        <el-form-item label="直接确认">
          <el-switch v-model="walkInForm.auto_confirm" />
          <span class="form-hint">开启后跳过待付款，直接占用库存为已确认</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="walkInVisible = false">取消</el-button>
        <el-button type="primary" :loading="walkInSubmitting" @click="submitWalkIn">创建订单</el-button>
      </template>
    </el-dialog>

    <!-- Edit booking dialog -->
    <el-dialog v-model="editVisible" title="编辑订单" width="520px" destroy-on-close>
      <el-form label-width="96px">
        <el-form-item label="入住日期">
          <el-date-picker
            v-model="editForm.check_in"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="退房日期">
          <el-date-picker
            v-model="editForm.check_out"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="3" maxlength="512" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- Change room dialog -->
    <el-dialog v-model="changeRoomVisible" title="更换客房" width="520px" destroy-on-close>
      <p v-if="changingBooking" class="dialog-hint">
        订单 #{{ changingBooking.id }} · {{ changingBooking.check_in }} → {{ changingBooking.check_out }}
        · 当前 {{ changingBooking.room?.room_number ?? changingBooking.room_id }}
      </p>
      <el-form label-width="96px">
        <el-form-item label="目标客房" required>
          <el-select
            v-model="changeRoomForm.room_id"
            placeholder="选择可用客房"
            filterable
            :loading="roomSearchLoading"
            style="width: 100%"
          >
            <el-option
              v-for="room in availableRooms.filter(r => r.id !== changingBooking?.room_id)"
              :key="room.id"
              :label="roomLabel(room)"
              :value="room.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changeRoomVisible = false">取消</el-button>
        <el-button type="primary" :loading="changeRoomSubmitting" @click="submitChangeRoom">确认换房</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stat-chip {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-color);
  background: var(--primary-light);
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid rgba(99, 102, 241, 0.15);
  white-space: nowrap;
}

.walk-in-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
}

.form-hint,
.dialog-hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.dialog-hint {
  margin: 0 0 16px;
  padding: 10px 12px;
  background: var(--primary-light);
  border-radius: var(--radius-sm);
}

.notes-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.filter-bar {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.4);
  padding: 16px 20px 4px;
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 25px -10px rgba(99, 102, 241, 0.04);
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.filter-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--text-secondary);
  font-size: 13px;
}

.query-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 10px -2px rgba(99, 102, 241, 0.3);
}

.reset-btn {
  background: transparent;
  border: 1px solid var(--card-border);
  color: var(--text-secondary);
}

.reset-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.table-wrapper {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 10px 30px -15px rgba(99, 102, 241, 0.05);
}

.admin-table-premium {
  background: transparent !important;
}

.admin-table-premium :deep(tr) {
  background: transparent !important;
}

.admin-table-premium :deep(th.el-table__cell) {
  background: rgba(255, 255, 255, 0.8) !important;
  font-weight: 700;
  color: var(--text-primary);
  font-size: 13px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
}

.admin-table-premium :deep(td.el-table__cell) {
  padding: 12px 0;
  border-bottom: 1px solid rgba(99, 102, 241, 0.05);
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.6);
  border-top: 1px solid rgba(99, 102, 241, 0.08);
}

.footer-summary {
  font-size: 13px;
  color: var(--text-secondary);
}

.booking-id-tag {
  font-family: monospace;
  font-weight: 700;
  font-size: 12px;
  color: var(--text-primary);
  background: var(--primary-light);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.cell-user {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar-mini {
  background: var(--accent-gradient);
}

.user-id {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.room-num {
  font-weight: 700;
  font-size: 13px;
  color: var(--text-primary);
}

.room-type-text {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.cell-dates {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.price-text {
  font-family: var(--font-title);
  font-weight: 800;
  color: var(--primary-color);
  font-size: 14px;
}

.status-badge-inline {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 20px;
  white-space: nowrap;
}

.status-badge-inline.pending { background: #fffbeb; color: #d97706; border: 1px solid #fef3c7; }
.status-badge-inline.confirmed { background: #ecfdf5; color: #059669; border: 1px solid #d1fae5; }
.status-badge-inline.checked_in { background: #eff6ff; color: #2563eb; border: 1px solid #dbeafe; }
.status-badge-inline.checked_out { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
.status-badge-inline.cancelled { background: #fdf2f2; color: #dc2626; border: 1px solid #fde8e8; }

.table-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.action-btn {
  font-weight: 600;
  border-radius: 6px;
  transition: all 0.2s;
  border: none;
}

.action-btn.pay { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #fff; box-shadow: 0 3px 6px rgba(16, 185, 129, 0.2); }
.action-btn.edit,
.action-btn.change-room { background: #f8fafc; border: 1px solid #e2e8f0; color: var(--text-primary); }
.action-btn.checkin { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: #fff; box-shadow: 0 3px 6px rgba(99, 102, 241, 0.2); }
.action-btn.checkout { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #fff; box-shadow: 0 3px 6px rgba(245, 158, 11, 0.2); }
.action-btn.cancel { background: transparent; border: 1px solid #fca5a5; color: #ef4444; }
.action-btn.cancel:hover { background: #fee2e2; border-color: #ef4444; }

.action-btn:hover {
  transform: translateY(-1px);
  opacity: 0.95;
}

@media (max-width: 768px) {
  .table-footer {
    flex-direction: column;
    align-items: flex-end;
  }
}
</style>
