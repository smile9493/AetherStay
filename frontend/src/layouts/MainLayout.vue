<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { House, Calendar, Ticket, Setting, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

onMounted(() => auth.fetchUser())

const isAdminRoute = computed(() => route.path.startsWith('/admin'))

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout-container">
    <el-header class="nav-header">
      <div class="header-inner glass-panel" :class="{ 'admin-width': isAdminRoute }">
        <div class="logo-area" @click="router.push('/')">
          <el-icon class="logo-icon" :size="24"><House /></el-icon>
          <span class="logo-text">AetherStay</span>
        </div>
        
        <div class="menu-area">
          <router-link to="/" class="nav-item" :class="{ active: route.name === 'home' }">
            <el-icon><House /></el-icon>
            <span>首页</span>
          </router-link>
          <router-link to="/rooms" class="nav-item" :class="{ active: route.name === 'rooms' }">
            <el-icon><Calendar /></el-icon>
            <span>客房预订</span>
          </router-link>
          <router-link
            v-if="auth.user"
            to="/bookings"
            class="nav-item"
            :class="{ active: route.name === 'bookings' }"
          >
            <el-icon><Ticket /></el-icon>
            <span>我的订单</span>
          </router-link>
          <router-link 
            v-if="auth.user && auth.user.role === 'admin'" 
            to="/admin/dashboard" 
            class="nav-item admin-nav" 
            :class="{ active: route.path.startsWith('/admin') }"
          >
            <el-icon><Setting /></el-icon>
            <span>管理后台</span>
          </router-link>
        </div>

        <div class="auth-area">
          <template v-if="auth.user">
            <el-dropdown trigger="click" placement="bottom-end">
              <div class="user-profile">
                <el-avatar :size="32" class="user-avatar">
                  {{ auth.user.username.charAt(0).toUpperCase() }}
                </el-avatar>
                <span class="user-name">{{ auth.user.username }}</span>
                <el-tag size="small" :type="auth.user.role === 'admin' ? 'danger' : 'success'" class="role-tag">
                  {{ auth.user.role === 'admin' ? '管理员' : '贵宾' }}
                </el-tag>
              </div>
              <template #dropdown>
                <el-dropdown-menu class="user-dropdown-menu">
                  <el-dropdown-item v-if="auth.user.role === 'admin'" @click="router.push('/admin/dashboard')">
                    <el-icon><Setting /></el-icon> 管理后台
                  </el-dropdown-item>
                  <el-dropdown-item @click="router.push('/bookings')">
                    <el-icon><Ticket /></el-icon> 我的订单
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="handleLogout" class="logout-item">
                    <el-icon><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <div class="auth-buttons">
              <span class="login-link" @click="router.push('/login')">登录</span>
              <el-button type="primary" class="register-btn" @click="router.push('/register')">
                免费注册
              </el-button>
            </div>
          </template>
        </div>
      </div>
    </el-header>
    
    <el-main class="main-content" :class="{ 'admin-width': isAdminRoute }">
      <div class="content-wrapper">
        <RouterView v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </RouterView>
      </div>
    </el-main>
    
    <el-footer class="nav-footer">
      <div class="footer-content" :class="{ 'admin-width': isAdminRoute }">
        <p class="copyright">AetherStay 酒店 &copy; 2026 — 品质住宿，安心之选</p>
        <p class="tech-stack">客服热线 400-888-0000 · 全年无休</p>
      </div>
    </el-footer>
  </el-container>
</template>

<style scoped>
.layout-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.nav-header {
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 12px 24px;
  height: 80px;
}

.header-inner {
  max-width: 1280px;
  height: 56px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-radius: var(--radius-md) !important;
  background: rgba(255, 255, 255, 0.75) !important;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.logo-icon {
  color: var(--primary-color);
}

.logo-text {
  font-family: var(--font-title);
  font-size: 20px;
  font-weight: 800;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.menu-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.25s ease;
}

.nav-item:hover {
  background: rgba(99, 102, 241, 0.05);
  color: var(--primary-color);
}

.nav-item.active {
  background: var(--primary-light);
  color: var(--primary-color);
  font-weight: 600;
}

.nav-item.admin-nav:hover {
  background: rgba(239, 68, 68, 0.05);
  color: #ef4444;
}

.nav-item.admin-nav.active {
  background: #fee2e2;
  color: #ef4444;
}

.auth-area {
  display: flex;
  align-items: center;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: background-color 0.2s;
}

.user-profile:hover {
  background: rgba(0, 0, 0, 0.02);
}

.user-avatar {
  background: var(--primary-color);
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.role-tag {
  border-radius: 4px;
  font-weight: 600;
}

.user-dropdown-menu :deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 8px 16px;
}

.logout-item {
  color: #ef4444 !important;
}

.auth-buttons {
  display: flex;
  align-items: center;
  gap: 16px;
}

.login-link {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.2s;
}

.login-link:hover {
  color: var(--primary-color);
}

.register-btn {
  border-radius: var(--radius-sm);
  font-weight: 500;
  padding: 8px 16px;
  box-shadow: 0 4px 12px -3px rgba(99, 102, 241, 0.3);
}

.main-content {
  flex: 1;
  padding: 24px;
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
}

.content-wrapper {
  min-height: calc(100vh - 200px);
}

.nav-footer {
  border-top: 1px solid var(--card-border);
  padding: 24px;
  text-align: center;
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(8px);
}

.footer-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.copyright {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.tech-stack {
  font-size: 11px;
  color: var(--text-muted);
}

.main-content.admin-width {
  flex: 0 0 auto;
}

.main-content.admin-width .content-wrapper {
  min-height: auto;
}

.admin-width {
  max-width: 1680px !important;
}
</style>
