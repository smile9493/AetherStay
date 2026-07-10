<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
    <el-card class="auth-card">
      <template #header><h2>登录</h2></template>
      <el-form :model="form" label-width="80px" @submit.prevent="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="auth.loading" native-type="submit">登录</el-button>
          <el-button @click="router.push('/register')">注册账号</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding: 64px 16px;
}
.auth-card {
  width: 420px;
}
.auth-card h2 {
  margin: 0;
  text-align: center;
}
</style>
