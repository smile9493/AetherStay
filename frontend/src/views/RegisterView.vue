<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = ref({ username: '', password: '', confirm: '' })

async function handleRegister() {
  if (form.value.password !== form.value.confirm) {
    ElMessage.warning('两次密码不一致')
    return
  }
  try {
    await auth.register(form.value.username, form.value.password)
    ElMessage.success('注册成功')
    router.push('/')
  } catch {
    ElMessage.error('注册失败，用户名可能已存在')
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <template #header><h2>注册</h2></template>
      <el-form :model="form" label-width="80px" @submit.prevent="handleRegister">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="3-64 个字符" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="至少 6 个字符" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.confirm" type="password" placeholder="再次输入密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="auth.loading" native-type="submit">注册</el-button>
          <el-button @click="router.push('/login')">已有账号</el-button>
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
