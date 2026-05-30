from ..config import LLM_MAX_CONTEXT_CHARS, LLM_MAX_PATCH_CHARS, LLM_MAX_REVIEW_FILES
from ..schemas import ChangedFile, PullRequestInfo, ReviewContextPack


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
    context_pack = ReviewContextPack(pr=pr, changed_files=files)
    return build_review_prompt(context_pack, depth)


def format_context_pack(context_pack: ReviewContextPack) -> str:
    chunks: list[str] = []
    pr = context_pack.pr
    chunks.append(
        "\n".join(
            [
                "# PR Metadata",
                f"- Repository: {pr.owner}/{pr.repo}",
                f"- Number: {pr.number}",
                f"- Title: {pr.title}",
                f"- Author: {pr.author}",
                f"- State: {pr.state or 'unknown'}",
                f"- Source branch: {pr.source_branch}",
                f"- Target branch: {pr.target_branch}",
                f"- Head SHA: {pr.head_sha or 'unknown'}",
                f"- Base SHA: {pr.base_sha or 'unknown'}",
                f"- Additions: {pr.additions}",
                f"- Deletions: {pr.deletions}",
                f"- Changed files: {pr.changed_files}",
            ]
        )
    )

    if context_pack.repository_context:
        chunks.append(
            "\n".join(
                [
                    "# Repository Context",
                    context_pack.repository_context.tree_summary,
                ]
            )
        )

    chunks.append("# Changed Files")
    contexts_by_path = {
        context.path: context for context in context_pack.changed_file_contexts
    }
    for file in context_pack.changed_files[:LLM_MAX_REVIEW_FILES]:
        context = contexts_by_path.get(file.filename)
        patch = file.patch or "(No textual patch was returned for this file.)"
        patch, patch_was_truncated = truncate_text(patch, LLM_MAX_PATCH_CHARS)
        file_chunks = [
            f"## {file.filename}",
            f"- status: {file.status}",
            f"- file_type: {file.file_type.value}",
            f"- review_strategy: {file.review_strategy.value}",
            f"- additions/deletions/changes: {file.additions}/{file.deletions}/{file.changes}",
            f"- patch_truncated: {file.patch_truncated or patch_was_truncated}",
            "### Diff Patch",
            patch,
        ]

        if context:
            if context.hunk_context and context.hunk_context.content:
                file_chunks.extend(
                    ["### Changed File Context: hunk_context", context.hunk_context.content]
                )
            if context.head_context and context.head_context.content:
                file_chunks.extend(
                    ["### Changed File Context: head_context", context.head_context.content]
                )
            if context.base_context and context.base_context.content:
                file_chunks.extend(
                    ["### Changed File Context: base_context", context.base_context.content]
                )
            if context.related_files:
                file_chunks.append("### Related Files")
                for related in context.related_files:
                    if related.skipped:
                        file_chunks.append(
                            f"- {related.path} ({related.relation}): skipped, {related.skip_reason}"
                        )
                        continue
                    file_chunks.extend(
                        [
                            f"#### {related.path} ({related.relation})",
                            related.content,
                        ]
                    )
            if context.context_warnings:
                file_chunks.extend(
                    ["### Context warnings", "\n".join(context.context_warnings)]
                )

        chunks.append("\n".join(file_chunks))

    limitations: list[str] = ["# Context Limitations"]
    limitations.extend(
        f"- {warning}" for warning in context_pack.context_warnings
    )
    if context_pack.repository_context:
        limitations.extend(
            f"- {warning}" for warning in context_pack.repository_context.warnings
        )
    if len(limitations) == 1:
        limitations.append("- No explicit context warnings.")
    chunks.append("\n".join(limitations))

    text = "\n\n".join(chunks)
    if len(text) > LLM_MAX_CONTEXT_CHARS:
        return text[:LLM_MAX_CONTEXT_CHARS] + "\n[TRUNCATED: prompt context budget reached]"
    return text


def build_review_prompt(
    context_pack: ReviewContextPack,
    review_depth: str,
) -> list[dict[str, str]]:
    system_prompt = (
        "You are a careful code review assistant. "
        "Use only the provided PR diff and Context Pack. "
        "Respect each file's file_type and review_strategy. "
        "Do not invent files, line numbers, dependencies, runtime behavior, or business context. "
        "Do not apply code review criteria to Markdown documentation files. "
        "Formal findings must include evidence_lines copied from the provided diff or context. "
        "If context is insufficient or evidence is weak, put the issue in pending_findings. "
        "Return strictly valid JSON. No markdown. No code fences. "
        "Write title, summary, and suggestion in Simplified Chinese for the UI. "
        "Also write comment_title, comment_summary, and comment_suggestion in clear English for copied GitHub comments. "
        "Keep file paths, identifiers, package names, and code symbols unchanged."
    )
    user_prompt = f"""
Review depth:
{review_depth_instruction(review_depth)}

Review strategies:
{review_strategy_instructions()}

Context Pack:
{format_context_pack(context_pack)}

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
      "suggestion": "specific Chinese suggestion",
      "comment_title": "short English issue title for GitHub comments",
      "comment_summary": "specific English explanation for GitHub comments",
      "comment_suggestion": "specific English recommendation for GitHub comments"
    }}
  ],
  "pending_findings": [
    {{
      "severity": "low",
      "file_path": "path/from/context",
      "line": 1,
      "file_type": "code",
      "review_strategy": "code_reviewer",
      "title": "short Chinese title",
      "summary": "why this needs human confirmation",
      "evidence_lines": [],
      "suggestion": "what a human should verify",
      "comment_title": "short English pending issue title",
      "comment_summary": "English explanation of why this needs human confirmation",
      "comment_suggestion": "English manual verification step"
    }}
  ]
}}

Rules:
- severity must be one of "high", "medium", "low".
- file_path must match a provided changed file or a related file.
- file_type and review_strategy must match the provided file metadata for that file.
- line must be a positive line number from the new side of the patch when possible.
- evidence_lines must contain 1 to 4 exact lines copied from the provided Diff Patch, hunk_context, head_context, base_context, or Related Files.
- If you cannot cite exact diff evidence for a possible issue, still return it with evidence_lines: [] so the product can place it in human confirmation instead of formal findings.
- comment_title, comment_summary, and comment_suggestion must be English only. Do not include Chinese text in those fields.
- Do not output generic style advice.
- Do not assign high severity to documentation-only changes unless there is a concrete security-sensitive misstatement.
- checks_total should be at least findings.length.
- checks_passed must be between 0 and checks_total.
- score is 0-100, where higher means safer to merge.
""".strip()
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
