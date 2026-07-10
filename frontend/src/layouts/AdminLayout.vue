<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { Cpu, List, House, Setting, User } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
</script>

<template>
  <div class="admin-layout">
    <el-row :gutter="24">
      <!-- Sidebar Menu -->
      <el-col :xs="24" :md="5" class="admin-sidebar-col">
        <div class="admin-sidebar glass-panel">
          <div class="sidebar-header">
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
              :class="{ active: route.name === 'admin-users' }"
              @click="router.push('/admin/users')"
            >
              <el-icon><User /></el-icon>
              <span>账户权限</span>
            </div>
          </div>
        </div>
      </el-col>

      <!-- Main Admin Content Area -->
      <el-col :xs="24" :md="19" class="admin-content-col">
        <div class="admin-body-card glass-panel">
          <RouterView />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.admin-layout {
  padding: 12px 0 24px;
}

.admin-sidebar-col {
  margin-bottom: 24px;
}

.admin-sidebar {
  padding: 24px;
  background: rgba(255, 255, 255, 0.7);
}

.sidebar-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--card-border);
}

.sidebar-header h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.sidebar-header p {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.sidebar-menu {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.menu-item:hover {
  background: rgba(99, 102, 241, 0.05);
  color: var(--primary-color);
}

.menu-item.active {
  background: var(--primary-color);
  color: #fff;
  font-weight: 600;
  box-shadow: 0 4px 12px -3px rgba(99, 102, 241, 0.4);
}

.admin-body-card {
  padding: 28px;
  background: rgba(255, 255, 255, 0.7);
  min-height: 520px;
}

@media (max-width: 768px) {
  .admin-sidebar {
    padding: 16px;
  }
  .sidebar-menu {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: space-around;
  }
  .menu-item {
    padding: 8px 12px;
    font-size: 13px;
  }
}
</style>
