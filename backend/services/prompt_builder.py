from ..config import (
    LLM_MAX_CONTEXT_CHARS,
    LLM_MAX_PATCH_CHARS,
    LLM_MAX_REVIEW_FILES,
)
from ..schemas import ChangedFile, PullRequestInfo


def review_depth_instruction(depth: str) -> str:
    instructions = {
        "quick": (
            "Focus only on high-confidence risks according to each file's "
            "review_strategy. Return 1 to 3 findings."
        ),
        "standard": (
            "Balance correctness, documentation accuracy, configuration safety, "
            "dependency risk, and maintainability according to each file's "
            "review_strategy. Return 2 to 5 findings."
        ),
        "deep": (
            "Perform a careful review using the strategy assigned to each file. "
            "Return 3 to 8 findings."
        ),
    }
    return instructions[depth]


def review_strategy_instructions() -> str:
    return """
Use file_type and review_strategy exactly as provided for each file:
- code/code_reviewer: review bugs, security issues, performance, readability, error handling, edge cases, and test coverage.
- markdown/documentation_reviewer: review project explanation consistency, startup command correctness, environment variable documentation, security reminders, real token/API key leakage, and whether the document exaggerates features that are not implemented. Do not review Markdown as application code.
- config/config_reviewer: review configuration names, sensitive information leakage, unsafe defaults, environment separation, and deployment footguns.
- dependency/dependency_reviewer: review dependency changes, script commands, lockfile/package consistency, supply-chain/security risks, and risky install/build scripts.
- other/context_only: use only as context unless a clear security or release risk appears.

Important: README.md and docs/*.md must be reviewed with documentation_reviewer, never code_reviewer.
""".strip()


def truncate_text(value: str, limit: int) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    return value[:limit] + "\n... truncated ...", True


def format_changed_files_for_prompt(files: list[ChangedFile]) -> str:
    chunks: list[str] = []
    remaining = LLM_MAX_CONTEXT_CHARS

    for file in files[:LLM_MAX_REVIEW_FILES]:
        patch = file.patch or "(No textual patch was returned for this file.)"
        patch, patch_was_truncated = truncate_text(patch, LLM_MAX_PATCH_CHARS)
        block = (
            f"FILE: {file.filename}\n"
            f"STATUS: {file.status}\n"
            f"FILE_TYPE: {file.file_type.value}\n"
            f"REVIEW_STRATEGY: {file.review_strategy.value}\n"
            f"ADDITIONS: {file.additions}, DELETIONS: {file.deletions}, "
            f"CHANGES: {file.changes}\n"
            f"PATCH_TRUNCATED: {file.patch_truncated or patch_was_truncated}\n"
            "PATCH:\n"
            f"{patch}\n"
        )

        if len(block) > remaining:
            clipped, _ = truncate_text(block, max(500, remaining))
            chunks.append(clipped)
            break

        chunks.append(block)
        remaining -= len(block)
        if remaining <= 500:
            break

    if len(files) > LLM_MAX_REVIEW_FILES:
        chunks.append(
            f"\nNOTE: {len(files) - LLM_MAX_REVIEW_FILES} additional files were omitted."
        )

    return "\n---\n".join(chunks)


def build_review_messages(
    pr: PullRequestInfo,
    depth: str,
    files: list[ChangedFile],
) -> list[dict[str, str]]:
    system_prompt = (
        "You are a senior software engineer performing pull request review. "
        "Use only the provided PR metadata and file patches. "
        "Respect each file's file_type and review_strategy. "
        "Do not invent files, line numbers, dependencies, runtime behavior, or business context. "
        "Do not apply code review criteria to Markdown documentation files. "
        "If evidence is weak, lower the severity or omit the finding. "
        "Every formal finding must include evidence_lines copied exactly from the provided PATCH. "
        "Return strictly valid JSON. No markdown. No code fences. "
        "Write findings in Simplified Chinese. Keep file paths and identifiers unchanged."
    )
    user_prompt = f"""
Review this GitHub pull request.

PR:
- Repository: {pr.owner}/{pr.repo}
- Number: {pr.number}
- Title: {pr.title}
- Author: {pr.author}
- State: {pr.state or "unknown"}
- Source branch: {pr.source_branch}
- Target branch: {pr.target_branch}
- Additions: {pr.additions}
- Deletions: {pr.deletions}
- Changed files reported by GitHub: {pr.changed_files}

Review depth:
{review_depth_instruction(depth)}

Review strategies:
{review_strategy_instructions()}

Changed files:
{format_changed_files_for_prompt(files)}

Return this exact JSON shape:
{{
  "summary": {{
    "verdict": "one concise Chinese sentence",
    "score": 85,
    "checks_total": 10,
    "checks_passed": 8,
    "estimated_review_minutes": 1
  }},
  "findings": [
    {{
      "severity": "high",
      "file_path": "path/from/patch",
      "line": 1,
      "file_type": "code",
      "review_strategy": "code_reviewer",
      "title": "short Chinese title",
      "summary": "evidence-based Chinese explanation",
      "evidence_lines": ["+ exact changed line copied from PATCH"],
      "suggestion": "specific Chinese suggestion"
    }}
  ]
}}

Rules:
- severity must be one of "high", "medium", "low".
- file_path must match a provided changed file.
- file_type and review_strategy must match the provided file metadata for that file.
- line must be a positive line number from the new side of the patch when possible.
- evidence_lines must contain 1 to 4 exact diff lines copied from the provided PATCH, including the leading + or - when present.
- If you cannot cite exact diff evidence for a possible issue, still return it with evidence_lines: [] so the product can place it in human confirmation instead of formal findings.
- checks_total should be at least findings.length.
- checks_passed must be between 0 and checks_total.
- score is 0-100, where higher means safer to merge.
""".strip()
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
