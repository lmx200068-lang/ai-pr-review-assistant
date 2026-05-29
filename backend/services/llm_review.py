import json
import re

from ..clients.llm import LLMClientError, openai_compatible_chat_completion
from ..schemas import (
    ChangedFile,
    FileType,
    LLMReviewPayload,
    ReviewFinding,
    ReviewStrategy,
    ReviewSummary,
    PullRequestInfo,
)
from .file_classifier import classify_changed_file
from .prompt_builder import build_review_messages


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


def verified_evidence_lines(file: ChangedFile, lines: list[str]) -> list[str]:
    if not file.patch:
        return []

    patch_lines = {line.strip() for line in file.patch.splitlines()}
    patch_content_lines = {strip_diff_marker(line) for line in patch_lines}
    verified: list[str] = []

    for line in normalize_evidence_lines(lines):
        if line in patch_lines or strip_diff_marker(line) in patch_content_lines:
            verified.append(line)

    return verified


def convert_payload_to_findings(
    payload: LLMReviewPayload,
    files: list[ChangedFile],
) -> tuple[list[ReviewFinding], list[ReviewFinding]]:
    files_by_name = {file.filename: file for file in files}
    findings: list[ReviewFinding] = []
    pending_findings: list[ReviewFinding] = []
    for index, finding in enumerate(payload.findings):
        file_type, review_strategy = resolve_finding_metadata(
            files,
            finding.file_path,
            finding.file_type,
            finding.review_strategy,
        )
        evidence_lines = verified_evidence_lines(
            files_by_name[finding.file_path],
            finding.evidence_lines,
        )
        review_finding = ReviewFinding(
            id=f"llm-finding-{index + 1}",
            severity=finding.severity,
            file_path=finding.file_path,
            line=finding.line,
            file_type=file_type,
            review_strategy=review_strategy,
            title=finding.title,
            summary=finding.summary,
            evidence_lines=evidence_lines
            if evidence_lines
            else normalize_evidence_lines(finding.evidence_lines),
            suggestion=finding.suggestion,
        )
        if evidence_lines:
            findings.append(review_finding)
        else:
            review_finding.id = f"llm-pending-{index + 1}"
            pending_findings.append(review_finding)

    return findings, pending_findings


def validate_llm_payload_against_files(
    payload: LLMReviewPayload,
    files: list[ChangedFile],
) -> None:
    known_files = {file.filename for file in files}
    for finding in payload.findings:
        if finding.file_path not in known_files:
            raise LLMClientError(
                f"LLM finding references unknown file: {finding.file_path}"
            )

        expected_type, expected_strategy = resolve_finding_metadata(
            files,
            finding.file_path,
        )
        if finding.file_type and finding.file_type != expected_type:
            raise LLMClientError(
                f"LLM finding used wrong file_type for {finding.file_path}: "
                f"{finding.file_type} != {expected_type}"
            )
        if finding.review_strategy and finding.review_strategy != expected_strategy:
            raise LLMClientError(
                f"LLM finding used wrong review_strategy for {finding.file_path}: "
                f"{finding.review_strategy} != {expected_strategy}"
            )


def run_real_llm_review(
    pr: PullRequestInfo,
    depth: str,
    files: list[ChangedFile],
) -> tuple[ReviewSummary, list[ReviewFinding], list[ReviewFinding]]:
    raw_content = openai_compatible_chat_completion(
        build_review_messages(pr, depth, files)
    )
    payload = LLMReviewPayload.model_validate(extract_json_object(raw_content))
    validate_llm_payload_against_files(payload, files)
    findings, pending_findings = convert_payload_to_findings(payload, files)
    return payload.summary, findings, pending_findings
