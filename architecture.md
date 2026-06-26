# Spotify AI-Powered Review Discovery Engine — Phase-wise Architecture

> **Stack:** Python · Streamlit · Groq API · Gemini API · Pandas  
> **Deployment Target:** Streamlit Community Cloud  
> **Build Timeline:** 2 days (Day 1 = Phases 0–4 | Day 2 = Phases 5–6)

---

## Overview

```
reviews_preloaded.xlsx
        │
        ▼
┌─────────────────────┐
│   Phase 1: Loader   │  ← Load ALL 5 sheets & normalize into one DataFrame
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   Phase 2: Filter   │  ← 3-tier relevance classification (HIGH/MEDIUM/LOW)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────┐
│   Phase 3: AI Pipeline      │  ← 3 sequential LLM calls (Groq/Gemini)
│   Call 1: Theme Extraction  │
│   Call 2: Six Questions     │
│   Call 3: Root Causes       │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│   Phase 4: Report UI        │  ← 7-tab Streamlit report
└─────────────────────────────┘
          │ (Day 2)
          ▼
┌─────────────────────────────┐
│   Phase 5: Live Scrapers    │  ← Play Store + App Store
└─────────────────────────────┘
          │
          ▼
┌─────────────────────────────┐
│   Phase 6: Exports          │  ← Markdown + CSV download
└─────────────────────────────┘
```

---

## Phase 0 — Project Scaffold & Configuration

**Goal:** Set up the full directory tree, dependencies, and environment before writing any logic.

### Files to Create
| File | Purpose |
|------|---------|
| `app.py` | Streamlit entry point (shell only at this phase) |
| `requirements.txt` | All Python dependencies |
| `.env.example` | Template for API keys (no real values) |
| `.gitignore` | Excludes `.env`, `__pycache__`, `.streamlit/secrets.toml` |
| `modules/__init__.py` | Makes `modules/` a package |
| `components/__init__.py` | Makes `components/` a package |

### `requirements.txt` Contents
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

### `.env.example` Contents
```
GROQ_API_KEY_1=
GROQ_API_KEY_2=
GEMINI_API_KEY_1=
GEMINI_API_KEY_2=
```

### `.gitignore` Contents
```
.env
__pycache__/
*.pyc
.streamlit/secrets.toml
```

### Validation Checkpoint
- [ ] `python -m streamlit run app.py` starts without import errors
- [ ] All directories exist: `data/`, `modules/`, `components/`

---

## Phase 1 — Data Loader (`modules/loader_excel.py`)

**Goal:** Load **all sheets** from `data/reviews_preloaded.xlsx` into a single clean, normalized, deduplicated Pandas DataFrame.

> ⚠️ **Bug fixed during implementation:** `pd.read_excel()` without `sheet_name` reads only the first sheet. The loader now iterates over all sheets using `pd.ExcelFile` and concatenates them.

### Workbook Structure (5 sheets)
| Sheet | Raw Rows | Valid Reviews |
|-------|----------|---------------|
| Google Playstore | 908 | 831 |
| App Store | 100 | 74 |
| Reddit | 1076 | 33 |
| Twitter | 29 | 29 |
| Community n Social | 9 | 9 |
| **Combined (deduped)** | — | **973** |

### Responsibilities
- Open workbook with `pd.ExcelFile` and iterate over every sheet
- Per sheet: normalize column names to `snake_case`, fill missing optional columns, default `source` to sheet name when blank, clean `review_text`
- Concatenate all sheet DataFrames into one
- Drop cross-sheet duplicate `review_text` values
- Reset index

### Output Schema
| Column | Type | Notes |
|--------|------|-------|
| `review_text` | str | Required — cleaned & stripped, min 20 chars |
| `source` | str | Sheet name used as fallback (e.g. `"Google Playstore"`) |
| `date` | str/None | Optional |
| `rating` | float/None | Optional |
| `language` | str/None | Optional |

### Key Logic
```
pd.ExcelFile → iterate sheets → _normalize_sheet() per sheet
    → pd.concat() → drop_duplicates(review_text) → reset_index → DataFrame
```

### Public Functions
| Function | Returns |
|----------|---------|
| `load_preloaded_reviews()` | Combined normalized DataFrame (all sheets) |
| `summarize_dataframe(df)` | Dict: total_reviews, sources dict, has_rating, has_date, has_language |

### Validation Checkpoint ✅
- [x] All 5 sheets loaded — **973 total reviews**
- [x] No null values in `review_text`
- [x] All expected columns present
- [x] Cross-sheet duplicates removed
- [x] Source defaults to sheet name (not `"Unknown"`)

---

## Phase 2 — Relevance Filter (`modules/filter_relevance.py`)

**Goal:** Classify every review into HIGH / MEDIUM / LOW relevance tiers and pass only HIGH + MEDIUM reviews to the AI pipeline — using **weighted keyword scoring only**, no LLM calls.

### Why Keyword Scoring (Not LLM)?
Sending 973 reviews to the LLM just for filtering would exhaust API quota. A deterministic, fast keyword scorer classifies all reviews in milliseconds.

### Analysis Priority (from spec)
**Prioritize reviews about:**
- Music discovery, new artist/genre discovery
- Recommendation quality, diversity, trust
- Discover Weekly / Release Radar experiences
- Playlist exploration, novelty seeking, exploration behavior
- Personalization, repetitive listening, recommendation loops
- Shuffle behavior, user control over recommendations

**Deprioritize (unless directly affecting discovery):**
- Billing, subscription pricing, payment issues
- Login, account problems, ads
- App crashes, technical bugs, performance, general UI

### 3-Tier Classification
| Tier | Definition | Used for AI? |
|------|-----------|-------------|
| **HIGH** | Directly discusses discovery, recommendations, new artists/genres, repetitive listening, personalization, playlists, novelty, recommendation trust | ✅ Yes |
| **MEDIUM** | Indirectly impacts discovery (shuffle behavior, user control, listening habits, mood context, library/saved songs) | ✅ Yes |
| **LOW** | No meaningful connection to music discovery (billing, login, crashes, ads, UI complaints) | ❌ No |

### Scoring Weights
| Keyword Type | Weight | Example Keywords |
|-------------|--------|------------------|
| HIGH keyword match | **+3** | `discover`, `recommendation`, `algorithm`, `repetitive`, `same songs`, `discover weekly`, `novelty`, `echo chamber`, `explore`... |
| MEDIUM keyword match | **+1** | `shuffle`, `playlist`, `genre`, `mood`, `library`, `liked songs`, `control`, `taste`, `feedback`... |
| LOW keyword match | **−2** | `billing`, `crash`, `password`, `too many ads`, `dark mode`, `podcast`, `bluetooth`... |

### Tier Thresholds
| Score Range | Tier |
|------------|------|
| ≥ 6 | HIGH |
| 2 – 5 | MEDIUM |
| < 2 | LOW |

> **Note on LOW penalty:** LOW keywords carry only −2 so a review like *"ads keep interrupting my Discover Weekly"* still scores positively from HIGH keyword hits — preserving reviews where deprioritized topics directly affect discovery.

### Output
- `filter_relevant(df)` returns HIGH + MEDIUM rows with `relevance_score` and `relevance_tier` columns, sorted by score descending
- `classify_all(df)` returns the full DataFrame with tier labels (for UI overview stats)
- `filter_summary(original, filtered)` returns per-tier counts and percentages

### Validation Results ✅ (on 973 reviews)
| Tier | Count | % of Total |
|------|-------|------------|
| HIGH | **116** | 11.9% |
| MEDIUM | **160** | 16.4% |
| LOW | 697 | 71.6% |
| **Used for AI (HIGH + MEDIUM)** | **276** | **28.4%** |

### Validation Checkpoint ✅
- [x] `filter_relevant(df)` returns only HIGH + MEDIUM rows
- [x] Output has `relevance_score` and `relevance_tier` columns
- [x] `filter_summary()` returns per-tier counts and percentages
- [x] Low count warning (`used_for_ai < 30`) — **False** (276 reviews used)
- [x] Low-penalty design preserves discovery-relevant reviews that mention deprioritized topics

---

## Phase 3 — AI Pipeline (`modules/key_manager.py` + `modules/prompts.py` + `modules/ai_pipeline.py`)

**Goal:** Run exactly **3 LLM calls** on the filtered reviews to extract themes, answer 6 research questions, and synthesize root causes.

### Sub-Phase 3a — Key Manager (`modules/key_manager.py`)

Manages a pool of Groq + Gemini API keys with round-robin rotation on rate-limit errors.

```
Key Pool: [GROQ_KEY_1, GROQ_KEY_2, GEMINI_KEY_1, GEMINI_KEY_2]
              ↓ on 429/rate-limit error
           rotate → next key → retry (up to 4 attempts)
```

| Method | Behaviour |
|--------|-----------|
| `current()` | Returns current key info dict `{provider, key}` |
| `rotate()` | Advances index mod len(keys) |

---

### Sub-Phase 3b — Prompts (`modules/prompts.py`)

Three prompt-builder functions. **Never hardcode review text inside prompts** — always pass as an argument.

| Function | Input | Output Format |
|----------|-------|--------------|
| `prompt_themes_and_filter(reviews_block)` | Raw review text block | `[{theme, description, frequency, example}]` — JSON array |
| `prompt_six_questions_and_segments(summary, n)` | Compressed theme summary | `{q1..q6, segments:[...]}` — JSON object |
| `prompt_root_causes_and_needs(summary)` | Compressed theme summary | `{root_causes, unwanted_repetition_causes, intentional_repetition_note, unmet_needs, key_insights}` — JSON object |

**Prompt Constraints (all 3 prompts enforce these):**
- Return **only valid JSON** — no markdown fences, no preamble
- Never suggest product features or solutions
- Distinguish unwanted repetition (algorithm failure) from intentional repetition (user choice)
- Segment users by **listening use-case only**, never by demographics

---

### Sub-Phase 3c — Orchestrator (`modules/ai_pipeline.py`)

```
filtered_df (n reviews)
     │
     ├─ chunk into batches of 30
     │
     ├── CALL 1: Theme Extraction (max 3 batches → up to 90 reviews)
     │       └── deduplicate themes by name
     │       └── build compressed theme_summary string
     │
     ├── CALL 2: Six Questions + Segments
     │       └── input: theme_summary + total review count
     │
     └── CALL 3: Root Causes + Unmet Needs + Key Insights
             └── input: theme_summary
```

**LLM Call Function (`call_llm`):**
- Tries current key
- On `429 / rate / quota / limit` error → `key_manager.rotate()` → `sleep(5)` → retry
- On other exceptions → re-raise immediately
- After 4 failed attempts → raise `RuntimeError`

**JSON Parser (`parse_json_response`):**
- Strips ` ```json ` / ` ``` ` fences if present
- Returns parsed Python object
- Caller catches parse errors gracefully (returns `{"error": "..."}`)

**`run_analysis(df)` Return Shape:**
```python
{
  "themes": [...],                   # from Call 1
  "questions": {...},                # from Call 2 (q1–q6 + segments)
  "root_causes_and_needs": {...}     # from Call 3
}
```

### Validation Checkpoint
- [ ] `run_analysis(filtered_df)` returns dict with all 3 keys
- [ ] No raw LLM text leaks into the return value
- [ ] Rate-limit errors are retried, not crashed

---

## Phase 4 — Report UI (`components/report_renderer.py` + `app.py` + CSS)

**Goal:** Render the full 7-tab Spotify-themed report in Streamlit (including Key Insights & Infographics).

### Sub-Phase 4a — Visual Theme (Spotify Dark CSS)

Applied via `st.markdown(SPOTIFY_CSS, unsafe_allow_html=True)` at the top of `app.py`.

| Element | Style |
|---------|-------|
| App background | `#121212` |
| Sidebar | `#000000` |
| Primary action buttons | `#1DB954` (Spotify Green), rounded, bold |
| Cards (`.insight-card`) | `#282828` bg, 8px border-radius |
| Section headers | `#1DB954`, uppercase, letter-spaced |
| Muted text | `#B3B3B3` |
| Frequency badges | Green (High) / Amber (Medium) / Grey (Low) |
| Active tab underline | `#1DB954` |

---

### Sub-Phase 4b — 7 Report Tabs

| Tab | Renderer Function | Data Source |
|-----|------------------|------------|
| 📊 Overview | `render_dataset_overview(df, filtered_df, mode)` | Raw + filtered DataFrames |
| 🎯 Themes | `render_themes(themes)` | `report["themes"]` |
| ❓ Six Questions | `render_six_questions(questions)` | `report["questions"]` |
| 👤 Segments | `render_segments(questions)` | `report["questions"]["segments"]` |
| 🔍 Root Causes | `render_root_causes(data)` | `report["root_causes_and_needs"]` |
| 💡 Unmet Needs | `render_unmet_needs(data)` | `report["root_causes_and_needs"]` |
| 🔑 Key Insights | `render_key_insights(data, df, filtered_df, report)` | `report["root_causes_and_needs"]` + `report["questions"]` + DataFrames |

**Tab 1 — Dataset Overview:**
- 3 metric cards: Total Reviews / Discovery-Relevant / Mode
- Source breakdown table with % of total

**Tab 2 — Themes:**
- One `.insight-card` per theme
- Badge: High (green) / Medium (amber) / Low (grey)
- Quoted paraphrased review example with left green border

**Tab 3 — Six Questions:**
- `st.expander` for each question
- Q4 (repetition) renders as two sub-keys: `unwanted_repetition` + `intentional_repetition`

**Tab 4 — Segments:**
- One card per segment
- Fields: name, what_they_do, discovery_blocker, repetition_type, evidence quote
- `repetition_type` values: Unwanted / Intentional / Mixed

**Tab 5 — Root Causes:**
- Bulleted list: primary root causes
- Bulleted list: unwanted repetition causes
- `st.info` block: intentional repetition note

**Tab 6 — Unmet Needs:**
- One card per need
- Fields: need statement, segment, evidence quote

**Tab 7 — Key Insights & Infographics:**
- One card per key insight: observation · impact on listener · actionable takeaway (green bordered panel)
- **6 infographic sections** — one per research question — each rendered as a full-width row with two columns:
  - **Left column — AI Analysis panel** (dark navy, green left border): verbatim LLM answer from Call 2 (`report["questions"]["q1"–"q6"]`)
  - **Right column — Keyword-frequency bar chart**: horizontal bar chart counting how many discovery-relevant reviews mention each pattern
- Q4 panel splits into ⚠ Unwanted Repetition (amber) and ✓ Intentional Repetition (green) sub-sections
- Q5 panel renders AI-identified segment cards (name + repetition-type badge + discovery blocker); chart uses segment keywords back-matched to review corpus
- Q6 panel renders AI-extracted unmet needs (need + segment); chart ranks needs by corpus signal, sorted descending
- Fallback to keyword-proxy charts when AI data is unavailable
- Footer footnote distinguishes chart source (keyword frequency) from AI panel source (LLM output)

| Infographic | Research Question | AI Panel Source | Chart Keyword Groups |
|---|---|---|---|
| ❶ | Why do users struggle to discover new music? | `questions["q1"]` | Algorithm, Repetitive recs, No variety, Filter bubble, Poor discovery |
| ❷ | Most common recommendation frustrations? | `questions["q2"]` | Feedback ignored, No variety, Taste mismatch, Recycled songs, Context blindness |
| ❸ | Listening behaviors users try to achieve? | `questions["q3"]` | Active discovery, Mood, Focus/work, Workout, Social |
| ❹ | Causes of repeated listening? | `questions["q4"]` (dict) | Algo loop, Comfort/familiar, Autoplay, Offline, Mood anchoring |
| ❺ | Which segments face different challenges? | `questions["segments"]` (cards) | Segment keywords back-matched to corpus |
| ❻ | Unmet needs across reviews? | `data["unmet_needs"]` (cards) | Need keywords back-matched, sorted by volume |

---

### Sub-Phase 4c — `app.py` Orchestration

```
Page Config → Apply CSS → Sidebar → Session State Init
     │
     └── [Run Analysis Button Clicked]
           ├── Load reviews (loader_excel)
           ├── Filter reviews (filter_relevance)
           ├── Run AI pipeline (ai_pipeline)
           └── Store in st.session_state.report
     │
     └── [Report in session_state]
           └── Render all 7 tabs
```

**Sidebar Controls:**
- Mode radio: `Preloaded Dataset` / `Live Collection`
- **Review-count slider** *(visible only in Live Collection mode)*:
  - Label: `Reviews to scrape (slide with max 2000 reviews)`
  - Range: 50 – 2000, step 50, default 400
  - Split: ~75% to Play Store, ~25% to App Store
  - Tooltip: "Total reviews to fetch across both sources"
- `▶ Run Analysis` button (full-width, Spotify green)

**State Keys:**
| Key | Value |
|-----|-------|
| `st.session_state.report` | Full analysis dict or `None` |
| `st.session_state.df` | Raw loaded DataFrame |
| `st.session_state.filtered_df` | Filtered DataFrame |

**Empty State:**
- 4-column step cards representing the Analysis Process (Data Ingestion, Relevance Filtering, Theme Extraction, Insights Synthesis)

### Validation Checkpoint ✅ (Day 1 Done)
- [ ] App loads at deployed URL without errors
- [ ] "Run Analysis" completes and renders all 7 tabs
- [ ] No Python traceback visible to users on failure (all errors caught and shown via `st.error`)
- [ ] Spotify dark theme applied throughout

---

## Phase 5 — Live Scrapers (Day 2)

**Goal:** Add real-time review collection from Google Play Store and Apple App Store, with a sidebar mode toggle.

### Sub-Phase 5a — Play Store Scraper (`modules/scraper_playstore.py`)

| Config | Value |
|--------|-------|
| Package ID | `com.spotify.music` |
| Language | `en` |
| Country | `in` |
| Sort | Newest |
| Count | `int(scrape_count × 0.75)` — slider-driven, min 10 |

Returns: `[{source, review_text, date, rating}]`

---

### Sub-Phase 5b — App Store Scraper (`modules/scraper_appstore.py`)

| Config | Value |
|--------|-------|
| Endpoint | iTunes RSS JSON API |
| App ID | `324684580` (Spotify) |
| Region | `in` |
| Sort | Most Recent |
| Count | `scrape_count - play_count` — slider-driven, min 10 |

Returns: `[{source, review_text, date, rating}]`

---

### Sub-Phase 5c — Sidebar Mode Toggle

```
Mode = "Preloaded Dataset"  → load_preloaded_reviews()
Mode = "Live Collection"    → scrape_playstore() + scrape_appstore()
                              → combine → pd.DataFrame
                              → same filter + AI pipeline
```

Both scraper outputs are combined, converted to DataFrame matching the loader schema, then passed through the same `filter_relevant()` → `run_analysis()` pipeline.

### Validation Checkpoint
- [ ] Live mode fetches > 0 reviews from at least one source
- [ ] Scraper failures are caught and surfaced as `st.warning`, not crashes
- [ ] Analysis pipeline works identically for both modes

---

## Phase 6 — Export Module (Day 2)

**Goal:** Allow users to download the full analysis report as Markdown or CSV.

### `modules/exporter.py`

| Function | Output |
|----------|--------|
| `export_markdown(report, df_stats)` | `.md` string — full report with themes, Q&A, root causes, unmet needs |
| `export_csv(report)` | `.csv` string — flat table with section / item / detail / evidence columns |

### UI Placement
- Below all 6 tabs (only visible when report exists)
- Two `st.download_button` calls side by side:
  - ⬇ Download Markdown → `spotify_discovery_report.md`
  - ⬇ Download CSV → `spotify_discovery_report.csv`

### Validation Checkpoint
- [ ] Downloaded Markdown is valid and readable
- [ ] Downloaded CSV opens correctly in Excel/Sheets
- [ ] Buttons only appear when a report exists in session state

---

## Deployment Checklist (Streamlit Community Cloud)

### Pre-Push Checks
- [ ] `data/reviews_preloaded.xlsx` committed (not gitignored)
- [ ] `.env` is in `.gitignore` — real keys never committed
- [ ] `requirements.txt` is complete and pinned if needed
- [ ] All 4 API key vars set in Streamlit Cloud Secrets panel

### Streamlit Cloud Secrets Format (`secrets.toml` equivalent)
```toml
GROQ_API_KEY_1 = "gsk_..."
GROQ_API_KEY_2 = "gsk_..."
GEMINI_API_KEY_1 = "AIza..."
GEMINI_API_KEY_2 = "AIza..."
```

### Post-Deploy Verification
- [ ] App loads at deployed URL in < 10 seconds
- [ ] "Run Analysis" with Preloaded mode completes without errors
- [ ] All 6 tabs render content
- [ ] No traceback visible to end users

---

## Scope Guard — What Must Never Be Built or Output

| ❌ Forbidden | ✅ Allowed Alternative |
|-------------|----------------------|
| MVP feature suggestions | "Users need X" framing |
| "Spotify should build X" | "Listeners want X" framing |
| Product roadmap items | Root cause statements |
| Interview/research plans | Theme + segment analysis |
| Demographic segmentation | Use-case based segments |
| Part 2/3/4 deliverables | Day 1 + Day 2 scope only |

---

## File Dependency Map

```
app.py
  ├── modules/loader_excel.py
  ├── modules/filter_relevance.py
  ├── modules/ai_pipeline.py
  │     ├── modules/key_manager.py
  │     └── modules/prompts.py
  ├── components/report_renderer.py
  └── (Day 2) modules/exporter.py
              modules/scraper_playstore.py
              modules/scraper_appstore.py
```

---

## Build Order (Recommended)

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 3a  →  Phase 3b  →  Phase 3c
(Scaffold)  (Loader)   (Filter)   (KeyMgr)    (Prompts)   (Pipeline)

     →  Phase 4a  →  Phase 4b  →  Phase 4c  →  DEPLOY  →  Phase 5  →  Phase 6
       (CSS)       (Renderers)   (app.py)                 (Scrapers)  (Exports)
```

---

*Architecture document for the Spotify Review Discovery Engine*  
*Aligned with `antigravity_build_prompt.md`*  
*Day 1: Phases 0–4 | Day 2: Phases 5–6*
