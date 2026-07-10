<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { CircleClose } from '@element-plus/icons-vue'

interface UserItem {
  id: number
  username: string
  role: string
  created_at: string
  is_active: boolean
}

const users = ref<UserItem[]>([])
const loading = ref(false)

onMounted(loadUsers)

async function loadUsers() {
  loading.value = true
  try {
    const { data } = await api.get<UserItem[]>('/admin/users')
    users.value = data
  } catch {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

async function disableUserAccount(user: UserItem) {
  try {
    await ElMessageBox.confirm(`确定要停用账户 "${user.username}" 吗？停用后该账户将无法登录系统。`, '账户禁用警告', { 
      type: 'warning',
      confirmButtonText: '确定停用',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger'
    })
    loading.value = true
    await api.post(`/admin/users/${user.id}/disable`)
    ElMessage.success(`账户 "${user.username}" 已被成功禁用`)
    loadUsers()
  } catch {
    // dismissed
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="admin-users-panel">
    <div class="panel-header">
      <h3>账户与权限管理</h3>
      <p>管理系统内的注册用户，分配或监控角色类型（管理员/客户），对违规账号进行紧急禁用挂起。</p>
    </div>

    <!-- Table List -->
    <el-table v-loading="loading" :data="users" stripe style="width: 100%" class="admin-table">
      <el-table-column prop="id" label="用户ID" width="90" />
      <el-table-column prop="username" label="用户名" min-width="120">
        <template #default="{ row }">
          <div class="user-cell">
            <el-avatar :size="24" style="background-color: var(--primary-color)">
              {{ row.username.charAt(0).toUpperCase() }}
            </el-avatar>
            <strong>{{ row.username }}</strong>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="角色身份" width="120">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'success'" size="small">
            {{ row.role === 'admin' ? '系统管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="注册时间" width="180">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="账号状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="plain">
            {{ row.is_active ? '正常启用' : '已停用挂起' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="管理控制" width="120">
        <template #default="{ row }">
          <el-button 
            v-if="row.is_active && row.role !== 'admin'" 
            type="danger" 
            size="small" 
            plain
            :icon="CircleClose"
            @click="disableUserAccount(row)"
          >
            禁用账户
          </el-button>
          <span v-else-if="row.role === 'admin'" class="admin-tip">受保护账户</span>
          <span v-else class="disabled-tip">已停用</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.admin-users-panel {
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

.admin-table {
  border: 1px solid var(--card-border);
  border-radius: var(--radius-sm);
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.admin-tip {
  font-size: 12px;
  color: var(--text-muted);
}

.disabled-tip {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
