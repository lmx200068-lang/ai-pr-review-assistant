from ..config import LLM_FALLBACK_TO_MOCK, LLM_MODEL, USE_MOCK_LLM
from ..schemas import (
    DataSource,
    ReviewFinding,
    ReviewContextPack,
    ReviewSource,
    ReviewSummary,
)
from .llm_review import run_real_llm_review
from .mock_data import (
    build_local_fallback_pending_findings,
    build_mock_findings,
    build_mock_summary,
)


def run_review_engine(
    context_pack: ReviewContextPack,
    depth: str,
    data_source: DataSource,
) -> tuple[
    ReviewSummary,
    list[ReviewFinding],
    list[ReviewFinding],
    ReviewSource,
    str | None,
    str | None,
    list[str],
]:
    if USE_MOCK_LLM:
        findings = build_mock_findings(
            context_pack.pr,
            depth,
            context_pack.changed_files,
            data_source,
        )
        summary = build_mock_summary(depth, len(findings), data_source)
        return summary, findings, [], ReviewSource.MOCK, None, None, []

    try:
        (
            summary,
            findings,
            pending_findings,
            validation_warnings,
        ) = run_real_llm_review(context_pack, depth)
        return (
            summary,
            findings,
            pending_findings,
            ReviewSource.LLM,
            LLM_MODEL,
            None,
            validation_warnings,
        )
    except Exception as exc:
        if not LLM_FALLBACK_TO_MOCK:
            raise

        error = f"{type(exc).__name__}: {exc}"
        pending_findings = build_local_fallback_pending_findings(
            context_pack.changed_files,
            error,
        )
        summary = ReviewSummary(
            verdict=(
                "LLM review failed. Local fallback only provides heuristic "
                "suggestions and no formal findings."
            ),
            score=0,
            checks_total=max(1, len(context_pack.changed_files)),
            checks_passed=0,
            estimated_review_minutes=1,
        )
        return (
            summary,
            [],
            pending_findings,
            ReviewSource.LOCAL_FALLBACK,
            LLM_MODEL or None,
            error,
            [],
        )
