"""Auth flow tests: registration, login, token validation, hashing."""

from httpx import AsyncClient

from app.auth import hash_password, verify_password


def test_password_hashing_roundtrip():
    stored = hash_password("hunter2-but-longer")
    assert stored != "hunter2-but-longer"          # never plaintext
    assert verify_password("hunter2-but-longer", stored)
    assert not verify_password("wrong-password", stored)


def test_hashes_are_salted():
    assert hash_password("same-pass") != hash_password("same-pass")


async def test_register_and_login(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "a@b.com", "password": "longenough"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@b.com"
    assert "hashed_password" not in body           # no secret leakage

    resp = await client.post(
        "/auth/login", data={"username": "a@b.com", "password": "longenough"}
    )
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


async def test_duplicate_email_rejected(client: AsyncClient):
    payload = {"email": "dup@b.com", "password": "longenough"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 409


async def test_short_password_rejected(client: AsyncClient):
    resp = await client.post(
        "/auth/register", json={"email": "a@b.com", "password": "short"}
    )
    assert resp.status_code == 422                 # pydantic validation


async def test_wrong_password_rejected(client: AsyncClient):
    await client.post(
        "/auth/register", json={"email": "a@b.com", "password": "longenough"}
    )
    resp = await client.post(
        "/auth/login", data={"username": "a@b.com", "password": "wrong-pass"}
    )
    assert resp.status_code == 401


async def test_protected_route_requires_token(client: AsyncClient):
    resp = await client.get("/tasks")
    assert resp.status_code == 401


async def test_garbage_token_rejected(client: AsyncClient):
    resp = await client.get(
        "/tasks", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert resp.status_code == 401
