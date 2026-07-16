"""Task CRUD + authorization (ownership) tests."""

from httpx import AsyncClient


async def test_task_crud_lifecycle(client: AsyncClient, auth_headers):
    # create
    resp = await client.post(
        "/tasks", json={"title": "Write tests", "description": "pytest"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    task = resp.json()
    assert task["status"] == "todo"

    # read
    resp = await client.get(f"/tasks/{task['id']}", headers=auth_headers)
    assert resp.status_code == 200

    # update
    resp = await client.patch(
        f"/tasks/{task['id']}", json={"status": "done"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"

    # delete
    resp = await client.delete(f"/tasks/{task['id']}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.get(f"/tasks/{task['id']}", headers=auth_headers)
    assert resp.status_code == 404


async def test_list_with_status_filter_and_pagination(client: AsyncClient, auth_headers):
    for i in range(3):
        await client.post(
            "/tasks", json={"title": f"task {i}"}, headers=auth_headers
        )
    resp = await client.get("/tasks?limit=2", headers=auth_headers)
    assert len(resp.json()) == 2

    resp = await client.get("/tasks?status=done", headers=auth_headers)
    assert resp.json() == []


async def test_users_cannot_access_others_tasks(client: AsyncClient, auth_headers):
    # user A creates a task
    resp = await client.post(
        "/tasks", json={"title": "private"}, headers=auth_headers
    )
    task_id = resp.json()["id"]

    # user B logs in
    await client.post(
        "/auth/register", json={"email": "b@b.com", "password": "longenough"}
    )
    resp = await client.post(
        "/auth/login", data={"username": "b@b.com", "password": "longenough"}
    )
    headers_b = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    # B cannot read, modify, or delete A's task (404, not 403 — no oracle)
    assert (await client.get(f"/tasks/{task_id}", headers=headers_b)).status_code == 404
    assert (
        await client.patch(f"/tasks/{task_id}", json={"title": "x"}, headers=headers_b)
    ).status_code == 404
    assert (await client.delete(f"/tasks/{task_id}", headers=headers_b)).status_code == 404


async def test_validation_rejects_bad_input(client: AsyncClient, auth_headers):
    resp = await client.post("/tasks", json={"title": ""}, headers=auth_headers)
    assert resp.status_code == 422


async def test_rate_limiter_returns_429():
    """Unit-test the limiter directly with a tiny budget."""
    import pytest
    from fastapi import HTTPException

    from app.rate_limit import RateLimiter

    limiter = RateLimiter(max_requests=2, window_s=60)
    await limiter.check("1.2.3.4")
    await limiter.check("1.2.3.4")
    with pytest.raises(HTTPException) as exc:
        await limiter.check("1.2.3.4")
    assert exc.value.status_code == 429
    # other clients are unaffected
    await limiter.check("5.6.7.8")


async def test_root_serves_frontend(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "TaskFlow" in resp.text
