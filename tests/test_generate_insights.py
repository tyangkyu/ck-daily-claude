from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ax_intel.io import read_json
from ax_intel.models import DailyAnalysis, HeroStory


ROOT = Path(__file__).resolve().parents[1]


def run_pipeline_to_signals(tmp_path: Path) -> Path:
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


def test_generate_insights_creates_daily_analysis_and_hero_story(tmp_path: Path) -> None:
    run_context_path = run_pipeline_to_signals(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_insights.py"),
            "--run-context",
            str(run_context_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output_paths = [Path(line) for line in result.stdout.strip().splitlines()]

    analysis_path = tmp_path / "2026-05-31" / "daily-analysis.json"
    hero_story_path = tmp_path / "2026-05-31" / "hero-story.json"
    assert output_paths == [analysis_path, hero_story_path]

    analysis = DailyAnalysis.model_validate(read_json(analysis_path))
    hero_story = HeroStory.model_validate(read_json(hero_story_path))

    # dry-run은 LLM 호출 없이 결정론적 템플릿 폴백을 사용한다.
    assert analysis.generated_by == "template"
    assert analysis.core_summary
    assert analysis.key_changes
    assert analysis.industry_insights
    assert analysis.korea_implications
    assert analysis.outlook

    assert hero_story.title
    assert hero_story.selection_reason
