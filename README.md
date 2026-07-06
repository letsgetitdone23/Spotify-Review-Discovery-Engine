# Spotify AI-Powered Review Discovery Engine

> A Streamlit-based web application that analyzes Spotify user reviews — sourced from app stores, the official Spotify Community forum, and live scrapers — to surface music discovery friction and repetitive listening behaviors using a 3-call LLM pipeline.

---

## 🚀 Live Demo
The application is deployed on Streamlit Community Cloud:  
**[🎧 Launch Live App → spotifyai-review-discovery-engine.streamlit.app](https://spotifyai-review-discovery-engine.streamlit.app/)**

---

## ✨ Features

### 📥 Dual Analysis Modes
- **Preloaded Dataset** — Loads 2,025 historical reviews from an Excel workbook (5 source sheets).
- **Live Collection** — Scrapes real-time content from 3 sources simultaneously:
  - 🛒 **Google Play Store** — User reviews for the Spotify Android app
  - 🍎 **Apple App Store** — User reviews via the iTunes RSS feed
  - 💬 **Spotify Community Forum** — Discovery-relevant discussions scraped from `community.spotify.com` board RSS feeds (Music, Features, Live Ideas). No auth required.
  - Count distributed as **60% Play Store · 20% App Store · 20% Community**

### 🎚 Dynamic Scraper Slider
Fine-tune total reviews to collect (50–2000), automatically split across all 3 sources.

### 🔍 Semantic Relevance Filter
A keyword-scoring classifier that eliminates noise (billing, crash, login) and isolates reviews discussing recommendation algorithms, discovery loops, and repetition behavior. Classifies into **HIGH / MEDIUM / LOW** tiers.

### 🤖 3-Stage Sequential AI Pipeline
- **Call 1 — Theme Extraction:** Surfaces recurring pain points with frequency labels (High / Medium / Low) and a paraphrased review example per theme.
- **Call 2 — Patterns and Needs + Segments:** Answers 6 patterns-and-needs questions with detailed explanations, key insights, and specific evidence, and clusters users into listening use-case segments (not demographics).
- **Call 3 — Root Cause & Needs Synthesis:** Maps systemic causes of discovery failure and frames unmet needs as listener-centric statements.
- Supports **Groq** (Llama-3.1-8b) as primary and **Gemini** (Gemini-2.0-flash) as fallback with automatic key rotation on rate limits.

### 📊 7-Tab Interactive Dashboard

| Tab | Content |
|-----|---------|
| 📊 Overview | Review counts, relevance tier breakdown, source table, rating distribution |
| 🎯 Themes | Theme cards with frequency badge and paraphrased user example |
| ❓ Patterns and Needs | Detailed paragraph explanation (150–200 words) + 🔑 Key Insights list + 🗣 Evidence from the Reviews (combined AI-paraphrased quotes & matching real-world review snippets) |
| 👤 Segments | Use-case based user segment cards with discovery blocker and evidence |
| 🔍 Root Causes | Bulleted root causes of discovery failure + unwanted repetition causes |
| 💡 Unmet Needs | Need statements framed as "Users need..." with evidence and segment label |
| 🔑 Key Insights | Systemic insight cards + **6 Plotly infographics** (one per pattern/need) in Spotify green |

### 📈 Spotify-Colored Infographics (Tab 7)
All 6 infographic charts use full Spotify branding:
- `#1DB954` green bars on `#121212` dark background
- `#282828` gridlines, white y-axis labels
- Built with Plotly — hover tooltips, `Inter` font

### ⬇ One-Click Exports
Download the full analysis report as clean **Markdown** (`.md`) or structured **CSV**.

---

## 🛠 Tech Stack

| Layer | Tools |
|---|---|
| **Frontend** | [Streamlit](https://streamlit.io/) with custom Spotify dark theme CSS |
| **Data Processing** | Pandas, openpyxl |
| **AI / LLMs** | Groq API (Llama-3.1-8b-instant) · Gemini API (gemini-2.0-flash) |
| **Scrapers** | `google-play-scraper` · Apple App Store iTunes RSS · `feedparser` (Spotify Community RSS) |
| **Charts** | Plotly |
| **Key Management** | Custom round-robin key rotation across providers |

---

## ⚙️ Setup

### 1. Clone & install
```bash
pip install -r requirements.txt
```

### 2. Configure API keys
Copy `.env.example` to `.env` and fill in your keys:
```
GROQ_API_KEY_1=your_groq_key
GEMINI_API_KEY_1=your_gemini_key
```
At least one Groq **or** one Gemini key is required.

### 3. Run locally
```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
├── app.py                          # Streamlit entry point + CSS theme
├── components/
│   └── report_renderer.py          # 7 tab rendering functions
├── modules/
│   ├── ai_pipeline.py              # 3-call LLM orchestrator
│   ├── prompts.py                  # Prompt builders for each LLM call
│   ├── filter_relevance.py         # Keyword-based relevance classifier
│   ├── loader_excel.py             # Preloaded dataset loader
│   ├── key_manager.py              # API key round-robin rotation
│   ├── scraper_playstore.py        # Google Play Store scraper
│   ├── scraper_appstore.py         # Apple App Store RSS scraper
│   ├── scraper_spotify_community.py# Spotify Community forum RSS scraper
│   └── exporter.py                 # Markdown + CSV export
├── data/                           # Preloaded Excel review dataset
├── requirements.txt
└── .env.example
```
