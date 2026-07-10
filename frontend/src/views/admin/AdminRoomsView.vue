<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { Plus, Edit, House, OfficeBuilding } from '@element-plus/icons-vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import { usePagination, type PaginatedResult } from '@/composables/usePagination'

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
const { currentPage, pageSize, total, pageStart, pageEnd, applyPageResult } = usePagination(20)

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
    const { data } = await api.get<PaginatedResult<Room>>('/admin/rooms', {
      params: { page: currentPage.value, page_size: pageSize.value },
    })
    rooms.value = data.items
    applyPageResult(data)
  } catch {
    ElMessage.error('加载客房列表失败')
  } finally {
    loading.value = false
  }
}

async function loadRoomTypes() {
  try {
    const { data } = await api.get<PaginatedResult<RoomType>>('/admin/room-types', {
      params: { page: 1, page_size: 100 },
    })
    roomTypes.value = data.items
  } catch {
    ElMessage.error('加载房型列表失败')
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadRooms()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadRooms()
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
          await api.put(`/admin/rooms/${roomForm.value.id}`, {
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
    <!-- Header panel -->
    <div class="panel-header-row">
      <div class="panel-header-left">
        <div class="header-icon">
          <el-icon><House /></el-icon>
        </div>
        <div class="title-cell">
          <h3>客房资源管理</h3>
          <p>在此维护酒店物理客房。新增客房会自动生成 90 天的可预订每日房态库存记录。</p>
        </div>
        <span v-if="total > 0" class="stat-chip">共 {{ total }} 间客房</span>
      </div>
      <el-button type="primary" class="add-btn" :icon="Plus" @click="openAddDialog">
        录入新客房
      </el-button>
    </div>

    <!-- Table List -->
    <div class="table-wrapper">
      <el-table
        v-loading="loading"
        :data="rooms"
        style="width: 100%"
        class="admin-table-premium"
        :max-height="560"
        empty-text="暂无客房数据"
      >
        <!-- Room ID -->
        <el-table-column prop="id" label="客房ID" width="100" />
        
        <!-- Room Number -->
        <el-table-column label="房间门牌" width="160">
          <template #default="{ row }">
            <div class="room-number-badge">
              <el-icon><OfficeBuilding /></el-icon>
              <span>Room {{ row.room_number }}</span>
            </div>
          </template>
        </el-table-column>
        
        <!-- Room Type -->
        <el-table-column label="对应房型">
          <template #default="{ row }">
            <span class="room-type-lbl">{{ row.room_type?.name ?? '-' }}</span>
          </template>
        </el-table-column>
        
        <!-- Capacity -->
        <el-table-column label="容纳上限" width="120">
          <template #default="{ row }">
            <span class="capacity-val">{{ row.room_type?.capacity ?? 0 }} 人</span>
          </template>
        </el-table-column>
        
        <!-- Price -->
        <el-table-column label="基准价格 (每晚)" width="160">
          <template #default="{ row }">
            <span class="price-val">¥{{ row.room_type?.base_price ?? '0.00' }}</span>
          </template>
        </el-table-column>
        
        <!-- Status -->
        <el-table-column label="营业状态" width="160">
          <template #default="{ row }">
            <span class="status-pill" :class="row.status">
              {{ row.status === 'active' ? '营业中' : '维护中' }}
            </span>
          </template>
        </el-table-column>
        
        <!-- Actions -->
        <el-table-column label="控制操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" class="edit-btn" :icon="Edit" @click="openEditDialog(row)">
              编辑
            </el-button>
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

    <!-- Add/Edit Room Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '录入新客房' : '编辑客房'"
      width="440px"
      align-center
      class="custom-admin-dialog"
    >
      <el-form 
        ref="formRef"
        :model="roomForm" 
        :rules="rules"
        label-position="top"
        class="custom-form"
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
          <el-radio-group v-model="roomForm.status" class="status-radio-group">
            <el-radio-button value="active">营业中 (Active)</el-radio-button>
            <el-radio-button value="inactive">停业维护 (Inactive)</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button class="cancel-btn" @click="dialogVisible = false">取 消</el-button>
          <el-button type="primary" class="submit-btn" :loading="submitLoading" @click="handleSubmit">确 定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-rooms-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.panel-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
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

.title-cell h3 {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary);
}

.title-cell p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.add-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  box-shadow: 0 4px 14px -3px rgba(99, 102, 241, 0.4);
}

.add-btn:hover {
  opacity: 0.95;
  transform: translateY(-1px);
}

/* Premium Table Override */
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
  padding: 14px 0;
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
}

.admin-table-premium :deep(td.el-table__cell) {
  padding: 16px 0;
  border-bottom: 1px solid rgba(99, 102, 241, 0.05);
}

/* Specific Cell Layouts */
.room-number-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--primary-light);
  color: var(--primary-color);
  padding: 4px 10px;
  border-radius: 20px;
  font-family: var(--font-title);
  font-weight: 700;
  font-size: 13px;
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.room-type-lbl {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 600;
}

.capacity-val {
  font-size: 13px;
  color: var(--text-secondary);
}

.price-val {
  font-family: var(--font-title);
  font-weight: 800;
  color: var(--primary-color);
  font-size: 14px;
}

.status-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 20px;
  display: inline-block;
}

.status-pill.active {
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #d1fae5;
}

.status-pill.inactive {
  background: #fdf2f2;
  color: #dc2626;
  border: 1px solid #fde8e8;
}

.edit-btn {
  background: transparent;
  border: 1px solid var(--card-border);
  color: var(--primary-color);
  font-weight: 600;
}

.edit-btn:hover {
  background: var(--primary-light);
  border-color: var(--primary-color);
}

/* Dialog styling */
.custom-admin-dialog :deep(.el-dialog) {
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--card-border);
}

.custom-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--text-secondary);
}

.status-radio-group {
  width: 100%;
  display: flex;
}

.status-radio-group :deep(.el-radio-button) {
  flex: 1;
}

.status-radio-group :deep(.el-radio-button__inner) {
  width: 100%;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.submit-btn {
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
}
</style>
