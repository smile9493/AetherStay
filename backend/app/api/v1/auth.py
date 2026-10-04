import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.token import RefreshTokenSession
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserLogin,
    UserProfileUpdate,
    UserRegister,
    UserResponse,
)
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
    CurrentUser,
)

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: Annotated[AsyncSession, Depends(get_db)]):
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(username=data.username, password_hash=hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse, operation_id="login")
async def login(data: UserLogin, response: Response, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    access_token = create_access_token(user.id, user.username, user.role)
    refresh_token = create_refresh_token(user.id, await _create_refresh_session(db, user.id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=60 * 15,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return TokenResponse()


@router.post("/logout")
async def logout(request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_db)]):
    token = request.cookies.get("refresh_token")
    if token:
        try:
            _, jti = decode_refresh_token(token)
            await _revoke_refresh_session(db, jti)
        except (JWTError, ValueError):
            pass
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[CurrentUser, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one()
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserProfileUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one()

    if data.phone is not None:
        user.phone = data.phone
    if data.email is not None:
        user.email = data.email

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_db)]):
    """旋转刷新令牌：校验旧会话 → 吊销 → 签发新 access + refresh。"""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    try:
        user_id, jti = decode_refresh_token(token)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    new_jti = await _rotate_refresh_session(db, jti, user_id)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")

    access_token = create_access_token(user.id, user.username, user.role)
    refresh_token = create_refresh_token(user.id, new_jti)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=60 * 15,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return TokenResponse()


async def _create_refresh_session(db: AsyncSession, user_id: int) -> str:
    jti = uuid.uuid4().hex
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshTokenSession(jti=jti, user_id=user_id, expires_at=expires_at))
    await db.commit()
    return jti


async def _rotate_refresh_session(db: AsyncSession, jti: str, user_id: int) -> str:
    result = await db.execute(select(RefreshTokenSession).where(RefreshTokenSession.jti == jti))
    session = result.scalar_one_or_none()
    if session is None or session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    if session.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    if session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # 轮换：吊销旧会话，签发新会话
    session.revoked_at = datetime.now(UTC)
    new_jti = uuid.uuid4().hex
    new_expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshTokenSession(jti=new_jti, user_id=user_id, expires_at=new_expires_at))
    await db.commit()
    return new_jti


async def _revoke_refresh_session(db: AsyncSession, jti: str) -> None:
    result = await db.execute(select(RefreshTokenSession).where(RefreshTokenSession.jti == jti))
    session = result.scalar_one_or_none()
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        await db.commit()
