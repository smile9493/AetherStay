# AetherStay AI Agent 开发指南

> 本文件面向 AI Agent（Cursor、Claude 等）及开发者，定义项目规范、架构约定与编码标准。  
> 系统设计详见 `doc/FastAPI 酒店系统设计.md`。

## 项目概述

AetherStay 是一个酒店客房预订管理系统（PMS），采用前后端分离架构，支持：

- **人类用户**：Vue 3 Web 界面
- **AI Agent**：通过 FastAPI-MCP 双模发布，同一套 API 同时暴露为 REST 与 MCP Tools

## 技术栈速览

| 层 | 技术 | 说明 |
|----|------|------|
| 后端框架 | FastAPI (ASGI 异步) | Python 3.12+ |
| ORM | SQLAlchemy 2.0 (AsyncSession) | 弃用旧 Query API，统一 2.0 风格 |
| 数据库 | MySQL 8.0 (InnoDB) | 行级锁、NOWAIT 悲观锁 |
| 前端框架 | Vue 3 (Composition API) | `<script setup>` + TypeScript |
| UI 组件库 | Element Plus | 中后台业务组件 |
| 状态管理 | Pinia | 认证状态等全局状态 |
| 路由 | Vue Router 5 | History 模式 |
| HTTP 客户端 | Axios | `withCredentials: true` 透传 Cookie |
| 构建工具 | Vite 8 | 开发代理 `/api` → 后端 |
| 认证 | JWT + HttpOnly Cookie | 禁止 LocalStorage 存 Token |
| AI 集成 | FastAPI-MCP | 自动将路由转为 MCP Tools |
| 部署 | Docker Compose + Nginx | 三服务编排 |

## 项目结构

```
AetherStay/
├── agent.md                      # 本文件 — AI Agent 开发规范
├── README.md                     # 项目说明与快速开始
├── .env.example                  # 环境变量模板（复制为 .env）
├── docker-compose.yml            # MySQL + 后端 + 前端
├── Dockerfile                    # 后端镜像
├── docker-entrypoint.sh          # 等待 MySQL 就绪
│
├── backend/                      # FastAPI 后端
│   ├── requirements.txt
│   ├── run.py                    # 开发启动入口
│   └── app/
│       ├── main.py               # 应用工厂、CORS、MCP 挂载
│       ├── config.py             # pydantic-settings 配置
│       ├── database.py           # 异步引擎、AsyncSession、Base
│       ├── api/v1/
│       │   ├── router.py         # 路由聚合
│       │   ├── auth.py           # 注册 / 登录 / 登出 / me
│       │   ├── rooms.py          # 客房列表 / 搜索
│       │   └── bookings.py       # 预订 CRUD / 取消
│       ├── models/               # SQLAlchemy ORM（禁止放业务逻辑）
│       │   ├── user.py
│       │   ├── room.py           # RoomType + Room
│       │   ├── inventory.py      # DailyRoomInventory
│       │   └── booking.py
│       ├── schemas/              # Pydantic 请求/响应模型
│       │   ├── auth.py
│       │   └── room.py
│       ├── services/             # 业务逻辑层（待扩展）
│       └── utils/
│           └── auth.py           # JWT、Cookie、RoleChecker
│
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── api/index.ts          # Axios 实例（withCredentials）
│   │   ├── stores/auth.ts        # Pinia 认证 Store
│   │   ├── router/index.ts       # 路由 + 守卫
│   │   ├── layouts/MainLayout.vue
│   │   └── views/                # 页面组件
│   ├── vite.config.ts            # 别名 @、API 代理
│   ├── Dockerfile                # 构建 + Nginx
│   └── nginx.conf
│
├── database/
│   └── schema.sql                # DDL + 种子数据
│
└── doc/
    └── FastAPI 酒店系统设计.md    # 完整系统设计白皮书
```

## 架构分层

```
客户端 (Vue / AI Agent)
        │
        ▼
  Nginx / Vite Proxy
        │
        ▼
  FastAPI Routers          ← api/v1/*.py
        │
        ▼
  Depends (Auth/RBAC)      ← utils/auth.py
        │
        ▼
  Services (业务逻辑)       ← services/（预订锁、状态机等）
        │
        ▼
  SQLAlchemy Async ORM     ← models/
        │
        ▼
  MySQL 8.0
```

**强制规则**：Router 层只做参数校验与响应封装；复杂业务逻辑必须放在 `services/`，不得直接堆在路由函数中。

## 开发约定

### 后端

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | snake_case | `booking_service.py` |
| 类名 | PascalCase | `BookingService` |
| 函数/变量 | snake_case | `get_current_user` |
| 路由前缀 | 复数名词 | `/rooms`, `/bookings` |
| operation_id | snake_case | `get_available_rooms`（MCP Tool 名） |

#### 模型与 Schema 分离

- `models/` — SQLAlchemy ORM，映射数据库表
- `schemas/` — Pydantic 模型，定义 API 入参/出参
- **禁止**在 ORM 模型中写 HTTP 相关逻辑

#### 路由注册

在 `backend/app/api/v1/router.py` 中通过 `api_router.include_router()` 注册新模块。

#### 认证与权限

```python
from typing import Annotated
from fastapi import Depends
from app.utils.auth import CurrentUser, RoleChecker, get_current_user
from app.models.user import UserRole

# 需要登录
async def endpoint(user: Annotated[CurrentUser, Depends(get_current_user)]):
    ...

# 需要管理员
async def admin_endpoint(user: Annotated[CurrentUser, Depends(RoleChecker([UserRole.ADMIN]))]):
    ...
```

- Token 通过 **HttpOnly Cookie**（`access_token`）传递，前端 JS 不可读
- 登录/注册接口通过 `Response.set_cookie()` 写入 Cookie
- 前端 Axios 必须设置 `withCredentials: true`

#### 数据库会话

```python
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.database import get_db

async def endpoint(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Room))
    ...
    await db.commit()
```

- 使用 `await db.execute()` + `select()`，**禁止**旧式 `db.query()`
- 关系加载用 `selectinload()` 避免 N+1

#### 新增 API 模块步骤

1. `models/` 定义 ORM 模型（若涉及新表）
2. `schemas/` 定义 Pydantic Schema
3. `api/v1/` 创建路由文件
4. `api/v1/router.py` 注册路由
5. 需要 MCP 暴露的路由，添加 `operation_id` 参数
6. 更新 `database/schema.sql`（若有表结构变更）
7. 前端 `api/`、`views/`、`router/` 同步更新

#### MCP 双模发布

- 带 `operation_id` 的路由会自动被 FastAPI-MCP 转为 Tool
- Tool 名称 = `operation_id`，描述 = 函数 docstring
- 当前已暴露：`get_available_rooms`、`create_booking`、`get_booking`、`cancel_booking`

### 前端

#### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件文件 | PascalCase | `RoomsView.vue` |
| 组合式函数 | camelCase | `useAuthStore` |
| 路由 name | camelCase | `rooms`, `bookings` |
| API 路径 | 与后端一致 | `/rooms/search` |

#### 目录职责

| 目录 | 职责 |
|------|------|
| `api/` | Axios 封装，按业务域拆分（待扩展） |
| `stores/` | Pinia 全局状态 |
| `views/` | 页面级组件 |
| `layouts/` | 布局骨架 |
| `components/` | 可复用 UI 组件 |
| `types/` | TypeScript 类型（待扩展，与后端 Schema 对齐） |

#### 新增页面步骤

1. `views/` 创建页面组件
2. `router/index.ts` 添加路由（需登录则设 `meta: { requiresAuth: true }`）
3. `layouts/MainLayout.vue` 导航菜单添加链接
4. 如需新 API，在 `api/` 中封装

#### UI 规范

- 统一使用 Element Plus 组件，不引入其他 UI 库
- 中文界面文案
- 表单提交用 `@submit.prevent`，按钮 loading 状态绑定 Store

### 通用

| 约定 | 值 |
|------|-----|
| API 前缀 | `/api/v1/` |
| 后端地址 | `http://0.0.0.0:8000` |
| 前端开发地址 | `http://localhost:5173` |
| MySQL 端口（Docker） | `3307`（映射容器 3306） |
| 日期区间 | 前闭后开 `[check_in, check_out)` |

## 数据模型关系

```
User 1──N Booking
RoomType 1──N Room
Room 1──N DailyRoomInventory
Room 1──N Booking
Booking 1──N DailyRoomInventory (via booking_id)
```

### 核心表

| 表 | 用途 |
|----|------|
| `users` | 用户凭证与角色（customer / admin） |
| `room_types` | 房型静态属性（名称、基准价、容量） |
| `rooms` | 物理客房（门牌号、上下架状态） |
| `daily_room_inventories` | 每日房态（available / held / booked / maintenance） |
| `bookings` | 订单（日期、价格、状态机） |

### 预订状态机（目标设计）

```
pending → confirmed → checked_in → checked_out
   │          │
   └→ cancelled ←┘
```

### 房态 Hold-then-Confirm（第 2-3 周实现）

```
available → held (15min TTL) → booked
                └→ available (超时释放)
```

实现时使用 `SELECT ... FOR UPDATE NOWAIT` 非阻塞悲观锁，详见设计文档第五章。

## 角色权限

| 角色 | 权限 |
|------|------|
| `customer` | 浏览客房、搜索、预订、查看/取消自己的订单 |
| `admin` | 全部 customer 权限 + 房型管理、全局订单、用户管理（待实现） |

## API 端点一览

### 认证 `/api/v1/auth`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/register` | 否 | 用户注册 |
| POST | `/login` | 否 | 登录，写入 Cookie |
| POST | `/logout` | 否 | 清除 Cookie |
| GET | `/me` | 是 | 当前用户信息 |

### 客房 `/api/v1/rooms`

| 方法 | 路径 | 认证 | MCP | 说明 |
|------|------|------|-----|------|
| GET | `/` | 否 | — | 全部客房列表 |
| GET | `/search` | 否 | `get_available_rooms` | 按日期搜索可用客房 |

### 预订 `/api/v1/bookings`

| 方法 | 路径 | 认证 | MCP | 说明 |
|------|------|------|-----|------|
| POST | `/` | 是 | `create_booking` | 创建预订 |
| GET | `/my` | 是 | — | 我的订单列表 |
| GET | `/{id}` | 是 | `get_booking` | 订单详情 |
| POST | `/{id}/cancel` | 是 | `cancel_booking` | 取消订单 |

## 编码原则

AI Agent 及开发者在修改代码时必须遵守：

1. **最小改动** — 只改与任务相关的文件，不重构无关代码
2. **复用现有抽象** — 扩展 `RoleChecker`、`get_db` 等，不重复造轮子
3. **匹配项目风格** — 命名、分层、import 顺序与现有代码一致
4. **不写废话注释** — 仅注释非显而易见的业务逻辑
5. **不提交密钥** — `.env` 不入库，生产 `SECRET_KEY` 必须替换
6. **不跳过测试** — 改动 API 后用 curl 或 Swagger 验证
7. **Schema 同步** — 后端 Schema 变更时同步前端类型

## 常用命令

```bash
# ── 基础设施 ──
docker compose up -d mysql          # 仅启动 MySQL
docker compose up -d                # 全栈启动

# ── 后端 ──
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run.py                       # 开发热重载 → :8000

# ── 前端 ──
cd frontend
npm install
npm run dev                         # 开发 → :5173
npm run build                       # 生产构建

# ── 验证 ──
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/rooms
curl http://localhost:8000/docs     # Swagger UI
```

## 环境变量

复制 `.env.example` 为 `.env`，**不要用 shell export 导入**（会破坏 JSON 数组）：

```bash
cp .env.example .env
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | MySQL 异步连接串 | `mysql+aiomysql://...@localhost:3307/aetherstay` |
| `SECRET_KEY` | JWT 签名密钥 | 必须替换 |
| `CORS_ORIGINS` | 允许的前端源（JSON 数组） | `["http://localhost:5173"]` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 有效期 | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 有效期 | `7` |
| `HOLD_TTL_MINUTES` | 预订 Hold 超时（分钟） | `15` |

配置加载：`backend/app/config.py` 自动读取项目根目录 `.env`。

## 开发路线图

| 阶段 | 周期 | 后端 | 前端 | 状态 |
|------|------|------|------|------|
| 脚手架 | 第 1 周 | 项目基线、ORM、基础 API | Vue 基线、登录/预订页面 | ✅ 完成 |
| 核心逻辑 | 第 2-3 周 | 悲观锁、Hold 状态机、MCP 完善 | 预订链路联调 | 🔲 待开发 |
| 管理后台 | 第 4-5 周 | 管理员 API、定时释放任务 | 管理工作台 | 🔲 待开发 |
| 压测优化 | 第 6 周 | Locust 压测、索引调优 | E2E 测试 | 🔲 待开发 |
| 部署交付 | 第 7 周 | Docker 生产镜像、Nginx 调优 | 部署文档 | 🔲 待开发 |

## 参考文档

| 文件 | 内容 |
|------|------|
| `doc/FastAPI 酒店系统设计.md` | 完整架构设计、并发控制、索引优化、Nginx 配置 |
| `docs/DEV.md` | 本地开发流程与故障排查 |
| `docs/API.md` | API 请求/响应示例 |
| `README.md` | 项目概览与快速开始 |
