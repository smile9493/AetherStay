"""Auth utility tests — JWT token lifecycle and RoleChecker."""

from __future__ import annotations

import os

os.environ.setdefault("TESTING", "1")

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import JWTError, jwt

from app.config import get_settings
from app.models.user import UserRole
from app.utils.auth import (
    RoleChecker,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)

settings = get_settings()


def test_password_hashing():
    """Password hashing and verification round-trip."""
    password = "MySecureP@ss123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_create_access_token_success():
    """Create and decode a valid access token."""
    token = create_access_token(
        user_id=1,
        username="testuser",
        role=UserRole.CUSTOMER,
    )
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert int(payload["sub"]) == 1
    assert payload["username"] == "testuser"
    assert payload["role"] == "customer"
    assert "exp" in payload


def test_create_refresh_token():
    """Refresh token has type=refresh claim."""
    token = create_refresh_token(user_id=42)
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert int(payload["sub"]) == 42
    assert payload.get("type") == "refresh"


def test_expired_token_raises():
    """Access token with past expiration should be rejected."""
    expire = datetime.now(UTC) - timedelta(hours=1)
    from jose import jwt as _jwt

    token = _jwt.encode(
        {
            "sub": "1",
            "username": "expired_user",
            "role": "customer",
            "exp": expire,
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(JWTError):
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def test_token_with_wrong_secret_fails():
    """Token signed with different secret should be rejected."""
    token = create_access_token(
        user_id=1,
        username="testuser",
        role=UserRole.ADMIN,
    )
    with pytest.raises(JWTError):
        jwt.decode(token, "wrong-secret", algorithms=[settings.ALGORITHM])


@pytest.mark.asyncio
async def test_role_checker_customer_denied():
    """Customer role should be denied for admin-only routes."""
    checker = RoleChecker([UserRole.ADMIN])

    class MockCurrentUser:
        def __init__(self):
            self.user_id = 1
            self.username = "customer"
            self.role = UserRole.CUSTOMER

    with pytest.raises(HTTPException) as exc:
        await checker(MockCurrentUser())
    assert exc.value.status_code == 403
    assert "Insufficient" in exc.value.detail or "insufficient" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_role_checker_admin_allowed():
    """Admin role should pass through admin-only checker."""
    checker = RoleChecker([UserRole.ADMIN])

    class MockCurrentUser:
        def __init__(self):
            self.user_id = 2
            self.username = "admin_user"
            self.role = UserRole.ADMIN

    result = await checker(MockCurrentUser())
    assert result.role == UserRole.ADMIN
    assert result.username == "admin_user"


@pytest.mark.asyncio
async def test_role_checker_multiple_allowed_roles():
    """Checker with multiple allowed roles should accept any of them."""
    checker = RoleChecker([UserRole.ADMIN, UserRole.CUSTOMER])

    class MockCustomer:
        def __init__(self):
            self.user_id = 1
            self.username = "cust"
            self.role = UserRole.CUSTOMER

    class MockAdmin:
        def __init__(self):
            self.user_id = 2
            self.username = "adm"
            self.role = UserRole.ADMIN

    assert (await checker(MockCustomer())).role == UserRole.CUSTOMER
    assert (await checker(MockAdmin())).role == UserRole.ADMIN
