import posixpath
import re
from pathlib import PurePosixPath


PY_FROM_RE = re.compile(r"^\s*from\s+([.\w]+)\s+import\s+", re.MULTILINE)
PY_IMPORT_RE = re.compile(r"^\s*import\s+([.\w]+)", re.MULTILINE)
JS_IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^'\"]+\s+from\s+)?|require\()\s*['\"]([^'\"]+)['\"]"
)

JS_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx")


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def existing_path(candidates: list[str], repo_tree_paths: set[str]) -> str | None:
    for candidate in candidates:
        normalized = normalize_path(candidate)
        if normalized in repo_tree_paths:
            return normalized
    return None


def python_module_candidates(module: str) -> list[str]:
    module_path = module.strip(".").replace(".", "/")
    if not module_path:
        return []
    return [f"{module_path}.py", f"{module_path}/__init__.py"]


def relative_python_candidates(changed_path: str, module: str) -> list[str]:
    dot_count = len(module) - len(module.lstrip("."))
    if dot_count == 0:
        return python_module_candidates(module)

    base = PurePosixPath(normalize_path(changed_path)).parent
    for _ in range(max(0, dot_count - 1)):
        base = base.parent
    rest = module.lstrip(".").replace(".", "/")
    if not rest:
        return []
    return [str(base / f"{rest}.py"), str(base / rest / "__init__.py")]


def js_import_candidates(changed_path: str, import_path: str) -> list[str]:
    if not import_path.startswith("."):
        return []

    base = PurePosixPath(normalize_path(changed_path)).parent
    target = normalize_path(posixpath.normpath(str(base / import_path)))
    candidates = [target]
    candidates.extend(f"{target}{extension}" for extension in JS_EXTENSIONS)
    candidates.extend(f"{target}/index{extension}" for extension in JS_EXTENSIONS)
    return candidates


def test_candidates(changed_path: str) -> list[tuple[str, str]]:
    path = PurePosixPath(normalize_path(changed_path))
    stem = path.stem
    suffix = path.suffix
    parent = str(path.parent)
    candidates = [
        (f"tests/test_{stem}.py", "possible matching test file"),
        (f"{parent}/test_{stem}.py", "possible matching test file"),
        (f"{parent}/__tests__/{stem}_test.py", "possible matching test file"),
        (f"{parent}/{stem}.test{suffix}", "possible matching test file"),
        (f"{parent}/__tests__/{stem}.test{suffix}", "possible matching test file"),
    ]
    return candidates


def add_candidate(
    related: list[tuple[str, str]],
    path: str | None,
    relation: str,
    max_files: int,
) -> None:
    if not path or len(related) >= max_files:
        return
    if any(existing == path for existing, _ in related):
        return
    related.append((path, relation))


def find_related_files(
    changed_path: str,
    changed_content: str | None,
    repo_tree_paths: list[str],
    max_files: int = 3,
) -> list[tuple[str, str]]:
    repo_paths = {normalize_path(path) for path in repo_tree_paths}
    changed_path = normalize_path(changed_path)
    content = changed_content or ""
    related: list[tuple[str, str]] = []

    for module in PY_FROM_RE.findall(content):
        path = existing_path(relative_python_candidates(changed_path, module), repo_paths)
        add_candidate(related, path, "imported local module", max_files)
    for module in PY_IMPORT_RE.findall(content):
        path = existing_path(python_module_candidates(module), repo_paths)
        add_candidate(related, path, "imported local module", max_files)

    for import_path in JS_IMPORT_RE.findall(content):
        path = existing_path(js_import_candidates(changed_path, import_path), repo_paths)
        add_candidate(related, path, "imported local module", max_files)

    for candidate, relation in test_candidates(changed_path):
        path = existing_path([candidate], repo_paths)
        add_candidate(related, path, relation, max_files)

    if changed_path == "backend/routes/review_tasks.py":
        add_candidate(
            related,
            existing_path(["frontend/src/App.jsx"], repo_paths),
            "frontend API consumer",
            max_files,
        )
        add_candidate(
            related,
            existing_path(["frontend/src/api/client.js"], repo_paths),
            "frontend API client",
            max_files,
        )

    if "/api/review-tasks" in content:
        add_candidate(
            related,
            existing_path(["backend/routes/review_tasks.py"], repo_paths),
            "backend API route",
            max_files,
        )
        add_candidate(
            related,
            existing_path(["backend/schemas.py"], repo_paths),
            "backend API contract",
            max_files,
        )

    config_related = [
        "backend/config.py",
        "backend/.env.example",
        "frontend/.env.example",
        "package.json",
        "frontend/package.json",
        "requirements.txt",
        "backend/requirements.txt",
    ]
    if changed_path in config_related or changed_path.endswith(
        ("package.json", "requirements.txt", ".env.example")
    ):
        for candidate in config_related:
            path = existing_path([candidate], repo_paths)
            add_candidate(related, path, "related configuration", max_files)

    return related[:max_files]
