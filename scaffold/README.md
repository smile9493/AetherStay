# AetherStay 脚手架工具

加速 AetherStay 项目开发的自动化代码生成工具。遵循 DRY 原则，确保生成的代码与项目现有架构风格完全一致。

## 安装

```bash
pip install -r scaffold/requirements.txt
```

## 快速开始

```bash
# 查看帮助
python scaffold/scaffold.py --help

# 初始化开发环境
python scaffold/scaffold.py init

# 检查项目健康状态
python scaffold/scaffold.py check

# 列出所有已注册模块
python scaffold/scaffold.py list
```

## 命令概览

| 命令 | 说明 |
|------|------|
| `init` | 初始化开发环境（.env、虚拟环境、依赖安装） |
| `check` | 检查项目结构完整性和健康状态 |
| `list` | 列出项目中所有已注册的模块 |
| `gen api <name>` | 生成完整 API 模块（model + schema + service + router） |
| `gen model <name>` | 生成 SQLAlchemy 数据模型 |
| `gen schema <name>` | 生成 Pydantic 数据校验 Schema |
| `gen service <name>` | 生成业务逻辑 Service |
| `gen router <name>` | 生成 API Router |
| `gen admin <name>` | 生成管理员 CRUD 模块 |
| `gen task <name>` | 生成定时任务 |
| `gen view <name>` | 生成 Vue 视图页面 |
| `gen store <name>` | 生成 Pinia 状态管理 Store |
| `gen component <name>` | 生成 Vue 组件 |

---

## 详细用法

### 开发环境初始化

```bash
python scaffold/scaffold.py init
```

一键完成：
1. 从 `.env.example` 复制生成 `.env` 配置文件
2. 创建 Python 虚拟环境并安装后端依赖
3. 安装前端 npm 依赖
4. 提示下一步操作（启动数据库、运行服务）

### 项目健康检查

```bash
python scaffold/scaffold.py check
```

检查内容包括：
- 核心配置文件是否存在（`.env`, `requirements.txt`, `package.json` 等）
- 后端模块目录完整性（`api/v1/`, `models/`, `schemas/`, `services/` 等）
- 前端模块目录完整性（`views/`, `stores/`, `api/`, `router/` 等）

### 模块列表

```bash
python scaffold/scaffold.py list
```

展示项目中已注册的：
- 数据模型（Models）
- API 路由（Routers）
- 管理员路由（Admin）
- 定时任务（Tasks）
- Vue 视图（Views）
- Pinia Stores
- Vue 路由

---

## 代码生成

### 生成完整 API 模块

```bash
python scaffold/scaffold.py gen api amenity
```

这将自动生成 4 个文件：

| # | 文件 | 路径 |
|---|------|------|
| 1 | Model | `backend/app/models/amenity.py` |
| 2 | Schema | `backend/app/schemas/amenity.py` |
| 3 | Service | `backend/app/services/amenity_service.py` |
| 4 | Router | `backend/app/api/v1/amenity.py` |

生成后会提示需要手动注册：
- 将 `Amenity` 添加到 `backend/app/models/__init__.py`
- 将 `amenity.router` 注册到 `backend/app/api/v1/router.py`
- 在 `database/schema.sql` 中添加 DDL 建表语句

### 生成单个模块

```bash
# 只生成 Model
python scaffold/scaffold.py gen model coupon

# 只生成 Schema
python scaffold/scaffold.py gen schema coupon

# 只生成 Service
python scaffold/scaffold.py gen service coupon

# 只生成 Router
python scaffold/scaffold.py gen router coupon
```

### 生成管理员 CRUD 模块

```bash
python scaffold/scaffold.py gen admin coupon
```

生成管理员专属 CRUD 路由（带 `RoleChecker([UserRole.ADMIN])` 权限控制），包含完整的增删改查接口。

### 生成定时任务

```bash
python scaffold/scaffold.py gen task release_expired_coupons --desc "Release expired coupons"
```

生成后台定时任务模板，需要在 `backend/app/main.py` 的 `lifespan` 中注册调度。

### 生成 Vue 视图

```bash
python scaffold/scaffold.py gen view Payment
```

生成带列表展示的 Vue 3 视图页面（Composition API + Element Plus）。

### 生成 Pinia Store

```bash
python scaffold/scaffold.py gen store payment
```

生成 Pinia 状态管理 Store，包含 `fetchItems` 方法。

### 生成 Vue 组件

```bash
python scaffold/scaffold.py gen component PriceCard
```

生成可复用的 Vue 3 组件（Props + Emits + 基础交互）。

---

## 模板目录结构

```
scaffold/
├── scaffold.py              # CLI 入口
├── requirements.txt         # 依赖（Jinja2）
├── templates/               # Jinja2 模板
│   ├── backend/
│   │   ├── model.py.j2      # SQLAlchemy 模型模板
│   │   ├── schema.py.j2     # Pydantic Schema 模板
│   │   ├── api_router.py.j2 # API Router 模板
│   │   ├── api_service.py.j2# Service 模板
│   │   ├── admin_module.py.j2# 管理员 CRUD 模板
│   │   └── task.py.j2       # 定时任务模板
│   └── frontend/
│       ├── View.vue.j2      # Vue 视图模板
│       ├── Store.ts.j2      # Pinia Store 模板
│       └── Component.vue.j2 # Vue 组件模板
└── README.md
```

## 架构规范

生成的代码严格遵循 AetherStay 现有架构规范：

### 后端分层

```
backend/app/
├── api/v1/          # 路由层 — HTTP 请求处理（依赖注入、输入校验、返回响应）
├── models/          # 持久层 — SQLAlchemy ORM 数据模型
├── schemas/         # 校验层 — Pydantic 请求/响应 Schema
├── services/        # 业务层 — 核心业务逻辑、事务管理
├── tasks/           # 定时层 — APScheduler 定时任务
└── utils/           # 工具层 — 认证、通用工具函数
```

### 前端架构

```
frontend/src/
├── views/           # 页面级组件
├── components/      # 可复用组件
├── stores/          # Pinia 状态管理
├── api/             # Axios API 客户端
└── router/          # Vue Router 路由配置
```
