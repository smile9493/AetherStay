import json
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import execute_tool, get_tools
from app.config import get_settings
from app.utils.auth import CurrentUser

settings = get_settings()

_CST = timezone(timedelta(hours=8))  # 部署所在时区，为 LLM 提供"今天"的日期


class AgentError(Exception):
    """Agent 运行期错误，将作为 SSE error 事件返回给前端。"""


def build_system_prompt(user: CurrentUser | None) -> str:
    today = datetime.now(_CST).date()
    weekday = "一二三四五六日"[today.weekday()]
    prompt = (
        "你是 AetherStay 酒店预订管理系统的智能助手。"
        f"今天是 {today}（周{weekday}）。\n"
        "你可以通过调用工具完成：查询可用客房、创建预订、查看我的订单、取消订单、模拟支付。\n"
    )
    if user is not None and user.role.value == "admin":
        prompt += (
            "当前用户是管理员，还可用 admin_* 工具完成：全局订单查询/确认/入住/退房、"
            "客房与房型的增改查、用户列表与禁用。\n"
        )
    prompt += (
        "请遵守以下规则：\n"
        "1. 日期格式为 YYYY-MM-DD，入住在前、离店在后。\n"
        "2. 预订、查看订单、取消、支付都需要用户登录；若用户未登录，请提示其先登录。\n"
        "3. 创建预订前，先与用户确认入住/离店日期，并以 search_available_rooms 返回的 room_id 为准下单，"
        "不要凭空编造房间号。\n"
        "4. 金额单位为人民币（元）。\n"
        "5. 全程使用中文回答（包含调用工具前的过渡说明），不要输出英文；必要时以列表形式呈现结果。\n"
        "6. 执行 admin_disable_user 禁用用户前，必须先向用户明确确认，且仅当用户同意后才携带 confirm=true 调用。"
    )
    return prompt


async def _run_assistant_turn(
    client: httpx.AsyncClient,
    conversation: list[dict],
    tools: list[dict],
) -> AsyncIterator[dict]:
    """向 LLM 流式请求一轮回复，产出 text / tool_call 事件和 __turn_end__ 哨兵。"""
    url = settings.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.LLM_MODEL,
        "messages": conversation,
        "tools": tools,
        "stream": True,
        "temperature": settings.LLM_TEMPERATURE,
    }

    tool_acc: dict[int, dict] = {}
    finish_reason = None

    async with client.stream("POST", url, json=payload, headers=headers) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            raise AgentError(f"LLM 请求失败（{resp.status_code}）：{body.decode()[:300]}")

        async for line in resp.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            data_str = line[len("data:"):].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            for choice in chunk.get("choices", []):
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if content:
                    yield {"type": "text", "content": content}
                for tc in delta.get("tool_calls") or []:
                    idx = tc.get("index", 0)
                    entry = tool_acc.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                    if tc.get("id"):
                        entry["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        entry["name"] = fn["name"]
                    if fn.get("arguments"):
                        entry["arguments"] += fn["arguments"]

    if finish_reason == "tool_calls":
        for idx in sorted(tool_acc):
            entry = tool_acc[idx]
            try:
                args = json.loads(entry["arguments"]) if entry["arguments"] else {}
            except json.JSONDecodeError:
                args = {}
            yield {
                "type": "tool_call",
                "id": entry["id"],
                "name": entry["name"],
                "arguments": args,
            }

    yield {"type": "__turn_end__", "has_tool_calls": finish_reason == "tool_calls"}


async def stream_agent_events(
    db: AsyncSession,
    user: CurrentUser | None,
    messages: list[dict],
) -> AsyncIterator[dict]:
    """运行 agent 循环，产出 SSE 事件（text / tool_call / tool_result / error）。"""
    if not settings.LLM_API_KEY:
        yield {"type": "error", "message": "未配置 LLM_API_KEY，请在 .env 中填写后再使用智能助手"}
        return

    conversation = [{"role": "system", "content": build_system_prompt(user)}, *messages]
    tools = get_tools(user)

    timeout = httpx.Timeout(settings.LLM_TIMEOUT_SECONDS, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for _ in range(settings.LLM_MAX_TOOL_ITERATIONS):
            tool_calls: list[dict] = []
            ended_with_tools = False

            async for event in _run_assistant_turn(client, conversation, tools):
                if event["type"] == "text":
                    yield event
                elif event["type"] == "tool_call":
                    tool_calls.append(event)
                    yield event
                elif event["type"] == "__turn_end__":
                    ended_with_tools = event["has_tool_calls"]

            if not ended_with_tools:
                return

            conversation.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )
            for tc in tool_calls:
                result = await execute_tool(db, user, tc["name"], tc["arguments"])
                yield {"type": "tool_result", "name": tc["name"], "result": result}
                conversation.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result}
                )

        yield {"type": "error", "message": "操作步骤过多，请重新描述需求"}