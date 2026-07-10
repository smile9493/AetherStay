# AetherStay

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=fff)](backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=fff)](backend/)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vue.js&logoColor=fff)](frontend/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=fff)](database/schema.sql)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff)](docker-compose.yml)
[![License](https://img.shields.io/badge/License-Private-red)](.)

基于 **FastAPI + Vue 3** 的智慧酒店客房预订管理系统，支持 Web 端与 AI Agent（MCP）双模交互。

采用 **Hold-then-Confirm** 两阶段预订模型 + **SELECT FOR UPDATE NOWAIT** 悲观锁，在高并发场景下实现防超卖库存一致性。

---

## 系统架构

```
客户端 ──→ Nginx ──→ FastAPI ──→ Services ──→ MySQL 8.0
  │                                            (InnoDB Row Lock)
  └──→ FastAPI-MCP ──→ AI Agent (Cursor / Claude)
```

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3, TypeScript, Element Plus, Pinia | SPA, 管理后台 |
| 网关 | Nginx | 反向代理, SPA 回退, SSE 长连接 |
| 后端 | FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2 | RESTful API + MCP |
| 数据库 | MySQL 8.0 (InnoDB) | 行级锁, `FOR UPDATE NOWAIT` |
| AI 集成 | FastAPI-MCP | 同一 API 自动暴露为 AI Agent 工具 |
| 部署 | Docker Compose | 三服务一键编排 |

---

## 特性

- **防超卖预订** — Hold-then-Confirm 两阶段模型 + 悲观锁（`SELECT FOR UPDATE NOWAIT`）
- **双模交互** — Web 端 + AI Agent（MCP 协议），同一套 API 两种入口
- **完整状态机** — `pending → confirmed → checked_in → checked_out / cancelled`
- **JWT HttpOnly Cookie 认证** — 防 XSS 凭证窃取，双 Token 自动刷新
- **管理员工作台** — Dashboard 统计、订单调度、客房/房型管理、房态日历、用户管理、系统设置
- **定时任务** — 过期 Hold 自动释放 + 按配置时间自动退房
- **并发压测验证** — Locust 测试 50 并发零超卖
- **CLI 脚手架** — 一键生成 model / schema / service / router / Vue 组件

---

## 项目结构

```
AetherStay/
├── agent.md                    # AI Agent 开发规范（编码约定、架构分层）
├── .env.example                # 环境变量模板
├── docker-compose.yml          # MySQL + 后端 + 前端 三服务编排
├── Dockerfile                  # 后端多阶段构建镜像
├── docker-entrypoint.sh        # 等待 MySQL 就绪
│
├── backend/                    # FastAPI 后端
│   ├── requirements.txt
│   ├── run.py                  # 开发启动入口（热重载）
│   └── app/
│       ├── main.py             # 应用工厂, CORS, MCP 挂载
│       ├── config.py           # pydantic-settings 配置
│       ├── database.py         # 异步引擎, AsyncSession, Base
│       ├── api/v1/             # REST API 路由
│       │   ├── auth.py         # 注册 / 登录 / 登出 / me
│       │   ├── rooms.py        # 客房列表 / 搜索
│       │   ├── bookings.py     # 预订 CRUD / 取消
│       │   ├── payments.py     # 模拟支付
│       │   └── admin/          # 管理员 API
│       │       ├── bookings.py, rooms.py, room_types.py
│       │       ├── users.py, stats.py, inventory.py
│       │       └── settings.py
│       ├── models/             # SQLAlchemy ORM
│       │   ├── user.py, room.py, inventory.py
│       │   ├── booking.py, system_setting.py
│       ├── schemas/            # Pydantic 请求/响应
│       ├── services/           # 业务逻辑层
│       │   ├── booking_service.py, inventory_service.py
│       │   ├── transaction.py, settings_service.py
│       ├── tasks/              # APScheduler 定时任务
│       │   ├── hold_release.py # 过期 Hold 释放
│       │   └── auto_checkout.py# 自动退房
│       └── utils/
│           └── auth.py         # JWT, Cookie, RoleChecker
│
├── frontend/                   # Vue 3 前端
│   ├── package.json
│   ├── Dockerfile              # 构建 + Nginx 运行时
│   ├── nginx.conf              # 反向代理配置（含 SSE 长连接优化）
│   ├── vite.config.ts          # 开发代理 /api → :8000
│   └── src/
│       ├── api/                # Axios 实例（withCredentials）
│       ├── stores/             # Pinia 全局状态
│       ├── router/             # Vue Router + 守卫（认证 / 管理员）
│       ├── layouts/            # MainLayout, AdminLayout
│       ├── views/              # 页面组件
│       │   └── admin/          # Dashboard, bookings, rooms, users...
│       ├── components/         # 可复用 UI 组件
│       ├── composables/        # 组合式函数
│       └── utils/              # 日期校验、错误处理
│
├── database/
│   ├── schema.sql              # DDL + 种子数据（7 间客房, 90 天房态）
│   └── migrations/             # 增量迁移脚本
│
├── docs/                       # 开发文档
│   ├── DEV.md                  # 本地开发指南 & 故障排查
│   ├── API.md                  # 完整 API 参考
│   ├── DEPLOY.md               # 生产部署指南
│   ├── MCP_GUIDE.md            # AI Agent MCP 配置与对话示例
│   └── PROJECT_NOTES.md        # 开发笔记（Bug / 难点 / 解决方案）
│
├── doc/                        # 系统设计 & 论文
│   ├── FastAPI 酒店系统设计.md  # 完整系统设计白皮书
│   ├── generate_draft.py       # 论文初稿生成脚本
│   ├── generate_proposal.py    # 开题报告生成脚本
│   └── docx_fonts.py           # DOCX 中文字体处理
│
├── scaffold/                   # CLI 脚手架（代码生成）
│   ├── scaffold.py
│   └── templates/              # Jinja2 模板
│
└── tests/                      # 测试
    ├── conftest.py             # pytest fixtures（SQLite 内存库）
    ├── test_booking_service.py # Hold-then-Confirm 状态机测试
    ├── test_auth_utils.py
    ├── test_user_bookings.py   # 用户端订单 CRUD
    ├── test_admin_*.py         # 管理员 API 测试
    ├── test_auto_checkout.py   # 自动退房测试
    └── load/                   # Locust 并发压测
        ├── locustfile.py       # 防超卖 + 混合搜索场景
        └── verify_no_oversell.sql
```

---

## 快速开始

### Docker Compose（推荐）

```bash
docker compose up -d
```

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost |
| 后端 API | http://localhost:8000 |
| Swagger 文档 | http://localhost:8000/docs |
| MCP 端点 | http://localhost:8000/mcp |

### 本地开发

```bash
# 环境变量
cp .env.example .env

# 启动 MySQL
docker compose up -d mysql

# 后端
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python run.py

# 前端
cd frontend && npm install && npm run dev
```

- 前端开发服务器：http://localhost:5173
- 详细步骤见 [docs/DEV.md](docs/DEV.md)

---

## 运行测试

```bash
# 安装测试依赖
pip install -r tests/requirements-dev.txt

# 执行单元/集成测试（默认 SQLite 内存库，无需 MySQL）
pytest tests/ -v

# Locust 并发压测（需后端运行）
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## 环境变量

```bash
cp .env.example .env
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | MySQL 异步连接串 | `mysql+aiomysql://...@localhost:3307/aetherstay` |
| `SECRET_KEY` | JWT 签名密钥 | 🚨 **生产环境必须替换** |
| `CORS_ORIGINS` | 允许的前端源（JSON 数组） | `["http://localhost:5173"]` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 有效期 | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 有效期 | `7` |
| `HOLD_TTL_MINUTES` | 预订 Hold 超时（分钟） | `15` |
| `HOLD_RELEASE_INTERVAL_MINUTES` | 过期 Hold 扫描间隔（分钟） | `1` |
| `DEBUG` | 调试模式 | `true` |
| `COOKIE_SECURE` | Cookie Secure 标志（生产应设为 `true`） | `false` |

---

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| GET | `/api/v1/auth/me` | 当前用户 |
| GET | `/api/v1/rooms/search` | 搜索可用客房 |
| POST | `/api/v1/bookings` | 创建预订（Hold 锁房） |
| POST | `/api/v1/bookings/{id}/pay` | 模拟支付确认 |
| POST | `/api/v1/bookings/{id}/cancel` | 取消订单 |
| GET | `/api/v1/admin/bookings` | 管理员：全局订单 |
| POST | `/api/v1/admin/bookings/{id}/confirm` | 管理员：确认付款 |
| POST | `/api/v1/admin/bookings/{id}/check-in` | 管理员：入住 |
| POST | `/api/v1/admin/bookings/{id}/check-out` | 管理员：退房 |

> **MCP 工具：** `login`, `get_available_rooms`, `create_booking`, `get_booking`, `cancel_booking`, `confirm_booking_payment`

完整 API 文档见 [docs/API.md](docs/API.md) 或运行后访问 `http://localhost:8000/docs`。

---

## MCP 配置

在 Cursor 或 Claude Desktop 中添加：

```json
{
  "mcpServers": {
    "aetherstay": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

AI Agent 可通过自然语言完成搜索 → 预订 → 支付全流程，详见 [docs/MCP_GUIDE.md](docs/MCP_GUIDE.md)。

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [agent.md](agent.md) | AI Agent 开发规范、编码约定、架构分层 |
| [docs/DEV.md](docs/DEV.md) | 本地开发流程、故障排查 |
| [docs/DEPLOY.md](docs/DEPLOY.md) | 生产环境部署与安全指南 |
| [docs/API.md](docs/API.md) | 完整 API 参考 |
| [docs/MCP_GUIDE.md](docs/MCP_GUIDE.md) | MCP 配置与 AI 对话示例 |
| [docs/PROJECT_NOTES.md](docs/PROJECT_NOTES.md) | 开发笔记：Bug、难点与解决方案（论文素材） |
| [scaffold/README.md](scaffold/README.md) | CLI 脚手架使用说明 |
| [tests/load/README.md](tests/load/README.md) | Locust 并发压测说明 |
| [doc/FastAPI 酒店系统设计.md](doc/FastAPI%20酒店系统设计.md) | 系统设计白皮书 |

---

## 开发路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| 第 1 周 | 项目脚手架、数据库设计、基础 API | ✅ |
| 第 2-3 周 | 悲观锁、Hold 状态机、MCP 完善 | ✅ |
| 第 4-5 周 | 管理员后台、定时释放/退房任务 | ✅ |
| 第 6 周 | 并发压测、索引优化、单元测试 | ✅ |
| 第 7 周 | 生产部署、文档完善 | ✅ |

---

## License

Private - 西南大学高等学历继续教育毕业论文项目
