<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { Plus, Edit } from '@element-plus/icons-vue'

interface RoomType {
  id: number
  name: string
  base_price: string
  capacity: number
  total_rooms: number
}

interface Room {
  id: number
  room_number: string
  room_type_id: number
  status: string
  room_type?: RoomType
}

const rooms = ref<Room[]>([])
const roomTypes = ref<RoomType[]>([])
const loading = ref(false)

// Dialog states
const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const submitLoading = ref(false)

const roomForm = ref({
  id: undefined as number | undefined,
  room_number: '',
  room_type_id: undefined as number | undefined,
  status: 'active',
})

const rules = {
  room_number: [
    { required: true, message: '请输入房间门牌号', trigger: 'blur' },
    { max: 16, message: '门牌号不能超过 16 个字符', trigger: 'blur' }
  ],
  room_type_id: [
    { required: true, message: '请选择客房类型', trigger: 'change' }
  ],
  status: [
    { required: true, message: '请选择客房状态', trigger: 'change' }
  ]
}

const formRef = ref()

onMounted(async () => {
  await Promise.all([loadRooms(), loadRoomTypes()])
})

async function loadRooms() {
  loading.value = true
  try {
    const { data } = await api.get<Room[]>('/admin/rooms')
    rooms.value = data
  } catch {
    ElMessage.error('加载客房列表失败')
  } finally {
    loading.value = false
  }
}

async function loadRoomTypes() {
  try {
    const { data } = await api.get<RoomType[]>('/admin/room-types')
    roomTypes.value = data
  } catch {
    ElMessage.error('加载房型列表失败')
  }
}

function openAddDialog() {
  dialogType.value = 'add'
  roomForm.value = {
    id: undefined,
    room_number: '',
    room_type_id: undefined,
    status: 'active',
  }
  dialogVisible.value = true
}

function openEditDialog(room: Room) {
  dialogType.value = 'edit'
  roomForm.value = {
    id: room.id,
    room_number: room.room_number,
    room_type_id: room.room_type_id,
    status: room.status,
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      submitLoading.value = true
      try {
        if (dialogType.value === 'add') {
          await api.post('/admin/rooms', {
            room_number: roomForm.value.room_number,
            room_type_id: roomForm.value.room_type_id,
            status: roomForm.value.status,
          })
          ElMessage.success('客房添加成功，系统已自动生成 90 天每日库存！')
        } else {
          await api.put(`/admin/rooms/\${roomForm.value.id}`, {
            room_number: roomForm.value.room_number,
            room_type_id: roomForm.value.room_type_id,
            status: roomForm.value.status,
          })
          ElMessage.success('客房信息更新成功')
        }
        dialogVisible.value = false
        loadRooms()
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || '操作失败，门牌号可能已存在或参数冲突'
        ElMessage.error(errorMsg)
      } finally {
        submitLoading.value = false
      }
    }
  })
}
</script>

<template>
  <div class="admin-rooms-panel">
    <div class="panel-header-row">
      <div class="title-cell">
        <h3>客房资源管理</h3>
        <p>在此维护酒店物理客房。新增客房会自动为该房间生成 90 天的可预订每日房态库存记录。</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openAddDialog">
        录入新客房
      </el-button>
    </div>

    <!-- Table List -->
    <el-table v-loading="loading" :data="rooms" stripe style="width: 100%" class="admin-table">
      <el-table-column prop="id" label="客房ID" width="90" />
      <el-table-column prop="room_number" label="门牌号" width="120">
        <template #default="{ row }">
          <strong>Room {{ row.room_number }}</strong>
        </template>
      </el-table-column>
      <el-table-column label="房型名称">
        <template #default="{ row }">{{ row.room_type?.name ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="容纳上限" width="100">
        <template #default="{ row }">{{ row.room_type?.capacity ?? 0 }} 人</template>
      </el-table-column>
      <el-table-column label="基本价格" width="120">
        <template #default="{ row }">¥{{ row.room_type?.base_price ?? '0.00' }}</template>
      </el-table-column>
      <el-table-column label="营业状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
            {{ row.status === 'active' ? '营业中 (Active)' : '已停业 (Inactive)' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="primary" :icon="Edit" size="small" @click="openEditDialog(row)">
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add/Edit Room Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '录入新客房' : '编辑客房'"
      width="440px"
      align-center
    >
      <el-form 
        ref="formRef"
        :model="roomForm" 
        :rules="rules"
        label-position="top"
      >
        <el-form-item label="房间门牌号" prop="room_number">
          <el-input v-model="roomForm.room_number" placeholder="请输入门牌号 (如 101)" />
        </el-form-item>
        <el-form-item label="对应客房房型" prop="room_type_id">
          <el-select v-model="roomForm.room_type_id" placeholder="请选择房型" style="width: 100%">
            <el-option 
              v-for="item in roomTypes" 
              :key="item.id" 
              :label="item.name" 
              :value="item.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="营业状态" prop="status">
          <el-radio-group v-model="roomForm.status">
            <el-radio value="active">营业中 (Active)</el-radio>
            <el-radio value="inactive">停业维护 (Inactive)</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-rooms-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-cell h3 {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.title-cell p {
  font-size: 13px;
  color: var(--text-secondary);
}

.admin-table {
  border: 1px solid var(--card-border);
  border-radius: var(--radius-sm);
}
</style>
