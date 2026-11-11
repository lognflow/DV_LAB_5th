"""
Dashboard and Notebook Analytics Utilities
Provides shared calculations, metrics, formatting, cause mappings,
and consistent styling for the Global Deforestation Analysis project.
"""

import os
import json
import pandas as pd
import numpy as np
import geopandas as gpd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

# Premium Forest Green Color Palette
THEME = {
    "primary": "#1b4332",       # Deep Forest Green
    "secondary": "#2d6a4f",     # Emerald Forest
    "accent": "#40916c",        # Medium Green
    "light_green": "#74c69d",   # Light Sage Green
    "pale_green": "#d8f3dc",    # Pale Green tint
    "loss_red": "#b91c1c",      # Deforestation Red
    "loss_light": "#ef4444",    # Light Deforestation Red
    "gain_green": "#15803d",    # Recovery Green
    "gain_light": "#22c55e",    # Light Recovery Green
    "warning_amber": "#d97706", # Warning Amber
    "fire_orange": "#ea580c",   # Wildfire Orange
    "dark_text": "#0f172a",     # Slate dark text
    "muted_text": "#475569",    # Muted Slate text
    "card_bg": "#ffffff",       # White card background
    "bg_subtle": "#f8fafc",     # Off-white / light slate background
    "border": "#e2e8f0"         # Border color
}

CONTINENT_COLORS = {
    "Africa": "#d97706",
    "Asia": "#0284c7",
    "Europe": "#059669",
    "North America": "#7c3aed",
    "South America": "#dc2626",
    "Oceania": "#0d9488",
    "Other": "#64748b"
}

DRIVER_COLORS = {
    "Permanent agriculture": "#dc2626",
    "Logging": "#059669",
    "Wildfire": "#ea580c",
    "Shifting cultivation": "#eab308",
    "Settlements and infrastructure": "#6366f1",
    "Mining and energy industry": "#475569",
    "Other natural disturbances": "#94a3b8"
}

COMMODITY_COLORS = {
    "Beef": "#b91c1c",
    "Forestry (paper and wood)": "#15803d",
    "Palm oil": "#d97706",
    "Soy": "#ca8a04",
    "Cocoa and coffee": "#7c2d12",
    "Cereals": "#eab308",
    "Roots and tubers": "#a16207",
    "Other crops": "#64748b"
}

COMMODITY_DISPLAY_NAMES = {
    "Beef": "Cattle (Beef, Leather & Pasture)"
}

# Mapping UI Cause options to exact dataset source, column name, color, and scientific classification
CAUSE_METADATA = {
    "All Causes": {
        "dataset": "drivers",
        "column": "Total_Loss_ha",
        "label": "All Measured Physical Causes",
        "category": "All",
        "years": (2001, 2024),
        "color": "#1b4332",
        "methodology": "Measured 30m Landsat satellite tree cover loss across all 7 Curtis et al. (2018) driver categories."
    },
    "Permanent Agriculture": {
        "dataset": "drivers",
        "column": "Permanent agriculture",
        "label": "Permanent Agriculture (Measured)",
        "category": "Direct Physical Driver",
        "years": (2001, 2024),
        "color": "#dc2626",
        "methodology": "Directly measured satellite conversion of forest to permanent croplands or grazing pastures."
    },
    "Commercial Forestry & Logging": {
        "dataset": "drivers",
        "column": "Logging",
        "label": "Commercial Forestry & Logging (Measured)",
        "category": "Direct Physical Driver",
        "years": (2001, 2024),
        "color": "#059669",
        "methodology": "Directly measured rotational timber harvesting and plantation forestry operations."
    },
    "Wildfire": {
        "dataset": "drivers",
        "column": "Wildfire",
        "label": "Wildfire & Forest Fires (Measured)",
        "category": "Direct Physical Driver",
        "years": (2001, 2024),
        "color": "#ea580c",
        "methodology": "Directly measured forest canopy loss from natural or human-ignited wildfires without land-use conversion."
    },
    "Shifting Cultivation": {
        "dataset": "drivers",
        "column": "Shifting cultivation",
        "label": "Shifting Cultivation (Measured)",
        "category": "Direct Physical Driver",
        "years": (2001, 2024),
        "color": "#eab308",
        "methodology": "Directly measured small-scale rotational slash-and-burn agriculture followed by fallow regrowth."
    },
    "Urban & Infrastructure": {
        "dataset": "drivers",
        "column": "Settlements and infrastructure",
        "label": "Urbanization & Infrastructure (Measured)",
        "category": "Direct Physical Driver",
        "years": (2001, 2024),
        "color": "#6366f1",
        "methodology": "Directly measured clearing for urban expansion, roads, dams, and built infrastructure."
    },
    "Mining & Energy": {
        "dataset": "drivers",
        "column": "Mining and energy industry",
        "label": "Mining & Energy Extraction (Measured)",
        "category": "Direct Physical Driver",
        "years": (2001, 2024),
        "color": "#475569",
        "methodology": "Directly measured tree cover loss caused by surface mining, quarries, and energy pipelines/sites."
    },
    "Commodity: Beef (Cattle Ranching)": {
        "dataset": "commodities",
        "column": "Beef",
        "label": "Cattle (Beef, Leather & Pasture — Inferred)",
        "category": "Inferred Commodity Attribution",
        "years": (2001, 2023),
        "color": "#b91c1c",
        "methodology": "Econometric attribution (OWID / Singh et al. 2026 & Pendrill et al.) allocating pasture/grazing, leather, and cattle land-use footprint overlap."
    },
    "Commodity: Palm Oil": {
        "dataset": "commodities",
        "column": "Palm oil",
        "label": "Oil Palm Plantations (Inferred)",
        "category": "Inferred Commodity Attribution",
        "years": (2001, 2023),
        "color": "#d97706",
        "methodology": "Econometric attribution linking spatial forest clearance to oil palm cultivation (predominantly SE Asia)."
    },
    "Commodity: Soy": {
        "dataset": "commodities",
        "column": "Soy",
        "label": "Soybean Expansion (Inferred)",
        "category": "Inferred Commodity Attribution",
        "years": (2001, 2023),
        "color": "#ca8a04",
        "methodology": "Econometric attribution linking spatial deforestation to mechanized soybean expansion."
    },
    "Commodity: Cocoa & Coffee": {
        "dataset": "commodities",
        "column": "Cocoa and coffee",
        "label": "Cocoa & Coffee Cash Crops (Inferred)",
        "category": "Inferred Commodity Attribution",
        "years": (2001, 2023),
        "color": "#7c2d12",
        "methodology": "Econometric attribution linking forest loss to tropical cocoa and coffee cultivation."
    },
    "Commodity: Forestry (Paper & Wood)": {
        "dataset": "commodities",
        "column": "Forestry (paper and wood)",
        "label": "Timber, Paper & Wood Fiber (Inferred)",
        "category": "Inferred Commodity Attribution",
        "years": (2001, 2023),
        "color": "#15803d",
        "methodology": "Econometric attribution linking deforestation to pulpwood and commercial forestry expansion."
    }
}

PLOTLY_LAYOUT = dict(
    template="plotly_white",
    font=dict(family="Inter, Segoe UI, Arial, sans-serif", color="#0f172a", size=12),
    plot_bgcolor="#ffffff",
    paper_bgcolor="#ffffff",
    margin=dict(l=55, r=40, t=70, b=70),
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.18,
        xanchor="center",
        x=0.5,
        font=dict(size=12, color="#0f172a"),
        bgcolor="rgba(255,255,255,0)"
    ),
    hoverlabel=dict(
        bgcolor="#0f172a",
        bordercolor="#1b4332",
        font_size=13,
        font_color="#ffffff",
        font_family="Inter, Segoe UI, sans-serif"
    )
)


def load_processed_data():
    """Load all processed datasets into a dictionary."""
    data = {}
    data["country_panel"] = pd.read_csv(os.path.join(DATA_DIR, "country_forest_panel.csv"))
    data["global_summary"] = pd.read_csv(os.path.join(DATA_DIR, "global_forest_summary.csv"))
    data["regional"] = pd.read_csv(os.path.join(DATA_DIR, "regional_comparison.csv"))
    data["drivers"] = pd.read_csv(os.path.join(DATA_DIR, "deforestation_drivers_processed.csv"))
    data["commodities"] = pd.read_csv(os.path.join(DATA_DIR, "commodity_drivers_processed.csv"))
    data["hotspots"] = pd.read_csv(os.path.join(DATA_DIR, "country_hotspots.csv"))

    with open(os.path.join(DATA_DIR, "metadata_sources.json"), "r", encoding="utf-8") as f:
        data["metadata"] = json.load(f)

    return data


def load_world_geodata():
    """Load Natural Earth / ISO3 country boundaries via GeoPandas."""
    geojson_path = os.path.join(RAW_DIR, "countries.geojson")
    if os.path.exists(geojson_path):
        gdf = gpd.read_file(geojson_path)
        return gdf
    return None


def convert_area(val_ha, unit_choice="Million Hectares (Mha)"):
    """Convert a value in hectares to the selected display unit and suffix."""
    if pd.isna(val_ha) or val_ha is None:
        return None, ""
    if "Million" in unit_choice:
        return val_ha / 1_000_000.0, "Mha"
    elif "Square" in unit_choice:
        return val_ha / 100.0, "km²"
    return val_ha, "ha"


def format_area_value(val_ha, unit_choice="Million Hectares (Mha)", signed=False, decimals=2):
    """Format an area value in hectares according to unit_choice."""
    if pd.isna(val_ha) or val_ha is None:
        return "Data Not Available"
    converted, suffix = convert_area(val_ha, unit_choice)
    if suffix == "ha":
        fmt = f"{{:{'+' if signed else ''},.0f}} {suffix}"
    elif suffix == "km²":
        fmt = f"{{:{'+' if signed else ''},.0f}} {suffix}" if abs(converted) >= 100 else f"{{:{'+' if signed else ''},.{decimals}f}} {suffix}"
    else:
        fmt = f"{{:{'+' if signed else ''},.{decimals}f}} {suffix}"
    return fmt.format(converted)


def format_metric(val, unit="ha", decimals=2):
    """Format large numbers into human-readable strings."""
    if pd.isna(val) or val is None:
        return "Data Not Available"

    sign = "+" if val > 0 else ""
    abs_val = abs(val)

    if unit == "ha":
        if abs_val >= 1_000_000_000:
            return f"{sign}{val / 1_000_000_000:.{decimals}f} B ha"
        elif abs_val >= 1_000_000:
            return f"{sign}{val / 1_000_000:.{decimals}f} M ha"
        elif abs_val >= 1_000:
            return f"{sign}{val / 1_000:.{decimals}f} k ha"
        return f"{sign}{val:,.0f} ha"

    elif unit == "sqkm":
        if abs_val >= 1_000_000:
            return f"{sign}{val / 1_000_000:.{decimals}f} M km²"
        elif abs_val >= 1_000:
            return f"{sign}{val / 1_000:.{decimals}f} k km²"
        return f"{sign}{val:,.0f} km²"

    elif unit == "pct":
        return f"{val:.{decimals}f}%"

    elif unit == "co2":
        if abs_val >= 1_000_000_000:
            return f"{val / 1_000_000_000:.{decimals}f} Gt CO₂"
        elif abs_val >= 1_000_000:
            return f"{val / 1_000_000:.{decimals}f} Mt CO₂"
        return f"{val:,.0f} t CO₂"

    return f"{val:,.{decimals}f}"


def get_global_kpis(df_global, target_year=2025):
    """Compute KPI dictionary for global overview (kept backward-compatible)."""
    row = df_global[df_global["Year"] == target_year]
    if row.empty:
        row = df_global.iloc[[-1]]
    r = row.iloc[0]

    base_row = df_global[df_global["Year"] == 1990].iloc[0]

    forest_area_latest = r["Forest_Area_ha"]
    forest_area_1990 = base_row["Forest_Area_ha"]
    net_change_since_1990 = forest_area_latest - forest_area_1990
    pct_net_change = (net_change_since_1990 / forest_area_1990) * 100.0

    annual_change = r["Annual_Change_ha"]
    forest_share = r["Forest_Share_pct"]
    co2_emissions = r["CO2_Emissions_tonnes"]

    defor_latest = df_global.dropna(subset=["Gross_Deforestation_ha"]).iloc[-1]
    gross_loss_latest = defor_latest["Gross_Deforestation_ha"]
    exp_latest = df_global.dropna(subset=["Gross_Expansion_ha"]).iloc[-1]
    gross_gain_latest = exp_latest["Gross_Expansion_ha"]

    return {
        "target_year": int(r["Year"]),
        "forest_area_ha": forest_area_latest,
        "forest_area_sqkm": r["Forest_Area_sqkm"],
        "forest_area_mha": r["Forest_Area_Mha"],
        "net_change_since_1990_ha": net_change_since_1990,
        "net_change_since_1990_mha": net_change_since_1990 / 1e6,
        "net_change_since_1990_sqkm": net_change_since_1990 / 100,
        "pct_net_change_since_1990": pct_net_change,
        "annual_rate_ha": annual_change,
        "annual_rate_mha": annual_change / 1e6,
        "forest_share_pct": forest_share,
        "co2_emissions_tonnes": co2_emissions,
        "co2_emissions_gt": r["CO2_Emissions_Gt"],
        "gross_loss_ha": gross_loss_latest,
        "gross_gain_ha": gross_gain_latest,
        "gross_reported_year": int(defor_latest["Year"])
    }


def compute_dynamic_kpis(df_panel, df_drivers, df_comm, start_year, end_year, continents, country_name="All Countries", selected_cause="All Causes", time_mode="range", snapshot_year=None):
    """
    Compute fully reactive KPIs based on Time Mode ('range' or 'snapshot'),
    Continent filter, Focus Country, and Cause filter.
    """
    if country_name != "All Countries":
        scope_df = df_panel[df_panel["Entity"] == country_name].copy()
        scope_label = country_name
        iso3 = scope_df["ISO3"].iloc[0] if not scope_df.empty else None
    else:
        scope_df = df_panel[df_panel["Continent"].isin(continents)].copy()
        scope_label = "Global" if len(continents) == 6 else ", ".join(continents)
        iso3 = None

    if time_mode == "snapshot":
        target_yr = snapshot_year if snapshot_year is not None else end_year
        y_start = target_yr
        y_end = target_yr
    else:
        target_yr = end_year
        y_start = start_year
        y_end = end_year

    df_start = scope_df[scope_df["Year"] == y_start]
    df_end = scope_df[scope_df["Year"] == y_end]

    area_start = df_start["Forest_Area_ha"].sum() if not df_start.empty else np.nan
    area_end = df_end["Forest_Area_ha"].sum() if not df_end.empty else np.nan
    annual_rate_end = df_end["Annual_Change_ha"].sum() if (not df_end.empty and df_end["Annual_Change_ha"].notna().any()) else np.nan

    if time_mode == "snapshot":
        net_change_period = annual_rate_end
        pct_change_period = ((annual_rate_end / area_end) * 100.0) if (pd.notna(annual_rate_end) and pd.notna(area_end) and area_end > 0) else np.nan
    else:
        net_change_period = (area_end - area_start) if (pd.notna(area_start) and pd.notna(area_end)) else np.nan
        pct_change_period = ((net_change_period / area_start) * 100.0) if (pd.notna(net_change_period) and area_start > 0) else np.nan

    # Area-weighted forest share in target_yr
    if not df_end.empty and df_end["Land_Area_ha"].sum() > 0:
        valid_land = df_end.dropna(subset=["Land_Area_ha", "Forest_Area_ha"])
        if not valid_land.empty and valid_land["Land_Area_ha"].sum() > 0:
            forest_share_end = (valid_land["Forest_Area_ha"].sum() / valid_land["Land_Area_ha"].sum()) * 100.0
        else:
            forest_share_end = df_end["Forest_Share_pct"].mean()
    else:
        forest_share_end = np.nan

    # Gross Deforestation & Expansion
    if time_mode == "snapshot":
        gross_sub = scope_df[(scope_df["Year"] == target_yr) & (scope_df["Gross_Deforestation_ha"].notna())]
    else:
        gross_sub = scope_df[(scope_df["Year"] >= y_start) & (scope_df["Year"] <= y_end) & (scope_df["Gross_Deforestation_ha"].notna())]

    if not gross_sub.empty:
        latest_gross_yr = int(gross_sub["Year"].max())
        gross_loss_ha = gross_sub[gross_sub["Year"] == latest_gross_yr]["Gross_Deforestation_ha"].sum()
        gross_gain_ha = gross_sub[gross_sub["Year"] == latest_gross_yr]["Gross_Expansion_ha"].sum()
    else:
        latest_gross_yr = None
        gross_loss_ha = np.nan
        gross_gain_ha = np.nan

    # CO2 Emissions
    if time_mode == "snapshot":
        co2_sub = scope_df[(scope_df["Year"] == target_yr) & (scope_df["CO2_Emissions_tonnes"].notna())]
    else:
        co2_sub = scope_df[(scope_df["Year"] <= y_end) & (scope_df["Year"] >= y_start) & (scope_df["CO2_Emissions_tonnes"].notna())]

    if not co2_sub.empty:
        latest_co2_yr = int(co2_sub["Year"].max())
        co2_end_tonnes = co2_sub[co2_sub["Year"] == latest_co2_yr]["CO2_Emissions_tonnes"].sum()
    else:
        latest_co2_yr = None
        co2_end_tonnes = np.nan

    # Cause-specific satellite loss
    cause_info = CAUSE_METADATA.get(selected_cause, CAUSE_METADATA["All Causes"])
    cause_df = df_drivers if cause_info["dataset"] == "drivers" else df_comm
    c_min_yr, c_max_yr = cause_info["years"]
    eff_start = max(y_start, c_min_yr)
    eff_end = min(y_end, c_max_yr)

    if eff_start <= eff_end:
        if iso3:
            c_sub = cause_df[(cause_df["Code"] == iso3) & (cause_df["Year"] >= eff_start) & (cause_df["Year"] <= eff_end)]
        else:
            c_sub = cause_df[(cause_df["Code"].str.len() == 3) & (~cause_df["Code"].str.startswith("OWID", na=False))]
            c_sub = c_sub[c_sub["Continent"].isin(continents) & (c_sub["Year"] >= eff_start) & (c_sub["Year"] <= eff_end)]

        cause_col = cause_info["column"]
        cause_loss_period = c_sub[cause_col].sum() if (not c_sub.empty and cause_col in c_sub.columns) else np.nan
        total_col = "Total_Loss_ha" if cause_info["dataset"] == "drivers" else "Total_Commodity_ha"
        total_cause_base = c_sub[total_col].sum() if (not c_sub.empty and total_col in c_sub.columns) else np.nan
        cause_share_pct = (cause_loss_period / total_cause_base * 100.0) if (pd.notna(cause_loss_period) and pd.notna(total_cause_base) and total_cause_base > 0) else np.nan
    else:
        cause_loss_period = np.nan
        cause_share_pct = np.nan

    return {
        "time_mode": time_mode,
        "scope_label": scope_label,
        "iso3": iso3,
        "start_year": y_start,
        "end_year": y_end,
        "area_start_ha": area_start,
        "area_end_ha": area_end,
        "net_change_period_ha": net_change_period,
        "pct_change_period": pct_change_period,
        "annual_rate_end_ha": annual_rate_end,
        "forest_share_end_pct": forest_share_end,
        "gross_loss_ha": gross_loss_ha,
        "gross_gain_ha": gross_gain_ha,
        "gross_reported_year": latest_gross_yr,
        "co2_end_tonnes": co2_end_tonnes,
        "co2_reported_year": latest_co2_yr,
        "cause_loss_ha": cause_loss_period,
        "cause_share_pct": cause_share_pct,
        "cause_years": (eff_start, eff_end) if eff_start <= eff_end else None
    }
