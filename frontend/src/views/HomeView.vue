<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="home">
    <el-row :gutter="24" align="middle">
      <el-col :span="14">
        <h1>欢迎来到 AetherStay</h1>
        <p class="subtitle">智能酒店客房预订管理系统 — 支持 Web 端与 AI Agent 双模交互</p>
        <div class="actions">
          <el-button type="primary" size="large" @click="router.push('/rooms')">
            浏览客房
          </el-button>
          <el-button size="large" @click="router.push('/register')">
            立即注册
          </el-button>
        </div>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>系统特性</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="后端">FastAPI + SQLAlchemy 2.0 异步</el-descriptions-item>
            <el-descriptions-item label="前端">Vue 3 + Element Plus</el-descriptions-item>
            <el-descriptions-item label="AI 集成">FastAPI-MCP 双模发布</el-descriptions-item>
            <el-descriptions-item label="并发控制">悲观锁 + Hold-then-Confirm</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.home {
  max-width: 1100px;
  margin: 0 auto;
  padding: 48px 0;
}
h1 {
  font-size: 36px;
  margin-bottom: 16px;
}
.subtitle {
  font-size: 16px;
  color: var(--el-text-color-secondary);
  margin-bottom: 32px;
  line-height: 1.6;
}
.actions {
  display: flex;
  gap: 16px;
}
</style>
