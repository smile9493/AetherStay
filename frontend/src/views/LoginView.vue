<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

const form = ref({ username: '', password: '' })
const ruleFormRef = ref()

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 64, message: '用户名长度需在 3 到 64 个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!ruleFormRef.value) return
  await ruleFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      try {
        await auth.login(form.value.username, form.value.password)
        ElMessage.success('登录成功，欢迎回来')
        const redirect = router.currentRoute.value.query.redirect as string
        router.push(redirect || '/')
      } catch (err: any) {
        const msg = err.response?.data?.detail || '用户名或密码错误'
        ElMessage.error(msg)
      }
    }
  })
}
</script>

<template>
  <div class="auth-container">
    <div class="glow-node glow-1"></div>
    <div class="glow-node glow-2"></div>
    
    <div class="auth-card-wrapper glass-panel">
      <div class="brand" @click="router.push('/')">
        <el-icon class="brand-icon" :size="32"><House /></el-icon>
        <span class="brand-name">AetherStay</span>
      </div>
      <h3 class="auth-title">尊享入住体验</h3>
      <p class="auth-subtitle">请输入您的账户凭证以登录系统</p>

      <el-form 
        ref="ruleFormRef"
        :model="form" 
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
        class="auth-form"
      >
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="form.username" 
            placeholder="请输入用户名" 
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="请输入密码" 
            :prefix-icon="Lock"
            show-password 
            size="large"
          />
        </el-form-item>
        
        <div class="form-actions">
          <el-button 
            type="primary" 
            class="submit-btn" 
            :loading="auth.loading" 
            native-type="submit"
            size="large"
          >
            登 录
          </el-button>
          <div class="auth-switch">
            <span>还没有账号？</span>
            <span class="link-text" @click="router.push('/register')">立即注册</span>
          </div>
        </div>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  background: radial-gradient(circle at 50% 50%, #0f172a, #020617);
  overflow: hidden;
  padding: 24px;
}

.glow-node {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.15;
  pointer-events: none;
}

.glow-1 {
  width: 400px;
  height: 400px;
  background: var(--primary-color);
  top: -100px;
  left: -100px;
}

.glow-2 {
  width: 500px;
  height: 500px;
  background: var(--accent-color);
  bottom: -150px;
  right: -100px;
}

.auth-card-wrapper {
  width: 100%;
  max-width: 460px;
  padding: 48px 40px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 30px 60px -15px rgba(0, 0, 0, 0.3);
  position: relative;
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  cursor: pointer;
  margin-bottom: 24px;
}

.brand-icon {
  color: var(--primary-color);
  filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.5));
}

.brand-name {
  font-family: var(--font-title);
  font-size: 26px;
  font-weight: 800;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.auth-title {
  text-align: center;
  font-size: 22px;
  color: #fff;
  margin-bottom: 8px;
  font-weight: 600;
}

.auth-subtitle {
  text-align: center;
  font-size: 14px;
  color: #94a3b8;
  margin-bottom: 36px;
}

.auth-form :deep(.el-form-item__label) {
  color: #cbd5e1;
  font-weight: 500;
  font-size: 13px;
  margin-bottom: 6px;
}

.auth-form :deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: none !important;
}

.auth-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--primary-color);
  background-color: rgba(255, 255, 255, 0.06);
}

.auth-form :deep(.el-input__inner) {
  color: #f8fafc;
  height: 48px;
}

.auth-form :deep(.el-input__icon) {
  color: #94a3b8;
}

.submit-btn {
  width: 100%;
  height: 48px;
  background: var(--accent-gradient);
  border: none;
  font-weight: 600;
  font-size: 16px;
  margin-top: 12px;
  box-shadow: 0 8px 24px -6px rgba(99, 102, 241, 0.5);
  transition: all 0.3s;
}

.submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px -4px rgba(99, 102, 241, 0.6);
}

.auth-switch {
  display: flex;
  justify-content: center;
  gap: 6px;
  font-size: 13px;
  color: #94a3b8;
  margin-top: 24px;
}

.link-text {
  color: var(--primary-color);
  cursor: pointer;
  font-weight: 500;
}

.link-text:hover {
  text-decoration: underline;
}
</style>
