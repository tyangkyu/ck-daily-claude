#!/usr/bin/env python3
"""Phase 9 (Slack): upload hero image, post message, attach report.pdf."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ax_intel.distribution.slack_upload import upload_slack
from ax_intel.io import read_json, write_json
from ax_intel.models import RunContext


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload daily brief to Slack.")
    parser.add_argument("--run-context", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = RunContext.model_validate(read_json(args.run_context))
    result = upload_slack(context)
    output_path = context.output_paths["slack_send_result"]
    write_json(output_path, result.model_dump(mode="json"))
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
