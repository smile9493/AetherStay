import json
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.schemas import ChatRequest
from app.agent.service import AgentError, stream_agent_events
from app.database import get_db
from app.utils.auth import CurrentUser, get_optional_current_user

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat")
async def agent_chat(
    data: ChatRequest,
    user: Annotated[CurrentUser | None, Depends(get_optional_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    messages = [m.model_dump() for m in data.messages]

    async def event_stream():
        try:
            async for event in stream_agent_events(db, user, messages):
                yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
        except AgentError as exc:
            event = {"type": "error", "message": str(exc)}
            yield f"event: error\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )