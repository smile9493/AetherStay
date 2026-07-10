<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

onMounted(() => auth.fetchUser())

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="logo" @click="router.push('/')">
        <el-icon :size="24"><House /></el-icon>
        <span>AetherStay</span>
      </div>
      <el-menu mode="horizontal" :ellipsis="false" router>
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/rooms">客房预订</el-menu-item>
        <el-menu-item v-if="auth.user" index="/bookings">我的订单</el-menu-item>
      </el-menu>
      <div class="user-area">
        <template v-if="auth.user">
          <span class="username">{{ auth.user.username }}</span>
          <el-button size="small" @click="handleLogout">退出</el-button>
        </template>
        <template v-else>
          <el-button size="small" @click="router.push('/login')">登录</el-button>
          <el-button size="small" type="primary" @click="router.push('/register')">注册</el-button>
        </template>
      </div>
    </el-header>
    <el-main>
      <RouterView />
    </el-main>
    <el-footer class="footer">
      AetherStay &copy; 2026 — 酒店客房预订管理系统
    </el-footer>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  gap: 24px;
  border-bottom: 1px solid var(--el-border-color-light);
  padding: 0 24px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-color-primary);
  cursor: pointer;
  white-space: nowrap;
}
.user-area {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
.footer {
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
