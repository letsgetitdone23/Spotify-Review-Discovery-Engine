"""
modules/scraper_appstore.py
--------------------------
Fetches recent reviews for Spotify from the Apple App Store (India).
Uses the iTunes RSS customer reviews JSON feed.
"""

import requests


def scrape_appstore_reviews(count: int = 100) -> list:
    """
    Fetch the latest reviews for Spotify from the Apple App Store (India).

    Args:
        count: The number of reviews to fetch (capped by Apple RSS API to 100 per request).

    Returns:
        List of dicts: [
            {"source": "App Store", "review_text": str, "date": str, "rating": float, "language": "en"}
        ]
    """
    app_id = "324684580"  # Spotify app ID
    region = "in"         # India store

    url = f"https://itunes.apple.com/{region}/rss/customerreviews/id={app_id}/mostRecent/json"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"App Store RSS returned status code {response.status_code}")
            return []

        data = response.json()
        feed = data.get("feed", {})
        entries = feed.get("entry", [])

        # If there's only one entry or feed is empty, entries could be a dict or None
        if not isinstance(entries, list):
            if isinstance(entries, dict):
                entries = [entries]
            else:
                return []

        scraped = []
        for entry in entries:
            # The first entry in the RSS feed is often the application detail page, not a review.
            # Real reviews will have rating and content keys.
            rating_obj = entry.get("im:rating")
            content_obj = entry.get("content")

            if not rating_obj or not content_obj:
                continue

            review_text = content_obj.get("label", "")
            title = entry.get("title", {}).get("label", "")
            if title:
                # Combine title and body to get the full context of the review
                review_text = f"{title}: {review_text}"

            rating = rating_obj.get("label")
            date_val = entry.get("updated", {}).get("label")

            scraped.append({
                "source": "App Store",
                "review_text": review_text.strip(),
                "date": date_val,
                "rating": float(rating) if rating is not None else None,
                "language": "en",
            })

            # Respect the requested count
            if len(scraped) >= count:
                break

        return scraped

    except Exception as e:
        print(f"Error scraping Apple App Store: {e}")
        return []
