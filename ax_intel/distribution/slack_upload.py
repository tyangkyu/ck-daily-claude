from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ax_intel.config import PROJECT_ROOT
from ax_intel.models import RunContext, RunMode, SlackSendResult

_ENV_LOADED = False


def _load_env_file() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)

def _env(key: str) -> Optional[str]:
    _load_env_file()
    return os.environ.get(key)


def upload_slack(context: RunContext) -> SlackSendResult:
    """Post Slack message and upload report.pdf as a required attachment."""
    channel_id = _env("SLACK_CHANNEL_ID") or "C0B7AUS6J0H"
    run_date = context.run_date

    if not context.dry_run and context.mode == RunMode.SEND and not _env("SLACK_BOT_TOKEN"):
        raise RuntimeError(
            "SLACK_BOT_TOKEN is required for --mode send. "
            "Set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID in .env or the environment."
        )

    if context.dry_run or not _env("SLACK_BOT_TOKEN"):
        return SlackSendResult(
            run_date=run_date,
            channel_id=channel_id,
            channel_name="dry-run",
            status="dry_run",
            sent_at=datetime.now(timezone.utc),
        )

    from slack_sdk import WebClient

    client = WebClient(token=_env("SLACK_BOT_TOKEN"))
    subject = f"[AX Commerce Intelligence] {run_date.strftime('%Y.%m.%d')} Daily Brief"

    pdf_ts: Optional[str] = None
    message_ts: Optional[str] = None

    # 0. Ensure bot is in the channel (works for public channels)
    try:
        client.conversations_join(channel=channel_id)
    except Exception:
        pass  # Private channel — must be manually invited

    # 1. Post the text message first
    slack_message_path: Path = context.output_paths["slack_message"]
    text = slack_message_path.read_text(encoding="utf-8") if slack_message_path.exists() else subject
    resp = client.chat_postMessage(channel=channel_id, text=text, mrkdwn=True)
    message_ts = resp["ts"]

    # 2. Upload report.pdf as reply. The daily distribution is incomplete without it.
    pdf_path: Path = context.output_paths["report_pdf"]
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing report PDF for Slack upload: {pdf_path}")
    try:
        resp = client.files_upload_v2(
            channel=channel_id,
            file=str(pdf_path),
            filename=pdf_path.name,
            title=f"Report PDF — {subject}",
            thread_ts=message_ts,
        )
        pdf_ts = resp.get("file", {}).get("id")
    except Exception as exc:
        print(f"[ERROR] PDF upload failed: {exc}", file=sys.stderr)
        raise
    if not pdf_ts:
        raise RuntimeError("Slack PDF upload did not return a file id")

    return SlackSendResult(
        run_date=run_date,
        channel_id=channel_id,
        channel_name=channel_id,
        message_ts=message_ts,
        pdf_ts=pdf_ts,
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )
