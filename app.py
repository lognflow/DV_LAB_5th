"""
Global Deforestation Analysis Dashboard (1990–2025)
Interactive, research-based Streamlit dashboard built with authentic, verified datasets
from FAO FRA, Global Forest Watch (Curtis et al.), Pendrill et al., Global Carbon Project, and IUCN.
"""

import os
import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure Streamlit page
st.set_page_config(
    page_title="Global Deforestation Analysis Dashboard (1990–2025)",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Append project directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.utils import (
    load_processed_data,
    load_world_geodata,
    compute_dynamic_kpis,
    format_area_value,
    convert_area,
    CAUSE_METADATA,
    CONTINENT_COLORS,
    DRIVER_COLORS,
    THEME,
    PLOTLY_LAYOUT
)
from src.charts import (
    _apply_layout,
    _empty_figure,
    create_world_choropleth,
    create_cause_world_choropleth,
    create_geopandas_country_zoom_map,
    create_global_trend_chart,
    create_gain_vs_loss_chart,
    create_drivers_pie_chart,
    create_drivers_stacked_bar,
    create_commodity_breakdown_chart,
    create_cause_top_countries_bar,
    create_cause_trajectory_by_continent,
    create_cause_share_comparison,
    create_top_countries_bar,
    create_regional_comparison_chart,
    create_country_deep_dive_chart,
    create_country_comparison_lines,
    create_country_cause_radar,
    create_country_heatmap,
    create_forest_vs_emissions_scatter,
    create_country_treemap,
    create_slope_dumbbell_chart,
    create_environmental_impact_chart
)

# Load custom CSS
css_path = os.path.join(BASE_DIR, "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_data
def get_dashboard_data():
    return load_processed_data()


@st.cache_resource
def get_geodata():
    return load_world_geodata()


data = get_dashboard_data()
gdf_world = get_geodata()

df_panel = data["country_panel"]
df_global = data["global_summary"]
df_reg = data["regional"]
df_drivers = data["drivers"]
df_comm = data["commodities"]
df_hotspots = data["hotspots"]
metadata = data["metadata"]

# ==============================================================================
# SIDEBAR: REACTIVE ANALYTICAL CONTROLS
# ==============================================================================
st.sidebar.markdown(
    """
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #e2e8f0;">
        <span style="font-size: 26px;">🌲</span>
        <div>
            <div style="font-size: 17px; font-weight: 800; color: #1b4332; line-height: 1.1;">Forest Intelligence</div>
            <div style="font-size: 11px; color: #64748b; font-weight: 600;">Empirical Analytics 1990–2025</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown("### 🌍 Geographic Scope")
all_continents = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"]
selected_continents = st.sidebar.multiselect(
    "Filter Continents",
    options=all_continents,
    default=all_continents,
    help="Filter all country rankings, maps, and regional totals."
)
if not selected_continents:
    selected_continents = all_continents

filtered_panel = df_panel[df_panel["Continent"].isin(selected_continents)].copy()
available_countries = sorted(filtered_panel["Entity"].unique().tolist())

focus_country = st.sidebar.selectbox(
    "Focus Country (Global or Single Nation)",
    options=["All Countries"] + available_countries,
    index=0,
    help="Select a specific country to inspect its metrics across Overview, Maps, and Country Analytics."
)

# Keep Tab 2 Country Selector synchronized when sidebar Focus Country changes
if "country_tab_primary" not in st.session_state:
    st.session_state["country_tab_primary"] = "Brazil" if "Brazil" in available_countries else available_countries[0]
if "prev_focus_country" not in st.session_state:
    st.session_state["prev_focus_country"] = focus_country
elif st.session_state["prev_focus_country"] != focus_country:
    st.session_state["prev_focus_country"] = focus_country
    if focus_country != "All Countries":
        st.session_state["country_tab_primary"] = focus_country
if st.session_state["country_tab_primary"] not in available_countries and available_countries:
    st.session_state["country_tab_primary"] = available_countries[0]

st.sidebar.markdown("### 📅 Temporal Horizon")
year_range = st.sidebar.slider(
    "Year Range (Period Trends & Cumulative Loss)",
    min_value=1990,
    max_value=2025,
    value=(1990, 2025),
    step=1
)
start_year, end_year = year_range

if start_year < end_year:
    snapshot_year = st.sidebar.slider(
        "Map & Snapshot Year",
        min_value=start_year,
        max_value=end_year,
        value=min(2020, end_year),
        step=1
    )
else:
    snapshot_year = start_year

st.sidebar.markdown("### 🔍 Deforestation Cause Filter")
cause_options = list(CAUSE_METADATA.keys())
selected_cause = st.sidebar.selectbox(
    "Select Cause (Updates Maps & Cause Graphs)",
    options=cause_options,
    index=0,
    help="Selecting a specific cause dynamically transforms maps, rankings, trajectories, and heatmaps to isolate that driver."
)
active_cause_meta = CAUSE_METADATA[selected_cause]

st.sidebar.markdown("### 📐 Unit Display")
unit_choice = st.sidebar.radio(
    "Measurement Unit",
    options=["Million Hectares (Mha)", "Square Kilometers (km²)", "Hectares (ha)"],
    index=0
)

# Sidebar Scientific Integrity Notice & Download
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 11px; font-size: 0.79rem; color: #1b4332;">
        <strong>🌿 Authentic Data Verification</strong><br>
        All metrics are derived exclusively from FAO FRA (1990–2025), Global Forest Watch / Curtis et al. (2001–2024), Pendrill et al. (2001–2023), Global Carbon Budget, and IUCN Red List.<br>
        <em>Missing data is marked "Data Not Available".</em>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.download_button(
    label="📥 Download Filtered Country Data (CSV)",
    data=filtered_panel[(filtered_panel["Year"] >= start_year) & (filtered_panel["Year"] <= end_year)].to_csv(index=False).encode("utf-8"),
    file_name=f"forest_panel_{start_year}_{end_year}.csv",
    mime="text/csv",
    width="stretch"
)

# Helper to compute dynamic period hotspots based on [start_year, end_year] and selected_continents
@st.cache_data
def compute_period_hotspots(panel_df, drivers_df, comm_df, y0, y1, continents):
    sub = panel_df[panel_df["Continent"].isin(continents)]
    p0 = sub[sub["Year"] == y0][["ISO3", "Entity", "Continent", "Sub_Region", "Forest_Area_ha", "Forest_Share_pct"]].rename(
        columns={"Forest_Area_ha": "Area_Start_ha", "Forest_Share_pct": "Share_Start_pct"}
    )
    p1 = sub[sub["Year"] == y1][["ISO3", "Forest_Area_ha", "Forest_Share_pct"]].rename(
        columns={"Forest_Area_ha": "Area_End_ha", "Forest_Share_pct": "Share_End_pct"}
    )
    res = p0.merge(p1, on="ISO3", how="inner")
    res["Forest_Area_1990_ha"] = res["Area_Start_ha"]
    res["Forest_Area_Latest_ha"] = res["Area_End_ha"]
    res["Net_Change_1990_to_Latest_ha"] = res["Area_End_ha"] - res["Area_Start_ha"]
    res["Net_Change_1990_to_Latest_Mha"] = res["Net_Change_1990_to_Latest_ha"] / 1_000_000.0
    res["Pct_Change_Since_1990"] = np.where(
        res["Area_Start_ha"] > 0,
        (res["Net_Change_1990_to_Latest_ha"] / res["Area_Start_ha"]) * 100.0,
        np.nan
    )
    # Attach dominant driver in overlapping window
    dy0, dy1 = max(y0, 2001), min(y1, 2024)
    d_cols = [c for c in DRIVER_COLORS.keys() if c in drivers_df.columns]
    if dy0 <= dy1:
        d_sub = drivers_df[(drivers_df["Code"].str.len() == 3) & (drivers_df["Year"] >= dy0) & (drivers_df["Year"] <= dy1)]
        d_grp = d_sub.groupby("Code")[d_cols].sum()
        d_valid = d_grp[d_grp.sum(axis=1) > 0]
        dom_drv = d_valid.idxmax(axis=1).reset_index()
        dom_drv.columns = ["ISO3", "Dominant_Driver"]
        res = res.merge(dom_drv, on="ISO3", how="left")
    else:
        res["Dominant_Driver"] = "Data Not Available"
    res["Dominant_Driver"] = res["Dominant_Driver"].fillna("Data Not Available")
    return res.sort_values("Net_Change_1990_to_Latest_ha").reset_index(drop=True)


period_hotspots = compute_period_hotspots(df_panel, df_drivers, df_comm, start_year, end_year, selected_continents)

# ==============================================================================
# HERO BANNER & ACTIVE FILTER RIBBON
# ==============================================================================
st.markdown(
    """
    <div class="main-header">
        <h1>Global Deforestation & Forest Dynamics Intelligence (1990–2025)</h1>
        <p>Interactive country-wise and cause-specific analytics tracking global forest cover loss, regeneration, commodity drivers, carbon emissions, and biodiversity risk from peer-reviewed repositories.</p>
        <div class="header-badges">
            <span class="badge">🌐 UN FAO FRA 2020/2025</span>
            <span class="badge">🛰️ Global Forest Watch (30m Landsat)</span>
            <span class="badge">🌱 Pendrill et al. Commodities</span>
            <span class="badge">💨 Global Carbon Budget</span>
            <span class="badge">🦎 IUCN Red List Index</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

scope_badge = focus_country if focus_country != "All Countries" else ("Global (6 Continents)" if len(selected_continents) == 6 else ", ".join(selected_continents))
st.markdown(
    f"""
    <div class="filter-ribbon">
        <span class="ribbon-item"><strong>Scope:</strong> <span class="ribbon-pill">{scope_badge}</span></span>
        <span class="ribbon-item"><strong>Period:</strong> <span class="ribbon-pill">{start_year}–{end_year}</span></span>
        <span class="ribbon-item"><strong>Snapshot Year:</strong> <span class="ribbon-pill">{snapshot_year}</span></span>
        <span class="ribbon-item"><strong>Active Cause:</strong> <span class="ribbon-pill cause">{selected_cause}</span></span>
        <span class="ribbon-item"><strong>Unit:</strong> <span class="ribbon-pill">{unit_choice.split('(')[1].replace(')', '')}</span></span>
    </div>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# EXECUTIVE 8-TAB NAVIGATION
# ==============================================================================
tabs = st.tabs([
    "1. 🌐 Overview & KPIs",
    "2. 🏳️ Country-Wise Analytics",
    "3. 🗺️ Interactive World Map",
    "4. 🔍 Cause-Driven Analytics",
    "5. 🔥 Hotspots & Rankings",
    "6. 📈 Historical & Recovery",
    "7. 🌍 Regional & Environmental",
    "8. 📊 Data Explorer & Audit"
])

# ------------------------------------------------------------------------------
# TAB 1: GLOBAL / SCOPED OVERVIEW & KPIs
# ------------------------------------------------------------------------------
with tabs[0]:
    kpis = compute_dynamic_kpis(
        df_panel, df_drivers, df_comm,
        start_year, end_year, selected_continents,
        country_name=focus_country,
        selected_cause=selected_cause
    )

    st.markdown(f"### 📊 Key Forest Metrics — **{kpis['scope_label']}** ({start_year}–{end_year})")

    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        val_str = format_area_value(kpis["area_end_ha"], unit_choice, signed=False, decimals=2)
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Forest Area ({end_year})</div>
                <div class="kpi-value">{val_str}</div>
                <div class="kpi-subtext">FAO FRA National Inventory</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with kpi_cols[1]:
        net_ha = kpis["net_change_period_ha"]
        net_str = format_area_value(net_ha, unit_choice, signed=True, decimals=2)
        pct_str = f"{kpis['pct_change_period']:+.1f}%" if pd.notna(kpis["pct_change_period"]) else "N/A"
        cls_card = "loss-card" if (pd.notna(net_ha) and net_ha < 0) else "gain-card"
        cls_val = "loss" if (pd.notna(net_ha) and net_ha < 0) else "gain"
        st.markdown(
            f"""
            <div class="kpi-card {cls_card}">
                <div class="kpi-label">Net Change ({start_year}–{end_year})</div>
                <div class="kpi-value {cls_val}">{net_str}</div>
                <div class="kpi-subtext">{pct_str} relative shift</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with kpi_cols[2]:
        share_str = f"{kpis['forest_share_end_pct']:.1f}%" if pd.notna(kpis["forest_share_end_pct"]) else "Data Not Available"
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Forest Cover Share ({end_year})</div>
                <div class="kpi-value">{share_str}</div>
                <div class="kpi-subtext">Area-weighted % of land area</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with kpi_cols[3]:
        if pd.notna(kpis["gross_loss_ha"]):
            g_loss = format_area_value(-abs(kpis["gross_loss_ha"]), unit_choice, signed=True, decimals=2)
            g_gain = format_area_value(abs(kpis["gross_gain_ha"]), unit_choice, signed=True, decimals=2) if pd.notna(kpis["gross_gain_ha"]) else "N/A"
            g_sub = f"Recovery: {g_gain}/yr ({kpis['gross_reported_year']})"
            g_cls = "loss"
        else:
            g_loss = format_area_value(kpis["annual_rate_end_ha"], unit_choice, signed=True, decimals=2)
            g_sub = f"Net Annual Rate ({end_year})"
            g_cls = "loss" if (pd.notna(kpis["annual_rate_end_ha"]) and kpis["annual_rate_end_ha"] < 0) else "gain"
        st.markdown(
            f"""
            <div class="kpi-card loss-card">
                <div class="kpi-label">Gross Deforestation Rate</div>
                <div class="kpi-value {g_cls}">{g_loss}</div>
                <div class="kpi-subtext">{g_sub}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with kpi_cols[4]:
        c_loss_str = format_area_value(kpis["cause_loss_ha"], unit_choice, signed=False, decimals=2)
        c_yrs = f"{kpis['cause_years'][0]}–{kpis['cause_years'][1]}" if kpis["cause_years"] else "Outside Driver Range"
        c_share = f"({kpis['cause_share_pct']:.1f}% of loss)" if (pd.notna(kpis["cause_share_pct"]) and selected_cause != "All Causes") else ""
        st.markdown(
            f"""
            <div class="kpi-card cause-card">
                <div class="kpi-label">{selected_cause}</div>
                <div class="kpi-value">{c_loss_str}</div>
                <div class="kpi-subtext">Satellite loss {c_yrs} {c_share}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    ov_col1, ov_col2 = st.columns([3, 2])
    with ov_col1:
        if focus_country != "All Countries" and kpis["iso3"]:
            st.plotly_chart(create_country_deep_dive_chart(df_panel, iso3=kpis["iso3"], start_year=start_year, end_year=end_year), width="stretch", key="tab1_country_trend")
        else:
            # Aggregate strictly across selected continents for exact accuracy
            agg_df = filtered_panel.groupby("Year").agg({
                "Forest_Area_ha": "sum",
                "Annual_Change_ha": "sum",
                "CO2_Emissions_tonnes": "sum"
            }).reset_index()
            agg_df["Forest_Area_Mha"] = agg_df["Forest_Area_ha"] / 1_000_000.0
            agg_df["Annual_Change_Mha"] = agg_df["Annual_Change_ha"] / 1_000_000.0
            st.plotly_chart(create_global_trend_chart(agg_df, start_year=start_year, end_year=end_year, title_prefix=scope_badge), width="stretch", key="tab1_global_trend")

    with ov_col2:
        if selected_cause != "All Causes":
            # Different graph immediately when cause is changed!
            c_df = df_drivers if active_cause_meta["dataset"] == "drivers" else df_comm
            cy0 = max(start_year, active_cause_meta["years"][0])
            cy1 = min(end_year, active_cause_meta["years"][1])
            if cy0 <= cy1:
                c_scoped = c_df[c_df["Entity"] == focus_country] if focus_country != "All Countries" else c_df[c_df["Continent"].isin(selected_continents)]
                st.plotly_chart(
                    create_cause_top_countries_bar(
                        c_scoped,
                        active_cause_meta["column"],
                        active_cause_meta["label"],
                        year_range=(cy0, cy1),
                        top_n=10,
                        cause_color=active_cause_meta["color"]
                    ),
                    width="stretch",
                    key="tab1_cause_top"
                )
            else:
                st.info(f"Driver data is available for {active_cause_meta['years'][0]}–{active_cause_meta['years'][1]}.")
        else:
            if focus_country != "All Countries" and kpis["iso3"]:
                st.plotly_chart(create_drivers_pie_chart(df_drivers, entity=focus_country, year_range=(max(start_year, 2001), min(end_year, 2024))), width="stretch", key="tab1_country_pie")
            elif len(selected_continents) == 6:
                st.plotly_chart(create_gain_vs_loss_chart(df_global, entity_label="Global"), width="stretch", key="tab1_global_gain_loss")
            else:
                st.plotly_chart(create_top_countries_bar(period_hotspots, top_n=10, ascending=True), width="stretch", key="tab1_cont_top_loss")

    # Hierarchical Treemap in Overview
    st.markdown("#### 🌳 Hierarchical Contribution: Forest Loss, Expansion & Remaining Stock")
    treemap_mode = st.radio(
        "Treemap View",
        options=["Cumulative Forest Loss", "Net Forest Expansion (Gainers)", "Current Forest Stock"],
        horizontal=True,
        label_visibility="collapsed"
    )
    t_map_arg = "loss" if "Loss" in treemap_mode else ("gain" if "Expansion" in treemap_mode else "stock")
    st.plotly_chart(create_country_treemap(period_hotspots, mode=t_map_arg), width="stretch", key="tab1_treemap")

# ------------------------------------------------------------------------------
# TAB 2: COUNTRY-WISE ANALYTICS (DEDICATED COUNTRY VISUALIZATION CENTERPIECE)
# ------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("### 🏳️ Country-Wise Data Visualization & Comparative Laboratory")

    c_ctrl1, c_ctrl2 = st.columns([1, 2])
    with c_ctrl1:
        selected_country_tab = st.selectbox(
            "Select Primary Country for Deep-Dive",
            options=available_countries,
            key="country_tab_primary"
        )
    with c_ctrl2:
        default_compare = [c for c in ["Brazil", "Indonesia", "Democratic Republic of Congo", "China", "Canada"] if c in available_countries]
        if selected_country_tab not in default_compare and selected_country_tab in available_countries:
            default_compare = [selected_country_tab] + default_compare[:4]
        compare_countries = st.multiselect(
            "Select Countries for Side-by-Side Comparison (2–6 recommended)",
            options=available_countries,
            default=default_compare,
            max_selections=6
        )

    c_panel_sub = filtered_panel[(filtered_panel["Entity"] == selected_country_tab) & (filtered_panel["Year"] >= start_year) & (filtered_panel["Year"] <= end_year)].sort_values("Year")
    if not c_panel_sub.empty:
        c_iso = c_panel_sub["ISO3"].iloc[0]
        c_cont = c_panel_sub["Continent"].iloc[0]
        c_subreg = c_panel_sub["Sub_Region"].iloc[0]
        c_hot_row = df_hotspots[df_hotspots["ISO3"] == c_iso]
        c_status = c_hot_row["Hotspot_Status"].iloc[0] if not c_hot_row.empty else "Not Classified"
        c_dom_drv = c_hot_row["Dominant_Driver"].iloc[0] if not c_hot_row.empty else "Data Not Available"
        c_dom_comm = c_hot_row["Dominant_Commodity"].iloc[0] if not c_hot_row.empty else "Data Not Available"

        c_kpis = compute_dynamic_kpis(
            df_panel, df_drivers, df_comm,
            start_year, end_year, selected_continents,
            country_name=selected_country_tab,
            selected_cause=selected_cause
        )

        # Country Scorecard Banner
        st.markdown(
            f"""
            <div class="country-banner">
                <div style="display:flex; justify-content:space-between; flex-wrap:wrap; align-items:center; gap:10px;">
                    <div>
                        <span style="font-size:1.35rem; font-weight:800; color:#1b4332;">{selected_country_tab} ({c_iso})</span>
                        <span style="margin-left:10px; font-size:0.88rem; color:#475569;">{c_cont} • {c_subreg}</span>
                    </div>
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                        <span class="ribbon-pill">{c_status}</span>
                        <span class="ribbon-pill cause">Primary Driver: {c_dom_drv}</span>
                        <span class="ribbon-pill">Top Commodity: {c_dom_comm}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Country 5 Metric Cards
        ck_cols = st.columns(5)
        ck_cols[0].metric(f"Forest Area ({end_year})", format_area_value(c_kpis["area_end_ha"], unit_choice))
        ck_cols[1].metric(
            f"Net Change ({start_year}–{end_year})",
            format_area_value(c_kpis["net_change_period_ha"], unit_choice, signed=True),
            delta=f"{c_kpis['pct_change_period']:+.1f}%" if pd.notna(c_kpis["pct_change_period"]) else None
        )
        ck_cols[2].metric(
            f"Forest Cover ({end_year})",
            f"{c_kpis['forest_share_end_pct']:.1f}%" if pd.notna(c_kpis["forest_share_end_pct"]) else "Data Not Available"
        )
        ck_cols[3].metric(
            f"Land-Use CO₂ ({c_kpis['co2_reported_year'] or 'N/A'})",
            f"{c_kpis['co2_end_tonnes']/1e6:,.1f} Mt CO₂" if pd.notna(c_kpis["co2_end_tonnes"]) else "Data Not Available"
        )
        rli_vals = c_panel_sub.dropna(subset=["Red_List_Index"])
        ck_cols[4].metric(
            "IUCN Red List Index",
            f"{rli_vals['Red_List_Index'].iloc[-1]:.3f}" if not rli_vals.empty else "Data Not Available",
            delta=f"{rli_vals['Red_List_Index'].iloc[-1] - rli_vals['Red_List_Index'].iloc[0]:+.3f}" if len(rli_vals) > 1 else None
        )

        # Row 1: GeoPandas Zoomed Spatial Map + Dual-Axis Historical Trajectory
        r1_c1, r1_c2 = st.columns([2, 3])
        with r1_c1:
            st.plotly_chart(create_geopandas_country_zoom_map(gdf_world, df_panel, iso3=c_iso, year=snapshot_year), width="stretch", key="tab2_geopandas_map")
        with r1_c2:
            st.plotly_chart(create_country_deep_dive_chart(df_panel, iso3=c_iso, start_year=start_year, end_year=end_year), width="stretch", key="tab2_country_trend")

        # Row 2: Cause-Responsive Country Analysis + Gross vs Net / Commodity Breakdown
        r2_c1, r2_c2 = st.columns(2)
        dy0, dy1 = max(start_year, 2001), min(end_year, 2024)
        with r2_c1:
            if selected_cause == "All Causes":
                st.plotly_chart(create_drivers_stacked_bar(df_drivers, entity=selected_country_tab, start_year=dy0, end_year=dy1), width="stretch", key="tab2_country_drivers_stacked")
            else:
                # Cause-specific timeline for THIS country vs Total Loss!
                c_src = df_drivers if active_cause_meta["dataset"] == "drivers" else df_comm
                c_col = active_cause_meta["column"]
                tot_col = "Total_Loss_ha" if active_cause_meta["dataset"] == "drivers" else "Total_Commodity_ha"
                cy0, cy1 = max(start_year, active_cause_meta["years"][0]), min(end_year, active_cause_meta["years"][1])
                c_sub = c_src[(c_src["Code"] == c_iso) & (c_src["Year"] >= cy0) & (c_src["Year"] <= cy1)].sort_values("Year")
                if not c_sub.empty and c_col in c_sub.columns:
                    fig_c_cause = go.Figure()
                    fig_c_cause.add_trace(go.Bar(
                        x=c_sub["Year"],
                        y=c_sub[tot_col] / 1000.0,
                        name="Total Tree Cover Loss",
                        marker_color="#cbd5e1",
                        hovertemplate="Total Loss (%{x}): %{y:,.1f} k ha<extra></extra>"
                    ))
                    fig_c_cause.add_trace(go.Scatter(
                        x=c_sub["Year"],
                        y=c_sub[c_col] / 1000.0,
                        name=active_cause_meta["label"],
                        mode="lines+markers",
                        line=dict(color=active_cause_meta["color"], width=3),
                        fill="tozeroy",
                        fillcolor="rgba(220, 38, 38, 0.12)",
                        hovertemplate=f"{selected_cause} (%{{x}}): %{{y:,.1f}} k ha<extra></extra>"
                    ))
                    _apply_layout(
                        fig_c_cause,
                        title=dict(text=f"{selected_country_tab}: {selected_cause} vs. Total Loss ({cy0}–{cy1})", font=dict(size=14, color=THEME["primary"])),
                        xaxis=dict(title="Year"),
                        yaxis=dict(title="Thousand Hectares (k ha)"),
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_c_cause, width="stretch", key="tab2_country_cause_line")
                else:
                    st.info(f"{selected_cause} data Not Available for {selected_country_tab}.")

        with r2_c2:
            sub_view = st.radio(
                "Secondary Country Panel",
                options=["Commodity Footprint (Pendrill et al.)", "Gross Deforestation vs. Expansion (FAO FRA)"],
                horizontal=True,
                key="country_sec_view"
            )
            if "Commodity" in sub_view:
                cy0, cy1 = max(start_year, 2001), min(end_year, 2023)
                st.plotly_chart(create_commodity_breakdown_chart(df_comm, entity=selected_country_tab, year_range=(cy0, cy1)), width="stretch", key="tab2_country_comm")
            else:
                st.plotly_chart(create_gain_vs_loss_chart(c_panel_sub, entity_label=selected_country_tab), width="stretch", key="tab2_country_gross")

        # Row 3: Multi-Country Side-by-Side Comparison
        st.markdown("---")
        st.markdown("#### ⚖️ Multi-Country Side-by-Side Comparison")
        if compare_countries:
            comp_iso_list = df_panel[df_panel["Entity"].isin(compare_countries)]["ISO3"].unique().tolist()
            mc_ctrl1, mc_ctrl2 = st.columns([2, 1])
            with mc_ctrl1:
                comp_metric = st.selectbox(
                    "Comparison Metric",
                    options=["Forest Area (Mha)", "Annual Net Change (Mha/yr)", "Forest Cover Share (% of Land)", "Land-Use CO₂ Emissions (Mt/yr)"],
                    index=0
                )
            with mc_ctrl2:
                normalize_idx = st.checkbox(f"Normalize Forest Area ({start_year} = 100)", value=True, disabled=("Forest Area" not in comp_metric))

            comp_col_map = {
                "Forest Area (Mha)": "Forest_Area_Mha",
                "Annual Net Change (Mha/yr)": "Annual_Change_Mha",
                "Forest Cover Share (% of Land)": "Forest_Share_pct",
                "Land-Use CO₂ Emissions (Mt/yr)": "CO2_Emissions_Mt"
            }

            mc_c1, mc_c2 = st.columns([3, 2])
            with mc_c1:
                st.plotly_chart(
                    create_country_comparison_lines(df_panel, comp_iso_list, metric=comp_col_map[comp_metric], normalize=normalize_idx, start_year=start_year, end_year=end_year),
                    width="stretch",
                    key="tab2_multi_country_lines"
                )
            with mc_c2:
                st.plotly_chart(
                    create_country_cause_radar(df_drivers, comp_iso_list, year_range=(max(start_year, 2001), min(end_year, 2024))),
                    width="stretch",
                    key="tab2_multi_country_radar"
                )

            # Multi-Country Intensity Heatmap
            hm_src = df_drivers if active_cause_meta["dataset"] == "drivers" else df_comm
            hm_col = active_cause_meta["column"]
            hy0, hy1 = max(start_year, active_cause_meta["years"][0]), min(end_year, active_cause_meta["years"][1])
            if hy0 <= hy1:
                st.plotly_chart(
                    create_country_heatmap(hm_src, hm_col, active_cause_meta["label"], iso3_list=comp_iso_list, year_range=(hy0, hy1), top_n=len(comp_iso_list)),
                    width="stretch",
                    key="tab2_multi_country_heatmap"
                )
        else:
            st.info("Select countries above to compare trajectories and driver fingerprints.")
    else:
        st.warning(f"Data Not Available for {selected_country_tab}.")

# ------------------------------------------------------------------------------
# TAB 3: INTERACTIVE WORLD MAP
# ------------------------------------------------------------------------------
with tabs[2]:
    st.markdown("### 🗺️ Interactive Global & Continental Cartography")

    map_c1, map_c2, map_c3 = st.columns([2, 1, 1])
    map_options = [
        f"Active Cause Loss: {selected_cause}",
        "Annual Net Forest Change (Mha/yr)",
        "Forest Cover Share (% of Land Area)",
        "Total Forest Area (Mha)"
    ]
    default_map_idx = 0 if selected_cause != "All Causes" else 1
    with map_c1:
        map_metric = st.selectbox("Map Visualization Layer", options=map_options, index=default_map_idx)
    with map_c2:
        scope_options = {
            "World": "world",
            "South America": "south america",
            "Africa": "africa",
            "Asia": "asia",
            "Europe": "europe",
            "North America": "north america"
        }
        chosen_scope = st.selectbox("Geographic Zoom Scope", options=list(scope_options.keys()), index=0)
    with map_c3:
        time_mode = st.radio("Map Time Mode", options=["Snapshot Year", "Cumulative Period"], horizontal=True)

    hi_iso = df_panel[df_panel["Entity"] == focus_country]["ISO3"].iloc[0] if focus_country != "All Countries" else None

    if map_metric.startswith("Active Cause Loss"):
        c_df = df_drivers if active_cause_meta["dataset"] == "drivers" else df_comm
        cy0, cy1 = active_cause_meta["years"]
        if time_mode == "Snapshot Year":
            eff_yr = min(max(snapshot_year, cy0), cy1)
            yr_tup = (eff_yr, eff_yr)
        else:
            eff_s, eff_e = max(start_year, cy0), min(end_year, cy1)
            yr_tup = (eff_s, eff_e) if eff_s <= eff_e else (cy0, cy1)

        fig_map = create_cause_world_choropleth(
            c_df[c_df["Continent"].isin(selected_continents)],
            active_cause_meta["column"],
            active_cause_meta["label"],
            year_range=yr_tup,
            scope=scope_options[chosen_scope],
            highlight_iso3=hi_iso,
            cause_color=active_cause_meta["color"]
        )
    elif "Annual Net" in map_metric:
        fig_map = create_world_choropleth(filtered_panel, year=snapshot_year, metric="Annual_Change_Mha", scope=scope_options[chosen_scope], highlight_iso3=hi_iso)
    elif "Forest Cover Share" in map_metric:
        fig_map = create_world_choropleth(filtered_panel, year=snapshot_year, metric="Forest_Share_pct", scope=scope_options[chosen_scope], highlight_iso3=hi_iso)
    else:
        fig_map = create_world_choropleth(filtered_panel, year=snapshot_year, metric="Forest_Area_Mha", scope=scope_options[chosen_scope], highlight_iso3=hi_iso)

    st.plotly_chart(fig_map, width="stretch", key="tab3_world_map")

    # Country Statistics Summary Table below Map
    st.markdown(f"#### 📋 Country-Level Snapshot Table ({snapshot_year})")
    snap_tbl = filtered_panel[filtered_panel["Year"] == snapshot_year][["ISO3", "Entity", "Continent", "Forest_Area_Mha", "Forest_Share_pct", "Annual_Change_Mha", "CO2_Emissions_Mt", "Net_Change_Type"]].copy()
    snap_tbl = snap_tbl.merge(df_hotspots[["ISO3", "Dominant_Driver"]], on="ISO3", how="left")
    snap_tbl = snap_tbl.sort_values("Annual_Change_Mha")
    st.dataframe(
        snap_tbl.style.format({
            "Forest_Area_Mha": "{:,.2f}",
            "Forest_Share_pct": "{:.1f}%",
            "Annual_Change_Mha": "{:+.3f}",
            "CO2_Emissions_Mt": "{:,.1f}"
        }),
        width="stretch",
        hide_index=True
    )

# ------------------------------------------------------------------------------
# TAB 4: CAUSE-DRIVEN ANALYTICS (DYNAMICALLY CHANGES GRAPHS ON CAUSE SELECTION!)
# ------------------------------------------------------------------------------
with tabs[3]:
    st.markdown(f"### 🔍 Cause-Driven Analytics — **{active_cause_meta['label']}**")

    st.markdown(
        f"""
        <div class="callout-box">
            <div class="callout-title">🔬 Methodology & Empirical Scope: {active_cause_meta['category']}</div>
            {active_cause_meta['methodology']} <em>(Valid data years: {active_cause_meta['years'][0]}–{active_cause_meta['years'][1]})</em>
        </div>
        """,
        unsafe_allow_html=True
    )

    if focus_country != "All Countries":
        entity_scope = focus_country
        drv_plot_df = df_drivers
        comm_plot_df = df_comm
    elif len(selected_continents) == 6:
        entity_scope = "World"
        drv_plot_df = df_drivers
        comm_plot_df = df_comm
    else:
        entity_scope = scope_badge
        drv_cols_num = [c for c in DRIVER_COLORS.keys() if c in df_drivers.columns] + ["Total_Loss_ha"]
        drv_plot_df = df_drivers[df_drivers["Continent"].isin(selected_continents)].groupby("Year")[drv_cols_num].sum().reset_index()
        drv_plot_df["Entity"] = entity_scope
        comm_cols_num = ["Beef", "Forestry (paper and wood)", "Palm oil", "Soy", "Cocoa and coffee", "Cereals", "Roots and tubers", "Other crops", "Total_Commodity_ha"]
        comm_plot_df = df_comm[df_comm["Continent"].isin(selected_continents)].groupby("Year")[comm_cols_num].sum().reset_index()
        comm_plot_df["Entity"] = entity_scope

    if selected_cause == "All Causes":
        # Complete multi-cause landscape
        dy0, dy1 = max(start_year, 2001), min(end_year, 2024)
        cy0, cy1 = max(start_year, 2001), min(end_year, 2023)

        c_r1_1, c_r1_2 = st.columns(2)
        with c_r1_1:
            st.plotly_chart(create_drivers_pie_chart(drv_plot_df, entity=entity_scope, year_range=(dy0, dy1)), width="stretch", key="tab4_all_pie")
        with c_r1_2:
            st.plotly_chart(create_commodity_breakdown_chart(comm_plot_df, entity=entity_scope, year_range=(cy0, cy1)), width="stretch", key="tab4_all_comm")

        st.plotly_chart(create_drivers_stacked_bar(drv_plot_df, entity=entity_scope, start_year=dy0, end_year=dy1), width="stretch", key="tab4_all_stacked")

        # Sunburst + Country Intensity Heatmap
        c_r3_1, c_r3_2 = st.columns(2)
        with c_r3_1:
            sun_rows = []
            drv_cols = [c for c in DRIVER_COLORS.keys() if c != "Other natural disturbances"]
            sub_sun = df_drivers[(df_drivers["Continent"].isin(selected_continents)) & (df_drivers["Year"] >= dy0) & (df_drivers["Year"] <= dy1)]
            for cont in selected_continents:
                c_sub = sub_sun[sub_sun["Continent"] == cont]
                for d in drv_cols:
                    val = c_sub[d].sum()
                    if val > 0:
                        sun_rows.append({"Continent": cont, "Driver": d, "Area_Mha": val / 1e6})
            if sun_rows:
                fig_sun = px.sunburst(
                    pd.DataFrame(sun_rows),
                    path=["Continent", "Driver"],
                    values="Area_Mha",
                    color="Driver",
                    color_discrete_map=DRIVER_COLORS,
                    title=f"Continental Share of Direct Drivers ({dy0}–{dy1}) [Mha]"
                )
                _apply_layout(fig_sun, title=dict(font=dict(size=14, color=THEME["primary"])))
                st.plotly_chart(fig_sun, width="stretch", key="tab4_all_sunburst")
            else:
                st.info("Data Not Available for Sunburst in selected range.")
        with c_r3_2:
            hm_scope_df = df_drivers[df_drivers["Continent"].isin(selected_continents)]
            st.plotly_chart(create_country_heatmap(hm_scope_df, "Total_Loss_ha", "All Direct Causes", year_range=(dy0, dy1), top_n=12), width="stretch", key="tab4_all_heatmap")

    else:
        # SPECIFIC CAUSE SELECTED -> COMPLETELY DIFFERENT, CAUSE-ISOLATED VISUALIZATIONS!
        c_df = df_drivers if active_cause_meta["dataset"] == "drivers" else df_comm
        c_col = active_cause_meta["column"]
        c_label = active_cause_meta["label"]
        c_color = active_cause_meta["color"]
        cy0, cy1 = max(start_year, active_cause_meta["years"][0]), min(end_year, active_cause_meta["years"][1])

        if cy0 > cy1:
            st.warning(f"Selected year range ({start_year}–{end_year}) falls outside {c_label} empirical coverage ({active_cause_meta['years'][0]}–{active_cause_meta['years'][1]}).")
        else:
            c_filtered = c_df[c_df["Continent"].isin(selected_continents)].copy()

            # Row 1: Cause-Specific World Map + Top 12 Countries Driven by THIS Cause
            sc_1, sc_2 = st.columns([3, 2])
            with sc_1:
                st.plotly_chart(
                    create_cause_world_choropleth(c_filtered, c_col, c_label, year_range=(cy0, cy1), cause_color=c_color),
                    width="stretch",
                    key="tab4_cause_map"
                )
            with sc_2:
                st.plotly_chart(
                    create_cause_top_countries_bar(c_filtered, c_col, c_label, year_range=(cy0, cy1), top_n=12, cause_color=c_color),
                    width="stretch",
                    key="tab4_cause_top"
                )

            # Row 2: Continental Trajectory of THIS Cause + Share of National Loss Bar
            sc_3, sc_4 = st.columns(2)
            with sc_3:
                st.plotly_chart(
                    create_cause_trajectory_by_continent(c_filtered, c_col, c_label, year_range=(cy0, cy1)),
                    width="stretch",
                    key="tab4_cause_cont_traj"
                )
            with sc_4:
                st.plotly_chart(
                    create_cause_share_comparison(c_filtered, c_col, c_label, year_range=(cy0, cy1), top_n=10, cause_color=c_color),
                    width="stretch",
                    key="tab4_cause_share_bar"
                )

            # Row 3: Country × Year Spike Heatmap for THIS Specific Cause
            st.plotly_chart(
                create_country_heatmap(c_filtered, c_col, c_label, year_range=(cy0, cy1), top_n=15),
                width="stretch",
                key="tab4_cause_heatmap"
            )

            # Ranked Cause Table
            st.markdown(f"#### 📋 Country Ranking Table for {c_label} ({cy0}–{cy1})")
            tot_col = "Total_Loss_ha" if active_cause_meta["dataset"] == "drivers" else "Total_Commodity_ha"
            c_countries = c_filtered[(c_filtered["Code"].str.len() == 3) & (~c_filtered["Code"].str.startswith("OWID", na=False))]
            c_tbl = c_countries[(c_countries["Year"] >= cy0) & (c_countries["Year"] <= cy1)].groupby(["Code", "Entity", "Continent"]).agg({
                c_col: "sum",
                tot_col: "sum"
            }).reset_index()
            c_tbl["Cause_Mha"] = c_tbl[c_col] / 1e6
            c_tbl["Share_of_Country_Loss_%"] = np.where(c_tbl[tot_col] > 0, (c_tbl[c_col] / c_tbl[tot_col]) * 100.0, 0)
            global_tot = c_tbl[c_col].sum()
            c_tbl["Share_of_Global_Cause_%"] = (c_tbl[c_col] / global_tot * 100.0) if global_tot > 0 else 0
            c_tbl = c_tbl.sort_values(c_col, ascending=False).head(25)
            st.dataframe(
                c_tbl[["Code", "Entity", "Continent", "Cause_Mha", "Share_of_Global_Cause_%", "Share_of_Country_Loss_%"]].style.format({
                    "Cause_Mha": "{:,.3f} Mha",
                    "Share_of_Global_Cause_%": "{:.1f}%",
                    "Share_of_Country_Loss_%": "{:.1f}%"
                }),
                width="stretch",
                hide_index=True
            )

# ------------------------------------------------------------------------------
# TAB 5: MOST AFFECTED AREAS & HOTSPOTS
# ------------------------------------------------------------------------------
with tabs[4]:
    st.markdown(f"### 🔥 Most Affected Hotspots & Forest Loss Rankings ({start_year}–{end_year})")

    top_n = st.slider("Number of Countries to Rank", min_value=5, max_value=25, value=10, key="hotspot_top_n")

    h_c1, h_c2 = st.columns(2)
    with h_c1:
        st.plotly_chart(create_top_countries_bar(period_hotspots, top_n=top_n, ascending=True), width="stretch", key="tab5_top_loss")
    with h_c2:
        st.plotly_chart(create_slope_dumbbell_chart(period_hotspots, top_n=top_n), width="stretch", key="tab5_dumbbell")

    # Interactive Bubble Scatter: Net Change vs CO2 Emissions
    st.plotly_chart(create_forest_vs_emissions_scatter(filtered_panel, year=min(snapshot_year, 2024)), width="stretch", key="tab5_scatter")

    st.markdown(f"#### 📋 Top {top_n} Most Deforested Countries Table ({start_year}–{end_year})")
    h_tbl = period_hotspots[period_hotspots["Net_Change_1990_to_Latest_Mha"] < 0].head(top_n)[[
        "ISO3", "Entity", "Continent", "Area_Start_ha", "Area_End_ha", "Net_Change_1990_to_Latest_Mha", "Pct_Change_Since_1990", "Dominant_Driver"
    ]].copy()
    h_tbl["Area_Start_Mha"] = h_tbl["Area_Start_ha"] / 1e6
    h_tbl["Area_End_Mha"] = h_tbl["Area_End_ha"] / 1e6
    st.dataframe(
        h_tbl[["ISO3", "Entity", "Continent", "Area_Start_Mha", "Area_End_Mha", "Net_Change_1990_to_Latest_Mha", "Pct_Change_Since_1990", "Dominant_Driver"]].style.format({
            "Area_Start_Mha": "{:,.2f} Mha",
            "Area_End_Mha": "{:,.2f} Mha",
            "Net_Change_1990_to_Latest_Mha": "{:+,.2f} Mha",
            "Pct_Change_Since_1990": "{:+.1f}%"
        }),
        width="stretch",
        hide_index=True
    )

# ------------------------------------------------------------------------------
# TAB 6: HISTORICAL ANALYSIS & FOREST RECOVERY
# ------------------------------------------------------------------------------
with tabs[5]:
    st.markdown("### 📈 Historical Decadal Analysis & Forest Recovery (1990–2025)")

    hr_c1, hr_c2 = st.columns(2)
    with hr_c1:
        # Decadal net change bar chart computed dynamically for filtered scope
        dec_source = filtered_panel if focus_country == "All Countries" else filtered_panel[filtered_panel["Entity"] == focus_country]
        dec_yr = dec_source.groupby("Year")["Annual_Change_Mha"].sum().reset_index()
        dec_yr = dec_yr[(dec_yr["Year"] >= max(start_year, 1991)) & (dec_yr["Year"] <= end_year)]
        fig_yr_bar = px.bar(
            dec_yr,
            x="Year",
            y="Annual_Change_Mha",
            color="Annual_Change_Mha",
            color_continuous_scale=[[0, THEME["loss_red"]], [0.5, "#e2e8f0"], [1, THEME["gain_green"]]],
            color_continuous_midpoint=0,
            title=f"Year-Wise Net Forest Area Change: {scope_badge} ({start_year}–{end_year})",
            labels={"Annual_Change_Mha": "Annual Change (Mha/yr)"}
        )
        _apply_layout(fig_yr_bar, coloraxis_showscale=False, title=dict(font=dict(size=14, color=THEME["primary"])))
        st.plotly_chart(fig_yr_bar, width="stretch", key="tab6_yearly_bar")

    with hr_c2:
        st.plotly_chart(create_top_countries_bar(period_hotspots, top_n=10, ascending=False), width="stretch", key="tab6_top_gain")

    # Forest Transition Theory Explorer (Recovery Leaders)
    st.markdown("#### 🌱 Forest Transition Curve: Recovery Leaders (China, India, Vietnam, France, Spain, Costa Rica)")
    rec_defaults = [c for c in ["China", "India", "Vietnam", "France", "Spain", "Costa Rica"] if c in available_countries]
    rec_sel = st.multiselect("Select Recovering Nations to Compare", options=available_countries, default=rec_defaults)
    if rec_sel:
        rec_isos = df_panel[df_panel["Entity"].isin(rec_sel)]["ISO3"].unique().tolist()
        st.plotly_chart(
            create_country_comparison_lines(df_panel, rec_isos, metric="Forest_Area_Mha", normalize=True, start_year=start_year, end_year=end_year),
            width="stretch",
            key="tab6_transition_lines"
        )

# ------------------------------------------------------------------------------
# TAB 7: REGIONAL COMPARISON & ENVIRONMENTAL IMPACT
# ------------------------------------------------------------------------------
with tabs[6]:
    st.markdown("### 🌍 Continental Comparison & Environmental Cascades")

    reg_metric = st.selectbox(
        "Select Continental Metric",
        options=[
            "Total Forest Area (Million Hectares)",
            "Annual Net Forest Change (Million Hectares / yr)",
            "Area-Weighted Forest Share (% of Land Area)",
            "Annual CO₂ Emissions from Land-Use Change (Mt CO₂)"
        ],
        index=0
    )
    reg_col_map = {
        "Total Forest Area (Million Hectares)": "Forest_Area_Mha",
        "Annual Net Forest Change (Million Hectares / yr)": "Annual_Change_Mha",
        "Area-Weighted Forest Share (% of Land Area)": "Forest_Share_pct",
        "Annual CO₂ Emissions from Land-Use Change (Mt CO₂)": "CO2_Emissions_Mt"
    }
    df_reg_filt = df_reg[df_reg["Continent"].isin(selected_continents)]
    st.plotly_chart(create_regional_comparison_chart(df_reg_filt, metric=reg_col_map[reg_metric], start_year=start_year, end_year=end_year), width="stretch", key="tab7_regional_lines")

    env_c1, env_c2 = st.columns(2)
    with env_c1:
        # Land-use CO2 emissions for filtered scope or country
        if focus_country != "All Countries":
            co2_scope = filtered_panel[filtered_panel["Entity"] == focus_country].copy()
            co2_scope["CO2_Emissions_Gt"] = co2_scope["CO2_Emissions_tonnes"] / 1e9
            st.plotly_chart(create_environmental_impact_chart(co2_scope, start_year=start_year, end_year=min(end_year, 2024), title_prefix=focus_country), width="stretch", key="tab7_co2_country")
        else:
            co2_agg = filtered_panel.groupby("Year")["CO2_Emissions_tonnes"].sum().reset_index()
            co2_agg["CO2_Emissions_Gt"] = co2_agg["CO2_Emissions_tonnes"] / 1e9
            st.plotly_chart(create_environmental_impact_chart(co2_agg, start_year=start_year, end_year=min(end_year, 2024), title_prefix=scope_badge), width="stretch", key="tab7_co2_scope")

    with env_c2:
        # IUCN Red List Index
        rli_default = ["BRA", "IDN", "COD", "MYS", "PER", "BOL"]
        if focus_country != "All Countries":
            f_iso = df_panel[df_panel["Entity"] == focus_country]["ISO3"].iloc[0]
            if f_iso not in rli_default:
                rli_default.append(f_iso)
        df_bio = filtered_panel[(filtered_panel["ISO3"].isin(rli_default)) & (filtered_panel["Year"] >= start_year) & (filtered_panel["Year"] <= end_year)].dropna(subset=["Red_List_Index"])
        if not df_bio.empty:
            fig_rli = px.line(
                df_bio,
                x="Year",
                y="Red_List_Index",
                color="Entity",
                markers=True,
                title="IUCN Red List Index in Key Forest Frontiers (1.0 = Least Concern)",
                labels={"Red_List_Index": "Red List Index"}
            )
            _apply_layout(fig_rli, title=dict(font=dict(size=14, color=THEME["primary"])))
            st.plotly_chart(fig_rli, width="stretch", key="tab7_rli_lines")
        else:
            st.info("IUCN Red List Index Data Not Available for the selected continents/years.")

# ------------------------------------------------------------------------------
# TAB 8: DATA EXPLORER & SCIENTIFIC AUDIT
# ------------------------------------------------------------------------------
with tabs[7]:
    st.markdown("### 📊 Verified Dataset Explorer, CSV Export & Scientific Citations")

    ds_choice = st.selectbox(
        "Select Dataset to Inspect & Export",
        options=[
            "Country Forest Panel (1990–2025)",
            "Period Hotspot Rankings",
            "Global Summary (1990–2025)",
            "Direct Physical Drivers (Curtis et al. 2001–2024)",
            "Commodity Attribution (Pendrill et al. 2001–2023)",
            "Regional Continental Comparison"
        ]
    )
    if ds_choice == "Country Forest Panel (1990–2025)":
        exp_df = filtered_panel[(filtered_panel["Year"] >= start_year) & (filtered_panel["Year"] <= end_year)]
        fname = "country_forest_panel_filtered.csv"
    elif ds_choice == "Period Hotspot Rankings":
        exp_df = period_hotspots
        fname = f"hotspots_{start_year}_{end_year}.csv"
    elif ds_choice == "Global Summary (1990–2025)":
        exp_df = df_global[(df_global["Year"] >= start_year) & (df_global["Year"] <= end_year)]
        fname = "global_forest_summary.csv"
    elif ds_choice.startswith("Direct Physical"):
        exp_df = df_drivers[(df_drivers["Year"] >= start_year) & (df_drivers["Year"] <= end_year)]
        fname = "deforestation_drivers_processed.csv"
    elif ds_choice.startswith("Commodity"):
        exp_df = df_comm[(df_comm["Year"] >= start_year) & (df_comm["Year"] <= end_year)]
        fname = "commodity_drivers_processed.csv"
    else:
        exp_df = df_reg[df_reg["Continent"].isin(selected_continents) & (df_reg["Year"] >= start_year) & (df_reg["Year"] <= end_year)]
        fname = "regional_comparison.csv"

    q_txt = st.text_input("🔍 Filter rows by Country name or ISO code:", "")
    if q_txt:
        mask = pd.Series(False, index=exp_df.index)
        if "Entity" in exp_df.columns:
            mask |= exp_df["Entity"].astype(str).str.contains(q_txt, case=False, na=False)
        if "ISO3" in exp_df.columns:
            mask |= exp_df["ISO3"].astype(str).str.contains(q_txt, case=False, na=False)
        if "Continent" in exp_df.columns:
            mask |= exp_df["Continent"].astype(str).str.contains(q_txt, case=False, na=False)
        exp_df = exp_df[mask]

    st.markdown(f"**Displaying {min(len(exp_df), 500):,} of {len(exp_df):,} verified records**")
    st.dataframe(exp_df.head(500), width="stretch")

    st.download_button(
        label=f"📥 Download {ds_choice} (CSV)",
        data=exp_df.to_csv(index=False).encode("utf-8"),
        file_name=fname,
        mime="text/csv",
        width="stretch"
    )

    st.markdown("---")
    st.markdown("#### 📚 Source Methodology & Measured vs. Inferred Distinction")
    for src in metadata["authoritative_sources"]:
        with st.expander(f"🔗 {src['name']} — {src['organization']} ({src['coverage']})"):
            st.write(f"**Classification:** {src['type']}")
            st.write(f"**Methodology:** {src['methodology']}")
            st.write(f"**Indicators:** {', '.join(src['indicators'])}")
            if "url" in src:
                st.write(f"**Official Reference:** {src['url']}")
            if "publication" in src:
                st.write(f"**Citation:** {src['publication']}")
