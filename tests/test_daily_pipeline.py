from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ax_intel.io import read_json
from ax_intel.models import RunLog, ValidationResult


ROOT = Path(__file__).resolve().parents[1]


def test_daily_pipeline_runs_end_to_end(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "daily_pipeline.py"),
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
    lines = result.stdout.strip().splitlines()
    run_log_path = Path(lines[0])
    run_log = RunLog.model_validate(read_json(run_log_path))
    validation = ValidationResult.model_validate(
        read_json(tmp_path / "2026-05-31" / "validation-result.json")
    )

    assert lines[1] == "completed"
    assert run_log.status == "completed"
    assert run_log.validation_passed is True
    assert validation.passed is True
    assert [step.name for step in run_log.steps] == [
        "init_run",
        "collect_sources",
        "clean_and_rank_sources",
        "score_signals",
        "generate_insights",
        "render_report",
        "render_slack_message",
        "send_slack",
        "validate_outputs",
    ]
    assert all(step.status == "completed" for step in run_log.steps)
    assert (tmp_path / "2026-05-31" / "slack-send-result.json").exists()
    assert (tmp_path / "2026-05-31" / "slack-message.md").exists()
    assert (tmp_path / "2026-05-31" / "report.pdf").exists()
