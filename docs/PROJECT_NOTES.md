# AetherStay 项目开发笔记

> 记录开发过程中遇到的 Bug、技术难点与解决方案，作为毕业论文「系统实现」「关键技术」「测试与调试」等章节的原始素材。  
> 新增条目请按模板追加，**不要删除历史记录**。

## 使用说明

- 每解决一个非平凡问题，追加一条记录
- 论文写作时可按「模块 / 技术点」检索本文件
- 关联代码路径、错误日志、修复提交（如有）尽量写全

---

## 记录模板

```markdown
### [YYYY-MM-DD] 简短标题

**模块**：后端 / 前端 / 数据库 / Docker / …
**阶段**：第 N 周 / 功能名称
**现象**：用户或测试看到的表现
**原因**：根因分析（可附错误日志片段）
**解决**：具体修改（文件路径 + 思路）
**论文可用点**：可写入论文的表述建议（技术难点、创新点、工程经验）
```

---

## 问题记录

### [2026-07-10] 环境变量 CORS_ORIGINS 被 shell 导出破坏

**模块**：后端 / 配置  
**阶段**：第 1 周 — 本地首次启动  
**现象**：后端启动报错 `SettingsError: error parsing value for field "CORS_ORIGINS"`。  
**原因**：使用 `export $(grep -v '^#' .env | xargs)` 导入环境变量时，JSON 数组 `["http://localhost:5173"]` 被 shell 拆成多个变量，pydantic 无法解析。  
**解决**：修改 `backend/app/config.py`，通过 `Path` 直接读取项目根目录 `.env`；启动命令改为 `python run.py`，不再 shell export。  
**论文可用点**：说明配置管理应使用专用加载机制，避免 shell 解析破坏结构化配置；体现生产环境配置规范的重要性。

---

### [2026-07-10] FastAPI Depends 隐式事务与 Service 层 `db.begin()` 冲突

**模块**：后端 / SQLAlchemy 事务  
**阶段**：第 2-3 周 — 悲观锁预订  
**现象**：创建预订返回 500，`A transaction is already begun on this Session`。  
**原因**：`get_current_user` 等 Depends 在同一 `AsyncSession` 上执行 SELECT 后已隐式开启事务，Service 层再调用 `async with db.begin()` 触发冲突。  
**解决**：新增 `backend/app/services/transaction.py`，在开启新事务前先 `await db.rollback()` 清理隐式事务；业务逻辑统一通过 `transaction(db)` 上下文管理器执行。  
**论文可用点**：阐述 FastAPI 依赖注入与 SQLAlchemy 会话生命周期的交互；说明分层架构中事务边界的工程设计。

---

### [2026-07-10] rollback 后 ORM 懒加载触发 MissingGreenlet

**模块**：后端 / SQLAlchemy 异步  
**阶段**：第 2-3 周 — 悲观锁预订  
**现象**：预订创建失败，`MissingGreenlet: greenlet_spawn has not been called`。  
**原因**：在 `transaction()` 执行 `rollback()` 后，事务外预加载的 `room.room_type` 对象会话失效，事务内访问 `room.room_type.base_price` 触发同步懒加载，在异步上下文中失败。  
**解决**：将房间查询移入 `transaction(db)` 块内部，确保事务内数据访问在同一会话、同一 greenlet 中完成。  
**论文可用点**：说明 SQLAlchemy 2.0 异步模式下 ORM 懒加载的限制；强调应用层事务内完成关联数据加载的必要性。

---

### [2026-07-10] MySQL 已有库缺少 is_active 字段

**模块**：数据库 / 迁移  
**阶段**：第 2-3 周 — 管理员与用户禁用  
**现象**：启动或查询用户时报列不存在错误（新字段 `is_active`）。  
**原因**：`schema.sql` 仅在新库初始化时执行，已运行的 Docker 卷不会自动应用 DDL 变更。  
**解决**：对已有库执行 `ALTER TABLE users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1`；新环境在 `schema.sql` 的 CREATE TABLE 中已包含该字段。  
**论文可用点**：讨论开发环境与生产环境数据库版本管理；可引出迁移脚本或版本化 DDL 的必要性。

---

### [2026-07-10] Hold-then-Confirm 初版未锁房态导致超卖风险

**模块**：后端 / 业务逻辑  
**阶段**：第 1 周 → 第 2-3 周  
**现象**：脚手架阶段 `create_booking` 仅插入 `bookings` 记录，不更新 `daily_room_inventories`，并发下可能超卖。  
**原因**：第一阶段仅实现 API 骨架，未实现设计文档中的悲观锁与房态联动。  
**解决**：实现 `inventory_service.lock_inventory_for_update(nowait=True)` 与 `booking_service.create_hold_booking()`，创建订单时将房态置为 `held` 并设置 `held_until`。  
**论文可用点**：作为系统核心难点——高并发防超卖的两阶段锁定机制（Hold-then-Confirm）的实现依据。

### [2026-07-10] Hold 过期窗口一致性修复（P0/P1）

**模块**：后端 / 业务逻辑 + 搜索接口  
**阶段**：第 3 周 — Hold-then-Confirm 加固  
**现象**：`held_until` 已过期但调度器尚未释放（0-60s 窗口）时：
- `create_booking` 返回 409（误判为不可预订）
- `rooms/search` 不返回该房间（房态不展示）
- `confirm_booking` 仍允许支付（本应拒绝过期 hold）

**原因**：所有路径均将 `held` 状态视为不可预订，未区分「有效 hold」与「过期 hold」；过期释放完全依赖 APScheduler 定时任务，存在窗口期。

**解决**：

1. **抽取判定函数**（`inventory_service.py`）：`is_bookable()` 将过期 held 视同 available；`is_held_valid()` 仅对未过期 held 返回 True。
2. **`create_hold_booking`**：遍历 `daily_records` 时对过期 held 在同一事务内先 `mark_available()` 再 `mark_held()`，无需等待调度器。
3. **`confirm_booking`**：加固校验——仅接受 HELD 状态（拒绝 BOOKED 防重复确认）、校验 `held_until >= now`、校验天数完整性。
4. **`release_expired_holds`**：重构为单事务 + `FOR UPDATE` 行锁；分组处理时对 PENDING 订单取消 + 释放，对非 PENDING 订单仅释放房态；处理无关联 booking_id 的孤儿行。
5. **`rooms/search`**：子查询条件增加 `OR (status='held' AND held_until < UTC_TIMESTAMP())`，使过期 held 房间重新出现在搜索结果中。

**修复提交**：`259f560`  
**论文可用点**：分布式环境下「读取路径 + 写入路径」一致性治理的典型案例——通过统一判定函数消除调度器延迟造成的线程间不一致，体现工程中「防御性读取」的设计思想。

---

### [2026-07-10] 行锁未置于事务内导致 release_expired_holds 可能漏锁

**模块**：后端 / SQLAlchemy 事务边界  
**阶段**：第 3 周 — Hold 过期修复  
**现象**：原 `release_expired_holds` 先 SELECT 过期记录（无锁），再在事务内逐条处理，并发下可能读取到已过期的快照后被其他事务修改。  
**原因**：FOR UPDATE 需要与事务绑定，原实现将查询放在 `transaction(db)` 块之外。  
**解决**：将 `SELECT ... WHERE ... FOR UPDATE` 整体放入 `transaction(db)` 上下文管理器内。  
**论文可用点**：说明 SELECT FOR UPDATE 的事务依赖性及「查询即加锁」的工程约束。

---

### [2026-07-10] 第 6 周 — Locust 并发预订压测

**模块**：测试 / 并发控制  
**阶段**：第 6 周 — 压测验证  
**场景**：25 并发用户、20 秒，S1 同一房间（room_id=2, 2026-08-09~11）争抢预订 + S2 搜索混合流量。  
**结果**：

| 指标 | 值 |
|------|-----|
| 并发用户 | 25 |
| 持续时间 | 20s |
| S1 预订请求 | 128 |
| 201 success_hold | 1 |
| 423 Locked | 3 |
| 409 Conflict | 125 |
| 超卖 SQL 校验 | 0 行（无重复占用） |

**结论**：`SELECT FOR UPDATE NOWAIT` + Hold 状态机在并发下有效防止超卖；仅 1 个请求成功创建 Hold，其余被拒绝。  
**论文可用点**：并发压测数据支撑「两阶段锁定机制」有效性论述；可配图展示 201 vs 423/409 分布。

---

### [2026-07-10] 第 6 周 — MySQL 索引优化（idx_status_held_until）

**模块**：数据库 / 性能优化  
**阶段**：第 6 周 — EXPLAIN 分析  
**背景**：`release_expired_holds` 定时任务扫描 `status='held' AND held_until < now`，原索引 `idx_date_status` 无法高效覆盖。  
**改动**：`daily_room_inventories` 新增 `INDEX idx_status_held_until (status, held_until)`。  
**EXPLAIN 对比（调度扫描）**：

| 指标 | 优化后 |
|------|--------|
| type | range |
| key | idx_status_held_until |
| Extra | Using where; Using index |

**悲观锁查询**（`room_id + date range FOR UPDATE`）：命中 PRIMARY，type=range，rows=2。  
**论文可用点**：Sargability 与复合索引设计；调度任务与预订锁查询的索引策略差异。

---

### [2026-07-10] 前端首页改版：从技术演示站转为标准酒店预订站

**模块**：前端 / 用户体验  
**阶段**：第 4-5 周 UI 打磨  
**现象**：原首页以「MCP Console」「AI Agent 模拟器」「核心设计架构」卡片为主，更像项目展示页，不符合市面酒店官网的用户预期。  
**原因**：脚手架阶段首页用于演示双模交互（REST + MCP）与 Hold-then-Confirm 机制，未按 C 端预订流程设计。  
**解决**：

1. **重写 `HomeView.vue`**：Hero 横幅 + 内嵌日期搜索、热门房型（`GET /rooms` 聚合）、酒店设施、简介；移除 AI 模拟器与 MCP 配置面板。
2. **深链打通**：首页搜索跳转 `/rooms?check_in=&check_out=`；「查看详情」可带 `room_type_id`。
3. **`RoomsView.vue`**：`onMounted` 读取 query 并自动搜索；无日期时按 `room_type_id` 客户端过滤列表。
4. **页脚文案**（`MainLayout.vue`）：改为酒店客服风格，去掉技术栈说明。
5. **提交**：`a1b8c80` on `cursor/phase2-booking-hold-admin-scheduler`。

**论文可用点**：说明产品从「技术验证界面」到「用户面向界面」的迭代；可对比改版前后信息架构（营销内容 vs 演示内容）。

---

### [2026-07-10] 首页 Code Review 修复：误导文案与日期校验

**模块**：前端 / 质量  
**阶段**：第 4-5 周 UI 打磨  
**现象**（Review 发现）：

| 问题 | 严重度 |
|------|--------|
| 房型徽章「X 间可订」实为物理房间总数，含维护房且与日期库存无关 | 高 |
| 仅带 `room_type_id` 深链时列表未过滤 | 中 |
| 首页搜索未校验退房 > 入住 | 中 |
| `minCheckOut` 用 `toISOString()` 在部分时区算错 | 中 |
| Hero「即时确认」与 Hold→支付流程不符 | 中 |

**解决**：

1. 新增 `frontend/src/utils/dates.ts`：本地日历日期解析/校验（`isValidDateRange`、`isPastDate`、`isOnOrBeforeDateStr`），首页与客房页共用。
2. 徽章改为「共 X 间」，统计时仅计 `status === 'active'` 房间。
3. Hero 文案改为「完成支付后订单即时确认」。
4. 搜索前校验日期区间；`watch` 入住日期变更时清空无效退房日。
5. 客房页 date-picker 增加 `disabled-date`；`room_type_id` 用 `Number.isFinite` 安全解析。

**论文可用点**：前端营销文案与后端业务状态机一致性的重要性；日期控件在跨时区场景下应使用 date-only 字符串运算而非 UTC ISO 切片。

---

### [2026-07-10] 管理后台与 C 端预订流程前端落地

**模块**：前端 / 管理端  
**阶段**：第 4-5 周 — Admin UI + 预订闭环  
**现象**：后端 Phase 2-3 已提供 Admin API 与 Hold-then-Confirm，但前端仍为脚手架级页面，无法完成搜索→锁定→支付→订单管理的完整用户路径。  
**解决**：

1. **路由与权限**（`router/index.ts`）：嵌套 `/admin/*` 子路由，`meta.requiresAdmin` + `RoleChecker` 前端守卫，非 admin 跳转首页并提示越权。
2. **管理布局**（`AdminLayout.vue`）：侧栏导航 + 玻璃拟态面板，挂载 Dashboard / 订单 / 客房 / 房型 / 用户五个视图。
3. **C 端闭环**（`RoomsView.vue`、`BookingsView.vue`）：搜索可用房 → `POST /bookings` 创建 Hold → 弹窗内倒计时 → `POST /bookings/{id}/pay` 确认；订单页按状态 Tab 筛选，待支付订单展示剩余锁定时间。
4. **管理 CRUD**（`views/admin/*`）：对接 `/api/v1/admin/bookings|rooms|room-types|users`，Dashboard 聚合统计（订单数、营收、入住率等）。
5. **提交**：`954d86d` on `cursor/phase2-booking-hold-admin-scheduler`。

**论文可用点**：前后端分离下 RBAC 的双层校验（路由守卫 + API `RoleChecker`）；Hold-then-Confirm 在 UI 层的倒计时与支付引导设计。

---

### [2026-07-10] Booking API 补充 held_until 供前端倒计时

**模块**：后端 / API 契约  
**阶段**：第 4-5 周 — 前后端联调  
**现象**：`BookingsView` 需展示 Hold 剩余时间，但 `BookingResponse` 无 `held_until` 字段；前端只能用 `created_at + 15min` 估算，与后端实际 `daily_room_inventories.held_until` 可能不一致。  
**原因**：Hold 截止时间存在库存表而非 `bookings` 表，ORM 直接序列化无法带出该字段。  
**解决**：

1. `BookingResponse` 增加 `held_until: datetime | None`。
2. `booking_service.get_held_until_map()`：`MIN(held_until)` 按 `booking_id` 聚合库存行。
3. `serialize_booking` / `serialize_bookings`：仅对 `PENDING` 订单填充 `held_until`；`bookings.py` 各端点统一走序列化函数。
4. 前端 `BookingsView` 优先使用 `booking.held_until`，无值时回退 `created_at + 15min`。

**论文可用点**：跨表业务字段的 API 聚合设计；说明「订单状态」与「库存锁定截止时间」的数据来源分离及展示层组装策略。

---

### [2026-07-10] CLI 脚手架工具（scaffold.py）

**模块**：工程化 / 开发效率  
**阶段**：第 5 周 — 标准化模块生成  
**现象**：每新增一个业务实体需手工创建 model、schema、service、router、admin 模块及前端 view/store，易漏文件或风格不一致。  
**解决**：新增 `scaffold/scaffold.py`（Jinja2 模板驱动）：

| 命令 | 作用 |
|------|------|
| `init` | 复制 `.env`、安装前后端依赖 |
| `check` | 校验目录结构与模板完整性 |
| `list` | 列出已注册模块 |
| `gen api <name>` | 一次生成 model + schema + service + router |
| `gen admin/task/view/store/component` | 按需生成单层文件 |

生成后提示手动注册 `router.py`、`models/__init__.py` 与 `schema.sql` DDL。  
**提交**：`5c49615`。

**论文可用点**：体现 DRY 原则与分层架构的可复制性；可作为「系统可扩展性设计」的工程支撑。

---

### [2026-07-10] 第 6 周 — pytest 预订核心路径单元测试

**模块**：测试 / 业务逻辑  
**阶段**：第 6 周 — 自动化测试  
**场景**：`tests/test_booking_service.py` 覆盖 Hold-then-Confirm 状态机关键路径。  
**环境**：`TESTING=1` + SQLite（`aiosqlite`）内存库，`conftest.py` 自动建表/清表。  
**用例**（节选）：

| 用例 | 验证点 |
|------|--------|
| `test_create_hold_booking_success` | 创建 Hold 后库存为 HELD |
| `test_create_hold_conflict` | 有效 Hold 冲突返回 409 |
| `test_confirm_expired_hold` | 过期 Hold 确认返回 400 |
| `test_create_hold_booking_expired_hold_reused` | 过期 Hold 可被新用户抢占 |
| `test_concurrent_hold_only_one_succeeds` | 并发仅一个成功 |
| `test_serialize_booking_includes_held_until` | API 序列化带出截止时间 |

**结果**：`8 passed, 11 skipped`（依赖 MySQL 种子库存窗口的集成用例在 SQLite 下 skip）。  
**论文可用点**：单元测试与 Locust 压测互补——前者验证状态机正确性，后者验证并发下的锁行为。

---

### [2026-07-10] Nginx MCP 长连接代理调优

**模块**：前端 / Nginx  
**阶段**：第 7 周 — 生产部署优化  
**背景**：MCP（Model Context Protocol）使用 SSE（Server-Sent Events）长连接，Nginx 默认 60s 超时可能导致连接中断。  
**改动**：`frontend/nginx.conf`：
- `proxy_read_timeout 86400s` / `proxy_send_timeout 86400s` — 24 小时长连接超时
- `proxy_buffering off` / `proxy_cache off` — SSE 实时性要求禁用缓冲
- `proxy_http_version 1.1` + `proxy_set_header Connection ""` — HTTP/1.1 长连接代理
- 新增 `keepalive_timeout 620s` — 确保 Nginx 自身不主动断连

**论文可用点**：SSE 长连接与传统 REST API 的 Nginx 代理配置差异；HTTP/1.1 keep-alive 在微服务网关层的工程实践。

---

## 待记录（开发过程中补充）

- [x] Locust 并发压测结果（第 6 周）
- [x] MySQL EXPLAIN 索引优化对比（第 6 周）
- [x] 前端首页改版与 Review 修复（第 4-5 周）
- [x] 管理后台与 C 端预订流程（第 4-5 周）
- [x] CLI 脚手架工具（第 5 周）
- [x] pytest 预订核心路径测试（第 6 周）
- [ ] Nginx MCP 长连接代理调优（第 7 周）
