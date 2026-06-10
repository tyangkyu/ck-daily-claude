from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List

from ax_intel.io import read_json
from ax_intel.models import (
    CleanItem,
    DailyAnalysis,
    HeroStory,
    RawItem,
    ReportManifest,
    RunContext,
    Signal,
    SlackSendResult,
    ValidationCheck,
    ValidationResult,
)


REQUIRED_OUTPUT_KEYS = [
    "run_context",
    "raw_items",
    "clean_items",
    "signals",
    "daily_analysis",
    "hero_story",
    "report_markdown",
    "report_docx",
    "report_pdf",
    "email_html",
    "slack_message",
    "archive_markdown",
    "report_manifest",
    "slack_send_result",
]


def _check(name: str, fn: Callable[[], str]) -> ValidationCheck:
    try:
        return ValidationCheck(name=name, passed=True, message=fn())
    except Exception as exc:
        return ValidationCheck(name=name, passed=False, message=str(exc))


def _existing_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    if path.is_file() and path.stat().st_size == 0:
        raise ValueError(f"Empty file: {path}")


def validate_required_files(context: RunContext) -> str:
    for key in REQUIRED_OUTPUT_KEYS:
        _existing_file(context.output_paths[key])
    return f"{len(REQUIRED_OUTPUT_KEYS)} required files exist"


def validate_json_contracts(context: RunContext) -> str:
    RawItem.model_validate(read_json(context.output_paths["raw_items"])[0])
    CleanItem.model_validate(read_json(context.output_paths["clean_items"])[0])
    Signal.model_validate(read_json(context.output_paths["signals"])[0])
    DailyAnalysis.model_validate(read_json(context.output_paths["daily_analysis"]))
    HeroStory.model_validate(read_json(context.output_paths["hero_story"]))
    ReportManifest.model_validate(read_json(context.output_paths["report_manifest"]))
    SlackSendResult.model_validate(read_json(context.output_paths["slack_send_result"]))
    return "JSON contracts are valid"


def validate_top_signals(context: RunContext) -> str:
    signals = [Signal.model_validate(signal) for signal in read_json(context.output_paths["signals"])]
    if not signals:
        raise ValueError("No signals found")
    totals = [signal.total_score for signal in signals]
    if totals != sorted(totals, reverse=True):
        raise ValueError("Signals are not sorted by total_score descending")
    return f"{len(signals[:5])} top signals available"


def validate_source_urls(context: RunContext) -> str:
    raw_items = [RawItem.model_validate(item) for item in read_json(context.output_paths["raw_items"])]
    if not raw_items:
        raise ValueError("No raw items found")
    return f"{len(raw_items)} source URLs valid"


def validate_email_html(context: RunContext) -> str:
    html = context.output_paths["email_html"].read_text(encoding="utf-8")
    required = ["AX Commerce Intelligence", "핵심 요약", "주목해야 할 변화", "향후 전망"]
    missing = [item for item in required if item not in html]
    if missing:
        raise ValueError(f"Email HTML missing: {', '.join(missing)}")
    return "Email HTML contains required blocks"


def validate_slack_result(context: RunContext) -> str:
    result = SlackSendResult.model_validate(read_json(context.output_paths["slack_send_result"]))
    if not result.status:
        raise ValueError("Slack send result has no status")
    return f"Slack distribution status: {result.status}"


def validate_report_exports(context: RunContext) -> str:
    pdf_path = context.output_paths["report_pdf"]
    docx_path = context.output_paths["report_docx"]
    if not pdf_path.read_bytes().startswith(b"%PDF-"):
        raise ValueError("PDF signature is invalid")
    if not docx_path.read_bytes().startswith(b"PK"):
        raise ValueError("DOCX zip signature is invalid")
    return "Report exports have valid signatures"


def run_validation(context: RunContext) -> ValidationResult:
    checks = [
        _check("required_files", lambda: validate_required_files(context)),
        _check("json_contracts", lambda: validate_json_contracts(context)),
        _check("top_signals", lambda: validate_top_signals(context)),
        _check("source_urls", lambda: validate_source_urls(context)),
        _check("email_html", lambda: validate_email_html(context)),
        _check("slack_result", lambda: validate_slack_result(context)),
        _check("report_exports", lambda: validate_report_exports(context)),
    ]
    return ValidationResult(
        run_date=context.run_date,
        passed=all(check.passed for check in checks),
        checks=checks,
        created_at=datetime.now(timezone.utc),
    )
