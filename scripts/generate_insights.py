#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ax_intel.insights.writer import generate_phase6_outputs
from ax_intel.io import read_json, write_json
from ax_intel.models import CleanItem, RunContext, Signal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Phase 6 executive insights and hero story.")
    parser.add_argument("--run-context", type=Path, required=True, help="Path to run-context.json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = RunContext.model_validate(read_json(args.run_context))
    clean_items = [
        CleanItem.model_validate(item)
        for item in read_json(context.output_paths["clean_items"])
    ]
    signals = [
        Signal.model_validate(signal)
        for signal in read_json(context.output_paths["signals"])
    ]
    analysis, hero_story = generate_phase6_outputs(
        signals,
        clean_items,
        run_date=context.run_date,
        use_llm=not context.dry_run,
    )

    write_json(context.output_paths["daily_analysis"], analysis.model_dump(mode="json"))
    write_json(context.output_paths["hero_story"], hero_story.model_dump(mode="json"))
    print(context.output_paths["daily_analysis"])
    print(context.output_paths["hero_story"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

