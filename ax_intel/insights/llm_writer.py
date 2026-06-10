from __future__ import annotations

"""
데일리 분석(DailyAnalysis) 생성기.

- live + ANTHROPIC_API_KEY 존재 → Anthropic Claude API로 실제 분석 생성 (고품질)
- dry_run 또는 키 부재 → 결정론적 템플릿 폴백 (무료, 오프라인 테스트용)

작성 원칙 (사용자 지정):
- 특별한 용어를 제외하고 최대한 한글 중심으로 작성한다.
- 원문 표현을 직역하지 말고 한국어 비즈니스 문서에 맞게 재구성한다.
- 누구나 예상 가능한 뻔한 인사이트는 배제한다.
- LG CNS·LG전자 등 특정 기업 연결은 명확한 근거가 있을 때만 제한적으로 한다.
- 억지로 자사 적용 관점을 만들지 않는다.
- 모든 인사이트는 근거 기반으로 작성한다.
"""

import json
import os
import sys
from datetime import date
from typing import List, Sequence

from ax_intel.models import CleanItem, DailyAnalysis, Signal

DEFAULT_MODEL = "claude-sonnet-4-6"
TOP_N = 8  # 분석에 투입할 상위 신호 수

SYSTEM_PROMPT = """당신은 LG CNS 디지털커머스사업단의 IT 산업 분석 전문위원입니다.
매일 수집된 글로벌·국내 AI/커머스 뉴스 신호를 바탕으로, IT 의사결정자가 읽는 한국어 데일리 분석을 작성합니다.

[작성 원칙]
- 특별한 고유명사·기술용어를 제외하고 최대한 한글 중심으로 작성합니다.
- 원문(영문) 표현을 직역하지 말고, 한국어 비즈니스 문서에 적합하게 재구성합니다.
- 누구나 예상 가능한 상투적·일반론적 인사이트는 배제합니다. 구체적 근거와 함의가 있는 문장만 씁니다.
- LG CNS·LG전자 등 특정 기업과의 연결은 명확한 근거가 있을 때만 제한적으로 언급하고, 억지로 자사 적용 관점을 만들지 않습니다.
- 기업 홍보성 해석을 배제하고, 실제 산업적 시사점에 집중합니다.
- 모든 인사이트는 수집된 신호에 근거합니다. 신호에 없는 사실을 지어내지 않습니다.

[인사이트 도출 관점 — 우선순위 순]
1. 기술 트렌드 변화: AI / Agent / LLM / Data / Cloud / Platform / Security / Software Engineering / Digital Commerce
2. 산업 구조 변화: 시장 지형 / 가치사슬 / 수익모델 / 플랫폼 경쟁 구도
3. 기업·조직 관점 시사점: 전략적 대응 / 조직 운영 / 개발 생산성 / 업무 방식 / 투자 우선순위
4. 실행 가능한 시사점: 향후 1~3년 내 현실적 적용 / 사업·서비스 전략 참고 / 기술·플랫폼 조직 고려사항

[출력 형식]
반드시 아래 JSON 스키마만 출력합니다. 코드블록·설명·서론 없이 JSON 객체 하나만 출력합니다.
{
  "core_summary": "핵심 요약 3~5줄. 오늘 신호 전체를 관통하는 메시지.",
  "key_changes": ["주목해야 할 변화 1", "변화 2", "변화 3"],
  "industry_insights": ["IT 산업 관점 핵심 인사이트 1 (근거 포함)", "인사이트 2", "인사이트 3"],
  "korea_implications": ["국내 기업이 고려해야 할 시사점 1", "시사점 2"],
  "outlook": "향후 전망. 근거 기반 시나리오."
}
- key_changes: 3~5개, industry_insights: 3~5개, korea_implications: 2~4개.
- 각 항목은 한 문장이 아니라 근거가 드러나는 2~3문장으로 작성해도 됩니다."""


def _signal_brief(signals: Sequence[Signal], clean_items: Sequence[CleanItem]) -> str:
    items_by_id = {item.id: item for item in clean_items}
    lines: List[str] = []
    for idx, sig in enumerate(signals[:TOP_N], start=1):
        item = items_by_id.get(sig.item_id)
        scope = ", ".join((item.related_scope or item.scope)) if item else ""
        companies = ", ".join(item.companies) if item and item.companies else "-"
        summary = (item.summary_raw.strip() if item else "") or "(요약 없음)"
        source = f"{item.source_name} (Tier {item.source_tier})" if item else ""
        url = str(item.url) if item else ""
        lines.append(
            f"[신호 {idx}] {sig.title}\n"
            f"  - 점수: {sig.total_score}/30 ({sig.priority})\n"
            f"  - 관련기업: {companies}\n"
            f"  - 영역: {scope}\n"
            f"  - 출처: {source}\n"
            f"  - 요약: {summary}\n"
            f"  - 링크: {url}"
        )
    return "\n\n".join(lines)


def _build_user_prompt(run_date: date, brief: str) -> str:
    return (
        f"분석 기준일: {run_date.isoformat()}\n\n"
        f"오늘 수집·스코어링된 상위 신호는 다음과 같습니다.\n\n"
        f"{brief}\n\n"
        "위 신호를 근거로 데일리 분석 JSON을 작성하세요."
    )


def _call_anthropic(run_date: date, brief: str, model: str, api_key: str) -> DailyAnalysis:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0.4,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(run_date, brief)}],
    )
    text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text").strip()

    # JSON 추출 (모델이 코드블록을 붙였을 경우 대비)
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    data = json.loads(text)

    return DailyAnalysis(
        run_date=run_date,
        core_summary=data["core_summary"].strip(),
        key_changes=[s.strip() for s in data["key_changes"] if s.strip()],
        industry_insights=[s.strip() for s in data["industry_insights"] if s.strip()],
        korea_implications=[s.strip() for s in data["korea_implications"] if s.strip()],
        outlook=data["outlook"].strip(),
        generated_by="llm",
    )


def _template_analysis(
    run_date: date, signals: Sequence[Signal], clean_items: Sequence[CleanItem]
) -> DailyAnalysis:
    """LLM 없이 신호로부터 만든 결정론적 폴백 (오프라인/무료)."""
    items_by_id = {item.id: item for item in clean_items}
    top = list(signals[:5])
    titles = [s.title for s in top]

    scopes: List[str] = []
    for s in top:
        item = items_by_id.get(s.item_id)
        if item:
            scopes.extend(item.related_scope or item.scope)
    uniq_scopes = list(dict.fromkeys(scopes))[:5]
    scope_phrase = ", ".join(uniq_scopes) if uniq_scopes else "AI·디지털 커머스"

    core_summary = (
        f"{run_date.isoformat()} 기준 상위 {len(top)}개 신호가 포착됐다. "
        f"핵심 축은 {scope_phrase}이며, 최상위 신호는 '{titles[0] if titles else '-'}'다. "
        "(LLM 분석 비활성 상태 — 템플릿 요약)"
    )
    key_changes = [
        f"{s.title} — {s.priority}, {s.total_score}/30점" for s in top
    ]
    industry_insights = [
        f"'{s.title}' 신호는 {(', '.join((items_by_id.get(s.item_id).related_scope or items_by_id.get(s.item_id).scope)) if items_by_id.get(s.item_id) else '관련 영역')} 측면에서 추적이 필요하다."
        for s in top[:3]
    ] or ["오늘은 상위 신호가 부족하다. 다음 수집 주기에서 보강이 필요하다."]
    korea_implications = [
        "국내 IT·커머스 기업은 위 신호가 고객 경험과 운영 효율로 전환되는 경로를 모니터링해야 한다.",
        "근거가 분명한 신호에 한해 PoC 가설을 정의하고 우선순위를 검토한다.",
    ]
    outlook = (
        "상위 신호의 우선순위와 출처 신뢰도를 기준으로, 향후 수집 주기에서 동일 주제의 후속 신호가 "
        "강화되는지 추적한다."
    )
    return DailyAnalysis(
        run_date=run_date,
        core_summary=core_summary,
        key_changes=key_changes,
        industry_insights=industry_insights,
        korea_implications=korea_implications,
        outlook=outlook,
        generated_by="template",
    )


def generate_daily_analysis(
    *,
    run_date: date,
    signals: Sequence[Signal],
    clean_items: Sequence[CleanItem],
    use_llm: bool = True,
) -> DailyAnalysis:
    """데일리 분석을 생성한다.

    use_llm=True 이고 ANTHROPIC_API_KEY가 있으면 Claude API로 분석.
    그 외에는 결정론적 템플릿 폴백.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if use_llm and api_key and signals:
        model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        try:
            brief = _signal_brief(signals, clean_items)
            return _call_anthropic(run_date, brief, model, api_key)
        except Exception as exc:  # noqa: BLE001 — 폴백 보장
            print(f"[WARN] LLM analysis failed, falling back to template: {exc}", file=sys.stderr)

    return _template_analysis(run_date, signals, clean_items)
