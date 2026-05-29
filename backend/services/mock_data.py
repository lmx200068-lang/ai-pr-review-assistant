import re

from ..schemas import (
    ChangedFile,
    DataSource,
    PullRequestInfo,
    ReviewFinding,
    ReviewStrategy,
    ReviewSummary,
    Severity,
)
from .file_classifier import make_changed_file
from .github_url import parse_github_pr_url


def build_mock_pr(pr_url: str) -> PullRequestInfo:
    parsed = parse_github_pr_url(pr_url)
    owner, repo, number = parsed if parsed else ("demo-org", "demo-repo", 128)
    changed_files = 7 + (number % 4)

    return PullRequestInfo(
        owner=owner,
        repo=repo,
        number=number,
        title=f"Improve review workflow for {repo}",
        source_branch=f"feature/pr-review-{number}",
        target_branch="main",
        author=f"{owner}-contributor",
        additions=180 + number % 90,
        deletions=34 + number % 28,
        changed_files=changed_files,
        html_url=pr_url,
        state="open",
    )


def build_mock_changed_files(pr: PullRequestInfo) -> list[ChangedFile]:
    return [
        make_changed_file(
            filename="backend/services/review_runner.py",
            status="modified",
            additions=74,
            deletions=18,
            changes=92,
            patch="@@ -64,6 +64,12 @@\n+persist_review_result(task_id, result)",
        ),
        make_changed_file(
            filename="frontend/src/features/review/ReviewPanel.jsx",
            status="modified",
            additions=68,
            deletions=14,
            changes=82,
            patch="@@ -112,6 +112,10 @@\n+renderEmptyReviewState(task)",
        ),
        make_changed_file(
            filename="README.md",
            status="added",
            additions=max(20, pr.changed_files * 4),
            deletions=0,
            changes=max(20, pr.changed_files * 4),
            patch="@@ -1,2 +1,8 @@\n # Demo project\n+\n+## Setup\n+Run `npm run dev` after configuring `.env.example`.\n+Do not commit real API keys.",
        ),
    ]


def build_mock_summary(
    depth: str,
    findings_count: int,
    data_source: DataSource,
) -> ReviewSummary:
    score_by_depth = {
        "quick": 83,
        "standard": 88,
        "deep": 91,
    }
    minutes_by_depth = {
        "quick": 3,
        "standard": 6,
        "deep": 11,
    }

    verdict = (
        "GitHub PR fetched successfully. Review findings are mock heuristics for now."
        if data_source == DataSource.GITHUB
        else "Mock review completed. Ready for human follow-up on flagged items."
    )

    return ReviewSummary(
        verdict=verdict,
        score=score_by_depth[depth] - findings_count,
        checks_total=12,
        checks_passed=12 - findings_count,
        estimated_review_minutes=minutes_by_depth[depth],
    )


def first_added_line(file: ChangedFile | None) -> int:
    if not file or not file.patch:
        return 1

    match = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)", file.patch)
    if not match:
        return 1
    return int(match.group(1))


def file_at(files: list[ChangedFile], index: int, fallback: str) -> ChangedFile:
    if len(files) > index:
        return files[index]
    return make_changed_file(
        filename=fallback,
        status="modified",
        additions=1,
        deletions=0,
        changes=1,
    )


def evidence_lines_for_file(file: ChangedFile) -> list[str]:
    if not file.patch:
        return []

    evidence_lines: list[str] = []
    for line in file.patch.splitlines():
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith(("+", "-")):
            evidence_lines.append(line)
        if len(evidence_lines) >= 4:
            break

    return evidence_lines


def build_strategy_mock_finding(
    file: ChangedFile,
    finding_id: str,
    severity: Severity,
    data_source: DataSource,
) -> ReviewFinding:
    source_note = (
        "This fallback finding uses real GitHub file metadata, but the review text is a local strategy-specific heuristic."
        if data_source == DataSource.GITHUB
        else "This is a local strategy-specific mock review finding."
    )

    strategy_templates = {
        ReviewStrategy.CODE: (
            "Code path should confirm state transitions and error handling",
            (
                f"{source_note} For code files, review should focus on bugs, security, "
                "performance, readability, edge cases, and missing tests."
            ),
            "Verify the changed logic with focused tests and keep status updates after durable result persistence.",
        ),
        ReviewStrategy.DOCUMENTATION: (
            "Documentation should match implemented behavior",
            (
                f"{source_note} For Markdown files, review should check startup commands, "
                "environment variable descriptions, safety reminders, token leakage, and claims about unfinished features."
            ),
            "Ensure README/docs describe only implemented behavior, include correct commands, and never expose real API keys.",
        ),
        ReviewStrategy.CONFIG: (
            "Configuration defaults should be explicit and safe",
            (
                f"{source_note} For config files, review should check naming consistency, "
                "secret exposure, unsafe defaults, and environment-specific behavior."
            ),
            "Prefer safe defaults, placeholders for secrets, and clear names for deployment-sensitive settings.",
        ),
        ReviewStrategy.DEPENDENCY: (
            "Dependency changes should be reviewed for supply-chain and script risk",
            (
                f"{source_note} For dependency files, review should check package changes, "
                "lockfile consistency, install/build scripts, and known security-sensitive changes."
            ),
            "Confirm dependency intent, lockfile consistency, and whether new scripts or packages introduce risk.",
        ),
        ReviewStrategy.CONTEXT: (
            "Non-code asset should be used as supporting context",
            (
                f"{source_note} This file is not code, documentation, config, or dependency metadata; "
                "only clear release or security risks should be flagged."
            ),
            "Use this change as context unless it clearly affects user-facing behavior or release safety.",
        ),
    }
    title, summary, suggestion = strategy_templates[file.review_strategy]
    return ReviewFinding(
        id=finding_id,
        severity=severity,
        file_path=file.filename,
        line=first_added_line(file),
        file_type=file.file_type,
        review_strategy=file.review_strategy,
        title=title,
        summary=summary,
        evidence_lines=evidence_lines_for_file(file),
        suggestion=suggestion,
    )


def build_mock_findings(
    pr: PullRequestInfo,
    depth: str,
    files: list[ChangedFile],
    data_source: DataSource,
) -> list[ReviewFinding]:
    primary_file = file_at(files, 0, "backend/services/review_runner.py")
    secondary_file = file_at(files, 1, "frontend/src/features/review/ReviewPanel.jsx")
    contract_file = file_at(files, 2, "docs/review-contract.md")
    findings = [
        build_strategy_mock_finding(
            primary_file,
            "mock-finding-1",
            Severity.HIGH,
            data_source,
        ),
        build_strategy_mock_finding(
            secondary_file,
            "mock-finding-2",
            Severity.MEDIUM,
            data_source,
        ),
        build_strategy_mock_finding(
            contract_file,
            "mock-finding-3",
            Severity.LOW,
            data_source,
        ),
    ]

    if depth == "quick":
        return findings[:2]

    if depth == "deep":
        deep_file = file_at(files, 3, f"{pr.repo}/security/auth_guard.py")
        return findings + [
            build_strategy_mock_finding(
                deep_file,
                "mock-finding-4",
                Severity.MEDIUM,
                data_source,
            )
        ]

    return findings


def build_local_fallback_pending_findings(
    files: list[ChangedFile],
    error: str,
    max_items: int = 4,
) -> list[ReviewFinding]:
    pending_findings: list[ReviewFinding] = []
    seen: set[tuple[str, str, str]] = set()

    for index, file in enumerate(files[:max_items]):
        title = "Heuristic review suggestion"
        summary = (
            "LLM review failed. This is a local heuristic suggestion based on "
            "file metadata and diff size, not a confirmed AI finding."
        )
        evidence = "No validated LLM evidence available."
        key = (file.filename, title, evidence)
        if key in seen:
            continue
        seen.add(key)
        pending_findings.append(
            ReviewFinding(
                id=f"local-fallback-{index + 1}",
                severity=Severity.MEDIUM,
                file_path=file.filename,
                line=None,
                file_type=file.file_type,
                review_strategy=file.review_strategy,
                title=title,
                summary=summary,
                evidence_lines=[],
                suggestion=(
                    "Manually review this changed file. "
                    f"Original LLM error: {error[:160]}"
                ),
            )
        )

    return pending_findings
