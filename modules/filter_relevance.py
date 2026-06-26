"""
modules/filter_relevance.py
---------------------------
Classifies reviews into HIGH / MEDIUM / LOW relevance tiers for music
discovery analysis, using deterministic weighted keyword scoring only.

No LLM calls are made here — fast, reproducible, quota-free.

Classification tiers
--------------------
  HIGH   — Review directly discusses discovery, recommendations, new
            artists/genres, repetitive listening, personalization,
            playlists, novelty, or recommendation trust.
            → Included in AI analysis.

  MEDIUM — Review indirectly impacts the discovery experience (e.g.
            shuffle behavior, user control, listening habits, mood
            context, library/saved songs).
            → Included in AI analysis.

  LOW    — Review has no meaningful connection to music discovery
            (billing, login, crashes, ads, general UI complaints).
            → Excluded from AI analysis.

Scoring weights
---------------
  HIGH keyword match   : +3 per keyword
  MEDIUM keyword match : +1 per keyword
  LOW keyword match    : -2 per keyword   (penalty)

Tier thresholds
---------------
  score >= 6  → HIGH
  score >= 2  → MEDIUM
  score <  2  → LOW

The low-keyword penalty is intentionally mild so that reviews mentioning
e.g. "ads ruined my discovery experience" still score positively due to
HIGH keyword matches.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Keyword lists
# ---------------------------------------------------------------------------

# HIGH: directly about discovery, recommendations, repetition, personalization
HIGH_KEYWORDS = [
    # Core discovery intent
    "discover", "discovery", "new music", "new artist", "new artists",
    "new genre", "new genres", "new song", "new track", "new band",
    "find new", "find music", "explore music",

    # Recommendation system
    "recommend", "recommendation", "recommendations", "algorithm",
    "suggestions", "suggestion", "personalization", "personalised",
    "personalized", "curated", "curation", "tailored",

    # Spotify discovery features (specific)
    "discover weekly", "release radar", "smart shuffle", "daily mix",
    "made for you", "spotify mix", "radio", "blend", "on repeat",
    "repeat mode", "spotify radio",

    # Repetitive listening (unwanted)
    "repetitive", "same songs", "same playlist", "same music",
    "same tracks", "same artists", "same thing", "shuffle repeat",
    "algorithm fatigue", "playlist fatigue", "stuck in a loop",
    "tired of the same", "always plays the same", "never shows me",
    "boring recommendations", "boring playlist", "stuck in a bubble",
    "echo chamber", "filter bubble",

    # Discovery failure / frustration
    "can't discover", "can't find new", "hard to find new",
    "never recommends", "doesn't recommend", "never shows",
    "outside my comfort zone", "broaden my taste", "widen my taste",
    "no variety", "lack of variety", "limited recommendations",
    "narrow recommendations", "algorithm is broken", "algorithm fails",
    "algorithm doesn't", "algorithm keeps", "algorithm only",

    # Repetition / looping keywords
    "loop", "repeat", "repetition",

    # Variety / diversity
    "variety", "diverse", "diversity", "different genres",
    "expand my taste", "musical exploration",

    # Trust in recommendations
    "trust", "trustworthy", "accurate recommendations",
    "inaccurate recommendations", "irrelevant recommendations",
    "off base", "wrong suggestions", "doesn't know my taste",
    "doesn't understand", "doesn't get my taste",

    # Novelty seeking
    "novelty", "novel music", "want something new",
    "something different", "fresh music", "fresh recommendations",
    "hidden gems", "underrated artists",

    # Explicit discovery behavior
    "explore", "exploration", "music journey", "deep cuts",
    "rabbit hole", "music discovery", "playlist exploration",
]

# MEDIUM: indirectly impacts the discovery experience
MEDIUM_KEYWORDS = [
    # Shuffle behavior
    "shuffle", "random", "autoplay", "auto play", "next song",
    "skip", "skipping", "queue",

    # User control over experience
    "control", "customize", "customise", "settings", "preferences",
    "fine-tune", "feedback", "thumbs up", "thumbs down", "heart",
    "like", "dislike", "not interested", "hide", "block artist",

    # Listening habits & taste
    "listening habits", "music taste", "taste", "music preferences",
    "what i like", "what i listen to", "genre", "genres",
    "artists i like", "favorite artists", "favourite artists",

    # Mood and context listening
    "mood", "context", "workout", "study", "focus", "relax",
    "party", "background music", "ambient", "sleep",

    # Library / saved content
    "library", "saved songs", "liked songs", "favorites",
    "favourites", "playlist", "playlists", "my playlist",
    "add to playlist", "saved playlist",

    # Discovery-adjacent features
    "related artists", "similar artists", "artist mix",
    "weekly", "radar", "wrapped", "listening history",
    "play history", "top songs", "top artists",
]

# LOW: non-discovery topics — penalize score
LOW_KEYWORDS = [
    # Billing / subscription
    "payment", "billing", "subscription price", "subscription cost",
    "premium price", "free tier", "charge", "refund", "invoice",
    "credit card", "cancel subscription", "pricing",

    # Login / account
    "login", "log in", "sign in", "sign up", "password",
    "forgot password", "reset password", "account locked",
    "two factor", "verification code",

    # App crashes / technical bugs
    "crash", "crashes", "crashing", "bug", "bugs", "glitch",
    "error message", "force close", "app freezes", "frozen",
    "not working", "stopped working", "won't open", "can't open",
    "app broke",

    # Performance
    "slow", "lagging", "lag", "loading", "buffering",
    "battery drain", "overheating",

    # Ads (standalone — not when combined with discovery context)
    # Note: mild penalty so "ads ruined discovery" still scores positively
    "too many ads", "unskippable ads", "ad break",

    # Offline / storage
    "offline mode", "can't download", "storage issue",
    "sync issue", "cache",

    # Unrelated content types
    "podcast", "audiobook", "lyrics display", "karaoke",

    # Pure UI complaints
    "dark mode", "widget broken", "lock screen", "notification spam",
    "ui change", "update ruined", "new update", "interface change",

    # Cross-platform / hardware
    "alexa", "google home", "chromecast", "bluetooth issue",
    "airpods", "car mode", "siri",
]

# ---------------------------------------------------------------------------
# Tier thresholds
# ---------------------------------------------------------------------------
SCORE_HIGH_THRESHOLD = 6
SCORE_MEDIUM_THRESHOLD = 2


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def score_review(text: str) -> int:
    """
    Compute a weighted relevance score for a single review.

    Weights:
        HIGH keyword   → +3
        MEDIUM keyword → +1
        LOW keyword    → -2

    Args:
        text: Raw review string (any case).

    Returns:
        Integer score. Can be negative.
    """
    t = text.lower()
    score = sum(3 for kw in HIGH_KEYWORDS if kw in t)
    score += sum(1 for kw in MEDIUM_KEYWORDS if kw in t)
    score -= sum(2 for kw in LOW_KEYWORDS if kw in t)
    return score


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------

def classify_tier(score: int) -> str:
    """
    Map a numeric relevance score to a tier label.

    Returns:
        'HIGH'   if score >= SCORE_HIGH_THRESHOLD  (6)
        'MEDIUM' if score >= SCORE_MEDIUM_THRESHOLD (2)
        'LOW'    otherwise
    """
    if score >= SCORE_HIGH_THRESHOLD:
        return "HIGH"
    elif score >= SCORE_MEDIUM_THRESHOLD:
        return "MEDIUM"
    else:
        return "LOW"


# ---------------------------------------------------------------------------
# Main filter function
# ---------------------------------------------------------------------------

def filter_relevant(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify every review and return only HIGH + MEDIUM tier reviews.

    Process:
      1. Score each review with score_review().
      2. Assign a relevance_tier (HIGH / MEDIUM / LOW).
      3. Return rows where tier is HIGH or MEDIUM, sorted by score desc.

    Args:
        df: DataFrame from loader_excel.load_preloaded_reviews().
            Must contain a 'review_text' column.

    Returns:
        Filtered DataFrame with two new columns:
          - relevance_score : int
          - relevance_tier  : 'HIGH' | 'MEDIUM'
        Sorted by relevance_score descending, index reset.
    """
    df = df.copy()
    df["relevance_score"] = df["review_text"].apply(score_review)
    df["relevance_tier"] = df["relevance_score"].apply(classify_tier)

    relevant = (
        df[df["relevance_tier"].isin(["HIGH", "MEDIUM"])]
        .sort_values("relevance_score", ascending=False)
        .reset_index(drop=True)
    )
    return relevant


def classify_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score and classify ALL reviews (including LOW tier) without filtering.
    Useful for generating the full tier breakdown shown in the UI overview.

    Returns:
        Full DataFrame with relevance_score and relevance_tier columns,
        sorted by score descending.
    """
    df = df.copy()
    df["relevance_score"] = df["review_text"].apply(score_review)
    df["relevance_tier"] = df["relevance_score"].apply(classify_tier)
    return df.sort_values("relevance_score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Diagnostic summary
# ---------------------------------------------------------------------------

def filter_summary(original_df: pd.DataFrame, filtered_df: pd.DataFrame) -> dict:
    """
    Return a detailed per-tier summary for UI display and logging.

    Args:
        original_df : Full DataFrame before filtering (all tiers).
        filtered_df : Filtered DataFrame (HIGH + MEDIUM only).

    Returns:
        dict with keys:
          total         — total reviews in original_df
          high          — count of HIGH tier reviews
          medium        — count of MEDIUM tier reviews
          low           — count of LOW tier reviews
          used_for_ai   — count used in AI pipeline (HIGH + MEDIUM)
          high_pct      — % of total that are HIGH
          medium_pct    — % of total that are MEDIUM
          low_pct       — % of total that are LOW
          low_count_warning — True if used_for_ai < 30
    """
    total = len(original_df)

    # Classify all reviews to get tier counts
    all_classified = classify_all(original_df)
    tier_counts = all_classified["relevance_tier"].value_counts().to_dict()

    high   = tier_counts.get("HIGH", 0)
    medium = tier_counts.get("MEDIUM", 0)
    low    = tier_counts.get("LOW", 0)
    used   = high + medium

    def pct(n):
        return round(n / total * 100, 1) if total > 0 else 0.0

    return {
        "total":             total,
        "high":              high,
        "medium":            medium,
        "low":               low,
        "used_for_ai":       used,
        "high_pct":          pct(high),
        "medium_pct":        pct(medium),
        "low_pct":           pct(low),
        "low_count_warning": used < 30,
    }

