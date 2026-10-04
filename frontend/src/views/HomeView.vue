<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="home">
    <section class="hero">
      <p class="hero__eyebrow">酒店客房预订管理系统</p>
      <h1 class="hero__title">欢迎来到 AetherStay</h1>
      <p class="hero__subtitle">智能酒店客房预订管理系统 — 支持 Web 端与 AI Agent 双模交互</p>
      <div class="hero__actions">
        <el-button size="large" class="hero-cta hero-cta--solid" @click="router.push('/rooms')">
          浏览客房
        </el-button>
        <el-button size="large" class="hero-cta hero-cta--ghost" @click="router.push('/register')">
          立即注册
        </el-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero {
  position: relative;
  overflow: hidden;
  padding: 64px 48px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--brand-700) 0%, var(--brand-900) 100%);
  color: #ffffff;
}

.hero::after {
  content: '';
  position: absolute;
  top: -40%;
  right: -8%;
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.16) 0%, rgba(255, 255, 255, 0) 70%);
  pointer-events: none;
}

.hero__eyebrow {
  display: inline-block;
  margin-bottom: 16px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.14);
  color: var(--brand-100);
  font-size: 12px;
  letter-spacing: 0.4px;
}

.hero__title {
  font-size: 40px;
  color: #ffffff;
}

.hero__subtitle {
  max-width: 560px;
  margin-top: 16px;
  font-size: 16px;
  line-height: 1.6;
  color: var(--brand-100);
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 32px;
}

/* 深色 Hero 上的按钮：通过 Element Plus 变量做反色，避免与主色撞色 */
.hero-cta--solid {
  --el-button-bg-color: #ffffff;
  --el-button-border-color: #ffffff;
  --el-button-text-color: var(--brand-700);
  --el-button-hover-bg-color: var(--brand-50);
  --el-button-hover-border-color: var(--brand-50);
  --el-button-hover-text-color: var(--brand-800);
  --el-button-active-bg-color: var(--brand-100);
  --el-button-active-border-color: var(--brand-100);
}

.hero-cta--ghost {
  --el-button-bg-color: transparent;
  --el-button-border-color: rgba(255, 255, 255, 0.6);
  --el-button-text-color: #ffffff;
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.12);
  --el-button-hover-border-color: #ffffff;
  --el-button-hover-text-color: #ffffff;
  --el-button-active-bg-color: rgba(255, 255, 255, 0.2);
  --el-button-active-border-color: #ffffff;
}

@media (max-width: 768px) {
  .hero {
    padding: 40px 24px;
  }

  .hero__title {
    font-size: 32px;
  }
}
</style>