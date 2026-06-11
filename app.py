from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from src.analytics import (
    aggregate_by_period,
    apply_filters,
    calculate_metrics,
    exclude_commodities,
    normalize_shipments,
    top_commodities,
)
from src.database import load_export_data


st.set_page_config(
    page_title="China Export Monitor",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --accent: #165DFF; --ink: #111827; --line: #D7DEE8; }
    .block-container { padding-top: 2rem; max-width: 1500px; }
    h1, h2, h3 { color: var(--ink); letter-spacing: -0.03em; }
    [data-testid="stMetric"] {
        border-top: 3px solid var(--accent);
        border-bottom: 1px solid var(--line);
        padding: 0.85rem 0.25rem;
    }
    [data-testid="stSidebar"] { border-right: 1px solid var(--line); }
    div[data-testid="stDataFrame"] { border: 1px solid var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner="正在读取数据库数据...")
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
        margin=dict(l=12, r=12, t=34, b=12),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#111827"),
        legend_title_text="",
        hovermode="x unified",
    )
    figure.update_xaxes(showgrid=False, linecolor="#D7DEE8")
    figure.update_yaxes(gridcolor="#E8EDF4", zeroline=False)
    return figure


st.title("中国出口商品装运量")
st.caption(
    "固定范围：装货国家为 China，卸货国家不为 China。总装运量始终跟随当前商品筛选；Top 10 仅用于排名比较。"
)

with st.sidebar:
    st.header("筛选")
    default_end = date.today()
    default_start = default_end - timedelta(days=365)
    selected_dates = st.date_input(
        "日期范围",
        value=(default_start, default_end),
        max_value=default_end,
    )
    grain = st.segmented_control(
        "时间粒度",
        options=["Daily", "Weekly", "Monthly"],
        default="Monthly",
        selection_mode="single",
    )

if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
    st.info("请选择开始日期和结束日期。")
    st.stop()

start_date, end_date = selected_dates

try:
    source = normalize_shipments(get_source_data(start_date, end_date))
except (KeyError, StreamlitSecretNotFoundError):
    st.error(
        "尚未配置数据库连接。请在 `.streamlit/secrets.toml` 或 Streamlit Cloud Secrets 中添加 `[mysql]` 配置。"
    )
    st.stop()
except Exception as exc:
    st.error(f"数据库读取失败：{exc}")
    st.stop()

with st.sidebar:
    commodities = st.multiselect(
        "商品",
        options=sorted(source["COMMODITY"].unique()),
        placeholder="默认全部商品，可搜索多选",
    )
    destinations = st.multiselect(
        "目的地国家",
        options=sorted(source["discharge_country"].unique()),
        placeholder="默认全部非中国国家",
    )
    if st.button("刷新数据库缓存", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

filtered = apply_filters(
    source,
    start_date=start_date,
    end_date=end_date,
    commodities=commodities,
    destinations=destinations,
)

if filtered.empty:
    st.warning("当前筛选范围没有数据，请调整日期、商品或目的地国家。")
    st.stop()

scope_label = "全部商品" if not commodities else "、".join(commodities[:3])
if len(commodities) > 3:
    scope_label += f" 等 {len(commodities)} 个商品"
st.info(f"当前总装运量口径：{scope_label}")

metrics = calculate_metrics(filtered, grain)
metric_columns = st.columns(4)
metric_columns[0].metric("筛选范围总装运量", format_volume(metrics["total_volume"]))
change = metrics["period_change_pct"]
metric_columns[1].metric(
    "最新周期环比",
    "暂无对比" if change is None else f"{change:+.1f}%",
)
metric_columns[2].metric("筛选范围商品数", f"{metrics['commodity_count']:,}")
metric_columns[3].metric("装运量最大商品", metrics["largest_commodity"] or "暂无")

st.subheader("筛选范围装运量趋势")
trend = aggregate_by_period(filtered, grain)
trend_chart = px.area(
    trend,
    x="period",
    y="voy_intake_mt",
    labels={"period": "日期", "voy_intake_mt": "装运量 (mt)"},
    color_discrete_sequence=["#165DFF"],
)
trend_chart.update_traces(line_width=2.5, fillcolor="rgba(22,93,255,0.14)")
st.plotly_chart(apply_chart_style(trend_chart), use_container_width=True)

left, right = st.columns(2)
ranked = top_commodities(
    apply_filters(source, start_date, end_date, destinations=destinations),
    limit=10,
)
with left:
    st.subheader("Top 10 出口商品")
    ranking_chart = px.bar(
        ranked.sort_values("voy_intake_mt"),
        x="voy_intake_mt",
        y="COMMODITY",
        orientation="h",
        labels={"COMMODITY": "商品", "voy_intake_mt": "装运量 (mt)"},
        color_discrete_sequence=["#165DFF"],
    )
    ranking_chart.update_layout(hovermode="closest")
    st.plotly_chart(apply_chart_style(ranking_chart), use_container_width=True)

with right:
    st.subheader("Top 10 商品趋势对比（不含 AGGREGATES）")
    top_names = ranked["COMMODITY"].tolist()
    top_rows = apply_filters(
        source,
        start_date,
        end_date,
        commodities=top_names,
        destinations=destinations,
    )
    top_rows = exclude_commodities(top_rows, ["AGGREGATES"])
    comparison = aggregate_by_period(top_rows, grain, group_columns=["COMMODITY"])
    comparison_chart = px.line(
        comparison,
        x="period",
        y="voy_intake_mt",
        color="COMMODITY",
        labels={"period": "日期", "voy_intake_mt": "装运量 (mt)", "COMMODITY": "商品"},
    )
    comparison_chart.update_traces(line_width=2.2)
    st.plotly_chart(apply_chart_style(comparison_chart), use_container_width=True)

st.subheader("筛选结果明细")
st.caption("仅用于核对数据，不提供下载。为保证页面性能，最多显示最新 1,000 行。")
detail = filtered.sort_values("load_start_date", ascending=False).head(1000).copy()
detail["load_start_date"] = detail["load_start_date"].dt.date
st.dataframe(
    detail,
    use_container_width=True,
    hide_index=True,
    column_config={
        "load_start_date": "装货开始日期",
        "COMMODITY": "商品",
        "discharge_country": "目的地国家",
        "voy_intake_mt": st.column_config.NumberColumn("装运量 (mt)", format="%.0f"),
    },
)
