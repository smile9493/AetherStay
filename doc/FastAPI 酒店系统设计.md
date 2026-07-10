# **基于 FastAPI \+ Vue3 的酒店客房预订管理系统总体方案设计与并发控制深度研究报告**

在移动互联网与人工智能深度融合的背景下，酒店及民宿行业的信息化管理正经历从传统的“图形用户界面（GUI）”向“对话即服务（CaaS）”与“智能体原生（Agent-Native）”的范式演进 \[cite: 1.1\]。传统的酒店管理系统（PMS）架构多依赖于 Java 或 .NET 等重型框架，部署复杂、维护成本高，且难以灵活适应大语言模型（LLM）智能体的动态调度 \[cite: 1.1\]。本报告提出一种基于 Python 异步生态 FastAPI 与渐进式前端框架 Vue3 的轻量级、高性能酒店客房预订管理系统设计方案，并创新性地集成模型上下文协议（Model Context Protocol, MCP） \[cite: 1.1, 1.2\]，使系统既能通过现代化的 Web 浏览器提供给人类用户使用，也能被 AI 助手（如 Claude、Cursor 等）自动探知并调用，实现“自然语言即预订”的交互模式 \[cite: 1.1, 1.2\]。  
本报告将对系统的技术选型、双模发布架构、每日房态数据库模型、高并发悲观锁机制、以 HttpOnly Cookie 为核心的安全认证以及 Nginx 生产级长连接代理进行深度解构。

## **一、 技术选型与技术优势深度剖析**

系统的技术选型旨在平衡高并发吞吐、敏捷开发、类型安全以及大模型原生对接的需求 \[cite: 1.1, 1.2\]。具体的技术栈配置及其架构合理性如表 2-1 所示：

### **表 2-1：系统核心技术栈选型与应用价值**

| 架构层级 | 选用技术 | 技术选型理由与核心优势 | 生产级安全/性能策略 |
| :---- | :---- | :---- | :---- |
| **后端 Web 框架** | FastAPI (Python 3.10+) \[cite: 1.2\] | 基于 Starlette 与 Pydantic，支持原生异步协程，具备极佳的 I/O 密集型并发处理能力；自动生成合规的 OpenAPI 交互式文档 \[cite: 1.2, 31, 91\]。 | 结合 FastAPI 依赖注入（Dependency Injection）实现请求级生命周期管理与连接池缓存1。 |
| **数据库** | MySQL 8.0 \[cite: 1.2\] | 成熟稳定的关系型数据库，完全支持 ACID 事务，并在 InnoDB 引擎中支持先进的行级锁与非阻塞锁定读3。 | 采用物理分区与 B-Tree 复合索引联合优化，消除大范围日期检索时的区间扫描开销6。 |
| **ORM 框架** | SQLAlchemy 2.0 (异步) \[cite: 1.2\] | 采用全新的 2.0 统一式 API，全面弃用传统的 Query 语法8；原生适配异步引擎与 AsyncSession 上下文，彻底避免数据库 I/O 阻塞 Python 事件循环3。 | 使用 async\_sessionmaker 构建连接工厂，并在生命周期钩子中安全释放连接归还连接池9。 |
| **前端框架** | Vue 3 (Composition API) \[cite: 1.2\] | 渐进式前端框架，具备极高的运行时性能和极低的学习曲线 \[cite: 1.2\]；响应式系统基于 Proxy 实现，大大减少组件不必要的重绘。 | 结合 Vite 构建工具，实现冷启动秒级加载与极致的代码分包（Code Splitting） \[cite: 1.2\]。 |
| **UI 组件库** | Element Plus \[cite: 1.2\] | 成熟的 Vue 3 组件生态，提供丰富的开箱即用中后台业务组件（如时间区间选择器、动态表格等） \[cite: 1.2\]。 | 采用按需引入（Auto Import）机制，大幅缩减前端最终打包体积。 |
| **构建工具** | Vite \[cite: 1.2\] | 基于原生 ESM 的极速冷启动，采用 Rollup 执行生产打包，开发体验极佳 \[cite: 1.2\]。 | 配置代码分割与动态导入，提升首屏渲染速度（FP/FCP）。 |
| **认证方案** | JWT (JSON Web Token) \[cite: 1.2\] | 无状态、自包含的认证凭证，天然适配前后端分离的分布式或容器化架构 \[cite: 1.2, 65\]。 | 摒弃 LocalStorage 存储，强制将 Token 写入 HttpOnly 及 SameSite 的安全 Cookie 中11。 |
| **MCP 集成方案** | **FastAPI-MCP** \[cite: 1.2, 8\] | Tadata 团队开源的桥接器，通过在 ASGI 协议层直接拦截，只需数行代码即可将现有的 FastAPI 路由直接转换为合规的 MCP 工具13。 | 保留 Pydantic 的入参和出参 Schema 定义，完美兼容 Depends 依赖项注入13。 |
| **反向代理与部署** | Docker \+ Nginx \[cite: 1.2\] | 容器化技术保证开发与线上生产环境的一致性 \[cite: 1.2\]；Nginx 充当反向代理、静态资源服务器及流量网关15。 | 针对 MCP 的 SSE/流式 HTTP 链路实施 proxy\_buffering off 调优，防止代理层数据积压17。 |

### **1.1 FastAPI 异步特性的学理分析**

传统的同步多线程 Web 框架（如 Flask、Django）在应对高并发酒店搜索与预订请求时，每一个传入的 HTTP 请求都会独占一个线程10。当遇到数据库查询、外部支付网关回调、大模型接口响应等慢速 I/O 操作时，该线程将进入阻塞挂起状态，导致高并发场景下线程上下文切换频繁，极易耗尽系统内存3。  
FastAPI 基于 ASGI 异步网关规范，利用 Python 的 asyncio 事件循环（Event Loop）机制10。当协程执行数据库异步查询（如通过 await session.execute()）时，当前协程会自动向事件循环交出 CPU 控制权，允许事件循环在此期间处理其他传入的并发 HTTP 请求8。这使得单台物理服务器能够以极低的资源开销维持数万个并发长连接（C10K 问题），非常适合高频的房态检索和 AI Agent 交互会话19。

### **1.2 桥接框架 FastAPI-MCP 的深层机制对比**

在将现有的 FastAPI 接口暴露给大语言模型时，业界存在三种主要的实现路径21。为了明确为何在本项目中采用 **FastAPI-MCP** 作为核心集成工具，需对其进行深度的学理与工程对比13：

### **表 2-2：Python 生态中三种 MCP 实现框架的工程对比**

| 评估维度 | 方案一：官方 Python SDK | 方案二：FastMCP (Prefect 团队) | 方案三：FastAPI-MCP (Tadata 团队) |
| :---- | :---- | :---- | :---- |
| **集成模式** | 底层协议参考实现，需手动注册 JSON-RPC 消息、传输通道和生命周期25。 | 独立的 Greenfield 框架，基于装饰器快速声明 Tools、Resources 和 Prompts13。 | **完全的 FastAPI 原生扩展**。通过 ASGI 机制直接包装既有的 FastAPI 路由并挂载13。 |
| **接入成本** | 极高，需要为每一个 API 编写繁琐的消息处理和通道包装代码21。 | 中等，如果已有成熟的 FastAPI 服务，需要重新用 FastMCP 的装饰器编写一层包装层13。 | **极低，近乎零侵入**。只需传入已有的 app 实例并执行 mcp.mount() 即可自动生成服务器13。 |
| **架构统一性** | 必须将 Web 服务与 MCP 服务拆分为两个独立运行的物理进程。 | 通常作为独立进程运行，虽然可以挂载，但其核心运行机制仍与 FastAPI 存在隔离。 | **物理与逻辑的高度统一**。同一套后台进程、同一个运行端口，共享所有的中间件、日志和路由链13。 |
| **Pydantic 兼容性** | 需手动将入参解析并转换为规范的 JSON Schema。 | 自动基于 Python 函数的类型签名和 Docstring 推导生成合规的 JSON Schema24。 | **原生继承。** 完美复用 FastAPI 路由上的 Pydantic 定义、Operation ID 以及 Swagger 中的文档描述13。 |
| **认证与依赖注入** | 需在传输层或消息处理体中手动编写认证逻辑。 | 支持其内置的 JWT 验证器或 OAuth2 机制13。 | **复用 FastAPI Depends()。** 在调用 MCP 工具时，可复用既有的 API 依赖链验证 Token 权限13。 |

通过对比可知，对于拥有丰富既有 API 路由和依赖注入链的酒店管理系统，**FastAPI-MCP** 是最具生产力和架构优雅性的桥接选择13。它利用底层的 ASGI Transport，避免了在调用工具时产生不必要的网络环回（Loopback）HTTP 损耗13，从而确保了 AI Agent 驱动的预订事务能够以极致的低延迟在后台执行14。

## **二、 系统架构与双模发布体系设计**

系统的整体架构采用前后端分离的设计模式，并在此基础上进行了“人类用户（GUI）与 AI 智能体（MCP）”双模协同的创新扩展 \[cite: 1.2, 8\]。

### **2.1 总体多层拓扑架构**

系统的整体运行架构由五个核心层级构成，通过清晰的职责划分，实现传统 Web 前端与现代 AI 智能体的无缝连接：

\+-----------------------------------------------------------------------------------+  
|                            人类与 AI 客户端层 (Clients)                            |  
|    \+------------------------+                     \+---------------------------+   |  
|    |  浏览器 (Vue 3 网页应用) |                     |  AI 智能体 (Claude/Cursor) |   |  
|    \+-----------+------------+                     \+-------------+-------------+   |  
\+----------------|------------------------------------------------|-----------------+  
                 | (标准 HTTPS REST API / v1)                      | (JSON-RPC over SSE / HTTP) \[cite: 25, 28\]  
                 v                                                v  
\+-----------------------------------------------------------------------------------+  
|                               反向代理与网关层 (Nginx)                             |  
|    \- 提供统一的 SSL 卸载、静态页面服务、并针对普通 API 路由与 MCP 路由进行精准转发  |  
\+------------------------+----------------------------------------+-----------------+  
                         |                                        |  
                         v                                        v  
\+-----------------------------------------------------------------------------------+  
|                        后端应用层 (FastAPI Application & ASGI)                     |  
|   \+---------------------------------------------------------------------------+   |  
|   | 路由层 (Routers)                                                          |   |  
|   |   \- REST API 控制器 (提供 Web 应用端点，支持 JSON 交换)                    |   |  
|   |   \- FastAPI-MCP 桥接控制器 (自动暴露符合 MCP 协议的 Tools & 传输层) \[cite: 13, 29\] |   |  
|   \+-------------------------------------+-------------------------------------+   |  
|                                         |  
|                                         v  
|   \+---------------------------------------------------------------------------+   |  
|   | 认证与依赖注入中间件 (Depends / Auth Middleware)                           |   |  
|   |   \- JWT 解析、HttpOnly Cookie 验证、基于 \`RoleChecker\` 的 RBAC 校验 \[cite: 11, 30\] |   |  
|   \+-------------------------------------+-------------------------------------+   |  
|                                         |  
|                                         v  
|   \+---------------------------------------------------------------------------+   |  
|   | 业务逻辑层 (Service / Business Domain)                                     |   |  
|   |   \- 日期冲突检测算法 (Allen 区间代数判定)                         |   |  
|   |   \- 悲观锁事务编排器 (SQLAlchemy Transaction Manager) \[cite: 2, 3\]           |   |  
|   \+-------------------------------------+-------------------------------------+   |  
|                                         |  
|                                         v  
|   \+---------------------------------------------------------------------------+   |  
|   | 数据访问层 (DAO \- SQLAlchemy 2.0 Async ORM)                                |   |  
|   \+---------------------------------------------------------------------------+   |  
\+-----------------------------------------|-----------------------------------------+  
                                          v (aiomysql 异步驱动连接池)  
\+-----------------------------------------------------------------------------------+  
|                            数据持久化与高可靠性存储层 (Storage)                     |  
|    \+-------------------------------------------------------------------------+    |  
|    |  MySQL 8.0 关系型数据库 (InnoDB 存储引擎，完全保障事务的 ACID 强一致性) \[cite: 1.2, 40\] |    |  
|    \+-------------------------------------------------------------------------+    |  
\+-----------------------------------------------------------------------------------+

### **2.2 双模发布机制原理解析**

在同一套后端服务中同时实现 REST API 和 MCP 协议，被称为**双模发布机制**13。 FastAPI-MCP 通过拦截 FastAPI 的路由树，提取每一个端点（Endpoint）的方法名、类型提示（Type Hints）、文档字符串（Docstring）以及相关的 Pydantic 校验模型，自动将它们转换为符合模型上下文协议格式的“工具说明书”（Tool Definition JSON Schema）13。  
当 AI 客户端（如 Claude Desktop 或 Cursor）发起初始化握手时，通过标准的 Server-Sent Events（SSE）或 HTTP 传输协议请求 /mcp/ 路径28：

1. **自动探知**：FastAPI-MCP 控制器向大模型列出所有可用的 Tools，其中工具名对应 FastAPI 路由的 operation\_id，功能描述对应 Python 方法的 Docstring22。  
2. **动态转化**：当前端人类用户在网页上进行图形化点击时，请求照常发送给 /api/v1/\* 路由并正常返回普通 JSON 报文 \[cite: 三, 29\]；而当 AI 客户端决定调用某个工具时，其会通过 ASGI 传输通道发送标准的 JSON-RPC 请求至 /mcp/13，经过桥接层在内存中将数据结构化，并像普通 HTTP 请求一样交由同一个 Service 业务逻辑层处理，最后将数据封装为 JSON-RPC 格式响应返还给 AI13。  
3. **零重复逻辑**：此设计确保了核心业务算法（如防止重叠预订和实时计价）仅需在一处实现，大大降低了维护复杂性，避免了传统 PMS 在进行 AI 化改造时产生两套独立后端的架构陷阱13。

## **三、 功能模块划分与业务生命周期编排**

系统功能在业务逻辑上分为三个核心维度，覆盖人类客户、酒店管理员以及 AI 智能体的交互边界：

### **表 3-1：系统功能模块分类及业务边界**

| 维度 | 功能模块 | 对应路由 / 接口端点 | 业务安全要求与行为约束 |
| :---- | :---- | :---- | :---- |
| **面向普通用户** \[cite: 4.1\] | **用户注册与认证** | POST /api/v1/auth/register POST /api/v1/auth/login | 登录成功后，安全将 JWT 存入 HttpOnly Cookie 中，避免凭证泄露11。 |
|  | **客房浏览与检索** | GET /api/v1/rooms/search | 支持按入住日期、退房日期、房型联合检索，需配合高精度日期冲突检测 \[cite: 4.1, 19\]。 |
|  | **在线预订与创建** | POST /api/v1/bookings | 提交预订申请，系统启动“Hold-then-Confirm”两阶段状态锁定机制20。 |
|  | **个人订单中心** | GET /api/v1/bookings/my POST /api/v1/bookings/{id}/cancel | 支持订单状态实时追溯。执行取消操作时需严格验证订单所属权 \[cite: 4.1\]。 |
| **面向管理员** \[cite: 4.2\] | **客房与房型配置** | POST /api/v1/admin/rooms PUT /api/v1/admin/room-types | 管理员可对特定客房执行“上架/下架/清洁中”状态变更，并定义房型基准房价 \[cite: 4.2\]。 |
|  | **订单综合控制** | GET /api/v1/admin/bookings POST /api/v1/admin/bookings/{id}/confirm | 审核待付款订单，办理住店登记（Check-in）与退房结算（Check-out） \[cite: 4.2\]。 |
|  | **账户生命周期管理** | POST /api/v1/admin/users/{id}/disable | 审计系统注册用户，可根据风控策略禁用恶意刷单的会员账号 \[cite: 4.2\]。 |
| **面向 AI 智能体** \[cite: 4.3\] | **get\_available\_rooms** | GET /api/v1/rooms/search (自动映射) | 供 AI 探知实时房态库存，通过自然语言返回最优匹配方案 \[cite: 4.3\]。 |
|  | **create\_booking** | POST /api/v1/bookings (自动映射) | AI 代理用户创建临时预订，后台需在锁定数据库资源的同时开始倒计时 \[cite: 4.3, 60\]。 |
|  | **get\_booking** | GET /api/v1/bookings/{id} (自动映射) | 实时追踪并向用户反馈当前的预订进展或退款审核进度 \[cite: 4.3\]。 |
|  | **cancel\_booking** | POST /api/v1/bookings/{id}/cancel (自动映射) | 通过自然语言对话驱动，执行无感化的退订与支付回滚流程 \[cite: 4.3, 60\]。 |

### **3.1 预订生命周期的“Hold-then-Confirm”两阶段锁定机制**

在酒店业务场景中，“防止超卖”与“保障支付体验”是一对核心矛盾20。如果采用在用户点击预订时即直接创建 permanent（永久）订单并扣减库存，若用户未支付，将导致大量真实库存被恶意锁死20；而如果采用支付完成后再扣减库存的策略，则由于支付和回调存在时间差，在极高并发下必然会出现“多名用户同时支付成功，但房间仅剩一间”的灾难性超卖情况33。  
为化解这一痛点，本系统引入“Hold-then-Confirm”两阶段预订状态机（如图 3-1 所示）20：

                    用户发起预订  
                         │  
                         ▼  
        ┌──────────────────────────────────┐  
        │       第一阶段：创建临时 Hold      │  
        │ \- 执行 select\_for\_update 悲观锁 \[cite: 3, 35\]  
        │ \- 检查目标客房连续日期状态均可用 \[cite: 20\]  
        │ \- 锁定房态为 'held' (软锁)  
        │ \- 设定过期时间 TTL (如 15分钟)  
        └────────────────┬─────────────────┘  
                         │  
                         ├─────────────────────────────────────────┐  
                         ▼ (15分钟内成功支付)                        ▼ (超时未支付 / 用户取消)  
        ┌──────────────────────────────────┐        ┌──────────────────────────────────┐  
        │      第二阶段：转为 Permanent      │        │          自动释放解锁机制          │  
        │ \- 接收支付网关回调成功信号        │        │ \- 异步 Celery 任务 / 定时任务触发   │  
        │ \- 更新房态状态为 'booked' (硬锁)   │        │ \- 恢复房态记录为 'available'     │  
        │ \- 订单状态流转为 'confirmed'      │        │ \- 释放悲观锁，退回公共库存        │  
        └──────────────────────────────────┘        └──────────────────────────────────┘

该状态机极好地平衡了并发一致性与应用层可用性，确保系统在面临极高并发流量时依然表现得极其稳健20。

## **四、 数据库物理 Schema 与索引设计原理**

在每日客房房态库存模型（Explicit Daily Inventory）下，系统需要对每一间具体客房的每一天占用状态进行持久化存储33。这种设计能够原生支持精确到具体某一天的客房差异化定价，同时也带来了庞大的表数据规模（![][image1] 行 / 万间房 / 年）34。因此，极佳的物理 Schema 和索引设计是保障查询响应时间低于 100ms 的关键6。

### **4.1 物理数据库 E-R schema 完整代码**

SQL  
\-- 1\. 用户实体表 (存储用户核心凭证及系统角色) \[cite: 五\]  
CREATE TABLE \`users\` (  
    \`id\` INT AUTO\_INCREMENT COMMENT '用户唯一物理主键',  
    \`username\` VARCHAR(64) NOT NULL UNIQUE COMMENT '用户登录账户',  
    \`password\_hash\` VARCHAR(255) NOT NULL COMMENT ' Argon2id 密码哈希值',  
    \`role\` ENUM('customer', 'admin') NOT NULL DEFAULT 'customer' COMMENT '系统角色：customer(客户), admin(管理员)',  
    \`created\_at\` TIMESTAMP DEFAULT CURRENT\_TIMESTAMP COMMENT '账户创建时间',  
    PRIMARY KEY (\`id\`),  
    INDEX \`idx\_username\` (\`username\`) COMMENT '加速登录凭证检索及唯一性校验'  
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4\_bin COMMENT='用户基本信息及鉴权表';

\-- 2\. 客房类型表 (定义物理房型的静态属性) \[cite: 五\]  
CREATE TABLE \`room\_types\` (  
    \`id\` INT AUTO\_INCREMENT COMMENT '房型主键',  
    \`name\` VARCHAR(64) NOT NULL COMMENT '房型名称，如：豪华海景大床房',  
    \`base\_price\` DECIMAL(10, 2\) NOT NULL COMMENT '该房型的基准门市价',  
    \`capacity\` TINYINT NOT NULL DEFAULT 2 COMMENT '最大可容纳住客人数',  
    \`total\_rooms\` INT NOT NULL DEFAULT 0 COMMENT '该房型下的总客房实体数',  
    PRIMARY KEY (\`id\`)  
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='房型静态属性表';

\-- 3\. 客房实体表 (映射物理世界中的具体房间) \[cite: 五\]  
CREATE TABLE \`rooms\` (  
    \`id\` INT AUTO\_INCREMENT COMMENT '房间主键',  
    \`room\_number\` VARCHAR(16) NOT NULL UNIQUE COMMENT '房间物理门牌号，如：8012',  
    \`room\_type\_id\` INT NOT NULL COMMENT '所属房型 ID',  
    \`status\` ENUM('active', 'inactive', 'maintenance') NOT NULL DEFAULT 'active' COMMENT '物理状态：active(可用), inactive(下架), maintenance(维护中)',  
    PRIMARY KEY (\`id\`),  
    CONSTRAINT \`fk\_rooms\_room\_type\` FOREIGN KEY (\`room\_type\_id\`) REFERENCES \`room\_types\` (\`id\`) ON DELETE RESTRICT,  
    INDEX \`idx\_room\_type\` (\`room\_type\_id\`) COMMENT '加速基于房型的关联筛选与聚合查询'  
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='具体客房实体表';

\-- 4\. 每日客房状态表 (房态的核心载体，也是并发锁定发生的核心目标)  
CREATE TABLE \`daily\_room\_inventories\` (  
    \`room\_id\` INT NOT NULL COMMENT '客房实体 ID',  
    \`date\` DATE NOT NULL COMMENT '具体日期',  
    \`status\` ENUM('available', 'held', 'booked', 'maintenance') NOT NULL DEFAULT 'available' COMMENT '当日房态：available(可预订), held(临时锁定), booked(已确认预订), maintenance(当日维护中)',  
    \`held\_until\` TIMESTAMP NULL DEFAULT NULL COMMENT '软锁定过期截至时间戳，用于 Hold 两阶段的软过期释放',  
    \`booking\_id\` INT NULL DEFAULT NULL COMMENT '当前锁定该房态的订单 ID',  
    PRIMARY KEY (\`room\_id\`, \`date\`), \-- 物理联合主键，确保（客房-日期）一维坐标的唯一性  
    INDEX \`idx\_date\_status\` (\`date\`, \`status\`) COMMENT '加速特定入住退房日期区间的空闲房间搜索',  
    CONSTRAINT \`fk\_dri\_room\` FOREIGN KEY (\`room\_id\`) REFERENCES \`rooms\` (\`id\`) ON DELETE CASCADE  
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日客房房态库存表';

\-- 5\. 订单预订表 (Booking 实体记录，描述合同与财务信息) \[cite: 五\]  
CREATE TABLE \`bookings\` (  
    \`id\` INT AUTO\_INCREMENT COMMENT '订单唯一物理主键',  
    \`user\_id\` INT NOT NULL COMMENT '预订发起人 ID',  
    \`room\_id\` INT NOT NULL COMMENT '所选客房实体 ID',  
    \`check\_in\` DATE NOT NULL COMMENT '入住日期',  
    \`check\_out\` DATE NOT NULL COMMENT '退房日期',  
    \`total\_price\` DECIMAL(10, 2\) NOT NULL COMMENT '订单成交总价',  
    \`status\` ENUM('pending', 'confirmed', 'checked\_in', 'checked\_out', 'cancelled') NOT NULL DEFAULT 'pending' COMMENT '订单状态',  
    \`created\_at\` TIMESTAMP DEFAULT CURRENT\_TIMESTAMP COMMENT '订单创建时间',  
    PRIMARY KEY (\`id\`),  
    CONSTRAINT \`fk\_bookings\_user\` FOREIGN KEY (\`user\_id\`) REFERENCES \`users\` (\`id\`) ON DELETE RESTRICT,  
    CONSTRAINT \`fk\_bookings\_room\` FOREIGN KEY (\`room\_id\`) REFERENCES \`rooms\` (\`id\`) ON DELETE RESTRICT,  
    INDEX \`idx\_user\_id\` (\`user\_id\`) COMMENT '加速用户在个人中心查询历史订单的效率 \[cite: 4.1\]',  
    \-- 复合索引设计：辅助在没有 daily 记录时的后备冲突检测与审计查询 \[cite: 五\]  
    INDEX \`idx\_room\_dates\_status\` (\`room\_id\`, \`status\`, \`check\_in\`, \`check\_out\`) COMMENT '核心区间重叠检索复合索引'  
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单主表';

### **4.2 复合索引排序原理与 Sargability 优化机制**

在关系型数据库查询中，Sargability（阶段可搜索性）是指查询中的过滤谓词能够高效利用 B-Tree 索引的有序性进行快速 seek 检索，而不是退化为全表扫描或全索引扫描6。  
在 bookings 表上，当我们需要判定某个房间在特定入住退房区间内是否已被占用时，典型的 SQL 查询如下：

SQL  
SELECT id FROM bookings   
WHERE room\_id \= 42   
  AND status IN ('pending', 'confirmed')  
  AND check\_in \< '2026-10-08'   
  AND check\_out \> '2026-10-01';

若针对该查询建立了复合索引，则索引中字段的先后物理顺序将直接决定查询的吞吐量6。为了验证索引设计的科学性，我们对比了两种不同的复合索引字段顺序在 InnoDB 底层 B-Tree 索引检索时的执行机制：

### **表 4-1：两种复合索引设计在 MySQL 底层的检索效率对比**

| 复合索引设计方案 | InnoDB B-Tree 物理检索路径与原理 | 核心优势与性能瓶颈 | 查询阶段搜索性评级 |
| :---- | :---- | :---- | :---- |
| **方案 A：** (check\_in, check\_out, room\_id, status) | 1\. 数据库引擎首先在 B-Tree 索引的最左侧，对范围谓词 check\_in \< '2026-10-08' 执行范围扫描（Range Scan）7。 2\. **由于最左列发生了范围操作，B-Tree 索引的有序性在当前分叉后断开**6。 3\. 引擎无法利用索引对 check\_out、room\_id 和 status 进行 ![][image2] 的精确二分定位，被迫在索引叶子节点的后续范围段内进行逐行线性遍历与扫描6。 | **瓶颈：** 当系统历史订单库极其庞大，且大量订单均落在目标 check\_in 之前时，该索引将引发极大的索引扫描 IO 开销7。 | **不具备充分 Sargability (Low)** \[cite: 6\] |
| **方案 B（本方案采用）：** (room\_id, status, check\_in, check\_out) \[cite: 五\] | 1\. 数据库引擎首选在最左侧对 room\_id \= 42 执行 ![][image2] 级别的精确等值Seek7。 2\. 接着对 status 字段在等值区间内进行快速过滤（等值匹配继续保留索引的最右侧有序性）36。 3\. 在定位到该房间、该生效订单状态的具体叶子节点局部段后，最后在第三位字段 check\_in 上应用区间边界范围检索36。 | **优势：** 最大化利用了等值前缀过滤，利用极小的局部子集定位替代了全局的范围扫，并在索引节点内部结合索引下推（ICP）机制完成 check\_out 判定，消除了回表开销37。 | **强 Sargability (High)** \[cite: 6\] |

本方案设计的复合索引 (room\_id, status, check\_in, check\_out) 遵循了“**等值字段在前，范围字段在后，最左前缀严格匹配**”的最高工程规范6，将高频重复预订查询的 CPU 负担降到了最低。

## **五、 异步并发控制、悲观锁与 RBAC 安全设计**

酒店客房具有极其严格的“排他性”（同一天同一间房只能由一人占有）20。因此在高并发抢购周期中，必须借助精密的事务与锁定策略确保数据的绝对一致，同时维持高性能异步 worker 的顺畅运转2。

### **5.1 日期冲突检测的 Allen 区间重叠数学证明**

在关系型数据库中，任何预订订单的日期占用区间都可以表示为一组前闭后开的连续实数集合31。令用户请求预订的区间为 ![][image3]，已有成功订单的占用区间为 ![][image4]31。 在数学上，两个区间相交的充要条件可以推导证明如下：  
**重叠定理证明：**  
两区间没有交集（不相交），其充要条件是其中一个区间完全在另一个区间的左侧或右侧：  
![][image5]  
\[cite: 31\]  
对上述无交集命题取逻辑非（Not），根据德·摩根定律（De Morgan's laws），即可得到两区间发生重叠相交的充要条件：  
![][image6]  
![][image7]  
\[cite: 31\]  
**结论：** 当且仅当 **请求退房日期大于已有入住日期**，且 **请求入住日期小于已有退房日期** 时，该日期段已被抢占，不允许创建新预订 \[cite: 6.1, 24\]。在系统中，该判定作为 Service 层的最后一道逻辑防线，配合底层的悲观锁共同协作3。

### **5.2 悲观锁（SELECT FOR UPDATE NOWAIT）防雪崩机制**

当万名用户同时抢订同一间特惠客房时，传统的 SELECT ... FOR UPDATE 会使抢不到锁的 9999 个请求线程在数据库连接中挂起等待，直至事务 A 释放锁，从而在 Web 服务器层引发排队雪崩效应3。 MySQL 8.0 引入的 NOWAIT 从根本上优化了这一现象4：

* **悲观非阻塞锁**：事务通过 SELECT ... FOR UPDATE NOWAIT 尝试锁定 daily\_room\_inventories 上的相关行3。若目标行已被其他事务加锁，该语句不会进入阻塞等待，而是立即抛出操作失败异常（MySQL Error Code: 3572）3。  
* **非阻塞快速失败**：FastAPI 捕获该数据库异常后，立即可将其翻译为友好提示返回，完全释放了异步 worker，避免任何因锁等待产生的协程积压与资源空转3。

以下代码展示了在 SQLAlchemy 2.0 异步上下文（AsyncSession）中，如何完美实现这一强一致性并发扣减逻辑8：

Python  
import logging  
from datetime import date  
from sqlalchemy import select, and\_  
from sqlalchemy.ext.asyncio import AsyncSession  
from sqlalchemy.exc import OperationalError  
from fastapi import HTTPException, status

\# 假设已从物理 Schema 导入 DailyRoomInventory 模型定义  
logger \= logging.getLogger("hotel.pms")

async def execute\_room\_booking\_transaction(  
    db: AsyncSession,  
    room\_id: int,  
    check\_in: date,  
    check\_out: date,  
    booking\_id: int  
) \-\> bool:  
    """  
    基于 SQLAlchemy 2.0 Async 驱动实现酒店房态的非阻塞悲观锁扣减  
    """  
    try:  
        \# 1\. 显式开启原子事务块 \[cite: 2\]  
        async with db.begin():  
            \# 2\. 构造具有 NOWAIT 标志的锁定查询  
            \# 该查询将锁定此客房在预订日期区间内的每一行 DailyRecord  
            stmt \= (  
                select(DailyRoomInventory)  
                .where(  
                    and\_(  
                        DailyRoomInventory.room\_id \== room\_id,  
                        DailyRoomInventory.date \>= check\_in,  
                        DailyRoomInventory.date \< check\_out \# 前闭后开  
                    )  
                )  
                .with\_for\_update(nowait=True) \# 核心：追加 MySQL 8.0 NOWAIT 机制  
            )  
              
            result \= await db.execute(stmt)  
            daily\_records \= result.scalars().all()  
              
            \# 3\. 校验获取的天数是否完整（检查库存完整性）  
            required\_days \= (check\_out \- check\_in).days  
            if len(daily\_records) \!= required\_days:  
                raise HTTPException(  
                    status\_code=status.HTTP\_400\_BAD\_REQUEST,  
                    detail="预订日期区间内部分房态未开放，请联系前台"  
                )  
                  
            \# 4\. 业务逻辑状态幂等检测（在锁保护下安全检查状态） \[cite: 20\]  
            for record in daily\_records:  
                if record.status \!= "available":  
                    raise HTTPException(  
                        status\_code=status.HTTP\_409\_CONFLICT,  
                        detail=f"抱歉，房间在 {record.date} 已被占用，请更换房源"  
                    )  
              
            \# 5\. 更新房态为临时锁定（软 Hold）状态  
            for record in daily\_records:  
                record.status \= "held"  
                record.booking\_id \= booking\_id  
                \# 预设在 daily\_room\_inventories 表上：held\_until 将在 Hold 定时任务中被核销  
                db.add(record) \# 记录标记为 Pending Update  
              
            \# 6\. 事务自动提交并安全释放 InnoDB 底层的排他锁（Exclusive Lock） \[cite: 3, 39\]  
            return True

    except OperationalError as e:  
        \# 捕获由于锁争抢导致的 NOWAIT 失败异常 (Error code 3572\)  
        if "3572" in str(e.orig) or "Lock wait timeout" in str(e.orig):  
            logger.warning(f"Room {room\_id} has locked by other transactions. Quick-Fail triggered.")  
            raise HTTPException(  
                status\_code=status.HTTP\_423\_LOCKED,  
                detail="当前客房正被其他用户疯狂抢购中，请在1分钟后重试"  
            )  
        \# 抛出其他未预期的底层异常 \[cite: 2\]  
        logger.error(f"Operational error: {e}")  
        raise HTTPException(  
            status\_code=status.HTTP\_500\_INTERNAL\_SERVER\_ERROR,  
            detail="系统高并发负载，事务执行异常"  
        )

### **5.3 HttpOnly \+ SameSite Cookie 的鉴权安全体系**

传统的 Token 认证常将 JWT 直接存放在浏览器的 localStorage 中11。这种架构在面对跨站脚本攻击（XSS）时极其脆弱，恶意代码可轻而易举地通过读取 DOM 内存窃取用户凭证11。  
本方案设计了一套由后端强制管理的**安全 HttpOnly Cookie 双令牌认证体系**11：

1. **令牌分离**：用户登录成功后，后端生成短效的 Access Token（15分钟）12 与长效的 Refresh Token（7天）40。  
2. **安全隔离（HttpOnly）**：Access Token 与 Refresh Token 均通过 HTTP 响应头中的 Set-Cookie 发送给浏览器11。Cookie 带有 HttpOnly 标志，**前端 JavaScript 代码完全无权读取或操作该 Cookie**，从根本上隔离了 XSS 窃取凭证的可能性11。  
3. **防止监听（Secure & SameSite）**：强制设置 Secure 属性确保 Cookie 仅在加密的 HTTPS 链路中流转12；设置 SameSite=Strict（或 Lax），告知浏览器仅在同源请求中携带此 Cookie，有效抵御跨站请求伪造（CSRF）攻击11。  
4. **无感刷新流程**：当 Access Token 过期时，前端（或 AI Agent 终端）无感向服务端 /refresh 发起静默请求，由后端自动验证 HttpOnly 的 Refresh Token 并重新颁发全新的 Access Cookie 覆盖，保障极佳的用户体验11。

以下是基于 FastAPI 构建的 Secure Cookie 凭证提取器与 Swagger 支持方案12：

Python  
from fastapi import Request, HTTPException, status  
from fastapi.security import OAuth2  
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel

class OAuth2PasswordBearerWithCookie(OAuth2):  
    """  
    重写 FastAPI 原生的 OAuth2 流程支持，使其能够直接从安全 Cookie 中提取 Bearer 令牌，  
    以此在保证 HttpOnly 饼干安全性的同时，依然使原生的 OpenAPI (/docs) 调试工具正常可用 \[cite: 43\]。  
    """  
    def \_\_init\_\_(self, tokenUrl: str, scheme\_name: str \= None, scopes: dict \= None, auto\_error: bool \= True):  
        if not scopes:  
            scopes \= {}  
        flows \= OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})  
        super().\_\_init\_\_(flows=flows, scheme\_name=scheme\_name, auto\_error=auto\_error)

    async def \_\_call\_\_(self, request: Request) \-\> str | None:  
        \# 重写获取令牌的方法，优先从 HttpOnly Cookie 中查找名为 "access\_token" 的字段  
        token: str \= request.cookies.get("access\_token")  
          
        if not token:  
            if self.auto\_error:  
                raise HTTPException(  
                    status\_code=status.HTTP\_401\_UNAUTHORIZED,  
                    detail="请求未携带身份 Cookie，请先完成登录"  
                )  
            return None  
        return token

\# 声明凭证验证依赖  
oauth2\_scheme \= OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/auth/login")

### **5.4 基于 FastAPI 依赖注入的参数化 RBAC 角色验证器**

系统在业务鉴权上，不仅需要验证用户的有效身份，还需要根据角色身份（普通顾客 customer 与系统管理员 admin）动态限制敏感接口的访问权限 \[cite: 五, 81\]。 利用 FastAPI 强大的依赖注入机制，我们可以将 RoleChecker 设计为一个带状态的参数化类，通过实现 Python 的 \_\_call\_\_ 幻数方法，使其在运行时自动作为依赖处理器接收系统的 UserPayload1：

Python  
from typing import List, Annotated  
from fastapi import Depends, HTTPException, status  
from jose import jwt, JWTError

\# 预设验证密钥  
SECRET\_KEY \= "SUPER\_SECURE\_HOTEL\_SECRET\_KEY"  
ALGORITHM \= "HS256"

class CurrentUserPayload:  
    """认证通过后的用户信息 DTO"""  
    def \_\_init\_\_(self, user\_id: int, username: str, role: str):  
        self.user\_id \= user\_id  
        self.username \= username  
        self.role \= role

async def get\_current\_user\_from\_jwt(token: Annotated\[str, Depends(oauth2\_scheme)\]) \-\> CurrentUserPayload:  
    """  
    核心依赖注入：解密 JWT 令牌，提取用户角色 \[cite: 30\]  
    """  
    try:  
        payload \= jwt.decode(token, SECRET\_KEY, algorithms=\[ALGORITHM\])  
        user\_id: int \= payload.get("sub")  
        username: str \= payload.get("username")  
        role: str \= payload.get("role")  
          
        if user\_id is None or role is None:  
            raise HTTPException(  
                status\_code=status.HTTP\_401\_UNAUTHORIZED,  
                detail="登录凭证解析失败，非合法的荷载载体"  
            )  
        return CurrentUserPayload(user\_id=user\_id, username=username, role=role)  
    except JWTError:  
        raise HTTPException(  
            status\_code=status.HTTP\_401\_UNAUTHORIZED,  
            detail="登录凭证签名损坏或已过期"  
        )

class RoleChecker:  
    """  
    参数化 RBAC 角色验证器，用于对不同端点动态设定访问角色白名单 \[cite: 30\]  
    """  
    def \_\_init\_\_(self, allowed\_roles: List\[str\]):  
        \# 初始化白名单角色，如 \["admin"\] 或 \["customer", "admin"\]  
        self.allowed\_roles \= allowed\_roles

    def \_\_call\_\_(self, current\_user: Annotated\[CurrentUserPayload, Depends(get\_current\_user\_from\_jwt)\]) \-\> CurrentUserPayload:  
        """  
        验证逻辑：不符合白名单的访问直接抛出 403 异常  
        """  
        if current\_user.role not in self.allowed\_roles:  
            raise HTTPException(  
                status\_code=status.HTTP\_403\_FORBIDDEN,  
                detail="抱歉，您的账号角色无权执行当前操作"  
            )  
        return current\_user

**应用案例：** 在需要拦截非管理员操作的路由中，直接通过 dependencies=\[Depends(RoleChecker(\['admin'\]))\] 进行守护，确保了鉴权边界的极其干净和统一30。

## **六、 MCP 智能接口与 AI 原生交互设计**

模型上下文协议（Model Context Protocol）是由 Anthropic 组织在 2024 年底主导发布的新型 AI 交互协议，其本质是打通 LLM 智能体（Agent）与其外部工具、数据资源之间的标准化 USB-C 接口23。

### **6.1 FastAPI-MCP 转换逻辑与运行原理**

传统的 RESTful 接口包含极其繁杂的请求体、头信息以及协议解析要求，LLM 很难在没有额外处理的情况下直接进行鲁棒的多步调用21。 本系统利用 **FastAPI-MCP** 桥接架构完美解决了这一障碍13：

1. **自动 Schema 注册**：在系统初始化时，FastAPI-MCP 会利用反射机制提取 FastAPI 的 Pydantic 模型（如房态查询入参、创建订单入参）13。  
2. **生成 JSON-RPC 桥**：将核心 RESTful Endpoint 转换为等价的工具说明书（Tools Definition），并统一种植在后端应用层专设的 /mcp/ 路径下，面向 AI 提供标准化的基于 TCP stdio、Server-Sent Events（SSE）或 HTTP 的 JSON-RPC 通信层13。  
3. **LLM 友好性**：AI Agent 可通过自然语言（例如：“帮我看看下周一 101 号房还空着吗，如果还空着请直接帮我锁定”）通过此通道向系统下达命令 \[cite: 4.3, 1.2\]。FastAPI-MCP 接收到命令后，无须发起昂贵的网络 HTTP 回环，直接将入参映射并传递给 FastAPI 的内存 ASGI 接口中，无缝完成房态校验与软锁定逻辑，最终将系统结果包装为大模型可读的自然语言响应体返还给用户13。

### **6.2 客户端连接配置样例**

为了让开发人员或用户在 Cursor（IDE 内嵌 Agent 客户端）或 Claude Desktop 中一键唤起、探知本系统的 MCP 工具，客户端只需在其全局 MCP 服务配置文件中添加一个简单的 SSE 连接声明即可28：

JSON  
{  
  "mcpServers": {  
    "hotel-booking-mcp": {  
      "url": "https://hotel.demo.com/mcp",  
      "env": {  
        "PYTHONPATH": "/app/backend"  
      }  
    }  
  }  
}

添加该配置并成功激活后，AI Agent 将自动列出暴露出的 get\_available\_rooms 与 create\_booking 等接口，并能在人机协同对话中无缝地为住客安排行程预订 \[cite: 4.3, 32, 34\]。

## **七、 项目开发计划**

为了确保项目能够在 7 周的研发周期内平稳落地并具备完整的生产演示能力，制定如下详尽的多维开发推进时间表 \[cite: 八\]：

### **表 7-1：系统 7 周敏捷研发推进路线图**

| 研发阶段 | 推进周期 \[cite: 八\] | 后端核心攻坚任务 \[cite: 八\] | 前端核心攻坚任务 \[cite: 八\] | 核心可交付物与里程碑节点 \[cite: 八\] |
| :---- | :---- | :---- | :---- | :---- |
| **第一阶段** | 第 1 周 \[cite: 八\] | 1\. 细化数据库 E-R 逻辑； 2\. 初始化 FastAPI 开发基线与 SQLAlchemy 2.0 异步引擎 \[cite: 1.2, 54\]； 3\. 架构 REST API 基础设计与 Swagger 端点规划 \[cite: 1.2, 29\]。 | 1\. 利用 Vite 脚手架完成 Vue 3 项目基线搭建 \[cite: 1.2\]； 2\. 规划 Vue-Router 的路由守卫、全局状态机 Pinia 架构； 3\. 安装并导入 Element Plus 全局样式库 \[cite: 1.2\]。 | 1\. 数据库 E-R 关系图及 SQL DDL 脚本； 2\. 合规的 Swagger OpenAPI 交互式设计文档 \[cite: 1.2, 29\]； 3\. 前后端项目脚手架代码。 |
| **第二阶段** | 第 2-3 周 \[cite: 八\] | 1\. 实现基于 Argon2id 的用户密码哈希与注册12； 2\. 部署 HttpOnly \+ SameSite JWT Cookie 颁发机制11； 3\. 实现每日房态库存的核心扣减、Allen 冲突检测及悲观非阻塞锁3； 4\. 集成并挂载 FastAPI-MCP 控制器13。 | 1\. 构建 Web 客户端的用户登录与注册交互表单； 2\. 开发客房及房态的多功能全局模糊查询面板 \[cite: 4.1\]； 3\. 实现“客房详情-日期时间选择器-预订表单”核心链路； 4\. 完成前后端 Axios 拦截器与 Cookie 的自动透传调试。 | 1\. 通过单元测试的后端预订与鉴权核心服务代码； 2\. 可通过 Mock 调试的前端核心页面原型； 3\. 能够成功被 MCP Inspector 本地成功探知的 MCP 工具集48。 |
| **第三阶段** | 第 4-5 周 \[cite: 八\] | 1\. 开发管理员专属权限接口（房型上下架、全局订单跟踪） \[cite: 4.2\]； 2\. 编写 Hold-then-Confirm 状态软锁定时自动核销的定时任务组件33； 3\. 编写模拟支付回调网关。 | 1\. 开发管理员后台工作台看板（基于 Element Plus Card 组件展现） \[cite: 1.2, 4.2\]； 2\. 实现管理员订单列表查询、手工入住/退房控制表单 \[cite: 4.2\]； 3\. 接入 MCP Web 对话控制面板（提供人类用户与 AI Agent 对话的 GUI 界面）。 | 1\. 覆盖全链路的系统业务后端完整代码； 2\. 实现管理员与普通用户端的前端系统应用； 3\. 演示“AI 自动解析指令并成功扣减库存”的系统原型。 |
| **第四阶段** | 第 6 周 \[cite: 八\] | 1\. 采用 Python 压测框架 Locust 对预订扣库存悲观锁事务实施并发压力测试3； 2\. 对 MySQL 执行 EXPLAIN 分析，验证复合索引的 Sargability Sargable 命中6； 3\. 消除可能由于悲观锁使用不当产生的交叉死锁风险3。 | 1\. 优化首屏加载性能与静态分包资源混淆； 2\. 执行跨浏览器兼容性调试； 3\. 联合 Cursor/Claude Code 进行端到端（E2E）的真实调用路径鲁棒性测试 \[cite: 八, 88\]。 | 1\. 系统并发压力测试分析报告 \[cite: 八\]； 2\. MySQL 慢查询诊断与优化日志； 3\. 最终前后端联调测试通过的上线代码分支。 |
| **第五阶段** | 第 7 周 \[cite: 八\] | 1\. 编写生产级 Dockerfile 镜像构建脚本； 2\. 编写 Docker-Compose 容器化一键编排脚本 \[cite: 1.2\]； 3\. 部署并深度调优生产级 Nginx 反向代理配置，优化长连接16。 | 1\. 在生产容器环境中完成静态资源的统一构建部署； 2\. 整合最终的项目技术手册。 | 1\. 完整的 Docker 镜像及一键部署运行包 \[cite: 八\]； 2\. 完整的项目技术白皮书、用户部署指南 \[cite: 八\]； 3\. 满足学校或行业标准的毕业论文初稿 \[cite: 八\]。 |

## **八、 部署架构与高性能 Nginx 反向代理配置**

在生产环境部署时，系统采用容器化部署（Docker）结合 Nginx 流量网关的经典拓扑 \[cite: 1.2, 三\]。特别需要注意的是，由于 MCP 模块（不论是基于 HTTP 还是标准的 SSE 传输协议）涉及长连接（Long-lived Connections）、AI 流式输出以及高强度的双向事件传输，Nginx 的默认配置往往会成为阻碍系统响应性能的严重瓶颈16。

### **8.1 代理缓冲（Proxy Buffering）的深层瓶颈分析**

在 Nginx 的默认代理模式下，proxy\_buffering 被配置为 on16。

* **缓冲阻断原理**：当后端 FastAPI 异步服务以极快的速度发送 SSE 消息或大模型的 Token 数据时，Nginx 会尝试将响应体完整读取并缓存到自己的内部内存或磁盘临时文件中16。在没有积压到指定的缓存块大小之前，Nginx 将拒绝对客户端推送这些微小的增量字节17。这导致前端或 AI 智能体发生严重的消息延迟积压，客户端长时间收不到事件，并在超时后被迫引发连接重连中断17。  
* **解决方案**：针对 MCP 传输路由，必须在 Nginx 中显式设置 **proxy\_buffering off;** 和 **proxy\_cache off;**16。这一指令让 Nginx 扮演完全的透明“管道”角色，后端每产生一个字节的数据（如大模型的一句话、房态变更的一帧状态推送），无需任何排队等待，立刻穿透并直达客户端16。

### **8.2 高性能生产级 Nginx 配置范式**

以下提供一份经过深度性能调优的高性能 Nginx 服务器配置文件（生产环境参考模板）：

Nginx  
\# 1\. 定义高性能后台负载均衡集群，开启 keepalive 连接池复用  
upstream fastapi\_app\_servers {  
    server 127.0.0.1:8000;  
    keepalive 64; \# 保持与 FastAPI 的 64 个空闲 TCP 物理连接，避免频繁三次握手 \[cite: 16\]  
}

server {  
    listen 80;  
    server\_name pms.demo.com;  
      
    \# 强制将普通不安全 HTTP 流量全量重定向至 HTTPS 安全隧道  
    return 301 https://$host$request\_uri;  
}

server {  
    listen 443 ssl http2; \# 启用 TLS 卸载与 HTTP/2 (普通页面采用 HTTP/2，MCP 采用 1.1 隔离) \[cite: 49\]  
    server\_name pms.demo.com;

    \# SSL 物理配置调优  
    ssl\_certificate /etc/nginx/certs/pms.crt;  
    ssl\_certificate\_key /etc/nginx/certs/pms.key;  
    ssl\_protocols TLSv1.2 TLSv1.3;  
    ssl\_ciphers HIGH:\!aNULL:\!MD5;  
    ssl\_prefer\_server\_ciphers on;

    \# \-------------------------------------------------------------  
    \# A. Vue 3 前端静态资源快速托管服务 \[cite: 1.2\]  
    \# \-------------------------------------------------------------  
    location / {  
        root /usr/share/nginx/html/dist;  
        index index.html;  
        try\_files $uri $uri/ /index.html; \# 支持 HTML5 History 路由模式下的子页面刷新

        \# 针对静态资源文件（CSS, JS, 字体, 图片）开启长期浏览器强缓存  
        location \~\* \\.(js|css|png|jpg|jpeg|gif|ico|woff2|svg)$ {  
            expires 30d;  
            add\_header Cache-Control "public, no-transform";  
        }  
    }

    \# \-------------------------------------------------------------  
    \# B. 代理普通 RESTful API 接口 (人类 Web 前端交互) \[cite: 三\]  
    \# \-------------------------------------------------------------  
    location /api/ {  
        proxy\_pass http://fastapi\_app\_servers;  
          
        \# 强制启用 HTTP/1.1 支持 keep-alive \[cite: 16, 18\]  
        proxy\_http\_version 1.1;  
        proxy\_set\_header Connection "";  
          
        \# 请求透传标头，保证后端可以准确追踪客户端真实 IP 与协议 \[cite: 16, 18\]  
        proxy\_set\_header Host $host;  
        proxy\_set\_header X-Real-IP $remote\_addr;  
        proxy\_set\_header X-Forwarded-For $proxy\_add\_x\_forwarded\_for;  
        proxy\_set\_header X-Forwarded-Proto $scheme;  
          
        \# 正常业务接口，保持短的超时限制，防止僵死连接挤占资源 \[cite: 18\]  
        proxy\_read\_timeout 60s;  
        proxy\_send\_timeout 60s;  
    }

    \# \-------------------------------------------------------------  
    \# C. 专项代理 AI Agent 调用的 MCP 长连接与 SSE 通信链路 \[cite: 三, 28\]  
    \# \-------------------------------------------------------------  
    location \~ ^/(mcp|sse)/ {  
        proxy\_pass http://fastapi\_app\_servers;

        \# 【极其关键】显式关闭 Nginx 的反向代理缓存与缓冲机制  
        \# 使得任何流式的 Token、状态帧和进度条变更可以立时无延迟推送给 AI  
        proxy\_buffering off;  
        proxy\_cache off;  
          
        \# 禁用 Nginx 对该通道的 gzip 压缩。压缩算法在构建压缩树时会导致数据排队，破坏 SSE \[cite: 16\]  
        gzip off;

        \# 【传输协议调优】  
        \# 强制指定 HTTP/1.1 协议。由于 SSE 采用长连接，需显式将 Connection 标头清空  
        \# 从而强行覆盖客户端传来的 'close' 指令，保持链路 keepalive 活性 \[cite: 16, 18, 49\]  
        proxy\_http\_version 1.1;  
        proxy\_set\_header Connection "";  
          
        \# 允许双向分块传输编码（Chunked Transfer Encoding）  
        chunked\_transfer\_encoding on;

        \# 大模型会话调用时间可能很长，将超时时间扩展到 24 小时（86400秒），防止频繁异常中断  
        proxy\_read\_timeout 86400s;  
        proxy\_send\_timeout 86400s;

        \# 满足特定 MCP 客户端的媒体类型接收协议规范 \[cite: 49\]  
        proxy\_set\_header Accept "application/json, text/event-stream";  
          
        \# 头部属性透传 \[cite: 16\]  
        proxy\_set\_header Host $host;  
        proxy\_set\_header X-Real-IP $remote\_addr;  
        proxy\_set\_header X-Forwarded-For $proxy\_add\_x\_forwarded\_for;  
        proxy\_set\_header X-Forwarded-Proto $scheme;  
    }  
}

## **九、 预期成果与创新点**

### **9.1 预期核心交付物**

* **代码及运行实体**：一套前后端完全解耦、容器化一键编排、具备生产级高并发抗压能力的酒店客房预订 PMS 完整系统代码 \[cite: 1.2, 九\]。  
* **标准化文档**：一份针对人类开发者的标准 Swagger OpenAPI 交互规范，以及一份针对 AI 智能体零配置自动发现的 MCP 智能接口定义指南 \[cite: 1.2, 九\]。  
* **部署运行包**：完全由 Dockerfile 构建的轻量化镜像包，在任何主流 Linux 物理机上输入 docker-compose up \-d 即可在秒级拉起整个系统 \[cite: 1.2\]。

### **9.2 系统核心创新维度**

1. **双模发布体系（Dual-Mode Publishing）**：  
   同一套 Service 层的核心逻辑，同时且一致地发布为传统的 RESTful 接口与 AI 友好的 MCP 工具 \[cite: 8, 九\]。这不仅满足了传统人类 Web GUI 的高性能交互，更顺应了未来大语言模型 Agent 自动调用服务（CaaS）的人机协同演进潮流 \[cite: 1.1, 九\]。  
2. **非阻塞防雪崩高并发控制（Non-blocking Pessimistic Lock）**： 在 SQLAlchemy 异步框架下，完美编排了 MySQL 8.0 NOWAIT 锁机制3。它摒弃了由于锁争抢导致 ASGI worker 协程大面积瘫痪等待的传统弊端3，在业务底层以极致的物理强一致性防止了房态超卖，实现了高频抢购下的“快速失败”防雪崩设计3。  
3. **极致的 B-Tree 索引 Sargability 调优**： 打破了在预订日期上盲目建立普通单列索引的传统误区，通过科学的复合索引字段排序机制，实现了在高达百万行数据集规模下，重叠日期范围检测的微秒级闪电 Seek 检索6。  
4. **HttpOnly \+ SameSite Cookie 与参数化 RBAC 安全防护**： 构建了严格的 Cookie JWT 双令牌无感刷新流，将敏感的 Access 凭证在 JavaScript 作用域中隔离并防止 XSS 窃取11；并在 FastAPI 层构建了高内聚的、复用性极强的参数化 RoleChecker 类，优雅实现了细粒度的 RBAC 拦截1。

#### **引用的著作**

1. Advanced Dependencies \- FastAPI, [https://fastapi.tiangolo.com/advanced/advanced-dependencies/](https://fastapi.tiangolo.com/advanced/advanced-dependencies/)  
2. Mastering ACID Transactions in Relational Databases with Python, [https://python.plainenglish.io/mastering-acid-transactions-in-relational-databases-with-python-6192aaca30a7](https://python.plainenglish.io/mastering-acid-transactions-in-relational-databases-with-python-6192aaca30a7)  
3. SQLAlchemy Database Locks Using FastAPI: A Simple Guide | by Mojtaba (MJ) Michael, [https://mjmichael.medium.com/sqlalchemy-database-locks-using-fastapi-a-simple-guide-3e7dcd552d87](https://mjmichael.medium.com/sqlalchemy-database-locks-using-fastapi-a-simple-guide-3e7dcd552d87)  
4. Beyond Just Locks: A Guide to Pessimistic and Optimistic Concurrency Control in Python with MySQL \- Hao Kuang, [https://kuangbyte.medium.com/beyond-just-locks-a-guide-to-pessimistic-and-optimistic-concurrency-control-in-python-with-mysql-51cbc2f6fab2](https://kuangbyte.medium.com/beyond-just-locks-a-guide-to-pessimistic-and-optimistic-concurrency-control-in-python-with-mysql-51cbc2f6fab2)  
5. The Ultimate Guide to Relational Databases for Backend Developers \- Dev Genius, [https://blog.devgenius.io/the-ultimate-guide-to-relational-databases-for-backend-developers-42b1efb492b0](https://blog.devgenius.io/the-ultimate-guide-to-relational-databases-for-backend-developers-42b1efb492b0)  
6. How to Optimize Date Range Queries in MySQL \- OneUptime, [https://oneuptime.com/blog/post/2026-03-31-mysql-optimize-date-range-queries/view](https://oneuptime.com/blog/post/2026-03-31-mysql-optimize-date-range-queries/view)  
7. Optimal MySQL index for search query within date ranges \- Stack Overflow, [https://stackoverflow.com/questions/27948039/optimal-mysql-index-for-search-query-within-date-ranges](https://stackoverflow.com/questions/27948039/optimal-mysql-index-for-search-query-within-date-ranges)  
8. SQLAlchemy 2.0 & Async Workflows. Modernizing Python Database… | by nunacode \- Medium, [https://medium.com/python-how-to/sqlalchemy-2-0-async-workflows-494fecffd28f](https://medium.com/python-how-to/sqlalchemy-2-0-async-workflows-494fecffd28f)  
9. FastAPI and async SQLAlchemy 2.0 with pytest done right \- Praciano, [https://praciano.com.br/fastapi-and-async-sqlalchemy-20-with-pytest-done-right.html](https://praciano.com.br/fastapi-and-async-sqlalchemy-20-with-pytest-done-right.html)  
10. Asynchronous Database Sessions in FastAPI with SQLAlchemy \- DEV Community, [https://dev.to/akarshan/asynchronous-database-sessions-in-fastapi-with-sqlalchemy-1o7e](https://dev.to/akarshan/asynchronous-database-sessions-in-fastapi-with-sqlalchemy-1o7e)  
11. JWT in Cookies \- FastAPI JWT Auth, [https://indominusbyte.github.io/fastapi-jwt-auth/usage/jwt-in-cookies/](https://indominusbyte.github.io/fastapi-jwt-auth/usage/jwt-in-cookies/)  
12. Token-Based Authentication with Cookies and JWT Expiration | CodeSignal Learn, [https://codesignal.com/learn/courses/secure-authentication-authorization-in-fastapi/lessons/token-based-authentication-with-cookies-and-jwt-expiration](https://codesignal.com/learn/courses/secure-authentication-authorization-in-fastapi/lessons/token-based-authentication-with-cookies-and-jwt-expiration)  
13. FastAPI-MCP by tadata-org | MCP API Tooling \- Augment Code, [https://www.augmentcode.com/mcp/fastapi-mcp](https://www.augmentcode.com/mcp/fastapi-mcp)  
14. GitHub \- tadata-org/fastapi\_mcp: Expose your FastAPI endpoints as Model Context Protocol (MCP) tools, with Auth\!, [https://github.com/tadata-org/fastapi\_mcp](https://github.com/tadata-org/fastapi_mcp)  
15. NGINX Configuration: Directives, Examples, and 4 Mistakes to Avoid | Solo.io, [https://www.solo.io/topics/nginx/nginx-configuration](https://www.solo.io/topics/nginx/nginx-configuration)  
16. How to Configure Server-Sent Events Through Nginx \- OneUptime, [https://oneuptime.com/blog/post/2025-12-16-server-sent-events-nginx/view](https://oneuptime.com/blog/post/2025-12-16-server-sent-events-nginx/view)  
17. What network configurations may cause responses to be buffered rather than streamed?​ · langgenius dify · Discussion \#25399 \- GitHub, [https://github.com/langgenius/dify/discussions/25399](https://github.com/langgenius/dify/discussions/25399)  
18. HTTP Deployment \- FastMCP, [https://gofastmcp.com/v2/deployment/http](https://gofastmcp.com/v2/deployment/http)  
19. Build an MCP Server with FastAPI \- Python Tutorial \- Fastio, [https://fast.io/resources/mcp-server-fastapi-python/](https://fast.io/resources/mcp-server-fastapi-python/)  
20. Hotel Booking System Design: Search, Inventory & Reservation Flow \- Codelit.io, [https://codelit.io/blog/hotel-booking-system-design](https://codelit.io/blog/hotel-booking-system-design)  
21. Build MCP in Python: FastMCP vs FastAPI-MCP vs Python SDK \- MCP.Directory, [https://mcp.directory/blog/fastmcp-vs-fastapi-mcp-vs-python-sdk-2026](https://mcp.directory/blog/fastmcp-vs-fastapi-mcp-vs-python-sdk-2026)  
22. fastapi-mcp \- PyPI, [https://pypi.org/project/fastapi-mcp/0.2.0/](https://pypi.org/project/fastapi-mcp/0.2.0/)  
23. Model Context Protocol \- GitHub, [https://github.com/modelcontextprotocol](https://github.com/modelcontextprotocol)  
24. PrefectHQ/fastmcp: The fast, Pythonic way to build MCP servers and clients. \- GitHub, [https://github.com/PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp)  
25. The official Python SDK for Model Context Protocol servers and clients \- GitHub, [https://github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)  
26. danilop/mcp-python-sdk: The official Python SDK for Model Context Protocol servers and clients \- GitHub, [https://github.com/danilop/mcp-python-sdk](https://github.com/danilop/mcp-python-sdk)  
27. Mount, Stream, Authenticate FastMCP with FastAPI | by Ekky Armandi | May, 2026 \- Medium, [https://medium.com/@ekkyarmandi/mount-stream-authenticate-fastmcp-with-fastapi-ea2ef6f45b2a](https://medium.com/@ekkyarmandi/mount-stream-authenticate-fastmcp-with-fastapi-ea2ef6f45b2a)  
28. Quickstart \- FastAPI MCP \- Tadata, [https://fastapi-mcp.tadata.com/getting-started/quickstart](https://fastapi-mcp.tadata.com/getting-started/quickstart)  
29. FastAPI Role Base Access Control With JWT \- Stackademic, [https://stackademic.com/blog/fastapi-role-base-access-control-with-jwt-9fa2922a088c](https://stackademic.com/blog/fastapi-role-base-access-control-with-jwt-9fa2922a088c)  
30. SQL Query to Find Overlapping (Conflicting) Date Ranges, [https://salman-w.blogspot.com/2012/06/sql-query-overlapping-date-ranges.html](https://salman-w.blogspot.com/2012/06/sql-query-overlapping-date-ranges.html)  
31. MCP Transport \- FastAPI MCP \- Tadata, [https://fastapi-mcp.tadata.com/advanced/transport](https://fastapi-mcp.tadata.com/advanced/transport)  
32. Design Hotel Booking System: A Step-by-Step Guide, [https://www.systemdesignhandbook.com/guides/design-hotel-booking-system/](https://www.systemdesignhandbook.com/guides/design-hotel-booking-system/)  
33. System Design HLD Example: Hotel Booking System (Airbnb), [https://abstractalgorithms.dev/system-design-hld-hotel-booking-example](https://abstractalgorithms.dev/system-design-hld-hotel-booking-example)  
34. MySQL 9.7 Reference Manual :: 10.2.1.2 Range Optimization, [https://dev.mysql.com/doc/en/range-optimization.html](https://dev.mysql.com/doc/en/range-optimization.html)  
35. MySQL Database: Core Fundamentals & Common Gotchas \- GitHub Gist, [https://gist.github.com/Integralist/51ae85eb6f522a6e8399cacefa385258](https://gist.github.com/Integralist/51ae85eb6f522a6e8399cacefa385258)  
36. FastAPI \+ SQLAlchemy Best Practices \- A Developer Bird Blog, [https://mshaeri.com/blog/fastapi-sqlalchemy-best-practices/](https://mshaeri.com/blog/fastapi-sqlalchemy-best-practices/)  
37. Understanding jwt tokens : r/FastAPI \- Reddit, [https://www.reddit.com/r/FastAPI/comments/1np8b7c/understanding\_jwt\_tokens/](https://www.reddit.com/r/FastAPI/comments/1np8b7c/understanding_jwt_tokens/)  
38. Refreshing Tokens \- Authx, [https://authx.yezz.me/get-started/refresh/](https://authx.yezz.me/get-started/refresh/)  
39. JWT in FastAPI, the Secure Way (Refresh Tokens Explained) | by Jagan Reddy \- Medium, [https://medium.com/@jagan\_reddy/jwt-in-fastapi-the-secure-way-refresh-tokens-explained-f7d2d17b1d17](https://medium.com/@jagan_reddy/jwt-in-fastapi-the-secure-way-refresh-tokens-explained-f7d2d17b1d17)  
40. Cookie based JWT tokens · fastapi fastapi · Discussion \#9142 \- GitHub, [https://github.com/fastapi/fastapi/discussions/9142](https://github.com/fastapi/fastapi/discussions/9142)  
41. How do you handle ReBAC, ABAC, and RBAC in FastAPI without overcomplicating it?, [https://www.reddit.com/r/FastAPI/comments/1jn1203/how\_do\_you\_handle\_rebac\_abac\_and\_rbac\_in\_fastapi/](https://www.reddit.com/r/FastAPI/comments/1jn1203/how_do_you_handle_rebac_abac_and_rbac_in_fastapi/)  
42. Model context protocol (MCP) \- OpenAI Agents SDK, [https://openai.github.io/openai-agents-python/mcp/](https://openai.github.io/openai-agents-python/mcp/)  
43. FastAPI FastMCP, [https://gofastmcp.com/integrations/fastapi](https://gofastmcp.com/integrations/fastapi)  
44. Building a Server-Sent Events (SSE) MCP Server with FastAPI \- Ragie.ai, [https://www.ragie.ai/blog/building-a-server-sent-events-sse-mcp-server-with-fastapi](https://www.ragie.ai/blog/building-a-server-sent-events-sse-mcp-server-with-fastapi)  
45. panz2018/fastapi\_mcp\_sse: A working example to create a FastAPI server with SSE-based MCP support \- GitHub, [https://github.com/panz2018/fastapi\_mcp\_sse](https://github.com/panz2018/fastapi_mcp_sse)  
46. Configuring Nginx for n8n MCP Servers with Claude Code \- \~/git/blog \- Jörg Thalheim, [https://blog.thalheim.io/2025/11/12/configuring-nginx-for-n8n-mcp-servers-with-claude-code/](https://blog.thalheim.io/2025/11/12/configuring-nginx-for-n8n-mcp-servers-with-claude-code/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFsAAAAZCAYAAABeplL+AAADi0lEQVR4Xu2YWahOURTHFzLPypyQPBgjkuFBSCmhJI8K11A8SMrwwIu8KCIlHjyYh0SJJyFTiZAiQ7gZylTmeVx/a59aZ929v3POd7/uvQ/7V/++s/9rf+fss8/ea+9ziCKRSCRSTxxjnWQ1Y51LhyKV5i2rPWss66+J1TsbWG1VuTFrgSo3NBaxLrLus7ab2GzWMuMVZifrMesBa6+JZYHOu8D6wDrFGpkO0yvWT9ZTkhv4yDqQqlG3DGFdsaajKes3yQCZxrrLmqjim1hLWftZt0g6PzftWO9Yg5S3hmR6LFReiJusT6r8jWpOrRckHf6VtYs1Oh2uM9Cu7+7XthF0ZX1htTQ+6m50x0dZW1SsWh1nMpnkZLeVN8l5p5UXAvXwcHTZ3shzU64vhrHakL+NYDn5fXjJPexgzVWxq6x+qpzJBFY3VV5NcoEVyvOBfHbHmh6eWSMn6Jih1lR0IElfRQl1Nmagz9f1kVLmqNg1Vg9VLgS2M/eccLOlwNM+TnKx9ySrtC9FoLOrWDfc8bZ0uCRIP4Ot6UDexbQuSqiz/5Df1/WR09e7Y6xVeECFQU5KLobkn8V4krpYTNYq/xfJAqippvRuZAlJ2kLD87CV1V+VW5CkOJtb8xLq7Lw+2o+F8zxrhPJz05HVh7WY9Zk1LhWtyXSSBmCX0Un5152vQWdpupPUwRYrD41YT0jaB/BCEdpN5MF2XkJRvyKgE7BzmGIDihkkDUBq0JxwPtJRKVCnSL7FdvQhSYdjB4TBUS6hzivqV4ysCwwkie8z/kHnJ3vT1uSfJVnntzRhHSEZBJ1NrCiha2Pb5/ND9QuDTTmmvh2JWRdA3kQKQedqDpP8b4wrY+T7zgMP+T0vu1mPSEY2zomdSLmE7g0vKT4/VL8wyaI43/j2Aj2p5mvqSpKFQoPXXP0/vPD8UGXQi6TOOuOH2Ez+BRK/5WDvLWEq+X14WAxrzVmSk+mVfZTzzigPnQqvt/K6OG+A8rC46gbvYR1SZYB9/EtKL6wh8NqMuhakJ3wasDMyD6HORqrCfQ43PurONF7ZYPuCE2JvjZGIY/2SA9BB+PaBBmnwnQD/we7gNWtVOvwfNB75MJmm+D6SB2wXS73UYJG8ZM0SJJ1sZXlDsr+/TDLzm6fDtQejGV/iID1l84CbxsOYZwMKfBZAGsLCaR9YQ6MVaxbJt6G+JhaJRCKRSKRS/AOa7/N9AGG4EgAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEgAAAAXCAYAAACoNQllAAADr0lEQVR4Xu2XWaiNURTHl5kyj1eGrjGSpIwPSkky5YGkDDdChghJSCmS6YFI3UxFigxPCiHDiykS8UKZ5znzzPrftbezzjp7n3OHc6/o/Orf/fZ/7f2dfde31/72R5QjR44c/xfdWfnW/EdoxLpvzWxyk7VLtR+wPrFeKO9f4Ckrz5ohCllXWT9Zr1jjWVWSeiTzntVUtdew7lLFJ+giyZx/ObVODtM0FfNapOKPWYdUO4nqJAMu2QBzgCRWxwaYnaw21mQmUMUnyIP/4Q3rOauGiQH8Lz2syTRgfbYmqMU6wjrqri1NSFbJBuPXo8gNmbH09xK0lLWeJBEFJgYwr0rWdGAxpIAbYWmmYwVJvwHK2+28EGMoniCsLiztljbgwGoewZrM6kDyIEazOutOEfqQjAe+jCyzrKHoZA3cEDeJ1p5jGUm/icq74bwQoQTVZm1mnWRtYX1jbUrqIdxjvWRdIHlwt1mLSTb/TCxU16EEIdldjadJ2WvPUOrKCLGVUhOEyT9TbU0oQWdZX1V7uGtXU147knF+dSGR29w1klbZXcc4rK79A9QvkGEUL68UfNn4CcRoTJIMCPuRB2OPq7bGJqg9Sf9eygN4MNjHmrs2NtYliXDR72HcKOXF6M36qNp1We9Izjh+ZVxOhDNzguTHsSekA6sG/c4bH95B43lsgrD00R+T1nR0/lSSlYRrnSC8WeBNV16MBZT6wFDCGD+S1ZD1Izmcniskg7vYgAF9IFufJUkQ+qG/30A9KCX4O1x7Het0IkyDWbcoc2mBt6x+1qTE/Dey9ppYWlCvGNjXBhSYGPqEXufwj1nTYRO0naR/feWBts5f5dqI4ylPInmjXKfM+6MHp/fYuQe6xpphYmlBfSPrp4zvmUJyYyz/EIjFNulxJKdwDw6Z6F+gPDCP5K3lN+q17i8eDMqrJCy3hmM+yW8/sYHigAljsM0sngR8TD4Gvl3QJwTu+9p4/il68NpH+QxU3kqSsspntWI1U7F04AEMtaYDif7A2mMDAew2UgT2AUwMqwmvXZTenKQeYWZSOEF+SXvlqVg31h2ScsCegIOgxm/aIYVez3ht234hcPbBvTOBqskaLVjfrcnUJCkR/ENV3XVxyCf5hsJLA5s5xuNes0lWwJA/PcuP/dYoKz1Zq61ZSlACsRWA8im0ZpaZS/HfLxM4jOkDZGnB9xcmiFWjwdnpHKu/8bPNI9Y+a2YD1Dc+A7IFDpX4BPrCekhyAEQ5lyeDSJ3yfwN++uTXuH6gvAAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJUAAAAaCAYAAAC+RB5CAAAE/ElEQVR4Xu2aVwgkRRCGy4Cinor5DHAPKir4oAjqiXIIgj6cIuaIijk/eIcg+mB4MiGKYD7M+KaCesYTAwbMWTGcZ3xQzJhDfdT0bV1tz+xtmJ1dbz74Yae6d7Z6qjpM94q0tLS0tLS0tLS0VLON6q9CD4SylnIejYZhuFH1b0bb+kpTBH7/Fo0ZblV9pfpMdVthO7RT3Ag/SXcccvpHtX7xnVHCfQ+IxkHYRXWIWCBw+ALVMapVfKUpoldSraG6RfWw6kixtj6lOkf1u6vXBMerTpJO8vD5RNXJqjNVN6t+EBuF64jP7arvonEYUkOmnV5JRRsvikYx+/fR2BD48nM0Op6OhhGyULVFNA7KipBU64i1cYNYoPyoui8aG2CmmI+PxALHndEwQhi9L47GQVhPrCGLYsEUUpVU54m1c6dYoDyr2ioaG+AaMR/3cLYLVXe7a6bJOuH3Z0Vjv+wndiOcn3aqkuoEsXZ+qpoRyiaF18X8X93ZFqtOddd1wzM6OBr75QXVn6q1YkHNvCyd1//l0Sv2tUqqkgq4T5rqk+5fpkZzzJVu39C3qpVcvbrhN9Mb8UCsKZZQJNa42Uy1fR/a3L5WSa+kYh/rKukO3CRwqZgvZ6v2Uh2oukJ1r680BvBhqH0r3oS4CVPg/4FeSRVhcU77t4wFDUDnjgm+qmpHdz3Pfa4LfHgpGvthkdhN6thMa4KypLo2GgqOEmt/7o1w3ORGzXWlM/WtLLa+qht8eDIa+yHXkHFBb4jrpiq9Zl+rJJdUbBReHWyJu6S59kfwg13tMt5SXR6NNYAfnDgMTC6pNlQtUb2helWsMYnnVM+ozpBOD2Jd9oVY0DdVXVfYe8EaKa6bqsQarBe5pNpZ9a5YT4+wi77YXX8ktmv9hOpL6bwFMQW9KLb2XLuwwRzV52L1aU8u8eerdovGAG97xOGdWOCgnDUh8eGlhficLhafdKyGv8SHDuvjc5mYb+xxEZ+DirIc/M750dgLHu5hYo3lBn+LOTPb1bmpKKOxR4tNj7+48ntU76lOK+oljg3X4yaXVA+pTlH9qrpSrENwJEG9XV09SNMhsM7cWvW86u2lNax8plgyfePsH8uyHRAYJXMdN0EiHid2bESdBWIBR0eIPd+vizJi5sFGe4kPG7vEx0/zxAeo59diXPdKqo2jsRf0+tRQLxIpwWemnAQNog4PGNHzP1A9VtgTu4frcZNLqpQQ9PIPxco56jhraY0OPqkSXHMmltpOMu1Q2P3uNs8iJhUw8pEYOS6R7jiUabXiOwni40df6rAHl/wkPslO50hwXZZUG8nybd0MBEnlz5/2le6HDRwnePskJlU/lCUVU18E+x3uuiyp4IZoGAE+PoA/bEtEsPvTgqqkWqjaJBpHRUyqGWKbcJ4HpXv6Y28lBmWc1JFUdJw/3DWLfoLEmsuPQKxxcknFEqJspBqGmFTEhzVwgvgA7eFfDomypGI087PTSGGxzQ+jeCL+uNjwz19FErz2fiK2YZaOQppi2KTi7Qv/CZDfZpkl1m5OAehgibligSSALI5zScXUuV00DgHx4R8V+Mk60TNHzE+/mU18rheLzwIpTyravn80TgI85GlOqmEoS6q9o6FhcknFlHdusE0MONtkUrGYTVsQjC7j5E3V+9E4gRCfw6NxkmE4xmle41ck9pTOkmGfUDZJcI6YmzZbWiaL/wDkVIHVzgQ9egAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,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>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAwCAYAAACsRiaAAAAIE0lEQVR4Xu3dd6gm1RnH8WOJNXaxxqyxYFc0ioiKa7BGxbZiA7121IiEoNhwFxONaEIMKJLoH1cSRbBj7wui2OuKiGVX7MYae/f8nHP2fd7nztyZuXfeu+v6/cDhzDwz77xzZ+Z9z3nPOTM3BAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAPOQFH5iLLeYDPzPb+EAHfkrnv2tLxrS7DwIAmvsmpu9deqhvjcL/fcCpWy7X+UBL37l5v+9dGtR2F/aBudQ7bt5fIzk9a1eaA1aP6duYbnPxLjzuA+PwmA8kp8T0UUwnxHS/WzaR/HkdxPU/1QcAAO0sHdMMM79EKApBq+6LW8sX9EHnSx+ocI4PRBfFtJYPRhfHNNkHO1L3N4/FVz4wF3omlJ9LHY+FXOxyN9+lf/qAc3ZMw2a+6/M1HNPaPjhGl/lAKD4PK6fpzWK6xSwbqxN9oAUdv9PN/CIp1qVDfQAA0JwqbL4F4K+h+y/rpsre17euZWXrdmGZmO72wQ6oEnKQDzawqA/UuNAHGloppqd8MLHHevuU72ZiXdB2P/XBCv7cX+Lmu+DfYzRVLWT7+UByhpuf382PhyqDG/jgKJYL/X/rqSl/xMS60OZ4AgAcVdgedbFVQ6/V7O00nak17vzQ6wZVS4eWbzh7jRDei+nK0KsIHhj6K11af1ZM98b0ZOgVDFXdnP8x09agCoDzYvqdD3ZArYTP+2CNrXyggeVj+r0PNnBBTEf4YLRUKM5VtpGZ7oKus7dCMdapKZ37k3ywY1XXV1lrWFmrpOj6LqNtr++DHfp1TJ/5YIW/h/6/9ZqUz2diXXgtplV8EADQTFmFTfQFnltQ8pf5zqGoaHm2wuYLuTNTPsXEDg7961VNZ2UDlv8cytftwqC2K222/XpMn7ikivKHMb0f0wcly20aCu18EdMvfTB6IKZdUrrWLRsvjeFawAcbWDYUrVo6nkpVFabx8C3P2RYxrWDmbzDTXtX5PiSmj0Ox/HO3rEs6n1Ut1Jn2Qd22O4bi2hrL+WhCFcOpPggAaKaswrZaKL7ENZ5NbKGjL3/N2wHnmq+qsOXCYg8T2z9UV9L862VbHwhFt09V9914le1DlTbrSpP1jw1Fy+Z4aRySWjVO9gsqVO2bjW9tprtyeEx/9MEWtH/H+GCJqq7iyT6Q3OMDhr0x42oz7VUd02zjUL/OWP0tpl19sITeP7du3plytaLWVYI1Bk+t4k3px5tacQEAY1A2hk2F0SwznwsU/QLPtjPTWp67d3zhc1PKbYVN43qqKml5enMTO8xMZ1pPXbddOy2M/Bs821W0hpnOdvABo27blrqWfatZm1Q1fqrKuzH9xsV0o0HZPjftbmtLdxOv6YOOboywyvYv09gwnS/lGqvl6c7daT6YvOoDxuIpVyvoaPy+qRvX7oeuH52rrqhCrZtx2vD7KE/7gJFb4DS2clO7IPHnJ9PQhiN9EADQjCpsT5h5FWC+CyV/oe8Veq0Jy6dctHydNK1uOt31JhoLlu1pppt0iaqVKSsbw2Zfo1/6mtf4MBXM/0pxdQdNCkWFVJUo/z5l3XvqcnzFzKvbSq5P+a0pvyLlz6X83JSPRmPYHvbBGm/4QEOq7LU1HEaOYdOdg75AvzEUYxfVKqOK25RQVBTyXaO6yzgfd/Gvr6PxV1WVmC1D//buiulPaVrXna6tPG5M3ZaqrOUbGX6V8jyOUK+VaSn36vZbrVB1d2bOcvO6vt4083oPXbP+WB6dlmvfVWnW50rUhVxFrbIab9iGtv2yi6min7eTP0tqqRXtr64J36Ku46zvEhlOuadt5FZ7AEALfpC/Hjsx3a6Q4jmpe2XdmL4O/ZUoLVNlJNP4sv+FooInfwm9bYjdpk2i7k9VkuwvcfuYkavCyNeInX4wpT+E/seJ2HXUDezHDtntDqWYCkptKxdYMtNM524zvSZX4qroLlHb0jgo//aBhlYP/d3M94WR58gf9xfNtOI6VqoAVB338dL5F/3I0HVhB7Hn91eF7bcppoqfv8tWD7GdYeanmWmrbr/9D5syQ25e3ZTqatQYRFtxk7JjqR8EqljmR4zU7VMbOn7+vPrzmz9L+frX3adDs5f21lVFVM+Vk+GUe13uOwCgBRXKamXQF7HGSw3Kf0P5c9gsWxjsm/KjQlHAb5LmfYHR5GG+qpzKP1Kuwv+4mA5I8/nxHxqLJIemXHSnrOUriHOjl0L92CXLVzJELZ6jHXdLLTVVqS21fq6YpvXDQvS3+Na6PP4s75ceY6M7ma3h0HtO2niVPYetjD2W6p7Ojg+9lryJOpZZ/iztk3J9Fu3zBMv2R49YKXtIdP4BBwCYYPqFrsdO+C6VQRitNUOVKRUce6d5dU/acTQ3h+KBvLZwyV2bdSaFXlfOHaHYxk4pz91z64ViYL993IMKX9+y06YiNCc1veFB3Xf6+3O3saj1Kj9SRMdd/4WgrFAfFHXLXhqKCkN+X+VXh6ISpJY5tRzeHorzJuoiPStNZ10+g6zq0R5W2bHUGLp8w4jGpemGgIk8lpI/SxrykFvk9CNG+cyUD4Xi2p/+4ytC+EUY2ZU/1c0DAFBpogs7FDju3eFYAgDmaYPsskW9si4yjA3XMgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAmNN+AHph50fnF11qAAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAwCAYAAACsRiaAAAAFYUlEQVR4Xu3cW6htVRkA4JGWFpYihlIvRRTlJaOCXtTypR66QIE+SBBbRUE0CiQx6uEo4oWSjIrAbicqeinqIZRSk0pBjG6GhJgieMkoS7tiZTX+5pitsf+91l5r7z330bP9PvgZc/5z7bPGmuvA+hmXWQoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcVE7NiQncmxPPMpflBACwM/9O53+u8Z8F8XQ6osZtNe6scWiN162/vCM/zYkd+ElONJfWeKLG+2vcnq4dSPk73Y3v9/ScAAC27zM1XpmT1edqnJJyD6fzA+kdZX0h9M/ueAr7a7wqJ7fpyzlRPVnjJe34DTVu6K49HaI4+0h3/vyWm9KXcgIA9pIX1nhBTi7x6ZxYUR5dG/U/3mut/ViX264ba1ybkyvIxcR70/kU8ntkt5TZvVjkzJxoPprOD0nnU7mwxq9zMjmmrP+sH27tj7vcFJ7KCQDYS/6WEyt4cY235+QS767xlZxs+h/0mMKbWow4vTonNxH9+XxOTmxZwfacGn/MyeTnOdHEv31CTk7oyBq/L6sVglEw95/1m62Nzzelr9Y4KycBYC+Iace/pPhTjcdr/GHOtRxrZXXfrfHOnKyuLMMP+ttqXJ2uTe3lZejHMs+r8Z0yW2s1bxp3pxatPQs/7I6/0B1ni4q+95XZ2sC/p2s7Ed/Pu3JyiehDTNu+tQz/r2I94G6Ift2akwBwMLugbJw2245Yi/RQjRflC3PcXeO0nCzD6Fcs7A+rjNhMId5zVTGN+/WcnOOMnGhOz4nm+znR6Yu0H3TH2aKCbXRyWf6aVW3334m/ixG5cFNrX1vjue14M//KiU28uSwecQSAg9pjZeOo2VZi0Rqqeb5R4+ycLMMP+rEp94t0PoUY3Ytdk8vkwiTOj0q5UYwWRZEZ7ViU9A6vsS8nmwdzoolRqGzR9GHu64fKsGZs9IoyfE9Tinv4npzcRO5juCsnOv0I3Ou749Evc6I5twzTogCwJ52TEyuKYm8r1srGNWyxMzT/oF9ehsdQRAEU6+vOKMPrzm/X/1rjsDJb37WsCIsC4LdltVHAGPXp+xN/++12HLstY/PBOIoT06YvLbNRo3HE6PrWjlOR+1qb5c89mvd9LJrGfSCdx3T2b7rzeI8oKKNvP6vxyTLs1uzv5fi68KvWLhP38ndl+YhofE/3p1wU+WMBPG48GDcMRD+ifyd15+HoMivk9rc2i2Jtq+sqAeCg8YmcWMFYlGxVv5PvijL8IM+LGJkK/Q7EyN9RhqLi5jJ7LMaiwidEsXBeTm7ig629tQx97TcejO8fBdsbu9zx/3/FIKYzY23gWMDtm11aZ7N+Z1/MiWYtnX+8DO8b6w/7wi3EZxn71N/LGL0b79FWpiDDRWXxLtG4f/l7HWMUo2XRj7GoO7Gs/0zja+OxKte04/2tzewSBYCJxCjIVhbw98VA7EocxeMkPtCOt1L47EQ8IuS4dvya1r6sbHz/sc/3tfaqsnH34v4ye07aTs17Dts8ffHZ38vwrdYueuzKbvlUa8d7Ef8//tGOQ763IZ7ZNxb0vetyAgDYvlWLgpgKjR/s2O04inVfl7Tjz5ZhOnLej/pu+VqZFT7xvjEtGu2jZejbA2UYnYt+jbsp7ynDNG9vymeQrbLQPgqi6Ge/Y7S/lxfX+FE5sPcyxMjevWWYyhxH5GI0Ldo3tXatDPf9e8Of/O+eP9KOR29J5wDAM8yBLjL2MvcSANg18XgRpjFvuhEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgK37L2gmGkI8KkX1AAAAAElFTkSuQmCC>