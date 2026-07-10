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

const roomTypes = ref<RoomType[]>([])
const loading = ref(false)

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
    const { data } = await api.get<RoomType[]>('/admin/room-types')
    roomTypes.value = data
  } catch {
    ElMessage.error('加载房型列表失败')
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  dialogType.value = 'add'
  typeForm.value = {
    id: undefined,
    name: '',
    base_price: 199,
    capacity: 2,
    total_rooms: 0,
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
          })
          ElMessage.success('新增房型成功')
        } else {
          await api.put(`/admin/room-types/\${typeForm.value.id}`, {
            name: typeForm.value.name,
            base_price: typeForm.value.base_price.toString(),
            capacity: typeForm.value.capacity,
            total_rooms: typeForm.value.total_rooms,
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
    <div class="panel-header-row">
      <div class="title-cell">
        <h3>客房房型设置</h3>
        <p>在此维护酒店销售的各类客房类型，包括其基准每晚房价和最大允许入住人数。</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openAddDialog">
        新增客房房型
      </el-button>
    </div>

    <!-- Table List -->
    <el-table v-loading="loading" :data="roomTypes" stripe style="width: 100%" class="admin-table">
      <el-table-column prop="id" label="房型ID" width="90" />
      <el-table-column prop="name" label="房型名称" min-width="150">
        <template #default="{ row }">
          <strong>{{ row.name }}</strong>
        </template>
      </el-table-column>
      <el-table-column label="基准价格 (每晚)" width="150">
        <template #default="{ row }">
          <span class="price-val">¥{{ row.base_price }}</span>
        </template>
      </el-table-column>
      <el-table-column label="最大容纳" width="100">
        <template #default="{ row }">{{ row.capacity }} 人</template>
      </el-table-column>
      <el-table-column prop="total_rooms" label="客房物理总量" width="120" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="primary" :icon="Edit" size="small" @click="openEditDialog(row)">
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '新增客房房型' : '编辑客房房型'"
      width="440px"
      align-center
    >
      <el-form 
        ref="formRef"
        :model="typeForm" 
        :rules="rules"
        label-position="top"
      >
        <el-form-item label="房型名称" prop="name">
          <el-input v-model="typeForm.name" placeholder="请输入房型名称 (如 总统套房)" />
        </el-form-item>
        <el-form-item label="基准房价 (每晚价格)" prop="base_price">
          <el-input-number 
            v-model="typeForm.base_price" 
            :min="10" 
            :max="99999" 
            style="width: 100%" 
          />
        </el-form-item>
        <el-form-item label="最大容纳人数" prop="capacity">
          <el-input-number 
            v-model="typeForm.capacity" 
            :min="1" 
            :max="20" 
            style="width: 100%" 
          />
        </el-form-item>
        <el-form-item label="初始房间数量" prop="total_rooms" v-if="dialogType === 'add'">
          <el-input-number 
            v-model="typeForm.total_rooms" 
            :min="0" 
            :max="100" 
            style="width: 100%" 
          />
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
.admin-roomtypes-panel {
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

.price-val {
  color: var(--primary-color);
  font-weight: 700;
}
</style>
