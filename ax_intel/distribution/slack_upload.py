from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ax_intel.models import RunContext, SlackSendResult


def _env(key: str) -> Optional[str]:
    return os.environ.get(key)


def upload_slack(context: RunContext) -> SlackSendResult:
    """Post Slack message and upload files.

    In dry-run mode or when SLACK_BOT_TOKEN is absent, returns a mock result.
    File uploads are best-effort — a failure does not abort the message post.
    """
    channel_id = _env("SLACK_CHANNEL_ID") or "C_PLACEHOLDER"
    run_date = context.run_date

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

    # 2. Upload report.pdf as reply (best-effort)
    pdf_path: Path = context.output_paths["report_pdf"]
    if pdf_path.exists():
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
            print(f"[WARN] PDF upload skipped: {exc}", file=sys.stderr)

    return SlackSendResult(
        run_date=run_date,
        channel_id=channel_id,
        channel_name=channel_id,
        message_ts=message_ts,
        pdf_ts=pdf_ts,
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )
