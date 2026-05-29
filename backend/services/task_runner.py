import asyncio

from ..clients.github import fetch_github_pr_context
from ..config import USE_MOCK_GITHUB, USE_MOCK_LLM
from ..schemas import DataSource, ReviewSource, TaskStatus
from ..store import tasks, update_task
from .context_collector import (
    ContextCollector,
    context_summary_from_pack,
    minimal_context_pack_from_pr_and_changed_files,
)
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
            progress=40,
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
            progress=55,
            message=(
                "Building diff-only context pack"
                if USE_MOCK_GITHUB
                else "Building GitHub Context Pack"
            ),
        )
        try:
            if USE_MOCK_GITHUB:
                context_pack = minimal_context_pack_from_pr_and_changed_files(
                    pr,
                    changed_files,
                    "Mock GitHub mode uses diff-only context pack.",
                )
            else:
                context_pack = await asyncio.to_thread(
                    ContextCollector().collect,
                    pr.owner,
                    pr.repo,
                    pr,
                    changed_files,
                    tasks[task_id].review_depth,
                )
        except Exception as exc:
            context_pack = minimal_context_pack_from_pr_and_changed_files(
                pr,
                changed_files,
                f"Context collection failed; fallback to diff-only review: {exc}",
            )

        context_summary = context_summary_from_pack(context_pack)
        update_task(
            task_id,
            progress=75,
            context_summary=context_summary,
            message=(
                "Running local mock review"
                if USE_MOCK_LLM
                else "Running LLM review with Context Pack"
            ),
        )

        update_task(
            task_id,
            progress=90,
            message=(
                "Running local mock review"
                if USE_MOCK_LLM
                else "Validating LLM findings evidence"
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
            review_warnings,
        ) = await asyncio.to_thread(
            run_review_engine,
            context_pack,
            task.review_depth,
            data_source,
        )
        if review_warnings:
            context_summary["warnings"] = sorted(
                set(context_summary.get("warnings", []) + review_warnings)
            )
        update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            findings=findings,
            pending_findings=pending_findings,
            context_summary=context_summary,
            summary=summary,
            review_source=review_source,
            review_model=review_model,
            review_error=review_error,
            message=(
                "LLM review completed"
                if review_source == ReviewSource.LLM
                else "Mock review completed"
                if review_source == ReviewSource.MOCK
                else "LLM failed; local fallback suggestions prepared"
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
