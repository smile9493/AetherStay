<script setup lang="ts">
const techStack = [
  { label: '后端', value: 'FastAPI · SQLAlchemy 2.0（异步）· MySQL 8.0' },
  { label: '前端', value: 'Vue 3 · Element Plus · Vite · Pinia' },
  { label: '认证', value: 'JWT（HttpOnly Cookie）' },
  { label: 'AI 集成', value: 'FastAPI-MCP 双模发布' },
  { label: '部署', value: 'Docker Compose · Nginx' },
]

const highlights = [
  '前后端分离，RESTful API + 自动 Swagger 文档',
  'JWT HttpOnly Cookie 认证，降低 XSS 凭证窃取风险',
  '每日房态库存模型，支持任意日期段的精确搜索',
  'FastAPI-MCP 双模发布，AI Agent 可直接调用预订接口',
  'Docker Compose 一键部署',
]

const mechanisms = [
  {
    icon: 'Lock',
    title: '悲观锁防超卖',
    desc: '创建订单时对房态行执行 SELECT ... FOR UPDATE NOWAIT 锁定，并发场景下避免超卖。',
  },
  {
    icon: 'Timer',
    title: 'Hold-then-Confirm',
    desc: '订单先置为 held 并记录 held_until，超时未确认时由定时任务自动释放房态。',
  },
  {
    icon: 'DataLine',
    title: '每日房态库存',
    desc: '以 daily_room_inventories 按天建模房态，支撑任意日期段的可订查询。',
  },
  {
    icon: 'MagicStick',
    title: 'MCP 双模发布',
    desc: '通过 FastAPI-MCP 将 REST 接口暴露给 AI Agent，实现对话式预订。',
  },
]

const addresses = [
  { label: '前端', value: 'http://localhost' },
  { label: '后端 API', value: 'http://localhost:8000' },
  { label: 'API 文档', value: 'http://localhost:8000/docs' },
  { label: 'MCP 端点', value: 'http://localhost:8000/mcp' },
]

const roles = [
  {
    name: 'customer',
    title: '顾客',
    items: ['注册 / 登录', '搜索可用客房', '创建与取消订单', '查看我的订单'],
    api: '/api/v1/* 用户端点',
  },
  {
    name: 'admin',
    title: '管理员',
    items: ['顾客的全部能力', '全局订单管理（确认 / 入住 / 退房）', '客房与房型管理', '用户管理'],
    api: '/api/v1/admin/* 管理端点',
  },
]
</script>

<template>
  <div class="about-page">
    <header class="page-head">
      <h2>项目介绍</h2>
      <p class="page-head__sub">AetherStay 酒店客房预订管理系统</p>
    </header>

    <section class="card overview">
      <h3 class="card__title">关于 AetherStay</h3>
      <p class="overview__desc">
        基于 FastAPI + Vue 3 的酒店客房预订管理系统，支持 Web 端与 AI Agent（MCP）双模交互。
      </p>
      <ul class="overview__list">
        <li v-for="item in highlights" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section class="grid">
      <div class="card">
        <h3 class="card__title">技术栈</h3>
        <dl class="kv">
          <div v-for="tech in techStack" :key="tech.label" class="kv__row">
            <dt>{{ tech.label }}</dt>
            <dd>{{ tech.value }}</dd>
          </div>
        </dl>
      </div>

      <div class="card">
        <h3 class="card__title">服务地址</h3>
        <dl class="kv">
          <div v-for="addr in addresses" :key="addr.label" class="kv__row">
            <dt>{{ addr.label }}</dt>
            <dd>{{ addr.value }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <section class="section">
      <h3 class="section__title">核心机制</h3>
      <div class="mechanism-grid">
        <article v-for="item in mechanisms" :key="item.title" class="mechanism-card">
          <span class="mechanism-card__icon">
            <el-icon :size="20"><component :is="item.icon" /></el-icon>
          </span>
          <h4 class="mechanism-card__title">{{ item.title }}</h4>
          <p class="mechanism-card__desc">{{ item.desc }}</p>
        </article>
      </div>
    </section>

    <section class="section">
      <h3 class="section__title">角色与权限</h3>
      <div class="role-grid">
        <article v-for="role in roles" :key="role.name" class="role-card">
          <header class="role-card__head">
            <h4 class="role-card__title">{{ role.title }}</h4>
            <code class="role-card__code">{{ role.name }}</code>
          </header>
          <ul class="role-card__list">
            <li v-for="item in role.items" :key="item">{{ item }}</li>
          </ul>
          <p class="role-card__api">{{ role.api }}</p>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 24px;
}

.page-head h2 {
  font-size: 24px;
}

.page-head__sub {
  margin-top: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

.card {
  padding: 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.card__title {
  margin-bottom: 16px;
  font-size: 16px;
}

.overview {
  margin-bottom: 24px;
}

.overview__desc {
  font-size: 14px;
  color: var(--text-secondary);
}

.overview__list {
  display: grid;
  gap: 8px;
  margin: 16px 0 0;
  padding-left: 20px;
  font-size: 14px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.kv {
  display: grid;
  gap: 12px;
  margin: 0;
}

.kv__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
}

.kv__row dt {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--text-tertiary);
}

.kv__row dd {
  margin: 0;
  font-size: 14px;
  text-align: right;
}

.section {
  margin-bottom: 32px;
}

.section__title {
  margin-bottom: 16px;
  font-size: 20px;
}

.mechanism-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.mechanism-card {
  padding: 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.mechanism-card:hover {
  border-color: var(--brand-200);
  box-shadow: var(--shadow-sm);
}

.mechanism-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin-bottom: 16px;
  border-radius: var(--radius-sm);
  background: var(--brand-50);
  color: var(--brand-600);
}

.mechanism-card__title {
  margin-bottom: 8px;
  font-size: 16px;
}

.mechanism-card__desc {
  font-size: 14px;
  color: var(--text-secondary);
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.role-card {
  padding: 20px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.role-card__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.role-card__title {
  font-size: 16px;
}

.role-card__code {
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--brand-50);
  color: var(--brand-700);
  font-size: 12px;
}

.role-card__list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
  font-size: 14px;
  color: var(--text-secondary);
}

.role-card__api {
  margin-top: 16px;
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>