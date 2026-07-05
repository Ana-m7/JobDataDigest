"""JobDataDigest: minimal interactive demo of the job market analysis.

Scope is deliberately narrow (by design, not by time pressure): a role/city
filter over the same skill-demand and salary numbers computed in
notebooks/03_sql_analytics.ipynb, re-shown live rather than as static
notebook output. It intentionally does not include a live salary-prediction
form: that would require justifying a much larger, harder-to-verify surface
area for a "minimal" deployed app. The trained model
(models/salary_band_model.joblib) is evaluated properly in
notebooks/04_ml_model.ipynb instead.

Data: app/data/*.csv, a small committed snapshot. See
app/export_app_data.py for why this app doesn't read the gitignored SQLite
database directly.

Run locally:
    streamlit run app/app.py
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"

# "Unknown" (seniority couldn't be inferred from the posting text) is a real
# category in the database and is analyzed in notebooks/03_sql_analytics.ipynb,
# but it isn't meaningful to someone using this app to gauge fresher pay, so
# the app only ever shows the three decision-relevant bands.
SENIORITY_ORDER = ["Junior", "Mid", "Senior"]

# A role's own name can be a tracked skill (Machine Learning Engineer /
# "Machine Learning"). When that role is selected, nearly every posting
# matches that skill simply because it was part of the search query used to
# pull the postings in the first place -- not because it's informative. It's
# excluded only in this per-role view; the all-roles aggregate is unaffected.
ROLE_SELF_SKILLS = {
    "Machine Learning Engineer": {"Machine Learning"},
}

# Theme constants, kept in one place so the Plotly charts always match the
# app theme in .streamlit/config.toml exactly rather than drifting from it.
PAGE_BG = "#0d0d0d"
CARD_BG = "#161615"
GRIDLINE = "#2c2c2a"
TEXT_PRIMARY = "#ffffff"
TEXT_MUTED = "#9c9b95"
ACCENT = "#3987e5"
FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

st.set_page_config(page_title="JobDataDigest", page_icon=None, layout="wide")

st.markdown(
    f"""
    <style>
    #MainMenu, header, footer, [data-testid="stToolbar"] {{
        visibility: hidden;
        height: 0;
    }}
    html, body, [class*="css"] {{
        font-family: {FONT_FAMILY};
    }}
    h1, h2, h3 {{
        font-weight: 600 !important;
        letter-spacing: -0.01em;
    }}
    [data-testid="stMetricValue"] {{
        font-weight: 600;
    }}
    [data-testid="stMetricLabel"] {{
        color: {TEXT_MUTED};
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    .section-label {{
        color: {TEXT_MUTED};
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.25rem;
    }}
    .app-subtitle {{
        color: {TEXT_MUTED};
        font-size: 0.95rem;
        margin-top: -0.6rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    postings = pd.read_csv(DATA_DIR / "postings.csv")
    posting_skills = pd.read_csv(DATA_DIR / "posting_skills.csv")
    return postings, posting_skills


def styled_bar_figure(categories, raw_values, orientation, mode="count", height=420):
    """mode="count" for plain postings counts; mode="salary" converts INR/year
    into Lakhs (Indian convention: 1L = Rs 1,00,000) and labels the axis and
    each bar accordingly, since Adzuna's figures are confirmed annual."""
    if mode == "salary":
        plot_values = [v / 100_000 for v in raw_values]
        bar_text = [f"₹{v:.1f}L" for v in plot_values]
        hover_text = [f"₹{v:.1f}L / year" for v in plot_values]
        numeric_axis_title = "₹ Lakhs / year"
    else:
        plot_values = list(raw_values)
        bar_text = [f"{v:,.0f}" for v in plot_values]
        hover_text = [f"{v:,.0f} postings" for v in plot_values]
        numeric_axis_title = "Postings"

    x, y = (plot_values, categories) if orientation == "h" else (categories, plot_values)

    fig = go.Figure(
        go.Bar(
            x=x, y=y, orientation=orientation,
            marker_color=ACCENT,
            text=bar_text,
            textposition="outside",
            textfont=dict(color=TEXT_PRIMARY, size=12, family=FONT_FAMILY),
            hovertext=hover_text,
            hoverinfo="text",
        )
    )
    fig.update_layout(
        height=height,
        plot_bgcolor=PAGE_BG,
        paper_bgcolor=PAGE_BG,
        font=dict(family=FONT_FAMILY, color=TEXT_MUTED, size=13),
        margin=dict(l=10, r=90, t=10, b=10),
        xaxis=dict(
            showgrid=orientation == "h", gridcolor=GRIDLINE, zeroline=False,
            showline=False,
            tickfont=dict(color=TEXT_PRIMARY if orientation == "v" else TEXT_MUTED, size=13),
            title_text=numeric_axis_title if orientation == "h" else None,
            automargin=True,
        ),
        yaxis=dict(
            showgrid=orientation == "v", gridcolor=GRIDLINE, zeroline=False,
            showline=False,
            tickfont=dict(color=TEXT_PRIMARY if orientation == "h" else TEXT_MUTED, size=13),
            title_text=numeric_axis_title if orientation == "v" else None,
            automargin=True,
        ),
        bargap=0.35,
    )
    return fig


postings, posting_skills = load_data()
pull_date = postings["pull_date"].max()

st.title("JobDataDigest")
st.markdown(
    f'<div class="app-subtitle">{len(postings):,} postings · 6 roles · 6 Indian metros · '
    f'as of {pull_date}</div>',
    unsafe_allow_html=True,
)
st.write("")

if "applied_role" not in st.session_state:
    st.session_state.applied_role = "All roles"
    st.session_state.applied_city = "All cities"

with st.container(border=True):
    st.markdown('<div class="section-label">Filters</div>', unsafe_allow_html=True)
    with st.form("filters_form"):
        col1, col2, col3 = st.columns([3, 3, 1])
        role_choice = col1.selectbox("Role", ["All roles"] + sorted(postings["primary_role"].unique()))
        city_choice = col2.selectbox("City", ["All cities"] + sorted(postings["city"].unique()))
        col3.write("")
        col3.write("")
        submitted = col3.form_submit_button("Generate", use_container_width=True)
        if submitted:
            st.session_state.applied_role = role_choice
            st.session_state.applied_city = city_choice

role = st.session_state.applied_role
city = st.session_state.applied_city

filtered = postings
if role != "All roles":
    filtered = filtered[filtered["primary_role"] == role]
if city != "All cities":
    filtered = filtered[filtered["city"] == city]

st.caption(f"Showing results for {role}, {city}")

if filtered.empty:
    st.warning("No postings match this filter.")
    st.stop()

salaried = filtered[filtered["has_salary"] == 1]
disclosure_rate = len(salaried) / len(filtered)
avg_salary = salaried["salary_avg"].mean() if len(salaried) else None
junior_salaried = salaried[salaried["seniority"] == "Junior"]
fresher_avg_salary = junior_salaried["salary_avg"].mean() if len(junior_salaried) else None

st.write("")
with st.container(border=True):
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Postings", f"{len(filtered):,}")
    m2.metric("Salary disclosed", f"{disclosure_rate:.0%}")
    m3.metric(
        "Avg advertised salary (per year)",
        f"₹{avg_salary / 100_000:.1f}L" if avg_salary else "n/a",
    )
    m4.metric(
        "Fresher (Junior) salary",
        f"₹{fresher_avg_salary / 100_000:.1f}L" if fresher_avg_salary else "No data",
        help="Average salary for postings inferred as Junior seniority.",
    )

st.write("")
left, right = st.columns(2)

with left:
    with st.container(border=True):
        st.markdown('<div class="section-label">Skill demand</div>', unsafe_allow_html=True)
        st.subheader("Top skills in demand")

        skills_in_filtered = posting_skills[posting_skills["posting_id"].isin(filtered["posting_id"])]
        excluded_self_skill = ROLE_SELF_SKILLS.get(role)
        if excluded_self_skill:
            skills_in_filtered = skills_in_filtered[~skills_in_filtered["skill"].isin(excluded_self_skill)]

        top = skills_in_filtered["skill"].value_counts().head(12).reset_index()
        top.columns = ["skill", "postings"]

        if excluded_self_skill:
            st.caption(f"{', '.join(excluded_self_skill)} excluded: it is part of the {role} search term itself.")

        if top.empty:
            st.info("No tracked skills detected for this filter.")
        else:
            top = top.sort_values("postings")
            fig = styled_bar_figure(top["skill"], top["postings"], orientation="h", mode="count")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.caption("Skill counts are relative, not absolute: descriptions are truncated at 500 characters.")

with right:
    with st.container(border=True):
        st.markdown('<div class="section-label">Compensation</div>', unsafe_allow_html=True)
        st.subheader("Average salary by seniority")

        sal_by_level = salaried.groupby("seniority")["salary_avg"].mean().reindex(SENIORITY_ORDER)
        present = sal_by_level.dropna()
        missing = [level for level in SENIORITY_ORDER if level not in present.index]

        if present.empty:
            st.info("Not enough salary disclosed postings in this filter to break down by seniority.")
        else:
            sal = present.reset_index()
            fig2 = styled_bar_figure(sal["seniority"], sal["salary_avg"], orientation="v", mode="salary")
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            if missing:
                st.caption(f"No salary disclosed {', '.join(missing)} postings in this filter.")

st.write("")
st.caption("Salary figures reflect only the ~23% of postings that disclose pay.")
