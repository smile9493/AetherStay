<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
</script>

<template>
  <div class="rooms-page">
    <h2>客房预订</h2>
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm">
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
    </el-card>

    <el-table v-loading="loading" :data="rooms" stripe style="width: 100%">
      <el-table-column prop="room_number" label="房间号" width="120" />
      <el-table-column label="房型">
        <template #default="{ row }">{{ row.room_type?.name ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="价格/晚" width="120">
        <template #default="{ row }">¥{{ row.room_type?.base_price ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="容纳人数" width="100">
        <template #default="{ row }">{{ row.room_type?.capacity ?? '-' }} 人</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="primary" size="small" :loading="bookingLoading" @click="bookRoom(row)">
            预订
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.rooms-page {
  max-width: 1100px;
  margin: 0 auto;
}
.search-card {
  margin-bottom: 24px;
}
</style>
