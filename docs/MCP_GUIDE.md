# AetherStay MCP Guide — AI 对话式酒店预订

本系统通过 **FastAPI-MCP** 将核心 REST API 自动暴露为 MCP（Model Context Protocol）工具，使 AI 客户端（如 Claude Desktop、Cursor）可直接通过自然语言完成酒店预订全流程。

---

## 配置方法

### Cursor

1. 确保后端已运行（`docker compose up -d backend` 或 `uvicorn app.main:app`）
2. Cursor 会自动检测 `http://localhost:8000/mcp` — 无需手动配置

### Claude Desktop

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "aetherstay": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

## 可用工具列表

| 工具 | 描述 | 是否需要登录 |
|------|------|------------|
| `login` | 用户登录（注册后使用），返回 cookie | — |
| `get_available_rooms` | 按日期范围搜索可用房间 | 否 |
| `create_booking` | 创建 Hold 预订锁房 | 是 |
| `get_booking` | 查询单笔订单详情 | 是 |
| `cancel_booking` | 取消预订释放库存 | 是 |
| `confirm_booking_payment` | 确认支付将 Hold → Confirmed | 是 |

> **注意**：所有需要登录的工具通过 Cookie 鉴权。AI 客户端需先调用 `login` 获得会话 cookie 后，后续工具调用会自动携带。

---

## 完整对话示例

以下展示从自然语言到预订成功的完整对话流程：

### 步骤 1: 注册 / 登录

**用户**：
```
我想预订酒店房间，先帮我注册一个账号。

用户名：testuser1
密码：TestPass123
```

**AI → 调用 `POST /api/v1/auth/register` → 注册成功**

**用户**：
```
登录我的账号。
```

**AI → 调用 `POST /api/v1/auth/login` → 设置 Cookie**

### 步骤 2: 搜索可用房间

**用户**：
```
帮我查一下7月15日到7月17日有哪些房间可选？
```

**AI → 调用 `GET /api/v1/rooms/search?check_in=2026-07-15&check_out=2026-07-17`**

**返回示例**：
```
有3间可用客房：
1. 房号 101 — Standard Twin（¥398/晚，可住2人）
2. 房号 104 — Standard Twin（¥398/晚，可住2人）
3. 房号 201 — Deluxe King（¥598/晚，可住2人）
```

### 步骤 3: 创建预订（Hold）

**用户**：
```
我要预订201号房，Deluxe King，7月15日入住，7月17日退房。
```

**AI → 调用 `POST /api/v1/bookings` → 返回 Hold 订单**

**返回示例**：
```
预订成功！订单号 #23，状态为待支付锁定。
总价：¥1196.00
锁房将在15分钟后过期，请尽快完成支付。
```

### 步骤 4: 确认支付

**用户**：
```
确认支付订单 #23。
```

**AI → 调用 `POST /api/v1/bookings/23/pay` → 状态更新为 Confirmed**

**返回示例**：
```
支付成功！订单 #23 已确认为 Confirmed 状态。
入住日期：2026-07-15
退房日期：2026-07-17
房型：Deluxe King
祝您入住愉快！
```

---

## 管理员专有工具（后续扩展）

以下工具需 `admin` 角色登录后使用：

| 工具 | 端点 | 用途 |
|------|------|------|
| `get_booking_stats` | `GET /admin/stats` | 获取系统订单统计 |
| `list_all_bookings` | `GET /admin/bookings` | 按状态筛选全部订单 |

---

## 技术说明

- **协议**：基于 FastAPI-MCP 自动挂载，无需手写 Tool Schema
- **认证**：通过 HTTP-Only Cookie 传递，AI 客户端退出后凭证自动失效
- **幂等性**：`create_booking` 已处理重复请求，同一房间相同时段不会重复锁房
- **超时机制**：Hold 预订 15 分钟后自动释放，AI 可提示用户尽快确认

---

## 论文价值

MCP 是本系统最大的创新亮点——**同一套 REST API** 通过 FastAPI-MCP 自动暴露为 AI Agent 工具，实现「人机双模」访问：

1. **传统模式**：用户通过 Web 浏览器进行预订
2. **AI 模式**：用户通过自然语言对话，AI 代理自动调用 API 完成预订

这种架构设计减少了对定制聊天机器人的开发成本，为现有 Web 系统提供了一条「零改造接入 AI」的可行路径。
