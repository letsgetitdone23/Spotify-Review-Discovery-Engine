"""
modules/scraper_reddit.py
--------------------------
Fetches recent posts and top comments from Spotify-related subreddits
via the Reddit OAuth2 "app-only" flow (no user login required).

Setup (one-time, free):
  1. Go to https://www.reddit.com/prefs/apps
  2. Click "Create App" → choose "script"
  3. Any redirect URI works (e.g. http://localhost)
  4. Copy client_id (shown under the app name) and client_secret
  5. Add to your .env:
       REDDIT_CLIENT_ID=your_client_id
       REDDIT_CLIENT_SECRET=your_client_secret

If credentials are missing the scraper returns [] gracefully — the rest
of the pipeline continues with other sources.

Target subreddits (discovery-focused):
  r/spotify          — general complaints and feature discussions
  r/SpotifyThefts    — algorithm frustrations
  r/ifyoulikeblank   — discovery behavior
  r/ListenToThis     — exploration behavior
"""

import os
import time
import requests

# Subreddits to scrape + the search query per subreddit
_TARGETS = [
    ("spotify",        "discovery OR recommendation OR algorithm OR repeat OR shuffle"),
    ("spotify",        "discover weekly OR release radar OR daily mix OR same song"),
    ("SpotifyThefts",  ""),                # this sub is already focused on algorithm issues
    ("ifyoulikeblank", "discover OR find OR recommend"),
]

# Keywords to keep only posts relevant to discovery/recommendation
_DISCOVERY_KEYWORDS = [
    "discover", "recommendation", "algorithm", "repeat", "same song",
    "new music", "new artist", "explore", "playlist", "shuffle",
    "discover weekly", "release radar", "daily mix", "smart shuffle",
    "suggestion", "variety", "genre", "taste", "personaliz", "loop",
    "keeps playing", "echo chamber", "filter bubble",
]

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_API_BASE  = "https://oauth.reddit.com"
_USER_AGENT = "SpotifyDiscoveryEngine/1.0 (research tool)"


def _get_token(client_id: str, client_secret: str) -> str | None:
    """Obtain an app-only OAuth2 token (no user login needed)."""
    try:
        resp = requests.post(
            _TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"User-Agent": _USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as e:
        print(f"Reddit token error: {e}")
        return None


def _is_relevant(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _DISCOVERY_KEYWORDS)


def scrape_reddit_posts(count: int = 150) -> list:
    """
    Fetch recent Reddit posts about Spotify music discovery.

    Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in env / .env.
    If missing, returns [] silently so the pipeline continues.

    Args:
        count: Approximate max posts to return.

    Returns:
        List of dicts:
          {"source": "Reddit", "review_text": str,
           "date": str | None, "rating": None, "language": "en"}
    """
    client_id     = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("Reddit credentials not set — skipping Reddit scraper.")
        return []

    token = _get_token(client_id, client_secret)
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": _USER_AGENT,
    }

    scraped = []
    per_target = max(5, count // len(_TARGETS))

    for subreddit, query in _TARGETS:
        if len(scraped) >= count:
            break

        try:
            if query:
                # Search within the subreddit
                url    = f"{_API_BASE}/r/{subreddit}/search"
                params = {
                    "q":          query,
                    "restrict_sr": "true",
                    "sort":       "new",
                    "limit":      min(per_target, 25),
                    "t":          "month",
                }
            else:
                # Just pull the newest posts
                url    = f"{_API_BASE}/r/{subreddit}/new"
                params = {"limit": min(per_target, 25)}

            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            posts = resp.json().get("data", {}).get("children", [])

        except Exception as e:
            print(f"Reddit fetch error for r/{subreddit}: {e}")
            continue

        for post in posts:
            if len(scraped) >= count:
                break

            data  = post.get("data", {})
            title = data.get("title", "")
            body  = data.get("selftext", "").strip()

            # Skip removed/deleted posts
            if body in ("[removed]", "[deleted]", ""):
                combined = title
            else:
                combined = f"{title}. {body}"

            combined = combined[:600]  # cap length

            if not combined or not _is_relevant(combined):
                continue

            created = data.get("created_utc")
            date_str = (
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(created))
                if created else None
            )

            scraped.append({
                "source":      "Reddit",
                "review_text": combined,
                "date":        date_str,
                "rating":      None,
                "language":    "en",
            })

        time.sleep(0.5)   # gentle rate limiting

    return scraped
