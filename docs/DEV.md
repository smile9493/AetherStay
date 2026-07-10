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

- 3 种房型（Standard Twin ¥299、Deluxe King ¥499、Executive Suite ¥899）
- 7 间客房（101-103、201-202、301-302）
- 90 天房态记录（每间客房）

默认管理员：`admin` / `admin1234`

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

可用 Tools：`login`、`get_available_rooms`、`create_booking`、`get_booking`、`cancel_booking`、`confirm_booking_payment`。

## 数据库迁移（已有 Docker 卷）

若从旧版 schema 升级，手动执行：

```sql
ALTER TABLE daily_room_inventories
ADD INDEX idx_status_held_until (status, held_until);
```

房型内容字段（`description` / `amenities` / `image_url`）：

```bash
mysql -h 127.0.0.1 -P 3307 -u aetherstay -paetherstay aetherstay \
  < database/migrations/002_room_types_content_fields.sql
```

系统设置表（自动退房等运行时配置）：

```bash
mysql -h 127.0.0.1 -P 3307 -u aetherstay -paetherstay aetherstay \
  < database/migrations/003_system_settings.sql
```

订单备注字段（代客下单 / 编辑订单）：

```bash
mysql -h 127.0.0.1 -P 3307 -u aetherstay -paetherstay aetherstay \
  < database/migrations/004_booking_notes.sql
```

用户会员资料（等级、积分、联系方式）：

```bash
mysql -h 127.0.0.1 -P 3307 -u aetherstay -paetherstay aetherstay \
  < database/migrations/005_user_membership.sql
```

新环境由 `database/schema.sql` 自动包含上述变更。

## 测试与压测

```bash
# 安装开发依赖
pip install -r tests/requirements-dev.txt

# 单元/集成测试（默认 SQLite，无需 MySQL）
pytest tests/ -v

# Locust 压测
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

详见 [tests/load/README.md](../tests/load/README.md)。
