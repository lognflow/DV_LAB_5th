"""
Plotly & GeoPandas Chart Generation Library
Interactive, publication-grade scientific visualizations designed with a forest-green theme.
Supports country-wise deep dives, multi-country comparison, and cause-dynamic visualizations.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from src.utils import (
    THEME,
    PLOTLY_LAYOUT,
    CONTINENT_COLORS,
    DRIVER_COLORS,
    COMMODITY_COLORS,
    convert_area
)


def _apply_layout(fig, **overrides):
    """Safely merge PLOTLY_LAYOUT with chart-specific overrides and enforce crisp dark fonts."""
    layout = dict(PLOTLY_LAYOUT)
    layout.update(overrides)
    fig.update_layout(layout)
    fig.update_xaxes(
        tickfont=dict(color="#334155", size=11),
        title_font=dict(color="#0f172a", size=12)
    )
    fig.update_yaxes(
        tickfont=dict(color="#334155", size=11),
        title_font=dict(color="#0f172a", size=12)
    )
    return fig


def _add_snapshot_vline(fig, snapshot_marker):
    """Draw a clean vertical dashed line & pill tag highlighting the active Snapshot Year."""
    if snapshot_marker is not None:
        fig.add_vline(
            x=snapshot_marker,
            line_width=2.2,
            line_dash="dash",
            line_color="#dc2626",
            annotation_text=f"Snapshot: {snapshot_marker}",
            annotation_position="top right",
            annotation_font=dict(size=11, color="#991b1b"),
            annotation_bgcolor="#fef2f2",
            annotation_bordercolor="#fecaca",
            annotation_borderwidth=1
        )
    return fig


def _empty_figure(message="Data Not Available for the selected filters"):
    """Return a clean placeholder figure when empirical data is absent."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color=THEME["muted_text"])
    )
    return _apply_layout(
        fig,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=380
    )


def create_global_forest_heatmap(df_panel, df_hotspots=None, start_year=1990, end_year=2025, snapshot_year=2020, scope="world", highlight_iso3=None, mode="period_change", unit_choice="Million Hectares (Mha)", time_mode="range"):
    """
    Global Forest Change Heatmap (Choropleth):
    Supports mutually exclusive 'range' (start_year..end_year) and 'snapshot' (single year) modes.
    Explicitly shows whether each country DECREASED or INCREASED in forest cover.
    """
    ref_yr = snapshot_year if time_mode == "snapshot" else end_year
    p_start = df_panel[df_panel["Year"] == start_year][["ISO3", "Entity", "Continent", "Forest_Area_ha"]].rename(
        columns={"Forest_Area_ha": "Area_Start_ha"}
    )
    p_end = df_panel[df_panel["Year"] == end_year][["ISO3", "Forest_Area_ha"]].rename(
        columns={"Forest_Area_ha": "Area_End_ha"}
    )
    p_snap = df_panel[df_panel["Year"] == ref_yr][["ISO3", "Entity", "Continent", "Forest_Area_ha", "Forest_Share_pct", "Annual_Change_ha"]].rename(
        columns={"Forest_Area_ha": "Area_Snap_ha", "Annual_Change_ha": "Annual_Snap_ha"}
    )

    if time_mode == "snapshot":
        merged = p_snap.copy()
        merged["Area_Start_ha"] = merged["Area_Snap_ha"]
        merged["Area_End_ha"] = merged["Area_Snap_ha"]
    else:
        merged = p_start.merge(p_end, on="ISO3", how="inner").merge(
            p_snap[["ISO3", "Area_Snap_ha", "Forest_Share_pct", "Annual_Snap_ha"]], on="ISO3", how="left"
        )

    if df_hotspots is not None and "Dominant_Driver" in df_hotspots.columns:
        merged = merged.merge(df_hotspots[["ISO3", "Dominant_Driver"]], on="ISO3", how="left")
    else:
        merged["Dominant_Driver"] = "Data Not Available"
    merged["Dominant_Driver"] = merged["Dominant_Driver"].fillna("Data Not Available")

    if merged.empty:
        return _empty_figure(f"Data Not Available for {ref_yr if time_mode == 'snapshot' else f'{start_year}–{end_year}'}")

    if "Square" in unit_choice:
        divisor, unit_lbl, val_fmt = 100.0, "km²", ",.0f"
    elif "Hectares (ha)" in unit_choice:
        divisor, unit_lbl, val_fmt = 1.0, "ha", ",.0f"
    else:
        divisor, unit_lbl, val_fmt = 1_000_000.0, "Mha", ",.2f"

    merged["Annual_Snap_Unit"] = merged["Annual_Snap_ha"] / divisor
    merged["Area_Snap_Unit"] = merged["Area_Snap_ha"] / divisor
    merged["Annual_Pct"] = np.where(
        (merged["Area_Snap_ha"] > 0) & merged["Annual_Snap_ha"].notna(),
        (merged["Annual_Snap_ha"] / merged["Area_Snap_ha"]) * 100.0,
        np.nan
    )

    if time_mode == "snapshot":
        if ref_yr == 1990 and mode in ["period_change", "annual_rate", "pct_change"]:
            return _empty_figure("Annual forest change rate begins in 1991 (1990 is the baseline inventory year). Select 1991–2025 or choose Year Range mode.")
        merged["Primary_Delta_ha"] = merged["Annual_Snap_ha"]
        merged["Primary_Delta_Unit"] = merged["Annual_Snap_Unit"]
        merged["Primary_Pct"] = merged["Annual_Pct"]
        effective_mode = "pct_change" if mode == "pct_change" else "annual_rate"
    else:
        merged["Primary_Delta_ha"] = merged["Area_End_ha"] - merged["Area_Start_ha"]
        merged["Primary_Delta_Unit"] = merged["Primary_Delta_ha"] / divisor
        merged["Primary_Pct"] = np.where(
            merged["Area_Start_ha"] > 0,
            (merged["Primary_Delta_ha"] / merged["Area_Start_ha"]) * 100.0,
            0.0
        )
        effective_mode = "annual_rate" if (start_year == end_year and mode == "period_change") else mode

    def status_badge(val):
        if pd.isna(val):
            return "Data Not Available"
        thresh = -100 if time_mode == "snapshot" else -500
        pos_thresh = 100 if time_mode == "snapshot" else 500
        if val < thresh:
            return "🔴 DECREASED (Forest Loss)"
        if val > pos_thresh:
            return "🟢 INCREASED (Forest Gain)"
        return "⚪ STABLE (No Net Change)"

    def annual_badge(val):
        if pd.isna(val):
            return "Data Not Available"
        conv = val / divisor
        num_str = f"{conv:+,.0f}" if divisor <= 100.0 else f"{conv:+,.3f}"
        if val < -100:
            return f"{num_str} {unit_lbl}/yr (Decreased)"
        if val > 100:
            return f"{num_str} {unit_lbl}/yr (Increased)"
        return f"0 {unit_lbl}/yr (Stable)"

    merged["Status_Badge"] = merged["Primary_Delta_ha"].apply(status_badge)
    merged["Annual_Status_Text"] = merged["Annual_Snap_ha"].apply(annual_badge)

    if effective_mode == "annual_rate":
        z_col = "Annual_Snap_Unit"
        title = f"Global Forest Heatmap: Annual Rate ({ref_yr}) — Decreased vs. Increased"
        cb_title = f"{unit_lbl} / yr"
    elif effective_mode == "pct_change":
        z_col = "Primary_Pct"
        lbl_span = f"{ref_yr} Annual % Rate" if time_mode == "snapshot" else f"{start_year}–{end_year} % Change"
        title = f"Global Forest Heatmap: {lbl_span} — Decreased vs. Increased"
        cb_title = "% Rate" if time_mode == "snapshot" else "% Change"
    else:
        z_col = "Primary_Delta_Unit"
        title = f"Global Forest Heatmap: Net Forest Change ({start_year}–{end_year}) — Decreased vs. Increased"
        cb_title = f"Net {unit_lbl}"

    valid_z = merged[z_col].dropna()
    q03 = valid_z.quantile(0.03) if not valid_z.empty else -2.0
    q97 = valid_z.quantile(0.97) if not valid_z.empty else 2.0
    max_abs = max(abs(float(q03)), abs(float(q97)))
    if pd.isna(max_abs) or max_abs == 0:
        max_abs = float(valid_z.abs().max()) if (not valid_z.empty and valid_z.abs().max() > 0) else 2.0

    line_colors = ["#0f172a" if iso == highlight_iso3 else "#ffffff" for iso in merged["ISO3"]]
    line_widths = [3.0 if iso == highlight_iso3 else 0.7 for iso in merged["ISO3"]]

    if time_mode == "snapshot":
        hover_tpl = (
            "<b>%{text} (%{location})</b> — %{customdata[0]}<br>"
            f"<b>Status ({ref_yr}): %{{customdata[1]}}</b><br>"
            f"Annual Change ({ref_yr}): <b>%{{customdata[4]}} (%{{customdata[3]:+.2f}}%/yr)</b><br>"
            f"Forest Area ({ref_yr}): %{{customdata[5]:{val_fmt}}} {unit_lbl} (%{{customdata[6]:.1f}}% of land)<br>"
            "Primary Cause: %{customdata[7]}"
            "<extra></extra>"
        )
    else:
        hover_tpl = (
            "<b>%{text} (%{location})</b> — %{customdata[0]}<br>"
            "<b>Status: %{customdata[1]}</b><br>"
            f"Net Change ({start_year}–{end_year}): <b>%{{customdata[2]:+{val_fmt}}} {unit_lbl} (%{{customdata[3]:+.1f}}%)</b><br>"
            f"Annual Rate ({ref_yr}): %{{customdata[4]}}<br>"
            f"Forest Area ({ref_yr}): %{{customdata[5]:{val_fmt}}} {unit_lbl} (%{{customdata[6]:.1f}}% of land)<br>"
            "Primary Cause: %{customdata[7]}"
            "<extra></extra>"
        )

    fig = go.Figure(go.Choropleth(
        locations=merged["ISO3"].tolist(),
        z=merged[z_col].fillna(0).tolist(),
        text=merged["Entity"].tolist(),
        customdata=np.stack([
            merged["Continent"],
            merged["Status_Badge"],
            merged["Primary_Delta_Unit"].fillna(0),
            merged["Primary_Pct"].fillna(0),
            merged["Annual_Status_Text"],
            merged["Area_Snap_Unit"].fillna(0),
            merged["Forest_Share_pct"].fillna(0),
            merged["Dominant_Driver"]
        ], axis=-1).tolist(),
        colorscale=[
            [0.0, "#991b1b"],
            [0.32, "#ef4444"],
            [0.47, "#fecaca"],
            [0.50, "#f1f5f9"],
            [0.53, "#bbf7d0"],
            [0.68, "#22c55e"],
            [1.0, "#14532d"]
        ],
        zmin=-max_abs,
        zmax=max_abs,
        zmid=0,
        marker=dict(
            line=dict(color=line_colors, width=line_widths)
        ),
        colorbar=dict(
            title=dict(text=cb_title, font=dict(color="#0f172a", size=12)),
            tickfont=dict(color="#0f172a", size=11),
            thickness=15,
            len=0.78,
            x=0.98
        ),
        hovertemplate=hover_tpl
    ))

    geo_cfg = dict(
        scope=scope,
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#94a3b8",
        projection_type="natural earth" if scope == "world" else "mercator",
        bgcolor="#ffffff",
        lakecolor="#eff6ff",
        showland=True,
        landcolor="#f1f5f9",
        showcountries=True,
        countrycolor="#e2e8f0"
    )
    if scope == "world" and len(merged) < 160:
        geo_cfg["fitbounds"] = "locations"

    return _apply_layout(
        fig,
        title=dict(text=title, font=dict(size=16, color="#0f172a")),
        geo=geo_cfg,
        margin=dict(l=5, r=5, t=55, b=5)
    )


def create_world_choropleth(df_panel, year=2020, metric="Annual_Change_Mha", scope="world", highlight_iso3=None):
    """
    World choropleth map showing country-level deforestation or forest area.
    Explicitly indicates Decreased vs. Increased on hover.
    """
    df_yr = df_panel[df_panel["Year"] == year].copy()
    if df_yr.empty:
        return _empty_figure(f"Data Not Available for Year {year}")

    df_yr["Direction"] = np.where(
        df_yr["Annual_Change_ha"] < -500, "🔴 DECREASED (Loss)",
        np.where(df_yr["Annual_Change_ha"] > 500, "🟢 INCREASED (Gain)", "⚪ STABLE")
    )

    if metric == "Annual_Change_Mha":
        title = f"Annual Net Forest Change by Country ({year}) — Decreased vs. Increased"
        color_col = "Annual_Change_Mha"
        q02 = df_yr[color_col].quantile(0.02)
        q98 = df_yr[color_col].quantile(0.98)
        max_abs = max(abs(q02) if pd.notna(q02) else 0, abs(q98) if pd.notna(q98) else 0)
        if pd.isna(max_abs) or max_abs == 0:
            max_abs = 2.0

        fig = px.choropleth(
            df_yr,
            locations="ISO3",
            color=color_col,
            hover_name="Entity",
            hover_data={
                "ISO3": True,
                "Continent": True,
                "Direction": True,
                "Forest_Area_Mha": ":.2f",
                "Forest_Share_pct": ":.1f",
                "Annual_Change_Mha": ":+.3f"
            },
            color_continuous_scale=[
                [0.0, "#991b1b"],
                [0.45, "#fca5a5"],
                [0.5, "#f1f5f9"],
                [0.55, "#86efac"],
                [1.0, "#14532d"]
            ],
            range_color=[-max_abs, max_abs],
            labels={"Annual_Change_Mha": "Net Change (Mha/yr)", "Forest_Share_pct": "Forest Share (%)"}
        )
    elif metric == "Forest_Share_pct":
        title = f"Forest Area as Share of Land Area ({year}) [%]"
        fig = px.choropleth(
            df_yr,
            locations="ISO3",
            color="Forest_Share_pct",
            hover_name="Entity",
            hover_data={
                "ISO3": True,
                "Continent": True,
                "Direction": True,
                "Forest_Area_Mha": ":.2f",
                "Forest_Share_pct": ":.1f"
            },
            color_continuous_scale=[
                [0.0, "#f7fcf5"],
                [0.2, "#e5f5e0"],
                [0.4, "#a1d99b"],
                [0.7, "#41ab5d"],
                [1.0, "#00441b"]
            ],
            range_color=[0, 100],
            labels={"Forest_Share_pct": "Forest Share (%)"}
        )
    else:
        title = f"Total Forest Area by Country ({year}) [Million Hectares]"
        fig = px.choropleth(
            df_yr,
            locations="ISO3",
            color="Forest_Area_Mha",
            hover_name="Entity",
            hover_data={
                "ISO3": True,
                "Continent": True,
                "Direction": True,
                "Forest_Area_Mha": ":.2f",
                "Forest_Share_pct": ":.1f"
            },
            color_continuous_scale=[
                [0.0, "#edf8e9"],
                [0.2, "#bae4b3"],
                [0.5, "#74c476"],
                [0.8, "#31a354"],
                [1.0, "#006d2c"]
            ],
            labels={"Forest_Area_Mha": "Forest Area (Mha)", "Forest_Share_pct": "Forest Share (%)"}
        )

    if highlight_iso3:
        sub_hi = df_yr[df_yr["ISO3"] == highlight_iso3]
        if not sub_hi.empty:
            fig.add_trace(
                go.Choropleth(
                    locations=sub_hi["ISO3"],
                    z=[1],
                    colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                    showscale=False,
                    marker_line_color="#111827",
                    marker_line_width=2.8,
                    hoverinfo="skip",
                    name="Selected Country"
                )
            )

    return _apply_layout(
        fig,
        title=dict(text=title, font=dict(size=15, color="#0f172a")),
        geo=dict(
            scope=scope,
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#94a3b8",
            projection_type="natural earth" if scope == "world" else "mercator",
            bgcolor="#ffffff",
            lakecolor="#f0f9ff",
            showland=True,
            landcolor="#f1f5f9"
        ),
        margin=dict(l=0, r=0, t=55, b=0),
        coloraxis_colorbar=dict(
            title=dict(font=dict(size=11, color="#0f172a")),
            tickfont=dict(size=11, color="#0f172a"),
            thickness=14,
            len=0.75,
            x=0.98
        )
    )


def create_cause_world_choropleth(df_cause, cause_col, cause_label, year_range=(2001, 2024), scope="world", highlight_iso3=None, cause_color="#dc2626"):
    """
    Cause-specific World Choropleth Map!
    Aggregates tree cover loss from a specific physical driver or commodity across year_range.
    """
    y0, y1 = year_range
    sub = df_cause[(df_cause["Code"].str.len() == 3) & (~df_cause["Code"].str.startswith("OWID", na=False))]
    sub = sub[(sub["Year"] >= y0) & (sub["Year"] <= y1)]

    if sub.empty or cause_col not in sub.columns:
        return _empty_figure(f"Data Not Available for {cause_label} ({y0}–{y1})")

    agg = sub.groupby(["Code", "Entity", "Continent"]).agg({cause_col: "sum"}).reset_index()
    agg["Loss_k_ha"] = agg[cause_col] / 1000.0
    agg["Loss_Mha"] = agg[cause_col] / 1_000_000.0

    # Use 98th percentile max so Brazil/Canada doesn't flatten rest of world colors
    q98 = agg["Loss_k_ha"].quantile(0.98)
    z_max = q98 if (pd.notna(q98) and q98 > 0) else agg["Loss_k_ha"].max()

    line_colors = ["#0f172a" if iso == highlight_iso3 else "#ffffff" for iso in agg["Code"]]
    line_widths = [3.0 if iso == highlight_iso3 else 0.7 for iso in agg["Code"]]

    fig = go.Figure(go.Choropleth(
        locations=agg["Code"].tolist(),
        z=agg["Loss_k_ha"].fillna(0).tolist(),
        text=agg["Entity"].tolist(),
        customdata=np.stack([agg["Continent"], agg["Loss_Mha"].fillna(0)], axis=-1).tolist(),
        colorscale=[[0.0, "#f8fafc"], [0.15, "#fef3c7"], [0.5, "#fb923c"], [1.0, cause_color]],
        zmin=0,
        zmax=float(z_max) if (pd.notna(z_max) and z_max > 0) else 10.0,
        marker=dict(line=dict(color=line_colors, width=line_widths)),
        colorbar=dict(
            title=dict(text="k ha", font=dict(color="#0f172a", size=11)),
            tickfont=dict(color="#0f172a", size=11),
            thickness=14,
            len=0.75,
            x=0.98
        ),
        hovertemplate=(
            "<b>%{text} (%{location})</b> — %{customdata[0]}<br>"
            f"<b>{cause_label}</b>: %{{z:,.1f}} k ha (%{{customdata[1]:.3f}} Mha)<extra></extra>"
        )
    ))

    yr_text = f"{y0}" if y0 == y1 else f"{y0}–{y1}"
    geo_cfg = dict(
        scope=scope,
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#94a3b8",
        projection_type="natural earth" if scope == "world" else "mercator",
        bgcolor="#ffffff",
        showland=True,
        landcolor="#f1f5f9",
        showcountries=True,
        countrycolor="#e2e8f0"
    )
    if scope == "world" and len(agg) < 160:
        geo_cfg["fitbounds"] = "locations"

    return _apply_layout(
        fig,
        title=dict(text=f"Global Map of {cause_label} ({yr_text}) [Thousand Hectares]", font=dict(size=15, color="#0f172a")),
        geo=geo_cfg,
        margin=dict(l=0, r=0, t=55, b=0)
    )


def create_geopandas_country_zoom_map(gdf_world, df_panel, iso3, year=2020):
    """
    GeoPandas-powered focused polygon map zoomed to the selected country & neighboring context.
    """
    if gdf_world is None or gdf_world.empty:
        return _empty_figure("GeoJSON boundaries unavailable.")

    target_geom = gdf_world[gdf_world["ISO3166-1-Alpha-3"] == iso3]
    if target_geom.empty:
        return _empty_figure(f"Country boundary polygon not available for {iso3}.")

    df_yr = df_panel[df_panel["Year"] == year].copy()
    merged = gdf_world.merge(df_yr, left_on="ISO3166-1-Alpha-3", right_on="ISO3", how="left")
    merged["Annual_Change_Mha"] = merged["Annual_Change_Mha"].fillna(0)

    # Calculate centroid & bounding box span using GeoPandas geometry
    bounds = target_geom.total_bounds  # [minx, miny, maxx, maxy]
    lon_center = (bounds[0] + bounds[2]) / 2.0
    lat_center = (bounds[1] + bounds[3]) / 2.0
    lon_span = max(bounds[2] - bounds[0], 5.0)
    lat_span = max(bounds[3] - bounds[1], 5.0)
    span = max(lon_span, lat_span)
    # Approximate zoom level for mapbox/geo projection
    proj_scale = min(max(120.0 / span, 1.5), 14.0)

    country_label = df_yr[df_yr["ISO3"] == iso3]["Entity"].iloc[0] if not df_yr[df_yr["ISO3"] == iso3].empty else iso3

    fig = px.choropleth(
        merged,
        geojson=merged.geometry.__geo_interface__,
        locations=merged.index,
        color="Forest_Share_pct",
        hover_name="name",
        hover_data={
            "ISO3": True,
            "Forest_Area_Mha": ":.2f",
            "Annual_Change_Mha": ":+.3f",
            "Forest_Share_pct": ":.1f"
        },
        color_continuous_scale=[[0, "#f1f5f9"], [0.3, "#bae4b3"], [0.7, "#31a354"], [1.0, "#00441b"]],
        range_color=[0, 100],
        labels={"Forest_Share_pct": "Forest Share (%)"}
    )

    # Outline target country boldly
    fig.add_trace(
        go.Choropleth(
            geojson=target_geom.geometry.__geo_interface__,
            locations=target_geom.index,
            z=[1],
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            showscale=False,
            marker_line_color="#dc2626",
            marker_line_width=3.0,
            hoverinfo="skip"
        )
    )

    fig.update_geos(
        center=dict(lon=lon_center, lat=lat_center),
        projection_scale=proj_scale,
        showcoastlines=True,
        coastlinecolor="#94a3b8",
        showcountries=True,
        countrycolor="#cbd5e1",
        bgcolor="#ffffff"
    )
    return _apply_layout(
        fig,
        title=dict(text=f"Spatial Focus: {country_label} ({year})", font=dict(size=14, color="#0f172a")),
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_colorbar=dict(
            title=dict(text="Cover %", font=dict(color="#0f172a", size=11)),
            tickfont=dict(color="#0f172a", size=11),
            thickness=12,
            len=0.7
        )
    )


def create_global_trend_chart(df_global, start_year=1990, end_year=2025, title_prefix="Global", snapshot_marker=None):
    """
    Historical trajectory of forest area and net change across start_year..end_year.
    """
    df_sub = df_global[(df_global["Year"] >= start_year) & (df_global["Year"] <= end_year)].copy()
    if df_sub.empty:
        return _empty_figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sub["Year"],
        y=df_sub["Forest_Area_Mha"],
        name="Forest Area (Mha)",
        mode="lines+markers",
        line=dict(color=THEME["primary"], width=3),
        marker=dict(size=6, color=THEME["primary"]),
        fill="tozeroy",
        fillcolor="rgba(45, 106, 79, 0.08)",
        hovertemplate="<b>Year %{x}</b><br>Forest Area: %{y:,.2f} Mha<extra></extra>"
    ))

    if title_prefix == "Global" and snapshot_marker is None:
        milestones = [
            {"year": 1992, "text": "Rio Earth Summit (1992)", "y_shift": -35},
            {"year": 1997, "text": "Kyoto Protocol (1997)", "y_shift": 30},
            {"year": 2015, "text": "Paris Agreement & SDGs (2015)", "y_shift": -35},
            {"year": 2021, "text": "Glasgow Declaration (COP26)", "y_shift": 30}
        ]
        for m in milestones:
            if start_year <= m["year"] <= end_year:
                y_val = df_sub[df_sub["Year"] == m["year"]]["Forest_Area_Mha"].values
                if len(y_val) > 0:
                    fig.add_annotation(
                        x=m["year"],
                        y=y_val[0],
                        text=m["text"],
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1,
                        arrowcolor=THEME["accent"],
                        ay=m["y_shift"],
                        font=dict(size=10, color=THEME["dark_text"]),
                        bgcolor="rgba(255, 255, 255, 0.9)",
                        bordercolor=THEME["border"],
                        borderwidth=1
                    )

    _add_snapshot_vline(fig, snapshot_marker)
    title_txt = (
        f"{title_prefix} Forest Area Context (Snapshot: {snapshot_marker})"
        if snapshot_marker is not None
        else f"{title_prefix} Forest Area Trajectory ({start_year}–{end_year})"
    )
    return _apply_layout(
        fig,
        title=dict(text=title_txt, font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(title="Year", showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(title="Forest Area (Million Hectares)", showgrid=True, gridcolor="#f1f5f9"),
        hovermode="x unified"
    )


def create_gain_vs_loss_chart(df_global, entity_label="Global"):
    """
    Compares gross deforestation vs forest expansion across FAO reporting periods.
    """
    df_sub = df_global.dropna(subset=["Gross_Deforestation_Mha", "Gross_Expansion_Mha"]).copy()
    if df_sub.empty:
        return _empty_figure(f"Gross Deforestation vs. Expansion Data Not Available for {entity_label}")

    df_sub["Net_Change_Mha"] = df_sub["Gross_Expansion_Mha"] - df_sub["Gross_Deforestation_Mha"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_sub["Year"],
        y=-df_sub["Gross_Deforestation_Mha"],
        name="Gross Deforestation (Loss)",
        marker_color=THEME["loss_light"],
        hovertemplate="<b>Year %{x}</b><br>Gross Loss: %{y:.3f} Mha/yr<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df_sub["Year"],
        y=df_sub["Gross_Expansion_Mha"],
        name="Gross Expansion (Recovery)",
        marker_color=THEME["gain_light"],
        hovertemplate="<b>Year %{x}</b><br>Gross Recovery: +%{y:.3f} Mha/yr<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=df_sub["Year"],
        y=df_sub["Net_Change_Mha"],
        name="Net Forest Change",
        mode="lines+markers",
        line=dict(color=THEME["dark_text"], width=2.5, dash="dash"),
        marker=dict(size=8, color=THEME["dark_text"]),
        hovertemplate="<b>Year %{x}</b><br>Net Change: %{y:+.3f} Mha/yr<extra></extra>"
    ))

    return _apply_layout(
        fig,
        barmode="relative",
        title=dict(text=f"Gross Deforestation vs. Forest Expansion: {entity_label} (FAO FRA)", font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(title="Reporting Period Year", tickmode="array", tickvals=df_sub["Year"].tolist()),
        yaxis=dict(title="Annual Change (Mha / year)", zeroline=True, zerolinecolor="#64748b", zerolinewidth=1.5)
    )


def create_drivers_pie_chart(df_drivers, entity="World", year=2023, year_range=None):
    """
    Pie / Donut chart breakdown of dominant direct drivers of tree cover loss (Curtis et al. 2018).
    Supports single year or cumulative year_range.
    """
    df_sub = df_drivers[df_drivers["Entity"] == entity]
    if year_range:
        y0, y1 = year_range
        df_sub = df_sub[(df_sub["Year"] >= y0) & (df_sub["Year"] <= y1)]
        title_suffix = f"{y0}–{y1}" if y0 != y1 else f"{y0}"
    elif year:
        df_yr = df_sub[df_sub["Year"] == year]
        if not df_yr.empty:
            df_sub = df_yr
        title_suffix = f"{year}"
    else:
        title_suffix = "Cumulative"

    if df_sub.empty:
        return _empty_figure(f"Direct Driver Data Not Available for {entity}")

    driver_cols = [c for c in DRIVER_COLORS.keys() if c in df_sub.columns]
    totals = df_sub[driver_cols].sum()
    df_plot = pd.DataFrame({"Driver": totals.index, "Area_ha": totals.values})
    df_plot = df_plot[df_plot["Area_ha"] > 0]

    if df_plot.empty:
        return _empty_figure(f"Zero recorded driver loss for {entity} ({title_suffix})")

    fig = px.pie(
        df_plot,
        names="Driver",
        values="Area_ha",
        color="Driver",
        color_discrete_map=DRIVER_COLORS,
        hole=0.45,
        title=f"Measured Direct Drivers: {entity} ({title_suffix})"
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Area: %{value:,.0f} ha (%{percent})<extra></extra>"
    )
    return _apply_layout(
        fig,
        showlegend=True,
        title=dict(font=dict(size=14, color=THEME["primary"]))
    )


def create_drivers_stacked_bar(df_drivers, entity="World", start_year=2001, end_year=2024):
    """
    Stacked bar chart of direct drivers over time.
    """
    df_sub = df_drivers[(df_drivers["Entity"] == entity) & (df_drivers["Year"] >= start_year) & (df_drivers["Year"] <= end_year)].sort_values("Year")
    if df_sub.empty:
        return _empty_figure(f"Time-series driver data Not Available for {entity}")

    driver_cols = [
        "Permanent agriculture",
        "Logging",
        "Wildfire",
        "Shifting cultivation",
        "Settlements and infrastructure",
        "Mining and energy industry"
    ]

    fig = go.Figure()
    for col in driver_cols:
        if col in df_sub.columns:
            fig.add_trace(go.Bar(
                x=df_sub["Year"],
                y=df_sub[col] / 1e6,
                name=col,
                marker_color=DRIVER_COLORS.get(col, "#94a3b8"),
                hovertemplate=f"<b>{col}</b> (%{{x}}): %{{y:,.3f}} Mha<extra></extra>"
            ))

    return _apply_layout(
        fig,
        barmode="stack",
        title=dict(text=f"Annual Tree Cover Loss by Direct Driver: {entity} ({df_sub['Year'].min()}–{df_sub['Year'].max()})", font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(title="Year", showgrid=False),
        yaxis=dict(title="Loss Area (Million Hectares)", showgrid=True, gridcolor="#f1f5f9")
    )


def create_commodity_breakdown_chart(df_commodities, entity="World", year=2023, year_range=None):
    """
    Bar chart of deforestation attributable to agricultural commodities (Pendrill et al.).
    """
    df_sub = df_commodities[df_commodities["Entity"] == entity]
    if year_range:
        y0, y1 = year_range
        df_sub = df_sub[(df_sub["Year"] >= y0) & (df_sub["Year"] <= y1)]
        title_suffix = f"{y0}–{y1}" if y0 != y1 else f"{y0}"
    elif year:
        df_yr = df_sub[df_sub["Year"] == year]
        if not df_yr.empty:
            df_sub = df_yr
        title_suffix = f"{year}"
    else:
        title_suffix = "Latest"

    if df_sub.empty:
        return _empty_figure(f"Commodity Attribution Data Not Available for {entity}")

    comm_cols = [c for c in COMMODITY_COLORS.keys() if c in df_sub.columns]
    sums = df_sub[comm_cols].sum().reset_index()
    sums.columns = ["Commodity", "Area_ha"]
    sums = sums[sums["Area_ha"] > 0].sort_values("Area_ha", ascending=True)
    if sums.empty:
        return _empty_figure(f"No commodity-driven deforestation recorded for {entity}")

    sums["Area_k_ha"] = sums["Area_ha"] / 1000.0
    fig = px.bar(
        sums,
        x="Area_k_ha",
        y="Commodity",
        orientation="h",
        color="Commodity",
        color_discrete_map=COMMODITY_COLORS,
        title=f"Inferred Deforestation by Commodity: {entity} ({title_suffix})",
        labels={"Area_k_ha": "Area Lost (Thousand Hectares)", "Commodity": "Commodity"}
    )
    fig.update_traces(hovertemplate="<b>%{y}</b>: %{x:,.1f} thousand ha<extra></extra>")
    return _apply_layout(
        fig,
        showlegend=False,
        title=dict(font=dict(size=14, color=THEME["primary"])),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9")
    )


def create_cause_top_countries_bar(df_cause, cause_col, cause_label, year_range=(2001, 2024), top_n=12, cause_color="#dc2626"):
    """
    Top N Countries most affected by a SPECIFIC deforestation cause!
    """
    y0, y1 = year_range
    sub = df_cause[(df_cause["Code"].str.len() == 3) & (~df_cause["Code"].str.startswith("OWID", na=False))]
    sub = sub[(sub["Year"] >= y0) & (sub["Year"] <= y1)]

    if sub.empty or cause_col not in sub.columns:
        return _empty_figure(f"Data Not Available for {cause_label}")

    agg = sub.groupby(["Code", "Entity", "Continent"])[cause_col].sum().reset_index()
    total_global_cause = agg[cause_col].sum()
    if total_global_cause <= 0:
        return _empty_figure(f"Zero recorded loss for {cause_label} in selected scope")

    agg["Share_Global_Cause_pct"] = (agg[cause_col] / total_global_cause) * 100.0
    agg["Loss_Mha"] = agg[cause_col] / 1_000_000.0
    top_df = agg.sort_values(cause_col, ascending=False).head(top_n).iloc[::-1]

    fig = go.Figure(go.Bar(
        x=top_df["Loss_Mha"],
        y=top_df["Entity"],
        orientation="h",
        marker_color=cause_color,
        text=[f"{m:.2f} Mha ({s:.1f}%)" for m, s in zip(top_df["Loss_Mha"], top_df["Share_Global_Cause_pct"])],
        textposition="outside",
        customdata=np.stack([top_df["Continent"], top_df["Share_Global_Cause_pct"]], axis=-1),
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>Loss: %{x:,.3f} Mha<br>Share of Global Cause: %{customdata[1]:.1f}%<extra></extra>"
    ))
    return _apply_layout(
        fig,
        title=dict(text=f"Top {top_n} Countries Driven by {cause_label} ({y0}–{y1})", font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(title="Cumulative Tree Cover Loss (Million Hectares)", showgrid=True, gridcolor="#f1f5f9", range=[0, top_df["Loss_Mha"].max() * 1.28]),
        yaxis=dict(title="")
    )


def create_cause_trajectory_by_continent(df_cause, cause_col, cause_label, year_range=(2001, 2024), snapshot_marker=None):
    """
    Stacked area / multi-line temporal trajectory of a SPECIFIC cause broken down by Continent!
    """
    y0, y1 = year_range
    continents = ["South America", "Africa", "Asia", "North America", "Europe", "Oceania"]
    sub = df_cause[(df_cause["Code"].str.len() == 3) & (~df_cause["Code"].str.startswith("OWID", na=False))]
    sub = sub[sub["Continent"].isin(continents) & (sub["Year"] >= y0) & (sub["Year"] <= y1)]

    if sub.empty or cause_col not in sub.columns:
        return _empty_figure(f"Continental Trajectory Data Not Available for {cause_label}")

    grouped = sub.groupby(["Year", "Continent"])[cause_col].sum().reset_index()
    grouped["Loss_Mha"] = grouped[cause_col] / 1_000_000.0

    fig = px.area(
        grouped,
        x="Year",
        y="Loss_Mha",
        color="Continent",
        color_discrete_map=CONTINENT_COLORS,
        title=f"Continental Trajectory of {cause_label} ({y0}–{y1})",
        labels={"Loss_Mha": "Annual Loss (Million Hectares)"}
    )
    _add_snapshot_vline(fig, snapshot_marker)
    return _apply_layout(
        fig,
        title=dict(font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        hovermode="x unified"
    )


def create_cause_share_comparison(df_cause, cause_col, cause_label, year_range=(2001, 2024), top_n=10, cause_color="#dc2626"):
    """
    For the top countries affected by a cause, compares how much of each country's TOTAL loss
    comes from THIS specific cause vs. all other causes (100% stacked composition!).
    """
    y0, y1 = year_range
    total_col = "Total_Loss_ha" if "Total_Loss_ha" in df_cause.columns else "Total_Commodity_ha"
    sub = df_cause[(df_cause["Code"].str.len() == 3) & (~df_cause["Code"].str.startswith("OWID", na=False))]
    sub = sub[(sub["Year"] >= y0) & (sub["Year"] <= y1)]

    if sub.empty or cause_col not in sub.columns:
        return _empty_figure()

    agg = sub.groupby(["Code", "Entity"]).agg({cause_col: "sum", total_col: "sum"}).reset_index()
    agg = agg[agg[total_col] > 0].sort_values(cause_col, ascending=False).head(top_n)
    agg["Cause_Pct"] = (agg[cause_col] / agg[total_col]) * 100.0
    agg["Other_Pct"] = 100.0 - agg["Cause_Pct"]
    agg = agg.sort_values("Cause_Pct", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=agg["Entity"],
        x=agg["Cause_Pct"],
        name=cause_label,
        orientation="h",
        marker_color=cause_color,
        text=[f"{v:.1f}%" for v in agg["Cause_Pct"]],
        textposition="inside",
        hovertemplate="<b>%{y}</b><br>" + cause_label + ": %{x:.1f}% of national loss<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        y=agg["Entity"],
        x=agg["Other_Pct"],
        name="All Other Causes",
        orientation="h",
        marker_color="#e2e8f0",
        hovertemplate="<b>%{y}</b><br>Other Causes: %{x:.1f}%<extra></extra>"
    ))

    return _apply_layout(
        fig,
        barmode="stack",
        title=dict(text=f"Share of National Loss Attributable to {cause_label} ({y0}–{y1})", font=dict(size=14, color=THEME["primary"])),
        xaxis=dict(title="Share of Total National Tree Cover Loss (%)", range=[0, 100]),
        yaxis=dict(title="")
    )


def create_top_countries_bar(df_hotspots, top_n=10, ascending=True):
    """
    Horizontal bar chart showing top deforested or reforested countries.
    """
    if df_hotspots.empty:
        return _empty_figure()

    if ascending:
        df_top = df_hotspots[df_hotspots["Net_Change_1990_to_Latest_Mha"] < 0].sort_values("Net_Change_1990_to_Latest_Mha").head(top_n).copy()
        title = f"Top {len(df_top)} Countries with Highest Cumulative Forest Loss"
        color_seq = [THEME["loss_red"]] * len(df_top)
        x_label = "Net Forest Loss (Million Hectares)"
    else:
        df_top = df_hotspots[df_hotspots["Net_Change_1990_to_Latest_Mha"] > 0].sort_values("Net_Change_1990_to_Latest_Mha", ascending=False).head(top_n).copy()
        title = f"Top {len(df_top)} Countries with Highest Forest Expansion (Gainers)"
        color_seq = [THEME["gain_green"]] * len(df_top)
        x_label = "Net Forest Expansion (Million Hectares)"

    if df_top.empty:
        return _empty_figure("No countries match this loss/gain direction in the filtered scope.")

    df_top = df_top.iloc[::-1]
    x_col = "Net_Change_1990_to_Latest_Mha"

    fig = go.Figure(go.Bar(
        x=df_top[x_col],
        y=df_top["Entity"],
        orientation="h",
        marker=dict(color=color_seq),
        text=[f"{val:+.1f} Mha ({pct:+.1f}%)" for val, pct in zip(df_top[x_col], df_top["Pct_Change_Since_1990"])],
        textposition="outside",
        customdata=np.stack([df_top["Continent"], df_top.get("Dominant_Driver", pd.Series(["N/A"]*len(df_top)))], axis=-1),
        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>Net Change: %{x:+.2f} Mha<br>Primary Driver: %{customdata[1]}<extra></extra>"
    ))

    x_min = min(df_top[x_col].min() * 1.32, 0) if ascending else 0
    x_max = 0 if ascending else df_top[x_col].max() * 1.32

    return _apply_layout(
        fig,
        title=dict(text=title, font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(title=x_label, showgrid=True, gridcolor="#f1f5f9", range=[x_min, x_max]),
        yaxis=dict(title="")
    )


def create_top_countries_annual_bar(df_panel, year, top_n=10, ascending=True, df_hotspots=None):
    """
    Horizontal bar chart ranking countries by SINGLE-YEAR Annual Net Change in a Snapshot Year.
    """
    if year == 1990:
        return _empty_figure("Annual forest change rates begin in 1991 (1990 is the baseline inventory year).")

    sub = df_panel[df_panel["Year"] == year].dropna(subset=["Annual_Change_Mha"]).copy()
    if sub.empty:
        return _empty_figure(f"Data Not Available for Snapshot Year {year}")

    if df_hotspots is not None and "Dominant_Driver" in df_hotspots.columns:
        sub = sub.merge(df_hotspots[["ISO3", "Dominant_Driver"]], on="ISO3", how="left")
    else:
        sub["Dominant_Driver"] = "Data Not Available"
    sub["Dominant_Driver"] = sub["Dominant_Driver"].fillna("Data Not Available")
    sub["Annual_Pct"] = np.where(sub["Forest_Area_ha"] > 0, (sub["Annual_Change_ha"] / sub["Forest_Area_ha"]) * 100.0, 0.0)

    if ascending:
        df_top = sub[sub["Annual_Change_Mha"] < 0].sort_values("Annual_Change_Mha").head(top_n).copy()
        title = f"Top {len(df_top)} Countries by Annual Forest Loss ({year})"
        color_seq = [THEME["loss_red"]] * len(df_top)
        x_label = f"Annual Net Loss in {year} (Mha/yr)"
    else:
        df_top = sub[sub["Annual_Change_Mha"] > 0].sort_values("Annual_Change_Mha", ascending=False).head(top_n).copy()
        title = f"Top {len(df_top)} Countries by Annual Forest Gain ({year})"
        color_seq = [THEME["gain_green"]] * len(df_top)
        x_label = f"Annual Net Expansion in {year} (Mha/yr)"

    if df_top.empty:
        return _empty_figure(f"No countries match this loss/gain direction in {year}.")

    df_top = df_top.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=df_top["Annual_Change_Mha"].tolist(),
        y=df_top["Entity"].tolist(),
        orientation="h",
        marker=dict(color=color_seq),
        text=[f"{val:+.3f} Mha/yr ({pct:+.2f}%)" for val, pct in zip(df_top["Annual_Change_Mha"], df_top["Annual_Pct"])],
        textposition="outside",
        customdata=np.stack([df_top["Continent"], df_top["Dominant_Driver"]], axis=-1).tolist(),
        hovertemplate=f"<b>%{{y}}</b> (%{{customdata[0]}})<br>Annual Change ({year}): %{{x:+.3f}} Mha/yr<br>Primary Driver: %{{customdata[1]}}<extra></extra>"
    ))

    x_min = min(float(df_top["Annual_Change_Mha"].min()) * 1.35, 0) if ascending else 0
    x_max = 0 if ascending else float(df_top["Annual_Change_Mha"].max()) * 1.35

    return _apply_layout(
        fig,
        title=dict(text=title, font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(title=x_label, showgrid=True, gridcolor="#f1f5f9", range=[x_min, x_max]),
        yaxis=dict(title="")
    )


def create_regional_comparison_chart(df_reg, metric="Forest_Area_Mha", start_year=1990, end_year=2025, snapshot_marker=None):
    """
    Multi-line regional comparison across Africa, Asia, Europe, North America, South America, Oceania.
    """
    df_sub = df_reg[(df_reg["Year"] >= start_year) & (df_reg["Year"] <= end_year)].copy()
    if df_sub.empty:
        return _empty_figure()

    metric_labels = {
        "Forest_Area_Mha": "Total Forest Area (Million Hectares)",
        "Annual_Change_Mha": "Annual Net Forest Change (Million Hectares / yr)",
        "Forest_Share_pct": "Area-Weighted Forest Share (% of Land Area)",
        "CO2_Emissions_Mt": "Annual CO₂ Emissions from Land-Use Change (Mt CO₂)"
    }

    fig = px.line(
        df_sub,
        x="Year",
        y=metric,
        color="Continent",
        markers=True,
        title=f"Continental Forest Dynamics ({start_year}–{end_year}): {metric_labels.get(metric, metric)}",
        labels={"Year": "Year", metric: metric_labels.get(metric, metric)},
        color_discrete_map=CONTINENT_COLORS
    )
    _add_snapshot_vline(fig, snapshot_marker)
    return _apply_layout(
        fig,
        title=dict(font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        hovermode="x unified"
    )


def create_country_deep_dive_chart(df_panel, iso3="BRA", start_year=1990, end_year=2025, snapshot_marker=None):
    """
    Dual-axis historical trajectory for a specific selected country.
    """
    df_c = df_panel[(df_panel["ISO3"] == iso3) & (df_panel["Year"] >= start_year) & (df_panel["Year"] <= end_year)].sort_values("Year")
    if df_c.empty:
        return _empty_figure(f"Historical Data Not Available for {iso3}")

    country_name = df_c["Entity"].iloc[0]
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_c["Year"],
        y=df_c["Forest_Area_Mha"],
        name="Forest Area (Mha)",
        mode="lines+markers",
        line=dict(color=THEME["primary"], width=3),
        hovertemplate="<b>%{x}</b><br>Forest Area: %{y:,.3f} Mha<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df_c["Year"],
        y=df_c["Annual_Change_Mha"],
        name="Annual Net Change (Mha/yr)",
        marker=dict(color=np.where(df_c["Annual_Change_Mha"] < 0, THEME["loss_light"], THEME["gain_light"])),
        yaxis="y2",
        opacity=0.55,
        hovertemplate="<b>%{x}</b><br>Annual Net Change: %{y:+.4f} Mha/yr<extra></extra>"
    ))

    _add_snapshot_vline(fig, snapshot_marker)
    title_txt = (
        f"Historical Forest Trajectory: {country_name} ({iso3}) [Snapshot: {snapshot_marker}]"
        if snapshot_marker is not None
        else f"Historical Forest Trajectory: {country_name} ({iso3}) [{start_year}–{end_year}]"
    )
    return _apply_layout(
        fig,
        title=dict(text=title_txt, font=dict(size=15, color="#0f172a")),
        xaxis=dict(title="Year", showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(title="Forest Area (Million Hectares)", side="left", showgrid=True, gridcolor="#f1f5f9"),
        yaxis2=dict(title="Annual Net Change (Mha/yr)", side="right", overlaying="y", showgrid=False)
    )


def create_country_comparison_lines(df_panel, iso3_list, metric="Forest_Area_Mha", normalize=False, start_year=1990, end_year=2025, snapshot_marker=None):
    """
    Compare multiple countries side-by-side (normalized to Start Year = 100 or absolute).
    """
    sub = df_panel[(df_panel["ISO3"].isin(iso3_list)) & (df_panel["Year"] >= start_year) & (df_panel["Year"] <= end_year)].sort_values("Year").copy()
    if sub.empty:
        return _empty_figure("Select at least one country with available data.")

    if normalize and metric == "Forest_Area_Mha":
        bases = sub.groupby("ISO3")[metric].transform("first")
        sub["Normalized_Index"] = np.where(bases > 0, (sub[metric] / bases) * 100.0, np.nan)
        y_col = "Normalized_Index"
        y_label = f"Forest Area Index ({start_year} = 100)"
        title = f"Multi-Country Relative Forest Trajectory ({start_year} = 100)"
    else:
        y_col = metric
        label_map = {
            "Forest_Area_Mha": "Forest Area (Mha)",
            "Annual_Change_Mha": "Annual Net Change (Mha/yr)",
            "Forest_Share_pct": "Forest Cover Share (% of Land)",
            "CO2_Emissions_Mt": "Land-Use CO₂ Emissions (Mt/yr)"
        }
        y_label = label_map.get(metric, metric)
        title = f"Multi-Country Comparison: {y_label} ({start_year}–{end_year})"

    fig = px.line(
        sub,
        x="Year",
        y=y_col,
        color="Entity",
        markers=True,
        title=title,
        labels={y_col: y_label}
    )
    if normalize and metric == "Forest_Area_Mha":
        fig.add_hline(y=100, line_dash="dot", line_color="#64748b", annotation_text="Baseline (100)")

    _add_snapshot_vline(fig, snapshot_marker)
    return _apply_layout(
        fig,
        title=dict(font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        hovermode="x unified"
    )


def create_country_cause_radar(df_drivers, iso3_list, year_range=(2001, 2024)):
    """
    Spider / Radar chart comparing normalized (%) direct driver fingerprints across multiple countries!
    """
    y0, y1 = year_range
    driver_cols = [
        "Permanent agriculture",
        "Logging",
        "Wildfire",
        "Shifting cultivation",
        "Settlements and infrastructure",
        "Mining and energy industry"
    ]
    sub = df_drivers[(df_drivers["Code"].isin(iso3_list)) & (df_drivers["Year"] >= y0) & (df_drivers["Year"] <= y1)]
    if sub.empty:
        return _empty_figure("Driver fingerprint Not Available for selected countries.")

    agg = sub.groupby(["Code", "Entity"])[driver_cols].sum().reset_index()
    fig = go.Figure()

    short_labels = ["Permanent Ag.", "Logging", "Wildfire", "Shifting Cult.", "Urban/Infra", "Mining/Energy"]
    for _, row in agg.iterrows():
        tot = sum(row[c] for c in driver_cols)
        if tot <= 0:
            continue
        pcts = [(row[c] / tot) * 100.0 for c in driver_cols]
        # Close polygon loop
        pcts_closed = pcts + [pcts[0]]
        labels_closed = short_labels + [short_labels[0]]
        fig.add_trace(go.Scatterpolar(
            r=pcts_closed,
            theta=labels_closed,
            fill="toself",
            name=row["Entity"],
            opacity=0.65,
            hovertemplate="<b>%{theta}</b>: %{r:.1f}%<extra>" + row["Entity"] + "</extra>"
        ))

    if len(fig.data) == 0:
        return _empty_figure("No tree cover loss recorded across selected countries.")

    return _apply_layout(
        fig,
        title=dict(text=f"Normalized Deforestation Driver Fingerprint (%) [{y0}–{y1}]", font=dict(size=14, color=THEME["primary"])),
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%"))
    )


def create_country_heatmap(df_cause, cause_col, cause_label, iso3_list=None, year_range=(2001, 2024), top_n=15):
    """
    Country × Year Intensity Heatmap revealing exact annual deforestation/wildfire spikes!
    """
    y0, y1 = year_range
    sub = df_cause[(df_cause["Code"].str.len() == 3) & (~df_cause["Code"].str.startswith("OWID", na=False))]
    sub = sub[(sub["Year"] >= y0) & (sub["Year"] <= y1)]
    if iso3_list:
        sub = sub[sub["Code"].isin(iso3_list)]
    if sub.empty or cause_col not in sub.columns:
        return _empty_figure(f"Heatmap Data Not Available for {cause_label}")

    top_entities = sub.groupby("Entity")[cause_col].sum().sort_values(ascending=False).head(top_n).index.tolist()
    sub_top = sub[sub["Entity"].isin(top_entities)]
    pivot = sub_top.pivot_table(index="Entity", columns="Year", values=cause_col, aggfunc="sum").fillna(0) / 1000.0
    # Order top-down
    pivot = pivot.loc[top_entities]

    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=[[0.0, "#f8fafc"], [0.2, "#fde68a"], [0.6, "#f97316"], [1.0, "#991b1b"]],
        labels=dict(x="Year", y="Country", color="Loss (k ha)"),
        title=f"Annual Intensity Heatmap: {cause_label} (Top {len(pivot)} Countries, Thousand ha)"
    )
    return _apply_layout(
        fig,
        title=dict(font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(dtick=2),
        height=max(420, 28 * len(pivot) + 120)
    )


def create_forest_vs_emissions_scatter(df_panel, year=2020):
    """
    Interactive Bubble Plot: Annual Net Change vs. CO2 Land-Use Emissions, sized by Forest Area.
    """
    sub = df_panel[(df_panel["Year"] == year) & (df_panel["Forest_Area_Mha"] > 0.5)].dropna(
        subset=["Annual_Change_Mha", "CO2_Emissions_Mt", "Forest_Area_Mha"]
    ).copy()
    if sub.empty:
        return _empty_figure(f"Scatter data Not Available for {year}")

    fig = px.scatter(
        sub,
        x="Annual_Change_Mha",
        y="CO2_Emissions_Mt",
        size="Forest_Area_Mha",
        color="Continent",
        hover_name="Entity",
        size_max=55,
        color_discrete_map=CONTINENT_COLORS,
        title=f"Country Forest Change vs. Land-Use CO₂ Emissions ({year}) [Bubble Size = Total Forest Area]",
        labels={
            "Annual_Change_Mha": "Annual Net Forest Change (Mha/yr)",
            "CO2_Emissions_Mt": "Land-Use CO₂ Emissions (Mt CO₂/yr)",
            "Forest_Area_Mha": "Total Forest Area (Mha)"
        },
        hover_data={"ISO3": True, "Forest_Share_pct": ":.1f"}
    )
    fig.add_vline(x=0, line_dash="dash", line_color="#64748b", opacity=0.7)
    fig.add_hline(y=0, line_dash="dash", line_color="#64748b", opacity=0.7)
    return _apply_layout(
        fig,
        title=dict(font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9")
    )


def create_country_treemap(df_hotspots, mode="loss"):
    """
    Hierarchical Treemap (Continent -> Country) of Cumulative Forest Loss or Expansion (1990–2025).
    """
    if mode == "loss":
        sub = df_hotspots[df_hotspots["Net_Change_1990_to_Latest_Mha"] < -0.05].copy()
        sub["Abs_Mha"] = sub["Net_Change_1990_to_Latest_Mha"].abs()
        title = "Global Deforestation Treemap: Share of Cumulative Forest Loss by Continent & Country"
        scale = [[0, "#fee2e2"], [0.4, "#f87171"], [1, "#991b1b"]]
    elif mode == "gain":
        sub = df_hotspots[df_hotspots["Net_Change_1990_to_Latest_Mha"] > 0.05].copy()
        sub["Abs_Mha"] = sub["Net_Change_1990_to_Latest_Mha"]
        title = "Global Reforestation Treemap: Share of Net Forest Expansion by Continent & Country"
        scale = [[0, "#dcfce7"], [0.4, "#4ade80"], [1, "#14532d"]]
    else:
        sub = df_hotspots[df_hotspots["Forest_Area_Latest_ha"] > 0].copy()
        sub["Abs_Mha"] = sub["Forest_Area_Latest_ha"] / 1_000_000.0
        title = "Global Forest Stock Treemap: Current Total Forest Area by Continent & Country"
        scale = [[0, "#e2e8f0"], [0.4, "#52b788"], [1, "#1b4332"]]

    if sub.empty:
        return _empty_figure()

    fig = px.treemap(
        sub,
        path=[px.Constant("World"), "Continent", "Entity"],
        values="Abs_Mha",
        color="Abs_Mha",
        color_continuous_scale=scale,
        hover_data={"Pct_Change_Since_1990": ":.1f", "Dominant_Driver": True},
        title=title
    )
    fig.update_traces(
        textinfo="label+value+percent parent",
        hovertemplate="<b>%{label}</b><br>Area: %{value:,.2f} Mha<br>Share of Parent: %{percentParent:.1%}<extra></extra>"
    )
    return _apply_layout(
        fig,
        title=dict(font=dict(size=15, color=THEME["primary"])),
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=45, b=10)
    )


def create_slope_dumbbell_chart(df_hotspots, top_n=12, start_label=1990, end_label=2025):
    """
    Dumbbell chart comparing start_label vs. end_label Forest Area for top changing countries.
    """
    sub = df_hotspots.copy()
    sub["Abs_Change"] = sub["Net_Change_1990_to_Latest_Mha"].abs()
    top_df = sub.sort_values("Abs_Change", ascending=False).head(top_n).sort_values("Net_Change_1990_to_Latest_Mha")
    if top_df.empty or top_df["Abs_Change"].max() == 0:
        return _empty_figure(f"No net difference between {start_label} and {end_label}.")

    fig = go.Figure()
    for _, row in top_df.iterrows():
        a90 = row["Forest_Area_1990_ha"] / 1e6
        alat = row["Forest_Area_Latest_ha"] / 1e6
        color = THEME["loss_red"] if alat < a90 else THEME["gain_green"]
        fig.add_trace(go.Scatter(
            x=[a90, alat],
            y=[row["Entity"], row["Entity"]],
            mode="lines",
            line=dict(color=color, width=3),
            showlegend=False,
            hoverinfo="skip"
        ))

    fig.add_trace(go.Scatter(
        x=top_df["Forest_Area_1990_ha"] / 1e6,
        y=top_df["Entity"],
        mode="markers",
        name=f"{start_label} Forest Area",
        marker=dict(color="#64748b", size=10, symbol="circle"),
        hovertemplate=f"<b>%{{y}}</b> ({start_label}): %{{x:,.1f}} Mha<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=top_df["Forest_Area_Latest_ha"] / 1e6,
        y=top_df["Entity"],
        mode="markers",
        name=f"{end_label} Forest Area",
        marker=dict(color=THEME["primary"], size=11, symbol="diamond"),
        hovertemplate=f"<b>%{{y}}</b> ({end_label}): %{{x:,.1f}} Mha<extra></extra>"
    ))

    return _apply_layout(
        fig,
        title=dict(text=f"Forest Shift Dumbbell ({start_label} vs. {end_label}): Top {top_n} Largest Absolute Shifts", font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(title="Total Forest Area (Million Hectares)", showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(title="")
    )


def create_environmental_impact_chart(df_global, start_year=1990, end_year=2024, title_prefix="Global", snapshot_marker=None):
    """
    Environmental impact: CO2 emissions from land-use change across start_year..end_year.
    """
    df_sub = df_global[(df_global["Year"] >= start_year) & (df_global["Year"] <= end_year)].dropna(subset=["CO2_Emissions_Gt"]).copy()
    if df_sub.empty:
        return _empty_figure(f"Land-use CO₂ Emissions Data Not Available for {title_prefix}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sub["Year"],
        y=df_sub["CO2_Emissions_Gt"],
        name="CO₂ Emissions from Land-Use Change (Gt CO₂/yr)",
        mode="lines+markers",
        line=dict(color="#ea580c", width=2.5),
        marker=dict(size=6, color="#ea580c"),
        fill="tozeroy",
        fillcolor="rgba(234, 88, 12, 0.08)",
        hovertemplate="<b>Year %{x}</b><br>Emissions: %{y:.2f} Gt CO₂/yr<extra></extra>"
    ))

    _add_snapshot_vline(fig, snapshot_marker)
    return _apply_layout(
        fig,
        title=dict(text=f"{title_prefix} Land-Use CO₂ Emissions ({df_sub['Year'].min()}–{df_sub['Year'].max()})", font=dict(size=15, color=THEME["primary"])),
        xaxis=dict(title="Year", showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(title="Annual Emissions (Gigatonnes CO₂ / year)", showgrid=True, gridcolor="#f1f5f9"),
        hovermode="x unified"
    )
