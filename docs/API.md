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

总价 = 房型基准价 × 入住天数。

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

需要 Cookie 认证。仅本人可操作。`checked_in` / `checked_out` 状态不可取消。

**MCP Tool:** `cancel_booking`

**响应 `200`：**
```json
{
  "message": "Booking cancelled"
}
```

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
| 423 | 房间被锁定（并发抢购，待实现） |

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
