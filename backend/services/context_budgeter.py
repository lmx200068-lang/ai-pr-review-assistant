from ..config import (
    CONTEXT_MAX_FILE_CHARS,
    CONTEXT_MAX_HUNK_CONTEXT_CHARS,
    CONTEXT_MAX_RELATED_FILE_CHARS,
    CONTEXT_MAX_TOTAL_CHARS,
)


class ContextBudgeter:
    def __init__(
        self,
        max_total_chars: int = CONTEXT_MAX_TOTAL_CHARS,
        max_file_chars: int = CONTEXT_MAX_FILE_CHARS,
        max_hunk_context_chars: int = CONTEXT_MAX_HUNK_CONTEXT_CHARS,
        max_related_file_chars: int = CONTEXT_MAX_RELATED_FILE_CHARS,
    ) -> None:
        self.max_total_chars = max_total_chars
        self.max_file_chars = max_file_chars
        self.max_hunk_context_chars = max_hunk_context_chars
        self.max_related_file_chars = max_related_file_chars
        self.used_chars = 0
        self.warnings: list[str] = []
        self.skipped: list[str] = []
        self.truncated: list[str] = []

    def can_add(self, text: str) -> bool:
        return self.used_chars + len(text or "") <= self.max_total_chars

    def reserve(self, text: str, label: str) -> bool:
        if self.can_add(text):
            self.used_chars += len(text or "")
            return True
        self.warnings.append(f"{label}: skipped because context budget is exhausted.")
        self.skipped.append(label)
        return False

    def trim(self, text: str, max_chars: int, label: str | None = None) -> tuple[str, bool]:
        if len(text or "") <= max_chars:
            return text, False
        if label:
            self.truncated.append(label)
        prefix = f"[TRUNCATED: showing first {max_chars} chars only]\n"
        return prefix + text[:max_chars], True
