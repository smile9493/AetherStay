<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { Plus, Edit, Setting } from '@element-plus/icons-vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import { usePagination, type PaginatedResult } from '@/composables/usePagination'

interface RoomType {
  id: number
  name: string
  base_price: string
  capacity: number
  total_rooms: number
  description?: string
  amenities?: string
  image_url?: string
}

const roomTypes = ref<RoomType[]>([])
const loading = ref(false)
const { currentPage, pageSize, total, pageStart, pageEnd, applyPageResult } = usePagination(10)

// Dialog states
const dialogVisible = ref(false)
const dialogType = ref<'add' | 'edit'>('add')
const submitLoading = ref(false)

const typeForm = ref({
  id: undefined as number | undefined,
  name: '',
  base_price: 100,
  capacity: 2,
  total_rooms: 0,
  description: '',
  amenities: '',
  image_url: '',
})

const rules = {
  name: [
    { required: true, message: '请输入房型名称', trigger: 'blur' },
    { max: 64, message: '房型名称不能超过 64 个字符', trigger: 'blur' }
  ],
  base_price: [
    { required: true, message: '请设定基准价格', trigger: 'blur' },
    { type: 'number', min: 1, message: '价格必须大于 0', trigger: 'blur' }
  ],
  capacity: [
    { required: true, message: '请选择最大容纳人数', trigger: 'blur' },
    { type: 'number', min: 1, max: 20, message: '容纳人数需在 1 至 20 之间', trigger: 'blur' }
  ]
}

const formRef = ref()

onMounted(loadRoomTypes)

async function loadRoomTypes() {
  loading.value = true
  try {
    const { data } = await api.get<PaginatedResult<RoomType>>('/admin/room-types', {
      params: { page: currentPage.value, page_size: pageSize.value },
    })
    roomTypes.value = data.items
    applyPageResult(data)
  } catch {
    ElMessage.error('加载房型列表失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadRoomTypes()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadRoomTypes()
}

function openAddDialog() {
  dialogType.value = 'add'
  typeForm.value = {
    id: undefined,
    name: '',
    base_price: 199,
    capacity: 2,
    total_rooms: 0,
    description: '',
    amenities: '',
    image_url: '',
  }
  dialogVisible.value = true
}

function openEditDialog(item: RoomType) {
  dialogType.value = 'edit'
  typeForm.value = {
    id: item.id,
    name: item.name,
    base_price: parseFloat(item.base_price),
    capacity: item.capacity,
    total_rooms: item.total_rooms,
    description: item.description ?? '',
    amenities: item.amenities ?? '',
    image_url: item.image_url ?? '',
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
          await api.post('/admin/room-types', {
            name: typeForm.value.name,
            base_price: typeForm.value.base_price.toString(),
            capacity: typeForm.value.capacity,
            total_rooms: typeForm.value.total_rooms,
            description: typeForm.value.description || null,
            amenities: typeForm.value.amenities || null,
            image_url: typeForm.value.image_url || null,
          })
          ElMessage.success('新增房型成功')
        } else {
          await api.put(`/admin/room-types/${typeForm.value.id}`, {
            name: typeForm.value.name,
            base_price: typeForm.value.base_price.toString(),
            capacity: typeForm.value.capacity,
            description: typeForm.value.description || null,
            amenities: typeForm.value.amenities || null,
            image_url: typeForm.value.image_url || null,
          })
          ElMessage.success('房型更新成功')
        }
        dialogVisible.value = false
        loadRoomTypes()
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || '操作失败，参数冲突。'
        ElMessage.error(errorMsg)
      } finally {
        submitLoading.value = false
      }
    }
  })
}
</script>

<template>
  <div class="admin-roomtypes-panel">
    <!-- Header banner -->
    <div class="panel-header-row">
      <div class="panel-header-left">
        <div class="header-icon">
          <el-icon><Setting /></el-icon>
        </div>
        <div class="title-cell">
          <h3>客房房型设置</h3>
          <p>在此维护酒店销售的各类客房类型，设定其基准每晚房价和允许的入住人数上限。</p>
        </div>
        <span v-if="total > 0" class="stat-chip">共 {{ total }} 种房型</span>
      </div>
      <el-button type="primary" class="add-btn" :icon="Plus" @click="openAddDialog">
        新增客房房型
      </el-button>
    </div>

    <!-- Table List -->
    <div class="table-wrapper">
      <el-table
        v-loading="loading"
        :data="roomTypes"
        style="width: 100%"
        class="admin-table-premium"
        :max-height="560"
        empty-text="暂无房型数据"
      >
        <!-- ID -->
        <el-table-column prop="id" label="房型ID" width="80" />
        
        <!-- Name -->
        <el-table-column label="房型名称" min-width="150">
          <template #default="{ row }">
            <span class="room-type-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        
        <!-- Base Price -->
        <el-table-column label="基准价格 (每晚)" width="150">
          <template #default="{ row }">
            <span class="price-val">¥{{ row.base_price }}</span>
          </template>
        </el-table-column>
        
        <!-- Capacity -->
        <el-table-column label="容纳人数" width="90">
          <template #default="{ row }">
            <span class="capacity-val">{{ row.capacity }} 人</span>
          </template>
        </el-table-column>
        
        <!-- Rooms Count -->
        <el-table-column prop="total_rooms" label="房间数量" width="100" />
        
        <!-- Description -->
        <el-table-column label="房型简介" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="desc-text">{{ row.description || '-' }}</span>
          </template>
        </el-table-column>
        
        <!-- Amenities -->
        <el-table-column label="设施配置" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="desc-text">{{ row.amenities || '-' }}</span>
          </template>
        </el-table-column>
        
        <!-- Cover Image -->
        <el-table-column label="封面图" width="120">
          <template #default="{ row }">
            <div v-if="row.image_url" class="thumbnail-wrapper">
              <el-image :src="row.image_url" class="room-thumbnail-mini" fit="cover" />
            </div>
            <span v-else class="desc-text">-</span>
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

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '新增客房房型' : '编辑客房房型'"
      width="480px"
      align-center
      class="custom-admin-dialog"
    >
      <el-form 
        ref="formRef"
        :model="typeForm" 
        :rules="rules"
        label-position="top"
        class="custom-form"
      >
        <el-form-item label="房型名称" prop="name">
          <el-input v-model="typeForm.name" placeholder="请输入房型名称 (如 总统套房)" />
        </el-form-item>
        
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="基准房价 (每晚价格)" prop="base_price">
              <el-input-number 
                v-model="typeForm.base_price" 
                :min="10" 
                :max="99999" 
                style="width: 100%" 
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大容纳人数" prop="capacity">
              <el-input-number 
                v-model="typeForm.capacity" 
                :min="1" 
                :max="20" 
                style="width: 100%" 
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="初始房间数量" prop="total_rooms" v-if="dialogType === 'add'">
          <el-input-number 
            v-model="typeForm.total_rooms" 
            :min="0" 
            :max="100" 
            style="width: 100%" 
          />
        </el-form-item>
        
        <el-form-item label="房型简介">
          <el-input
            v-model="typeForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述房型特色，例如：舒适的标准双床房..."
            maxlength="512"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="设施配置标签">
          <el-input
            v-model="typeForm.amenities"
            placeholder="使用英文逗号分隔，如：WiFi,空调,独立卫浴"
            maxlength="512"
          />
        </el-form-item>
        
        <el-form-item label="封面图片链接">
          <el-input
            v-model="typeForm.image_url"
            placeholder="https://images.unsplash.com/photo-xxx"
            maxlength="256"
          />
          <div v-if="typeForm.image_url" class="image-preview-box">
            <el-image :src="typeForm.image_url" class="preview-img" fit="cover" />
          </div>
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
.admin-roomtypes-panel {
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

/* Cell content layouts */
.room-type-name {
  font-weight: 700;
  color: var(--text-primary);
  font-size: 14px;
}

.price-val {
  font-family: var(--font-title);
  font-weight: 800;
  color: var(--primary-color);
  font-size: 14px;
}

.capacity-val {
  font-size: 13px;
  color: var(--text-secondary);
}

.desc-text {
  font-size: 12px;
  color: var(--text-muted);
}

.thumbnail-wrapper {
  width: 68px;
  height: 44px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid rgba(99, 102, 241, 0.15);
  box-shadow: 0 4px 10px -3px rgba(0, 0, 0, 0.08);
}

.room-thumbnail-mini {
  width: 100%;
  height: 100%;
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

.image-preview-box {
  width: 100%;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--card-border);
  margin-top: 10px;
}

.preview-img {
  width: 100%;
  max-height: 140px;
  display: block;
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
