"""
modules/scraper_spotify_community.py
-------------------------------------
Fetches recent discussion posts from the Spotify Community forum
(community.spotify.com) via Lithium/Khoros RSS feeds.

No authentication required — Lithium forums expose public RSS at:
  https://community.spotify.com/t5/<board-id>/rss

Targeted boards (discovery-relevant):
  - music-space       → Music · Talk about music
  - spotify-features  → Spotify Features (users request / complain about features)
  - live-ideas        → Live Ideas (voted feature requests)

Returns posts in the same schema as other scrapers so they drop cleanly
into the existing pipeline.
"""

import re
import requests

# Board RSS URLs — discovery-relevant sections
_BOARD_RSS_URLS = [
    ("Spotify Community — Music",
     "https://community.spotify.com/t5/Music/rss"),
    ("Spotify Community — Features",
     "https://community.spotify.com/t5/Content-Questions/rss"),
    ("Spotify Community — Ideas",
     "https://community.spotify.com/t5/Live-Ideas/rss"),
]

# Keywords to keep only discovery/recommendation-related posts
_DISCOVERY_KEYWORDS = [
    "discover", "recommendation", "algorithm", "repeat", "same song",
    "new music", "new artist", "explore", "playlist", "shuffle",
    "discover weekly", "release radar", "daily mix", "smart shuffle",
    "suggestion", "variety", "genre", "taste", "personaliz",
]


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_relevant(text: str) -> bool:
    """Return True if the post touches discovery or recommendation topics."""
    lower = text.lower()
    return any(kw in lower for kw in _DISCOVERY_KEYWORDS)


def scrape_spotify_community(count: int = 100) -> list:
    """
    Fetch recent Spotify Community forum posts via RSS and filter for
    music-discovery relevance.

    Args:
        count: Max total posts to return (split across boards).

    Returns:
        List of dicts:
          {"source": "Spotify Community", "review_text": str,
           "date": str | None, "rating": None, "language": "en"}
    """
    try:
        import feedparser  # lazy import — keeps startup fast if library absent
    except ImportError:
        print("feedparser not installed — Spotify Community scraper skipped.")
        return []

    per_board = max(10, count // len(_BOARD_RSS_URLS))
    scraped = []

    for label, url in _BOARD_RSS_URLS:
        if len(scraped) >= count:
            break
        try:
            feed = feedparser.parse(url)
            entries = feed.get("entries", [])
        except Exception as e:
            print(f"Failed to fetch RSS from {url}: {e}")
            continue

        for entry in entries:
            if len(scraped) >= count:
                break

            title   = entry.get("title", "")
            summary = _strip_html(entry.get("summary", ""))
            text    = f"{title}. {summary}".strip(". ")

            if not text or not _is_relevant(text):
                continue

            # Trim to a sane length
            text = text[:600]

            published = entry.get("published", None)

            scraped.append({
                "source":      "Spotify Community",
                "review_text": text,
                "date":        published,
                "rating":      None,
                "language":    "en",
            })

            if len(scraped) >= per_board:
                break   # move to next board

    return scraped
