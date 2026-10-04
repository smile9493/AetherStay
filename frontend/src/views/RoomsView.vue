<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'

interface Room {
  id: number
  room_number: string
  room_type_id: number
  status: string
  room_type: {
    name: string
    base_price: string
    capacity: number
  }
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
    ElMessage.error('搜索失败')
  } finally {
    loading.value = false
  }
}

async function bookRoom(room: Room) {
  if (!auth.user) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }
  if (!searchForm.value.check_in || !searchForm.value.check_out) {
    ElMessage.warning('请先选择入住和退房日期')
    return
  }
  bookingLoading.value = true
  try {
    await api.post('/bookings', {
      room_id: room.id,
      check_in: searchForm.value.check_in,
      check_out: searchForm.value.check_out,
    })
    ElMessage.success(`房间 ${room.room_number} 预订成功`)
    router.push('/bookings')
  } catch {
    ElMessage.error('预订失败')
  } finally {
    bookingLoading.value = false
  }
}

// 仅用于展示：后端未识别的状态值会原样回退显示
const statusMeta: Record<string, { label: string; type: 'success' | 'warning' | 'info' | 'danger' }> = {
  available: { label: '可预订', type: 'success' },
  reserved: { label: '已预订', type: 'warning' },
  occupied: { label: '已入住', type: 'warning' },
  maintenance: { label: '维护中', type: 'danger' },
  cleaning: { label: '清洁中', type: 'info' },
}

function statusLabel(status: string) {
  return statusMeta[status]?.label ?? status
}

function statusType(status: string) {
  return statusMeta[status]?.type ?? 'info'
}
</script>

<template>
  <div class="rooms-page">
    <header class="page-head">
      <h2>客房预订</h2>
      <p class="page-head__sub">选择入住与退房日期，查询该日期段可预订的客房</p>
    </header>

    <section class="search-panel">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="入住日期">
          <el-date-picker v-model="searchForm.check_in" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="退房日期">
          <el-date-picker v-model="searchForm.check_out" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="searchRooms">搜索可用客房</el-button>
          <el-button @click="loadAllRooms">显示全部</el-button>
        </el-form-item>
      </el-form>
    </section>

    <div v-loading="loading" class="room-grid">
      <article v-for="room in rooms" :key="room.id" class="room-card">
        <header class="room-card__head">
          <div>
            <h3 class="room-card__title">{{ room.room_type?.name ?? '-' }}</h3>
            <p class="room-card__no">房间号 {{ room.room_number }}</p>
          </div>
          <el-tag :type="statusType(room.status)" effect="light" round>{{ statusLabel(room.status) }}</el-tag>
        </header>

        <dl class="room-card__meta">
          <div class="room-card__meta-item">
            <dt>容纳人数</dt>
            <dd>{{ room.room_type?.capacity ?? '-' }} 人</dd>
          </div>
          <div class="room-card__meta-item">
            <dt>价格</dt>
            <dd class="room-card__price">¥{{ room.room_type?.base_price ?? '-' }}<span>/晚</span></dd>
          </div>
        </dl>

        <el-button type="primary" class="room-card__action" :loading="bookingLoading" @click="bookRoom(room)">
          预订
        </el-button>
      </article>
    </div>

    <el-empty v-if="!loading && rooms.length === 0" description="暂无可预订客房" />
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

.search-panel {
  padding: 16px 24px 0;
  margin-bottom: 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.room-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  min-height: 120px;
}

.room-card {
  display: flex;
  flex-direction: column;
  padding: 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition),
    transform var(--transition);
}

.room-card:hover {
  border-color: var(--brand-200);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.room-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.room-card__title {
  font-size: 16px;
}

.room-card__no {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.room-card__meta {
  display: flex;
  gap: 24px;
  margin: 20px 0;
}

.room-card__meta-item dt {
  font-size: 12px;
  color: var(--text-tertiary);
}

.room-card__meta-item dd {
  margin: 4px 0 0;
  font-size: 14px;
}

.room-card__price {
  font-size: 20px;
  font-weight: 600;
  color: var(--brand-700);
}

.room-card__price span {
  margin-left: 2px;
  font-size: 12px;
  font-weight: 400;
  color: var(--text-tertiary);
}

.room-card__action {
  width: 100%;
  margin-top: auto;
}

@media (max-width: 768px) {
  .room-grid {
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  }
}
</style>