"""
modules/scraper_playstore.py
----------------------------
Fetches recent reviews for Spotify from the Google Play Store.
Uses the google-play-scraper library.
"""

from google_play_scraper import Sort, reviews as playstore_reviews


def scrape_playstore_reviews(count: int = 300) -> list:
    """
    Fetch the latest reviews for Spotify from the Google Play Store (India, English).

    Args:
        count: The number of reviews to fetch (default: 300).

    Returns:
        List of dicts: [
            {"source": "Google Playstore", "review_text": str, "date": str, "rating": float, "language": "en"}
        ]
    """
    try:
        # Fetch reviews for Spotify Android app (com.spotify.music)
        result, _ = playstore_reviews(
            "com.spotify.music",
            lang="en",
            country="in",
            sort=Sort.NEWEST,
            count=count,
        )

        scraped = []
        for r in result:
            review_text = r.get("content")
            if not review_text:
                continue

            scraped.append({
                "source": "Google Playstore",
                "review_text": review_text.strip(),
                # Store date as ISO-formatted string
                "date": r.get("at").isoformat() if r.get("at") else None,
                "rating": float(r.get("score")) if r.get("score") is not None else None,
                "language": "en",
            })
        return scraped

    except Exception as e:
        # Return empty list and let caller handle warning/error gracefully
        print(f"Error scraping Google Play Store: {e}")
        return []
