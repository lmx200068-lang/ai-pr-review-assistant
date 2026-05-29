from ..clients.github import GitHubClient
from ..config import (
    CONTEXT_ENABLE,
    CONTEXT_HUNK_AFTER_LINES,
    CONTEXT_HUNK_BEFORE_LINES,
    CONTEXT_MAX_CHANGED_FILES_DETAILED,
    CONTEXT_MAX_FILE_CHARS,
    CONTEXT_MAX_HUNK_CONTEXT_CHARS,
    CONTEXT_MAX_RELATED_FILE_CHARS,
    CONTEXT_MAX_RELATED_FILES,
    CONTEXT_MAX_TREE_ITEMS,
    CONTEXT_SKIP_BINARY,
    CONTEXT_SKIP_LARGE_PATCH_CHARS,
    CONTEXT_SKIP_LOCK_FILES,
)
from ..schemas import (
    ChangedFile,
    ChangedFileContext,
    FileContentContext,
    PullRequestInfo,
    RelatedFileContext,
    RepositoryContext,
    ReviewContextPack,
)
from .context_budgeter import ContextBudgeter
from .context_ranker import LOCK_SUFFIXES, score_changed_file
from .diff_context import parse_patch_hunks, slice_context_by_hunks
from .related_file_finder import find_related_files
from .repo_tree_summarizer import summarize_repo_tree


def minimal_context_pack_from_pr_and_changed_files(
    pr_info: PullRequestInfo,
    changed_files: list[ChangedFile],
    warning: str | None = None,
) -> ReviewContextPack:
    warnings = [warning] if warning else []
    return ReviewContextPack(
        pr=pr_info,
        changed_files=changed_files,
        changed_file_contexts=[
            ChangedFileContext(
                path=file.filename,
                file_type=file.file_type.value,
                review_strategy=file.review_strategy.value,
                patch=file.patch,
            )
            for file in changed_files
        ],
        repository_context=RepositoryContext(
            tree_summary="Repository tree summary: unavailable.",
            warnings=warnings,
        ),
        context_warnings=warnings,
    )


def context_summary_from_pack(context_pack: ReviewContextPack) -> dict[str, object]:
    changed_context_files = 0
    related_files = 0
    truncated_files: list[str] = []
    skipped_files: list[str] = []
    warnings = list(context_pack.context_warnings)
    used_chars = 0
    max_chars = 0
    visible_warnings: list[str] = []
    for warning in warnings:
        if warning.startswith("__budget_used_chars__="):
            used_chars = int(warning.split("=", 1)[1])
        elif warning.startswith("__budget_max_chars__="):
            max_chars = int(warning.split("=", 1)[1])
        else:
            visible_warnings.append(warning)
    warnings = visible_warnings

    for context in context_pack.changed_file_contexts:
        contexts = [
            context.head_context,
            context.base_context,
            context.hunk_context,
        ]
        if any(item and item.content and not item.skipped for item in contexts):
            changed_context_files += 1
        for item in contexts:
            if item and item.truncated:
                truncated_files.append(f"{context.path}:{item.source}")
            if item and item.skipped:
                skipped_files.append(f"{context.path}:{item.source}")
        related_files += len(
            [related for related in context.related_files if not related.skipped]
        )
        for related in context.related_files:
            if related.truncated:
                truncated_files.append(f"{related.path}:related")
            if related.skipped:
                skipped_files.append(f"{related.path}:related")
        warnings.extend(context.context_warnings)

    repository_context = context_pack.repository_context
    if repository_context:
        warnings.extend(repository_context.warnings)

    return {
        "enabled": CONTEXT_ENABLE,
        "changed_context_files": changed_context_files,
        "related_files": related_files,
        "repo_tree_loaded": bool(
            repository_context and repository_context.key_files
        ),
        "used_chars": used_chars,
        "max_chars": max_chars,
        "truncated_files": sorted(set(truncated_files)),
        "skipped_files": sorted(set(skipped_files)),
        "warnings": sorted(set(warnings)),
    }


class ContextCollector:
    def __init__(
        self,
        github_client: GitHubClient | None = None,
        budgeter: ContextBudgeter | None = None,
    ) -> None:
        self.github_client = github_client or GitHubClient()
        self.budgeter = budgeter or ContextBudgeter()

    def collect(
        self,
        owner: str,
        repo: str,
        pr_info: PullRequestInfo,
        changed_files: list[ChangedFile],
        review_depth: str,
    ) -> ReviewContextPack:
        if not CONTEXT_ENABLE:
            return minimal_context_pack_from_pr_and_changed_files(
                pr_info,
                changed_files,
                "Context collection disabled by CONTEXT_ENABLE=false.",
            )

        context_warnings: list[str] = []
        head_ref = pr_info.head_sha or pr_info.source_branch
        base_ref = pr_info.base_sha or pr_info.target_branch

        tree_items = self.github_client.get_repo_tree(owner, repo, head_ref)
        repository_context = summarize_repo_tree(tree_items, CONTEXT_MAX_TREE_ITEMS)
        if self.github_client.last_tree_truncated:
            repository_context.truncated = True
            repository_context.warnings.append("GitHub repo tree response was truncated.")
        context_warnings.extend(self.github_client.warnings)
        context_warnings.extend(self.budgeter.warnings)
        repo_tree_paths = [str(item.get("path", "")) for item in tree_items]
        if not repo_tree_paths:
            repo_tree_paths = [file.filename for file in changed_files]

        detailed_files = self.select_detailed_files(changed_files, review_depth)
        detailed_paths = {file.filename for file in detailed_files}
        changed_file_contexts: list[ChangedFileContext] = []
        related_seen: set[str] = set()

        for file in changed_files:
            context = ChangedFileContext(
                path=file.filename,
                file_type=file.file_type.value,
                review_strategy=file.review_strategy.value,
                patch=file.patch,
            )
            if file.filename in detailed_paths:
                self.enrich_changed_file_context(
                    owner,
                    repo,
                    file,
                    context,
                    head_ref,
                    base_ref,
                    repo_tree_paths,
                    review_depth,
                    related_seen,
                )
            changed_file_contexts.append(context)

        context_warnings.extend(self.budgeter.warnings)
        context_warnings.extend(self.github_client.warnings)
        context_pack = ReviewContextPack(
            pr=pr_info,
            changed_files=changed_files,
            changed_file_contexts=changed_file_contexts,
            repository_context=repository_context,
            context_warnings=sorted(set(context_warnings)),
        )
        context_pack.context_warnings.extend(
            [
                f"__budget_used_chars__={self.budgeter.used_chars}",
                f"__budget_max_chars__={self.budgeter.max_total_chars}",
            ]
        )
        return context_pack

    def select_detailed_files(
        self,
        changed_files: list[ChangedFile],
        review_depth: str,
    ) -> list[ChangedFile]:
        if review_depth == "quick":
            return []

        max_files = CONTEXT_MAX_CHANGED_FILES_DETAILED
        if review_depth == "standard":
            max_files = min(max_files, 5)

        scored_files = sorted(
            changed_files,
            key=score_changed_file,
            reverse=True,
        )
        return scored_files[:max_files]

    def should_skip_detailed_context(self, file: ChangedFile) -> str | None:
        filename = file.filename.lower()
        if CONTEXT_SKIP_LOCK_FILES and filename.endswith(LOCK_SUFFIXES):
            return "lock file skipped by context policy"
        if file.patch and len(file.patch) > CONTEXT_SKIP_LARGE_PATCH_CHARS:
            return "large patch skipped by context policy"
        return None

    def add_file_context(
        self,
        path: str,
        ref: str,
        source: str,
        content: str | None,
        max_chars: int,
    ) -> FileContentContext:
        if content is None:
            return FileContentContext(
                path=path,
                ref=ref,
                source=source,
                skipped=True,
                skip_reason="content unavailable",
            )
        if CONTEXT_SKIP_BINARY and "\x00" in content:
            return FileContentContext(
                path=path,
                ref=ref,
                source=source,
                skipped=True,
                skip_reason="binary-like content skipped",
            )

        trimmed, truncated = self.budgeter.trim(content, max_chars, f"{path}:{source}")
        if not self.budgeter.reserve(trimmed, f"{path}:{source}"):
            return FileContentContext(
                path=path,
                ref=ref,
                source=source,
                skipped=True,
                skip_reason="context budget exhausted",
            )

        return FileContentContext(
            path=path,
            ref=ref,
            source=source,
            content=trimmed,
            truncated=truncated,
        )

    def add_related_context(
        self,
        path: str,
        relation: str,
        content: str | None,
    ) -> RelatedFileContext:
        if content is None:
            return RelatedFileContext(
                path=path,
                relation=relation,
                skipped=True,
                skip_reason="content unavailable",
            )
        if CONTEXT_SKIP_BINARY and "\x00" in content:
            return RelatedFileContext(
                path=path,
                relation=relation,
                skipped=True,
                skip_reason="binary-like content skipped",
            )

        trimmed, truncated = self.budgeter.trim(
            content,
            CONTEXT_MAX_RELATED_FILE_CHARS,
            f"{path}:related",
        )
        if not self.budgeter.reserve(trimmed, f"{path}:related"):
            return RelatedFileContext(
                path=path,
                relation=relation,
                skipped=True,
                skip_reason="context budget exhausted",
            )
        return RelatedFileContext(
            path=path,
            relation=relation,
            content=trimmed,
            truncated=truncated,
        )

    def enrich_changed_file_context(
        self,
        owner: str,
        repo: str,
        file: ChangedFile,
        context: ChangedFileContext,
        head_ref: str,
        base_ref: str,
        repo_tree_paths: list[str],
        review_depth: str,
        related_seen: set[str],
    ) -> None:
        skip_reason = self.should_skip_detailed_context(file)
        if skip_reason:
            context.context_warnings.append(f"{file.filename}: {skip_reason}")
            return

        head_content: str | None = None
        base_content: str | None = None
        base_path = file.previous_filename or file.filename
        full_file_contexts: list[tuple[str, str, str, str | None]] = []

        if file.status != "removed":
            head_content = self.github_client.get_file_content(
                owner,
                repo,
                file.filename,
                head_ref,
            )
            full_file_contexts.append((file.filename, head_ref, "head", head_content))

        if review_depth == "deep" and file.status != "added":
            base_content = self.github_client.get_file_content(
                owner,
                repo,
                base_path,
                base_ref,
            )
            full_file_contexts.append((base_path, base_ref, "base", base_content))

        hunk_source_content = head_content or base_content
        if hunk_source_content:
            hunk_content, truncated = slice_context_by_hunks(
                hunk_source_content,
                parse_patch_hunks(file.patch or ""),
                before=CONTEXT_HUNK_BEFORE_LINES,
                after=CONTEXT_HUNK_AFTER_LINES,
                max_chars=CONTEXT_MAX_HUNK_CONTEXT_CHARS,
            )
            hunk_context = self.add_file_context(
                file.filename,
                head_ref if head_content else base_ref,
                "hunk",
                hunk_content,
                CONTEXT_MAX_HUNK_CONTEXT_CHARS,
            )
            hunk_context.truncated = hunk_context.truncated or truncated
            context.hunk_context = hunk_context

        per_file_related_limit = 3 if review_depth == "deep" else 2
        related_limit = min(per_file_related_limit, CONTEXT_MAX_RELATED_FILES)
        related_files = find_related_files(
            file.filename,
            head_content or file.patch,
            repo_tree_paths,
            max_files=related_limit,
        )
        for related_path, relation in related_files:
            if len(related_seen) >= CONTEXT_MAX_RELATED_FILES:
                break
            if related_path in related_seen or related_path == file.filename:
                continue
            related_seen.add(related_path)
            related_content = self.github_client.get_file_content(
                owner,
                repo,
                related_path,
                head_ref,
            )
            context.related_files.append(
                self.add_related_context(related_path, relation, related_content)
            )

        for path, ref, source, content in full_file_contexts:
            full_context = self.add_file_context(
                path,
                ref,
                source,
                content,
                CONTEXT_MAX_FILE_CHARS,
            )
            if source == "head":
                context.head_context = full_context
            else:
                context.base_context = full_context
