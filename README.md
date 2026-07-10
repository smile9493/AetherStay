# AetherStay

基于 **FastAPI + Vue 3** 的酒店客房预订管理系统，支持 Web 端与 AI Agent（MCP）双模交互。

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
├── backend/          # FastAPI 后端
│   └── app/
│       ├── api/v1/   # REST API 路由
│       ├── models/   # SQLAlchemy ORM 模型
│       ├── schemas/  # Pydantic 数据校验
│       └── utils/    # 认证、工具函数
├── frontend/         # Vue 3 前端
├── database/         # MySQL DDL 脚本
├── doc/              # 系统设计文档
├── docker-compose.yml
└── Dockerfile
```

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
docker compose up -d
```

- 前端：http://localhost
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
- MCP 端点：http://localhost:8000/mcp

### 方式二：本地开发

**1. 启动 MySQL**

```bash
docker compose up -d mysql
```

**2. 启动后端**

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
python run.py
```

**3. 启动前端**

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器：http://localhost:5173

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| GET | `/api/v1/rooms/search` | 搜索可用客房 |
| POST | `/api/v1/bookings` | 创建预订 |
| GET | `/api/v1/bookings/my` | 我的订单 |
| POST | `/api/v1/bookings/{id}/cancel` | 取消订单 |

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

参考 `.env.example` 配置：

```bash
cp .env.example .env
```

## 开发计划

详见 `doc/FastAPI 酒店系统设计.md`，项目按 7 周敏捷迭代推进：

- **第 1 周**：项目脚手架、数据库设计、API 规划（当前阶段）
- **第 2-3 周**：认证、预订核心逻辑、悲观锁、MCP 集成
- **第 4-5 周**：管理员后台、Hold-then-Confirm 状态机
- **第 6 周**：并发压测、索引优化
- **第 7 周**：生产部署、文档完善

## License

Private
