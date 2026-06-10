#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ax_intel.config import load_config
from ax_intel.io import read_json, write_json
from ax_intel.models import RawItem, RunContext, SourceTier
from ax_intel.source_clients.rss import collect_rss_feed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Phase 3 raw source items.")
    parser.add_argument("--run-context", type=Path, required=True, help="Path to run-context.json.")
    return parser.parse_args()


def collect_from_config(context: RunContext) -> List[RawItem]:
    sources_config = load_config("sources.yaml")
    discovered_at = context.created_at
    cutoff_reference = (
        datetime.combine(context.run_date, dt_time(23, 59, 59), tzinfo=timezone.utc)
        if context.dry_run
        else discovered_at
    )
    cutoff_at = cutoff_reference - timedelta(hours=context.collection_window_hours)
    collected: List[RawItem] = []

    offline_mode = context.dry_run
    for feed in sources_config.get("rss_feeds", []):
        if feed.get("offline_only") and not offline_mode:
            continue
        if offline_mode and not feed.get("offline_only"):
            continue
        try:
            collected.extend(
                collect_rss_feed(
                    feed_url=feed["url"],
                    source_name=feed["name"],
                    source_tier=SourceTier(feed["tier"]),
                    default_companies=feed.get("companies", []),
                    default_scope=feed.get("scope", []),
                    discovered_at=discovered_at,
                    cutoff_at=cutoff_at,
                )
            )
        except Exception as exc:
            print(f"[WARN] Skipping feed {feed['name']}: {exc}", file=sys.stderr)

    return collected


def main() -> int:
    args = parse_args()
    context = RunContext.model_validate(read_json(args.run_context))
    items = collect_from_config(context)
    output_path = context.output_paths["raw_items"]
    write_json(output_path, [item.model_dump(mode="json") for item in items])
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

