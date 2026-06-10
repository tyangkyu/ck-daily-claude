from __future__ import annotations

from typing import List, Sequence, Tuple

from ax_intel.insights.llm_writer import generate_daily_analysis
from ax_intel.models import CleanItem, DailyAnalysis, HeroStory, Signal


def select_hero_story(signals: List[Signal]) -> HeroStory:
    if not signals:
        raise ValueError("Cannot select hero story without signals")

    hero = max(
        signals,
        key=lambda signal: (
            signal.total_score,
            signal.scores.executive_urgency,
            signal.scores.ax_relevance,
            signal.scores.market_disruption,
        ),
    )
    alternatives = [signal.item_id for signal in signals if signal.item_id != hero.item_id][:2]

    return HeroStory(
        signal_id=hero.item_id,
        title=hero.title,
        selection_reason=(
            f"총점 {hero.total_score}/30점, AX 연관성 {hero.scores.ax_relevance}/5점, "
            f"경영진 긴급도 {hero.scores.executive_urgency}/5점으로 오늘의 핵심 신호로 선정했다."
        ),
        alternative_signal_ids=alternatives,
    )


def generate_phase6_outputs(
    signals: List[Signal],
    clean_items: List[CleanItem],
    *,
    run_date,
    use_llm: bool = True,
) -> Tuple[DailyAnalysis, HeroStory]:
    analysis = generate_daily_analysis(
        run_date=run_date,
        signals=signals,
        clean_items=clean_items,
        use_llm=use_llm,
    )
    hero_story = select_hero_story(signals)
    return analysis, hero_story
