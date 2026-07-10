<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { CircleClose, Lock, View, Edit, Medal } from '@element-plus/icons-vue'
import AdminPagination from '@/components/admin/AdminPagination.vue'
import { usePagination, type PaginatedResult } from '@/composables/usePagination'

interface UserItem {
  id: number
  username: string
  display_name?: string | null
  role: string
  created_at: string
  is_active: boolean
  phone?: string | null
  email?: string | null
  membership_tier: string
  membership_points: number
}

interface UserBookingStats {
  total_bookings: number
  completed_bookings: number
  total_spent: number
  last_booking_at: string | null
}

interface UserDetail extends UserItem {
  admin_notes?: string | null
  stats: UserBookingStats
}

const MEMBERSHIP_TIERS: Record<string, { label: string; discount: string; desc: string }> = {
  standard: { label: '普通会员', discount: '无', desc: '注册即享基础预订服务' },
  silver: { label: '银卡会员', discount: '95折', desc: '累计消费达标或管理员升级' },
  gold: { label: '金卡会员', discount: '9折', desc: '高价值客户专属礼遇' },
  platinum: { label: '白金会员', discount: '85折', desc: '顶级贵宾尊享权益' },
}

const users = ref<UserItem[]>([])
const loading = ref(false)
const tierFilter = ref('')
const { currentPage, pageSize, total, pageStart, pageEnd, applyPageResult, resetPage } = usePagination(20)

const detailVisible = ref(false)
const detailLoading = ref(false)
const userDetail = ref<UserDetail | null>(null)

const editVisible = ref(false)
const editSubmitting = ref(false)
const editingUser = ref<UserItem | null>(null)
const editForm = ref({
  display_name: '',
  phone: '',
  email: '',
  membership_tier: 'standard',
  membership_points: 0,
  is_active: true,
  admin_notes: '',
})

onMounted(loadUsers)

function tierLabel(tier: string) {
  return MEMBERSHIP_TIERS[tier]?.label ?? tier
}

async function loadUsers() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (tierFilter.value) params.membership_tier = tierFilter.value

    const { data } = await api.get<PaginatedResult<UserItem>>('/admin/users', { params })
    users.value = data.items
    applyPageResult(data)
  } catch {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

function handleTierFilter() {
  resetPage()
  loadUsers()
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

async function openDetail(user: UserItem) {
  detailVisible.value = true
  detailLoading.value = true
  userDetail.value = null
  try {
    const { data } = await api.get<UserDetail>(`/admin/users/${user.id}`)
    userDetail.value = data
  } catch {
    ElMessage.error('加载用户详情失败')
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

function openEdit(user: UserItem) {
  editingUser.value = user
  editForm.value = {
    display_name: user.display_name ?? '',
    phone: user.phone ?? '',
    email: user.email ?? '',
    membership_tier: user.membership_tier,
    membership_points: user.membership_points,
    is_active: user.is_active,
    admin_notes: '',
  }
  editVisible.value = true
  if (detailVisible.value && userDetail.value?.id === user.id) {
    editForm.value.admin_notes = userDetail.value.admin_notes ?? ''
  } else {
    api.get<UserDetail>(`/admin/users/${user.id}`).then(({ data }) => {
      editForm.value.admin_notes = data.admin_notes ?? ''
    }).catch(() => {})
  }
}

function openEditFromDetail() {
  if (!userDetail.value) return
  const u = userDetail.value
  editingUser.value = u
  editForm.value = {
    display_name: u.display_name ?? '',
    phone: u.phone ?? '',
    email: u.email ?? '',
    membership_tier: u.membership_tier,
    membership_points: u.membership_points,
    is_active: u.is_active,
    admin_notes: u.admin_notes ?? '',
  }
  editVisible.value = true
}

async function submitEdit() {
  if (!editingUser.value) return
  editSubmitting.value = true
  try {
    const { data } = await api.put<UserDetail>(`/admin/users/${editingUser.value.id}`, {
      display_name: editForm.value.display_name || null,
      phone: editForm.value.phone || null,
      email: editForm.value.email || null,
      membership_tier: editForm.value.membership_tier,
      membership_points: editForm.value.membership_points,
      is_active: editForm.value.is_active,
      admin_notes: editForm.value.admin_notes || null,
    })
    ElMessage.success('用户信息已更新')
    editVisible.value = false
    loadUsers()
    if (detailVisible.value && userDetail.value?.id === data.id) {
      userDetail.value = data
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    editSubmitting.value = false
  }
}

async function disableUserAccount(user: UserItem) {
  try {
    await ElMessageBox.confirm(
      `确定要停用账户 "${user.username}" 吗？停用后该账户将无法登录系统。`,
      '账户禁用警告',
      {
        type: 'warning',
        confirmButtonText: '确定停用',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      },
    )
    loading.value = true
    await api.post(`/admin/users/${user.id}/disable`)
    ElMessage.success(`账户 "${user.username}" 已被成功禁用`)
    loadUsers()
    if (userDetail.value?.id === user.id) {
      userDetail.value = { ...userDetail.value, is_active: false }
    }
  } catch {
    // dismissed
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="admin-users-panel admin-table-page">
    <div class="panel-header">
      <div class="header-icon">
        <el-icon><Lock /></el-icon>
      </div>
      <div class="header-info">
        <h3>账户与权限管理</h3>
        <p>管理注册会员资料、等级权益与账户状态，支持详情查看与编辑。</p>
      </div>
      <span v-if="total > 0" class="stat-chip">共 {{ total }} 个账户</span>
    </div>

    <div class="filter-bar glass-panel-inner">
      <el-form :inline="true" @submit.prevent="handleTierFilter">
        <el-form-item label="会员等级">
          <el-select v-model="tierFilter" placeholder="全部等级" clearable style="width: 160px" @change="handleTierFilter">
            <el-option
              v-for="(meta, key) in MEMBERSHIP_TIERS"
              :key="key"
              :label="meta.label"
              :value="key"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </div>

    <div class="table-wrapper">
      <el-table
        v-loading="loading"
        :data="users"
        style="width: 100%"
        class="admin-table-premium"
        height="100%"
        empty-text="暂无用户数据"
      >
        <el-table-column prop="id" label="用户ID" width="90" />

        <el-table-column label="账户信息" min-width="180">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="32" class="user-avatar-premium">
                {{ (row.display_name || row.username).charAt(0).toUpperCase() }}
              </el-avatar>
              <div class="user-cell-info">
                <strong>{{ row.display_name || row.username }}</strong>
                <span class="user-sub">@{{ row.username }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="会员等级" width="130">
          <template #default="{ row }">
            <span class="tier-badge" :class="row.membership_tier">
              <el-icon><Medal /></el-icon>
              {{ tierLabel(row.membership_tier) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="积分" width="90" align="right">
          <template #default="{ row }">
            <span class="points-text">{{ row.membership_points }}</span>
          </template>
        </el-table-column>

        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <span class="role-badge" :class="row.role">
              {{ row.role === 'admin' ? '管理员' : '贵宾' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="注册时间" width="170">
          <template #default="{ row }">
            <span class="date-text">{{ new Date(row.created_at).toLocaleString() }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="status-badge" :class="{ active: row.is_active, disabled: !row.is_active }">
              {{ row.is_active ? '正常' : '停用' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button size="small" :icon="View" @click="openDetail(row)">详情</el-button>
              <el-button size="small" type="primary" plain :icon="Edit" @click="openEdit(row)">编辑</el-button>
              <el-button
                v-if="row.is_active && row.role !== 'admin'"
                type="danger"
                size="small"
                plain
                :icon="CircleClose"
                @click="disableUserAccount(row)"
              >
                禁用
              </el-button>
            </div>
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

    <!-- Detail drawer -->
    <el-drawer v-model="detailVisible" title="会员详情" size="420px" destroy-on-close>
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="userDetail">
          <div class="detail-profile">
            <el-avatar :size="56" class="detail-avatar">
              {{ (userDetail.display_name || userDetail.username).charAt(0).toUpperCase() }}
            </el-avatar>
            <div>
              <h4>{{ userDetail.display_name || userDetail.username }}</h4>
              <p>@{{ userDetail.username }}</p>
              <span class="tier-badge large" :class="userDetail.membership_tier">
                {{ tierLabel(userDetail.membership_tier) }}
              </span>
            </div>
          </div>

          <div class="detail-section">
            <h5>会员权益</h5>
            <p class="tier-desc">{{ MEMBERSHIP_TIERS[userDetail.membership_tier]?.desc }}</p>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="lbl">预订折扣</span>
                <span class="val">{{ MEMBERSHIP_TIERS[userDetail.membership_tier]?.discount }}</span>
              </div>
              <div class="detail-item">
                <span class="lbl">积分</span>
                <span class="val">{{ userDetail.membership_points }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h5>联系信息</h5>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="lbl">手机</span>
                <span class="val">{{ userDetail.phone || '—' }}</span>
              </div>
              <div class="detail-item">
                <span class="lbl">邮箱</span>
                <span class="val">{{ userDetail.email || '—' }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h5>消费统计</h5>
            <div class="stats-cards">
              <div class="stat-card">
                <span class="num">{{ userDetail.stats.total_bookings }}</span>
                <span class="lbl">有效订单</span>
              </div>
              <div class="stat-card">
                <span class="num">{{ userDetail.stats.completed_bookings }}</span>
                <span class="lbl">已退房</span>
              </div>
              <div class="stat-card">
                <span class="num">¥{{ userDetail.stats.total_spent.toFixed(0) }}</span>
                <span class="lbl">累计消费</span>
              </div>
            </div>
            <p v-if="userDetail.stats.last_booking_at" class="last-booking">
              最近下单：{{ new Date(userDetail.stats.last_booking_at).toLocaleString() }}
            </p>
          </div>

          <div class="detail-section">
            <h5>账户状态</h5>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="lbl">角色</span>
                <span class="val">{{ userDetail.role === 'admin' ? '管理员' : '贵宾' }}</span>
              </div>
              <div class="detail-item">
                <span class="lbl">状态</span>
                <span class="val">{{ userDetail.is_active ? '正常启用' : '已停用' }}</span>
              </div>
              <div class="detail-item full">
                <span class="lbl">注册时间</span>
                <span class="val">{{ new Date(userDetail.created_at).toLocaleString() }}</span>
              </div>
            </div>
          </div>

          <div v-if="userDetail.admin_notes" class="detail-section">
            <h5>管理员备注</h5>
            <p class="admin-notes">{{ userDetail.admin_notes }}</p>
          </div>

          <div class="detail-actions">
            <el-button type="primary" :icon="Edit" @click="openEditFromDetail">编辑资料</el-button>
          </div>
        </template>
      </div>
    </el-drawer>

    <!-- Edit dialog -->
    <el-dialog v-model="editVisible" title="编辑会员资料" width="520px" destroy-on-close>
      <el-form label-width="100px" class="edit-form">
        <el-form-item label="显示名称">
          <el-input v-model="editForm.display_name" placeholder="可选，用于前台展示" maxlength="64" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="editForm.phone" placeholder="联系电话" maxlength="20" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="联系邮箱" maxlength="128" />
        </el-form-item>
        <el-form-item label="会员等级">
          <el-select v-model="editForm.membership_tier" style="width: 100%">
            <el-option
              v-for="(meta, key) in MEMBERSHIP_TIERS"
              :key="key"
              :label="`${meta.label}（${meta.discount}）`"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="会员积分">
          <el-input-number v-model="editForm.membership_points" :min="0" :max="9999999" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="editingUser?.role !== 'admin'" label="账户状态">
          <el-switch v-model="editForm.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="管理备注">
          <el-input
            v-model="editForm.admin_notes"
            type="textarea"
            :rows="3"
            maxlength="512"
            show-word-limit
            placeholder="仅管理员可见"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stat-chip {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-color);
  background: var(--primary-light);
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid rgba(99, 102, 241, 0.15);
  white-space: nowrap;
}

.filter-bar {
  padding: 12px 20px 4px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.4);
}

.table-wrapper {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.admin-table-premium :deep(th.el-table__cell) {
  background: rgba(255, 255, 255, 0.8) !important;
  font-weight: 700;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar-premium,
.detail-avatar {
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
  font-weight: 700;
}

.user-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.tier-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 20px;
}

.tier-badge.standard { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
.tier-badge.silver { background: #f8fafc; color: #64748b; border: 1px solid #cbd5e1; }
.tier-badge.gold { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.tier-badge.platinum { background: #f5f3ff; color: #6d28d9; border: 1px solid #ddd6fe; }

.tier-badge.large {
  margin-top: 8px;
  font-size: 12px;
}

.points-text {
  font-weight: 700;
  color: var(--primary-color);
}

.role-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 20px;
}

.role-badge.admin { background: #fdf2f2; color: #dc2626; }
.role-badge.customer { background: #ecfdf5; color: #059669; }

.date-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-sm);
}

.status-badge.active { background: rgba(16, 185, 129, 0.1); color: #059669; }
.status-badge.disabled { background: rgba(148, 163, 184, 0.1); color: #475569; }

.table-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.detail-body {
  min-height: 200px;
}

.detail-profile {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
}

.detail-profile h4 {
  font-size: 18px;
  font-weight: 800;
}

.detail-profile p {
  font-size: 12px;
  color: var(--text-muted);
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section h5 {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.tier-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.detail-item {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(99, 102, 241, 0.06);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}

.detail-item.full {
  grid-column: 1 / -1;
}

.detail-item .lbl {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.detail-item .val {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.stat-card {
  text-align: center;
  padding: 12px 8px;
  background: var(--primary-light);
  border-radius: var(--radius-md);
  border: 1px solid rgba(99, 102, 241, 0.1);
}

.stat-card .num {
  display: block;
  font-size: 18px;
  font-weight: 800;
  color: var(--primary-color);
}

.stat-card .lbl {
  font-size: 10px;
  color: var(--text-muted);
}

.last-booking {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-secondary);
}

.admin-notes {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  padding: 10px;
  background: #fffbeb;
  border-radius: var(--radius-sm);
  border: 1px solid #fef3c7;
}

.detail-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid rgba(99, 102, 241, 0.1);
}
</style>
