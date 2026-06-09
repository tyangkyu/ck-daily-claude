from __future__ import annotations

"""
뉴스레터체 히어로 이미지 생성기 (Pillow 기반)
DALL-E 없이 Executive Newsletter 스타일 16:9 이미지를 생성한다.
"""

import textwrap
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
_FONT_BOLD = _FONT_DIR / "NanumGothic-Bold.ttf"
_FONT_REG = _FONT_DIR / "NanumGothic-Regular.ttf"

# 16:9 캔버스
WIDTH, HEIGHT = 1792, 1008

# Executive dark palette
PALETTE = {
    "bg_dark":    (10, 14, 26),
    "bg_mid":     (18, 26, 48),
    "accent":     (59, 130, 246),     # 블루
    "accent2":    (16, 185, 129),     # 그린
    "warn":       (245, 158, 11),     # 앰버
    "critical":   (239, 68, 68),      # 레드
    "text_white": (255, 255, 255),
    "text_gray":  (156, 163, 175),
    "text_dim":   (75, 85, 99),
    "card_bg":    (22, 33, 62),
    "card_bdr":   (37, 56, 100),
}


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = _FONT_BOLD if bold else _FONT_REG
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _priority_color(priority: str) -> Tuple[int, int, int]:
    if "Critical" in priority:
        return PALETTE["critical"]
    if "High" in priority:
        return PALETTE["warn"]
    return PALETTE["accent2"]


def _draw_gradient_bg(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(PALETTE["bg_dark"][0] * (1 - t) + PALETTE["bg_mid"][0] * t)
        g = int(PALETTE["bg_dark"][1] * (1 - t) + PALETTE["bg_mid"][1] * t)
        b = int(PALETTE["bg_dark"][2] * (1 - t) + PALETTE["bg_mid"][2] * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))


def _draw_grid_lines(draw: ImageDraw.Draw) -> None:
    """배경 그리드 — 테크 뉴스레터 느낌"""
    for x in range(0, WIDTH, 80):
        draw.line([(x, 0), (x, HEIGHT)], fill=(255, 255, 255, 8), width=1)
    for y in range(0, HEIGHT, 80):
        draw.line([(0, y), (WIDTH, y)], fill=(255, 255, 255, 8), width=1)


def _draw_accent_bar(draw: ImageDraw.Draw, color: Tuple[int, int, int]) -> None:
    draw.rectangle([(0, 0), (WIDTH, 6)], fill=color)
    draw.rectangle([(0, HEIGHT - 6), (WIDTH, HEIGHT)], fill=color)


def _draw_top_label(draw: ImageDraw.Draw, run_date: str) -> None:
    font = _load_font(22, bold=False)
    label = f"AX COMMERCE INTELLIGENCE  ·  {run_date}"
    draw.text((48, 28), label, font=font, fill=PALETTE["text_gray"])


def _draw_headline(draw: ImageDraw.Draw, title: str, priority: str) -> int:
    """메인 헤드라인. y 반환."""
    color = _priority_color(priority)
    # 우선순위 뱃지
    badge_font = _load_font(20, bold=True)
    badge_text = f"  {priority.upper()}  "
    bw, bh = 220, 34
    draw.rectangle([(48, 72), (48 + bw, 72 + bh)], fill=color)
    draw.text((54, 74), badge_text, font=badge_font, fill=(255, 255, 255))

    # 헤드라인 텍스트 — 최대 2줄
    h_font = _load_font(52, bold=True)
    wrapped = textwrap.fill(title, width=38)
    lines = wrapped.split("\n")[:2]
    y = 122
    for line in lines:
        draw.text((48, y), line, font=h_font, fill=PALETTE["text_white"])
        y += 64
    return y + 8


def _draw_signal_meter(draw: ImageDraw.Draw, total_score: int, x: int, y: int) -> None:
    """총점 게이지 바"""
    label_font = _load_font(18, bold=False)
    val_font = _load_font(44, bold=True)
    draw.text((x, y), "SIGNAL SCORE", font=label_font, fill=PALETTE["text_gray"])
    draw.text((x, y + 24), f"{total_score}", font=val_font, fill=PALETTE["accent"])
    draw.text((x + 68, y + 52), "/30", font=label_font, fill=PALETTE["text_gray"])

    # 게이지 바
    bar_y = y + 90
    bar_w = 200
    bar_h = 8
    draw.rectangle([(x, bar_y), (x + bar_w, bar_y + bar_h)], fill=PALETTE["text_dim"])
    filled = int(bar_w * total_score / 30)
    color = _priority_color("Critical" if total_score >= 25 else "High" if total_score >= 20 else "")
    draw.rectangle([(x, bar_y), (x + filled, bar_y + bar_h)], fill=color)


def _draw_score_chips(
    draw: ImageDraw.Draw,
    scores: dict,
    x: int, y: int,
) -> None:
    chip_font = _load_font(17, bold=False)
    val_font = _load_font(17, bold=True)
    labels = {
        "ax_relevance":      "AX",
        "executive_urgency": "Urgency",
        "strategic_impact":  "Strategic",
        "market_disruption": "Market",
        "revenue_impact":    "Revenue",
        "competitive_threat":"Threat",
    }
    cx, cy = x, y
    for key, label in labels.items():
        val = scores.get(key, 0)
        color = PALETTE["accent"] if val >= 4 else PALETTE["accent2"] if val == 3 else PALETTE["text_dim"]
        draw.rectangle([(cx, cy), (cx + 120, cy + 34)], outline=color, width=1)
        draw.text((cx + 8, cy + 6), label, font=chip_font, fill=PALETTE["text_gray"])
        draw.text((cx + 88, cy + 6), str(val), font=val_font, fill=color)
        cx += 132
        if cx + 132 > WIDTH - 48:
            cx = x
            cy += 44


def _draw_signals_card(
    draw: ImageDraw.Draw,
    signals: List[dict],
    x: int, y: int, w: int,
) -> None:
    title_font = _load_font(18, bold=True)
    item_font = _load_font(16, bold=False)
    score_font = _load_font(16, bold=True)

    draw.text((x, y), "TOP SIGNALS TODAY", font=title_font, fill=PALETTE["accent"])
    y += 28

    for i, sig in enumerate(signals[:5]):
        priority = sig.get("priority", "")
        score = sig.get("total_score", 0)
        title = sig.get("title", "")[:55] + ("…" if len(sig.get("title", "")) > 55 else "")
        color = _priority_color(priority)

        draw.rectangle([(x, y), (x + 6, y + 22)], fill=color)
        draw.text((x + 14, y + 2), f"{i+1}. {title}", font=item_font, fill=PALETTE["text_white"])
        draw.text((x + w - 48, y + 2), str(score), font=score_font, fill=color)
        y += 30


def _draw_credit(draw: ImageDraw.Draw, run_date: str) -> None:
    font = _load_font(18, bold=False)
    text = f"ck-daily | {run_date}"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((WIDTH - tw - 32, HEIGHT - 36), text, font=font, fill=PALETTE["text_dim"])


def generate_newsletter_image(
    *,
    hero_title: str,
    priority: str,
    total_score: int,
    scores: dict,
    signals: List[dict],
    run_date: str,
    output_path: Path,
) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    _draw_gradient_bg(img)

    # RGBA 오버레이로 그리드
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    _draw_grid_lines(overlay_draw)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    accent_color = _priority_color(priority)

    _draw_accent_bar(draw, accent_color)
    _draw_top_label(draw, run_date)

    # 좌측 — 헤드라인 + 점수
    y_after_headline = _draw_headline(draw, hero_title, priority)

    # 세로 구분선
    div_x = int(WIDTH * 0.62)
    draw.rectangle([(div_x, 60), (div_x + 1, HEIGHT - 60)], fill=PALETTE["card_bdr"])

    # 좌측 하단 — 점수 칩
    _draw_score_chips(draw, scores, 48, max(y_after_headline + 20, 330))

    # 좌측 중단 — 시그널 미터
    _draw_signal_meter(draw, total_score, 48, max(y_after_headline + 120, 430))

    # 우측 — 시그널 카드
    _draw_signals_card(draw, signals, div_x + 32, 80, WIDTH - div_x - 64)

    _draw_credit(draw, run_date)

    # 약한 비네팅
    vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(80):
        alpha = int(120 * (i / 80) ** 2)
        vd.rectangle([(i, i), (WIDTH - i, HEIGHT - i)], outline=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG", optimize=True)
