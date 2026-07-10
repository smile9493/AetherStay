#!/usr/bin/env python3
"""
AetherStay — 项目脚手架 CLI 工具

Usage:
    scaffold.py init                    初始化开发环境
    scaffold.py check                   检查项目健康状态
    scaffold.py gen api <name>          生成完整的 API 模块（model+schema+service+router）
    scaffold.py gen model <name>        生成 SQLAlchemy 数据模型
    scaffold.py gen schema <name>       生成 Pydantic 数据校验 Schema
    scaffold.py gen service <name>      生成业务逻辑 Service
    scaffold.py gen router <name>       生成 API Router
    scaffold.py gen admin <name>        生成管理员 CRUD 模块
    scaffold.py gen task <name>         生成定时任务
    scaffold.py gen view <name>         生成 Vue 视图页面
    scaffold.py gen store <name>        生成 Pinia 状态管理 Store
    scaffold.py gen component <name>    生成 Vue 组件
    scaffold.py list                    列出所有已注册的模块
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from string import Template

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError:
    print(
        "❌ 缺少依赖 Jinja2。请先安装：pip install -r scaffold/requirements.txt"
    )
    sys.exit(1)

# ── 项目路径常量 ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend" / "app"
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "src"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

def jinja_pluralize(name: str) -> str:
    """Simple English pluralization filter for Jinja2 templates."""
    if name.endswith("s"):
        return name
    if name.endswith("y"):
        return name[:-1] + "ies"
    return name + "s"


jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
jinja_env.filters["pluralize"] = jinja_pluralize


# ── 工具函数 ─────────────────────────────────────────────────


def to_snake(name: str) -> str:
    """Convert PascalCase or kebab-case to snake_case."""
    s = name.replace("-", "_").replace(" ", "_")
    return "".join(f"_{c.lower()}" if c.isupper() else c for c in s).lstrip("_")


def to_pascal(name: str) -> str:
    """Convert snake_case or kebab-case to PascalCase."""
    return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))


def to_lower(name: str) -> str:
    return name.lower().replace("-", "_")


def pluralize(name: str) -> str:
    """Simple English pluralization."""
    if name.endswith("s"):
        return name
    if name.endswith("y"):
        return name[:-1] + "ies"
    return name + "s"


def make_ctx(name: str) -> dict[str, str]:
    """Build template context with consistent naming."""
    snake = to_snake(name)
    pascal = to_pascal(name)
    return {"pascal": pascal, "snake": snake, "plural": pluralize(snake)}


def render_template(template_name: str, **kwargs) -> str:
    """Render a Jinja2 template with given context."""
    tpl = jinja_env.get_template(template_name)
    return tpl.render(**kwargs)


def write_file(path: Path, content: str) -> None:
    """Write content to file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  ✅ 创建 {path.relative_to(PROJECT_ROOT)}")


def check_file_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


# ── 命令：init ───────────────────────────────────────────────


def cmd_init():
    """初始化开发环境：.env、虚拟环境、数据库、依赖安装。"""
    print("=" * 60)
    print("  🏗️  AetherStay 项目初始化")
    print("=" * 60)

    # 1. 复制 .env
    env_example = PROJECT_ROOT / ".env.example"
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        if env_example.exists():
            env_file.write_text(env_example.read_text())
            print(f"  ✅ 创建 {env_file.relative_to(PROJECT_ROOT)} （请修改密钥等配置）")
        else:
            print("  ⚠️  未找到 .env.example，跳过 .env 创建")
    else:
        print(f"  ℹ️  {env_file.relative_to(PROJECT_ROOT)} 已存在，跳过")

    # 2. 后端虚拟环境
    venv_dir = BACKEND_DIR.parent / "venv"
    if not venv_dir.exists():
        print("  📦 创建 Python 虚拟环境...")
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
        )
        print(f"  ✅ 创建虚拟环境 {venv_dir}")
    else:
        print(f"  ℹ️  虚拟环境已存在，跳过")

    # 3. 后端依赖
    pip = venv_dir / ("bin" if sys.platform != "win32" else "Scripts") / "pip"
    req = BACKEND_DIR.parent / "requirements.txt"
    if pip.exists():
        print("  📦 安装后端依赖...")
        subprocess.run([str(pip), "install", "-r", str(req)], check=False)
    else:
        print("  ⚠️  pip 未找到，请手动安装后端依赖")

    # 4. 前端依赖
    if (FRONTEND_DIR.parent / "package.json").exists():
        node_modules = FRONTEND_DIR.parent / "node_modules"
        if not node_modules.exists():
            print("  📦 安装前端依赖...")
            subprocess.run(
                ["npm", "install"], cwd=str(FRONTEND_DIR.parent), check=False
            )
        else:
            print("  ℹ️  前端依赖已安装，跳过")
    else:
        print("  ⚠️  未找到 frontend/package.json，跳过前端依赖安装")

    # 5. Docker Compose 启动数据库
    print()
    print("  💡 接下来请运行 docker compose up -d mysql 启动数据库")
    print("  💡 然后执行 cd backend && source venv/bin/activate && python run.py")
    print("  💡 前端：cd frontend && npm run dev")
    print("=" * 60)


# ── 命令：check ──────────────────────────────────────────────


def cmd_check():
    """检查项目健康状态。"""
    print("=" * 60)
    print("  🔍 AetherStay 项目健康检查")
    print("=" * 60)

    checks = [
        ("📄  .env 配置文件", lambda: check_file_exists(PROJECT_ROOT / ".env")),
        (
            "🐍  后端 requirements.txt",
            lambda: check_file_exists(BACKEND_DIR.parent / "requirements.txt"),
        ),
        (
            "📦  前端 package.json",
            lambda: check_file_exists(FRONTEND_DIR.parent / "package.json"),
        ),
        (
            "🐳  Docker Compose",
            lambda: check_file_exists(PROJECT_ROOT / "docker-compose.yml"),
        ),
        (
            "🗄️   数据库 DDL",
            lambda: check_file_exists(PROJECT_ROOT / "database" / "schema.sql"),
        ),
        (
            "🐍  后端入口 main.py",
            lambda: check_file_exists(BACKEND_DIR / "main.py"),
        ),
        (
            "📦  前端入口 main.ts",
            lambda: check_file_exists(FRONTEND_DIR / "main.ts"),
        ),
        (
            "📄  README.md",
            lambda: check_file_exists(PROJECT_ROOT / "README.md"),
        ),
        (
            "⚙️  项目配置 config.py",
            lambda: check_file_exists(BACKEND_DIR / "config.py"),
        ),
        (
            "🔐  认证工具 utils/auth.py",
            lambda: check_file_exists(BACKEND_DIR / "utils" / "auth.py"),
        ),
    ]

    all_ok = True
    for label, check_fn in checks:
        ok = check_fn()
        status = "✅" if ok else "❌ 缺失"
        if not ok:
            all_ok = False
        print(f"    {status}  {label}")

    # 检查后端模块完整性
    print()
    print("  📂 后端模块检查：")
    for subdir in ["api/v1", "models", "schemas", "services", "tasks", "utils"]:
        path = BACKEND_DIR / subdir
        ok = path.exists() and path.is_dir()
        status = "✅" if ok else "❌ 缺失"
        if not ok:
            all_ok = False
        print(f"    {status}  backend/app/{subdir}/")

    # 检查前端模块完整性
    print()
    print("  📂 前端模块检查：")
    for subdir in ["views", "stores", "api", "router", "layouts"]:
        path = FRONTEND_DIR / subdir
        ok = path.exists() and path.is_dir()
        status = "✅" if ok else "❌ 缺失"
        if not ok:
            all_ok = False
        print(f"    {status}  frontend/src/{subdir}/")

    print()
    if all_ok:
        print("  ✅ 所有检查通过！项目结构完整。")
    else:
        print("  ⚠️  存在缺失文件，请检查上方标记。")

    # 脚手架自身检查
    print()
    print("  🛠️  脚手架工具检查：")
    scaffold_checks = [
        ("scaffold.py", PROJECT_ROOT / "scaffold" / "scaffold.py"),
        ("requirements.txt", PROJECT_ROOT / "scaffold" / "requirements.txt"),
        ("README.md", PROJECT_ROOT / "scaffold" / "README.md"),
        ("templates/backend", PROJECT_ROOT / "scaffold" / "templates" / "backend"),
        ("templates/frontend", PROJECT_ROOT / "scaffold" / "templates" / "frontend"),
    ]
    scaffold_ok = True
    for label, path in scaffold_checks:
        ok = path.exists()
        status = "✅" if ok else "❌ 缺失"
        if not ok:
            scaffold_ok = False
        print(f"    {status}  {label}")

    template_count = len(list((PROJECT_ROOT / "scaffold" / "templates").rglob("*.j2")))
    print(f"    ℹ️   Jinja2 模板数量：{template_count}")

    print()
    if scaffold_ok:
        print("  ✅ 脚手架工具完整可用。")
    else:
        print("  ⚠️  脚手架工具存在缺失文件。")
    print("=" * 60)


# ── 命令：list ────────────────────────────────────────────────


def cmd_list():
    """列出项目中已注册的模块。"""
    print("=" * 60)
    print("  📋 AetherStay 已注册模块")
    print("=" * 60)

    # 后端 Models
    print()
    print("  📦 数据模型 (Models):")
    models_init = BACKEND_DIR / "models" / "__init__.py"
    if models_init.exists():
        content = models_init.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("from") and "import" in line:
                name = line.split("import")[-1].strip()
                print(f"    • {name}")

    # 后端 Routers
    print()
    print("  🚏 API 路由 (Routers):")
    router_file = BACKEND_DIR / "api" / "v1" / "router.py"
    if router_file.exists():
        content = router_file.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("api_router.include_router"):
                parts = line.split("(")
                if len(parts) > 1:
                    name = parts[1].split(")")[0].split(".")[0]
                    print(f"    • {name}")

    # 后端 Admin Routers
    print()
    print("  🛡️  管理员路由 (Admin):")
    admin_router_file = BACKEND_DIR / "api" / "v1" / "admin" / "router.py"
    if admin_router_file.exists():
        content = admin_router_file.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("admin_router.include_router"):
                parts = line.split("(")
                if len(parts) > 1:
                    name = parts[1].split(")")[0].split(".")[0]
                    print(f"    • admin/{name}")

    # 后端 Tasks
    print()
    print("  ⏰ 定时任务 (Tasks):")
    tasks_dir = BACKEND_DIR / "tasks"
    if tasks_dir.exists():
        for f in sorted(tasks_dir.glob("*.py")):
            if f.name != "__init__.py":
                print(f"    • {f.stem}")

    # 前端 Views
    print()
    print("  🖥️  Vue 视图 (Views):")
    views_dir = FRONTEND_DIR / "views"
    if views_dir.exists():
        for f in sorted(views_dir.glob("*.vue")):
            print(f"    • {f.stem}")
        admin_views_dir = views_dir / "admin"
        if admin_views_dir.exists():
            for f in sorted(admin_views_dir.glob("*.vue")):
                print(f"    • admin/{f.stem}")

    # 前端 Stores
    print()
    print("  🗄️  Pinia Stores:")
    stores_dir = FRONTEND_DIR / "stores"
    if stores_dir.exists():
        for f in sorted(stores_dir.glob("*.ts")):
            print(f"    • {f.stem}")

    # 前端 Routes
    print()
    print("  🧭 Vue 路由 (Routes):")
    router_file_fe = FRONTEND_DIR / "router" / "index.ts"
    if router_file_fe.exists():
        content = router_file_fe.read_text()
        seen: set[str] = set()
        for match in re.finditer(r"name:\s*'([^']+)'", content):
            route_name = match.group(1)
            if route_name not in seen:
                seen.add(route_name)
                print(f"    • {route_name}")

    print()
    print("=" * 60)


# ── Generator: 后端 API 模块 ─────────────────────────────


def gen_api(name: str):
    """生成一个完整的 API 模块（model + schema + service + router）。"""
    snake = to_snake(name)
    pascal = to_pascal(name)

    # 确定文件名
    model_file = BACKEND_DIR / "models" / f"{snake}.py"
    schema_file = BACKEND_DIR / "schemas" / f"{snake}.py"
    service_file = BACKEND_DIR / "services" / f"{snake}_service.py"
    router_file = BACKEND_DIR / "api" / "v1" / f"{snake}.py"

    ctx = make_ctx(name)

    print(f"\n  🚀 生成 API 模块：{pascal} ({snake})\n")

    # 1. Model
    print("  📦 [1/4] 生成 Model...")
    if model_file.exists():
        print(f"  ⚠️  跳过（已存在）：{model_file.relative_to(PROJECT_ROOT)}")
    else:
        content = render_template("backend/model.py.j2", **ctx)
        write_file(model_file, content)
        print(
            f"       → 请将 {pascal} 添加到 backend/app/models/__init__.py"
        )

    # 2. Schema
    print("  📋 [2/4] 生成 Schema...")
    if schema_file.exists():
        print(f"  ⚠️  跳过（已存在）：{schema_file.relative_to(PROJECT_ROOT)}")
    else:
        content = render_template("backend/schema.py.j2", **ctx)
        write_file(schema_file, content)

    # 3. Service
    print("  🔧 [3/4] 生成 Service...")
    if service_file.exists():
        print(f"  ⚠️  跳过（已存在）：{service_file.relative_to(PROJECT_ROOT)}")
    else:
        content = render_template("backend/api_service.py.j2", **ctx)
        write_file(service_file, content)

    # 4. Router
    print("  🚏 [4/4] 生成 Router...")
    if router_file.exists():
        print(f"  ⚠️  跳过（已存在）：{router_file.relative_to(PROJECT_ROOT)}")
    else:
        content = render_template("backend/api_router.py.j2", **ctx)
        write_file(router_file, content)
        print(
            f"       → 请将 {snake}.router 注册到 backend/app/api/v1/router.py"
        )

    print(f"\n  ✅ API 模块 {pascal} 生成完成！")
    print()
    print("  📌 接下来需要手动完成：")
    print(f"     1. 在 backend/app/models/__init__.py 中添加 {pascal}")
    print(f"     2. 在 backend/app/api/v1/router.py 中添加 {snake}.router")
    print(f"     3. 在 database/schema.sql 中添加对应的 DDL 建表语句")
    print(f"     4. 如果需要在 Admin 中管理，执行：scaffold.py gen admin {snake}")


def gen_model(name: str):
    """生成 SQLAlchemy 数据模型。"""
    snake = to_snake(name)
    pascal = to_pascal(name)
    ctx = make_ctx(name)
    filepath = BACKEND_DIR / "models" / f"{snake}.py"

    print(f"\n  📦 生成 Model：{pascal}\n")
    if filepath.exists():
        print(f"  ⚠️  文件已存在：{filepath.relative_to(PROJECT_ROOT)}")
        return
    content = render_template("backend/model.py.j2", **ctx)
    write_file(filepath, content)
    print(f"\n  ✅ 生成完成！请将 {pascal} 添加到 backend/app/models/__init__.py")


def gen_schema(name: str):
    """生成 Pydantic Schema。"""
    snake = to_snake(name)
    pascal = to_pascal(name)
    ctx = make_ctx(name)
    filepath = BACKEND_DIR / "schemas" / f"{snake}.py"

    print(f"\n  📋 生成 Schema：{pascal}\n")
    if filepath.exists():
        print(f"  ⚠️  文件已存在：{filepath.relative_to(PROJECT_ROOT)}")
        return
    content = render_template("backend/schema.py.j2", **ctx)
    write_file(filepath, content)
    print(f"\n  ✅ Schema {pascal} 生成完成！")


def gen_service(name: str):
    """生成业务逻辑 Service。"""
    snake = to_snake(name)
    pascal = to_pascal(name)
    ctx = make_ctx(name)
    filepath = BACKEND_DIR / "services" / f"{snake}_service.py"

    print(f"\n  🔧 生成 Service：{pascal}Service\n")
    if filepath.exists():
        print(f"  ⚠️  文件已存在：{filepath.relative_to(PROJECT_ROOT)}")
        return
    content = render_template("backend/api_service.py.j2", **ctx)
    write_file(filepath, content)
    print(f"\n  ✅ Service {pascal}Service 生成完成！")


def gen_router(name: str):
    """生成 API Router。"""
    snake = to_snake(name)
    pascal = to_pascal(name)
    ctx = make_ctx(name)
    filepath = BACKEND_DIR / "api" / "v1" / f"{snake}.py"

    print(f"\n  🚏 生成 Router：{snake}\n")
    if filepath.exists():
        print(f"  ⚠️  文件已存在：{filepath.relative_to(PROJECT_ROOT)}")
        return
    content = render_template("backend/api_router.py.j2", **ctx)
    write_file(filepath, content)
    print(f"\n  ✅ Router 生成完成！")
    print(f"  📌 请将 {snake}.router 注册到 backend/app/api/v1/router.py")


def gen_admin(name: str):
    """生成管理员 CRUD 模块。"""
    snake = to_snake(name)
    pascal = to_pascal(name)
    ctx = make_ctx(name)
    filepath = BACKEND_DIR / "api" / "v1" / "admin" / f"{snake}.py"

    print(f"\n  🛡️  生成 Admin 模块：{pascal}\n")
    if filepath.exists():
        print(f"  ⚠️  文件已存在：{filepath.relative_to(PROJECT_ROOT)}")
        return
    content = render_template("backend/admin_module.py.j2", **ctx)
    write_file(filepath, content)
    print(f"\n  ✅ Admin 模块生成完成！")
    print(
        f"  📌 请将 {snake}.router 注册到 backend/app/api/v1/admin/router.py"
    )


def gen_task(name: str, description: str = ""):
    """生成定时任务。"""
    snake = to_snake(name)
    ctx = {"task_name": snake, "task_description": description or snake}
    filepath = BACKEND_DIR / "tasks" / f"{snake}.py"

    print(f"\n  ⏰ 生成定时任务：{snake}\n")
    if filepath.exists():
        print(f"  ⚠️  文件已存在：{filepath.relative_to(PROJECT_ROOT)}")
        return
    content = render_template("backend/task.py.j2", **ctx)
    write_file(filepath, content)
    print(f"\n  ✅ 定时任务生成完成！")
    print(
        f"  📌 请将任务注册到 backend/app/main.py 的 lifespan 函数中"
    )


# ── Generator: 前端模块 ────────────────────────────────


def gen_view(name: str):
    """生成 Vue 视图页面。"""
    snake = to_snake(name)
    pascal = to_pascal(name)
    ctx = make_ctx(name)
    filename = f"{pascal}View.vue"
    filepath = FRONTEND_DIR / "views" / filename

    print(f"\n  🖥️  生成 Vue 视图：{filename}\n")
    if filepath.exists():
        print(f"  ⚠️  文件已存在：{filepath.relative_to(PROJECT_ROOT)}")
        return
    content = render_template("frontend/View.vue.j2", **ctx)
    write_file(filepath, content)
    print(f"\n  ✅ 视图生成完成！")
    print(f"  📌 请将路由注册到 frontend/src/router/index.ts")


def gen_store(name: str):
    """生成 Pinia Store。"""
    snake = to_snake(name)
    pascal = to_pascal(name)
    ctx = make_ctx(name)
    filename = f"{snake}.ts"
    filepath = FRONTEND_DIR / "stores" / filename

    print(f"\n  🗄️  生成 Pinia Store：{filename}\n")
    if filepath.exists():
        print(f"  ⚠️  文件已存在：{filepath.relative_to(PROJECT_ROOT)}")
        return
    content = render_template("frontend/Store.ts.j2", **ctx)
    write_file(filepath, content)
    print(f"\n  ✅ Store 生成完成！")


def gen_component(name: str):
    """生成 Vue 组件。"""
    pascal = to_pascal(name)
    ctx = {"component_name": pascal}
    filename = f"{pascal}.vue"
    filepath = FRONTEND_DIR / "components" / filename

    # 创建 components 目录（如果没有）
    (FRONTEND_DIR / "components").mkdir(exist_ok=True)

    print(f"\n  🧩 生成 Vue 组件：{filename}\n")
    if filepath.exists():
        print(f"  ⚠️  文件已存在：{filepath.relative_to(PROJECT_ROOT)}")
        return
    content = render_template("frontend/Component.vue.j2", **ctx)
    write_file(filepath, content)
    print(f"\n  ✅ 组件生成完成！")


# ── 命令映射 ──────────────────────────────────────────────────

GENERATORS = {
    "api": gen_api,
    "model": gen_model,
    "schema": gen_schema,
    "service": gen_service,
    "router": gen_router,
    "admin": gen_admin,
    "task": gen_task,
    "view": gen_view,
    "store": gen_store,
    "component": gen_component,
}

COMMANDS = {
    "init": cmd_init,
    "check": cmd_check,
    "list": cmd_list,
}


def main():
    parser = argparse.ArgumentParser(
        prog="scaffold.py",
        description="AetherStay 项目脚手架 — 自动生成标准化代码模块",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  scaffold.py init                         初始化开发环境
  scaffold.py check                        检查项目健康状态
  scaffold.py list                         列出所有已注册模块
  scaffold.py gen api amenity              生成完整 API 模块（model + schema + service + router）
  scaffold.py gen model coupon             只生成 Model
  scaffold.py gen admin coupon             生成管理员 CRUD 模块
  scaffold.py gen task release_bookings    生成定时任务
  scaffold.py gen view Payment             生成 Vue 视图
  scaffold.py gen store payment            生成 Pinia Store
  scaffold.py gen component PriceCard      生成 Vue 组件
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # init
    subparsers.add_parser("init", help="初始化开发环境")

    # check
    subparsers.add_parser("check", help="检查项目健康状态")

    # list
    subparsers.add_parser("list", help="列出所有已注册模块")

    # gen
    gen_parser = subparsers.add_parser("gen", help="生成代码模块")
    gen_parser.add_argument(
        "type",
        choices=list(GENERATORS.keys()),
        help="生成类型",
    )
    gen_parser.add_argument("name", help="模块名称（支持 PascalCase, snake_case, kebab-case）")
    gen_parser.add_argument(
        "--desc",
        "-d",
        default="",
        help="模块描述（仅对 task 类型生效）",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "gen":
        generator = GENERATORS.get(args.type)
        if generator:
            if args.type == "task":
                generator(args.name, description=args.desc)
            else:
                generator(args.name)
        else:
            print(f"❌ 未知生成类型：{args.type}")
            sys.exit(1)
    else:
        cmd_fn = COMMANDS.get(args.command)
        if cmd_fn:
            cmd_fn()
        else:
            print(f"❌ 未知命令：{args.command}")
            sys.exit(1)


if __name__ == "__main__":
    main()
