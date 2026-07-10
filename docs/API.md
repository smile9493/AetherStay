# API 参考

> Base URL: `http://localhost:8000/api/v1`  
> 认证方式: HttpOnly Cookie（`access_token`）  
> 交互式文档: http://localhost:8000/docs

## 通用约定

- 请求体：`Content-Type: application/json`
- 日期格式：`YYYY-MM-DD`
- 价格格式：`Decimal` 字符串，如 `"299.00"`
- 日期区间：前闭后开 `[check_in, check_out)`
- 错误响应：`{"detail": "错误信息"}`

## 认证

### 注册

```
POST /auth/register
```

**请求体：**
```json
{
  "username": "alice",
  "password": "secret123"
}
```

**响应 `201`：**
```json
{
  "id": 1,
  "username": "alice",
  "role": "customer",
  "created_at": "2026-07-10T07:16:06"
}
```

### 登录

```
POST /auth/login
```

**请求体：**
```json
{
  "username": "alice",
  "password": "secret123"
}
```

**响应 `200`：**
```json
{
  "message": "Login successful"
}
```

响应头 `Set-Cookie` 写入 `access_token` 和 `refresh_token`。

### 当前用户

```
GET /auth/me
```

需要 Cookie 认证。

**响应 `200`：**
```json
{
  "id": 1,
  "username": "alice",
  "role": "customer",
  "created_at": "2026-07-10T07:16:06"
}
```

### 登出

```
POST /auth/logout
```

清除 Cookie。

## 客房

### 客房列表

```
GET /rooms
```

**响应 `200`：**
```json
[
  {
    "id": 1,
    "room_number": "101",
    "room_type_id": 1,
    "status": "active",
    "room_type": {
      "id": 1,
      "name": "Standard Twin",
      "base_price": "299.00",
      "capacity": 2,
      "total_rooms": 10
    }
  }
]
```

### 搜索可用客房

```
GET /rooms/search?check_in=2026-07-17&check_out=2026-07-19&room_type_id=1
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `check_in` | date | 是 | 入住日期 |
| `check_out` | date | 是 | 退房日期 |
| `room_type_id` | int | 否 | 按房型筛选 |

**MCP Tool:** `get_available_rooms`

返回在指定日期区间内所有天均为 `available` 的客房。

## 预订

### 创建预订

```
POST /bookings
```

需要 Cookie 认证。

**请求体：**
```json
{
  "room_id": 1,
  "check_in": "2026-07-17",
  "check_out": "2026-07-19"
}
```

**响应 `201`：**
```json
{
  "id": 1,
  "user_id": 1,
  "room_id": 1,
  "check_in": "2026-07-17",
  "check_out": "2026-07-19",
  "total_price": "598.00",
  "status": "pending",
  "created_at": "2026-07-10T07:16:09",
  "room": { "..." }
}
```

**MCP Tool:** `create_booking`

创建预订时执行 Hold 阶段：使用 `SELECT FOR UPDATE NOWAIT` 悲观锁锁定房态，状态设为 `held`，订单为 `pending`。总价 = 房型基准价 × 入住天数。

### 模拟支付确认

```
POST /bookings/{booking_id}/pay
```

需要 Cookie 认证。仅订单本人可操作。将 `pending` 订单确认为 `confirmed`，房态从 `held` 变为 `booked`。

**MCP Tool:** `confirm_booking_payment`

**错误响应：**

- `400 Hold has expired, please create a new booking` — `held_until` 已过期，需重新创建预订
- `409 Inventory on {date} is not held` — 房态不是 HELD（如已被他人确认或释放）

### 我的订单

```
GET /bookings/my
```

需要 Cookie 认证。按创建时间倒序返回。

### 订单详情

```
GET /bookings/{booking_id}
```

需要 Cookie 认证。仅本人或 admin 可查看。

**MCP Tool:** `get_booking`

### 取消订单

```
POST /bookings/{booking_id}/cancel
```

需要 Cookie 认证。仅本人可操作。`checked_in` / `checked_out` 状态不可取消。同步释放关联房态为 `available`。

**MCP Tool:** `cancel_booking`

**响应 `200`：**
```json
{
  "message": "Booking cancelled"
}
```

## 管理员 API

所有 `/admin/*` 端点需要 `admin` 角色。

### 订单管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/bookings` | 全局订单列表（分页；`page` 默认 1，`page_size` 默认 20；支持 `status`、`check_in_from`、`check_in_to` 筛选） |
| POST | `/admin/bookings/{id}/confirm` | 确认 pending 订单 |
| POST | `/admin/bookings/{id}/check-in` | 办理入住 |
| POST | `/admin/bookings/{id}/check-out` | 办理退房 |

### 客房管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/rooms` | 客房列表（分页；含 inactive） |
| POST | `/admin/rooms` | 新增客房并生成 90 天房态 |
| PUT | `/admin/rooms/{id}` | 更新门牌号/房型/状态 |

### 房型管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/room-types` | 房型列表（分页） |
| POST | `/admin/room-types` | 新增房型 |
| PUT | `/admin/room-types/{id}` | 更新房型 |

### 房态日历

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/inventory` | 房态矩阵（按房间分页：`page`、`page_size` 默认 10） |

### 用户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/users` | 用户列表（分页：`page`、`page_size`） |
| POST | `/admin/users/{id}/disable` | 禁用用户 |

### 系统设置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/settings/auto-checkout` | 获取自动退房配置（开关、触发时间、时区） |
| PUT | `/admin/settings/auto-checkout` | 更新自动退房配置（仅 `checked_in` 订单到期自动退房） |

请求体示例（PUT）：

```json
{
  "enabled": true,
  "checkout_time": "12:00",
  "timezone": "Asia/Shanghai"
}
```

默认管理员：`admin` / `admin1234`

## 状态码

| 码 | 含义 |
|----|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 冲突（如用户名已存在、房间已被占用） |
| 423 | 房间被锁定（并发抢购 NOWAIT 快速失败） |

## 健康检查

```
GET /health
```

```json
{
  "status": "ok",
  "app": "AetherStay",
  "version": "0.1.0"
}
```
