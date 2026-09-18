"""
Internship Radar -- local Streamlit dashboard.

Run with:  streamlit run app.py

This file wires together the collectors, database, and ranker modules in
src/ into a single-page dashboard with sidebar navigation. It intentionally
stays a single file for this first version (per project scope) but keeps
all the "real" logic (DB access, scoring, collecting) in src/ so this file
is mostly UI/orchestration.
"""

import pandas as pd
import streamlit as st

from src import db
from src.config import (
    DB_PATH,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    STATUS_OPTIONS,
    VIEWED_PAGE_STATUS_OPTIONS,
    ROLE_CATEGORIES,
    ROLE_CATEGORY_KEYWORDS,
    HIGH_FIT_SCORE_THRESHOLD,
)
from src.collectors.sample_source import get_sample_jobs
from src.collectors.board_apis import fetch_all_board_jobs
from src.dedupe import dedupe_job_list
from src.ranker import rank_job
from src.urls import is_valid_url, link_status
from src.refresh_state import save_refresh_state, load_refresh_state

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Internship Radar",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

PAGES = ["Dashboard", "All Internships", "Applied Tracker", "Viewed Jobs", "Settings"]
TOP_MATCHES_LIMIT = 6

# ---------------------------------------------------------------------------
# Styling -- JMU-colored, Greystone-inspired corporate dashboard look.
# No gradients, no heavy rounding, no cartoon icons.
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
:root {
    --jmu-purple: #450084;
    --jmu-gold: #CBB677;
    --bg-offwhite: #F7F5EF;
    --text-charcoal: #1F1F1F;
    --text-muted: #6B6B6B;
    --card-white: #FFFFFF;
    --border-thin: #E2DFD6;
    color-scheme: light;
}

html, body, [class*="css"] {
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: var(--text-charcoal);
}

/* Force light rendering regardless of OS/browser dark-mode preference --
   without this, native form controls (radio dots, etc.) and any color
   inherited from the UA dark stylesheet can end up unreadable. */
.stApp {
    background-color: var(--bg-offwhite);
    color-scheme: light;
}

/* Remove default Streamlit top padding so the header sits tighter */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* Headings */
h1, h2, h3 {
    color: var(--text-charcoal);
    font-weight: 600;
    letter-spacing: -0.01em;
}

a, .ir-card a {
    color: var(--jmu-purple);
    font-weight: 600;
    text-decoration: none;
}
a:hover, .ir-card a:hover {
    text-decoration: underline;
}

/* App title block */
.ir-header {
    border-bottom: 3px solid var(--jmu-purple);
    padding-bottom: 14px;
    margin-bottom: 6px;
}
.ir-title {
    font-size: 2.0rem;
    font-weight: 700;
    color: var(--jmu-purple);
    margin: 0;
    letter-spacing: -0.01em;
}
.ir-subtitle {
    font-size: 1.0rem;
    color: var(--text-muted);
    margin-top: 2px;
    font-weight: 400;
}
.ir-description {
    color: var(--text-charcoal);
    font-size: 0.92rem;
    margin-top: 10px;
    max-width: 780px;
    line-height: 1.5;
}

/* Section labels -- small caps style used above groups of content */
.ir-section-label {
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.72rem;
    color: var(--text-muted);
    font-weight: 600;
    margin-bottom: 8px;
    margin-top: 4px;
}

/* Divider */
.ir-divider {
    border: none;
    border-top: 1px solid var(--border-thin);
    margin: 22px 0;
}

/* Metric cards */
.ir-metric-row {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    margin-bottom: 8px;
}
.ir-metric-card {
    background-color: var(--card-white);
    border: 1px solid var(--border-thin);
    border-top: 3px solid var(--jmu-gold);
    border-radius: 3px;
    padding: 14px 18px;
    flex: 1;
    min-width: 150px;
}
.ir-metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--jmu-purple);
    line-height: 1.1;
}
.ir-metric-label {
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.68rem;
    color: var(--text-muted);
    font-weight: 600;
    margin-top: 4px;
}

/* Generic card container for grouped content */
.ir-card {
    background-color: var(--card-white);
    border: 1px solid var(--border-thin);
    border-radius: 3px;
    padding: 18px 20px;
    margin-bottom: 16px;
}

/* Job match cards on the Dashboard */
[class*="st-key-jobcard_"] {
    border: 1px solid var(--border-thin);
    border-radius: 3px;
    background-color: var(--card-white);
    padding: 16px 18px 10px 18px;
    margin-bottom: 14px;
}

/* Buttons -- primary (Refresh Jobs, Save Changes, etc.) */
.stButton > button {
    background-color: var(--jmu-purple);
    color: #FFFFFF;
    border: 1px solid var(--jmu-purple);
    border-radius: 3px;
    padding: 0.5rem 1.1rem;
    font-weight: 600;
    letter-spacing: 0.01em;
}
.stButton > button:hover {
    background-color: #350066;
    border-color: #350066;
    color: #FFFFFF;
}
.stButton > button:active {
    background-color: #29004f;
}
.stFormSubmitButton > button {
    background-color: var(--jmu-purple);
    color: #FFFFFF;
    border-radius: 3px;
    border: 1px solid var(--jmu-purple);
    font-weight: 600;
}

/* Quick-action buttons on job cards -- secondary/outline treatment so they
   don't compete visually with the primary purple buttons */
[class*="st-key-qa_"] .stButton > button {
    background-color: var(--card-white);
    color: var(--jmu-purple);
    border: 1px solid var(--jmu-purple);
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.35rem 0.5rem;
}
[class*="st-key-qa_"] .stButton > button:hover {
    background-color: var(--bg-offwhite);
    color: var(--jmu-purple);
}

/* ---------------------------------------------------------------------
   Sidebar -- forced light colors so nav text is always readable, plus a
   nav-link style for the page radio (hover + selected highlight).
   --------------------------------------------------------------------- */
[data-testid="stSidebar"] {
    background-color: var(--card-white) !important;
    border-right: 1px solid var(--border-thin);
    color-scheme: light;
}
[data-testid="stSidebar"] * {
    color: var(--text-charcoal) !important;
}
[data-testid="stSidebar"] .ir-sidebar-title {
    color: var(--jmu-purple) !important;
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: 0.03em;
    padding: 4px 0 10px 0;
    border-bottom: 2px solid var(--jmu-gold);
    margin-bottom: 10px;
}
[data-testid="stSidebar"] .ir-kv-key {
    color: var(--text-muted) !important;
}
[data-testid="stSidebar"] .ir-kv-val {
    color: var(--text-charcoal) !important;
    font-weight: 600;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 3px;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label {
    padding: 9px 12px;
    margin: 0;
    border-radius: 3px;
    border: 1px solid transparent;
    cursor: pointer;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label:hover {
    background-color: var(--bg-offwhite);
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label p {
    font-size: 0.92rem;
    font-weight: 500;
    margin: 0;
}
[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"] {
    accent-color: var(--jmu-purple);
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
    background-color: var(--jmu-purple);
    border-color: var(--jmu-purple);
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p {
    color: #FFFFFF !important;
    font-weight: 700;
}

/* Status / fit badges */
.ir-badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid var(--border-thin);
    background-color: var(--bg-offwhite);
    color: var(--text-charcoal);
    margin-right: 6px;
}
.ir-badge-highfit {
    background-color: var(--jmu-gold);
    border-color: var(--jmu-gold);
    color: var(--text-charcoal);
}

/* Dataframe / table tightening */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border-thin);
    border-radius: 3px;
}

/* Tone down Streamlit's default rounded input corners */
input, textarea, select, .stSelectbox div[data-baseweb="select"] > div {
    border-radius: 3px !important;
}

/* Metric-ish key/value rows used in Settings and job detail panels */
.ir-kv-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid var(--border-thin);
    font-size: 0.88rem;
}
.ir-kv-key {
    color: var(--text-muted);
}
.ir-kv-val {
    color: var(--text-charcoal);
    font-weight: 600;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def categorize_role(title: str, description: str = "") -> str:
    """Bucket a job into one of the ROLE_CATEGORIES based on keywords found
    in its title/description. First matching category wins."""
    text = f" {title} {description} ".lower()
    for category, keywords in ROLE_CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            return category
    return "Other"


def run_refresh() -> tuple:
    """
    Collect from every configured source, dedupe, save new postings, and
    score anything that doesn't have a score yet.

    Two sources feed the pipeline:
      - sample_source: static illustrative postings, always available, no
        network required. Useful the moment you first run the app, and as
        a fallback if the live sources below are unreachable.
      - board_apis: live postings pulled from each configured company's
        real Greenhouse/Lever job board (src.config.BOARD_SOURCES). A bad
        token or a network hiccup for one company is isolated there and
        never stops the others from coming through.

    Returns (new_job_count, scored_count, source_counts, board_stats) so the
    UI can show exactly where new postings came from and surface anything
    that needs attention (e.g. a stale board token).
    """
    sample_jobs = dedupe_job_list(get_sample_jobs())
    board_jobs, board_stats = fetch_all_board_jobs()
    board_jobs = dedupe_job_list(board_jobs)

    source_counts = {
        "sample_source": db.upsert_jobs(sample_jobs),
        "board_api": db.upsert_jobs(board_jobs),
    }
    new_count = sum(source_counts.values())

    unscored = db.get_jobs_needing_score()
    for job in unscored:
        result = rank_job(job)
        db.update_job_score(
            job["id"],
            result.get("score", 0),
            result.get("summary", ""),
            result.get("matched_skills", []),
        )

    save_refresh_state(source_counts, board_stats)

    return new_count, len(unscored), source_counts, board_stats


def load_jobs() -> pd.DataFrame:
    """Load every job straight from SQLite (no caching -- this is a small
    local dataset, and a stale cache is worse than an extra query)."""
    df = db.get_all_jobs_df()
    if df.empty:
        return df
    df = df.copy()
    df["role_category"] = df.apply(
        lambda row: categorize_role(row.get("title", ""), row.get("description", "")),
        axis=1,
    )
    df["is_viewed"] = (df["viewed"] == 1) | (df["status"] == "Viewed")
    return df


def render_metrics(df: pd.DataFrame) -> None:
    new_roles = int((df["status"] == "New").sum()) if not df.empty else 0
    high_fit = int((df["score"].fillna(0) >= HIGH_FIT_SCORE_THRESHOLD).sum()) if not df.empty else 0
    viewed_jobs = int(df["is_viewed"].sum()) if not df.empty else 0
    applied = int((df["status"] == "Applied").sum()) if not df.empty else 0
    interviews = int((df["status"] == "Interview").sum()) if not df.empty else 0

    metrics = [
        ("New Roles", new_roles),
        ("High-Fit Roles", high_fit),
        ("Viewed Jobs", viewed_jobs),
        ("Applied", applied),
        ("Interviews", interviews),
    ]

    cards_html = '<div class="ir-metric-row">'
    for label, value in metrics:
        cards_html += (
            f'<div class="ir-metric-card">'
            f'<div class="ir-metric-value">{value}</div>'
            f'<div class="ir-metric-label">{label}</div>'
            f'</div>'
        )
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)


def apply_filters(
    df: pd.DataFrame,
    status_filter,
    min_score,
    search_text,
    category_filter,
    viewed_only: bool = False,
    unviewed_only: bool = False,
) -> pd.DataFrame:
    if df.empty:
        return df

    filtered = df.copy()

    if status_filter and "All" not in status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]

    filtered = filtered[filtered["score"].fillna(0) >= min_score]

    if category_filter and "All" not in category_filter:
        filtered = filtered[filtered["role_category"].isin(category_filter)]

    if viewed_only:
        filtered = filtered[filtered["is_viewed"]]
    if unviewed_only:
        filtered = filtered[~filtered["is_viewed"]]

    if search_text:
        needle = search_text.strip().lower()
        mask = (
            filtered["company"].str.lower().str.contains(needle, na=False)
            | filtered["title"].str.lower().str.contains(needle, na=False)
            | filtered["location"].str.lower().str.contains(needle, na=False)
        )
        filtered = filtered[mask]

    return filtered


def render_filters(df: pd.DataFrame) -> tuple:
    st.markdown('<div class="ir-section-label">Filters</div>', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([1.2, 1, 1.4, 1.2])

    with f1:
        status_filter = st.multiselect(
            "Status", options=["All"] + STATUS_OPTIONS, default=["All"]
        )
    with f2:
        min_score = st.slider("Minimum score", min_value=0, max_value=100, value=0, step=5)
    with f3:
        search_text = st.text_input("Search company / title / location", value="")
    with f4:
        category_filter = st.multiselect(
            "Role category", options=["All"] + ROLE_CATEGORIES, default=["All"]
        )

    v1, v2, _ = st.columns([1, 1, 2.4])
    with v1:
        viewed_only = st.checkbox("Viewed only")
    with v2:
        unviewed_only = st.checkbox("Unviewed only")

    return status_filter, min_score, search_text, category_filter, viewed_only, unviewed_only


def _score_badge_html(score) -> str:
    if pd.isna(score):
        return '<span class="ir-badge">Unscored</span>'
    score = int(score)
    if score >= HIGH_FIT_SCORE_THRESHOLD:
        return f'<span class="ir-badge ir-badge-highfit">High Fit &middot; {score}</span>'
    return f'<span class="ir-badge">Score {score}</span>'


def render_job_cards(df: pd.DataFrame, key_prefix: str) -> None:
    """Card-per-job layout used for the Dashboard's Top Internship Matches,
    each with quick-action status buttons."""
    if df.empty:
        st.markdown(
            '<div class="ir-card">No scored postings yet. Click '
            "<strong>Refresh Jobs</strong> above to pull in postings.</div>",
            unsafe_allow_html=True,
        )
        return

    ranked = df.dropna(subset=["score"]).sort_values("score", ascending=False)
    if ranked.empty:
        ranked = df

    for _, row in ranked.head(TOP_MATCHES_LIMIT).iterrows():
        job_id = int(row["id"])
        with st.container(key=f"jobcard_{key_prefix}_{job_id}"):
            st.markdown(f"**{row['company']}**")
            st.markdown(f"{row['title']}")
            st.markdown(f"{row['location']} &middot; Source: {row['source']}")
            st.markdown(
                _score_badge_html(row["score"])
                + f'<span class="ir-badge">{row["status"]}</span>'
                + ('<span class="ir-badge">Viewed</span>' if row["is_viewed"] else ""),
                unsafe_allow_html=True,
            )
            if row.get("ai_summary"):
                st.markdown(f"_{row['ai_summary']}_")
            if is_valid_url(row.get("url")):
                st.markdown(f"[Open posting]({row['url']})")
            else:
                st.markdown('<span class="ir-badge">No verified link</span>', unsafe_allow_html=True)

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button("Mark Viewed", key=f"qa_viewed_{key_prefix}_{job_id}", width='stretch'):
                    db.update_job_status(job_id, "Viewed")
                    st.rerun()
            with b2:
                if st.button("Mark Interested", key=f"qa_interested_{key_prefix}_{job_id}", width='stretch'):
                    db.update_job_status(job_id, "Interested")
                    st.rerun()
            with b3:
                if st.button("Mark Applied", key=f"qa_applied_{key_prefix}_{job_id}", width='stretch'):
                    db.update_job_status(job_id, "Applied")
                    st.rerun()
            with b4:
                if st.button("Not Interested", key=f"qa_notint_{key_prefix}_{job_id}", width='stretch'):
                    db.update_job_status(job_id, "Not Interested")
                    st.rerun()


def render_all_internships_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.markdown(
            '<div class="ir-card">No jobs match the current filters yet. '
            "Click **Refresh Jobs** on the Dashboard to pull in postings.</div>",
            unsafe_allow_html=True,
        )
        return

    display_df = df.copy()
    display_df["Viewed"] = display_df["is_viewed"].map({True: "Yes", False: "No"})
    display_df["Notes Preview"] = display_df["notes"].fillna("").str.slice(0, 60)
    display_df["Link Status"] = display_df.apply(
        lambda r: link_status(r["url"], r["source"]), axis=1
    )
    # Only a genuinely valid URL is allowed into the link column -- anything
    # else (blank, or a placeholder like ".../404") becomes None so it
    # renders as an empty, non-clickable cell instead of a fake/broken link.
    display_df["Application URL"] = display_df["url"].where(
        display_df["url"].apply(is_valid_url), None
    )

    display_df = display_df[
        [
            "company", "title", "location", "score", "status", "ai_summary",
            "source", "Application URL", "Link Status", "Viewed", "Notes Preview",
        ]
    ].rename(
        columns={
            "company": "Company",
            "title": "Title",
            "location": "Location",
            "score": "Score",
            "status": "Status",
            "ai_summary": "AI Summary",
            "source": "Source",
        }
    )

    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        column_config={
            "Application URL": st.column_config.LinkColumn("Application URL", display_text="Open posting"),
            "Score": st.column_config.NumberColumn("Score", format="%d"),
        },
    )


def render_applied_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.markdown('<div class="ir-card">No applications tracked yet.</div>', unsafe_allow_html=True)
        return

    display_df = df.copy()
    display_df["Applied Date"] = display_df["applied_at"].fillna("").str.slice(0, 10)
    display_df["url"] = display_df["url"].where(display_df["url"].apply(is_valid_url), None)
    display_df = display_df[
        ["company", "title", "location", "Applied Date", "score", "notes", "url"]
    ].rename(
        columns={
            "company": "Company",
            "title": "Title",
            "location": "Location",
            "score": "Score",
            "notes": "Notes",
            "url": "URL",
        }
    )
    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        column_config={
            "URL": st.column_config.LinkColumn("URL", display_text="Open posting"),
            "Score": st.column_config.NumberColumn("Score", format="%d"),
        },
    )


def render_viewed_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.markdown('<div class="ir-card">No viewed jobs yet.</div>', unsafe_allow_html=True)
        return

    display_df = df.copy()
    display_df["Viewed Date"] = display_df["viewed_at"].fillna("").str.slice(0, 10)
    display_df["url"] = display_df["url"].where(display_df["url"].apply(is_valid_url), None)
    display_df = display_df[
        ["company", "title", "location", "Viewed Date", "status", "score", "notes", "url"]
    ].rename(
        columns={
            "company": "Company",
            "title": "Title",
            "location": "Location",
            "status": "Status",
            "score": "Score",
            "notes": "Notes",
            "url": "URL",
        }
    )
    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True,
        column_config={
            "URL": st.column_config.LinkColumn("URL", display_text="Open posting"),
            "Score": st.column_config.NumberColumn("Score", format="%d"),
        },
    )


def render_job_detail_editor(df: pd.DataFrame, key_suffix: str, allowed_statuses=None) -> None:
    """Select a job, edit its status/notes/viewed flag, and save back to
    SQLite. Selecting a job here always marks it as viewed."""
    if df.empty:
        return

    status_choices = allowed_statuses if allowed_statuses else STATUS_OPTIONS

    st.markdown('<div class="ir-section-label">Job Detail & Editing</div>', unsafe_allow_html=True)

    options = {
        int(row["id"]): f'{row["company"]} — {row["title"]} ({row["location"]})'
        for _, row in df.iterrows()
    }
    selected_id = st.selectbox(
        "Select a job to update",
        options=list(options.keys()),
        format_func=lambda job_id: options[job_id],
        key=f"selected_job_id_{key_suffix}",
    )

    job_row = df[df["id"] == selected_id].iloc[0]

    with st.container():
        st.markdown('<div class="ir-card">', unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**{job_row['title']}**")
            st.markdown(f"{job_row['company']} · {job_row['location']} · Source: {job_row['source']}")
            if job_row.get("ai_summary"):
                st.markdown(f"_{job_row['ai_summary']}_")
            if job_row.get("matched_skills"):
                st.markdown(f"**Matched skills:** {job_row['matched_skills']}")
            if is_valid_url(job_row.get("url")):
                st.markdown(f"[Open posting]({job_row['url']})")
            else:
                st.markdown('<span class="ir-badge">No verified link</span>', unsafe_allow_html=True)
        with col2:
            score_display = job_row["score"] if pd.notna(job_row["score"]) else "—"
            applied_display = str(job_row.get("applied_at") or "—")[:10]
            viewed_display = str(job_row.get("viewed_at") or "—")[:10]
            st.markdown(
                f'<div class="ir-kv-row"><span class="ir-kv-key">Score</span>'
                f'<span class="ir-kv-val">{score_display}</span></div>'
                f'<div class="ir-kv-row"><span class="ir-kv-key">Viewed</span>'
                f'<span class="ir-kv-val">{viewed_display}</span></div>'
                f'<div class="ir-kv-row"><span class="ir-kv-key">Applied</span>'
                f'<span class="ir-kv-val">{applied_display}</span></div>',
                unsafe_allow_html=True,
            )

        with st.form(key=f"edit_form_{key_suffix}_{selected_id}"):
            current_status = job_row["status"] if job_row["status"] in status_choices else status_choices[0]
            new_status = st.selectbox(
                "Status",
                options=status_choices,
                index=status_choices.index(current_status),
            )
            new_viewed = st.checkbox("Viewed", value=bool(job_row["is_viewed"]))
            new_notes = st.text_area("Notes", value=job_row.get("notes") or "", height=100)
            submitted = st.form_submit_button("Save Changes")

            if submitted:
                db.update_job_full(int(selected_id), new_status, new_notes, new_viewed)
                st.success("Job updated.")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

st.sidebar.markdown('<div class="ir-sidebar-title">INTERNSHIP RADAR</div>', unsafe_allow_html=True)
page = st.sidebar.radio(
    "Navigate",
    options=PAGES,
    label_visibility="collapsed",
)

st.sidebar.markdown('<hr class="ir-divider">', unsafe_allow_html=True)
st.sidebar.markdown(
    f'<div class="ir-kv-row"><span class="ir-kv-key">Database</span>'
    f'<span class="ir-kv-val">SQLite</span></div>'
    f'<div class="ir-kv-row"><span class="ir-kv-key">Scoring</span>'
    f'<span class="ir-kv-val">{"OpenAI" if OPENAI_API_KEY else "Keyword fallback"}</span></div>',
    unsafe_allow_html=True,
)

# Opening a job's detail editor marks it viewed. The relevant selectbox key
# already holds the newly-selected id (Streamlit updates session_state
# before rerunning), so applying this before loading jobs_df lets metrics
# reflect it on the very same run instead of lagging a step behind.
_detail_editor_keys = {
    "All Internships": "selected_job_id_all",
    "Applied Tracker": "selected_job_id_applied",
    "Viewed Jobs": "selected_job_id_viewed",
}
_detail_editor_key = _detail_editor_keys.get(page)
if _detail_editor_key and _detail_editor_key in st.session_state:
    db.mark_viewed(int(st.session_state[_detail_editor_key]))


# ---------------------------------------------------------------------------
# Header (shown on every page)
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="ir-header">
        <div class="ir-title">Internship Radar</div>
        <div class="ir-subtitle">Summer 2027 Software, AI &amp; Coding Internship Intelligence</div>
        <div class="ir-description">
            A local dashboard for discovering and tracking Summer 2027 software engineering,
            AI/ML, data science, cloud, and cybersecurity internships. Pull new postings on
            demand, score each one for fit, and manage your pipeline from a single view.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

jobs_df = load_jobs()


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------

if page == "Dashboard":
    top_col1, top_col2 = st.columns([5, 1])
    with top_col2:
        if st.button("Refresh Jobs", width='stretch'):
            with st.spinner("Collecting and scoring postings..."):
                new_count, scored_count, source_counts, board_stats = run_refresh()
            board_errors = [s for s in board_stats if s["error"]]
            st.success(
                f"Added {new_count} new job(s) "
                f"({source_counts.get('sample_source', 0)} sample, "
                f"{source_counts.get('board_api', 0)} live). "
                f"Scored {scored_count} job(s)."
            )
            if board_errors:
                st.warning(
                    f"{len(board_errors)} live source(s) couldn't be reached this "
                    "time -- see Settings for details."
                )
            jobs_df = load_jobs()

    st.markdown('<div class="ir-section-label">Overview</div>', unsafe_allow_html=True)
    render_metrics(jobs_df)

    refresh_state = load_refresh_state()
    if refresh_state.get("refreshed_at"):
        counts = refresh_state.get("source_counts", {})
        st.caption(
            f"Last refreshed {refresh_state['refreshed_at']} · "
            f"{counts.get('sample_source', 0)} from sample data, "
            f"{counts.get('board_api', 0)} from live company boards."
        )

    st.markdown('<hr class="ir-divider">', unsafe_allow_html=True)
    st.markdown('<div class="ir-section-label">Top Internship Matches</div>', unsafe_allow_html=True)
    render_job_cards(jobs_df, key_prefix="dash")


# ---------------------------------------------------------------------------
# All Internships page
# ---------------------------------------------------------------------------

elif page == "All Internships":
    status_filter, min_score, search_text, category_filter, viewed_only, unviewed_only = render_filters(jobs_df)
    filtered_df = apply_filters(
        jobs_df, status_filter, min_score, search_text, category_filter, viewed_only, unviewed_only
    )

    sort_col, _ = st.columns([1, 3])
    with sort_col:
        sort_choice = st.selectbox(
            "Sort by",
            options=["Best fit first", "Newest first", "Company A-Z"],
        )
    if not filtered_df.empty:
        if sort_choice == "Best fit first":
            filtered_df = filtered_df.sort_values("score", ascending=False, na_position="last")
        elif sort_choice == "Newest first":
            filtered_df = filtered_df.sort_values("discovered_at", ascending=False)
        elif sort_choice == "Company A-Z":
            filtered_df = filtered_df.sort_values("company", key=lambda s: s.str.lower())

    st.markdown('<div class="ir-section-label">All Postings</div>', unsafe_allow_html=True)
    render_all_internships_table(filtered_df)

    st.markdown('<hr class="ir-divider">', unsafe_allow_html=True)
    render_job_detail_editor(filtered_df, key_suffix="all")


# ---------------------------------------------------------------------------
# Applied Tracker page
# ---------------------------------------------------------------------------

elif page == "Applied Tracker":
    applied_df = jobs_df[jobs_df["status"] == "Applied"] if not jobs_df.empty else jobs_df

    st.markdown('<div class="ir-section-label">Application Pipeline</div>', unsafe_allow_html=True)
    render_metrics(jobs_df)

    st.markdown('<hr class="ir-divider">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ir-section-label">Applied Jobs &middot; {len(applied_df)} total</div>',
        unsafe_allow_html=True,
    )
    render_applied_table(applied_df)

    st.markdown('<hr class="ir-divider">', unsafe_allow_html=True)
    render_job_detail_editor(applied_df, key_suffix="applied")


# ---------------------------------------------------------------------------
# Viewed Jobs page
# ---------------------------------------------------------------------------

elif page == "Viewed Jobs":
    viewed_df = jobs_df[jobs_df["is_viewed"]] if not jobs_df.empty else jobs_df

    st.markdown('<div class="ir-section-label">Overview</div>', unsafe_allow_html=True)
    render_metrics(jobs_df)

    st.markdown('<hr class="ir-divider">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ir-section-label">Viewed Jobs &middot; {len(viewed_df)} total</div>',
        unsafe_allow_html=True,
    )
    render_viewed_table(viewed_df)

    st.markdown('<hr class="ir-divider">', unsafe_allow_html=True)
    render_job_detail_editor(viewed_df, key_suffix="viewed", allowed_statuses=VIEWED_PAGE_STATUS_OPTIONS)


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------

elif page == "Settings":
    st.markdown('<div class="ir-section-label">Configuration</div>', unsafe_allow_html=True)

    total_jobs = len(jobs_df)
    key_status = "Detected" if OPENAI_API_KEY else "Not set (using keyword fallback scoring)"
    scoring_mode = "OpenAI" if OPENAI_API_KEY else "Keyword fallback"

    st.markdown(
        f"""
        <div class="ir-card">
            <div class="ir-kv-row"><span class="ir-kv-key">OpenAI API Key</span><span class="ir-kv-val">{key_status}</span></div>
            <div class="ir-kv-row"><span class="ir-kv-key">Scoring Mode</span><span class="ir-kv-val">{scoring_mode}</span></div>
            <div class="ir-kv-row"><span class="ir-kv-key">OpenAI Model</span><span class="ir-kv-val">{OPENAI_MODEL}</span></div>
            <div class="ir-kv-row"><span class="ir-kv-key">Database File</span><span class="ir-kv-val">{DB_PATH}</span></div>
            <div class="ir-kv-row"><span class="ir-kv-key">Total Jobs Stored</span><span class="ir-kv-val">{total_jobs}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ir-section-label">Live Data Sources</div>', unsafe_allow_html=True)
    refresh_state = load_refresh_state()
    board_stats = refresh_state.get("board_stats", [])
    if not board_stats:
        st.markdown(
            '<div class="ir-card">No refresh has run yet this session with live-source '
            "data available. Click <strong>Refresh Jobs</strong> on the Dashboard to pull "
            "from the configured company boards (see src/config.py: BOARD_SOURCES).</div>",
            unsafe_allow_html=True,
        )
    else:
        rows_html = ""
        for stat in board_stats:
            status_text = f"Error: {stat['error']}" if stat["error"] else f"{stat['found']} relevant posting(s)"
            status_color = "var(--text-muted)" if stat["error"] else "var(--jmu-purple)"
            rows_html += (
                f'<div class="ir-kv-row"><span class="ir-kv-key">'
                f'{stat["company"]} ({stat["board"]}, token: {stat["token"]})</span>'
                f'<span class="ir-kv-val" style="color:{status_color}">{status_text}</span></div>'
            )
        st.markdown(f'<div class="ir-card">{rows_html}</div>', unsafe_allow_html=True)
        error_count = sum(1 for s in board_stats if s["error"])
        if error_count:
            st.caption(
                f"{error_count} board token(s) returned an error on the last refresh. "
                "A company may have renamed its board, switched ATS providers, or been "
                "temporarily unreachable -- update the token in src/config.py's "
                "BOARD_SOURCES, or run scripts/verify_boards.py to check all of them at once."
            )

    st.markdown('<div class="ir-section-label">How To Use This App</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="ir-card">
        Click <strong>Refresh Jobs</strong> on the Dashboard whenever you want new postings
        pulled in -- there is no background scheduler, so nothing happens until you ask for it.
        New postings are deduplicated against what's already stored, scored for fit, and added
        to the database. Use <strong>All Internships</strong> to filter and edit any job,
        <strong>Applied Tracker</strong> to see everything you've applied to, and
        <strong>Viewed Jobs</strong> to revisit postings you've already looked at. Selecting a
        job in any detail editor automatically marks it viewed; setting a job's status to
        <em>Applied</em> stamps an applied date the first time it happens.
        Set <code>OPENAI_API_KEY</code> in a <code>.env</code> file to enable AI-based scoring;
        without it, the app scores jobs using a transparent keyword fallback so it always
        remains usable.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ir-section-label">Danger Zone</div>', unsafe_allow_html=True)
    with st.expander("Clear all stored jobs"):
        st.markdown("This permanently deletes every job in the local database. This cannot be undone.")
        confirm = st.checkbox("I understand this will delete all stored job data.")
        if st.button("Clear Database", disabled=not confirm):
            conn = db.get_connection()
            conn.execute("DELETE FROM jobs")
            conn.commit()
            conn.close()
            st.success("Database cleared.")
            st.rerun()
