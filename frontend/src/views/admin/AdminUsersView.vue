<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { CircleClose, Lock } from '@element-plus/icons-vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import { usePagination, type PaginatedResult } from '@/composables/usePagination'

interface UserItem {
  id: number
  username: string
  role: string
  created_at: string
  is_active: boolean
}

const users = ref<UserItem[]>([])
const loading = ref(false)
const { currentPage, pageSize, total, pageStart, pageEnd, applyPageResult } = usePagination(20)

onMounted(loadUsers)

async function loadUsers() {
  loading.value = true
  try {
    const { data } = await api.get<PaginatedResult<UserItem>>('/admin/users', {
      params: { page: currentPage.value, page_size: pageSize.value },
    })
    users.value = data.items
    applyPageResult(data)
  } catch {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadUsers()
}

function handleSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadUsers()
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
    <!-- Header panel -->
    <div class="panel-header">
      <div class="header-icon">
        <el-icon><Lock /></el-icon>
      </div>
      <div class="header-info">
        <h3>账户与权限管理</h3>
        <p>监控系统内部的注册用户，核实角色分类并对有违规异常行为的账号执行紧急禁用挂起。</p>
      </div>
      <div v-if="total > 0" class="header-stats">
        <span class="stat-chip">共 {{ total }} 个账户</span>
      </div>
    </div>

    <!-- Table List -->
    <div class="table-wrapper">
      <el-table
        v-loading="loading"
        :data="users"
        style="width: 100%"
        class="admin-table-premium"
        :max-height="560"
        empty-text="暂无用户数据"
      >
        <!-- ID -->
        <el-table-column prop="id" label="用户ID" width="100" />
        
        <!-- Username and Profile -->
        <el-table-column label="账户信息" min-width="160">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="32" class="user-avatar-premium">
                {{ row.username.charAt(0).toUpperCase() }}
              </el-avatar>
              <div class="user-cell-info">
                <strong>{{ row.username }}</strong>
                <span class="user-sub">注册账号</span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <!-- Role -->
        <el-table-column label="角色身份" width="140">
          <template #default="{ row }">
            <span class="role-badge" :class="row.role">
              {{ row.role === 'admin' ? '系统管理员' : '普通贵宾' }}
            </span>
          </template>
        </el-table-column>
        
        <!-- Registration date -->
        <el-table-column label="注册时间" width="200">
          <template #default="{ row }">
            <span class="date-text">{{ new Date(row.created_at).toLocaleString() }}</span>
          </template>
        </el-table-column>
        
        <!-- Account status -->
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <span class="status-badge" :class="{ 'active': row.is_active, 'disabled': !row.is_active }">
              {{ row.is_active ? '正常启用' : '已停用' }}
            </span>
          </template>
        </el-table-column>
        
        <!-- Controls -->
        <el-table-column label="安全管理" width="140" fixed="right">
          <template #default="{ row }">
            <el-button 
              v-if="row.is_active && row.role !== 'admin'" 
              type="danger" 
              size="small" 
              plain
              class="disable-btn"
              :icon="CircleClose"
              @click="disableUserAccount(row)"
            >
              禁用账户
            </el-button>
            <span v-else-if="row.role === 'admin'" class="admin-tip">受系统保护</span>
            <span v-else class="disabled-tip">已执行停用</span>
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
  </div>
</template>

<style scoped>
.admin-users-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.header-info {
  flex: 1;
  min-width: 200px;
}

.header-stats {
  margin-left: auto;
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

.panel-header h3 {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary);
}

.panel-header p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
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
.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar-premium {
  background: var(--accent-gradient);
  font-weight: 700;
  color: #fff;
}

.user-cell-info {
  display: flex;
  flex-direction: column;
}

.user-cell-info strong {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 700;
}

.user-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.role-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 20px;
  display: inline-block;
}

.role-badge.admin {
  background: #fdf2f2;
  color: #dc2626;
  border: 1px solid #fde8e8;
}

.role-badge.customer {
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #d1fae5;
}

.date-text {
  font-size: 13px;
  color: var(--text-secondary);
}

.status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  display: inline-block;
}

.status-badge.active {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-badge.disabled {
  background: rgba(148, 163, 184, 0.1);
  color: #475569;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.disable-btn {
  font-weight: 600;
  border-radius: 6px;
  transition: all 0.2s;
  border: 1px solid #fee2e2;
  color: #ef4444;
}

.disable-btn:hover {
  background: #fee2e2;
  border-color: #ef4444;
  transform: translateY(-1px);
}

.admin-tip {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.disabled-tip {
  font-size: 12px;
  color: #dc2626;
  font-weight: 500;
}
</style>
