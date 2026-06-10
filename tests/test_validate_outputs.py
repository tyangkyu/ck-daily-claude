from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ax_intel.io import read_json
from ax_intel.models import ValidationResult


ROOT = Path(__file__).resolve().parents[1]


def run_pipeline_to_distribution(tmp_path: Path) -> Path:
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
        "send_slack.py",
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


def test_validate_outputs_passes_for_complete_pipeline(tmp_path: Path) -> None:
    run_context_path = run_pipeline_to_distribution(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_outputs.py"),
            "--run-context",
            str(run_context_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = result.stdout.strip().splitlines()
    validation_path = Path(lines[0])
    validation = ValidationResult.model_validate(read_json(validation_path))

    assert lines[1] == "passed"
    assert validation.passed is True
    assert len(validation.checks) == 7
    assert all(check.passed for check in validation.checks)


def test_validate_outputs_records_failure_without_nonzero_exit(tmp_path: Path) -> None:
    run_context_path = run_pipeline_to_distribution(tmp_path)
    (tmp_path / "2026-05-31" / "report.pdf").unlink()

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_outputs.py"),
            "--run-context",
            str(run_context_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = result.stdout.strip().splitlines()
    validation = ValidationResult.model_validate(read_json(Path(lines[0])))

    assert lines[1] == "failed"
    assert validation.passed is False
    assert any(not check.passed and "report.pdf" in check.message for check in validation.checks)
