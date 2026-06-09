from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def _build_dalle_prompt(hero_title: str, visual_message: str, run_date: str) -> str:
    """Build a DALL-E 3 prompt in the 뉴스레터체 style shown in the reference samples."""
    return f"""Create a vibrant, high-density pixel art or digital illustration in the style of a Korean commerce/business editorial thumbnail.

Style reference: Pixel art OR colorful anime-style illustration. Bright, vivid colors. Dense composition. Feels like a Korean retail/commerce editorial magazine cover.

Scene concept: {visual_message}

Visual requirements:
- 16:9 wide format composition
- Pixel art or anime/webtoon illustration style (like Korean gaming or retail brand marketing)
- Vibrant, saturated color palette — blues, greens, oranges, or brand colors depending on context
- Busy, information-dense scene showing Korean commerce, AI, retail, or tech landscape
- People or characters actively engaged in shopping, technology, or commerce activities
- Modern Korean urban setting (shopping mall, retail store, online platform, city street)
- Small text label in bottom-right corner: "ck-daily | {run_date}"
- Top area has space for a headline overlay (keep top 15% relatively clean)
- NO generic robot icons, NO clipart, NO western corporate stock photo style
- High energy, storytelling composition that communicates: {hero_title}

Make it look like a top-tier Korean retail brand's social media thumbnail or a business news editorial illustration."""


def generate_dalle_image(
    *,
    hero_title: str,
    visual_message: str,
    run_date: str,
    output_path: Path,
    api_key: Optional[str] = None,
) -> bool:
    """Generate hero image using DALL-E 3. Returns True on success, False on failure."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        print("[WARN] OPENAI_API_KEY not set — skipping DALL-E generation", file=sys.stderr)
        return False

    try:
        import httpx
        from openai import OpenAI

        client = OpenAI(api_key=key)
        prompt = _build_dalle_prompt(hero_title, visual_message, run_date)

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",   # 16:9에 가장 근접한 DALL-E 3 사이즈
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        image_bytes = httpx.get(image_url, timeout=60).content
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        print(f"[DALL-E] Hero image saved: {output_path} ({len(image_bytes):,} bytes)", file=sys.stderr)
        return True

    except Exception as exc:
        print(f"[WARN] DALL-E generation failed: {exc}", file=sys.stderr)
        return False
