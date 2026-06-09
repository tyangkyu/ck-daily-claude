from __future__ import annotations

"""
Replicate API 기반 히어로 이미지 생성기
모델: black-forest-labs/flux-schnell (빠름, 고품질, $0.003/장)
"""

import os
import sys
from pathlib import Path
from typing import Optional


def _build_prompt(hero_title: str, visual_message: str, run_date: str) -> str:
    return (
        f"Wide cinematic 16:9 editorial illustration, vibrant anime or pixel art style, "
        f"high energy business and technology scene, NO text, NO signs, NO labels, NO writing, "
        f"NO storefronts with text, NO banners with characters, "
        f"scene: {visual_message}, "
        f"people using smartphones and tablets, data holograms, glowing UI screens, "
        f"dynamic commerce and AI technology atmosphere, "
        f"bold saturated colors, blue orange green palette, "
        f"executive business magazine cover composition, "
        f"clean background with abstract geometric data visualization elements, "
        f"professional editorial illustration, ultra detailed, "
        f"no readable text anywhere in the image"
    )


def _build_negative_prompt() -> str:
    return (
        "text, words, letters, writing, signs, banners, labels, storefronts, "
        "Chinese characters, Japanese text, kanji, hiragana, katakana, hanzi, "
        "Korean text, hangul, Arabic, any alphabet, typography, fonts, "
        "watermark, signature, logo with text, blurry, low quality, ugly"
    )


def generate_replicate_image(
    *,
    hero_title: str,
    visual_message: str,
    run_date: str,
    output_path: Path,
    api_token: Optional[str] = None,
) -> bool:
    """Replicate Flux Schnell로 이미지 생성. 성공 시 True 반환."""
    token = api_token or os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("[WARN] REPLICATE_API_TOKEN not set — skipping Replicate generation", file=sys.stderr)
        return False

    try:
        import replicate
        import httpx

        client = replicate.Client(api_token=token)
        prompt = _build_prompt(hero_title, visual_message, run_date)

        # flux-dev는 negative_prompt 지원, schnell보다 품질 우수
        output = client.run(
            "black-forest-labs/flux-dev",
            input={
                "prompt": prompt,
                "negative_prompt": _build_negative_prompt(),
                "aspect_ratio": "16:9",
                "num_outputs": 1,
                "num_inference_steps": 28,
                "guidance": 3.5,
                "output_format": "png",
                "output_quality": 90,
            },
        )

        # output은 URL 리스트 또는 FileOutput 리스트
        result = output[0] if isinstance(output, list) else output
        url = str(result)

        image_bytes = httpx.get(url, timeout=60).content
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        print(f"[Replicate] Hero image saved: {output_path} ({len(image_bytes):,} bytes)", file=sys.stderr)
        return True

    except Exception as exc:
        print(f"[WARN] Replicate generation failed: {exc}", file=sys.stderr)
        return False
