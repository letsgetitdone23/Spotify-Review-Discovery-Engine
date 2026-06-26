# Spotify AI-Powered Review Discovery Engine

> **NextLeap Graduation Project — Part 2**  
> A Streamlit-based web application to analyze Spotify user reviews focusing on music discovery friction and repetitive listening behaviors.

---

## 🚀 Live Demo
The application is deployed on Streamlit Community Cloud:  
**[Live App Link](https://spotify-discovery-engine-s9dbbg7cxuxhxymdshdacu.streamlit.app/)**

---

## ✨ Features

- **Double Analysis Modes:**
  - **Preloaded Dataset:** Loads historical review data from Excel (973 reviews across 5 source sheets).
  - **Live Collection:** Scrapes real-time reviews from the Google Play Store and Apple App Store.
- **Dynamic Scraper Slider:** Fine-tune reviews to scrape (up to 2000 reviews max) with a 75/25 auto-distribution split between Play Store & App Store.
- **Semantic Relevance Filter:** A fast keyword-based scoring mechanism that eliminates noise and isolates reviews talking about recommendation algorithms and loops.
- **3-Stage Sequential AI Pipeline:**
  - **Theme Extraction:** Surfaces recurring pain points with severity/frequency metrics.
  - **Use-Case Segmentation:** Clusters user feedback by listening use-case (avoiding demographic stereotypes).
  - **Root Cause & Needs Synthesis:** Maps deep causes of repetition and outlines actionable user needs.
- **7-Tab Interactive Dashboard:** Custom Spotify-themed layout with metrics and breakdown charts:
  1. 📊 Overview
  2. 🎯 Themes
  3. ❓ Six Questions
  4. 👤 Segments
  5. 🔍 Root Causes
  6. 💡 Unmet Needs
  7. 🔑 Key Insights (with Infographics)
- **One-Click Exports:** Download reports as clean Markdown (`.md`) or structured CSV tables.

---

## 🛠 Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/)
- **Data processing:** [Pandas](https://pandas.pydata.org/) & `openpyxl`
- **APIs & LLMs:** [Groq API](https://groq.com/) (Llama3-8b) & [Gemini API](https://ai.google.dev/) (Gemini-1.5-Flash)
- **Web Scraping:** `google-play-scraper` & Apple App Store XML RSS

---

## 📦 Setup & Installation

### Prerequisites
- Python 3.9 or higher
- Git

### 1. Clone the repository
```bash
git clone https://github.com/letsgetitdone23/Spotify-Review-Discovery-Engine.git
cd Spotify-Review-Discovery-Engine
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
Create a `.env` file in the root directory (you can copy [.env.example](.env.example)):
```env
GROQ_API_KEY_1=your_groq_api_key_here
GROQ_API_KEY_2=your_alternate_groq_key_here
GEMINI_API_KEY_1=your_gemini_api_key_here
GEMINI_API_KEY_2=your_alternate_gemini_key_here
```
*(The API Key Manager will automatically rotate keys in case of rate limits).*

### 4. Run the app locally
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## ☁️ Deployment Checklist (Streamlit Cloud)

1. Push your repository commits to GitHub (excluding `.env`).
2. Deploy the repository on Streamlit Community Cloud.
3. In the **App Settings > Secrets** panel, add the API keys:
```toml
GROQ_API_KEY_1 = "gsk_..."
GROQ_API_KEY_2 = "gsk_..."
GEMINI_API_KEY_1 = "AIza..."
GEMINI_API_KEY_2 = "AIza..."
```
4. Trigger a build and enjoy the deployed discovery engine!
