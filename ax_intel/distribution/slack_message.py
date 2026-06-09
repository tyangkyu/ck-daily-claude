from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from ax_intel.models import CleanItem, HeroStory, Insight, ReportManifest, RunContext, Signal


def _signal_lookup(signals: Iterable[Signal]) -> Dict[str, Signal]:
    return {signal.item_id: signal for signal in signals}


def _item_lookup(clean_items: Iterable[CleanItem]) -> Dict[str, CleanItem]:
    return {item.id: item for item in clean_items}


def _hero_insight(insights: List[Insight], hero_story: HeroStory) -> Insight:
    return next((insight for insight in insights if insight.signal_id == hero_story.signal_id), insights[0])


def _clip(text: str, limit: int = 360) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def render_slack_message(
    *,
    context: RunContext,
    signals: List[Signal],
    insights: List[Insight],
    hero_story: HeroStory,
    manifest: ReportManifest,
    clean_items: List[CleanItem],
    canvas_url: Optional[str] = None,
) -> str:
    signals_by_id = _signal_lookup(signals)
    items_by_id = _item_lookup(clean_items)
    hero_signal = signals_by_id[hero_story.signal_id]
    hero_item = items_by_id[hero_story.signal_id]
    insight = _hero_insight(insights, hero_story)
    top_signals = "\n".join(
        (
            f"{index}. *{signal.title}* - {signal.priority}, {signal.total_score}/30점\n"
            f"   - {items_by_id[signal.item_id].summary_raw}"
        )
        for index, signal in enumerate(signals[:5], start=1)
    )
    immediate_actions = "\n".join(f"- {action}" for action in insight.recommended_actions.immediate[:3])
    canvas_line = f"- Slack Canvas: {canvas_url}\n" if canvas_url else ""

    return f"""*ck-daily | {context.run_date.isoformat()} 데일리 브리프*

*히어로 신호*
{hero_story.title}
- 출처: {hero_item.source_name} / Tier {hero_item.source_tier}
- 원문: {hero_item.url}
- 우선순위: {hero_signal.priority}, {hero_signal.total_score}/30점

*무슨 뉴스인가*
{_clip(insight.what_happened)}

*왜 중요한가*
{_clip(insight.why_it_matters)}

*한국 시장 영향*
{_clip(insight.implication_for_korea)}

*LG / Enterprise Commerce 시사점*
{_clip(insight.implication_for_lg)}

*Top 전략 신호*
{top_signals}

*핵심 권고*
{immediate_actions}

_Hero Image · PDF 리포트가 스레드에 첨부됩니다._
"""
