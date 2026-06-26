"""
modules/prompts.py
------------------
Prompt-builder functions for the 3-call AI analysis pipeline.

Rules enforced in every prompt:
  - Return ONLY valid JSON — no markdown fences, no preamble, no trailing text
  - Never suggest product features, MVPs, or roadmap items
  - Never use "Spotify should build X" language
  - Distinguish UNWANTED repetition (algorithm failure) from
    INTENTIONAL repetition (deliberate user choice)
  - Segment users by listening USE-CASE only — never by age, income,
    or demographics unless a review explicitly mentions them
  - Unmet needs framed as "Users need..." or "Listeners want..." — not
    as product specifications

These functions only build the prompt string. They never call the LLM.
The caller (ai_pipeline.run_analysis) passes the strings to call_llm().
"""


# ---------------------------------------------------------------------------
# Call 1 — Theme Extraction
# ---------------------------------------------------------------------------

def prompt_themes_and_filter(reviews_block: str) -> str:
    """
    Build the Call-1 prompt: extract recurring themes from a block of reviews.

    The LLM prioritises:
      - Music discovery failures
      - Repetitive listening (unwanted vs intentional — keep separate)
      - Recommendation quality and trust
      - Algorithm frustrations
      - Personalization failures
      - Novelty-seeking and exploration behavior

    Args:
        reviews_block: Reviews joined by "\\n---\\n" separators.

    Returns:
        Prompt string ready to pass to call_llm().

    LLM output format:
        JSON array — [{"theme": "...", "description": "...",
                       "frequency": "High|Medium|Low", "example": "..."}]
    """
    return f"""
You are a senior UX researcher analyzing Spotify user reviews about music discovery.

PRIORITY TOPICS — focus your theme extraction on:
  - Music discovery failures and friction
  - New artist / new genre discovery (or lack thereof)
  - Recommendation quality, diversity, and trustworthiness
  - Discover Weekly, Release Radar, Daily Mix, Smart Shuffle experiences
  - Playlist exploration and novelty seeking
  - Repetitive listening — IMPORTANT: distinguish carefully:
      * UNWANTED repetition caused by algorithm failure
      * INTENTIONAL repetition the user deliberately chose
  - Personalization accuracy and user control over recommendations
  - Recommendation loops and echo chambers

DEPRIORITIZE themes about billing, crashes, ads, login issues, or general UI
UNLESS the review explicitly connects them to discovery behavior.

Below are user reviews. Identify the top recurring themes related to the
priority topics above.

For each theme return:
  - theme      : short descriptive name
  - description: 1–2 sentence explanation of the theme
  - frequency  : "High" | "Medium" | "Low" based on how often it appears
  - example    : one paraphrased (not copied) review illustrating this theme

RULES:
  - Return ONLY valid JSON. No preamble. No markdown fences. No trailing text.
  - Never suggest product solutions or features.
  - Do NOT merge unwanted and intentional repetition into one theme.

Format — return a JSON array:
[{{"theme": "...", "description": "...", "frequency": "High|Medium|Low", "example": "..."}}]

Reviews:
{reviews_block}
"""


# ---------------------------------------------------------------------------
# Call 2 — Six Research Questions + User Segments
# ---------------------------------------------------------------------------

def prompt_six_questions_and_segments(summary: str, n_reviews: int) -> str:
    """
    Build the Call-2 prompt: answer 6 research questions and identify
    use-case-based user segments.

    Args:
        summary:   Compressed theme summary string built from Call-1 output.
        n_reviews: Total number of reviews analyzed (for context).

    Returns:
        Prompt string ready to pass to call_llm().

    LLM output format:
        JSON object matching the exact structure below.
    """
    return f"""
You are a product researcher. Below is a summary of themes extracted from
{n_reviews} Spotify user reviews about music discovery and repetitive listening.

Answer all six research questions AND identify user segments.

STRICT RULES:
  1. Segment users by listening USE-CASE only (e.g. "Mood-based listeners",
     "Genre explorers"). Never segment by age, income, or demographics
     unless a review explicitly mentions them.
  2. For Q4, you MUST explicitly separate:
       - UNWANTED repetition: caused by algorithm failure (a problem)
       - INTENTIONAL repetition: deliberate user choice (NOT a problem)
     Do not treat intentional repetition as a failure.
  3. Do NOT include product suggestions, MVP ideas, or feature recommendations
     anywhere in the response.
  4. Be specific. Avoid generic phrases like "users want better recommendations."
  5. Unmet needs must be framed as "Users need..." or "Listeners want..." —
     never as "Spotify should build..."
  6. Return ONLY valid JSON. No preamble. No markdown fences. No trailing text.

Return this EXACT JSON structure (do not add or remove any keys):
{{
  "q1": "Why users struggle to discover new music — specific causes from reviews",
  "q2": "Most common recommendation frustrations — specific patterns",
  "q3": "Listening behaviors users are trying to achieve — specific goals",
  "q4": {{
    "unwanted_repetition": "Specific causes of algorithm-driven unwanted repetition",
    "intentional_repetition": "Where and why repetition is a deliberate user choice"
  }},
  "q5": "Which user segments experience different discovery challenges",
  "q6": "Unmet needs emerging consistently — framed as user needs, not features",
  "segments": [
    {{
      "name": "Segment name — use-case based (e.g. 'Mood-based listeners')",
      "what_they_do": "How this segment uses Spotify for music",
      "discovery_blocker": "What specifically prevents this segment from discovering new music",
      "repetition_type": "Unwanted | Intentional | Mixed",
      "evidence": "Paraphrased review example from this segment"
    }}
  ]
}}

Theme summary from {n_reviews} reviews:
{summary}
"""


# ---------------------------------------------------------------------------
# Call 3 — Root Causes + Unmet Needs
# ---------------------------------------------------------------------------

def prompt_root_causes_and_needs(summary: str) -> str:
    """
    Build the Call-3 prompt: synthesize root causes of discovery failure,
    extract unmet user needs, and derive key insights with actionable takeaways.

    Args:
        summary: Compressed theme summary string built from Call-1 output.

    Returns:
        Prompt string ready to pass to call_llm().

    LLM output format:
        JSON object matching the exact structure below.
    """
    return f"""
You are a UX researcher identifying the root causes of music discovery failure
on Spotify, extracting the unmet needs, and synthesizing key actionable insights.

STRICT RULES:
  1. Treat repetitive listening as a SYMPTOM. Dig for the underlying cause
     (e.g. algorithm over-exploitation of known preferences, lack of serendipity
     mechanism, absence of user-controlled discovery modes).
  2. State root causes only. Do NOT suggest solutions or product features.
  3. Unmet needs MUST be framed as "Users need..." or "Listeners want..." —
     never as "Spotify should build X" or feature specifications.
  4. No MVP suggestions. No product roadmap language.
  5. Separate unwanted repetition causes from intentional repetition behavior.
  6. Key insights must focus on major systemic trends/observations from the reviews,
     and each must include a user-centric actionable takeaway.
  7. Return ONLY valid JSON. No preamble. No markdown fences. No trailing text.

Return this EXACT JSON structure (do not add or remove any keys):
{{
  "root_causes": [
    "Specific root cause 1 — why discovery fails at a systemic level",
    "Specific root cause 2",
    "..."
  ],
  "unwanted_repetition_causes": [
    "Specific cause of algorithm-driven repetition 1",
    "..."
  ],
  "intentional_repetition_note": "Brief note on where repetition is deliberate user behavior — not a failure",
  "unmet_needs": [
    {{
      "need": "Users need... / Listeners want...",
      "evidence": "Paraphrased review evidence supporting this need",
      "segment": "Which user segment this need most affects (use-case label, or 'General')"
    }}
  ],
  "key_insights": [
    {{
      "insight": "A major systemic insight or observation from the reviews",
      "impact": "The impact this has on the listener's engagement or satisfaction",
      "actionable_takeaway": "Actionable takeaway framed as a listener need (e.g. 'Listeners require...')"
    }}
  ]
}}

Theme summary:
{summary}
"""

