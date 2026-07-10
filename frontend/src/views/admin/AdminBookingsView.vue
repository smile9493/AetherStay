<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { Search, Refresh, Calendar, Avatar, Operation } from '@element-plus/icons-vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import { usePagination, type PaginatedResult } from '@/composables/usePagination'

interface Booking {
  id: number
  user_id: number
  room_id: number
  check_in: string
  check_out: string
  total_price: string
  status: string
  created_at: string
  room?: {
    room_number: string
    room_type?: { name: string }
  }
}

interface PaginatedBookings extends PaginatedResult<Booking> {}

const bookings = ref<Booking[]>([])
const loading = ref(false)
const { currentPage, pageSize, total, pageStart, pageEnd, applyPageResult, resetPage } = usePagination(20)

const filterForm = ref({
  status: '' as string,
  check_in_from: '' as string,
  check_in_to: '' as string,
})

onMounted(() => loadBookings())

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
    loading.value = true
    await api.post(`/admin/bookings/${id}/check-in`)
    ElMessage.success('已成功办理入住登记')
    loadBookings()
  } catch {
    // dismissed
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
    loading.value = true
    await api.post(`/admin/bookings/${id}/check-out`)
    ElMessage.success('已成功办理退房，客房已清扫归还')
    loadBookings()
  } catch {
    // dismissed
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
    loading.value = true
    await api.post(`/bookings/${id}/cancel`)
    ElMessage.success('订单已取消并归还锁定的库存')
    loadBookings()
  } catch {
    // dismissed
  } finally {
    loading.value = false
  }
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
  <div class="admin-bookings-panel">
    <div class="panel-header">
      <div class="header-icon">
        <el-icon><Operation /></el-icon>
      </div>
      <div class="header-info">
        <h3>全局订单调度中心</h3>
        <p>管理系统中所有客户生成的入住预订单，进行支付核实、入住登记及退房释放。</p>
      </div>
      <div v-if="total > 0" class="header-stats">
        <span class="stat-chip">共 {{ total }} 笔订单</span>
      </div>
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
        :max-height="560"
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

        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="status-badge-inline" :class="row.status">
              {{ statusMap[row.status]?.text || row.status }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="调度操作" min-width="200" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
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
  </div>
</template>

<style scoped>
.admin-bookings-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.header-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: var(--primary-light);
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
}

.header-info {
  flex: 1;
  min-width: 200px;
}

.panel-header h3 {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary);
}

.panel-header p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.header-stats {
  margin-left: auto;
}

.stat-chip {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-color);
  background: var(--primary-light);
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid rgba(99, 102, 241, 0.15);
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
