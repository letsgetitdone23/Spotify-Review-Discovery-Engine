"""
app.py — Spotify AI-Powered Review Discovery Engine
----------------------------------------------------
Streamlit entry point. Orchestrates the full Day-1 pipeline:
  1. Load all reviews from the preloaded Excel workbook (5 sheets)
  2. Classify reviews into HIGH / MEDIUM / LOW relevance tiers
  3. Run 3-call AI analysis (theme extraction → patterns and needs → root causes)
  4. Render a 6-tab Spotify-themed report

Day-2 additions (live scrapers + export) are stubbed and ready to wire in.
"""

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

load_dotenv()  # loads .env locally; Streamlit Cloud uses Secrets panel

# --- Page config (must be the very first Streamlit call) ---
_page_icon = Image.open("logo/spotifylogo.png")
st.set_page_config(
    page_title="Spotify Review Discovery Engine",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===========================================================================
# Spotify Dark Theme — CSS
# ===========================================================================

SPOTIFY_CSS = """
<style>
    /* ---- Google Font ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* ---- Base ---- */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background-color: #121212;
        color: #FFFFFF;
    }

    /* ---- Force Dark Header & Strip ---- */
    header, [data-testid="stHeader"], [data-testid="stHeader"] > div {
        background-color: #000000 !important;
        background: #000000 !important;
        border-bottom: 1px solid #282828 !important;
    }
    div[data-testid="stDecoration"] {
        background-image: none !important;
        background-color: #000000 !important;
        background: #000000 !important;
        height: 0px !important;
    }

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #282828;
    }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] label {
        color: #B3B3B3;
    }

    /* ---- Primary button (Run Analysis) ---- */
    .stButton > button {
        background-color: #1DB954 !important;
        color: #000000 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 500px !important;
        padding: 0.6rem 2rem !important;
        font-size: 0.95rem !important;
        transition: background-color 0.15s ease, transform 0.1s ease !important;
    }
    .stButton > button:hover {
        background-color: #1ed760 !important;
        transform: scale(1.02) !important;
    }
    .stButton > button:active {
        transform: scale(0.98) !important;
    }

    /* ---- Insight cards ---- */
    .insight-card {
        background-color: #282828;
        border-radius: 8px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        border: 1px solid #333;
        transition: border-color 0.2s ease;
    }
    .insight-card:hover {
        border-color: #1DB954;
    }

    /* ---- Frequency / tier badges ---- */
    .badge-high {
        background: #1DB954;
        color: #000;
        padding: 2px 10px;
        border-radius: 500px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-medium {
        background: #E8A400;
        color: #000;
        padding: 2px 10px;
        border-radius: 500px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-low {
        background: #535353;
        color: #fff;
        padding: 2px 10px;
        border-radius: 500px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* ---- Source tag ---- */
    .source-tag {
        background: #333;
        color: #B3B3B3;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
    }

    /* ---- Section headers ---- */
    .section-header {
        color: #1DB954;
        font-size: 1.05rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 1rem;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid #282828;
    }

    /* ---- Muted / helper text ---- */
    .muted {
        color: #B3B3B3;
        font-size: 0.9rem;
    }

    /* ---- Divider ---- */
    hr {
        border-color: #282828;
        margin: 1rem 0;
    }

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #121212;
        border-bottom: 1px solid #282828;
        gap: 0.25rem;
    }
    .stTabs [data-baseweb="tab"] {
        color: #B3B3B3;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [aria-selected="true"] {
        color: #1DB954 !important;
        border-bottom: 2px solid #1DB954 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #FFFFFF;
        background-color: #282828;
    }

    /* ---- Metrics ---- */
    [data-testid="stMetricValue"] {
        color: #FFFFFF;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #B3B3B3;
    }

    /* ---- Expanders ---- */
    details summary {
        color: #FFFFFF;
        font-weight: 600;
    }
    details[open] summary {
        color: #1DB954;
    }

    /* ---- Dataframe ---- */
    [data-testid="stDataFrame"] {
        border: 1px solid #333;
        border-radius: 6px;
    }

    /* ---- Info / warning boxes ---- */
    [data-testid="stAlert"] {
        border-radius: 8px;
        border-left-width: 4px;
    }

    /* ---- Spinner ---- */
    [data-testid="stSpinner"] {
        color: #1DB954;
    }

    /* ---- Scrollbar ---- */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #121212; }
    ::-webkit-scrollbar-thumb { background: #535353; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #1DB954; }
</style>
"""

st.markdown(SPOTIFY_CSS, unsafe_allow_html=True)

# ===========================================================================
# Imports — after CSS to avoid flash of unstyled content
# ===========================================================================

from modules.loader_excel import load_preloaded_reviews, summarize_dataframe
from modules.filter_relevance import filter_relevant, filter_summary
from modules.ai_pipeline import run_analysis
from modules.scraper_playstore import scrape_playstore_reviews
from modules.scraper_appstore import scrape_appstore_reviews
from modules.scraper_spotify_community import scrape_spotify_community
from modules.exporter import export_markdown, export_csv
from components.report_renderer import (
    render_dataset_overview,
    render_themes,
    render_six_questions,
    render_segments,
    render_root_causes,
    render_unmet_needs,
    render_key_insights,
)

# ===========================================================================
# Sidebar
# ===========================================================================

with st.sidebar:
    st.markdown(
        '<h2 style="color:#1DB954;margin-bottom:0;">🎵 Discovery Engine</h2>',
        unsafe_allow_html=True,
    )
    st.markdown('<p class="muted">Spotify Review Analysis</p>', unsafe_allow_html=True)
    st.markdown("---")

    mode = st.radio(
        "Analysis Mode",
        ["Preloaded Dataset", "Live Collection"],
        key="analysis_mode_radio",
        help="Live Collection scrapes real-time reviews from Google Play Store & Apple App Store.",
    )

    if mode == "Live Collection":
        st.info(
            "Scrapes live discussions from:\n"
            "- 🛒 Google Play Store reviews\n"
            "- 🍎 Apple App Store reviews\n"
            "- 💬 Spotify Community forum (RSS)",
            icon="🌐",
        )
        scrape_count = st.slider(
            "Reviews to scrape (slide with max 2000 reviews)",
            min_value=50,
            max_value=2000,
            value=400,
            step=50,
            key="scrape_count_slider",
            help="Total reviews to fetch across both sources. Split ~75% Play Store / 25% App Store.",
        )
    else:
        scrape_count = 400

    st.markdown("---")

    run_btn = st.button("▶  Run Analysis", key="run_analysis_btn", use_container_width=True)

    st.markdown("---")

# ===========================================================================
# Main panel — header
# ===========================================================================

st.markdown(
    '<h1 style="margin-bottom:0.2rem;">Spotify Review Discovery Engine</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="muted" style="font-size:1rem;margin-bottom:1.5rem;">'
    'AI-powered analysis of user reviews — focused on music discovery '
    'and repetitive listening behavior.'
    '</p>',
    unsafe_allow_html=True,
)

# ===========================================================================
# Session state initialisation
# ===========================================================================

for key in ("report", "df", "filtered_df", "mode"):
    if key not in st.session_state:
        st.session_state[key] = None

# ===========================================================================
# Run Analysis flow
# ===========================================================================

if run_btn:
    st.session_state.mode = mode
    # --- Step 1: Load/Scrape reviews ---
    with st.spinner("Loading reviews..."):
        try:
            if mode == "Live Collection":
                with st.spinner("Scraping live reviews (Play Store + App Store + Community)..."):
                    # Distribute count: 60% Play Store, 20% App Store, 20% Community
                    play_count      = max(10, int(scrape_count * 0.60))
                    app_count       = max(10, int(scrape_count * 0.20))
                    community_count = max(10, scrape_count - play_count - app_count)

                    play_reviews      = scrape_playstore_reviews(count=play_count)
                    app_reviews       = scrape_appstore_reviews(count=app_count)
                    community_reviews = scrape_spotify_community(count=community_count)

                    all_scraped = play_reviews + app_reviews + community_reviews

                    # Status breakdown toast
                    parts = []
                    if play_reviews:      parts.append(f"{len(play_reviews)} Play Store")
                    if app_reviews:       parts.append(f"{len(app_reviews)} App Store")
                    if community_reviews: parts.append(f"{len(community_reviews)} Community")
                    
                    if not all_scraped:
                        st.warning("Failed to scrape live reviews. Falling back to preloaded dataset.", icon="⚠")
                        df = load_preloaded_reviews()
                    else:
                        import pandas as pd
                        df = pd.DataFrame(all_scraped)
                        # Normalize columns to match the preloaded schema
                        if "language" not in df.columns:
                            df["language"] = "en"
                        if "rating" not in df.columns:
                            df["rating"] = None
                        summary = " · ".join(parts) if parts else f"{len(df)} total"
                        st.toast(f"✅ Scraped {len(df)} reviews — {summary}", icon="🌐")
            else:
                df = load_preloaded_reviews()
                
            st.session_state.df = df
        except FileNotFoundError as e:
            st.error(str(e))
            st.stop()
        except ValueError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error loading reviews: {e}")
            st.stop()

    # --- Step 2: Filter / classify ---
    with st.spinner("Classifying reviews for discovery relevance…"):
        filtered_df = filter_relevant(df)
        st.session_state.filtered_df = filtered_df
        fs = filter_summary(df, filtered_df)

        if fs["low_count_warning"]:
            st.warning(
                f"Only {fs['used_for_ai']} discovery-relevant reviews found "
                f"({fs['high']} HIGH + {fs['medium']} MEDIUM). "
                "Results may be limited — consider adding more reviews.",
                icon="⚠",
            )
        else:
            st.toast(
                f"✅ {fs['used_for_ai']} relevant reviews found "
                f"({fs['high']} HIGH · {fs['medium']} MEDIUM)",
                icon="🎯",
            )

    # --- Step 3: AI analysis ---
    with st.spinner(
        "Running AI analysis — 3 LLM calls in progress… (~30–90 seconds)"
    ):
        try:
            report = run_analysis(filtered_df)
            st.session_state.report = report
        except RuntimeError as e:
            st.error(
                f"AI analysis failed after all retries: {e}\n\n"
                "Check that your API keys are set correctly in `.env` or "
                "Streamlit Secrets."
            )
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error during AI analysis: {e}")
            st.stop()

    st.success("✅ Analysis complete! Scroll down and check the below tabs to explore the report.", icon="🎉")

# ===========================================================================
# Report rendering — 6 tabs
# ===========================================================================

if st.session_state.report is not None:
    report      = st.session_state.report
    df          = st.session_state.df
    filtered_df = st.session_state.filtered_df

    tabs = st.tabs([
        "📊 Overview",
        "🎯 Themes",
        "❓ Patterns and Needs",
        "👤 Segments",
        "🔍 Root Causes",
        "💡 Unmet Needs",
        "🔑 Key Insights",
    ])

    with tabs[0]:
        render_dataset_overview(df, filtered_df, mode)

    with tabs[1]:
        render_themes(report.get("themes", []))

    with tabs[2]:
        render_six_questions(report.get("questions", {}), filtered_df)

    with tabs[3]:
        render_segments(report.get("questions", {}))

    with tabs[4]:
        render_root_causes(report.get("root_causes_and_needs", {}))

    with tabs[5]:
        render_unmet_needs(report.get("root_causes_and_needs", {}))

    with tabs[6]:
        render_key_insights(report.get("root_causes_and_needs", {}), df, filtered_df, report=report)

    # --- Export section ---
    st.markdown("---")
    st.markdown('<p class="section-header">⬇ Export Analysis Report</p>', unsafe_allow_html=True)
    
    mode_used = st.session_state.mode if st.session_state.mode else "Preloaded Dataset"
    stats_dict = {
        "mode": mode_used,
        "total": len(df),
        "used": len(filtered_df),
    }
    
    md_report = export_markdown(report, stats_dict)
    csv_report = export_csv(report)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇ Download Report (Markdown)",
            data=md_report,
            file_name="spotify_discovery_report.md",
            mime="text/markdown",
            key="download_md_btn",
            use_container_width=True
        )
    with col2:
        st.download_button(
            label="⬇ Download Report (CSV)",
            data=csv_report,
            file_name="spotify_discovery_report.csv",
            mime="text/csv",
            key="download_csv_btn",
            use_container_width=True
        )

# ===========================================================================
# Empty state — shown before first run
# ===========================================================================

else:
    st.markdown(
        """
        <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">🎵</div>
            <h2 style="color: #FFFFFF; margin-bottom: 0.5rem;">Ready to Analyze</h2>
            <p class="muted" style="font-size: 1.05rem; max-width: 600px; margin: 0 auto;">
                Configure your analysis settings in the sidebar and click 
                <strong style="color:#1DB954;">▶ Run Analysis</strong> to begin.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<h3 style="color:#1DB954; font-size:1.2rem; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:1.5rem; text-align:center;">Analysis Process</h3>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            """
            <div class="insight-card" style="min-height: 240px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <span style="font-size: 2rem;">📥</span>
                        <span style="background: #1DB954; color: #000; padding: 2px 10px; border-radius: 500px; font-size: 0.75rem; font-weight: 700;">Step 1</span>
                    </div>
                    <h4 style="margin-bottom: 0.5rem; color: #FFFFFF;">Data Ingestion</h4>
                    <p class="muted" style="font-size: 0.85rem; line-height: 1.4;">
                        Collects raw user feedback. Scrapes live reviews from Google Play Store & Apple App Store in real-time or loads historical datasets.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
    with col2:
        st.markdown(
            """
            <div class="insight-card" style="min-height: 240px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <span style="font-size: 2rem;">🎯</span>
                        <span style="background: #1DB954; color: #000; padding: 2px 10px; border-radius: 500px; font-size: 0.75rem; font-weight: 700;">Step 2</span>
                    </div>
                    <h4 style="margin-bottom: 0.5rem; color: #FFFFFF;">Relevance Filtering</h4>
                    <p class="muted" style="font-size: 0.85rem; line-height: 1.4;">
                        Filters out noise. Classifies reviews using semantic keyword scoring to isolate music discovery and repetition issues.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
    with col3:
        st.markdown(
            """
            <div class="insight-card" style="min-height: 240px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <span style="font-size: 2rem;">🤖</span>
                        <span style="background: #1DB954; color: #000; padding: 2px 10px; border-radius: 500px; font-size: 0.75rem; font-weight: 700;">Step 3</span>
                    </div>
                    <h4 style="margin-bottom: 0.5rem; color: #FFFFFF;">Theme Extraction</h4>
                    <p class="muted" style="font-size: 0.85rem; line-height: 1.4;">
                        Leverages LLMs to extract recurring pain points, categorizing them by theme name, description, frequency, and real user examples.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
    with col4:
        st.markdown(
            """
            <div class="insight-card" style="min-height: 240px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <span style="font-size: 2rem;">🧠</span>
                        <span style="background: #1DB954; color: #000; padding: 2px 10px; border-radius: 500px; font-size: 0.75rem; font-weight: 700;">Step 4</span>
                    </div>
                    <h4 style="margin-bottom: 0.5rem; color: #FFFFFF;">Insights Synthesis</h4>
                    <p class="muted" style="font-size: 0.85rem; line-height: 1.4;">
                        Synthesizes findings to map root causes of repetition, segment users by use-case, and identify key unmet needs.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
