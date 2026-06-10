#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ax_intel.io import read_json, write_json
from ax_intel.models import DailyAnalysis, HeroStory, RunContext, Signal
from ax_intel.reporting.exporters import write_docx, write_pdf
from ax_intel.reporting.renderer import (
    build_manifest,
    render_archive_markdown,
    render_email_html,
    render_report_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Phase 8 report skeleton artifacts.")
    parser.add_argument("--run-context", type=Path, required=True, help="Path to run-context.json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = RunContext.model_validate(read_json(args.run_context))
    signals = [Signal.model_validate(signal) for signal in read_json(context.output_paths["signals"])]
    analysis = DailyAnalysis.model_validate(read_json(context.output_paths["daily_analysis"]))
    hero_story = HeroStory.model_validate(read_json(context.output_paths["hero_story"]))

    report_markdown = render_report_markdown(
        context=context,
        signals=signals,
        analysis=analysis,
        hero_story=hero_story,
    )
    email_html = render_email_html(
        context=context,
        signals=signals,
        analysis=analysis,
        hero_story=hero_story,
    )
    archive_markdown = render_archive_markdown(
        context=context,
        signals=signals,
        analysis=analysis,
        hero_story=hero_story,
    )
    manifest = build_manifest(context)

    context.output_paths["report_markdown"].write_text(report_markdown, encoding="utf-8")
    context.output_paths["email_html"].write_text(email_html, encoding="utf-8")
    context.output_paths["archive_markdown"].write_text(archive_markdown, encoding="utf-8")
    write_docx(context.output_paths["report_docx"], report_markdown)
    write_pdf(context.output_paths["report_pdf"], report_markdown)
    write_json(context.output_paths["report_manifest"], manifest.model_dump(mode="json"))

    print(context.output_paths["report_markdown"])
    print(context.output_paths["report_docx"])
    print(context.output_paths["report_pdf"])
    print(context.output_paths["email_html"])
    print(context.output_paths["archive_markdown"])
    print(context.output_paths["report_manifest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
