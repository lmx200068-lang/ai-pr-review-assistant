from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataSource(str, Enum):
    GITHUB = "github"
    MOCK = "mock"


class ReviewSource(str, Enum):
    LLM = "llm"
    MOCK = "mock"
    FALLBACK = "fallback"


class FileType(str, Enum):
    CODE = "code"
    MARKDOWN = "markdown"
    CONFIG = "config"
    DEPENDENCY = "dependency"
    OTHER = "other"


class ReviewStrategy(str, Enum):
    CODE = "code_reviewer"
    DOCUMENTATION = "documentation_reviewer"
    CONFIG = "config_reviewer"
    DEPENDENCY = "dependency_reviewer"
    CONTEXT = "context_only"


class ReviewTaskCreate(BaseModel):
    pr_url: HttpUrl = Field(
        ...,
        examples=["https://github.com/octocat/Hello-World/pull/1"],
    )
    review_depth: Literal["quick", "standard", "deep"] = "standard"


class PullRequestInfo(BaseModel):
    owner: str
    repo: str
    number: int
    title: str
    source_branch: str
    target_branch: str
    author: str
    additions: int
    deletions: int
    changed_files: int
    html_url: str | None = None
    state: str | None = None


class ChangedFile(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    file_type: FileType
    review_strategy: ReviewStrategy
    patch: str | None = None
    patch_truncated: bool = False
    blob_url: str | None = None


class ReviewFinding(BaseModel):
    id: str
    severity: Severity
    file_path: str
    line: int
    file_type: FileType
    review_strategy: ReviewStrategy
    title: str
    summary: str
    evidence_lines: list[str] = Field(default_factory=list, max_length=8)
    suggestion: str


class LLMReviewFinding(BaseModel):
    severity: Severity
    file_path: str
    line: int = Field(..., ge=1)
    file_type: FileType | None = None
    review_strategy: ReviewStrategy | None = None
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    evidence_lines: list[str] = Field(default_factory=list, max_length=8)
    suggestion: str = Field(..., min_length=1)


class ReviewSummary(BaseModel):
    verdict: str
    score: int = Field(..., ge=0, le=100)
    checks_total: int = Field(..., ge=1)
    checks_passed: int = Field(..., ge=0)
    estimated_review_minutes: int = Field(..., ge=1)

    @model_validator(mode="after")
    def checks_passed_cannot_exceed_total(self) -> "ReviewSummary":
        if self.checks_passed > self.checks_total:
            raise ValueError("checks_passed cannot exceed checks_total")
        return self


class LLMReviewPayload(BaseModel):
    summary: ReviewSummary
    findings: list[LLMReviewFinding] = Field(default_factory=list, max_length=12)


class ReviewTask(BaseModel):
    id: str
    status: TaskStatus
    progress: int
    pr_url: HttpUrl
    review_depth: Literal["quick", "standard", "deep"]
    data_source: DataSource
    review_source: ReviewSource | None = None
    review_model: str | None = None
    review_error: str | None = None
    created_at: datetime
    updated_at: datetime
    message: str
    pr: PullRequestInfo | None = None
    changed_files: list[ChangedFile] = Field(default_factory=list)
    summary: ReviewSummary | None = None
    findings: list[ReviewFinding] = Field(default_factory=list)
    pending_findings: list[ReviewFinding] = Field(default_factory=list)
