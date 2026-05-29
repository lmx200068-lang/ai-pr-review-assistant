from pathlib import Path

from ..schemas import ChangedFile, FileType, ReviewStrategy


DEPENDENCY_FILENAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "poetry.lock",
    "pipfile",
    "pipfile.lock",
    "cargo.toml",
    "cargo.lock",
    "go.mod",
    "go.sum",
    "composer.json",
    "composer.lock",
    "gemfile",
    "gemfile.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "gradle.lockfile",
    "mix.exs",
    "mix.lock",
    "pubspec.yaml",
    "pubspec.lock",
}

CONFIG_FILENAMES = {
    ".env",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "vite.config.js",
    "vite.config.ts",
    "eslint.config.js",
    "eslint.config.mjs",
    "tsconfig.json",
    "jsconfig.json",
    "pytest.ini",
    "tox.ini",
    "mypy.ini",
}

CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".cc",
    ".c",
    ".h",
    ".hpp",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
    ".sh",
    ".ps1",
    ".sql",
}

CONFIG_EXTENSIONS = {
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".json",
    ".jsonc",
    ".properties",
    ".xml",
}


def classify_changed_file(filename: str) -> tuple[FileType, ReviewStrategy]:
    normalized = filename.replace("\\", "/")
    lower_path = normalized.lower()
    basename = lower_path.rsplit("/", 1)[-1]
    suffix = Path(basename).suffix.lower()

    if basename in DEPENDENCY_FILENAMES:
        return FileType.DEPENDENCY, ReviewStrategy.DEPENDENCY

    if basename in {"readme", "readme.md"} or suffix in {".md", ".mdx"}:
        return FileType.MARKDOWN, ReviewStrategy.DOCUMENTATION

    if (
        basename in CONFIG_FILENAMES
        or basename.startswith(".env")
        or lower_path.startswith(".github/workflows/")
        or lower_path.startswith(".github/dependabot")
        or suffix in CONFIG_EXTENSIONS
    ):
        return FileType.CONFIG, ReviewStrategy.CONFIG

    if suffix in CODE_EXTENSIONS:
        return FileType.CODE, ReviewStrategy.CODE

    return FileType.OTHER, ReviewStrategy.CONTEXT


def make_changed_file(
    filename: str,
    status: str,
    additions: int,
    deletions: int,
    changes: int,
    previous_filename: str | None = None,
    patch: str | None = None,
    patch_truncated: bool = False,
    blob_url: str | None = None,
) -> ChangedFile:
    file_type, review_strategy = classify_changed_file(filename)
    return ChangedFile(
        filename=filename,
        previous_filename=previous_filename,
        status=status,
        additions=additions,
        deletions=deletions,
        changes=changes,
        file_type=file_type,
        review_strategy=review_strategy,
        patch=patch,
        patch_truncated=patch_truncated,
        blob_url=blob_url,
    )


def safe_patch(patch: str | None, limit: int = 4000) -> tuple[str | None, bool]:
    if not patch or len(patch) <= limit:
        return patch, False
    return f"{patch[:limit]}\n... patch truncated for preview ...", True
