from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ax_intel.models import RunContext, SlackSendResult


def _env(key: str) -> Optional[str]:
    return os.environ.get(key)


def upload_slack(context: RunContext) -> SlackSendResult:
    """Upload hero image, send the Slack message, then attach report.pdf.

    In dry-run mode, writes a mock result without touching the Slack API.
    In live mode, requires SLACK_BOT_TOKEN and SLACK_CHANNEL_ID env vars.
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
    from slack_sdk.errors import SlackApiError

    client = WebClient(token=_env("SLACK_BOT_TOKEN"))
    subject = f"[AX Commerce Intelligence] {run_date.strftime('%Y.%m.%d')} Daily Brief"

    hero_image_ts: Optional[str] = None
    pdf_ts: Optional[str] = None
    message_ts: Optional[str] = None

    # 1. Upload hero image
    hero_path: Path = context.output_paths["hero_image"]
    if hero_path.exists():
        resp = client.files_upload_v2(
            channel=channel_id,
            file=str(hero_path),
            filename=hero_path.name,
            title=f"Hero Visual — {subject}",
        )
        hero_image_ts = resp.get("file", {}).get("shares", {}).get(channel_id, [{}])[0].get("ts")

    # 2. Post the text message
    slack_message_path: Path = context.output_paths["slack_message"]
    text = slack_message_path.read_text(encoding="utf-8") if slack_message_path.exists() else subject
    resp = client.chat_postMessage(channel=channel_id, text=text, mrkdwn=True)
    message_ts = resp["ts"]

    # 3. Upload report.pdf as thread reply
    pdf_path: Path = context.output_paths["report_pdf"]
    if pdf_path.exists() and message_ts:
        resp = client.files_upload_v2(
            channel=channel_id,
            file=str(pdf_path),
            filename=pdf_path.name,
            title=f"Report PDF — {subject}",
            thread_ts=message_ts,
        )
        pdf_ts = resp.get("file", {}).get("shares", {}).get(channel_id, [{}])[0].get("ts")

    return SlackSendResult(
        run_date=run_date,
        channel_id=channel_id,
        channel_name=channel_id,
        message_ts=message_ts,
        hero_image_ts=hero_image_ts,
        pdf_ts=pdf_ts,
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )
