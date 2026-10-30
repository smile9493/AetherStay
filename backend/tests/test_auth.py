"""认证接口测试：注册 / 登录 / 鉴权 / 刷新令牌轮换 / 登出。"""

from app.database import async_session_factory
from app.models.token import RefreshTokenSession
from app.utils.auth import decode_refresh_token
from tests.conftest import login_user, register_and_login, register_user


async def test_register_success(client):
    resp = await register_user(client, "alice")
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "alice"
    assert body["role"] == "customer"


async def test_register_duplicate_conflict(client):
    await register_user(client, "bob")
    resp = await register_user(client, "bob")
    assert resp.status_code == 409


async def test_register_short_password_rejected(client):
    resp = await register_user(client, "carol", password="123")
    assert resp.status_code == 422


async def test_login_success_sets_cookie(client):
    await register_user(client, "dave")
    resp = await login_user(client, "dave")
    assert resp.status_code == 200
    assert "access_token" in resp.cookies


async def test_login_wrong_password_unauthorized(client):
    await register_user(client, "erin")
    resp = await login_user(client, "erin", password="wrong-pass")
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(client):
    await register_user(client, "frank")
    await login_user(client, "frank")
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "frank"


async def test_refresh_rotates_and_revokes_old_session(client):
    """刷新令牌轮换：签发新 refresh，并吊销旧会话。"""
    await register_user(client, "refresh_user")
    login_resp = await login_user(client, "refresh_user")
    old_refresh = login_resp.cookies["refresh_token"]
    old_jti = decode_refresh_token(old_refresh)[1]

    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    new_refresh = resp.cookies["refresh_token"]
    assert new_refresh and new_refresh != old_refresh

    async with async_session_factory() as session:
        old_session = await session.get(RefreshTokenSession, old_jti)
        assert old_session is not None
        assert old_session.revoked_at is not None


async def test_refresh_requires_token(client):
    """未携带刷新令牌时刷新失败。"""
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


async def test_refresh_rejects_revoked_token(client):
    """重用已吊销的刷新令牌应返回 401。"""
    await register_user(client, "reuse_user")
    login_resp = await login_user(client, "reuse_user")
    old_refresh = login_resp.cookies["refresh_token"]

    assert (await client.post("/api/v1/auth/refresh")).status_code == 200

    client.cookies.clear()
    reused = await client.post(
        "/api/v1/auth/refresh", cookies={"refresh_token": old_refresh}
    )
    assert reused.status_code == 401


async def test_logout_revokes_refresh_session(client):
    """登出吊销刷新令牌会话。"""
    await register_user(client, "logout_user")
    login_resp = await login_user(client, "logout_user")
    old_refresh = login_resp.cookies["refresh_token"]
    old_jti = decode_refresh_token(old_refresh)[1]

    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    async with async_session_factory() as session:
        old_session = await session.get(RefreshTokenSession, old_jti)
        assert old_session is not None
        assert old_session.revoked_at is not None