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

## 待记录（开发过程中补充）

- [ ] Locust 并发压测结果（第 6 周）
- [ ] MySQL EXPLAIN 索引优化对比（第 6 周）
- [ ] Nginx MCP 长连接代理调优（第 7 周）
