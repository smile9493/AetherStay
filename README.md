# AetherStay

基于 **FastAPI + Vue 3** 的酒店客房预订管理系统，支持 Web 端与 AI Agent（MCP）双模交互。

## 特性

- 前后端分离，RESTful API + 自动 Swagger 文档
- JWT 双 Token（Access 15min + Refresh 7d）HttpOnly Cookie 认证，支持令牌轮换与失效
- Hold-then-Confirm 两阶段预订，MySQL `FOR UPDATE NOWAIT` 悲观锁 + 指数退避重试 + 幂等键防超卖
- 每日房态库存模型（「房×日」复合主键），支持精确日期搜索
- FastAPI-MCP 双模发布，同一套 API 同时服务 Web 用户与 AI Agent
- 内置 LLM 订房助手（DeepSeek + Function Calling + SSE 流式），17 个业务工具（用户端 5 + 管理端 12）
- 会员等级与积分字段、后台管理 REST API、自动退房与过期 Hold 释放调度
- 24 项自动化测试（pytest）+ Locust 并发压测 + 并发控制/索引对照实验脚本
- Docker Compose 一键部署

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI, SQLAlchemy 2.0 (异步), MySQL 8.0, APScheduler |
| 前端 | Vue 3, TypeScript, Element Plus, Vite, Pinia |
| 认证 | JWT 双 Token (HttpOnly Cookie) + Argon2 密码哈希 |
| AI 集成 | FastAPI-MCP（双模）+ 内置 LLM Agent（DeepSeek） |
| 测试 | pytest + httpx、Locust、并发/索引对照实验脚本 |
| 部署 | Docker Compose + Nginx |

## 项目结构

```
AetherStay/
├── agent.md              # AI Agent 开发规范（编码约定、架构分层）
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/       # REST API 路由（含 admin 子路由）
│   │   ├── models/       # SQLAlchemy ORM 模型
│   │   ├── schemas/      # Pydantic 数据校验
│   │   ├── services/     # 业务逻辑层（预订锁、库存、事务）
│   │   ├── agent/        # 内置 LLM 对话 Agent（工具集 + 服务层）
│   │   ├── tasks/        # APScheduler 定时任务（过期释放 / 自动退房）
│   │   └── utils/        # 认证、角色权限、限流
│   ├── experiments/      # 并发控制基准 + 索引 EXPLAIN 对照实验
│   ├── tests/            # pytest 自动化测试（24 项）
│   ├── locustfile.py     # Locust 并发压测脚本
│   └── requirements*.txt
├── frontend/             # Vue 3 前端
├── database/             # schema.sql + migrations/ 迁移脚本
├── docs/                 # 开发文档（DEV.md / API.md / PROJECT_NOTES.md）
└── docker-compose.yml
```

## 快速开始

### Docker Compose（推荐）

```bash
docker compose up -d
```

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| MCP 端点 | http://localhost:8000/mcp |

### 本地开发

```bash
# 环境变量
cp .env.example .env

# MySQL
docker compose up -d mysql

# 后端
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python run.py

# 前端
cd frontend && npm install && npm run dev
```

前端开发服务器：http://localhost:5173

详细步骤见 [docs/DEV.md](docs/DEV.md)。

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| GET | `/api/v1/rooms/search` | 搜索可用客房 |
| POST | `/api/v1/bookings` | 创建预订（Hold 锁房） |
| POST | `/api/v1/bookings/{id}/pay` | 支付确认（模拟） |
| GET | `/api/v1/bookings/my` | 我的订单 |
| POST | `/api/v1/bookings/{id}/cancel` | 取消订单 |
| GET | `/api/v1/admin/stats` | Dashboard 统计 |
| GET/POST/PUT/DELETE | `/api/v1/admin/rooms` | 客房管理 |
| GET/POST/PUT/DELETE | `/api/v1/admin/room-types` | 房型管理 |
| GET/PUT | `/api/v1/admin/settings` | 系统设置 |
| POST | `/api/v1/agent/chat` | AI 对话（SSE 流式） |

完整 API 文档见 [docs/API.md](docs/API.md) 或 http://localhost:8000/docs。

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

## 环境变量

```bash
cp .env.example .env
```

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | MySQL 连接串（本地端口 3307） |
| `SECRET_KEY` | JWT 签名密钥 |
| `CORS_ORIGINS` | 允许的前端源（JSON 数组） |

## 文档索引

| 文档 | 内容 |
|------|------|
| [agent.md](agent.md) | AI Agent 开发规范、编码约定、架构分层 |
| [docs/DEV.md](docs/DEV.md) | 本地开发流程、故障排查 |
| [docs/API.md](docs/API.md) | API 参考 |
| [docs/PROJECT_NOTES.md](docs/PROJECT_NOTES.md) | 开发笔记：Bug、难点与解决方案（论文素材） |

## 开发计划

| 阶段 | 内容 | 状态 |
|------|------|------|
| 第 1 周 | 项目脚手架、数据库设计、基础 API | ✅ |
| 第 2-3 周 | 悲观锁、Hold 状态机、MCP 完善 | ✅ |
| 第 4-5 周 | 管理员后台 API、定时任务、LLM Agent | ✅ |
| 第 6 周 | 并发压测、索引优化、微基准实验 | ✅ |
| 第 7 周 | 生产部署、文档完善 | ✅ |

## License

Private
