from datetime import datetime, timezone

from .schemas import ReviewTask


tasks: dict[str, ReviewTask] = {}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def update_task(task_id: str, **changes: object) -> None:
    task = tasks[task_id]
    data = task.model_dump()
    data.update(changes)
    data["updated_at"] = utc_now()
    tasks[task_id] = ReviewTask(**data)
