from ..schemas import RepositoryContext


IGNORED_PREFIXES = (
    ".git/",
    "node_modules/",
    "dist/",
    "build/",
    "__pycache__/",
    ".venv/",
    "venv/",
    "coverage/",
)

KEY_EXACT_FILES = {
    "README.md",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "vite.config.js",
    "vite.config.ts",
    ".env.example",
    "backend/.env.example",
    "frontend/.env.example",
}

KEY_PREFIXES = (
    "backend/",
    "frontend/",
    "src/",
    "tests/",
)


def should_ignore(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in IGNORED_PREFIXES
    )


def tree_priority(path: str) -> tuple[int, str]:
    basename = path.rsplit("/", 1)[-1]
    if path in KEY_EXACT_FILES or basename in KEY_EXACT_FILES:
        return 0, path
    if any(path.startswith(prefix) for prefix in KEY_PREFIXES):
        return 1, path
    return 2, path


def summarize_repo_tree(
    tree_items: list[dict],
    max_items: int = 300,
) -> RepositoryContext:
    candidate_paths: list[str] = []
    for item in tree_items:
        if item.get("type") != "blob":
            continue
        path = str(item.get("path", ""))
        if not path or should_ignore(path):
            continue
        candidate_paths.append(path)

    ordered_paths = sorted(set(candidate_paths), key=tree_priority)
    key_files = ordered_paths[:max_items]
    truncated = len(ordered_paths) > len(key_files)
    warnings = []
    if truncated:
        warnings.append(
            f"Repository tree summary truncated from {len(ordered_paths)} to {max_items} items."
        )

    tree_summary = "Repository tree summary:\n" + "\n".join(
        f"- {path}" for path in key_files
    )
    if not key_files:
        tree_summary = "Repository tree summary: unavailable."

    return RepositoryContext(
        tree_summary=tree_summary,
        key_files=key_files,
        truncated=truncated,
        warnings=warnings,
    )
