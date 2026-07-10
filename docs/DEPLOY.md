# AetherStay 生产部署指南

> 本文档指导将 AetherStay 部署到生产环境，涵盖安全配置、Docker 部署、域名绑定、SSL 证书、备份与监控。

---

## 目录

- [前置要求](#前置要求)
- [安全清单](#安全清单)
- [Docker 生产部署](#docker-生产部署)
- [数据库安全与备份](#数据库安全与备份)
- [域名与 SSL](#域名与-ssl)
- [Nginx 调优](#nginx-调优)
- [监控](#监控)
- [升级指南](#升级指南)
- [故障排查](#故障排查)

---

## 前置要求

| 要求 | 说明 |
|------|------|
| Linux 服务器 | Ubuntu 22.04+ / Debian 12+ / CentOS 8+ |
| Docker & Docker Compose | Docker 24+，Compose v2+ |
| 域名（可选） | 用于 HTTPS 证书绑定 |
| 端口 | 80（HTTP）、443（HTTPS）、3307（MySQL 管理） |

## 安全清单

> 🚨 **部署生产前请逐项确认以下配置**

| # | 检查项 | 操作 | 风险等级 |
|---|--------|------|----------|
| 1 | **替换 `SECRET_KEY`** | 生成 64 字节随机串（见下文） | 🔴 高 |
| 2 | **设置 `COOKIE_SECURE=true`** | 确保 Cookie 仅通过 HTTPS 传输 | 🔴 高 |
| 3 | **关闭调试模式** | `DEBUG=false` | 🟡 中 |
| 4 | **更改数据库密码** | 随机生成密码，替换 `.env` 和 `docker-compose.yml` | 🔴 高 |
| 5 | **配置 CORS 白名单** | `CORS_ORIGINS` 限定为具体域名，不使用通配符 | 🟡 中 |
| 6 | **绑定数据库端口** | 生产环境关闭 MySQL 外网端口暴露 | 🟡 中 |
| 7 | **开启 HTTP Only Cookie** | 默认开启，检查 `samesite="lax"` | 🟢 低 |
| 8 | **配置防火墙** | 仅开放 80/443 端口 | 🟡 中 |

### 生成密钥

```bash
# 生成 64 字节随机密钥
python3 -c "import secrets; print(secrets.token_hex(64))"

# 输出示例：a1b2c3d4e5f6...
```

### 生成数据库密码

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"

# 输出示例：x7y8z9...
```

---

## Docker 生产部署

### 1. 准备环境

```bash
# 克隆项目
git clone https://github.com/your-org/AetherStay.git
cd AetherStay

# 配置环境变量
cp .env.example .env
```

编辑 `.env`：

```ini
DEBUG=false
SECRET_KEY=<生成的 64 字节密钥>
DATABASE_URL=mysql+aiomysql://aetherstay:<新密码>@mysql:3306/aetherstay
CORS_ORIGINS=["https://your-domain.com"]
COOKIE_SECURE=true
```

编辑 `docker-compose.yml`，修改 MySQL 密码：

```yaml
environment:
  MYSQL_ROOT_PASSWORD: <随机 root 密码>
  MYSQL_PASSWORD: <随机 aetherstay 密码>
```

### 2. 启动服务

```bash
docker compose up -d --build
```

验证：

```bash
# 健康检查
curl http://localhost:8000/health

# 预期输出
{"status":"ok","app":"AetherStay","version":"0.1.0"}
```

### 3. 初始化管理员

创建默认管理员账号：

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<强密码>"}'
```

---

## 数据库安全与备份

### 自动备份脚本

```bash
#!/bin/bash
# /etc/cron.daily/aetherstay-backup

BACKUP_DIR=/var/backups/aetherstay
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_USER=aetherstay
DB_PASS=<密码>
DB_NAME=aetherstay
CONTAINER=aetherstay-mysql

mkdir -p "$BACKUP_DIR"

docker exec "$CONTAINER" mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" \
  | gzip > "$BACKUP_DIR/aetherstay_$TIMESTAMP.sql.gz"

# 保留最近 30 天备份
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
```

### 还原

```bash
gunzip < backup.sql.gz | docker exec -i aetherstay-mysql mysql \
  -uaetherstay -p<密码> aetherstay
```

---

## 域名与 SSL

### 使用 Nginx Proxy Manager（推荐）

```bash
docker run -d \
  --name npm \
  -p 80:80 -p 443:443 \
  -v npm_data:/data \
  -v npm_letsencrypt:/etc/letsencrypt \
  jc21/nginx-proxy-manager:latest
```

在 NPM 面板中：
1. 添加 Proxy Host → `your-domain.com` → 转发到 `http://aetherstay-frontend:80`
2. 开启 SSL → Let's Encrypt 自动申请证书

### 手动 Nginx SSL 配置

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}
```

---

## Nginx 调优

生产环境的 Nginx 配置模板（`frontend/nginx.conf`）：

```nginx
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 2048;
    use epoll;
    multi_accept on;
}

http {
    # ... 复用现有配置 ...

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml image/svg+xml;
    gzip_min_length 1024;
    gzip_vary on;

    # 安全头
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000" always;
}
```

---

## 监控

### 健康检查端点

```bash
# 后端存活检查
GET /health
# {"status":"ok","app":"AetherStay","version":"0.1.0"}
```

### Docker Compose 健康检查

项目已内置 healthcheck（参见 `docker-compose.yml`）：

```yaml
healthcheck:
  test: ["CMD", "python", "-c",
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 15s
```

### 查看服务状态

```bash
# 各容器运行状态
docker compose ps

# 日志（实时）
docker compose logs -f --tail=100

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f frontend
```

### 资源使用

```bash
# 容器资源占用
docker stats

# MySQL 连接数
docker exec aetherstay-mysql mysqladmin status -uroot -p<root密码>
```

---

## 升级指南

### 数据库迁移

当 `database/schema.sql` 或 `database/migrations/` 有更新时：

```bash
# 备份当前数据
docker exec aetherstay-mysql mysqldump -uaetherstay -p<密码> aetherstay > pre_upgrade.sql

# 执行迁移脚本
cat database/migrations/<NNN>_<name>.sql \
  | docker exec -i aetherstay-mysql mysql -uaetherstay -p<密码> aetherstay
```

### 应用升级

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker compose up -d --build

# 验证
curl http://localhost:8000/health
```

---

## 故障排查

| 问题 | 检查点 |
|------|--------|
| 后端 502 | `docker compose logs backend` 查看启动错误 |
| 前端白屏 | 浏览器 F12 → Console 查看 API 调用错误 |
| 数据库连接失败 | 检查 `DATABASE_URL` 中密码是否正确 |
| Cookie 登录失败 | 检查 `COOKIE_SECURE` 是否与协议匹配（HTTPS→true） |
| 跨域错误 | 检查 `CORS_ORIGINS` 是否包含前端域名 |
| 预订锁冲突过多 | 检查 `HOLD_TTL_MINUTES` 是否过小（建议 ≥15） |

---

## 参考

- [docs/DEV.md](DEV.md) — 本地开发指南
- [docker-compose.yml](../docker-compose.yml) — 服务编排配置
- [frontend/nginx.conf](../frontend/nginx.conf) — Nginx 反向代理
