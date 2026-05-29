import asyncio

from ..clients.github import fetch_github_pr_context
from ..config import USE_MOCK_GITHUB, USE_MOCK_LLM
from ..schemas import DataSource, ReviewSource, TaskStatus
from ..store import tasks, update_task
from .mock_data import build_mock_changed_files, build_mock_pr
from .review_engine import run_review_engine


async def run_review_task(task_id: str) -> None:
    try:
        update_task(
            task_id,
            status=TaskStatus.RUNNING,
            progress=20,
            message=(
                "Fetching mock pull request metadata"
                if USE_MOCK_GITHUB
                else "Fetching GitHub pull request metadata"
            ),
        )

        task = tasks[task_id]
        data_source = DataSource.MOCK
        if USE_MOCK_GITHUB:
            await asyncio.sleep(0.5)
            pr = build_mock_pr(str(task.pr_url))
            changed_files = build_mock_changed_files(pr)
        else:
            pr, changed_files = await asyncio.to_thread(
                fetch_github_pr_context,
                str(task.pr_url),
            )
            data_source = DataSource.GITHUB

        update_task(
            task_id,
            progress=48,
            data_source=data_source,
            pr=pr,
            changed_files=changed_files,
            message=(
                f"Loaded {len(changed_files)} changed files from "
                f"{data_source.value}"
            ),
        )
        await asyncio.sleep(0.5)

        update_task(
            task_id,
            progress=72,
            message=(
                "Running local mock review"
                if USE_MOCK_LLM
                else "Running LLM review"
            ),
        )

        task = tasks[task_id]
        (
            summary,
            findings,
            pending_findings,
            review_source,
            review_model,
            review_error,
        ) = await asyncio.to_thread(
            run_review_engine,
            pr,
            task.review_depth,
            changed_files,
            data_source,
        )
        update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            findings=findings,
            pending_findings=pending_findings,
            summary=summary,
            review_source=review_source,
            review_model=review_model,
            review_error=review_error,
            message=(
                "LLM review completed"
                if review_source == ReviewSource.LLM
                else "Mock review completed"
                if review_source == ReviewSource.MOCK
                else "LLM failed; fallback review completed"
            ),
        )
    except Exception as exc:
        update_task(
            task_id,
            status=TaskStatus.FAILED,
            progress=100,
            review_error=f"{type(exc).__name__}: {exc}",
            message=f"Review task failed: {exc}",
        )
