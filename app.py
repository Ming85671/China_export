from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from src.analytics import (
    aggregate_by_period,
    apply_filters,
    calculate_metrics,
    nice_axis_tick_step,
    nice_axis_upper_bound,
    normalize_shipments,
    prepare_weekly_average_comparison,
    top_commodities,
    weekly_historical_stats,
)
from src.database import load_export_data


CHART_COLORS = ["#2563EB", "#D97706", "#0F766E", "#7C3AED", "#BE123C", "#0369A1"]


st.set_page_config(
    page_title="China Export Monitor",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --color-primary: #1E40AF;
        --color-secondary: #2563EB;
        --color-accent: #D97706;
        --color-background: #F4F7FB;
        --color-surface: #FFFFFF;
        --color-ink: #0F172A;
        --color-muted: #64748B;
        --color-border: #DCE5F2;
        --shadow-card: 0 10px 30px rgba(30, 64, 175, 0.06);
        --radius-card: 16px;
    }

    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--color-ink);
    }
    .stApp { background: var(--color-background); }
    .block-container {
        max-width: 1480px;
        padding-top: 1.75rem;
        padding-bottom: 4rem;
    }
    h1, h2, h3 {
        color: var(--color-ink);
        letter-spacing: -0.035em;
    }

    .dashboard-hero {
        position: relative;
        overflow: hidden;
        padding: 2rem 2.25rem;
        margin-bottom: 1.25rem;
        border: 1px solid rgba(30, 64, 175, 0.15);
        border-radius: 20px;
        background:
            radial-gradient(circle at 90% 15%, rgba(59, 130, 246, 0.18), transparent 30%),
            linear-gradient(135deg, #FFFFFF 0%, #F0F6FF 100%);
        box-shadow: var(--shadow-card);
    }
    .dashboard-hero::after {
        content: "";
        position: absolute;
        right: -42px;
        bottom: -78px;
        width: 230px;
        height: 230px;
        border: 32px solid rgba(30, 64, 175, 0.05);
        border-radius: 50%;
    }
    .dashboard-eyebrow,
    .section-kicker {
        color: var(--color-primary);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.13em;
        line-height: 1.2;
        text-transform: uppercase;
    }
    .dashboard-hero h1 {
        position: relative;
        z-index: 1;
        max-width: 850px;
        margin: 0.55rem 0 0.65rem;
        font-size: clamp(2rem, 4vw, 3.2rem);
        line-height: 1.05;
    }
    .dashboard-hero p {
        position: relative;
        z-index: 1;
        max-width: 780px;
        margin: 0;
        color: #475569;
        font-size: 0.98rem;
        line-height: 1.65;
    }
    .dashboard-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        margin-top: 1.15rem;
        padding: 0.42rem 0.72rem;
        border: 1px solid #BFDBFE;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.82);
        color: #1E3A8A;
        font-size: 0.76rem;
        font-weight: 650;
    }
    .dashboard-badge::before {
        content: "";
        width: 0.46rem;
        height: 0.46rem;
        border-radius: 50%;
        background: #2563EB;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
    }
    .section-heading {
        margin: 2rem 0 0.65rem;
    }
    .section-heading h2 {
        margin: 0.3rem 0 0;
        font-size: 1.35rem;
        line-height: 1.25;
    }

    [data-testid="stMetric"] {
        min-height: 132px;
        padding: 1.15rem 1.2rem;
        border: 1px solid var(--color-border);
        border-radius: var(--radius-card);
        background: var(--color-surface);
        box-shadow: var(--shadow-card);
        transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #BFDBFE;
        box-shadow: 0 14px 32px rgba(30, 64, 175, 0.1);
    }
    [data-testid="stMetricLabel"] {
        color: var(--color-muted);
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    [data-testid="stMetricValue"] {
        color: var(--color-ink);
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
        font-size: clamp(1.45rem, 2vw, 2rem);
        font-weight: 700;
        letter-spacing: -0.04em;
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid var(--color-border);
        background: #FFFFFF;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem;
    }
    [data-testid="stSidebar"] h2 {
        margin-bottom: 0;
        color: var(--color-ink);
        font-size: 1.25rem;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p {
        color: #475569;
        font-weight: 600;
    }
    [data-baseweb="input"],
    [data-baseweb="select"] > div {
        border-color: var(--color-border) !important;
        border-radius: 10px !important;
        background: #F8FAFC !important;
    }
    [data-baseweb="input"]:focus-within,
    [data-baseweb="select"] > div:focus-within {
        border-color: var(--color-secondary) !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.13) !important;
    }
    [data-testid="stBaseButton-secondary"] {
        min-height: 44px;
        border: 1px solid #BFDBFE;
        border-radius: 10px;
        background: #EFF6FF;
        color: var(--color-primary);
        font-weight: 700;
        transition: background 180ms ease, border-color 180ms ease;
    }
    [data-testid="stBaseButton-secondary"]:hover {
        border-color: var(--color-secondary);
        background: #DBEAFE;
        color: #1E3A8A;
    }
    [data-testid="stSegmentedControl"] {
        padding: 0.22rem;
        border: 1px solid var(--color-border);
        border-radius: 12px;
        background: #F1F5F9;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
        border: 1px solid #BFDBFE;
        background: #EFF6FF;
    }
    [data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"] {
        padding: 0.65rem;
        border: 1px solid var(--color-border);
        border-radius: var(--radius-card);
        background: var(--color-surface);
        box-shadow: var(--shadow-card);
    }
    div[data-testid="stDataFrame"] {
        padding: 0.35rem;
        overflow: hidden;
    }
    [data-testid="stCaptionContainer"] {
        color: var(--color-muted);
    }
    button:focus-visible,
    input:focus-visible {
        outline: 3px solid rgba(37, 99, 235, 0.35) !important;
        outline-offset: 2px;
    }

    @media (max-width: 768px) {
        .block-container {
            padding: 1rem 0.85rem 3rem;
        }
        .dashboard-hero {
            padding: 1.5rem 1.25rem;
            border-radius: 16px;
        }
        .dashboard-hero h1 {
            font-size: 2rem;
        }
        [data-testid="stMetric"] {
            min-height: 112px;
        }
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            scroll-behavior: auto !important;
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner="Loading database data...")
def get_source_data(start_date: date, end_date: date) -> pd.DataFrame:
    return load_export_data(st.secrets["mysql"], start_date, end_date)


def format_volume(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M mt"
    if abs(value) >= 1_000:
        return f"{value / 1_000:,.1f}K mt"
    return f"{value:,.0f} mt"


def apply_chart_style(figure, height: int = 390):
    figure.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=30, b=18),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#475569", family="Inter, Arial, sans-serif", size=12),
        legend_title_text="",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#0F172A",
            bordercolor="#0F172A",
            font=dict(color="#FFFFFF", family="Inter, Arial, sans-serif"),
        ),
        separators=".,",
    )
    figure.update_xaxes(
        showgrid=False,
        linecolor="#DCE5F2",
        tickfont=dict(color="#64748B"),
        title_font=dict(color="#475569"),
    )
    figure.update_yaxes(
        gridcolor="#E8EEF7",
        linecolor="#DCE5F2",
        zeroline=False,
        tickfont=dict(color="#64748B"),
        title_font=dict(color="#475569"),
        tickformat="~s",
    )
    return figure


def apply_trend_chart_style(figure, trend: pd.DataFrame):
    figure = apply_chart_style(figure)
    figure.update_layout(
        legend=dict(
            orientation="h",
            x=1,
            xanchor="right",
            y=1.02,
            yanchor="bottom",
        ),
    )
    if not trend.empty:
        max_volume = trend["voy_intake_mt"].max()
        min_volume = trend["voy_intake_mt"].min()
        y_axis_upper_bound = nice_axis_upper_bound(max_volume)
        y_axis_tick_step = nice_axis_tick_step(y_axis_upper_bound)
        y_axis_lower_bound = (min_volume // y_axis_tick_step) * y_axis_tick_step
        figure.update_yaxes(
            range=[y_axis_lower_bound, y_axis_upper_bound],
            tickmode="linear",
            tick0=0,
            dtick=nice_axis_tick_step(y_axis_upper_bound),
        )
        figure.add_hline(
            y=y_axis_upper_bound,
            line_color="#E8EEF7",
            line_width=1,
            layer="below",
        )
    return figure


def make_weekly_average_range_chart(weekly: pd.DataFrame, comparison_year: int):
    """Show the comparison year against prior years and historical bands."""
    if weekly.empty:
        return None

    current = weekly[weekly["year"] == comparison_year]
    if current.empty:
        return None

    history_stats = weekly_historical_stats(weekly, comparison_year)
    figure = go.Figure()
    if not history_stats.empty:
        figure.add_trace(
            go.Scatter(
                x=history_stats["x_date"],
                y=history_stats["min"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=history_stats["x_date"],
                y=history_stats["max"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(37,99,235,0.09)",
                name="Historical min-max",
                customdata=history_stats[["min", "max"]],
                hovertemplate="Min-max: %{customdata[0]:,.0f} - %{customdata[1]:,.0f} mt/day<extra></extra>",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=history_stats["x_date"],
                y=history_stats["q25"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=history_stats["x_date"],
                y=history_stats["q75"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(37,99,235,0.18)",
                name="Historical 25%-75%",
                customdata=history_stats[["q25", "q75"]],
                hovertemplate="25%-75%: %{customdata[0]:,.0f} - %{customdata[1]:,.0f} mt/day<extra></extra>",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=history_stats["x_date"],
                y=history_stats["median"],
                mode="lines",
                line=dict(color="#0F172A", width=2),
                name="Historical median",
                hovertemplate="Median: %{y:,.0f} mt/day<extra></extra>",
            )
        )

    past_years = sorted(
        weekly.loc[weekly["year"] < comparison_year, "year"].unique()
    )
    for index, year in enumerate(past_years):
        year_data = weekly[weekly["year"] == year]
        figure.add_trace(
            go.Scatter(
                x=year_data["x_date"],
                y=year_data["daily_average_mt"],
                mode="lines",
                line=dict(
                    color=CHART_COLORS[(index + 1) % len(CHART_COLORS)],
                    width=1.3,
                    dash="dot" if year == comparison_year - 1 else "solid",
                ),
                opacity=0.7,
                name=str(year),
                hovertemplate=f"{year}: " + "%{y:,.0f} mt/day<extra></extra>",
            )
        )

    figure.add_trace(
        go.Scatter(
            x=current["x_date"],
            y=current["daily_average_mt"],
            mode="lines+markers",
            line=dict(color=CHART_COLORS[0], width=3),
            marker=dict(color=CHART_COLORS[0], size=6),
            name=str(comparison_year),
            hovertemplate=f"{comparison_year}: " + "%{y:,.0f} mt/day<extra></extra>",
        )
    )
    figure.update_layout(
        legend=dict(orientation="h", x=1, xanchor="right", y=1.02, yanchor="bottom"),
    )
    figure.update_xaxes(tickformat="%b", hoverformat="%b %d")
    figure.update_yaxes(title="Weekly Average Volume (mt/day)")
    return apply_chart_style(figure, height=440)


def make_weekly_average_bar_chart(weekly: pd.DataFrame, comparison_year: int):
    """Show current-year weekly daily averages with a four-week average."""
    current = weekly[weekly["year"] == comparison_year]
    if current.empty:
        return None

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=current["x_date"],
            y=current["daily_average_mt"],
            marker_color="#93C5FD",
            name="Weekly daily average",
            hovertemplate="Weekly daily average: %{y:,.0f} mt/day<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=current["x_date"],
            y=current["four_week_average_mt"],
            mode="lines+markers",
            line=dict(color="#0F172A", width=2.2, dash="dot"),
            marker=dict(color="#0F172A", size=5),
            name="4-week average",
            hovertemplate="4-week average: %{y:,.0f} mt/day<extra></extra>",
        )
    )
    figure.update_layout(
        bargap=0.22,
        legend=dict(orientation="h", x=1, xanchor="right", y=1.02, yanchor="bottom"),
    )
    figure.update_xaxes(tickformat="%b", hoverformat="%b %d")
    figure.update_yaxes(title="Weekly Average Volume (mt/day)")
    return apply_chart_style(figure, height=440)


def render_section_header(kicker: str, title: str) -> None:
    st.markdown(
        f"""
        <div class="section-heading">
            <div class="section-kicker">{kicker}</div>
            <h2>{title}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="dashboard-hero">
        <div class="dashboard-eyebrow">China Export Monitor</div>
        <h1>China Export Commodity Shipments</h1>
        <p>
            Track shipment volume loaded in China and discharged worldwide.
            Explore commodity trends, compare leading exports, and inspect the underlying shipment records.
        </p>
        <div class="dashboard-badge">Live database scope · China outbound cargoes</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Filters")
    st.caption("Refine the date range, reporting grain, commodity, and destination.")
    default_end = date.today()
    default_start = default_end - timedelta(days=365)
    selected_dates = st.date_input(
        "Date range",
        value=(default_start, default_end),
        max_value=default_end,
    )
    grain = st.segmented_control(
        "Time grain",
        options=["Daily", "Weekly", "Monthly"],
        default="Monthly",
        selection_mode="single",
    )

if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
    st.info("Please select both a start date and an end date.")
    st.stop()

start_date, end_date = selected_dates

try:
    source = normalize_shipments(get_source_data(start_date, end_date))
except (KeyError, StreamlitSecretNotFoundError):
    st.error(
        "The database connection is not configured. Add the `[mysql]` configuration "
        "to `.streamlit/secrets.toml` or Streamlit Community Cloud Secrets."
    )
    st.stop()
except Exception as exc:
    st.error(f"Failed to load data from the database: {exc}")
    st.stop()

with st.sidebar:
    commodities = st.multiselect(
        "Commodity",
        options=sorted(source["COMMODITY"].unique()),
        placeholder="All commodities by default; search to select multiple",
    )
    destinations = st.multiselect(
        "Destination country",
        options=sorted(source["discharge_country"].unique()),
        placeholder="All destinations outside China by default",
    )
    if st.button("Refresh database cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

comparison_year = end_date.year
comparison_source_start = date(comparison_year - 5, 1, 1)
try:
    comparison_source = normalize_shipments(
        get_source_data(comparison_source_start, end_date)
    )
except Exception as exc:
    st.error(f"Failed to load weekly comparison data from the database: {exc}")
    st.stop()

filtered = apply_filters(
    source,
    start_date=start_date,
    end_date=end_date,
    commodities=commodities,
    destinations=destinations,
)

if filtered.empty:
    st.warning("No data is available for the current filters. Adjust the date range, commodity, or destination country.")
    st.stop()

scope_label = "All commodities" if not commodities else ", ".join(commodities[:3])
if len(commodities) > 3:
    scope_label += f", among {len(commodities)} selected commodities"
st.info(f"Current total shipment volume scope: {scope_label}")

metrics = calculate_metrics(filtered, grain)
metric_columns = st.columns(4)
metric_columns[0].metric("Total Shipment Volume", format_volume(metrics["total_volume"]))
change = metrics["period_change_pct"]
metric_columns[1].metric(
    "Latest Period Change",
    "No comparison" if change is None else f"{change:+.1f}%",
)
metric_columns[2].metric("Commodity Count", f"{metrics['commodity_count']:,}")
metric_columns[3].metric("Largest Commodity by Volume", metrics["largest_commodity"] or "N/A")

render_section_header("Trend analysis", "Shipment Volume Trend")
if commodities:
    trend = aggregate_by_period(filtered, grain, group_columns=["COMMODITY"])
    trend_chart = px.line(
        trend,
        x="period",
        y="voy_intake_mt",
        color="COMMODITY",
        labels={
            "period": "Date",
            "voy_intake_mt": "Shipment Volume (mt)",
            "COMMODITY": "Commodity",
        },
        color_discrete_sequence=CHART_COLORS,
    )
    trend_chart.update_traces(
        line_width=2.8,
        hovertemplate="%{y:,.0f} mt<extra>%{fullData.name}</extra>",
    )
else:
    trend = aggregate_by_period(filtered, grain)
    trend_chart = px.area(
        trend,
        x="period",
        y="voy_intake_mt",
        labels={"period": "Date", "voy_intake_mt": "Shipment Volume (mt)"},
        color_discrete_sequence=[CHART_COLORS[0]],
    )
    trend_chart.update_traces(
        line_width=2.8,
        fillcolor="rgba(37,99,235,0.12)",
        hovertemplate="%{y:,.0f} mt<extra></extra>",
    )
st.plotly_chart(apply_trend_chart_style(trend_chart, trend), use_container_width=True)

ranked = top_commodities(
    apply_filters(source, start_date, end_date, destinations=destinations),
    limit=10,
)
render_section_header("Ranked comparison", "Top 10 Export Commodities")
ranking_chart = px.bar(
    ranked.sort_values("voy_intake_mt"),
    x="voy_intake_mt",
    y="COMMODITY",
    orientation="h",
    labels={"COMMODITY": "Commodity", "voy_intake_mt": "Shipment Volume (mt)"},
    color_discrete_sequence=["#2563EB"],
)
ranking_chart.update_traces(
    marker_line_width=0,
    hovertemplate="%{y}<br>%{x:,.0f} mt<extra></extra>",
)
ranking_chart.update_layout(hovermode="closest", bargap=0.3)
st.plotly_chart(apply_chart_style(ranking_chart), use_container_width=True)

render_section_header("Data inspection", "Filtered Shipment Details")
st.caption("For data verification only; downloads are not available. The latest 1,000 rows are displayed for performance.")
detail = filtered.sort_values("load_start_date", ascending=False).head(1000).copy()
detail["load_start_date"] = detail["load_start_date"].dt.date
st.dataframe(
    detail,
    use_container_width=True,
    hide_index=True,
    column_config={
        "load_start_date": "Load Start Date",
        "COMMODITY": "Commodity",
        "discharge_country": "Destination Country",
        "voy_intake_mt": st.column_config.NumberColumn("Shipment Volume (mt)", format="%.0f"),
    },
)

comparison_filtered = apply_filters(
    comparison_source,
    start_date=comparison_source_start,
    end_date=end_date,
    commodities=commodities,
    destinations=destinations,
)
weekly_comparison = prepare_weekly_average_comparison(
    comparison_filtered,
    start_date=start_date,
    end_date=end_date,
)

render_section_header("Historical context", "Weekly Average Comparison")
st.caption(
    "Weekly totals are divided by seven and compared across the selected year "
    "and the previous five years. The current incomplete week is excluded."
)
range_chart = make_weekly_average_range_chart(weekly_comparison, comparison_year)
if range_chart is None:
    st.info("Not enough data is available to generate the historical weekly comparison.")
else:
    st.plotly_chart(
        range_chart,
        use_container_width=True,
        key="weekly-average-range",
    )

bar_chart = make_weekly_average_bar_chart(weekly_comparison, comparison_year)
if bar_chart is None:
    st.info("Not enough current-year data is available to generate the weekly average chart.")
else:
    st.plotly_chart(
        bar_chart,
        use_container_width=True,
        key="weekly-average-bar",
    )
