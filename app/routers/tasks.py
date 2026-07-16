"""Task CRUD endpoints — every route requires a valid JWT.

Authorization model: users can only see and modify their own tasks;
ownership is enforced in the query itself, so a valid token for user A
can never read or mutate user B's rows (no IDOR).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_session
from ..models import Task, TaskStatus, User
from ..schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _get_owned_task(
    task_id: int, user: User, session: AsyncSession
) -> Task:
    task = await session.scalar(
        select(Task).where(Task.id == task_id, Task.owner_id == user.id)
    )
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Task:
    task = Task(title=payload.title, description=payload.description, owner_id=user.id)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Task]:
    query = select(Task).where(Task.owner_id == user.id)
    if status_filter is not None:
        query = query.where(Task.status == status_filter)
    query = query.order_by(Task.created_at.desc()).limit(limit).offset(offset)
    return list((await session.scalars(query)).all())


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Task:
    return await _get_owned_task(task_id, user, session)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Task:
    task = await _get_owned_task(task_id, user, session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    task = await _get_owned_task(task_id, user, session)
    await session.delete(task)
    await session.commit()
