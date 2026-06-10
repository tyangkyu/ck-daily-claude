from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from ax_intel.models import CleanItem, DailyAnalysis, HeroStory, ReportManifest, RunContext, Signal


def _signal_lookup(signals: Iterable[Signal]) -> Dict[str, Signal]:
    return {signal.item_id: signal for signal in signals}


def _item_lookup(clean_items: Iterable[CleanItem]) -> Dict[str, CleanItem]:
    return {item.id: item for item in clean_items}


def _clip(text: str, limit: int = 600) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _bullets(items: List[str], limit: int) -> str:
    return "\n".join(f"• {_clip(item, 300)}" for item in items[:limit])


def render_slack_message(
    *,
    context: RunContext,
    signals: List[Signal],
    analysis: DailyAnalysis,
    hero_story: HeroStory,
    manifest: ReportManifest,
    clean_items: List[CleanItem],
    canvas_url: Optional[str] = None,
) -> str:
    signals_by_id = _signal_lookup(signals)
    items_by_id = _item_lookup(clean_items)
    hero_signal = signals_by_id.get(hero_story.signal_id)
    hero_item = items_by_id.get(hero_story.signal_id)

    top_signals = "\n".join(
        f"{index}. *{signal.title}* — {signal.priority}, {signal.total_score}/30점"
        for index, signal in enumerate(signals[:5], start=1)
    )

    hero_line = ""
    if hero_signal and hero_item:
        hero_line = (
            f"*오늘의 핵심 신호*\n"
            f"{hero_story.title}\n"
            f"- 출처: {hero_item.source_name} / Tier {hero_item.source_tier}\n"
            f"- 원문: {hero_item.url}\n"
            f"- 우선순위: {hero_signal.priority}, {hero_signal.total_score}/30점\n\n"
        )

    return f"""*AX Commerce Intelligence | {context.run_date.isoformat()} 데일리 분석*

*1. 핵심 요약*
{_clip(analysis.core_summary)}

*2. 주목해야 할 변화*
{_bullets(analysis.key_changes, 5)}

*3. IT 산업 관점 핵심 인사이트*
{_bullets(analysis.industry_insights, 5)}

*4. 국내 기업이 고려해야 할 시사점*
{_bullets(analysis.korea_implications, 4)}

*5. 향후 전망*
{_clip(analysis.outlook)}

{hero_line}*Top 전략 신호*
{top_signals}

_PDF 리포트가 스레드에 첨부됩니다._
"""
