#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ax_intel.config import REPORTS_DIR, load_config
from ax_intel.io import write_json
from ax_intel.models import RunContext, RunMode


OUTPUT_FILES = {
    "run_context": "run-context.json",
    "raw_items": "raw-items.json",
    "clean_items": "clean-items.json",
    "signals": "signals.json",
    "insights": "insights.json",
    "hero_story": "hero-story.json",
    "hero_prompt": "hero-prompt.md",
    "hero_image": "hero-image.png",
    "report_markdown": "report.md",
    "report_docx": "report.docx",
    "report_pdf": "report.pdf",
    "email_html": "email.html",
    "slack_message": "slack-message.md",
    "archive_markdown": "archive.md",
    "report_manifest": "report-manifest.json",
    "email_draft_preview": "email-draft-preview.json",
    "email_send_result": "email-send-result.json",
    "slack_send_result": "slack-send-result.json",
    "validation_result": "validation-result.json",
    "run_log": "run-log.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a ck-daily run.")
    parser.add_argument("--date", dest="run_date", required=True, help="Run date in YYYY-MM-DD format.")
    parser.add_argument("--mode", choices=[mode.value for mode in RunMode], default=RunMode.DRAFT.value)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR)
    return parser.parse_args()


def build_run_context(run_date: date, mode: RunMode, dry_run: bool, reports_dir: Path) -> RunContext:
    companies_config = load_config("companies.yaml")
    sources_config = load_config("sources.yaml")
    schedule_config = load_config("schedule.yaml")

    report_dir = reports_dir / run_date.isoformat()
    output_paths = {name: report_dir / filename for name, filename in OUTPUT_FILES.items()}
    company_names = list(
        dict.fromkeys(
            company
            for companies in companies_config["tiers"].values()
            for company in companies
        )
    )

    return RunContext(
        run_date=run_date,
        timezone=schedule_config.get("timezone", "Asia/Seoul"),
        mode=mode,
        dry_run=dry_run,
        collection_window_hours=sources_config["policy"]["default_collection_window_hours"],
        report_dir=report_dir,
        output_paths=output_paths,
        companies=company_names,
        created_at=datetime.now(timezone.utc),
    )


def main() -> int:
    args = parse_args()
    run_date = date.fromisoformat(args.run_date)
    mode = RunMode(args.mode)
    context = build_run_context(run_date, mode, args.dry_run, args.reports_dir)

    context.report_dir.mkdir(parents=True, exist_ok=True)
    write_json(context.output_paths["run_context"], context.model_dump(mode="json"))
    print(context.output_paths["run_context"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
