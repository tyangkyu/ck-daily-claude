from __future__ import annotations

import subprocess
import sys
from pathlib import Path


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


def test_render_slack_message_creates_post_ready_markdown(tmp_path: Path) -> None:
    run_context_path = run_pipeline_to_report(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "render_slack_message.py"),
            "--run-context",
            str(run_context_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    slack_path = Path(result.stdout.strip())
    message = slack_path.read_text(encoding="utf-8")

    assert slack_path == tmp_path / "2026-05-31" / "slack-message.md"
    assert "*AX Commerce Intelligence | 2026-05-31 데일리 분석*" in message
    assert "*1. 핵심 요약*" in message
    assert "*2. 주목해야 할 변화*" in message
    assert "*3. IT 산업 관점 핵심 인사이트*" in message
    assert "*4. 국내 기업이 고려해야 할 시사점*" in message
    assert "*5. 향후 전망*" in message
    assert "*Top 전략 신호*" in message
    assert "OpenAI expands enterprise agent controls" in message
    assert "PDF 리포트" in message
