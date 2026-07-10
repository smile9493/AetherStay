<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { Calendar, Cpu, List, House, Setting, User, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="admin-layout">
    <el-row :gutter="24" class="admin-row">
      <!-- Sidebar Menu -->
      <el-col :xs="24" :md="6" :lg="5" class="admin-sidebar-col">
        <div class="admin-sidebar glass-panel shadow-premium">
          <div class="sidebar-header">
            <div class="brand-badge">Admin</div>
            <h4>管理工作台</h4>
            <p>AetherStay Control Panel</p>
          </div>
          
          <div class="sidebar-menu">
            <div 
              class="menu-item" 
              :class="{ active: route.name === 'admin-dashboard' }"
              @click="router.push('/admin/dashboard')"
            >
              <el-icon><Cpu /></el-icon>
              <span>数据大盘</span>
            </div>
            <div 
              class="menu-item" 
              :class="{ active: route.name === 'admin-bookings' }"
              @click="router.push('/admin/bookings')"
            >
              <el-icon><List /></el-icon>
              <span>订单调度</span>
            </div>
            <div 
              class="menu-item" 
              :class="{ active: route.name === 'admin-rooms' }"
              @click="router.push('/admin/rooms')"
            >
              <el-icon><House /></el-icon>
              <span>客房资源</span>
            </div>
            <div 
              class="menu-item" 
              :class="{ active: route.name === 'admin-room-types' }"
              @click="router.push('/admin/room-types')"
            >
              <el-icon><Setting /></el-icon>
              <span>房型设置</span>
            </div>
            <div 
              class="menu-item" 
              :class="{ active: route.name === 'admin-inventory' }"
              @click="router.push('/admin/inventory')"
            >
              <el-icon><Calendar /></el-icon>
              <span>房态日历</span>
            </div>
            <div 
              class="menu-item" 
              :class="{ active: route.name === 'admin-users' }"
              @click="router.push('/admin/users')"
            >
              <el-icon><User /></el-icon>
              <span>账户权限</span>
            </div>
          </div>

          <!-- Bottom profile card for admin -->
          <div v-if="auth.user" class="sidebar-footer">
            <div class="admin-profile-card">
              <el-avatar :size="36" class="admin-avatar">
                {{ auth.user.username.charAt(0).toUpperCase() }}
              </el-avatar>
              <div class="admin-info">
                <span class="admin-name">{{ auth.user.username }}</span>
                <span class="admin-role">系统管理员</span>
              </div>
              <el-tooltip content="退出管理" placement="top">
                <div class="logout-btn" @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                </div>
              </el-tooltip>
            </div>
          </div>
        </div>
      </el-col>

      <!-- Main Admin Content Area -->
      <el-col :xs="24" :md="18" :lg="19" class="admin-content-col">
        <div class="admin-body-card glass-panel shadow-premium">
          <RouterView v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </RouterView>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.admin-layout {
  padding: 12px 0 32px;
}

.admin-row {
  align-items: stretch;
}

.admin-sidebar-col {
  margin-bottom: 24px;
}

.admin-sidebar {
  padding: 24px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.4);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: calc(100vh - 180px);
}

.shadow-premium {
  box-shadow: 0 15px 35px -10px rgba(99, 102, 241, 0.12), 
              0 0 0 1px rgba(99, 102, 241, 0.02),
              inset 0 1px 1px rgba(255, 255, 255, 0.8);
}

.sidebar-header {
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.1);
  position: relative;
}

.brand-badge {
  position: absolute;
  top: 0;
  right: 0;
  background: var(--accent-gradient);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.sidebar-header h4 {
  font-size: 18px;
  font-weight: 800;
  background: linear-gradient(135deg, var(--text-primary) 30%, #4f46e5 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.sidebar-header p {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  font-family: var(--font-title);
  letter-spacing: 0.5px;
}

.sidebar-menu {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.menu-item:hover {
  background: rgba(99, 102, 241, 0.06);
  color: var(--primary-color);
  transform: translateX(4px);
}

.menu-item.active {
  background: var(--accent-gradient);
  color: #fff;
  box-shadow: 0 8px 20px -6px rgba(99, 102, 241, 0.4);
}

.menu-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: #fff;
  border-radius: 0 4px 4px 0;
}

.sidebar-footer {
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid rgba(99, 102, 241, 0.1);
}

.admin-profile-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.5);
  padding: 10px 14px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(99, 102, 241, 0.08);
}

.admin-avatar {
  background: var(--accent-gradient);
  font-weight: 700;
  color: #fff;
}

.admin-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.admin-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.admin-role {
  font-size: 10px;
  color: var(--text-muted);
}

.logout-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #fee2e2;
  color: #ef4444;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: #fca5a5;
  color: #b91c1c;
  transform: rotate(90deg);
}

.admin-body-card {
  padding: 32px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.4);
  min-height: calc(100vh - 180px);
}

@media (max-width: 992px) {
  .admin-sidebar {
    min-height: auto;
  }
  .sidebar-menu {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 8px;
  }
  .menu-item {
    flex: 1 1 45%;
    padding: 10px 14px;
    font-size: 13px;
  }
  .sidebar-footer {
    display: none;
  }
}

@media (max-width: 576px) {
  .menu-item {
    flex: 1 1 100%;
  }
}
</style>
