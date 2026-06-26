"""
modules/ai_pipeline.py
-----------------------
Orchestrates the 3-call LLM analysis pipeline on filtered Spotify reviews.

Pipeline flow:
  CALL 1 — Theme extraction   (batches of 30, max 3 batches)
  CALL 2 — Six questions + user segments
  CALL 3 — Root causes + unmet needs

Calls 2 and 3 receive a compressed theme_summary string (not raw reviews)
to minimize token usage and stay within LLM context limits.

LLM providers supported:
  - Groq  (llama-3.1-8b-instant) — primary, fastest
  - Gemini (gemini-1.5-flash)    — fallback

Key rotation:
  On 429 / rate-limit / quota errors the key manager rotates to the
  next available key and retries (up to max_retries attempts).
  Other exceptions are re-raised immediately.
"""

import time
import json
import re

from groq import Groq
from google import genai as google_genai

from modules.key_manager import APIKeyManager
from modules.prompts import (
    prompt_themes_and_filter,
    prompt_six_questions_and_segments,
    prompt_root_causes_and_needs,
)

# Key manager is created fresh inside run_analysis() on every call.
# DO NOT create it at module level — it would run before load_dotenv()
# and always see an empty environment.


# ---------------------------------------------------------------------------
# Core LLM call with automatic key rotation
# ---------------------------------------------------------------------------

def call_llm(prompt: str, key_manager: APIKeyManager, max_tokens: int = 1000, max_retries: int = 4) -> str:
    """
    Send a prompt to the current LLM provider and return the raw text response.

    On rate-limit / quota errors the key manager rotates to the next key
    and retries after a 5-second pause. Other exceptions are re-raised
    immediately (they indicate a prompt or logic problem, not a quota issue).

    Args:
        prompt:      Full prompt string to send.
        key_manager: APIKeyManager instance (created fresh in run_analysis).
        max_tokens:  Limit on model response tokens (default: 1000).
        max_retries: Maximum number of attempts before giving up (default: 4).

    Returns:
        Raw text response string from the LLM.

    Raises:
        RuntimeError: if all retry attempts fail.
        Exception:    any non-rate-limit error from the provider.
    """
    for attempt in range(max_retries):
        key_info = key_manager.current()
        try:
            if key_info["provider"] == "groq":
                client = Groq(api_key=key_info["key"])
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.3,
                )
                return response.choices[0].message.content

            elif key_info["provider"] == "gemini":
                client = google_genai.Client(api_key=key_info["key"])
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
                return response.text

        except Exception as e:
            err = str(e).lower()
            is_rate_limit = any(
                token in err
                for token in ("429", "rate", "quota", "limit", "resource_exhausted")
            )
            if is_rate_limit:
                key_manager.rotate()
                time.sleep(5)
            else:
                raise e  # non-quota errors are not retried

    raise RuntimeError(
        f"All {max_retries} LLM call attempts failed. "
        "Check API key validity and rate limit status."
    )


# ---------------------------------------------------------------------------
# JSON response parser
# ---------------------------------------------------------------------------

def parse_json_response(raw: str):
    """
    Safely parse a JSON response from the LLM.

    Handles common LLM quirks:
      - Strips leading/trailing whitespace
      - Removes ```json ... ``` or ``` ... ``` fences
      - Extracts the first valid JSON object/array if surrounded by prose

    Args:
        raw: Raw text string returned by the LLM.

    Returns:
        Parsed Python object (list or dict).

    Raises:
        json.JSONDecodeError: if no valid JSON can be extracted.
    """
    cleaned = raw.strip()

    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    if cleaned.startswith("```"):
        # Remove opening fence (```json or ```)
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        # Remove closing fence
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        cleaned = cleaned.strip()

    # If there's still surrounding prose, try to extract the JSON object/array
    # by finding the first { or [ and the matching closing bracket
    if not (cleaned.startswith("{") or cleaned.startswith("[")):
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if match:
            cleaned = match.group(1)

    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

def run_analysis(df) -> dict:
    """
    Run the full 3-call AI analysis pipeline on a filtered reviews DataFrame.

    The DataFrame must already be filtered to HIGH + MEDIUM relevance reviews
    (output of filter_relevance.filter_relevant()).

    Pipeline:
      CALL 1 — Theme extraction from batches of 30 reviews (max 3 batches).
               Deduplicates themes by name. Builds a compressed theme_summary.
      CALL 2 — Six research questions + use-case-based user segments.
               Input: theme_summary + total review count.
      CALL 3 — Root cause synthesis + unmet needs extraction.
               Input: theme_summary.

    Args:
        df: Filtered DataFrame with a 'review_text' column.

    Returns:
        dict with keys:
          "themes"               — list of theme dicts from Call 1
          "questions"            — dict from Call 2 (q1–q6 + segments)
          "root_causes_and_needs"— dict from Call 3
    """
    # Create a fresh key manager here — NEVER at module level.
    # This guarantees env vars are read after load_dotenv() has run.
    key_manager = APIKeyManager()

    reviews = df["review_text"].tolist()
    n_reviews = len(reviews)

    # ------------------------------------------------------------------
    # CALL 1 — Theme Extraction
    # Process up to 3 batches of 30 reviews each (90 reviews max)
    # This cap keeps Call 1 token usage predictable and within limits.
    # ------------------------------------------------------------------
    batch_size = 12
    batches = [reviews[i:i + batch_size] for i in range(0, n_reviews, batch_size)]

    all_themes = []
    for i, batch in enumerate(batches[:3]):
        if i > 0:
            time.sleep(1.0)  # brief pause to avoid hitting rapid-fire limits
        block = "\n---\n".join(batch)
        raw = call_llm(block_prompt := prompt_themes_and_filter(block), key_manager, max_tokens=1000)
        try:
            themes = parse_json_response(raw)
            if isinstance(themes, list):
                all_themes.extend(themes)
        except Exception:
            pass  # Skip a failed batch — continue with remaining batches

    # Deduplicate themes by name (case-insensitive)
    seen_themes: set = set()
    unique_themes = []
    for t in all_themes:
        name = t.get("theme", "").lower().strip()
        if name and name not in seen_themes:
            seen_themes.add(name)
            unique_themes.append(t)

    # Build compressed summary for Calls 2 and 3
    # Format: "- Theme Name (High): Short description"
    theme_summary = "\n".join(
        f"- {t.get('theme', 'Unknown')} ({t.get('frequency', 'Unknown')}): {t.get('description', '')}"
        for t in unique_themes
    )

    if not theme_summary:
        theme_summary = "No themes could be extracted from the provided reviews."

    # ------------------------------------------------------------------
    # CALL 2 — Six Questions + User Segments
    # ------------------------------------------------------------------
    time.sleep(1.0)
    raw2 = call_llm(prompt_six_questions_and_segments(theme_summary, n_reviews), key_manager, max_tokens=1500)
    try:
        questions_and_segments = parse_json_response(raw2)
        if not isinstance(questions_and_segments, dict):
            raise ValueError("Expected a JSON object from Call 2")
    except Exception as e:
        questions_and_segments = {
            "error": f"Six-question analysis failed: {e}",
            "segments": [],
        }

    # ------------------------------------------------------------------
    # CALL 3 — Root Causes + Unmet Needs
    # ------------------------------------------------------------------
    time.sleep(1.0)
    raw3 = call_llm(prompt_root_causes_and_needs(theme_summary), key_manager, max_tokens=1500)
    try:
        root_and_needs = parse_json_response(raw3)
        if not isinstance(root_and_needs, dict):
            raise ValueError("Expected a JSON object from Call 3")
    except Exception as e:
        root_and_needs = {
            "error": f"Root cause analysis failed: {e}",
            "root_causes": [],
            "unwanted_repetition_causes": [],
            "intentional_repetition_note": "",
            "unmet_needs": [],
        }

    # ------------------------------------------------------------------
    # Return structured report
    # ------------------------------------------------------------------
    return {
        "themes":                unique_themes,
        "questions":             questions_and_segments,
        "root_causes_and_needs": root_and_needs,
        "_meta": {
            "total_reviews_analyzed": n_reviews,
            "batches_processed":      min(len(batches), 3),
            "themes_extracted":       len(unique_themes),
        },
    }
