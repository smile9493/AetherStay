# AetherStay

基于 **FastAPI + Vue 3** 的酒店客房预订管理系统，支持 Web 端与 AI Agent（MCP）双模交互。

## 特性

- 前后端分离，RESTful API + 自动 Swagger 文档
- JWT HttpOnly Cookie 认证，防 XSS 凭证窃取
- 每日房态库存模型，支持精确日期搜索
- FastAPI-MCP 双模发布，AI Agent 可直接调用预订接口
- Docker Compose 一键部署

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI, SQLAlchemy 2.0 (异步), MySQL 8.0 |
| 前端 | Vue 3, Element Plus, Vite, Pinia |
| 认证 | JWT (HttpOnly Cookie) |
| AI 集成 | FastAPI-MCP |
| 部署 | Docker, Nginx |

## 项目结构

```
AetherStay/
├── agent.md              # AI Agent 开发规范（编码约定、架构分层）
├── backend/              # FastAPI 后端
│   └── app/
│       ├── api/v1/       # REST API 路由
│       ├── models/       # SQLAlchemy ORM 模型
│       ├── schemas/      # Pydantic 数据校验
│       ├── services/     # 业务逻辑层
│       └── utils/        # 认证、工具函数
├── frontend/             # Vue 3 前端
├── database/             # MySQL DDL 脚本
├── docs/                 # 开发文档
│   ├── DEV.md            # 本地开发指南
│   └── API.md            # API 参考
├── doc/                  # 系统设计白皮书
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
| GET | `/api/v1/rooms/search` | 搜索可用客房 |
| POST | `/api/v1/bookings` | 创建预订 |
| GET | `/api/v1/bookings/my` | 我的订单 |
| POST | `/api/v1/bookings/{id}/cancel` | 取消订单 |

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
| [docs/PROJECT_NOTES.md](docs/PROJECT_NOTES.md) | 开发笔记：Bug、难点与解决方案（论文素材） |
| [doc/FastAPI 酒店系统设计.md](doc/FastAPI%20酒店系统设计.md) | 完整系统设计白皮书 |

## 开发计划

| 阶段 | 内容 | 状态 |
|------|------|------|
| 第 1 周 | 项目脚手架、数据库设计、基础 API | ✅ |
| 第 2-3 周 | 悲观锁、Hold 状态机、MCP 完善 | 🔲 |
| 第 4-5 周 | 管理员后台、定时释放任务 | 🔲 |
| 第 6 周 | 并发压测、索引优化 | 🔲 |
| 第 7 周 | 生产部署、文档完善 | 🔲 |

## License

Private
