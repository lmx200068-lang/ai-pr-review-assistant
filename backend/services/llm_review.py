import json
import re

from ..clients.llm import LLMClientError, openai_compatible_chat_completion
from ..schemas import (
    ChangedFile,
    FileType,
    LLMReviewFinding,
    LLMReviewPayload,
    RelatedFileContext,
    ReviewFinding,
    ReviewContextPack,
    ReviewStrategy,
    ReviewSummary,
    Severity,
)
from .file_classifier import classify_changed_file
from .prompt_builder import build_review_prompt


VALID_SEVERITIES = {"high", "medium", "low"}
VALID_FILE_TYPES = {"code", "markdown", "config", "dependency", "other"}
VALID_REVIEW_STRATEGIES = {
    "code_reviewer",
    "documentation_reviewer",
    "config_reviewer",
    "dependency_reviewer",
    "context_only",
}


def extract_json_object(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end < start:
            raise LLMClientError("LLM response did not contain a JSON object")
        parsed = json.loads(cleaned[start : end + 1])

    if not isinstance(parsed, dict):
        raise LLMClientError("LLM response JSON must be an object")
    return parsed


def normalize_line_value(value: object) -> object:
    if value in (None, "", 0, "0"):
        return None
    return value


def normalize_severity(value: object) -> str:
    severity = str(value or "medium").lower().strip()
    if severity == "critical":
        return "high"
    if severity not in VALID_SEVERITIES:
        return "medium"
    return severity


def normalize_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()][:8]
    return [str(value)] if str(value).strip() else []


def safe_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_summary(raw_summary: object, findings_count: int) -> dict[str, object]:
    summary = raw_summary if isinstance(raw_summary, dict) else {}
    checks_total = safe_int(
        summary.get("checks_total"),
        max(1, findings_count, 1),
    )
    checks_passed = safe_int(
        summary.get("checks_passed"),
        max(0, checks_total - findings_count),
    )
    checks_passed = min(checks_passed, checks_total)
    score = safe_int(summary.get("score"), 80)
    score = max(0, min(100, score))
    minutes = safe_int(summary.get("estimated_review_minutes"), 1)

    return {
        "verdict": str(
            summary.get("verdict")
            or summary.get("overall")
            or "LLM review completed; some fields were normalized by the validator."
        ),
        "score": score,
        "checks_total": max(1, checks_total),
        "checks_passed": max(0, checks_passed),
        "estimated_review_minutes": max(1, minutes),
    }


def normalize_review_strategy(value: object) -> object:
    normalized = str(value or "").lower().strip()
    return normalized if normalized in VALID_REVIEW_STRATEGIES else None


def normalize_file_type(value: object) -> object:
    normalized = str(value or "").lower().strip()
    return normalized if normalized in VALID_FILE_TYPES else None


def normalize_finding_item(item: object) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None

    file_path = item.get("file_path") or item.get("path") or item.get("file")
    if not file_path:
        return None

    evidence_lines = normalize_string_list(
        item.get("evidence_lines")
        if "evidence_lines" in item
        else item.get("evidence")
    )
    summary = item.get("summary") or item.get("description") or item.get("reason")
    title = item.get("title") or "待确认评审问题"

    return {
        "severity": normalize_severity(item.get("severity")),
        "file_path": str(file_path),
        "line": normalize_line_value(item.get("line")),
        "file_type": normalize_file_type(item.get("file_type")),
        "review_strategy": normalize_review_strategy(item.get("review_strategy")),
        "title": str(title),
        "summary": str(summary or title),
        "evidence_lines": evidence_lines,
        "suggestion": str(
            item.get("suggestion")
            or item.get("recommendation")
            or "请人工复核该项。"
        ),
    }


def normalize_finding_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    normalized_items: list[dict[str, object]] = []
    for item in value:
        normalized = normalize_finding_item(item)
        if normalized:
            normalized_items.append(normalized)
        if len(normalized_items) >= 12:
            break
    return normalized_items


def normalize_llm_payload(raw_payload: dict[str, object]) -> dict[str, object]:
    findings = normalize_finding_list(raw_payload.get("findings"))
    pending_findings = normalize_finding_list(raw_payload.get("pending_findings"))

    formal_findings: list[dict[str, object]] = []
    for finding in findings:
        if finding["evidence_lines"]:
            formal_findings.append(finding)
        else:
            pending_findings.append(finding)

    return {
        "summary": normalize_summary(
            raw_payload.get("summary"),
            len(formal_findings) + len(pending_findings),
        ),
        "findings": formal_findings[:12],
        "pending_findings": pending_findings[:12],
    }


def resolve_finding_metadata(
    files: list[ChangedFile],
    file_path: str,
    model_file_type: FileType | None = None,
    model_review_strategy: ReviewStrategy | None = None,
) -> tuple[FileType, ReviewStrategy]:
    for file in files:
        if file.filename == file_path:
            return file.file_type, file.review_strategy

    if model_file_type and model_review_strategy:
        return model_file_type, model_review_strategy

    return classify_changed_file(file_path)


def normalize_evidence_lines(lines: list[str]) -> list[str]:
    normalized_lines: list[str] = []
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            normalized_lines.append(cleaned[:240])
        if len(normalized_lines) >= 8:
            break
    return normalized_lines


def strip_diff_marker(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith(("+", "-", " ")):
        return stripped[1:].strip()
    return stripped


def searchable_context_lines(texts: list[str]) -> tuple[set[str], set[str]]:
    context_lines: set[str] = set()
    context_content_lines: set[str] = set()
    for text in texts:
        for line in (text or "").splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            context_lines.add(cleaned)
            context_content_lines.add(strip_diff_marker(cleaned))
    return context_lines, context_content_lines


def verified_evidence_lines(texts: list[str], lines: list[str]) -> list[str]:
    if not texts:
        return []

    context_lines, context_content_lines = searchable_context_lines(texts)
    verified: list[str] = []

    for line in normalize_evidence_lines(lines):
        stripped_line = strip_diff_marker(line)
        if line in context_lines or stripped_line in context_content_lines:
            verified.append(line)
            continue
        if any(stripped_line and stripped_line in context for context in context_content_lines):
            verified.append(line)

    return verified


def context_texts_by_path(context_pack: ReviewContextPack) -> dict[str, list[str]]:
    texts_by_path: dict[str, list[str]] = {}
    for file in context_pack.changed_files:
        texts_by_path.setdefault(file.filename, [])
        if file.patch:
            texts_by_path[file.filename].append(file.patch)

    for context in context_pack.changed_file_contexts:
        texts = texts_by_path.setdefault(context.path, [])
        if context.patch:
            texts.append(context.patch)
        for item in (
            context.hunk_context,
            context.head_context,
            context.base_context,
        ):
            if item and item.content:
                texts.append(item.content)
        for related in context.related_files:
            if related.content:
                texts_by_path.setdefault(related.path, []).append(related.content)
    return texts_by_path


def related_paths(context_pack: ReviewContextPack) -> set[str]:
    paths: set[str] = set()
    for context in context_pack.changed_file_contexts:
        for related in context.related_files:
            paths.add(related.path)
    return paths


def is_security_sensitive_text(finding: LLMReviewFinding) -> bool:
    text = " ".join(
        [
            finding.file_path,
            finding.title,
            finding.summary,
            finding.suggestion,
            " ".join(finding.evidence_lines),
        ]
    ).lower()
    return any(
        keyword in text
        for keyword in ("token", "api key", "secret", "password", "credential", "安全")
    )


def cap_severity(
    severity: Severity,
    file_type: FileType,
    related_only: bool,
    finding: LLMReviewFinding,
) -> Severity:
    if related_only and severity == Severity.HIGH:
        severity = Severity.MEDIUM
    if file_type == FileType.MARKDOWN and not is_security_sensitive_text(finding):
        severity = Severity.LOW
    return severity


def build_review_finding(
    finding: LLMReviewFinding,
    finding_id: str,
    context_pack: ReviewContextPack,
    related_only: bool,
    evidence_lines: list[str],
) -> ReviewFinding:
    file_type, review_strategy = resolve_finding_metadata(
        context_pack.changed_files,
        finding.file_path,
        finding.file_type,
        finding.review_strategy,
    )
    return ReviewFinding(
        id=finding_id,
        severity=cap_severity(
            finding.severity,
            file_type,
            related_only,
            finding,
        ),
        file_path=finding.file_path,
        line=finding.line,
        file_type=file_type,
        review_strategy=review_strategy,
        title=finding.title,
        summary=finding.summary,
        evidence_lines=evidence_lines,
        suggestion=finding.suggestion,
    )


def convert_payload_to_findings(
    payload: LLMReviewPayload,
    context_pack: ReviewContextPack,
) -> tuple[list[ReviewFinding], list[ReviewFinding], list[str]]:
    findings: list[ReviewFinding] = []
    pending_findings: list[ReviewFinding] = []
    validation_warnings: list[str] = []
    texts_by_path = context_texts_by_path(context_pack)
    changed_paths = {file.filename for file in context_pack.changed_files}
    allowed_related_paths = related_paths(context_pack)
    allowed_paths = changed_paths | allowed_related_paths

    for index, finding in enumerate(payload.findings):
        is_allowed_path = finding.file_path in allowed_paths
        related_only = finding.file_path in allowed_related_paths and finding.file_path not in changed_paths
        evidence_lines = verified_evidence_lines(
            texts_by_path.get(finding.file_path, []),
            finding.evidence_lines,
        )
        review_finding = build_review_finding(
            finding,
            f"llm-finding-{index + 1}",
            context_pack,
            related_only,
            evidence_lines if evidence_lines else normalize_evidence_lines(finding.evidence_lines),
        )

        if is_allowed_path and evidence_lines:
            findings.append(review_finding)
            continue

        review_finding.id = f"llm-pending-{index + 1}"
        pending_findings.append(review_finding)
        if not is_allowed_path:
            validation_warnings.append(
                f"Finding downgraded to pending because file_path is outside changed/related context: {finding.file_path}"
            )
        elif not evidence_lines:
            validation_warnings.append(
                f"Finding downgraded to pending because evidence was not found in provided context: {finding.file_path}"
            )

    start_index = len(pending_findings) + 1
    for index, finding in enumerate(payload.pending_findings, start=start_index):
        related_only = finding.file_path in allowed_related_paths and finding.file_path not in changed_paths
        evidence_lines = verified_evidence_lines(
            texts_by_path.get(finding.file_path, []),
            finding.evidence_lines,
        )
        pending_findings.append(
            build_review_finding(
                finding,
                f"llm-pending-{index}",
                context_pack,
                related_only,
                evidence_lines if evidence_lines else normalize_evidence_lines(finding.evidence_lines),
            )
        )

    return findings, pending_findings, validation_warnings


def run_real_llm_review(
    context_pack: ReviewContextPack,
    depth: str,
) -> tuple[ReviewSummary, list[ReviewFinding], list[ReviewFinding], list[str]]:
    raw_content = openai_compatible_chat_completion(build_review_prompt(context_pack, depth))
    raw_payload = extract_json_object(raw_content)
    payload = LLMReviewPayload.model_validate(normalize_llm_payload(raw_payload))
    findings, pending_findings, validation_warnings = convert_payload_to_findings(
        payload,
        context_pack,
    )
    return payload.summary, findings, pending_findings, validation_warnings
