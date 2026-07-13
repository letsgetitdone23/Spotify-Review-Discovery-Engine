"""
components/report_renderer.py
------------------------------
Six rendering functions — one per report tab — for the Spotify Review
Discovery Engine. All functions write directly to the Streamlit UI using
st.markdown with unsafe_allow_html=True for the custom CSS card/badge system.

Tab mapping:
  render_dataset_overview()  → 📊 Overview
  render_themes()            → 🎯 Themes
  render_six_questions()     → ❓ Patterns and Needs
  render_segments()          → 👤 Segments
  render_root_causes()       → 🔍 Root Causes
  render_unmet_needs()       → 💡 Unmet Needs
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go


# ---------------------------------------------------------------------------
# Helper: section header
# ---------------------------------------------------------------------------

def _section_header(title: str):
    st.markdown(
        f'<div class="section-header">{title}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Helper: frequency badge HTML
# ---------------------------------------------------------------------------

def _badge(frequency: str) -> str:
    tier = frequency.lower() if frequency else "low"
    if tier == "high":
        css = "badge-high"
    elif tier == "medium":
        css = "badge-medium"
    else:
        css = "badge-low"
    return f'<span class="{css}">{frequency}</span>'


# ---------------------------------------------------------------------------
# Helper: repetition type chip
# ---------------------------------------------------------------------------

def _rep_chip(rep_type: str) -> str:
    t = (rep_type or "").lower()
    if "unwanted" in t:
        color = "#E8A400"
    elif "intentional" in t:
        color = "#1DB954"
    else:
        color = "#535353"
    return (
        f'<span style="background:{color};color:#000;padding:2px 10px;'
        f'border-radius:500px;font-size:0.75rem;font-weight:700;">'
        f'{rep_type}</span>'
    )


# ---------------------------------------------------------------------------
# Helper: Spotify-themed horizontal Plotly bar chart (shared by all tabs)
# ---------------------------------------------------------------------------

def _spotify_bar_chart(
    df_in: pd.DataFrame,
    caption: str = "",
    bar_color: str = "#1DB954",
    height: int = 260,
):
    """
    Render a horizontal Plotly bar chart styled in the Spotify dark theme.

    Args:
        df_in:     DataFrame with a single numeric column; index = category labels.
        caption:   Optional caption rendered below the chart in muted text.
        bar_color: Bar fill colour — default Spotify Green #1DB954.
        height:    Chart height in pixels.
    """
    labels = df_in.index.tolist()
    values = df_in.iloc[:, 0].tolist()

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=bar_color,
        marker_line_width=0,
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="#121212",
        plot_bgcolor="#121212",
        font=dict(family="Inter, sans-serif", color="#B3B3B3", size=12),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            gridcolor="#282828",
            zerolinecolor="#282828",
            tickfont=dict(color="#B3B3B3"),
        ),
        yaxis=dict(
            tickfont=dict(color="#FFFFFF", size=11),
            automargin=True,
        ),
        height=height,
    )
    st.plotly_chart(fig, use_container_width=True)  # plotly_chart still uses use_container_width
    if caption:
        st.markdown(
            f'<p class="muted" style="font-size:0.78rem;text-align:center;margin-top:0.3rem;">'
            f'{caption}</p>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab 1 — Dataset Overview
# ---------------------------------------------------------------------------

def render_dataset_overview(df, filtered_df, mode: str):
    """
    Render the Dataset Overview tab.

    Shows:
      - 3 metric cards: total reviews, discovery-relevant count, analysis mode
      - 3-tier classification breakdown (HIGH / MEDIUM / LOW) if available
      - Source breakdown table with counts and percentages
      - Analysis metadata (_meta) if present in the session report
    """
    _section_header("Dataset Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Reviews", f"{len(df):,}")
    col2.metric("Used for Analysis", f"{len(filtered_df):,}")
    col3.metric("Mode", mode)

    st.markdown("---")

    # Tier breakdown if relevance_tier column is present
    if "relevance_tier" in filtered_df.columns:
        st.markdown("**Relevance Classification**")
        tier_counts = filtered_df["relevance_tier"].value_counts()
        tier_cols = st.columns(3)
        tier_colors = {"HIGH": "#1DB954", "MEDIUM": "#E8A400", "LOW": "#535353"}
        for i, tier in enumerate(["HIGH", "MEDIUM", "LOW"]):
            count = tier_counts.get(tier, 0)
            pct = round(count / len(filtered_df) * 100, 1) if len(filtered_df) else 0
            tier_cols[i].markdown(
                f'<div class="insight-card" style="text-align:center;">'
                f'<span style="color:{tier_colors[tier]};font-weight:700;font-size:1.1rem;">{tier}</span><br>'
                f'<span style="font-size:1.5rem;font-weight:700;">{count}</span><br>'
                f'<span class="muted">{pct}% of analyzed</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

    # Source breakdown
    st.markdown("**Source Breakdown**")
    import pandas as pd
    source_counts = filtered_df["source"].value_counts().reset_index()
    source_counts.columns = ["Source", "Reviews"]
    source_counts["% of Analyzed"] = (
        source_counts["Reviews"] / len(filtered_df) * 100
    ).round(1).astype(str) + "%"
    st.dataframe(source_counts, hide_index=True, use_container_width=True)

    # Rating distribution if available
    if "rating" in filtered_df.columns and filtered_df["rating"].notna().any():
        st.markdown("---")
        st.markdown("**Rating Distribution**")
        rating_counts = (
            filtered_df["rating"]
            .dropna()
            .astype(int)
            .value_counts()
            .sort_index()
            .reset_index()
        )
        rating_counts.columns = ["Rating (Stars)", "Count"]
        _spotify_bar_chart(
            rating_counts.set_index("Rating (Stars)"),
            caption="Star rating distribution across analyzed reviews",
            bar_color="#1DB954",
            height=220,
        )

    # --- Tab navigation guide ---
    st.markdown("---")
    st.markdown(
        '<p class="section-header">🗂 Explore the Full Analysis</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="muted" style="margin-bottom:1.2rem;">'
        'The dataset is loaded and classified. Use the tabs above to dive deeper into each layer of the analysis.'
        '</p>',
        unsafe_allow_html=True,
    )

    tab_guide = [
        ("🎯", "Themes",             "Recurring pain points extracted from reviews, ranked by frequency."),
        ("❓", "Patterns and Needs", "Detailed answers to 6 research questions — with key insights and user evidence."),
        ("👤", "Segments",           "Use-case based listener segments and their discovery blockers."),
        ("🔍", "Root Causes",        "Systemic causes behind discovery failure and unwanted repetition."),
        ("💡", "Unmet Needs",        "Listener needs identified from the reviews, framed as user statements."),
        ("🔑", "Key Insights",       "High-level takeaways and 6 keyword-frequency infographics."),
    ]

    for icon, tab_name, description in tab_guide:
        st.markdown(
            f'<div class="insight-card" style="display:flex;align-items:flex-start;gap:1rem;padding:0.9rem 1.2rem;margin-bottom:0.6rem;">'
            f'  <span style="font-size:1.5rem;line-height:1;">{icon}</span>'
            f'  <div>'
            f'    <p style="margin:0;font-weight:700;color:#FFFFFF;font-size:0.95rem;">{tab_name}</p>'
            f'    <p class="muted" style="margin:0.2rem 0 0 0;font-size:0.85rem;">{description}</p>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab 2 — Discovery Theme Analysis
# ---------------------------------------------------------------------------

def render_themes(themes: list):
    """
    Render the Themes tab.

    One insight-card per theme showing:
      - Theme name + frequency badge (High / Medium / Low)
      - Description
      - Paraphrased review example with green left border
    """
    _section_header("Discovery Theme Analysis")

    if not themes:
        st.info("No themes were extracted. Try running the analysis again.")
        return

    st.markdown(
        f'<p class="muted">{len(themes)} themes identified across the analyzed reviews.</p>',
        unsafe_allow_html=True,
    )

    for t in themes:
        freq = t.get("frequency", "Low")
        badge = _badge(freq)
        st.markdown(
            f"""
            <div class="insight-card">
                <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.5rem;">
                    <strong style="font-size:1rem;">{t.get('theme', 'Theme')}</strong>
                    {badge}
                </div>
                <p class="muted" style="margin:0.3rem 0 0.6rem 0;">{t.get('description', '')}</p>
                <div style="border-left:3px solid #1DB954;padding-left:0.8rem;margin-top:0.5rem;">
                    <p style="font-size:0.85rem;color:#ccc;margin:0;">
                        &ldquo;{t.get('example', '')}&rdquo;
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab 3 — Patterns and Needs
# ---------------------------------------------------------------------------

def render_six_questions(questions: dict, filtered_df=None):
    """
    Render the Patterns and Needs tab.

    Each question in an st.expander showing:
      - A detailed paragraph answer (150-200 words)
      - Key Insights for that particular question
      - Evidence from the Reviews (AI paraphrased + real matching snippets)
    """
    import random

    _section_header("Patterns and Needs")

    if "error" in questions:
        st.error(f"Analysis error: {questions['error']}")
        return

    # Keywords used to find matching evidence quotes from real reviews
    Q_KEYWORDS = {
        "q1": ["discover", "new music", "new artist", "can't find", "explore", "algorithm", "recommendation"],
        "q2": ["frustrat", "same song", "repeat", "recommend", "doesn't learn", "feedback", "thumbs", "irrelevant"],
        "q3": ["mood", "focus", "study", "workout", "gym", "chill", "relax", "vibe", "feel", "explore"],
        "q4": ["same song", "loop", "repeat", "keeps playing", "comfort", "familiar", "autoplay"],
        "q5": ["casual", "daily", "power user", "explorer", "mood", "gym", "work", "study", "segment"],
        "q6": ["need", "want", "wish", "should", "missing", "can't", "unable", "would love"],
    }

    def _get_evidence(key: str, n: int = 2) -> list:
        """Return up to n short real review snippets matching this question."""
        if filtered_df is None or filtered_df.empty:
            return []
        kws = Q_KEYWORDS.get(key, [])
        texts = filtered_df["review_text"].dropna().tolist()
        matches = [
            t.strip() for t in texts
            if any(kw in t.lower() for kw in kws) and 30 < len(t.strip()) < 280
        ]
        random.seed(42)
        sample = random.sample(matches, min(n, len(matches))) if matches else []
        # Trim to a readable length
        return [s[:220] + ("…" if len(s) > 220 else "") for s in sample]

    def _text_to_bullets(text: str) -> list:
        """Split a paragraph of AI text into a list of bullet strings."""
        if not text:
            return []
        # Split on common sentence / clause endings
        import re
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z•\-])', text.strip())
        # Also handle lines that already start with dash/bullet
        bullets = []
        for p in parts:
            sub = re.split(r'\n\s*[-•]\s*', p)
            bullets.extend(sub)
        bullets = [b.strip().lstrip("-•").strip() for b in bullets if b.strip()]
        return bullets

    def _render_bullets_and_evidence(text: str, key: str):
        """Render bullet points from AI text + evidence block."""
        bullets = _text_to_bullets(text)
        if bullets:
            for b in bullets:
                st.markdown(f"- {b}")
        else:
            st.write(text)

        evidence = _get_evidence(key)
        if evidence:
            st.markdown(
                '<p style="color:#B3B3B3;font-size:0.8rem;font-weight:700;'
                'text-transform:uppercase;letter-spacing:0.08em;margin:0.9rem 0 0.4rem 0;">'
                '🗣 User Evidence</p>',
                unsafe_allow_html=True,
            )
            for quote in evidence:
                st.markdown(
                    f'<div style="border-left:3px solid #1DB954;padding:0.5rem 0.8rem;'
                    f'margin-bottom:0.5rem;background:#1a1a2e;border-radius:0 6px 6px 0;">'
                    f'<p style="color:#ccc;font-size:0.85rem;margin:0;">'
                    f'&ldquo;{quote}&rdquo;</p></div>',
                    unsafe_allow_html=True,
                )

    q_labels = {
        "q1": "❶  Why do users struggle to discover new music?",
        "q2": "❷  What are the most common recommendation frustrations?",
        "q3": "❸  What listening behaviors are users trying to achieve?",
        "q4": "❹  What causes users to repeatedly listen to the same content?",
        "q5": "❺  Which user segments experience different challenges?",
        "q6": "❻  What unmet needs emerge consistently from reviews?",
    }

    for key, label in q_labels.items():
        val = questions.get(key, "Not available.")
        with st.expander(label, expanded=False):
            if isinstance(val, dict) and "explanation" in val:
                # 1. Clear explanation paragraph (150-200 words)
                st.markdown(
                    f'<p style="font-size:0.95rem; line-height:1.6; color:#E0E0E0; margin-bottom:1rem; text-align:justify;">'
                    f'{val.get("explanation", "")}'
                    f'</p>',
                    unsafe_allow_html=True
                )
                
                # 2. Key Insights for that particular question
                insights = val.get("key_insights", [])
                if insights:
                    st.markdown(
                        '<p style="color:#1DB954; font-size:0.8rem; font-weight:700;'
                        'text-transform:uppercase; letter-spacing:0.08em; margin:1.2rem 0 0.5rem 0;">'
                        '🔑 Key Insights</p>',
                        unsafe_allow_html=True
                    )
                    for insight in insights:
                        st.markdown(f"- **Insight:** {insight}")
                
                # 3. Evidence from the Reviews
                ai_evidence = val.get("evidence", [])
                real_evidence = _get_evidence(key, n=1)
                all_evidence = list(ai_evidence) + real_evidence
                
                if all_evidence:
                    st.markdown(
                        '<p style="color:#B3B3B3; font-size:0.8rem; font-weight:700;'
                        'text-transform:uppercase; letter-spacing:0.08em; margin:1.2rem 0 0.5rem 0;">'
                        '🗣 Evidence from the Reviews</p>',
                        unsafe_allow_html=True
                    )
                    for quote in all_evidence:
                        st.markdown(
                            f'<div style="border-left:3px solid #1DB954; padding:0.6rem 0.8rem;'
                            f'margin-bottom:0.5rem; background:#1a1a2e; border-radius:0 6px 6px 0;">'
                            f'<p style="color:#ccc; font-size:0.85rem; margin:0; font-style:italic;">'
                            f'&ldquo;{quote}&rdquo;</p></div>',
                            unsafe_allow_html=True
                        )

            elif key == "q4" and isinstance(val, dict):
                st.markdown(
                    '<span style="color:#E8A400;font-weight:700;">⚠ Unwanted Repetition</span>'
                    ' — caused by algorithm failure',
                    unsafe_allow_html=True,
                )
                _render_bullets_and_evidence(val.get("unwanted_repetition", "Not available."), "q4")
                st.markdown("---")
                st.markdown(
                    '<span style="color:#1DB954;font-weight:700;">✓ Intentional Repetition</span>'
                    ' — deliberate user choice',
                    unsafe_allow_html=True,
                )
                _render_bullets_and_evidence(val.get("intentional_repetition", "Not available."), "q4")
            elif isinstance(val, dict):
                for k, v in val.items():
                    st.markdown(f"**{k.replace('_', ' ').title()}:**")
                    _render_bullets_and_evidence(str(v), key)
            elif isinstance(val, list):
                for item in val:
                    st.markdown(f"- {item}")
                evidence = _get_evidence(key)
                if evidence:
                    st.markdown(
                        '<p style="color:#B3B3B3;font-size:0.8rem;font-weight:700;'
                        'text-transform:uppercase;letter-spacing:0.08em;margin:0.9rem 0 0.4rem 0;">'
                        '🗣 User Evidence</p>',
                        unsafe_allow_html=True,
                    )
                    for quote in evidence:
                        st.markdown(
                            f'<div style="border-left:3px solid #1DB954;padding:0.5rem 0.8rem;'
                            f'margin-bottom:0.5rem;background:#1a1a2e;border-radius:0 6px 6px 0;">'
                            f'<p style="color:#ccc;font-size:0.85rem;margin:0;">'
                            f'&ldquo;{quote}&rdquo;</p></div>',
                            unsafe_allow_html=True,
                        )
            else:
                _render_bullets_and_evidence(str(val), key)


# ---------------------------------------------------------------------------
# Tab 4 — User Segments
# ---------------------------------------------------------------------------

def render_segments(questions: dict):
    """
    Render the Segments tab.

    One card per use-case-based user segment showing:
      - Segment name + repetition type chip
      - What they do / discovery blocker / repetition type
      - Evidence quote
    """
    _section_header("Use-Case Based User Segments")

    segments = questions.get("segments", [])

    if not segments:
        st.info("No user segments were identified in this analysis.")
        return

    st.markdown(
        f'<p class="muted">{len(segments)} distinct listening segments identified.</p>',
        unsafe_allow_html=True,
    )

    for seg in segments:
        rep_type = seg.get("repetition_type", "")
        chip = _rep_chip(rep_type)
        st.markdown(
            f"""
            <div class="insight-card">
                <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.4rem;">
                    <strong style="font-size:1rem;">👤 {seg.get('name', 'Segment')}</strong>
                    {chip}
                </div>
                <p class="muted" style="margin:0.3rem 0;">{seg.get('what_they_do', '')}</p>
                <p style="margin:0.4rem 0;">
                    <span style="color:#1DB954;font-weight:600;">Discovery blocker:</span>
                    {seg.get('discovery_blocker', '')}
                </p>
                <div style="border-left:3px solid #535353;padding-left:0.8rem;margin-top:0.6rem;">
                    <p style="font-size:0.85rem;color:#ccc;margin:0;">
                        &ldquo;{seg.get('evidence', '')}&rdquo;
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab 5 — Root Cause Synthesis
# ---------------------------------------------------------------------------

def render_root_causes(data: dict):
    """
    Render the Root Causes tab.

    Shows:
      - Bulleted list of primary root causes
      - Bulleted list of unwanted repetition causes
      - st.info block for intentional repetition note
    """
    _section_header("Root Cause Synthesis")

    if "error" in data:
        st.error(f"Analysis error: {data['error']}")
        return

    root_causes = data.get("root_causes", [])
    unwanted_causes = data.get("unwanted_repetition_causes", [])
    intentional_note = data.get("intentional_repetition_note", "")

    if root_causes:
        st.markdown(
            '<p style="color:#1DB954;font-weight:700;margin-bottom:0.3rem;">'
            '🔍 Primary Root Causes of Discovery Failure</p>',
            unsafe_allow_html=True,
        )
        for cause in root_causes:
            st.markdown(f"- {cause}")
    else:
        st.markdown('<p class="muted">No root causes extracted.</p>', unsafe_allow_html=True)

    st.markdown("---")

    if unwanted_causes:
        st.markdown(
            '<p style="color:#E8A400;font-weight:700;margin-bottom:0.3rem;">'
            '⚠ Causes of Unwanted Repetition</p>',
            unsafe_allow_html=True,
        )
        for cause in unwanted_causes:
            st.markdown(f"- {cause}")
    else:
        st.markdown('<p class="muted">No unwanted repetition causes extracted.</p>', unsafe_allow_html=True)

    if intentional_note:
        st.markdown("---")
        st.info(f"✓ **On intentional repetition:** {intentional_note}")


# ---------------------------------------------------------------------------
# Tab 6 — Unmet Needs
# ---------------------------------------------------------------------------

def render_unmet_needs(data: dict):
    """
    Render the Unmet Needs tab.

    One card per unmet need showing:
      - Need statement (framed as "Users need..." or "Listeners want...")
      - Segment label
      - Evidence quote from reviews
    """
    _section_header("Unmet User Needs")

    if "error" in data:
        st.error(f"Analysis error: {data['error']}")
        return

    needs = data.get("unmet_needs", [])

    if not needs:
        st.info("No unmet needs were identified in this analysis.")
        return

    st.markdown(
        f'<p class="muted">{len(needs)} unmet needs identified from the reviews.</p>',
        unsafe_allow_html=True,
    )

    for n in needs:
        segment = n.get("segment", "General")
        st.markdown(
            f"""
            <div class="insight-card">
                <strong style="font-size:1rem;">💡 {n.get('need', '')}</strong>
                <p class="muted" style="margin:0.3rem 0 0.6rem 0;">
                    <span style="color:#1DB954;">Segment:</span> {segment}
                </p>
                <p style="font-size:0.85rem;color:#ccc;margin:0;">{n.get('evidence', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab 7 — Key Insights & Infographics
# ---------------------------------------------------------------------------

def render_key_insights(data: dict, df, filtered_df, report: dict = None):
    """
    Render the Key Insights tab.

    Shows:
      - Systemic key insights with impact + actionable takeaway cards
      - 6 infographic charts — one per pattern/need:
          ❶ Why do users struggle to discover new music?
          ❷ What are the most common recommendation frustrations?
          ❸ What listening behaviors are users trying to achieve?
          ❹ What causes users to repeatedly listen to the same content?
          ❺ Which user segments experience different discovery challenges?
          ❻ What unmet needs emerge consistently across reviews?

    Args:
        data:        report["root_causes_and_needs"] dict (key_insights + unmet_needs)
        df:          Full reviews DataFrame (all sources, all tiers)
        filtered_df: Discovery-relevant reviews only
        report:      Full report dict (for questions + segments from Call 2)
    """
    _section_header("Key Insights & Actionable Takeaways")

    if "error" in data:
        st.error(f"Analysis error: {data['error']}")
        return

    # ------------------------------------------------------------------ #
    # Key Insight cards
    # ------------------------------------------------------------------ #
    insights = data.get("key_insights", [])

    if insights:
        for ki in insights:
            st.markdown(
                f"""
                <div class="insight-card">
                    <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.5rem;">
                        <strong style="font-size:1rem;">🔑 {ki.get('insight', 'Insight')}</strong>
                    </div>
                    <p style="margin:0.3rem 0 0.6rem 0;">
                        <span style="color:#1DB954;font-weight:600;">Impact on Listener:</span> {ki.get('impact', '')}
                    </p>
                    <div style="border-left:3px solid #1DB954;padding-left:0.8rem;margin-top:0.5rem;background-color:#1e2d24;padding-top:0.4rem;padding-bottom:0.4rem;border-radius:0 4px 4px 0;">
                        <p style="font-size:0.9rem;color:#fff;margin:0;font-weight:600;">
                            💡 Actionable Takeaway: {ki.get('actionable_takeaway', '')}
                        </p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No key insights were generated. Try running the analysis again.")

    st.markdown("---")
    _section_header("Infographics — Patterns and Needs Visualised")
    st.markdown(
        '<p class="muted" style="margin-bottom:1.2rem;">'
        'For each pattern and need: the <strong style="color:#fff;">AI analysis</strong> '
        '(left) paired with a <strong style="color:#fff;">keyword-frequency chart</strong> '
        'measuring how many discovery-relevant reviews echo each pattern (right).'
        '</p>',
        unsafe_allow_html=True,
    )

    # Pre-compute before helpers so all Q-sections can access them
    texts = filtered_df["review_text"].fillna("").tolist()
    questions = (report or {}).get("questions", {})

    # ------------------------------------------------------------------ #
    # Shared helper: count reviews that mention any keyword in a group
    # ------------------------------------------------------------------ #
    def _kw_counts(texts: list, groups: dict) -> pd.DataFrame:
        rows = []
        for label, keywords in groups.items():
            c = sum(1 for t in texts if any(kw in str(t).lower() for kw in keywords))
            rows.append({"Label": label, "Reviews": c})
        return pd.DataFrame(rows).set_index("Label")

    def _q_header(number: str, question: str):
        st.markdown(
            f'<p style="color:#1DB954;font-weight:700;font-size:1rem;margin:1.2rem 0 0.6rem 0;">'
            f'{number} {question}</p>',
            unsafe_allow_html=True,
        )

    def _ai_box(text: str):
        """Render the AI-generated answer in a styled panel."""
        st.markdown(
            f'<div style="background:#1a1a2e;border-left:3px solid #1DB954;'
            f'border-radius:0 6px 6px 0;padding:0.9rem 1rem;height:100%;min-height:160px;">'
            f'<p style="color:#aaa;font-size:0.72rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin:0 0 0.5rem 0;">AI Analysis</p>'
            f'<p style="color:#e0e0e0;font-size:0.88rem;line-height:1.55;margin:0;">{text}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )


    # ================================================================== #
    # Q1 — Why do users struggle to discover new music?
    # ================================================================== #
    _q_header("❶", "Why do users struggle to discover new music?")
    c_text, c_chart = st.columns([1, 1])
    with c_text:
        q1_ai = questions.get("q1", "")
        if isinstance(q1_ai, dict):
            q1_ai_text = q1_ai.get("explanation", "")
        else:
            q1_ai_text = str(q1_ai)
        _ai_box(q1_ai_text if q1_ai_text else "Run the analysis to generate AI insights.")
    with c_chart:
        try:
            q1_df = _kw_counts(texts, {
                "Algorithm doesn't learn taste":  ["algorithm", "doesn't learn", "ignores", "doesn't understand", "preference"],
                "Repetitive recommendations":      ["same song", "same artist", "same tracks", "keeps playing", "repeat", "loop"],
                "No genre / mood variety":         ["genre", "variety", "diverse", "different type", "different style", "monoton"],
                "Filter bubble / echo chamber":    ["bubble", "echo chamber", "comfort zone", "stuck in", "always plays"],
                "Poor discovery features":         ["discover", "new music", "new artist", "can't find", "hard to find", "explore"],
            })
            _spotify_bar_chart(q1_df, "Reviews mentioning each discovery-struggle pattern")
        except Exception as e:
            st.warning(f"Chart unavailable: {e}")

    st.markdown("---")

    # ================================================================== #
    # Q2 — Most common recommendation frustrations?
    # ================================================================== #
    _q_header("❷", "What are the most common frustrations with recommendations?")
    c_text, c_chart = st.columns([1, 1])
    with c_text:
        q2_ai = questions.get("q2", "")
        if isinstance(q2_ai, dict):
            q2_ai_text = q2_ai.get("explanation", "")
        else:
            q2_ai_text = str(q2_ai)
        _ai_box(q2_ai_text if q2_ai_text else "Run the analysis to generate AI insights.")
    with c_chart:
        try:
            q2_df = _kw_counts(texts, {
                "Feedback / thumbs ignored":      ["feedback", "thumbs", "dislike", "thumbs down", "doesn't listen", "doesn't take"],
                "Too similar / no variety":        ["too similar", "same type", "always same", "no variety", "monotonous", "repetitive"],
                "Taste / genre mismatch":          ["doesn't match", "wrong genre", "not my taste", "irrelevant", "random songs"],
                "Already-heard songs recycled":    ["already heard", "already know", "old songs", "recommend same", "heard before"],
                "Algorithm ignores context":        ["context", "ignores what", "doesn't remember", "time of day", "mood"],
            })
            _spotify_bar_chart(q2_df, "Reviews citing each recommendation frustration")
        except Exception as e:
            st.warning(f"Chart unavailable: {e}")

    st.markdown("---")

    # ================================================================== #
    # Q3 — What listening behaviors are users trying to achieve?
    # ================================================================== #
    _q_header("❸", "What listening behaviors are users trying to achieve?")
    c_text, c_chart = st.columns([1, 1])
    with c_text:
        q3_ai = questions.get("q3", "")
        if isinstance(q3_ai, dict):
            q3_ai_text = q3_ai.get("explanation", "")
        else:
            q3_ai_text = str(q3_ai)
        _ai_box(q3_ai_text if q3_ai_text else "Run the analysis to generate AI insights.")
    with c_chart:
        try:
            q3_df = _kw_counts(texts, {
                "Active discovery / exploration": ["discover", "explore", "new artist", "find new", "new music", "broaden"],
                "Mood / emotional listening":      ["mood", "feel", "emotion", "vibe", "sad", "happy", "chill", "relax"],
                "Focus / study / work":            ["focus", "study", "work", "concentrate", "background", "productive"],
                "Workout / high energy":            ["workout", "gym", "exercise", "run", "energy", "pump", "motivation"],
                "Social / shared listening":        ["share", "friend", "collaborate", "social", "group", "party", "together"],
            })
            _spotify_bar_chart(q3_df, "Reviews indicating each listening goal")
        except Exception as e:
            st.warning(f"Chart unavailable: {e}")

    st.markdown("---")

    # ================================================================== #
    # Q4 — What causes repeated listening? (unwanted vs intentional split)
    # ================================================================== #
    _q_header("❹", "What causes users to repeatedly listen to the same content?")
    c_text, c_chart = st.columns([1, 1])
    with c_text:
        q4_ai = questions.get("q4", {})
        if isinstance(q4_ai, dict) and "explanation" in q4_ai:
            _ai_box(q4_ai.get("explanation", ""))
        elif isinstance(q4_ai, dict) and ("unwanted_repetition" in q4_ai or "intentional_repetition" in q4_ai):
            unwanted = q4_ai.get("unwanted_repetition", "")
            intentional = q4_ai.get("intentional_repetition", "")
            st.markdown(
                f'<div style="background:#1a1a2e;border-left:3px solid #1DB954;'
                f'border-radius:0 6px 6px 0;padding:0.9rem 1rem;min-height:160px;">'
                f'<p style="color:#aaa;font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:0.08em;margin:0 0 0.5rem 0;">AI Analysis</p>'
                f'<p style="color:#E8A400;font-weight:700;font-size:0.8rem;margin:0 0 0.25rem 0;">⚠ Unwanted (Algorithm Failure)</p>'
                f'<p style="color:#e0e0e0;font-size:0.85rem;line-height:1.5;margin:0 0 0.8rem 0;">{unwanted}</p>'
                f'<p style="color:#1DB954;font-weight:700;font-size:0.8rem;margin:0 0 0.25rem 0;">✓ Intentional (User Choice)</p>'
                f'<p style="color:#e0e0e0;font-size:0.85rem;line-height:1.5;margin:0;">{intentional}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            _ai_box(str(q4_ai) if q4_ai else "Run the analysis to generate AI insights.")
    with c_chart:
        try:
            q4_df = _kw_counts(texts, {
                "Algorithmic loop (unwanted)":          ["algorithm", "same songs", "keeps repeating", "stuck", "loop", "can't escape", "forces"],
                "Comfort / familiarity (intentional)":  ["comfort", "familiar", "feel safe", "reassuring", "go-to", "favourite", "favorite"],
                "Autoplay behaviour":                   ["autoplay", "auto play", "auto-play", "plays automatically", "keeps playing"],
                "Limited library / offline mode":       ["offline", "downloaded", "limited library", "few songs", "cache"],
                "Mood anchoring":                       ["matches my mood", "perfect for", "fits the mood", "suits", "matches how"],
            })
            _spotify_bar_chart(q4_df, "Reviews attributing repetition to each cause — orange = unwanted, green = intentional")
        except Exception as e:
            st.warning(f"Chart unavailable: {e}")

    st.markdown("---")

    # ================================================================== #
    # Q5 — Which user segments face different discovery challenges?
    # ================================================================== #
    _q_header("❺", "Which user segments experience different discovery challenges?")
    segments = questions.get("segments", [])

    # AI text answer for Q5
    c_text, c_chart = st.columns([1, 1])
    with c_text:
        q5_ai = questions.get("q5", "")
        if isinstance(q5_ai, dict):
            q5_ai_text = q5_ai.get("explanation", "")
        else:
            q5_ai_text = str(q5_ai)

        if segments:
            # Build a mini segment card list inside the AI panel
            seg_html = (
                '<div style="background:#1a1a2e;border-left:3px solid #1DB954;'
                'border-radius:0 6px 6px 0;padding:0.9rem 1rem;min-height:160px;">'
                '<p style="color:#aaa;font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                'letter-spacing:0.08em;margin:0 0 0.6rem 0;">AI-Identified Segments</p>'
            )
            for seg in segments:
                rep = seg.get("repetition_type", "")
                rep_color = "#E8A400" if "Unwanted" in rep else ("#1DB954" if "Intentional" in rep else "#888")
                seg_html += (
                    f'<div style="margin-bottom:0.6rem;padding-bottom:0.6rem;border-bottom:1px solid #333;">'
                    f'<span style="font-size:0.85rem;font-weight:700;color:#fff;">👤 {seg.get("name","")}</span> '
                    f'<span style="background:{rep_color};color:#000;font-size:0.7rem;font-weight:700;'
                    f'padding:1px 7px;border-radius:500px;">{rep}</span>'
                    f'<p style="color:#aaa;font-size:0.8rem;margin:0.2rem 0 0 0;">{seg.get("discovery_blocker","")}</p>'
                    f'</div>'
                )
            seg_html += '</div>'
            st.markdown(seg_html, unsafe_allow_html=True)
        else:
            _ai_box(q5_ai_text if q5_ai_text else "Run the analysis to generate AI insights.")
    with c_chart:
        try:
            if segments:
                seg_rows = []
                for seg in segments:
                    name = seg.get("name", "Unknown Segment")
                    source_text = " ".join([
                        seg.get("what_they_do", ""),
                        seg.get("discovery_blocker", ""),
                    ])
                    kws = [w for w in source_text.lower().split() if len(w) > 4][:5]
                    count = sum(1 for t in texts if any(kw in str(t).lower() for kw in kws)) if kws else 0
                    seg_rows.append({"Segment": name, "Matching Reviews": count})
                seg_df = pd.DataFrame(seg_rows).set_index("Segment")
                _spotify_bar_chart(seg_df, "Estimated review volume per AI-identified user segment")
            else:
                q5_df = _kw_counts(texts, {
                    "Casual listeners":          ["casual", "sometimes", "occasionally", "whenever"],
                    "Power / daily users":        ["every day", "daily", "all the time", "constant", "always use"],
                    "Active music explorers":     ["discover", "explore", "new artist", "new genre", "find"],
                    "Mood-driven listeners":      ["mood", "feeling", "emotion", "vibe"],
                    "Comfort / repeat listeners": ["same playlist", "comfort", "familiar songs", "safe", "go-to"],
                })
                _spotify_bar_chart(q5_df, "Keyword-proxy segment volume (AI segments not available)")
        except Exception as e:
            st.warning(f"Chart unavailable: {e}")

    st.markdown("---")

    # ================================================================== #
    # Q6 — What unmet needs emerge consistently across reviews?
    # ================================================================== #
    _q_header("❻", "What unmet needs emerge consistently across reviews?")
    unmet_needs = data.get("unmet_needs", [])

    c_text, c_chart = st.columns([1, 1])
    with c_text:
        q6_ai = questions.get("q6", "")
        if isinstance(q6_ai, dict):
            q6_ai_text = q6_ai.get("explanation", "")
        else:
            q6_ai_text = str(q6_ai)

        if unmet_needs:
            # Build a mini need list inside the AI panel
            needs_html = (
                '<div style="background:#1a1a2e;border-left:3px solid #1DB954;'
                'border-radius:0 6px 6px 0;padding:0.9rem 1rem;min-height:160px;">'
                '<p style="color:#aaa;font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                'letter-spacing:0.08em;margin:0 0 0.6rem 0;">AI-Extracted Unmet Needs</p>'
            )
            for n in unmet_needs:
                needs_html += (
                    f'<div style="margin-bottom:0.55rem;padding-bottom:0.55rem;border-bottom:1px solid #333;">'
                    f'<p style="color:#fff;font-size:0.85rem;font-weight:600;margin:0 0 0.15rem 0;">'
                    f'💡 {n.get("need","")}</p>'
                    f'<p style="color:#aaa;font-size:0.78rem;margin:0;">'
                    f'<span style="color:#1DB954;">Segment:</span> {n.get("segment","General")}</p>'
                    f'</div>'
                )
            needs_html += '</div>'
            st.markdown(needs_html, unsafe_allow_html=True)
        else:
            _ai_box(q6_ai_text if q6_ai_text else "Run the analysis to generate AI insights.")
    with c_chart:
        try:
            if unmet_needs:
                need_rows = []
                for n in unmet_needs:
                    need_label = n.get("need", "")[:55].rstrip()
                    kws = [w for w in need_label.lower().split() if len(w) > 4][:5]
                    count = sum(1 for t in texts if any(kw in str(t).lower() for kw in kws)) if kws else 0
                    need_rows.append({"Unmet Need": need_label, "Matching Reviews": count})
                need_df = (
                    pd.DataFrame(need_rows)
                    .sort_values("Matching Reviews", ascending=False)
                    .set_index("Unmet Need")
                )
                _spotify_bar_chart(need_df, "AI-extracted unmet needs ranked by review corpus signal")
            else:
                q6_df = _kw_counts(texts, {
                    "Better discovery tools":       ["better discover", "improve discover", "discovery feature", "new music"],
                    "Algorithm that learns taste":  ["learn my taste", "understand me", "smarter", "better algorithm"],
                    "Genre / mood control":          ["genre control", "mood filter", "choose genre", "filter by mood"],
                    "Block / hide songs":            ["block", "hide", "never play", "ban", "exclude", "don't play again"],
                    "Feedback that works":           ["take my feedback", "listen to me", "thumbs work", "feedback"],
                })
                _spotify_bar_chart(q6_df, "Keyword-proxy unmet need volume (AI needs not available)")
        except Exception as e:
            st.warning(f"Chart unavailable: {e}")

    st.markdown(
        '<p class="muted" style="font-size:0.78rem;text-align:center;margin-top:1.2rem;">'
        '⚡ Charts = keyword-frequency analysis on discovery-relevant reviews. '
        'AI panels = direct LLM output from the 3-call analysis pipeline.'
        '</p>',
        unsafe_allow_html=True,
    )


