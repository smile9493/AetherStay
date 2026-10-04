<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
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

// 将后端的 YYYY-MM-DD 转为中文日期，如 2026年11月10日
function formatDate(value: string) {
  const matched = /^(\d{4})-(\d{2})-(\d{2})/.exec(value ?? '')
  if (!matched) return value ?? '-'
  const [, year, month, day] = matched
  return `${year}年${Number(month)}月${Number(day)}日`
}
</script>

<template>
  <div class="bookings-page">
    <header class="page-head">
      <h2>我的订单</h2>
      <p class="page-head__sub">
        <template v-if="!loading && bookings.length">共 {{ bookings.length }} 个订单</template>
        <template v-else>查看并管理你的预订记录</template>
      </p>
    </header>

    <div v-loading="loading" class="booking-list">
      <article v-for="booking in bookings" :key="booking.id" class="booking-card">
        <div class="booking-card__main">
          <h3 class="booking-card__title">
            {{ booking.room?.room_number ?? booking.room_id }}
            <small v-if="booking.room?.room_type">{{ booking.room.room_type.name }}</small>
          </h3>
          <p class="booking-card__dates">
            {{ formatDate(booking.check_in) }} → {{ formatDate(booking.check_out) }}
          </p>
          <p class="booking-card__id">订单号 #{{ booking.id }}</p>
        </div>

        <div class="booking-card__side">
          <el-tag
            :type="booking.status === 'cancelled' ? 'info' : booking.status === 'confirmed' ? 'success' : 'warning'"
            effect="light"
            round
          >
            {{ statusMap[booking.status] ?? booking.status }}
          </el-tag>
          <p class="booking-card__price">¥{{ booking.total_price }}</p>
          <el-button
            v-if="['pending', 'confirmed'].includes(booking.status)"
            type="danger"
            plain
            size="small"
            @click="cancelBooking(booking.id)"
          >
            取消
          </el-button>
        </div>
      </article>

      <el-empty v-if="!loading && bookings.length === 0" description="暂无订单" />
    </div>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 24px;
}

.page-head h2 {
  font-size: 24px;
}

.page-head__sub {
  margin-top: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

.booking-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 120px;
}

.booking-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.booking-card:hover {
  border-color: var(--brand-200);
  box-shadow: var(--shadow-sm);
}

.booking-card__title {
  font-size: 16px;
}

.booking-card__title small {
  margin-left: 8px;
  font-size: 14px;
  font-weight: 400;
  color: var(--text-secondary);
}

.booking-card__dates {
  margin-top: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

.booking-card__id {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.booking-card__side {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.booking-card__price {
  font-size: 20px;
  font-weight: 600;
  color: var(--brand-700);
}

@media (max-width: 640px) {
  .booking-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .booking-card__side {
    width: 100%;
    justify-content: space-between;
  }
}
</style>