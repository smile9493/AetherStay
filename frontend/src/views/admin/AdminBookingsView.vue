<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { Search, Refresh } from '@element-plus/icons-vue'

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

const bookings = ref<Booking[]>([])
const loading = ref(false)

const filterForm = ref({
  status: '' as string,
  check_in_from: '' as string,
  check_in_to: '' as string,
})

onMounted(loadAllBookings)

async function loadAllBookings() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (filterForm.value.status) params.status = filterForm.value.status
    if (filterForm.value.check_in_from) params.check_in_from = filterForm.value.check_in_from
    if (filterForm.value.check_in_to) params.check_in_to = filterForm.value.check_in_to
    
    const { data } = await api.get<Booking[]>('/admin/bookings', { params })
    bookings.value = data
  } catch {
    ElMessage.error('加载全局订单失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  filterForm.value.status = ''
  filterForm.value.check_in_from = ''
  filterForm.value.check_in_to = ''
  loadAllBookings()
}

// Action operations
async function confirmPayment(id: number) {
  try {
    await ElMessageBox.confirm('是否手工确认该订单的付款状态？此操作将确认分配房间库存。', '确认付款', { type: 'warning' })
    loading.value = true
    await api.post(`/admin/bookings/${id}/confirm`)
    ElMessage.success('订单付款确认成功')
    loadAllBookings()
  } catch {
    // dismissed
  } finally {
    loading.value = false
  }
}

async function handleCheckIn(id: number) {
  try {
    await ElMessageBox.confirm('确认办理入住登记？', '入住办理', { type: 'success' })
    loading.value = true
    await api.post(`/admin/bookings/${id}/check-in`)
    ElMessage.success('已成功办理入住登记')
    loadAllBookings()
  } catch {
    // dismissed
  } finally {
    loading.value = false
  }
}

async function handleCheckOut(id: number) {
  try {
    await ElMessageBox.confirm('确认办理退房结算？退房后库存将自动标记为 AVAILABLE。', '退房办理', { type: 'warning' })
    loading.value = true
    await api.post(`/admin/bookings/${id}/check-out`)
    ElMessage.success('已成功办理退房，客房已清扫归还')
    loadAllBookings()
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
      confirmButtonClass: 'el-button--danger'
    })
    loading.value = true
    await api.post(`/bookings/${id}/cancel`)
    ElMessage.success('订单已取消并归还锁定的库存')
    loadAllBookings()
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
      <h3>全局订单调度中心</h3>
      <p>管理系统中所有客户生成的入住预订单，进行支付核实、入住登记及退房释放。</p>
    </div>

    <!-- Filter Form -->
    <div class="filter-bar">
      <el-form :inline="true" :model="filterForm" size="default">
        <el-form-item label="订单状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" clearable style="width: 140px">
            <el-option label="待付款" value="pending" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已入住" value="checked_in" />
            <el-option label="已退房" value="checked_out" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="入住始于">
          <el-date-picker 
            v-model="filterForm.check_in_from" 
            type="date" 
            value-format="YYYY-MM-DD" 
            placeholder="开始日期" 
            style="width: 150px" 
          />
        </el-form-item>
        <el-form-item label="入住止于">
          <el-date-picker 
            v-model="filterForm.check_in_to" 
            type="date" 
            value-format="YYYY-MM-DD" 
            placeholder="结束日期" 
            style="width: 150px" 
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="loadAllBookings">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- Table List -->
    <el-table v-loading="loading" :data="bookings" stripe style="width: 100%" class="admin-table">
      <el-table-column prop="id" label="订单号" width="70" />
      <el-table-column prop="user_id" label="客户ID" width="70" />
      <el-table-column label="房间号" width="80">
        <template #default="{ row }">
          <strong>{{ row.room?.room_number ?? row.room_id }}</strong>
        </template>
      </el-table-column>
      <el-table-column label="房型名称">
        <template #default="{ row }">{{ row.room?.room_type?.name ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="check_in" label="入住日期" width="100" />
      <el-table-column prop="check_out" label="退房日期" width="100" />
      <el-table-column label="总价" width="100">
        <template #default="{ row }">¥{{ row.total_price }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusMap[row.status]?.type || 'info'" size="small">
            {{ statusMap[row.status]?.text || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="150">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="调度操作" min-width="160">
        <template #default="{ row }">
          <div class="table-actions">
            <!-- Confirm Payment for pending -->
            <el-button 
              v-if="row.status === 'pending'" 
              type="success" 
              size="small" 
              @click="confirmPayment(row.id)"
            >
              确认支付
            </el-button>

            <!-- Check In for confirmed -->
            <el-button 
              v-if="row.status === 'confirmed'" 
              type="primary" 
              size="small" 
              @click="handleCheckIn(row.id)"
            >
              入住
            </el-button>

            <!-- Check Out for checked_in -->
            <el-button 
              v-if="row.status === 'checked_in'" 
              type="warning" 
              size="small" 
              @click="handleCheckOut(row.id)"
            >
              退房
            </el-button>

            <!-- Cancel for pending/confirmed -->
            <el-button 
              v-if="['pending', 'confirmed'].includes(row.status)" 
              type="danger" 
              plain
              size="small" 
              @click="cancelOrder(row.id)"
            >
              取消
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.admin-bookings-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-header h3 {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.panel-header p {
  font-size: 13px;
  color: var(--text-secondary);
}

.filter-bar {
  background: #f8fafc;
  padding: 16px 16px 4px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--card-border);
}

.admin-table {
  border: 1px solid var(--card-border);
  border-radius: var(--radius-sm);
}

.table-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
