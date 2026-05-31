from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from ax_intel.config import PROJECT_ROOT
from ax_intel.models import RawItem, SourceTier


def parse_rss_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def stable_item_id(source_name: str, title: str, url: str) -> str:
    digest = hashlib.sha256(f"{source_name}|{title}|{url}".encode("utf-8")).hexdigest()
    return digest[:16]


def read_feed_text(feed_url: str) -> str:
    candidate = Path(feed_url)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")

    req = Request(feed_url, headers={"User-Agent": "Mozilla/5.0 (compatible; AXCommerceIntel/1.0)"})
    with urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8")


def collect_rss_feed(
    *,
    feed_url: str,
    source_name: str,
    source_tier: SourceTier,
    default_companies: Iterable[str],
    default_scope: Iterable[str],
    discovered_at: datetime,
    cutoff_at: datetime,
) -> List[RawItem]:
    feed_text = read_feed_text(feed_url)
    root = ElementTree.fromstring(feed_text)
    items: List[RawItem] = []

    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        published_at = parse_rss_datetime(item.findtext("pubDate"))

        if not title or not link:
            continue
        if published_at is not None and published_at < cutoff_at:
            continue

        items.append(
            RawItem(
                id=stable_item_id(source_name, title, link),
                title=title,
                url=link,
                source_name=source_name,
                source_tier=source_tier,
                published_at=published_at,
                discovered_at=discovered_at,
                companies=list(default_companies),
                scope=list(default_scope),
                summary_raw=description,
            )
        )

    return items

