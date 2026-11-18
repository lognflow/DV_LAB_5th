"""
FastAPI Backend Server for Global Deforestation Analytics Dashboard (1990–2025).
Serves the modern custom web frontend and computes authentic metrics and Plotly figures
directly from verified FAO, Global Forest Watch, Pendrill et al., GCP, and IUCN datasets.
"""

import os
import sys
import json
import io
import base64
from typing import List, Optional
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.utils import (
    load_processed_data,
    compute_dynamic_kpis,
    format_area_value,
    CAUSE_METADATA,
    CONTINENT_COLORS,
    DRIVER_COLORS,
    COMMODITY_DISPLAY_NAMES,
    THEME
)
from src.charts import (
    _add_snapshot_vline,
    _apply_layout,
    _empty_figure,
    create_global_forest_heatmap,
    create_world_choropleth,
    create_cause_world_choropleth,
    create_global_trend_chart,
    create_gain_vs_loss_chart,
    create_drivers_pie_chart,
    create_drivers_stacked_bar,
    create_commodity_breakdown_chart,
    create_cause_top_countries_bar,
    create_cause_trajectory_by_continent,
    create_cause_share_comparison,
    create_top_countries_bar,
    create_top_countries_annual_bar,
    create_country_deep_dive_chart,
    create_country_cause_radar,
    create_country_heatmap,
    create_forest_vs_emissions_scatter,
    create_country_treemap,
    create_slope_dumbbell_chart,
    create_environmental_impact_chart
)

app = FastAPI(title="Global Deforestation Analytics API", version="2.0.0")


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static/") or path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


# Mount frontend static assets
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Load verified datasets into memory on startup
DATA = load_processed_data()

DF_PANEL = DATA["country_panel"]
DF_GLOBAL = DATA["global_summary"]
DF_DRIVERS = DATA["drivers"]
DF_COMM = DATA["commodities"]
DF_HOTSPOTS = DATA["hotspots"]

ALL_CONTINENTS = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"]


def _decode_bdata(obj):
    """Recursively decode Plotly 7 binary bdata dicts into plain JSON lists for universal Plotly.js compatibility."""
    if isinstance(obj, dict):
        if "dtype" in obj and "bdata" in obj and len(obj) <= 3:
            dtype_map = {
                "f8": "<f8", "f4": "<f4", "i8": "<i8", "i4": "<i4",
                "i2": "<i2", "i1": "<i1", "u1": "<u1", "u2": "<u2", "u4": "<u4"
            }
            dt = dtype_map.get(obj["dtype"])
            if dt:
                raw = base64.b64decode(obj["bdata"])
                arr = np.frombuffer(raw, dtype=dt)
                if "shape" in obj:
                    shape = tuple(int(x.strip()) for x in str(obj["shape"]).split(","))
                    arr = arr.reshape(shape)
                py_list = arr.tolist()
                if arr.ndim == 1:
                    return [None if (isinstance(v, float) and (np.isnan(v) or np.isinf(v))) else v for v in py_list]
                return [
                    [None if (isinstance(v, float) and (np.isnan(v) or np.isinf(v))) else v for v in row]
                    if isinstance(row, list) else row
                    for row in py_list
                ]
        return {k: _decode_bdata(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_decode_bdata(x) for x in obj]
    return obj


def fig_to_dict(fig: go.Figure) -> dict:
    """Convert a Plotly Figure into a pure JSON-serializable dict without binary bdata dicts."""
    raw_dict = json.loads(fig.to_json())
    return _decode_bdata(raw_dict)


def compute_period_hotspots_df(y0: int, y1: int, continents: List[str]) -> pd.DataFrame:
    """Compute exact net change and dominant driver across [y0, y1] for selected continents."""
    sub = DF_PANEL[DF_PANEL["Continent"].isin(continents)]
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

    dy0, dy1 = max(y0, 2001), min(y1, 2024)
    d_cols = [c for c in DRIVER_COLORS.keys() if c in DF_DRIVERS.columns]
    if dy0 <= dy1:
        d_sub = DF_DRIVERS[(DF_DRIVERS["Code"].str.len() == 3) & (DF_DRIVERS["Year"] >= dy0) & (DF_DRIVERS["Year"] <= dy1)]
        d_grp = d_sub.groupby("Code")[d_cols].sum()
        d_valid = d_grp[d_grp.sum(axis=1) > 0]
        dom_drv = d_valid.idxmax(axis=1).reset_index()
        dom_drv.columns = ["ISO3", "Dominant_Driver"]
        res = res.merge(dom_drv, on="ISO3", how="left")
    else:
        res["Dominant_Driver"] = "Data Not Available"
    res["Dominant_Driver"] = res["Dominant_Driver"].fillna("Data Not Available")
    return res.sort_values("Net_Change_1990_to_Latest_ha").reset_index(drop=True)


class FilterState(BaseModel):
    continents: List[str] = ALL_CONTINENTS
    focus_country: str = "All Countries"
    time_mode: str = "range"  # "range" or "snapshot" (mutually exclusive)
    start_year: int = 1990
    end_year: int = 2025
    snapshot_year: int = 2020
    cause: str = "All Causes"
    unit: str = "Million Hectares (Mha)"
    map_mode: str = "period_change"
    map_scope: str = "world"
    treemap_mode: str = "loss"
    primary_country: str = "Brazil"
    compare_countries: List[str] = ["Brazil", "Indonesia", "Democratic Republic of Congo", "China", "Canada"]
    compare_metric: str = "Forest_Area_Mha"
    normalize_compare: bool = True
    country_secondary_view: str = "commodity"
    top_n: int = 10
    recovery_countries: List[str] = ["China", "India", "Vietnam", "France", "Spain", "Costa Rica"]
    regional_metric: str = "Forest_Area_Mha"


def _resolve_time_window(state: FilterState):
    """Enforce strict mutual exclusion between 'range' and 'snapshot' time modes."""
    mode = "snapshot" if state.time_mode == "snapshot" else "range"
    if mode == "snapshot":
        snap = int(state.snapshot_year)
        return "snapshot", snap, snap, snap, 1990, 2025, snap
    y0, y1 = min(int(state.start_year), int(state.end_year)), max(int(state.start_year), int(state.end_year))
    return "range", y0, y1, y1, y0, y1, None


def _snapshot_treemap_df(snap: int, continents: List[str]) -> pd.DataFrame:
    """Build single-year DataFrame compatible with create_country_treemap."""
    sub = DF_PANEL[(DF_PANEL["Year"] == snap) & (DF_PANEL["Continent"].isin(continents))].copy()
    sub = sub.merge(DF_HOTSPOTS[["ISO3", "Dominant_Driver"]], on="ISO3", how="left")
    sub["Dominant_Driver"] = sub["Dominant_Driver"].fillna("Data Not Available")
    sub["Forest_Area_Latest_ha"] = sub["Forest_Area_ha"]
    sub["Net_Change_1990_to_Latest_Mha"] = sub["Annual_Change_Mha"].fillna(0)
    sub["Pct_Change_Since_1990"] = np.where(
        sub["Forest_Area_ha"] > 0,
        (sub["Annual_Change_ha"].fillna(0) / sub["Forest_Area_ha"]) * 100.0,
        0.0
    )
    return sub


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/vendor/plotly.min.js")
async def serve_plotly_js():
    """Serve bundled Plotly.js directly from the installed Python plotly package."""
    plotly_js = os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js")
    if not os.path.exists(plotly_js):
        raise HTTPException(status_code=404, detail="Bundled plotly.min.js not found")
    return FileResponse(plotly_js, media_type="application/javascript")


@app.get("/api/filters")
async def get_filter_options():
    """Return valid options for all UI controls."""
    countries_df = DF_PANEL[["Entity", "ISO3", "Continent"]].drop_duplicates().sort_values("Entity")
    countries_list = countries_df.to_dict(orient="records")
    causes_list = [
        {
            "id": k,
            "label": v["label"],
            "category": v["category"],
            "years": list(v["years"]),
            "color": v["color"]
        }
        for k, v in CAUSE_METADATA.items()
    ]
    return {
        "continents": ALL_CONTINENTS,
        "countries": countries_list,
        "year_min": 1990,
        "year_max": 2025,
        "causes": causes_list,
        "units": ["Million Hectares (Mha)", "Square Kilometers (km²)", "Hectares (ha)"]
    }


@app.post("/api/overview")
async def get_overview(state: FilterState):
    continents = state.continents or ALL_CONTINENTS
    t_mode, y0, y1, snap, line_y0, line_y1, snap_marker = _resolve_time_window(state)

    kpis = compute_dynamic_kpis(
        DF_PANEL, DF_DRIVERS, DF_COMM,
        y0, y1, continents,
        country_name=state.focus_country,
        selected_cause=state.cause,
        time_mode=t_mode,
        snapshot_year=snap
    )

    net_ha = kpis["net_change_period_ha"]
    direction_status = (
        "DECREASED" if (pd.notna(net_ha) and net_ha < (-100 if t_mode == "snapshot" else -500))
        else ("INCREASED" if (pd.notna(net_ha) and net_ha > (100 if t_mode == "snapshot" else 500)) else ("Data Not Available" if pd.isna(net_ha) else "STABLE"))
    )

    change_label = f"Annual Net Change ({snap})" if t_mode == "snapshot" else f"Net Change ({y0}–{y1})"
    change_suffix = "/yr" if t_mode == "snapshot" else ""
    pct_txt = f"{kpis['pct_change_period']:+.2f}%{change_suffix}" if pd.notna(kpis["pct_change_period"]) else ("Annual rate starts 1991" if (t_mode == "snapshot" and snap == 1990) else "N/A")

    kpi_cards = [
        {
            "label": f"Forest Area ({snap if t_mode == 'snapshot' else y1})",
            "value": format_area_value(kpis["area_end_ha"], state.unit, signed=False),
            "subtext": f"Scope: {kpis['scope_label']}",
            "tone": "neutral"
        },
        {
            "label": change_label,
            "value": (format_area_value(net_ha, state.unit, signed=True) + change_suffix) if pd.notna(net_ha) else "Data Not Available",
            "subtext": f"{direction_status} • {pct_txt}",
            "tone": "loss" if direction_status == "DECREASED" else ("gain" if direction_status == "INCREASED" else "neutral")
        },
        {
            "label": f"Forest Cover ({snap if t_mode == 'snapshot' else y1})",
            "value": f"{kpis['forest_share_end_pct']:.1f}%" if pd.notna(kpis["forest_share_end_pct"]) else "Data Not Available",
            "subtext": "Share of total land area",
            "tone": "neutral"
        }
    ]

    filtered_panel = DF_PANEL[DF_PANEL["Continent"].isin(continents)]
    period_hotspots = compute_period_hotspots_df(y0, y1, continents) if t_mode == "range" else _snapshot_treemap_df(snap, continents)
    hi_iso = kpis["iso3"]
    scope_badge = state.focus_country if state.focus_country != "All Countries" else ("Global" if len(continents) == 6 else ", ".join(continents))

    # 1. Global Heatmap (Decreased vs Increased OR Cause Heatmap)
    cause_meta = CAUSE_METADATA.get(state.cause, CAUSE_METADATA["All Causes"])
    if state.map_mode == "cause_loss" and state.cause != "All Causes":
        c_df = DF_DRIVERS if cause_meta["dataset"] == "drivers" else DF_COMM
        cy0, cy1 = max(y0, cause_meta["years"][0]), min(y1, cause_meta["years"][1])
        if cy0 <= cy1:
            fig_heatmap = create_cause_world_choropleth(
                c_df[c_df["Continent"].isin(continents)],
                cause_meta["column"],
                cause_meta["label"],
                year_range=(cy0, cy1),
                scope=state.map_scope,
                highlight_iso3=hi_iso,
                cause_color=cause_meta["color"]
            )
        else:
            fig_heatmap = _empty_figure(f"{cause_meta['label']} data is available for {cause_meta['years'][0]}–{cause_meta['years'][1]}.")
    else:
        mode_arg = state.map_mode if state.map_mode in ["period_change", "annual_rate", "pct_change"] else "period_change"
        fig_heatmap = create_global_forest_heatmap(
            filtered_panel,
            df_hotspots=DF_HOTSPOTS,
            start_year=y0,
            end_year=y1,
            snapshot_year=snap,
            scope=state.map_scope,
            highlight_iso3=hi_iso,
            mode=mode_arg,
            unit_choice=state.unit,
            time_mode=t_mode
        )

    # 2. Trajectory Chart
    if state.focus_country != "All Countries" and hi_iso:
        fig_trend = create_country_deep_dive_chart(
            DF_PANEL, iso3=hi_iso, start_year=line_y0, end_year=line_y1, snapshot_marker=snap_marker, df_drivers=DF_DRIVERS, unit_choice=state.unit
        )
    else:
        agg_df = filtered_panel.groupby("Year").agg({
            "Forest_Area_ha": "sum",
            "Annual_Change_ha": "sum",
            "CO2_Emissions_tonnes": "sum"
        }).reset_index()
        agg_df["Forest_Area_Mha"] = agg_df["Forest_Area_ha"] / 1_000_000.0
        agg_df["Annual_Change_Mha"] = agg_df["Annual_Change_ha"] / 1_000_000.0
        fig_trend = create_global_trend_chart(agg_df, start_year=line_y0, end_year=line_y1, title_prefix=scope_badge, snapshot_marker=snap_marker)

    # 3. Hierarchical Treemap
    tr_mode = state.treemap_mode if state.treemap_mode in ["loss", "gain", "stock"] else "loss"
    if t_mode == "snapshot" and snap == 1990 and tr_mode in ["loss", "gain"]:
        fig_treemap = _empty_figure("Annual change treemap starts in 1991. Switch to Forest Stock or select 1991–2025.")
    else:
        fig_treemap = create_country_treemap(period_hotspots, mode=tr_mode)

    return {
        "kpis": kpi_cards,
        "charts": {
            "heatmap": fig_to_dict(fig_heatmap),
            "trend": fig_to_dict(fig_trend),
            "secondary": None,
            "treemap": fig_to_dict(fig_treemap)
        }
    }


@app.post("/api/country")
async def get_country_analytics(state: FilterState):
    continents = state.continents or ALL_CONTINENTS
    t_mode, y0, y1, snap, line_y0, line_y1, snap_marker = _resolve_time_window(state)

    target_country = state.primary_country
    if state.focus_country != "All Countries":
        target_country = state.focus_country

    c_panel = DF_PANEL[(DF_PANEL["Entity"] == target_country) & (DF_PANEL["Year"] >= line_y0) & (DF_PANEL["Year"] <= line_y1)].sort_values("Year")
    if c_panel.empty:
        raise HTTPException(status_code=404, detail=f"No data for {target_country}")

    c_iso = c_panel["ISO3"].iloc[0]
    c_cont = c_panel["Continent"].iloc[0]
    c_subreg = c_panel["Sub_Region"].iloc[0]
    hot_row = DF_HOTSPOTS[DF_HOTSPOTS["ISO3"] == c_iso]

    c_kpis = compute_dynamic_kpis(
        DF_PANEL, DF_DRIVERS, DF_COMM,
        y0, y1, continents,
        country_name=target_country,
        selected_cause=state.cause,
        time_mode=t_mode,
        snapshot_year=snap
    )
    net_ha = c_kpis["net_change_period_ha"]
    direction = (
        "DECREASED" if (pd.notna(net_ha) and net_ha < (-100 if t_mode == "snapshot" else -500))
        else ("INCREASED" if (pd.notna(net_ha) and net_ha > (100 if t_mode == "snapshot" else 500)) else ("Data Not Available" if pd.isna(net_ha) else "STABLE"))
    )

    if t_mode == "snapshot":
        rli_row = c_panel[c_panel["Year"] == snap].dropna(subset=["Red_List_Index"])
        rli_str = f"{rli_row['Red_List_Index'].iloc[0]:.3f}" if not rli_row.empty else "Data Not Available"
        rli_delta = ""
    else:
        rli_vals = c_panel.dropna(subset=["Red_List_Index"])
        rli_str = f"{rli_vals['Red_List_Index'].iloc[-1]:.3f}" if not rli_vals.empty else "Data Not Available"
        rli_delta = f"({rli_vals['Red_List_Index'].iloc[-1] - rli_vals['Red_List_Index'].iloc[0]:+.3f})" if len(rli_vals) > 1 else ""

    c_change_lbl = f"Annual Change ({snap})" if t_mode == "snapshot" else f"Net Change ({y0}–{y1})"
    c_sfx = "/yr" if t_mode == "snapshot" else ""
    c_pct_str = f"{c_kpis['pct_change_period']:+.2f}%{c_sfx}" if pd.notna(c_kpis["pct_change_period"]) else "N/A"

    scorecard = {
        "country": target_country,
        "iso3": c_iso,
        "continent": c_cont,
        "sub_region": c_subreg,
        "direction": direction,
        "status": hot_row["Hotspot_Status"].iloc[0] if not hot_row.empty else "Not Classified",
        "dominant_driver": hot_row["Dominant_Driver"].iloc[0] if not hot_row.empty else "Data Not Available",
        "dominant_commodity": COMMODITY_DISPLAY_NAMES.get(hot_row["Dominant_Commodity"].iloc[0], hot_row["Dominant_Commodity"].iloc[0]) if not hot_row.empty else "Data Not Available",
        "metrics": [
            {"label": f"Forest Area ({snap if t_mode == 'snapshot' else y1})", "value": format_area_value(c_kpis["area_end_ha"], state.unit), "tone": "neutral"},
            {
                "label": c_change_lbl,
                "value": (format_area_value(net_ha, state.unit, signed=True) + c_sfx) if pd.notna(net_ha) else "Data Not Available",
                "subtext": f"{direction} • {c_pct_str}",
                "tone": "loss" if direction == "DECREASED" else ("gain" if direction == "INCREASED" else "neutral")
            }
        ]
    }

    fig_deep = create_country_deep_dive_chart(
        DF_PANEL, iso3=c_iso, start_year=line_y0, end_year=line_y1, snapshot_marker=snap_marker, df_drivers=DF_DRIVERS, unit_choice=state.unit
    )

    cause_meta = CAUSE_METADATA.get(state.cause, CAUSE_METADATA["All Causes"])
    if state.cause == "All Causes":
        if t_mode == "snapshot":
            if 2001 <= snap <= 2024:
                fig_c_cause = create_drivers_pie_chart(DF_DRIVERS, entity=target_country, year_range=(snap, snap))
            else:
                fig_c_cause = _empty_figure(f"Direct driver satellite data spans 2001–2024 (selected {snap}).")
        else:
            fig_c_cause = create_drivers_stacked_bar(DF_DRIVERS, entity=target_country, start_year=max(y0, 2001), end_year=min(y1, 2024))
    else:
        c_src = DF_DRIVERS if cause_meta["dataset"] == "drivers" else DF_COMM
        c_col = cause_meta["column"]
        tot_col = "Total_Loss_ha" if cause_meta["dataset"] == "drivers" else "Total_Commodity_ha"
        cy0, cy1 = max(line_y0, cause_meta["years"][0]), min(line_y1, cause_meta["years"][1])
        c_sub = c_src[(c_src["Code"] == c_iso) & (c_src["Year"] >= cy0) & (c_src["Year"] <= cy1)].sort_values("Year")
        if not c_sub.empty and c_col in c_sub.columns:
            fig_c_cause = go.Figure()
            fig_c_cause.add_trace(go.Bar(
                x=c_sub["Year"], y=c_sub[tot_col] / 1000.0,
                name="Total Tree Cover Loss", marker_color="#cbd5e1",
                hovertemplate="Total Loss (%{x}): %{y:,.1f} k ha<extra></extra>"
            ))
            fig_c_cause.add_trace(go.Scatter(
                x=c_sub["Year"], y=c_sub[c_col] / 1000.0,
                name=cause_meta["label"], mode="lines+markers",
                line=dict(color=cause_meta["color"], width=3),
                fill="tozeroy", fillcolor="rgba(220, 38, 38, 0.12)",
                hovertemplate=f"{state.cause} (%{{x}}): %{{y:,.1f}} k ha<extra></extra>"
            ))
            _add_snapshot_vline(fig_c_cause, snap_marker if (snap_marker and cy0 <= snap_marker <= cy1) else None)
            _apply_layout(
                fig_c_cause,
                title=dict(text=f"{target_country}: {state.cause} vs. Total Loss ({cy0}–{cy1})", font=dict(size=14, color="#0f172a")),
                xaxis=dict(title="Year"), yaxis=dict(title="Thousand Hectares (k ha)"), hovermode="x unified"
            )
        else:
            fig_c_cause = _empty_figure(f"{state.cause} data Not Available for {target_country}")

    if state.country_secondary_view == "gross":
        fig_c_sec = create_gain_vs_loss_chart(c_panel, entity_label=target_country)
    else:
        cy0, cy1 = max(y0, 2001), min(y1, 2023)
        if cy0 <= cy1:
            fig_c_sec = create_commodity_breakdown_chart(DF_COMM, entity=target_country, year_range=(cy0, cy1))
        else:
            fig_c_sec = _empty_figure(f"Commodity attribution data spans 2001–2023 (selected {snap}).")

    comp_list = state.compare_countries or [target_country]
    comp_isos = DF_PANEL[DF_PANEL["Entity"].isin(comp_list)]["ISO3"].unique().tolist()

    rad_y0, rad_y1 = max(y0, 2001), min(y1, 2024)
    if rad_y0 <= rad_y1:
        fig_comp_radar = create_country_cause_radar(DF_DRIVERS, comp_isos, year_range=(rad_y0, rad_y1))
    else:
        fig_comp_radar = _empty_figure(f"Driver radar data spans 2001–2024 (selected {snap}).")

    hm_src = DF_DRIVERS if cause_meta["dataset"] == "drivers" else DF_COMM
    hy0, hy1 = max(line_y0, cause_meta["years"][0]), min(line_y1, cause_meta["years"][1])
    if hy0 <= hy1 and comp_isos:
        fig_comp_heat = create_country_heatmap(hm_src, cause_meta["column"], cause_meta["label"], iso3_list=comp_isos, year_range=(hy0, hy1), top_n=len(comp_isos))
    else:
        fig_comp_heat = _empty_figure("Heatmap unavailable for selected years/countries.")

    return {
        "scorecard": scorecard,
        "charts": {
            "deep_dive": fig_to_dict(fig_deep),
            "cause_timeline": fig_to_dict(fig_c_cause),
            "secondary": fig_to_dict(fig_c_sec),
            "compare_radar": fig_to_dict(fig_comp_radar),
            "compare_heatmap": fig_to_dict(fig_comp_heat)
        }
    }


@app.post("/api/causes")
async def get_causes_analytics(state: FilterState):
    continents = state.continents or ALL_CONTINENTS
    t_mode, y0, y1, snap, line_y0, line_y1, snap_marker = _resolve_time_window(state)
    cause_meta = CAUSE_METADATA.get(state.cause, CAUSE_METADATA["All Causes"])

    comp_list = state.compare_countries or ["Brazil", "Indonesia", "Democratic Republic of Congo", "China", "Canada"]
    comp_isos = DF_PANEL[DF_PANEL["Entity"].isin(comp_list)]["ISO3"].unique().tolist()

    rad_y0, rad_y1 = max(y0, 2001), min(y1, 2024)
    if rad_y0 <= rad_y1 and comp_isos:
        fig_comp_radar = create_country_cause_radar(DF_DRIVERS, comp_isos, year_range=(rad_y0, rad_y1))
    else:
        fig_comp_radar = _empty_figure(f"Driver radar data spans 2001–2024 (selected {snap}).")

    hm_src = DF_DRIVERS if cause_meta["dataset"] == "drivers" else DF_COMM
    hy0, hy1 = max(line_y0, cause_meta["years"][0]), min(line_y1, cause_meta["years"][1])
    if hy0 <= hy1 and comp_isos:
        fig_comp_heat = create_country_heatmap(hm_src, cause_meta["column"], cause_meta["label"], iso3_list=comp_isos, year_range=(hy0, hy1), top_n=len(comp_isos))
    else:
        fig_comp_heat = _empty_figure("Heatmap unavailable for selected years/countries.")

    if state.cause == "All Causes":
        dy0, dy1 = max(y0, 2001), min(y1, 2024)
        cy0, cy1 = max(y0, 2001), min(y1, 2023)
        line_dy0, line_dy1 = max(line_y0, 2001), min(line_y1, 2024)
        scope_label = state.focus_country if state.focus_country != "All Countries" else ("World" if len(continents) == 6 else ", ".join(continents))

        if state.focus_country != "All Countries":
            drv_df, comm_df = DF_DRIVERS, DF_COMM
        elif len(continents) == 6:
            drv_df, comm_df = DF_DRIVERS, DF_COMM
        else:
            drv_cols = [c for c in DRIVER_COLORS.keys() if c in DF_DRIVERS.columns] + ["Total_Loss_ha"]
            drv_df = DF_DRIVERS[DF_DRIVERS["Continent"].isin(continents)].groupby("Year")[drv_cols].sum().reset_index()
            drv_df["Entity"] = scope_label
            comm_cols = ["Beef", "Forestry (paper and wood)", "Palm oil", "Soy", "Cocoa and coffee", "Cereals", "Roots and tubers", "Other crops", "Total_Commodity_ha"]
            comm_df = DF_COMM[DF_COMM["Continent"].isin(continents)].groupby("Year")[comm_cols].sum().reset_index()
            comm_df["Entity"] = scope_label

        fig_pie = create_drivers_pie_chart(drv_df, entity=scope_label, year_range=(dy0, dy1)) if dy0 <= dy1 else _empty_figure("Direct driver data spans 2001–2024.")
        fig_comm = create_commodity_breakdown_chart(comm_df, entity=scope_label, year_range=(cy0, cy1)) if cy0 <= cy1 else _empty_figure("Commodity attribution data spans 2001–2023.")
        fig_stacked = create_drivers_stacked_bar(drv_df, entity=scope_label, start_year=line_dy0, end_year=line_dy1)
        if snap_marker and line_dy0 <= snap_marker <= line_dy1:
            _add_snapshot_vline(fig_stacked, snap_marker)

        sun_rows = []
        if dy0 <= dy1:
            drv_cols_sun = [c for c in DRIVER_COLORS.keys() if c != "Other natural disturbances"]
            sub_sun = DF_DRIVERS[(DF_DRIVERS["Continent"].isin(continents)) & (DF_DRIVERS["Year"] >= dy0) & (DF_DRIVERS["Year"] <= dy1)]
            for cont in continents:
                c_sub = sub_sun[sub_sun["Continent"] == cont]
                for d in drv_cols_sun:
                    val = c_sub[d].sum()
                    if val > 0:
                        sun_rows.append({"Continent": cont, "Driver": d, "Area_Mha": val / 1e6})
        if sun_rows:
            sun_yr = f"{dy0}" if dy0 == dy1 else f"{dy0}–{dy1}"
            fig_sun = px.sunburst(
                pd.DataFrame(sun_rows), path=["Continent", "Driver"], values="Area_Mha",
                color="Driver", color_discrete_map=DRIVER_COLORS,
                title=f"Continental Share of Direct Drivers ({sun_yr}) [Mha]"
            )
            _apply_layout(fig_sun, title=dict(font=dict(size=14, color="#0f172a")))
        else:
            fig_sun = _empty_figure("Direct driver data spans 2001–2024.")

        fig_heat = create_country_heatmap(DF_DRIVERS[DF_DRIVERS["Continent"].isin(continents)], "Total_Loss_ha", "All Direct Causes", year_range=(line_dy0, line_dy1), top_n=12)

        return {
            "mode": "all",
            "cause_label": f"{cause_meta['label']} ({snap if t_mode == 'snapshot' else f'{y0}–{y1}'})",
            "charts": {
                "pie": fig_to_dict(fig_pie),
                "commodity": fig_to_dict(fig_comm),
                "stacked": fig_to_dict(fig_stacked),
                "sunburst": fig_to_dict(fig_sun),
                "heatmap": fig_to_dict(fig_heat),
                "compare_radar": fig_to_dict(fig_comp_radar),
                "compare_heatmap": fig_to_dict(fig_comp_heat)
            },
            "table": []
        }

    # SPECIFIC CAUSE SELECTED
    c_df = DF_DRIVERS if cause_meta["dataset"] == "drivers" else DF_COMM
    c_col = cause_meta["column"]
    c_label = cause_meta["label"]
    c_color = cause_meta["color"]
    cy0, cy1 = max(y0, cause_meta["years"][0]), min(y1, cause_meta["years"][1])
    line_cy0, line_cy1 = max(line_y0, cause_meta["years"][0]), min(line_y1, cause_meta["years"][1])

    if cy0 > cy1:
        empty = fig_to_dict(_empty_figure(f"{c_label} data is available for {cause_meta['years'][0]}–{cause_meta['years'][1]} (selected {snap if t_mode == 'snapshot' else f'{y0}–{y1}'})."))
        return {
            "mode": "specific",
            "cause_label": c_label,
            "charts": {
                "map": empty, "top": empty, "trajectory": empty, "share": empty, "heatmap": empty,
                "compare_radar": fig_to_dict(fig_comp_radar),
                "compare_heatmap": fig_to_dict(fig_comp_heat)
            },
            "table": []
        }

    c_filtered = c_df[c_df["Continent"].isin(continents)].copy()
    hi_df = DF_PANEL[DF_PANEL["Entity"] == state.focus_country] if state.focus_country != "All Countries" else pd.DataFrame()
    hi_iso = hi_df["ISO3"].iloc[0] if not hi_df.empty else None

    fig_map = create_cause_world_choropleth(c_filtered, c_col, c_label, year_range=(cy0, cy1), scope=state.map_scope, highlight_iso3=hi_iso, cause_color=c_color)
    fig_top = create_cause_top_countries_bar(c_filtered, c_col, c_label, year_range=(cy0, cy1), top_n=12, cause_color=c_color)
    fig_traj = create_cause_trajectory_by_continent(c_filtered, c_col, c_label, year_range=(line_cy0, line_cy1), snapshot_marker=snap_marker)
    fig_share = create_cause_share_comparison(c_filtered, c_col, c_label, year_range=(cy0, cy1), top_n=10, cause_color=c_color)
    fig_heat = create_country_heatmap(c_filtered, c_col, c_label, year_range=(line_cy0, line_cy1), top_n=15)

    tot_col = "Total_Loss_ha" if cause_meta["dataset"] == "drivers" else "Total_Commodity_ha"
    c_countries = c_filtered[(c_filtered["Code"].str.len() == 3) & (~c_filtered["Code"].str.startswith("OWID", na=False))]
    c_tbl = c_countries[(c_countries["Year"] >= cy0) & (c_countries["Year"] <= cy1)].groupby(["Code", "Entity", "Continent"]).agg({c_col: "sum", tot_col: "sum"}).reset_index()
    c_tbl["Cause_Mha"] = (c_tbl[c_col] / 1e6).round(3)
    c_tbl["Share_of_Country_Loss"] = np.where(c_tbl[tot_col] > 0, (c_tbl[c_col] / c_tbl[tot_col]) * 100.0, 0).round(1)
    g_tot = c_tbl[c_col].sum()
    c_tbl["Share_of_Global_Cause"] = ((c_tbl[c_col] / g_tot * 100.0) if g_tot > 0 else 0).round(1)
    c_tbl = c_tbl.sort_values(c_col, ascending=False).head(25)

    yr_disp = f"{snap}" if t_mode == "snapshot" else f"{cy0}–{cy1}"
    return {
        "mode": "specific",
        "cause_label": f"{c_label} ({yr_disp})",
        "charts": {
            "map": fig_to_dict(fig_map),
            "top": fig_to_dict(fig_top),
            "trajectory": fig_to_dict(fig_traj),
            "share": fig_to_dict(fig_share),
            "heatmap": fig_to_dict(fig_heat),
            "compare_radar": fig_to_dict(fig_comp_radar),
            "compare_heatmap": fig_to_dict(fig_comp_heat)
        },
        "table": c_tbl[["Code", "Entity", "Continent", "Cause_Mha", "Share_of_Global_Cause", "Share_of_Country_Loss"]].to_dict(orient="records")
    }


@app.post("/api/hotspots")
async def get_hotspots_analytics(state: FilterState):
    continents = state.continents or ALL_CONTINENTS
    t_mode, y0, y1, snap, line_y0, line_y1, snap_marker = _resolve_time_window(state)

    filtered_panel = DF_PANEL[DF_PANEL["Continent"].isin(continents)]

    if t_mode == "snapshot":
        fig_loss = create_top_countries_annual_bar(filtered_panel, year=snap, top_n=state.top_n, ascending=True, df_hotspots=DF_HOTSPOTS)
        fig_gain = create_top_countries_annual_bar(filtered_panel, year=snap, top_n=state.top_n, ascending=False, df_hotspots=DF_HOTSPOTS)
    else:
        period_hotspots = compute_period_hotspots_df(y0, y1, continents)
        fig_loss = create_top_countries_bar(period_hotspots, top_n=state.top_n, ascending=True)
        fig_gain = create_top_countries_bar(period_hotspots, top_n=state.top_n, ascending=False)

    return {
        "time_mode": t_mode,
        "year_label": f"{snap}" if t_mode == "snapshot" else f"{y0}–{y1}",
        "charts": {
            "top_loss": fig_to_dict(fig_loss),
            "top_gain": fig_to_dict(fig_gain)
        }
    }

