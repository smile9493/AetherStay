"""认证接口测试：注册 / 登录 / 鉴权。"""

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