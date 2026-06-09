from __future__ import annotations

"""
Pollinations.ai 기반 히어로 이미지 생성기
- 완전 무료, API 키 불필요
- https://pollinations.ai
"""

import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


def _build_prompt(visual_message: str) -> str:
    return (
        "pixel art editorial illustration, vibrant colors, 16:9, "
        "Korean commerce and AI technology scene, "
        "people shopping and using technology, modern retail environment, "
        "colorful and energetic composition, no text, no signs, no writing, "
        "executive business magazine style, high detail, "
        f"{visual_message}"
    )


def generate_pollinations_image(
    *,
    hero_title: str,
    visual_message: str,
    run_date: str,
    output_path: Path,
) -> bool:
    """Pollinations.ai로 무료 이미지 생성. 성공 시 True 반환."""
    try:
        prompt = _build_prompt(visual_message)
        encoded = urllib.parse.quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1792&height=1008&model=flux&nologo=true&seed={abs(hash(hero_title)) % 9999}"
        )

        req = urllib.request.Request(url, headers={"User-Agent": "ck-daily/1.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            image_bytes = resp.read()

        if len(image_bytes) < 10000:
            raise ValueError(f"응답이 너무 작음: {len(image_bytes)} bytes")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        print(f"[Pollinations] Hero image saved: {output_path} ({len(image_bytes):,} bytes)", file=sys.stderr)
        return True

    except Exception as exc:
        print(f"[WARN] Pollinations generation failed: {exc}", file=sys.stderr)
        return False
