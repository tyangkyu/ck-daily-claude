from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ax_intel.io import read_json
from ax_intel.models import SlackSendResult


ROOT = Path(__file__).resolve().parents[1]


def run_pipeline_to_report(tmp_path: Path) -> Path:
    init_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "init_run.py"),
            "--date",
            "2026-05-31",
            "--dry-run",
            "--reports-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    run_context_path = Path(init_result.stdout.strip())

    for script_name in [
        "collect_sources.py",
        "clean_and_rank_sources.py",
        "score_signals.py",
        "generate_insights.py",
        "render_report.py",
        "render_slack_message.py",
    ]:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / script_name),
                "--run-context",
                str(run_context_path),
            ],
            cwd=ROOT,
            check=True,
        )

    return run_context_path


def test_send_slack_creates_send_result_in_dry_run(tmp_path: Path) -> None:
    run_context_path = run_pipeline_to_report(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "send_slack.py"),
            "--run-context",
            str(run_context_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output_path = Path(result.stdout.strip())

    assert output_path == tmp_path / "2026-05-31" / "slack-send-result.json"
    send_result = SlackSendResult.model_validate(read_json(output_path))
    assert send_result.status == "dry_run"
    assert send_result.channel_id
    assert send_result.run_date.isoformat() == "2026-05-31"
