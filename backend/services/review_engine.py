from ..config import LLM_FALLBACK_TO_MOCK, LLM_MODEL, USE_MOCK_LLM
from ..schemas import (
    ChangedFile,
    DataSource,
    PullRequestInfo,
    ReviewFinding,
    ReviewSource,
    ReviewSummary,
)
from .llm_review import run_real_llm_review
from .mock_data import build_mock_findings, build_mock_summary


def run_review_engine(
    pr: PullRequestInfo,
    depth: str,
    files: list[ChangedFile],
    data_source: DataSource,
) -> tuple[
    ReviewSummary,
    list[ReviewFinding],
    list[ReviewFinding],
    ReviewSource,
    str | None,
    str | None,
]:
    if USE_MOCK_LLM:
        findings = build_mock_findings(pr, depth, files, data_source)
        summary = build_mock_summary(depth, len(findings), data_source)
        return summary, findings, [], ReviewSource.MOCK, None, None

    try:
        summary, findings, pending_findings = run_real_llm_review(pr, depth, files)
        return summary, findings, pending_findings, ReviewSource.LLM, LLM_MODEL, None
    except Exception as exc:
        if not LLM_FALLBACK_TO_MOCK:
            raise

        findings = build_mock_findings(pr, depth, files, data_source)
        summary = build_mock_summary(depth, len(findings), data_source)
        error = f"{type(exc).__name__}: {exc}"
        summary.verdict = (
            "LLM review failed, so this task fell back to local mock review. "
            f"Original error: {error[:180]}"
        )
        return summary, findings, [], ReviewSource.FALLBACK, LLM_MODEL or None, error
