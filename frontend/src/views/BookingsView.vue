<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

interface Booking {
  id: number
  room_id: number
  check_in: string
  check_out: string
  total_price: string
  status: string
  created_at: string
  room?: { room_number: string; room_type?: { name: string } }
}

const router = useRouter()
const auth = useAuthStore()
const bookings = ref<Booking[]>([])
const loading = ref(false)

onMounted(async () => {
  if (!auth.user) {
    await auth.fetchUser()
    if (!auth.user) {
      router.push('/login')
      return
    }
  }
  loadBookings()
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
    await ElMessageBox.confirm('确定要取消此订单吗？', '确认取消', { type: 'warning' })
    await api.post(`/bookings/${id}/cancel`)
    ElMessage.success('订单已取消')
    loadBookings()
  } catch {
    // user dismissed or error
  }
}

const statusMap: Record<string, string> = {
  pending: '待确认',
  confirmed: '已确认',
  checked_in: '已入住',
  checked_out: '已退房',
  cancelled: '已取消',
}
</script>

<template>
  <div class="bookings-page">
    <h2>我的订单</h2>
    <el-table v-loading="loading" :data="bookings" stripe style="width: 100%">
      <el-table-column prop="id" label="订单号" width="80" />
      <el-table-column label="房间">
        <template #default="{ row }">
          {{ row.room?.room_number ?? row.room_id }}
          <span v-if="row.room?.room_type" class="room-type">({{ row.room.room_type.name }})</span>
        </template>
      </el-table-column>
      <el-table-column prop="check_in" label="入住" width="120" />
      <el-table-column prop="check_out" label="退房" width="120" />
      <el-table-column label="总价" width="100">
        <template #default="{ row }">¥{{ row.total_price }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'cancelled' ? 'info' : row.status === 'confirmed' ? 'success' : 'warning'">
            {{ statusMap[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button
            v-if="['pending', 'confirmed'].includes(row.status)"
            type="danger"
            size="small"
            @click="cancelBooking(row.id)"
          >
            取消
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && bookings.length === 0" description="暂无订单" />
  </div>
</template>

<style scoped>
.bookings-page {
  max-width: 1100px;
  margin: 0 auto;
}
.room-type {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
