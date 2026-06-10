from __future__ import annotations

from html import escape
from typing import Dict, Iterable, List

from ax_intel.models import DailyAnalysis, HeroStory, ReportManifest, RunContext, Signal


def _signal_lookup(signals: Iterable[Signal]) -> Dict[str, Signal]:
    return {signal.item_id: signal for signal in signals}


def _top_signal_lines(signals: List[Signal]) -> List[str]:
    return [
        f"- **{signal.title}** — {signal.priority}, {signal.total_score}/30점"
        for signal in signals[:5]
    ]


def _bullets(items: List[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _numbered(items: List[str]) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, start=1))


def render_report_markdown(
    *, context: RunContext, signals: List[Signal], analysis: DailyAnalysis, hero_story: HeroStory
) -> str:
    signal_lines = "\n".join(_top_signal_lines(signals))
    hero_signal = _signal_lookup(signals).get(hero_story.signal_id)
    hero_priority = hero_signal.priority if hero_signal else "-"

    return f"""# AX Commerce Intelligence 데일리 분석

> 분석 기준일: {context.run_date.isoformat()}
> 분석 방식: {"LLM 분석" if analysis.generated_by == "llm" else "템플릿 요약"}

## 1. 핵심 요약

{analysis.core_summary}

## 2. 주목해야 할 변화

{_bullets(analysis.key_changes)}

## 3. IT 산업 관점 핵심 인사이트

{_numbered(analysis.industry_insights)}

## 4. 국내 기업이 고려해야 할 시사점

{_bullets(analysis.korea_implications)}

## 5. 향후 전망

{analysis.outlook}

---

## 참고: 오늘의 상위 신호

오늘의 핵심 신호: **{hero_story.title}** ({hero_priority})

{hero_story.selection_reason}

{signal_lines}
"""


def render_email_html(
    *, context: RunContext, signals: List[Signal], analysis: DailyAnalysis, hero_story: HeroStory
) -> str:
    top_items = "".join(
        f"<li><strong>{escape(signal.title)}</strong> — {escape(signal.priority)}, {signal.total_score}/30</li>"
        for signal in signals[:5]
    )
    changes = "".join(f"<li>{escape(c)}</li>" for c in analysis.key_changes)
    insights = "".join(f"<li>{escape(c)}</li>" for c in analysis.industry_insights)
    korea = "".join(f"<li>{escape(c)}</li>" for c in analysis.korea_implications)
    return f"""<!doctype html>
<html>
  <body style="font-family: Arial, sans-serif; color: #111827; line-height: 1.6;">
    <h1 style="margin-bottom: 4px;">AX Commerce Intelligence</h1>
    <p style="margin-top: 0; color: #6b7280;">{context.run_date.isoformat()} 데일리 분석</p>
    <h2>핵심 요약</h2>
    <p>{escape(analysis.core_summary)}</p>
    <h3>주목해야 할 변화</h3>
    <ul>{changes}</ul>
    <h3>IT 산업 관점 핵심 인사이트</h3>
    <ul>{insights}</ul>
    <h3>국내 기업이 고려해야 할 시사점</h3>
    <ul>{korea}</ul>
    <h3>향후 전망</h3>
    <p>{escape(analysis.outlook)}</p>
    <h3>오늘의 상위 신호</h3>
    <ol>{top_items}</ol>
  </body>
</html>
"""


def render_archive_markdown(
    *, context: RunContext, signals: List[Signal], analysis: DailyAnalysis, hero_story: HeroStory
) -> str:
    report = render_report_markdown(
        context=context,
        signals=signals,
        analysis=analysis,
        hero_story=hero_story,
    )
    return report + "\n\n---\n\n아카이브 상태: 텍스트 중심 데일리 분석.\n"


def build_manifest(context: RunContext) -> ReportManifest:
    return ReportManifest(
        run_date=context.run_date,
        report_dir=context.report_dir,
        markdown_path=context.output_paths["report_markdown"],
        docx_path=context.output_paths["report_docx"],
        pdf_path=context.output_paths["report_pdf"],
        html_email_path=context.output_paths["email_html"],
        archive_path=context.output_paths["archive_markdown"],
    )
