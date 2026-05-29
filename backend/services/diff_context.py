import re


HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<header>.*)$"
)


def parse_patch_hunks(patch: str) -> list[dict]:
    hunks: list[dict] = []
    if not patch:
        return hunks

    for line in patch.splitlines():
        match = HUNK_RE.match(line)
        if not match:
            continue
        hunks.append(
            {
                "old_start": int(match.group("old_start")),
                "old_count": int(match.group("old_count") or "1"),
                "new_start": int(match.group("new_start")),
                "new_count": int(match.group("new_count") or "1"),
                "header": line,
            }
        )
    return hunks


def merge_windows(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not windows:
        return []

    merged: list[tuple[int, int]] = []
    for start, end in sorted(windows):
        if not merged or start > merged[-1][1] + 1:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end))
    return merged


def slice_context_by_hunks(
    content: str,
    hunks: list[dict],
    before: int = 40,
    after: int = 40,
    max_chars: int = 12000,
) -> tuple[str, bool]:
    if not content:
        return "", False

    lines = content.splitlines()
    if not lines:
        return "", False

    windows: list[tuple[int, int]] = []
    for hunk in hunks:
        new_start = max(1, int(hunk.get("new_start", 1)))
        new_count = max(1, int(hunk.get("new_count", 1)))
        start = max(1, new_start - before)
        end = min(len(lines), new_start + new_count + after - 1)
        windows.append((start, end))

    if not windows:
        windows.append((1, min(len(lines), before + after)))

    chunks: list[str] = []
    for start, end in merge_windows(windows):
        chunks.append(f"[Lines {start}-{end}]")
        for line_number in range(start, end + 1):
            chunks.append(f"{line_number} | {lines[line_number - 1]}")

    result = "\n".join(chunks)
    if len(result) <= max_chars:
        return result, False

    return result[:max_chars] + "\n[TRUNCATED: hunk context exceeded budget]", True
