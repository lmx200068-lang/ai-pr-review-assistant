import base64
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from ..config import (
    GITHUB_API_BASE,
    GITHUB_MAX_FILES,
    GITHUB_TIMEOUT_SECONDS,
    GITHUB_TOKEN,
    is_github_token_configured,
)
from ..schemas import ChangedFile, PullRequestInfo
from ..services.file_classifier import make_changed_file, safe_patch
from ..services.github_url import parse_github_pr_url


class GitHubClientError(RuntimeError):
    pass


class GitHubClient:
    """Read-only GitHub API client for PR metadata, files, contents, and tree."""

    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.last_tree_truncated = False

    def request_json(self, path: str) -> object:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-pr-review-assistant-local",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if is_github_token_configured():
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        request = Request(f"{GITHUB_API_BASE}{path}", headers=headers, method="GET")

        try:
            with urlopen(request, timeout=GITHUB_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubClientError(
                f"GitHub API returned {exc.code} for {path}: {detail[:240]}"
            ) from exc
        except URLError as exc:
            raise GitHubClientError(f"GitHub API request failed: {exc.reason}") from exc

    def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
    ) -> str | None:
        owner_path = quote(owner, safe="")
        repo_path = quote(repo, safe="")
        file_path = quote(path, safe="/")
        ref_path = quote(ref, safe="")

        try:
            data = self.request_json(
                f"/repos/{owner_path}/{repo_path}/contents/{file_path}?ref={ref_path}"
            )
            if isinstance(data, list):
                self.warnings.append(f"{path}: skipped directory content response")
                return None
            if not isinstance(data, dict):
                self.warnings.append(f"{path}: unexpected content response")
                return None
            if data.get("type") != "file":
                self.warnings.append(f"{path}: skipped non-file content")
                return None
            if data.get("encoding") != "base64":
                self.warnings.append(f"{path}: skipped non-base64 content")
                return None

            raw_content = data.get("content")
            if not isinstance(raw_content, str) or not raw_content:
                self.warnings.append(f"{path}: empty content response")
                return None

            decoded = base64.b64decode(raw_content).decode(
                "utf-8",
                errors="replace",
            )
            return decoded
        except Exception as exc:
            self.warnings.append(f"{path}: failed to read content at {ref}: {exc}")
            return None

    def get_repo_tree(
        self,
        owner: str,
        repo: str,
        ref: str,
        recursive: bool = True,
    ) -> list[dict]:
        owner_path = quote(owner, safe="")
        repo_path = quote(repo, safe="")
        ref_path = quote(ref, safe="")
        recursive_query = "?recursive=1" if recursive else ""

        try:
            data = self.request_json(
                f"/repos/{owner_path}/{repo_path}/git/trees/{ref_path}{recursive_query}"
            )
        except Exception as exc:
            self.warnings.append(f"repo tree: failed to load at {ref}: {exc}")
            self.last_tree_truncated = False
            return []

        if not isinstance(data, dict):
            self.warnings.append("repo tree: unexpected response")
            self.last_tree_truncated = False
            return []

        self.last_tree_truncated = bool(data.get("truncated"))
        tree = data.get("tree")
        if not isinstance(tree, list):
            self.warnings.append("repo tree: missing tree items")
            return []

        items: list[dict] = []
        for item in tree:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            item_type = item.get("type")
            if not isinstance(path, str) or not isinstance(item_type, str):
                continue
            items.append(
                {
                    "path": path,
                    "type": item_type,
                    "size": item.get("size"),
                }
            )
        return items


default_client = GitHubClient()


def github_api_json(path: str) -> object:
    return default_client.request_json(path)


def get_file_content(owner: str, repo: str, path: str, ref: str) -> str | None:
    return default_client.get_file_content(owner, repo, path, ref)


def get_repo_tree(
    owner: str,
    repo: str,
    ref: str,
    recursive: bool = True,
) -> list[dict]:
    return default_client.get_repo_tree(owner, repo, ref, recursive)


def fetch_github_pr_context(pr_url: str) -> tuple[PullRequestInfo, list[ChangedFile]]:
    parsed = parse_github_pr_url(pr_url)
    if not parsed:
        raise GitHubClientError("Only GitHub pull request URLs are supported")

    owner, repo, number = parsed
    owner_path = quote(owner, safe="")
    repo_path = quote(repo, safe="")
    pr_data = github_api_json(f"/repos/{owner_path}/{repo_path}/pulls/{number}")
    if not isinstance(pr_data, dict):
        raise GitHubClientError("GitHub API returned an unexpected PR payload")

    files: list[ChangedFile] = []
    page = 1
    while len(files) < GITHUB_MAX_FILES:
        per_page = min(100, GITHUB_MAX_FILES - len(files))
        files_data = github_api_json(
            f"/repos/{owner_path}/{repo_path}/pulls/{number}/files"
            f"?per_page={per_page}&page={page}"
        )
        if not isinstance(files_data, list):
            raise GitHubClientError("GitHub API returned an unexpected files payload")
        if not files_data:
            break

        for item in files_data:
            patch, patch_truncated = safe_patch(item.get("patch"))
            files.append(
                make_changed_file(
                    filename=item.get("filename", "unknown"),
                    status=item.get("status", "modified"),
                    additions=int(item.get("additions", 0)),
                    deletions=int(item.get("deletions", 0)),
                    changes=int(item.get("changes", 0)),
                    previous_filename=item.get("previous_filename"),
                    patch=patch,
                    patch_truncated=patch_truncated,
                    blob_url=item.get("blob_url"),
                )
            )

        if len(files_data) < per_page:
            break
        page += 1

    base_repo = pr_data.get("base", {}).get("repo", {}) or {}
    base_owner = base_repo.get("owner", {}).get("login") or owner
    base_repo_name = base_repo.get("name") or repo
    head = pr_data.get("head", {}) or {}
    base = pr_data.get("base", {}) or {}
    author = (pr_data.get("user") or {}).get("login") or "unknown"

    pr = PullRequestInfo(
        owner=base_owner,
        repo=base_repo_name,
        number=int(pr_data.get("number", number)),
        title=pr_data.get("title") or f"Pull request #{number}",
        source_branch=head.get("label") or head.get("ref") or "unknown",
        target_branch=base.get("ref") or "unknown",
        author=author,
        additions=int(pr_data.get("additions", 0)),
        deletions=int(pr_data.get("deletions", 0)),
        changed_files=int(pr_data.get("changed_files", len(files))),
        html_url=pr_data.get("html_url"),
        state=pr_data.get("state"),
        head_sha=head.get("sha"),
        base_sha=base.get("sha"),
    )
    return pr, files
