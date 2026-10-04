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

---

### [2026-10-03] Locust 并发压测（50 用户）

**模块**：后端 / 测试与性能
**阶段**：第 6 周 — 并发压测
**现象/方法**：使用 Locust 对运行中的后端（`localhost:8000`）做无头压测，50 并发用户、30 秒，共 774 次请求、0 失败（约 26 req/s）。脚本见 `backend/locustfile.py`（登录复用预置管理员，任务按权重：搜索 3 / 创建预订 1）。
**结果**：核心指标如下（Avg / P95）：

| 接口 | 次数 | 失败 | Avg | P95 |
|------|------|------|-----|-----|
| GET /api/v1/rooms/search | 703 | 0 | 14ms | 88ms |
| POST /api/v1/bookings | 21 | 0 | 14ms | 17ms |
| POST /api/v1/auth/login | 50 | 0 | 225ms | 400ms |

**分析**：搜索/预订在悲观锁保护下保持亚毫秒到十几毫秒级别；登录最慢，瓶颈是 Argon2id 慢哈希（安全与性能的权衡）。并发争抢同一房间时仅出现预期内的 423（NOWAIT 锁冲突），未产生超卖。
**论文可用点**：用实测数据论证「悲观锁防超卖的性能代价可控」与「慢哈希是认证链路的性能瓶颈」，可作为系统测试章节的量化证据。

---

### [2026-10-03] MySQL EXPLAIN 索引优化对比

**模块**：数据库 / 索引
**阶段**：第 6 周 — 索引优化
**现象**：对预订链路核心查询执行 `EXPLAIN`，发现「我的订单」查询 `WHERE user_id = ? ORDER BY created_at DESC` 出现全表扫描 + `Using filesort`。
**原因**：原仅有单列索引 `idx_user_id(user_id)`，无法覆盖 `created_at` 排序，需另做 filesort。
**解决**：在 `bookings` 上以复合索引 `idx_user_created(user_id, created_at)` 取代单列索引（同步修改 ORM 模型 `backend/app/models/booking.py` 与 `database/schema.sql`）。对比：

- 搜索查询：命中 `idx_date_status(date, status)`（`type=range`）
- 预订加锁查询：命中主键 `PRIMARY(room_id, date)`（`type=range`，锁定精确到「房×日」）
- 「我的订单」优化前：`type=ALL, Extra=Using where; Using filesort`
- 「我的订单」优化后（强制走索引）：`type=ref, key=idx_user_created, Extra=Backward index scan`

**论文可用点**：说明复合索引消除 filesort 的原理；体现「以 EXPLAIN 驱动索引设计」的数据库调优方法论。

---

### [2026-10-03] EXPLAIN ANALYZE 索引顺序对照（真实造数）

**模块**：数据库 / 索引
**阶段**：第 6 周 — 论文意见2落实
**方法**：在 `aetherstay_exp` 库造数 300 间房 × 365 天 = 109,500 条库存、20 万条 bookings，用 `EXPLAIN ANALYZE` 对三条核心查询比较「全表扫描 / 复合索引不同顺序」。脚本 `backend/experiments/explain_index.py`。

| 查询 | 对比项 | 执行时间 | 扫描行数 |
|------|--------|---------|---------|
| 搜索可用房间(`date∈3天`+`status='available'`) | 全表扫描 | 12.9ms | 109,500 |
|  | idx_date_status(date,status) | 0.272ms | 900 |
|  | idx_status_date(status,date) | 0.189ms | 630 |
| 预订加锁(`room_id=?`+`date∈3天` FOR UPDATE) | 全表扫描 | 10.1ms | 109,500 |
|  | 主键 PRIMARY(room_id,date) | 0.015ms | 3 |
| 我的订单(`user_id=?` ORDER BY created_at DESC) | 全表扫描 | 18.2ms | 200,000 |
|  | idx_user_created(user_id,created_at) | 0.032ms | 40 |

**分析**：复合索引相对全表扫描提速 1~2 个数量级、扫描行数下降 99% 以上。「我的订单」复合索引 `(user_id, created_at)` 顺带消除 `Using filesort`（索引天然按 created_at 有序）。对搜索查询，`(status,date)` 因 status 等值先过滤而比 `(date,status)` 少扫 30% 行，但两者均已亚毫秒级；考虑到 `date` 范围常为 3~14 晚的窄区间、且状态枚举仅 4 值（低选择性），二者差异在实际业务中不显著，故保留 `idx_date_status(date,status)` 与主键 `(room_id,date)` 的组合即可满足预订与搜索需求。
**论文可用点**：以真实 SQL + 字段选择性 + 数据分布为依据、用 EXPLAIN ANALYZE 量化比较不同索引顺序与全表扫描的执行时间/扫描行数，论证复合索引设计。

---

### [2026-10-03] 并发控制三策略对照基准（无锁 / 等待锁 / NOWAIT）

**模块**：后端 / 数据库并发控制
**阶段**：第 6 周 — 论文意见6落实
**方法**：固定数据规模（1 间房与 50 间房），以并发梯度对三种预订并发控制策略做对照，度量 TPS、P50/P95/P99、锁冲突率、重试成功率、超售数量。脚本 `backend/experiments/lock_benchmark.py`。

要点（热点争抢 C=50、容量 1）：

| 策略 | 成功预订 | 总超售量 | 说明 |
|------|---------|---------|------|
| 无锁（读-判-写） | 50 | 49 | 并发下同一房间被多次重复预订，发生超卖 |
| 等待锁（FOR UPDATE） | 1 | 0 | 阻塞串行化，正确但排队 |
| NOWAIT+退避重试（本系统） | 1 | 0 | 立即冲突，首轮锁冲突率 82%，无超卖 |

高争用吞吐（50 间房 × 500 请求，随机分配，C=100）：

| 策略 | TPS | P95 | P99 | 成功 | 超售量 |
|------|-----|-----|-----|------|--------|
| 无锁 | 7215/s | 33ms | 44ms | 100 | 50 |
| 等待锁 | 5729/s | 21ms | 22ms | 50 | 0 |
| NOWAIT | 1932/s | 171ms | 179ms | 50 | 0 |

**分析**：无锁策略 TPS 虽最高，但产生 50 条超卖（每间房被重复预订一次），正确性不可接受；等待锁与 NOWAIT 均实现零超卖。NOWAIT 在高争用下因指数退避（50ms·2^n）使尾部延迟升高、TPS 略降，但「失败快速返回 + 客户端重试」避免长事务占用连接；等待锁则通过阻塞串行化避免退避抖动。重试成功率在热点场景为 0/49，是预期结果——房间已被合法持有（HELD），重试本就不应抢占，其作用在于平滑瞬态锁持有与回滚场景，而非抢占已占用资源。
**论文可用点**：用对照组量化「无锁必然超卖、NOWAIT 以有限尾延迟代价换取零超卖」，为悲观锁选型与退避参数（3 次、50ms 基数）提供实验依据。

---

## 待记录（开发过程中补充）

- [x] Locust 并发压测结果（第 6 周）
- [x] MySQL EXPLAIN 索引优化对比（第 6 周）
- [ ] Nginx MCP 长连接代理调优（第 7 周）
