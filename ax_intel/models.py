from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator, model_validator


class SourceTier(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class SignalPriority(str, Enum):
    CRITICAL = "Critical Signal"
    HIGH = "High Priority"
    MONITOR = "Monitor"
    LOW = "Low Priority"


class RunMode(str, Enum):
    DRAFT = "draft"
    SEND_AFTER_APPROVAL = "send_after_approval"
    SEND = "send"


class BaseContract(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class RunContext(BaseContract):
    run_date: date
    timezone: str = "Asia/Seoul"
    mode: RunMode = RunMode.DRAFT
    dry_run: bool = True
    collection_window_hours: int = Field(72, ge=1, le=168)
    report_dir: Path
    output_paths: Dict[str, Path]
    companies: List[str] = Field(min_length=1)
    created_at: datetime


class RawItem(BaseContract):
    id: str = Field(min_length=8)
    title: str = Field(min_length=1)
    url: HttpUrl
    source_name: str = Field(min_length=1)
    source_tier: SourceTier
    published_at: Optional[datetime] = None
    discovered_at: datetime
    companies: List[str] = Field(default_factory=list)
    scope: List[str] = Field(default_factory=list)
    summary_raw: str = ""


class CleanItem(RawItem):
    canonical_url: HttpUrl
    credibility_reason: str = Field(min_length=1)
    related_scope: List[str] = Field(default_factory=list)
    duplicate_group_id: str = Field(min_length=1)
    needs_review: bool = False


class ScoreSet(BaseContract):
    strategic_impact: int = Field(ge=1, le=5)
    market_disruption: int = Field(ge=1, le=5)
    revenue_impact: int = Field(ge=1, le=5)
    competitive_threat: int = Field(ge=1, le=5)
    ax_relevance: int = Field(ge=1, le=5)
    executive_urgency: int = Field(ge=1, le=5)

    @property
    def total(self) -> int:
        return sum(
            [
                self.strategic_impact,
                self.market_disruption,
                self.revenue_impact,
                self.competitive_threat,
                self.ax_relevance,
                self.executive_urgency,
            ]
        )


class Signal(BaseContract):
    item_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_tier: SourceTier
    scores: ScoreSet
    total_score: int = Field(ge=6, le=30)
    priority: SignalPriority
    rationale: str = Field(min_length=10)

    @model_validator(mode="after")
    def validate_total_score(self) -> "Signal":
        if self.total_score != self.scores.total:
            raise ValueError("total_score must equal the sum of scores")
        return self


class HeroStory(BaseContract):
    signal_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    selection_reason: str = Field(min_length=1)
    alternative_signal_ids: List[str] = Field(default_factory=list)


class DailyAnalysis(BaseContract):
    """텍스트 중심 데일리 분석 결과 (5단 구조).

    1) core_summary       핵심 요약 (3~5줄)
    2) key_changes        주목해야 할 변화
    3) industry_insights  IT 산업 관점 핵심 인사이트 (3~5개)
    4) korea_implications 국내 기업이 고려해야 할 시사점
    5) outlook            향후 전망
    """

    run_date: date
    core_summary: str = Field(min_length=1)
    key_changes: List[str] = Field(min_length=1)
    industry_insights: List[str] = Field(min_length=1)
    korea_implications: List[str] = Field(min_length=1)
    outlook: str = Field(min_length=1)
    generated_by: str = "template"  # "template" | "llm"


class ReportManifest(BaseContract):
    run_date: date
    report_dir: Path
    markdown_path: Optional[Path] = None
    docx_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    html_email_path: Optional[Path] = None
    archive_path: Optional[Path] = None


class Recipient(BaseContract):
    group: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: EmailStr


class SendResult(BaseContract):
    run_date: date
    mode: RunMode
    recipients: List[Recipient]
    status: str = Field(min_length=1)
    draft_id: Optional[str] = None
    message_id: Optional[str] = None
    sent_at: Optional[datetime] = None

    @field_validator("recipients")
    @classmethod
    def validate_recipient_count(cls, recipients: List[Recipient]) -> List[Recipient]:
        if len(recipients) > 5:
            raise ValueError("recipient count must not exceed 5")
        return recipients


class EmailDraftPreview(BaseContract):
    run_date: date
    subject: str = Field(min_length=1)
    recipients: List[Recipient]
    html_path: Path
    pdf_path: Path
    download_link: Optional[HttpUrl] = None
    draft_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    created_at: datetime


class SlackSendResult(BaseContract):
    run_date: date
    channel_id: str = Field(min_length=1)
    channel_name: str = ""
    message_ts: Optional[str] = None
    pdf_ts: Optional[str] = None
    status: str = Field(min_length=1)
    sent_at: Optional[datetime] = None


class ValidationCheck(BaseContract):
    name: str = Field(min_length=1)
    passed: bool
    message: str = Field(min_length=1)


class ValidationResult(BaseContract):
    run_date: date
    passed: bool
    checks: List[ValidationCheck]
    created_at: datetime


class PipelineStepResult(BaseContract):
    name: str = Field(min_length=1)
    status: str = Field(min_length=1)
    output_paths: List[Path] = Field(default_factory=list)
    message: str = ""
    started_at: datetime
    finished_at: datetime


class RunLog(BaseContract):
    run_date: date
    status: str = Field(min_length=1)
    mode: RunMode
    dry_run: bool
    report_dir: Path
    steps: List[PipelineStepResult]
    validation_passed: bool = False
    started_at: datetime
    finished_at: datetime
