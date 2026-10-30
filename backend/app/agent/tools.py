import json
import logging
from datetime import date
from decimal import Decimal
from typing import Awaitable, Callable

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.audit import ToolCallAuditLog
from app.models.booking import Booking, BookingStatus
from app.models.inventory import DailyRoomInventory, InventoryStatus
from app.models.room import Room, RoomStatus, RoomType
from app.models.user import User, UserRole
from app.services import booking_service, inventory_service
from app.services.transaction import transaction
from app.utils.auth import CurrentUser
from app.utils.rate_limit import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)

_settings = get_settings()
_tool_rate_limiter = SlidingWindowRateLimiter(
    max_requests=_settings.AGENT_RATE_LIMIT_MAX,
    window_seconds=_settings.AGENT_RATE_LIMIT_WINDOW_SECONDS,
)

# 顾客视角工具（与后端已暴露的 MCP 工具一一对应）
CUSTOMER_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_available_rooms",
            "description": "根据入住日期和离店日期查询可预订的客房列表，返回 room_id、房号、房型、每晚价格、可住人数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "check_in": {"type": "string", "description": "入住日期，格式 YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "离店日期，格式 YYYY-MM-DD"},
                    "room_type_id": {"type": "integer", "description": "可选，按房型 id 过滤"},
                },
                "required": ["check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "为用户创建预订（Hold 保留房间），需要用户已登录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer", "description": "要预订的房间 id"},
                    "check_in": {"type": "string", "description": "入住日期，格式 YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "离店日期，格式 YYYY-MM-DD"},
                },
                "required": ["room_id", "check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_my_bookings",
            "description": "查询当前登录用户的所有订单，需要用户已登录。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "取消指定订单并释放房态，需要用户已登录且订单属于本人。",
            "parameters": {
                "type": "object",
                "properties": {"booking_id": {"type": "integer", "description": "订单 id"}},
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_payment",
            "description": "模拟支付以确认当前用户自己的待支付（pending）订单，需要用户已登录。",
            "parameters": {
                "type": "object",
                "properties": {"booking_id": {"type": "integer", "description": "订单 id"}},
                "required": ["booking_id"],
            },
        },
    },
]

# 管理员视角工具（仅 admin 角色可用）
ADMIN_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "admin_list_bookings",
            "description": "查询全局所有订单，可按状态或入住日期过滤，需要管理员权限。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "可选，订单状态：pending / confirmed / checked_in / checked_out / cancelled",
                    },
                    "check_in_from": {"type": "string", "description": "可选，入住日期下限 YYYY-MM-DD"},
                    "check_in_to": {"type": "string", "description": "可选，入住日期上限 YYYY-MM-DD"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_confirm_booking",
            "description": "管理员确认任意待支付订单（pending → confirmed），需要管理员权限。",
            "parameters": {
                "type": "object",
                "properties": {"booking_id": {"type": "integer", "description": "订单 id"}},
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_check_in_booking",
            "description": "管理员办理入住（confirmed → checked_in），需要管理员权限。",
            "parameters": {
                "type": "object",
                "properties": {"booking_id": {"type": "integer", "description": "订单 id"}},
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_check_out_booking",
            "description": "管理员办理退房（checked_in → checked_out），需要管理员权限。",
            "parameters": {
                "type": "object",
                "properties": {"booking_id": {"type": "integer", "description": "订单 id"}},
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_list_rooms",
            "description": "查询所有客房（含上下架、维护状态），需要管理员权限。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_create_room",
            "description": "新增一间客房并自动生成 90 天可售房态，需要管理员权限。",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_number": {"type": "string", "description": "房号，如 301"},
                    "room_type_id": {"type": "integer", "description": "所属房型 id"},
                    "status": {
                        "type": "string",
                        "description": "可选，客房状态：active / inactive / maintenance，默认 active",
                    },
                },
                "required": ["room_number", "room_type_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_update_room",
            "description": "更新客房信息（房号/房型/状态），需要管理员权限。",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer", "description": "客房 id"},
                    "room_number": {"type": "string", "description": "可选，新房号"},
                    "room_type_id": {"type": "integer", "description": "可选，新房型 id"},
                    "status": {"type": "string", "description": "可选，active / inactive / maintenance"},
                },
                "required": ["room_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_list_room_types",
            "description": "查询所有房型，需要管理员权限。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_create_room_type",
            "description": "新增房型，需要管理员权限。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "房型名称，如 大床房"},
                    "base_price": {"type": "number", "description": "每晚基准价（元）"},
                    "capacity": {"type": "integer", "description": "可住人数"},
                    "total_rooms": {"type": "integer", "description": "该房型客房总数，默认 0"},
                },
                "required": ["name", "base_price", "capacity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_update_room_type",
            "description": "更新房型信息，需要管理员权限。",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type_id": {"type": "integer", "description": "房型 id"},
                    "name": {"type": "string", "description": "可选，新房型名称"},
                    "base_price": {"type": "number", "description": "可选，新基准价"},
                    "capacity": {"type": "integer", "description": "可选，可住人数"},
                    "total_rooms": {"type": "integer", "description": "可选，客房总数"},
                },
                "required": ["room_type_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_list_users",
            "description": "查询所有用户，需要管理员权限。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_disable_user",
            "description": "禁用指定用户账号（不能禁用自己），需要管理员权限。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "用户 id"},
                    "confirm": {"type": "boolean", "description": "执行禁用前需用户明确确认，传 true 表示已确认"},
                },
                "required": ["user_id"],
            },
        },
    },
]


def get_tools(user: CurrentUser | None) -> list[dict]:
    """根据当前用户角色返回可用工具集，管理员额外获得后台管理工具。"""
    tools = list(CUSTOMER_TOOLS)
    if user is not None and user.role == UserRole.ADMIN:
        tools.extend(ADMIN_TOOLS)
    return tools


def _is_admin(user: CurrentUser | None) -> bool:
    return user is not None and user.role == UserRole.ADMIN


def _booking_to_dict(booking: Booking) -> dict:
    room = booking.room
    room_type = room.room_type if room else None
    return {
        "booking_id": booking.id,
        "room_number": room.room_number if room else None,
        "room_type": room_type.name if room_type else None,
        "check_in": str(booking.check_in),
        "check_out": str(booking.check_out),
        "total_price": float(booking.total_price),
        "status": booking.status.value,
    }


def _admin_booking_to_dict(booking: Booking) -> dict:
    data = _booking_to_dict(booking)
    data["user_id"] = booking.user_id
    data["username"] = booking.user.username if booking.user else None
    return data


async def _handle_search(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    check_in = date.fromisoformat(args["check_in"])
    check_out = date.fromisoformat(args["check_out"])
    room_type_id = args.get("room_type_id")

    required_days = (check_out - check_in).days
    if required_days <= 0:
        return {"rooms": [], "message": "离店日期必须晚于入住日期"}

    subq = (
        select(DailyRoomInventory.room_id)
        .where(
            and_(
                DailyRoomInventory.date >= check_in,
                DailyRoomInventory.date < check_out,
                DailyRoomInventory.status == InventoryStatus.AVAILABLE,
            )
        )
        .group_by(DailyRoomInventory.room_id)
        .having(func.count() == required_days)
        .subquery()
    )

    stmt = (
        select(Room)
        .options(selectinload(Room.room_type))
        .where(Room.status == RoomStatus.ACTIVE, Room.id.in_(select(subq.c.room_id)))
    )
    if room_type_id:
        stmt = stmt.where(Room.room_type_id == room_type_id)

    result = await db.execute(stmt)
    rooms = result.scalars().all()
    data = [
        {
            "room_id": room.id,
            "room_number": room.room_number,
            "room_type": room.room_type.name if room.room_type else None,
            "price_per_night": float(room.room_type.base_price) if room.room_type else None,
            "capacity": room.room_type.capacity if room.room_type else None,
        }
        for room in rooms
    ]
    return {"rooms": data}


async def _handle_create_booking(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if user is None:
        return {"error": "请先登录后再预订"}
    check_in = date.fromisoformat(args["check_in"])
    check_out = date.fromisoformat(args["check_out"])
    booking = await booking_service.create_hold_booking(
        db,
        user_id=user.user_id,
        room_id=int(args["room_id"]),
        check_in=check_in,
        check_out=check_out,
    )
    return {
        "booking_id": booking.id,
        "status": booking.status.value,
        "total_price": float(booking.total_price),
        "check_in": str(booking.check_in),
        "check_out": str(booking.check_out),
    }


async def _handle_list_bookings(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if user is None:
        return {"error": "请先登录后查看订单"}
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.room).selectinload(Room.room_type))
        .where(Booking.user_id == user.user_id)
        .order_by(Booking.created_at.desc())
    )
    bookings = result.scalars().all()
    return {"bookings": [_booking_to_dict(b) for b in bookings]}


async def _handle_cancel_booking(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if user is None:
        return {"error": "请先登录后操作"}
    await booking_service.cancel_booking(
        db,
        booking_id=int(args["booking_id"]),
        user_id=user.user_id,
    )
    return {"message": "订单已取消"}


async def _handle_confirm_payment(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if user is None:
        return {"error": "请先登录后操作"}
    booking_id = int(args["booking_id"])
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        return {"error": "订单不存在"}
    if booking.user_id != user.user_id:
        return {"error": "无权操作该订单"}
    confirmed = await booking_service.confirm_booking(db, booking_id)
    return {"booking_id": confirmed.id, "status": confirmed.status.value}


async def _handle_admin_list_bookings(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    conditions = []
    if args.get("status"):
        try:
            conditions.append(Booking.status == BookingStatus(str(args["status"])))
        except ValueError:
            return {"error": f"无效的订单状态：{args['status']}"}
    if args.get("check_in_from"):
        conditions.append(Booking.check_in >= date.fromisoformat(args["check_in_from"]))
    if args.get("check_in_to"):
        conditions.append(Booking.check_in <= date.fromisoformat(args["check_in_to"]))

    stmt = (
        select(Booking)
        .options(
            selectinload(Booking.room).selectinload(Room.room_type),
            selectinload(Booking.user),
        )
        .order_by(Booking.created_at.desc())
    )
    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await db.execute(stmt)
    bookings = result.scalars().all()
    return {"bookings": [_admin_booking_to_dict(b) for b in bookings]}


async def _handle_admin_confirm_booking(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    booking = await booking_service.confirm_booking(db, int(args["booking_id"]))
    return {"booking_id": booking.id, "status": booking.status.value}


async def _handle_admin_check_in(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    booking = await booking_service.check_in_booking(db, int(args["booking_id"]))
    return {"booking_id": booking.id, "status": booking.status.value}


async def _handle_admin_check_out(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    booking = await booking_service.check_out_booking(db, int(args["booking_id"]))
    return {"booking_id": booking.id, "status": booking.status.value}


async def _handle_admin_list_rooms(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    result = await db.execute(select(Room).options(selectinload(Room.room_type)))
    rooms = result.scalars().all()
    return {
        "rooms": [
            {
                "room_id": room.id,
                "room_number": room.room_number,
                "room_type_id": room.room_type_id,
                "room_type": room.room_type.name if room.room_type else None,
                "status": room.status.value,
            }
            for room in rooms
        ]
    }


async def _handle_admin_create_room(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    room_number = str(args["room_number"])
    room_type_id = int(args["room_type_id"])
    try:
        room_status = RoomStatus(str(args.get("status") or "active"))
    except ValueError:
        return {"error": f"无效的客房状态：{args.get('status')}"}

    room_type = await db.get(RoomType, room_type_id)
    if not room_type:
        return {"error": "房型不存在"}

    existing = await db.execute(select(Room).where(Room.room_number == room_number))
    if existing.scalar_one_or_none():
        return {"error": "房号已存在"}

    async with transaction(db):
        room = Room(room_number=room_number, room_type_id=room_type_id, status=room_status)
        db.add(room)
        await db.flush()
        await inventory_service.generate_inventory_for_room(db, room.id)
        room_type.total_rooms += 1
        room_id = room.id

    return {"room_id": room_id, "room_number": room_number, "status": room_status.value}


async def _handle_admin_update_room(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    room = await db.get(Room, int(args["room_id"]))
    if not room:
        return {"error": "客房不存在"}

    if args.get("room_number") is not None:
        room.room_number = str(args["room_number"])
    if args.get("room_type_id") is not None:
        room_type = await db.get(RoomType, int(args["room_type_id"]))
        if not room_type:
            return {"error": "房型不存在"}
        room.room_type_id = int(args["room_type_id"])
    if args.get("status") is not None:
        try:
            room.status = RoomStatus(str(args["status"]))
        except ValueError:
            return {"error": f"无效的客房状态：{args['status']}"}

    await db.commit()
    return {"room_id": room.id, "room_number": room.room_number, "status": room.status.value}


async def _handle_admin_list_room_types(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    result = await db.execute(select(RoomType))
    room_types = result.scalars().all()
    return {
        "room_types": [
            {
                "room_type_id": rt.id,
                "name": rt.name,
                "base_price": float(rt.base_price),
                "capacity": rt.capacity,
                "total_rooms": rt.total_rooms,
            }
            for rt in room_types
        ]
    }


async def _handle_admin_create_room_type(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    room_type = RoomType(
        name=str(args["name"]),
        base_price=Decimal(str(args["base_price"])),
        capacity=int(args["capacity"]),
        total_rooms=int(args.get("total_rooms") or 0),
    )
    db.add(room_type)
    await db.commit()
    await db.refresh(room_type)
    return {"room_type_id": room_type.id, "name": room_type.name}


async def _handle_admin_update_room_type(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    room_type = await db.get(RoomType, int(args["room_type_id"]))
    if not room_type:
        return {"error": "房型不存在"}

    if args.get("name") is not None:
        room_type.name = str(args["name"])
    if args.get("base_price") is not None:
        room_type.base_price = Decimal(str(args["base_price"]))
    if args.get("capacity") is not None:
        room_type.capacity = int(args["capacity"])
    if args.get("total_rooms") is not None:
        room_type.total_rooms = int(args["total_rooms"])

    await db.commit()
    await db.refresh(room_type)
    return {"room_type_id": room_type.id, "name": room_type.name}


async def _handle_admin_list_users(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {
        "users": [
            {
                "user_id": u.id,
                "username": u.username,
                "role": u.role.value,
                "is_active": u.is_active,
            }
            for u in users
        ]
    }


async def _handle_admin_disable_user(db: AsyncSession, user: CurrentUser | None, args: dict) -> dict:
    if not _is_admin(user):
        return {"error": "需要管理员权限"}
    target_id = int(args["user_id"])
    if target_id == user.user_id:
        return {"error": "不能禁用自己的账号"}
    target = await db.get(User, target_id)
    if not target:
        return {"error": "用户不存在"}
    target.is_active = False
    await db.commit()
    return {"message": f"用户 {target.username} 已被禁用"}


_HANDLERS: dict[str, Callable[[AsyncSession, CurrentUser | None, dict], Awaitable[dict]]] = {
    "search_available_rooms": _handle_search,
    "create_booking": _handle_create_booking,
    "list_my_bookings": _handle_list_bookings,
    "cancel_booking": _handle_cancel_booking,
    "confirm_payment": _handle_confirm_payment,
    "admin_list_bookings": _handle_admin_list_bookings,
    "admin_confirm_booking": _handle_admin_confirm_booking,
    "admin_check_in_booking": _handle_admin_check_in,
    "admin_check_out_booking": _handle_admin_check_out,
    "admin_list_rooms": _handle_admin_list_rooms,
    "admin_create_room": _handle_admin_create_room,
    "admin_update_room": _handle_admin_update_room,
    "admin_list_room_types": _handle_admin_list_room_types,
    "admin_create_room_type": _handle_admin_create_room_type,
    "admin_update_room_type": _handle_admin_update_room_type,
    "admin_list_users": _handle_admin_list_users,
    "admin_disable_user": _handle_admin_disable_user,
}

# 需要「用户显式确认」的敏感工具：不可逆/高危操作
SENSITIVE_TOOLS: frozenset[str] = frozenset({"admin_disable_user"})


async def execute_tool(db: AsyncSession, user: CurrentUser | None, name: str, arguments: dict) -> str:
    """Execute an agent tool and serialize its result back to the LLM."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return json.dumps({"error": f"未知工具 {name}"}, ensure_ascii=False)

    arguments = arguments or {}

    # 限流：按用户做滑动窗口限流，防止工具被高频调用
    rate_key = f"user:{user.user_id}" if user is not None else "anon"
    if not _tool_rate_limiter.allow(rate_key):
        return json.dumps({"error": "请求过于频繁，请稍后再试"}, ensure_ascii=False)

    # 敏感操作人工确认：未显式确认前拒绝执行，并记审计（标记失败）
    if name in SENSITIVE_TOOLS and arguments.get("confirm") is not True:
        result = {"error": f"敏感操作 {name} 需要用户明确确认（confirm=true）"}
        await _audit_tool_call(db, user, name, arguments, result, success=False)
        return json.dumps(result, ensure_ascii=False)

    success = True
    try:
        result = await handler(db, user, arguments)
        # 处理器返回业务错误（如越权/RBAC 拒绝）时，审计应标记为失败
        if isinstance(result, dict) and "error" in result:
            success = False
    except HTTPException as exc:
        result = {"error": exc.detail}
        success = False
    except ValueError as exc:
        result = {"error": f"参数错误：{exc}"}
        success = False
    except Exception as exc:  # 兜底，避免流式响应中途崩溃
        result = {"error": f"操作失败：{exc}"}
        success = False

    await _audit_tool_call(db, user, name, arguments, result, success)

    return json.dumps(result, ensure_ascii=False, default=str)


async def _audit_tool_call(
    db: AsyncSession,
    user: CurrentUser | None,
    name: str,
    arguments: dict,
    result: dict,
    success: bool,
) -> None:
    """记录工具调用审计日志。审计失败不应阻断工具本身的执行。"""
    try:
        db.add(
            ToolCallAuditLog(
                user_id=user.user_id if user is not None else None,
                tool_name=name,
                arguments=json.dumps(arguments, ensure_ascii=False, default=str),
                result=json.dumps(result, ensure_ascii=False, default=str)[:1024],
                success=success,
            )
        )
        await db.commit()
    except Exception:
        logger.exception("Failed to write tool call audit log")