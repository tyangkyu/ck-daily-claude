#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ax_intel.distribution.slack_message import render_slack_message
from ax_intel.io import read_json
from ax_intel.models import CleanItem, DailyAnalysis, HeroStory, ReportManifest, RunContext, Signal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a ck-daily Slack message artifact.")
    parser.add_argument("--run-context", type=Path, required=True, help="Path to run-context.json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = RunContext.model_validate(read_json(args.run_context))
    signals = [Signal.model_validate(signal) for signal in read_json(context.output_paths["signals"])]
    clean_items = [CleanItem.model_validate(item) for item in read_json(context.output_paths["clean_items"])]
    analysis = DailyAnalysis.model_validate(read_json(context.output_paths["daily_analysis"]))
    hero_story = HeroStory.model_validate(read_json(context.output_paths["hero_story"]))
    manifest = ReportManifest.model_validate(read_json(context.output_paths["report_manifest"]))

    message = render_slack_message(
        context=context,
        signals=signals,
        analysis=analysis,
        hero_story=hero_story,
        manifest=manifest,
        clean_items=clean_items,
    )
    context.output_paths["slack_message"].write_text(message, encoding="utf-8")
    print(context.output_paths["slack_message"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
