from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..config import LLM_MODEL, USE_MOCK_GITHUB, USE_MOCK_LLM
from ..schemas import (
    DataSource,
    ReviewSource,
    ReviewTask,
    ReviewTaskCreate,
    TaskStatus,
)
from ..services.task_runner import run_review_task
from ..store import tasks, utc_now


router = APIRouter(prefix="/api/review-tasks")


@router.post("", response_model=ReviewTask, status_code=201)
async def create_review_task(
    payload: ReviewTaskCreate,
    background_tasks: BackgroundTasks,
) -> ReviewTask:
    task_id = str(uuid4())
    now = utc_now()
    task = ReviewTask(
        id=task_id,
        status=TaskStatus.QUEUED,
        progress=0,
        pr_url=payload.pr_url,
        review_depth=payload.review_depth,
        data_source=DataSource.MOCK if USE_MOCK_GITHUB else DataSource.GITHUB,
        review_source=ReviewSource.MOCK if USE_MOCK_LLM else None,
        review_model=None if USE_MOCK_LLM else LLM_MODEL or None,
        created_at=now,
        updated_at=now,
        message="Review task queued",
    )
    tasks[task_id] = task
    background_tasks.add_task(run_review_task, task_id)
    return task


@router.get("/{task_id}", response_model=ReviewTask)
async def get_review_task(task_id: str) -> ReviewTask:
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")
    return task


@router.get("", response_model=list[ReviewTask])
async def list_review_tasks() -> list[ReviewTask]:
    return sorted(tasks.values(), key=lambda task: task.created_at, reverse=True)
