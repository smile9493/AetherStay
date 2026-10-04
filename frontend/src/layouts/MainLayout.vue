<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

onMounted(() => auth.fetchUser())

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}

function isActive(path: string) {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}
</script>

<template>
  <div class="layout">
    <header class="site-header">
      <div class="container site-header__inner">
        <button class="brand" type="button" @click="router.push('/')">
          <span class="brand__mark">
            <el-icon :size="18"><House /></el-icon>
          </span>
          <span class="brand__name">AetherStay</span>
        </button>

        <nav class="site-nav" aria-label="主导航">
          <RouterLink to="/" class="nav-link" :class="{ 'is-active': isActive('/') }">首页</RouterLink>
          <RouterLink to="/rooms" class="nav-link" :class="{ 'is-active': isActive('/rooms') }">客房预订</RouterLink>
          <RouterLink to="/agent" class="nav-link" :class="{ 'is-active': isActive('/agent') }">智能助手</RouterLink>
          <RouterLink
            v-if="auth.user"
            to="/bookings"
            class="nav-link"
            :class="{ 'is-active': isActive('/bookings') }"
          >
            我的订单
          </RouterLink>
          <RouterLink
            v-if="auth.user?.role === 'admin'"
            to="/about"
            class="nav-link"
            :class="{ 'is-active': isActive('/about') }"
          >
            项目介绍
          </RouterLink>
        </nav>

        <div class="user-area">
          <template v-if="auth.user">
            <span class="user-area__name">{{ auth.user.username }}</span>
            <el-button text @click="handleLogout">退出</el-button>
          </template>
          <template v-else>
            <el-button text @click="router.push('/login')">登录</el-button>
            <el-button type="primary" @click="router.push('/register')">注册</el-button>
          </template>
        </div>
      </div>
    </header>

    <main class="site-main">
      <div class="container">
        <RouterView />
      </div>
    </main>

    <footer class="site-footer">
      <div class="container">AetherStay &copy; 2026 — 酒店客房预订管理系统</div>
    </footer>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.site-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-border);
}

.site-header__inner {
  display: flex;
  align-items: center;
  gap: 32px;
  height: var(--header-h);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  font: inherit;
}

.brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: var(--brand-600);
  color: #ffffff;
}

.brand__name {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.2px;
  color: var(--text-primary);
  transition: color var(--transition-fast);
}

.brand:hover .brand__name {
  color: var(--brand-700);
}

.site-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-link {
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--text-secondary);
  transition: color var(--transition-fast), background-color var(--transition-fast);
  white-space: nowrap;
}

.nav-link:hover {
  color: var(--brand-700);
  background: var(--brand-50);
}

.nav-link.is-active {
  color: var(--brand-700);
  font-weight: 600;
  background: var(--brand-50);
}

.user-area {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.user-area__name {
  font-size: 14px;
  color: var(--text-secondary);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-main {
  flex: 1;
  padding: 32px 0 48px;
}

.site-footer {
  padding: 24px 0;
  border-top: 1px solid var(--color-border);
  text-align: center;
  font-size: 14px;
  color: var(--text-tertiary);
}

@media (max-width: 768px) {
  .site-header__inner {
    gap: 16px;
  }

  .brand__name {
    font-size: 16px;
  }

  .nav-link {
    padding: 6px 8px;
  }

  .site-main {
    padding: 24px 0 32px;
  }
}

@media (max-width: 640px) {
  .user-area__name {
    display: none;
  }
}
</style>