<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = ref({ username: '', password: '' })

async function handleLogin() {
  try {
    await auth.login(form.value.username, form.value.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch {
    ElMessage.error('用户名或密码错误')
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-panel">
      <aside class="auth-brand">
        <span class="auth-brand__mark">
          <el-icon :size="22"><House /></el-icon>
        </span>
        <h1>AetherStay</h1>
        <p>酒店客房预订管理系统</p>
      </aside>

      <div class="auth-form">
        <h2>登录</h2>
        <p class="auth-form__sub">欢迎回来，请登录你的账号</p>

        <el-form :model="form" label-position="top" @submit.prevent="handleLogin">
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
          </el-form-item>
          <el-button type="primary" class="auth-submit" native-type="submit" :loading="auth.loading">
            登录
          </el-button>
          <p class="auth-switch">
            还没有账号？
            <RouterLink to="/register">立即注册</RouterLink>
          </p>
        </el-form>

        <RouterLink to="/" class="auth-home">返回首页</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 48px 16px;
  background: linear-gradient(160deg, var(--brand-50) 0%, var(--gray-50) 45%, var(--gray-100) 100%);
}

.auth-panel {
  display: grid;
  grid-template-columns: 320px 400px;
  width: 100%;
  max-width: 720px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.auth-brand {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  padding: 40px 32px;
  background: linear-gradient(150deg, var(--brand-700) 0%, var(--brand-900) 100%);
  color: #ffffff;
}

.auth-brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.16);
}

.auth-brand h1 {
  font-size: 24px;
  color: #ffffff;
}

.auth-brand p {
  font-size: 14px;
  color: var(--brand-100);
}

.auth-form {
  padding: 40px 32px;
}

.auth-form h2 {
  font-size: 20px;
}

.auth-form__sub {
  margin: 8px 0 24px;
  font-size: 14px;
  color: var(--text-secondary);
}

.auth-submit {
  width: 100%;
}

.auth-switch {
  margin-top: 16px;
  font-size: 14px;
  color: var(--text-secondary);
  text-align: center;
}

.auth-home {
  display: inline-block;
  margin-top: 24px;
  font-size: 14px;
  color: var(--text-tertiary);
}

.auth-home:hover {
  color: var(--brand-600);
}

@media (max-width: 640px) {
  .auth-panel {
    grid-template-columns: 1fr;
    max-width: 400px;
  }

  .auth-brand {
    flex-direction: row;
    align-items: center;
    gap: 12px;
    padding: 24px;
  }

  .auth-brand h1 {
    font-size: 18px;
  }

  .auth-brand p {
    display: none;
  }

  .auth-form {
    padding: 24px;
  }
}
</style>