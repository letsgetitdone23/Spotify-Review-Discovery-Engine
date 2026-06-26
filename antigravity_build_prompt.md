# Antigravity Build Prompt — Spotify Review Discovery Engine
**Paste this entire file into Antigravity as your first message.**

---

## What You Are Building

A Streamlit web app called the **Spotify AI-Powered Review Discovery Engine**.

It analyzes user reviews to answer six research questions about why Spotify users struggle to discover new music and why they get stuck in repetitive listening.

This is a **2-day build**. Follow the Day 1 and Day 2 scope exactly. Do not build anything outside the scope listed below.

---

## Day 1 Scope (Build This First — Must Work Before Day 2)

1. Load and normalize a preloaded Excel file from `data/reviews_preloaded.xlsx`
2. Filter reviews for discovery relevance using keyword scoring
3. Run a 3-call AI analysis pipeline using Groq API
4. Render a full 6-section report in the Streamlit UI
5. Apply Spotify-inspired dark visual theme
6. Deploy to Streamlit Community Cloud

**Day 1 is done when:** The deployed app loads the Excel file, runs analysis, and renders all 6 report sections without errors.

## Day 2 Scope (Add After Day 1 Is Deployed)

1. Add Google Play Store live scraping (via `google-play-scraper`)
2. Add Apple App Store live scraping (via iTunes RSS)
3. Add a mode toggle in the sidebar (Live vs Preloaded)
4. Add Markdown and CSV export download buttons

---

## Project Structure

Create exactly this folder and file structure:

```
spotify-review-engine/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   └── reviews_preloaded.xlsx        # Student adds this file — do not create it
├── modules/
│   ├── loader_excel.py
│   ├── scraper_playstore.py          # Day 2
│   ├── scraper_appstore.py           # Day 2
│   ├── filter_relevance.py
│   ├── key_manager.py
│   ├── ai_pipeline.py
│   ├── prompts.py
│   └── exporter.py                   # Day 2
└── components/
    ├── sidebar.py
    └── report_renderer.py
```

---

## Requirements File

```
streamlit
pandas
openpyxl
requests
beautifulsoup4
google-play-scraper
groq
google-generativeai
python-dotenv
langdetect
fpdf2
```

---

## Environment Variables

Create `.env.example` with:

```
GROQ_API_KEY_1=
GROQ_API_KEY_2=
GEMINI_API_KEY_1=
GEMINI_API_KEY_2=
```

**Never hardcode any API key in any Python file.**

Load keys in code using:
```python
from dotenv import load_dotenv
load_dotenv()
```

On Streamlit Cloud, keys are set via the Secrets panel and accessed with `st.secrets` or `os.getenv`.

---

## API Key Manager — `modules/key_manager.py`

```python
import os

class APIKeyManager:
    def __init__(self):
        self.keys = [
            {"provider": "groq",   "key": os.getenv("GROQ_API_KEY_1")},
            {"provider": "groq",   "key": os.getenv("GROQ_API_KEY_2")},
            {"provider": "gemini", "key": os.getenv("GEMINI_API_KEY_1")},
            {"provider": "gemini", "key": os.getenv("GEMINI_API_KEY_2")},
        ]
        # Remove entries with no key set
        self.keys = [k for k in self.keys if k["key"]]
        self.index = 0

    def current(self):
        if not self.keys:
            raise ValueError("No API keys configured.")
        return self.keys[self.index]

    def rotate(self):
        self.index = (self.index + 1) % len(self.keys)
        return self.current()
```

---

## LLM Call Function — inside `modules/ai_pipeline.py`

```python
import time
import json
from groq import Groq
import google.generativeai as genai
from modules.key_manager import APIKeyManager

key_manager = APIKeyManager()

def call_llm(prompt: str, max_retries: int = 4) -> str:
    """
    Call the LLM with automatic key rotation on failure.
    Returns the raw text response string.
    """
    for attempt in range(max_retries):
        key_info = key_manager.current()
        try:
            if key_info["provider"] == "groq":
                client = Groq(api_key=key_info["key"])
                response = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.3,
                )
                return response.choices[0].message.content

            elif key_info["provider"] == "gemini":
                genai.configure(api_key=key_info["key"])
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                return response.text

        except Exception as e:
            err = str(e).lower()
            if "429" in err or "rate" in err or "quota" in err or "limit" in err:
                key_manager.rotate()
                time.sleep(5)
            else:
                raise e

    raise RuntimeError("All API keys exhausted or failed after retries.")


def parse_json_response(raw: str) -> any:
    """
    Safely parse a JSON response from the LLM.
    Strips markdown code fences if present.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())
```

---

## Data Loader — `modules/loader_excel.py`

```python
import pandas as pd

EXCEL_PATH = "data/reviews_preloaded.xlsx"

def load_preloaded_reviews() -> pd.DataFrame:
    """
    Load the preloaded Excel file and normalize columns.
    Required columns: review_text, source
    Optional: date, rating, language
    """
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")

    # Normalize column names to lowercase
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "review_text" not in df.columns:
        raise ValueError("Excel file must have a 'review_text' column.")
    if "source" not in df.columns:
        df["source"] = "Unknown"

    # Fill optional columns
    for col in ["date", "rating", "language"]:
        if col not in df.columns:
            df[col] = None

    # Clean
    df = df.dropna(subset=["review_text"])
    df["review_text"] = df["review_text"].astype(str).str.strip()
    df = df[df["review_text"].str.len() >= 20]
    df = df.drop_duplicates(subset=["review_text"])
    df = df.reset_index(drop=True)

    return df
```

---

## Relevance Filter — `modules/filter_relevance.py`

**Use keyword scoring only. Do NOT send every review to the LLM for filtering — it wastes API quota.**

```python
HIGH_RELEVANCE = [
    "discover", "discovery", "new music", "new artist", "new genre",
    "recommend", "recommendation", "algorithm", "discover weekly",
    "release radar", "smart shuffle", "radio", "repetitive", "same songs",
    "same playlist", "shuffle repeat", "algorithm fatigue", "stuck in a loop",
    "tired of the same", "personalization", "boring recommendations",
    "never shows me", "always plays the same", "variety", "suggestion",
    "explore", "familiar", "loop", "repeat", "curated", "playlist fatigue"
]

LOW_RELEVANCE = [
    "login", "password", "payment", "crash", "bug", "offline",
    "download", "podcast", "lyrics", "dark mode", "widget", "billing",
    "subscription", "account", "sign in", "storage"
]

def score_review(text: str) -> int:
    t = text.lower()
    score = sum(2 for kw in HIGH_RELEVANCE if kw in t)
    score -= sum(1 for kw in LOW_RELEVANCE if kw in t)
    return score

def filter_relevant(df):
    df = df.copy()
    df["relevance_score"] = df["review_text"].apply(score_review)
    relevant = df[df["relevance_score"] >= 2].reset_index(drop=True)
    return relevant
```

---

## Prompts — `modules/prompts.py`

Build exactly **3 prompts**. This is the full AI pipeline — no more, no fewer.

```python
def prompt_themes_and_filter(reviews_block: str) -> str:
    return f"""
You are a UX researcher analyzing Spotify user reviews about music discovery.

Below are user reviews. First, identify the top recurring themes related to:
- music discovery failures
- repetitive listening (distinguish UNWANTED repetition caused by poor discovery 
  from INTENTIONAL repetition the user chose)
- recommendation quality
- algorithm frustrations

For each theme return:
- theme name
- short description
- frequency: High / Medium / Low
- one paraphrased review example

Return ONLY valid JSON. No preamble. No markdown fences.

Format:
[{{"theme": "...", "description": "...", "frequency": "High/Medium/Low", "example": "..."}}]

Reviews:
{reviews_block}
"""

def prompt_six_questions_and_segments(summary: str, n_reviews: int) -> str:
    return f"""
You are a product researcher. Below is a summary of themes from {n_reviews} Spotify user reviews
about music discovery and repetitive listening.

Answer all six questions AND identify user segments. Return ONLY valid JSON. No preamble.

RULES:
- Segment users by listening USE-CASE only. Never by age, income, or demographics 
  unless a review explicitly mentions them.
- For Q4, explicitly separate UNWANTED repetition (algorithm failure) 
  from INTENTIONAL repetition (user preference). Do not treat intentional repetition as a problem.
- Do not include product suggestions, MVP ideas, or feature recommendations anywhere.
- Be specific. Avoid generic answers like "users want better recommendations."

Return this exact JSON structure:
{{
  "q1": "Why users struggle to discover new music",
  "q2": "Most common recommendation frustrations",
  "q3": "Listening behaviors users are trying to achieve",
  "q4": {{
    "unwanted_repetition": "Causes of unwanted repetition",
    "intentional_repetition": "Where repetition is deliberate user choice"
  }},
  "q5": "User segments experiencing different challenges",
  "q6": "Unmet needs emerging from reviews",
  "segments": [
    {{
      "name": "Segment name (use-case based)",
      "what_they_do": "...",
      "discovery_blocker": "...",
      "repetition_type": "Unwanted / Intentional / Mixed",
      "evidence": "Paraphrased review example"
    }}
  ]
}}

Theme summary:
{summary}
"""

def prompt_root_causes_and_needs(summary: str) -> str:
    return f"""
You are identifying root causes of music discovery failure on Spotify and extracting unmet user needs.

RULES:
- Treat repetitive listening as a SYMPTOM. Find the underlying cause.
- State causes only. Do not suggest solutions.
- Unmet needs must be framed as "Users need..." or "Listeners want..." — never as product features.
- No MVP suggestions. No product roadmap language.

Return ONLY valid JSON. No preamble. No markdown fences.

{{
  "root_causes": ["...", "..."],
  "unwanted_repetition_causes": ["...", "..."],
  "intentional_repetition_note": "...",
  "unmet_needs": [
    {{"need": "...", "evidence": "...", "segment": "..."}}
  ]
}}

Summary:
{summary}
"""
```

---

## AI Pipeline Orchestrator — `modules/ai_pipeline.py` (continued)

Add this function after the `call_llm` and `parse_json_response` functions:

```python
from modules.prompts import (
    prompt_themes_and_filter,
    prompt_six_questions_and_segments,
    prompt_root_causes_and_needs
)

def run_analysis(df) -> dict:
    """
    Run the full 3-call AI analysis pipeline on a filtered reviews DataFrame.
    Returns a structured report dict.
    """
    # Prepare review text — batch into chunks of 30, summarize to save tokens
    reviews = df["review_text"].tolist()
    
    # Chunk reviews into batches of 30
    batch_size = 30
    batches = [reviews[i:i+batch_size] for i in range(0, len(reviews), batch_size)]
    
    # --- CALL 1: Theme extraction (run on first 3 batches max to save tokens) ---
    all_themes = []
    for batch in batches[:3]:
        block = "\n---\n".join(batch)
        raw = call_llm(prompt_themes_and_filter(block))
        try:
            themes = parse_json_response(raw)
            all_themes.extend(themes)
        except Exception:
            pass  # Skip failed batch, continue

    # Deduplicate themes by name
    seen = set()
    unique_themes = []
    for t in all_themes:
        if t.get("theme", "").lower() not in seen:
            seen.add(t.get("theme", "").lower())
            unique_themes.append(t)

    # Build a compressed summary for calls 2 and 3
    theme_summary = "\n".join(
        [f"- {t['theme']} ({t['frequency']}): {t['description']}" for t in unique_themes]
    )

    # --- CALL 2: Six questions + segments ---
    raw2 = call_llm(prompt_six_questions_and_segments(theme_summary, len(reviews)))
    try:
        questions_and_segments = parse_json_response(raw2)
    except Exception:
        questions_and_segments = {"error": "Analysis failed for this section."}

    # --- CALL 3: Root causes + unmet needs ---
    raw3 = call_llm(prompt_root_causes_and_needs(theme_summary))
    try:
        root_and_needs = parse_json_response(raw3)
    except Exception:
        root_and_needs = {"error": "Analysis failed for this section."}

    return {
        "themes": unique_themes,
        "questions": questions_and_segments,
        "root_causes_and_needs": root_and_needs,
    }
```

---

## Visual Theme — Apply in `app.py`

```python
SPOTIFY_CSS = """
<style>
    /* Base */
    .stApp { background-color: #121212; color: #FFFFFF; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #000000; }
    
    /* Primary button */
    .stButton > button {
        background-color: #1DB954;
        color: #000000;
        font-weight: 700;
        border: none;
        border-radius: 500px;
        padding: 0.6rem 2rem;
    }
    .stButton > button:hover { background-color: #1ed760; }
    
    /* Cards */
    .insight-card {
        background-color: #282828;
        border-radius: 8px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
    }
    
    /* Frequency badge */
    .badge-high   { background: #1DB954; color: #000; padding: 2px 10px; border-radius: 500px; font-size: 0.75rem; font-weight: 700; }
    .badge-medium { background: #E8A400; color: #000; padding: 2px 10px; border-radius: 500px; font-size: 0.75rem; font-weight: 700; }
    .badge-low    { background: #535353; color: #fff; padding: 2px 10px; border-radius: 500px; font-size: 0.75rem; font-weight: 700; }
    
    /* Source tag */
    .source-tag { background: #333; color: #B3B3B3; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
    
    /* Section header */
    .section-header { color: #1DB954; font-size: 1.1rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem; }
    
    /* Muted text */
    .muted { color: #B3B3B3; font-size: 0.9rem; }
    
    /* Divider */
    hr { border-color: #282828; }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab"] { color: #B3B3B3; }
    .stTabs [aria-selected="true"] { color: #1DB954; border-bottom-color: #1DB954; }
</style>
"""

st.markdown(SPOTIFY_CSS, unsafe_allow_html=True)
```

---

## Report Renderer — `components/report_renderer.py`

Build 6 rendering functions, one per section. Use `st.tabs` for navigation.

```python
import streamlit as st

def render_dataset_overview(df, filtered_df, mode):
    st.markdown('<div class="section-header">Dataset Overview</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Reviews", len(df))
    col2.metric("Discovery-Relevant", len(filtered_df))
    col3.metric("Mode", mode)
    
    st.markdown("**Source breakdown**")
    source_counts = filtered_df["source"].value_counts().reset_index()
    source_counts.columns = ["Source", "Count"]
    source_counts["% of Total"] = (source_counts["Count"] / len(filtered_df) * 100).round(1).astype(str) + "%"
    st.dataframe(source_counts, hide_index=True)


def render_themes(themes):
    st.markdown('<div class="section-header">Discovery Theme Analysis</div>', unsafe_allow_html=True)
    for t in themes:
        badge_class = f"badge-{t.get('frequency', 'Low').lower()}"
        st.markdown(f"""
        <div class="insight-card">
            <strong>{t.get('theme', 'Theme')}</strong>
            &nbsp;<span class="{badge_class}">{t.get('frequency', '')}</span>
            <p class="muted" style="margin-top:0.5rem">{t.get('description', '')}</p>
            <p style="font-size:0.85rem; border-left: 3px solid #1DB954; padding-left: 0.8rem; color:#ccc">
                "{t.get('example', '')}"
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_six_questions(questions):
    st.markdown('<div class="section-header">Answers to the Six Brief Questions</div>', unsafe_allow_html=True)
    labels = {
        "q1": "Why do users struggle to discover new music?",
        "q2": "What are the most common recommendation frustrations?",
        "q3": "What listening behaviors are users trying to achieve?",
        "q4": "What causes users to repeatedly listen to the same content?",
        "q5": "Which user segments experience different challenges?",
        "q6": "What unmet needs emerge consistently?",
    }
    for key, label in labels.items():
        with st.expander(label):
            val = questions.get(key, "Not available.")
            if isinstance(val, dict):
                for k, v in val.items():
                    st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
            else:
                st.write(val)


def render_segments(questions):
    st.markdown('<div class="section-header">Use-Case Based User Segments</div>', unsafe_allow_html=True)
    segments = questions.get("segments", [])
    if not segments:
        st.info("No segments identified.")
        return
    for seg in segments:
        st.markdown(f"""
        <div class="insight-card">
            <strong>{seg.get('name', 'Segment')}</strong>
            <p class="muted">{seg.get('what_they_do', '')}</p>
            <p><span style="color:#1DB954">Discovery blocker:</span> {seg.get('discovery_blocker', '')}</p>
            <p><span style="color:#1DB954">Repetition type:</span> {seg.get('repetition_type', '')}</p>
            <p style="font-size:0.85rem; border-left: 3px solid #535353; padding-left: 0.8rem; color:#ccc">
                "{seg.get('evidence', '')}"
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_root_causes(data):
    st.markdown('<div class="section-header">Root Cause Synthesis</div>', unsafe_allow_html=True)
    st.markdown("**Primary root causes of failed discovery:**")
    for c in data.get("root_causes", []):
        st.markdown(f"- {c}")
    st.markdown("**Causes of unwanted repetition:**")
    for c in data.get("unwanted_repetition_causes", []):
        st.markdown(f"- {c}")
    note = data.get("intentional_repetition_note", "")
    if note:
        st.info(f"ℹ️ **On intentional repetition:** {note}")


def render_unmet_needs(data):
    st.markdown('<div class="section-header">Unmet Needs</div>', unsafe_allow_html=True)
    needs = data.get("unmet_needs", [])
    if not needs:
        st.info("No unmet needs identified.")
        return
    for n in needs:
        st.markdown(f"""
        <div class="insight-card">
            <strong>{n.get('need', '')}</strong>
            <p class="muted">Segment: {n.get('segment', 'General')}</p>
            <p style="font-size:0.85rem; color:#ccc">{n.get('evidence', '')}</p>
        </div>
        """, unsafe_allow_html=True)
```

---

## Main App — `app.py`

```python
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from modules.loader_excel import load_preloaded_reviews
from modules.filter_relevance import filter_relevant
from modules.ai_pipeline import run_analysis
from components.report_renderer import (
    render_dataset_overview, render_themes, render_six_questions,
    render_segments, render_root_causes, render_unmet_needs
)

# --- Page config ---
st.set_page_config(
    page_title="Spotify Review Discovery Engine",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Apply CSS (paste SPOTIFY_CSS block here) ---
# [paste the SPOTIFY_CSS st.markdown block here]

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🎵 Discovery Engine")
    st.markdown("---")
    mode = st.radio("Analysis Mode", ["Preloaded Dataset", "Live Collection"])
    st.markdown("---")
    run_btn = st.button("▶ Run Analysis", use_container_width=True)

# --- Main Panel ---
st.title("Spotify Review Discovery Engine")
st.markdown('<p class="muted">AI-powered analysis of user reviews — focused on music discovery and repetitive listening behavior.</p>', unsafe_allow_html=True)

if "report" not in st.session_state:
    st.session_state.report = None
    st.session_state.df = None
    st.session_state.filtered_df = None

if run_btn:
    with st.spinner("Loading reviews..."):
        try:
            if mode == "Preloaded Dataset":
                df = load_preloaded_reviews()
            else:
                # Day 2: wire live scrapers here
                st.warning("Live mode not yet implemented. Falling back to preloaded dataset.")
                df = load_preloaded_reviews()

            st.session_state.df = df
        except Exception as e:
            st.error(f"Failed to load reviews: {e}")
            st.stop()

    with st.spinner("Filtering for discovery-relevant reviews..."):
        filtered_df = filter_relevant(df)
        st.session_state.filtered_df = filtered_df
        if len(filtered_df) < 30:
            st.warning(f"Only {len(filtered_df)} discovery-relevant reviews found. Results may be limited.")

    with st.spinner("Running AI analysis (3 calls)... this takes ~30–60 seconds"):
        try:
            report = run_analysis(filtered_df)
            st.session_state.report = report
        except Exception as e:
            st.error(f"AI analysis failed: {e}")
            st.stop()

    st.success("Analysis complete!")

# --- Render Report ---
if st.session_state.report:
    report = st.session_state.report
    df = st.session_state.df
    filtered_df = st.session_state.filtered_df

    tabs = st.tabs([
        "📊 Overview",
        "🎯 Themes",
        "❓ Six Questions",
        "👤 Segments",
        "🔍 Root Causes",
        "💡 Unmet Needs"
    ])

    with tabs[0]: render_dataset_overview(df, filtered_df, mode)
    with tabs[1]: render_themes(report.get("themes", []))
    with tabs[2]: render_six_questions(report.get("questions", {}))
    with tabs[3]: render_segments(report.get("questions", {}))
    with tabs[4]: render_root_causes(report.get("root_causes_and_needs", {}))
    with tabs[5]: render_unmet_needs(report.get("root_causes_and_needs", {}))

else:
    st.markdown("""
    <div class="insight-card" style="text-align:center; padding: 3rem;">
        <h3>Ready to analyze</h3>
        <p class="muted">Select a mode in the sidebar and click <strong>Run Analysis</strong> to begin.</p>
    </div>
    """, unsafe_allow_html=True)
```

---

## Day 2 Additions

### `modules/scraper_playstore.py`

```python
from google_play_scraper import reviews, Sort

def scrape_playstore(count=300) -> list:
    try:
        result, _ = reviews(
            "com.spotify.music",
            lang="en",
            country="in",
            sort=Sort.NEWEST,
            count=count,
        )
        return [{"source": "Play Store", "review_text": r["content"],
                 "date": str(r.get("at", "")), "rating": r.get("score")} for r in result]
    except Exception as e:
        print(f"Play Store scrape failed: {e}")
        return []
```

### `modules/scraper_appstore.py`

```python
import requests

def scrape_appstore() -> list:
    url = "https://itunes.apple.com/in/rss/customerreviews/id=324684580/sortBy=mostRecent/json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        entries = data.get("feed", {}).get("entry", [])[1:]  # skip first (app info)
        return [{"source": "App Store", "review_text": e["content"]["label"],
                 "date": e.get("updated", {}).get("label", ""),
                 "rating": e.get("im:rating", {}).get("label")} for e in entries]
    except Exception as e:
        print(f"App Store scrape failed: {e}")
        return []
```

### `modules/exporter.py`

```python
import pandas as pd
import json

def export_markdown(report: dict, df_stats: dict) -> str:
    lines = ["# Spotify Review Discovery Engine — Analysis Report\n"]
    lines.append(f"**Total reviews analyzed:** {df_stats.get('total', 'N/A')}  ")
    lines.append(f"**Discovery-relevant reviews:** {df_stats.get('filtered', 'N/A')}\n")
    lines.append("---\n## Themes\n")
    for t in report.get("themes", []):
        lines.append(f"### {t['theme']} ({t['frequency']})")
        lines.append(f"{t['description']}\n> {t['example']}\n")
    lines.append("---\n## Six Brief Questions\n")
    q = report.get("questions", {})
    for key in ["q1", "q2", "q3", "q4", "q5", "q6"]:
        val = q.get(key, "N/A")
        lines.append(f"**{key.upper()}:** {json.dumps(val) if isinstance(val, dict) else val}\n")
    lines.append("---\n## Root Causes\n")
    rc = report.get("root_causes_and_needs", {})
    for c in rc.get("root_causes", []):
        lines.append(f"- {c}")
    lines.append("\n## Unmet Needs\n")
    for n in rc.get("unmet_needs", []):
        lines.append(f"- **{n['need']}** *(Segment: {n['segment']})*\n  {n['evidence']}\n")
    return "\n".join(lines)


def export_csv(report: dict) -> str:
    rows = []
    for t in report.get("themes", []):
        rows.append({"section": "Theme", "item": t["theme"],
                     "detail": t["description"], "evidence": t["example"]})
    rc = report.get("root_causes_and_needs", {})
    for n in rc.get("unmet_needs", []):
        rows.append({"section": "Unmet Need", "item": n["need"],
                     "detail": n.get("segment", ""), "evidence": n["evidence"]})
    return pd.DataFrame(rows).to_csv(index=False)
```

Add these buttons at the bottom of the report in `app.py` (Day 2):

```python
if st.session_state.report:
    st.markdown("---")
    st.markdown("### Export Report")
    from modules.exporter import export_markdown, export_csv
    col1, col2 = st.columns(2)
    stats = {"total": len(st.session_state.df), "filtered": len(st.session_state.filtered_df)}
    with col1:
        st.download_button("⬇ Download Markdown", export_markdown(report, stats),
                           file_name="spotify_discovery_report.md", mime="text/markdown")
    with col2:
        st.download_button("⬇ Download CSV", export_csv(report),
                           file_name="spotify_discovery_report.csv", mime="text/csv")
```

---

## Deployment Checklist

Before pushing to GitHub and deploying on Streamlit Cloud:

- [ ] `data/reviews_preloaded.xlsx` is in the repo (committed, not gitignored)
- [ ] `.env` is in `.gitignore` — never commit real keys
- [ ] `requirements.txt` is complete
- [ ] All 4 API key variables are set in Streamlit Cloud Secrets panel
- [ ] Mode 2 (Preloaded) runs end-to-end on the deployed URL
- [ ] No Python traceback is visible to users on any failure

**Streamlit Cloud Secrets format:**
```toml
GROQ_API_KEY_1 = "gsk_..."
GROQ_API_KEY_2 = "gsk_..."
GEMINI_API_KEY_1 = "AIza..."
GEMINI_API_KEY_2 = "AIza..."
```

---

## What This Must NOT Include (Scope Guard)

The app and its AI output must never contain:

- Interview plans or user research plans
- MVP feature suggestions
- Product roadmap items
- "Spotify should build X" language
- Part 2, 3, or 4 deliverables

If the LLM returns solution-oriented language in any section, display it as a user need ("Users want X") rather than a recommendation ("Spotify should build X").

---

*End of Antigravity Build Prompt — Spotify Review Discovery Engine*
*Day 1: Preloaded mode + 6-section report + deployed URL*
*Day 2: Live scraping + exports*
