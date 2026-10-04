# 本地开发指南

## 前置条件

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- Git

## 首次搭建

```bash
# 1. 克隆仓库
git clone https://github.com/smile9493/AetherStay.git
cd AetherStay

# 2. 环境变量
cp .env.example .env

# 3. 启动 MySQL（自动执行 database/schema.sql 初始化）
docker compose up -d mysql

# 4. 后端
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py

# 5. 前端（新终端）
cd frontend
npm install
npm run dev
```

## 访问地址

| 服务 | URL |
|------|-----|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| Swagger 文档 | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| MCP 端点 | http://localhost:8000/mcp |
| MySQL | `localhost:3307`（用户 `aetherstay` / 密码 `aetherstay`） |

## 验证安装

```bash
# 健康检查
curl http://localhost:8000/health

# 客房列表（应有 7 间）
curl http://localhost:8000/api/v1/rooms | python3 -m json.tool

# 注册用户
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo1234"}'

# 登录
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo1234"}'

# 搜索可用客房
curl "http://localhost:8000/api/v1/rooms/search?check_in=2026-07-17&check_out=2026-07-19"
```

## 数据库

### 连接信息

```
Host:     localhost
Port:     3307
Database: aetherstay
User:     aetherstay
Password: aetherstay
```

### 重置数据库

```bash
docker compose down -v          # 删除数据卷
docker compose up -d mysql      # 重新初始化
```

### 种子数据

`schema.sql` 自动创建：

- 3 种房型（标准双床房 ¥299、豪华大床房 ¥499、行政套房 ¥899）
- 7 间客房（101-103、201-202、301-302）
- 90 天房态记录（每间客房）

默认管理员：`admin` / `admin1234`

## 自动化测试与压测

### 前置

- 已启动 MySQL（`docker compose up -d mysql`，端口 3307）
- 后端已在虚拟环境中安装运行依赖（`pip install -r requirements.txt`）

### 安装测试依赖

```bash
cd backend
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 运行接口测试

```bash
cd backend
pytest -q
```

说明：

- 测试使用 **独立数据库 `aetherstay_test`**（由 `tests/conftest.py` 自动创建/销毁），
  不会污染开发库 `aetherstay`；需要 MySQL 的 `root/root` 账号来建库。
- 测试通过 `httpx.ASGITransport` 在进程内调用 ASGI 应用，但底层是真实 MySQL，
  因此悲观锁（`SELECT ... FOR UPDATE NOWAIT`）行为可被真实覆盖。
- 用例覆盖：注册/登录/鉴权、客房搜索、预订 Hold–支付–取消、以及
  「多并发争抢同一房间只允许 1 单」的防超卖断言。

### 运行压测（Locust）

```bash
cd backend
locust -f locustfile.py --host http://localhost:8000 --headless -u 50 -r 10 -t 30s
```

- `-u` 并发用户数、`-r` 每秒孵化数、`-t` 持续时间
- 脚本复用预置管理员账号登录，任务权重：搜索 3 / 创建预订 1

## 故障排查

### 后端启动失败：`CORS_ORIGINS` 解析错误

**原因**：使用 `export $(grep .env)` 会破坏 JSON 数组格式。

**解决**：直接启动，config.py 会自动读取项目根目录 `.env`：

```bash
cd backend && source venv/bin/activate && python run.py
```

### 后端连接数据库失败

1. 确认 MySQL 容器运行：`docker ps | grep aetherstay-mysql`
2. 确认端口为 `3307`（`.env` 中 `DATABASE_URL`）
3. 等待健康检查通过：`docker exec aetherstay-mysql mysqladmin ping -u root -proot`

### 前端 API 请求 404

确认 Vite 代理配置（`frontend/vite.config.ts`）：

```ts
proxy: {
  '/api': { target: 'http://localhost:8000', changeOrigin: true },
}
```

### Cookie 登录不生效

- 后端 `set_cookie` 需设置 `samesite="lax"`
- 前端 Axios 需 `withCredentials: true`
- 开发环境 `secure=False`（生产环境改为 `True`）

## Docker 全栈部署

```bash
docker compose up -d --build
```

| 服务 | 端口 |
|------|------|
| 前端 (Nginx) | http://localhost |
| 后端 | http://localhost:8000 |
| MySQL | localhost:3307 |

## MCP 本地调试

在 Cursor 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "aetherstay": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

可用 Tools：`get_available_rooms`、`create_booking`、`get_booking`、`cancel_booking`。
