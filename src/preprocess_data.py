"""
Data Preprocessing Script
Consolidates raw authoritative datasets from FAO, Global Forest Watch,
Global Carbon Project, and World Bank into clean, verified panel and summary tables.
"""

import os
import json
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(PROC_DIR, exist_ok=True)


def load_regional_mapping():
    """Load ISO-3 country to Continent and Sub-Region mapping with accurate Americas split."""
    path = os.path.join(RAW_DIR, "country_regions.csv")
    df = pd.read_csv(path)

    def assign_continent(row):
        reg = str(row.get("region", ""))
        sub = str(row.get("sub-region", ""))
        inter = str(row.get("intermediate-region", ""))
        if reg == "Americas":
            if inter == "South America" or sub == "South America":
                return "South America"
            return "North America"
        elif reg in ["Africa", "Asia", "Europe", "Oceania"]:
            return reg
        return "Other"

    df["Continent"] = df.apply(assign_continent, axis=1)
    df["Sub_Region_Detail"] = np.where(
        df["intermediate-region"].notna() & (df["intermediate-region"] != ""),
        df["intermediate-region"],
        df["sub-region"]
    )
    df = df.rename(columns={"alpha-3": "ISO3", "name": "Country_Name"})
    return (
        df[["ISO3", "Country_Name", "Continent", "Sub_Region_Detail"]]
        .rename(columns={"Sub_Region_Detail": "Sub_Region"})
        .dropna(subset=["ISO3"])
        .drop_duplicates(subset=["ISO3"])
    )


def preprocess():
    print("Beginning preprocessing of authentic deforestation datasets...")
    geo_map = load_regional_mapping()

    # 1. Forest Area (FAO FRA)
    df_area = pd.read_csv(os.path.join(RAW_DIR, "forest_area.csv"))
    df_area = df_area.rename(columns={"Forest area": "Forest_Area_ha", "Code": "ISO3"})

    # 2. Annual Change in Forest Area (FAO FRA)
    df_change = pd.read_csv(os.path.join(RAW_DIR, "annual_change_forest_area.csv"))
    df_change = df_change.rename(columns={"Annual change in forest area": "Annual_Change_ha", "Code": "ISO3"})

    # 3. Gross Deforestation & Expansion (FAO FRA: 1990, 2000, 2010, 2015, 2020)
    df_defor = pd.read_csv(os.path.join(RAW_DIR, "annual_deforestation.csv"))
    df_defor = df_defor.rename(columns={"Deforestation": "Gross_Deforestation_ha", "Code": "ISO3"})
    df_exp = pd.read_csv(os.path.join(RAW_DIR, "annual_forest_expansion.csv"))
    df_exp = df_exp.rename(columns={"Forest expansion": "Gross_Expansion_ha", "Code": "ISO3"})

    # 4. Forest Share of Land Area (FAO / World Bank)
    df_share = pd.read_csv(os.path.join(RAW_DIR, "forest_area_share_land.csv"))
    df_share = df_share.rename(columns={"Share of land covered by forest": "Forest_Share_pct", "Code": "ISO3"})
    if "Share of land covered by forest (Annotations)" in df_share.columns:
        df_share = df_share.drop(columns=["Share of land covered by forest (Annotations)"])

    # 5. Land-use CO2 emissions (Global Carbon Project / UN FAO)
    df_co2 = pd.read_csv(os.path.join(RAW_DIR, "annual_co2_land_use.csv"))
    df_co2 = df_co2.rename(columns={"Annual CO₂ emissions from land-use change": "CO2_Emissions_tonnes", "Code": "ISO3"})

    # 6. Red List Index (IUCN)
    df_rli = pd.read_csv(os.path.join(RAW_DIR, "red_list_index.csv"))
    df_rli = df_rli.rename(columns={"Red List Index": "Red_List_Index", "Code": "ISO3"})

    # --- COUNTRY LEVEL PANEL (1990 - 2025) ---
    country_area = df_area[df_area["ISO3"].str.len() == 3].copy()
    country_area = country_area[~country_area["ISO3"].str.startswith("OWID", na=False)]

    panel = country_area.merge(df_change[["ISO3", "Year", "Annual_Change_ha"]], on=["ISO3", "Year"], how="left")
    panel = panel.merge(df_defor[["ISO3", "Year", "Gross_Deforestation_ha"]].dropna(subset=["ISO3"]), on=["ISO3", "Year"], how="left")
    panel = panel.merge(df_exp[["ISO3", "Year", "Gross_Expansion_ha"]].dropna(subset=["ISO3"]), on=["ISO3", "Year"], how="left")
    panel = panel.merge(df_share[["ISO3", "Year", "Forest_Share_pct"]], on=["ISO3", "Year"], how="left")
    panel = panel.merge(df_co2[["ISO3", "Year", "CO2_Emissions_tonnes"]], on=["ISO3", "Year"], how="left")
    panel = panel.merge(df_rli[["ISO3", "Year", "Red_List_Index"]], on=["ISO3", "Year"], how="left")

    # Merge continent info
    panel = panel.merge(geo_map, on="ISO3", how="left")
    panel["Continent"] = panel["Continent"].fillna("Other")
    panel["Sub_Region"] = panel["Sub_Region"].fillna("Other")

    # Filter years 1990 to 2025
    panel = panel[(panel["Year"] >= 1990) & (panel["Year"] <= 2025)].sort_values(["ISO3", "Year"]).reset_index(drop=True)

    # Derive static country Land Area (ha) from valid 2020 observation for accurate weighted shares
    ref_2020 = panel[(panel["Year"] == 2020) & (panel["Forest_Share_pct"] > 0)].copy()
    ref_2020["Land_Area_ha"] = ref_2020["Forest_Area_ha"] / (ref_2020["Forest_Share_pct"] / 100.0)
    panel = panel.merge(ref_2020[["ISO3", "Land_Area_ha"]], on="ISO3", how="left")

    # Add metric conversions
    panel["Forest_Area_sqkm"] = panel["Forest_Area_ha"] / 100.0
    panel["Forest_Area_Mha"] = panel["Forest_Area_ha"] / 1_000_000.0
    panel["Annual_Change_sqkm"] = panel["Annual_Change_ha"] / 100.0
    panel["Annual_Change_Mha"] = panel["Annual_Change_ha"] / 1_000_000.0
    panel["Gross_Deforestation_Mha"] = panel["Gross_Deforestation_ha"] / 1_000_000.0
    panel["Gross_Expansion_Mha"] = panel["Gross_Expansion_ha"] / 1_000_000.0
    panel["CO2_Emissions_Mt"] = panel["CO2_Emissions_tonnes"] / 1_000_000.0

    def net_status(val):
        if pd.isna(val):
            return "Unknown"
        elif val < -500:
            return "Deforestation (Net Loss)"
        elif val > 500:
            return "Afforestation / Recovery (Net Gain)"
        else:
            return "Stable (Net Zero)"

    panel["Net_Change_Type"] = panel["Annual_Change_ha"].apply(net_status)
    panel_path = os.path.join(PROC_DIR, "country_forest_panel.csv")
    panel.to_csv(panel_path, index=False)
    print(f"Saved country panel: {panel_path} ({len(panel)} rows)")

    # --- GLOBAL SUMMARY (1990 - 2025) ---
    world_area = df_area[df_area["Entity"] == "World"].copy()
    world_change = df_change[df_change["Entity"] == "World"].copy()
    world_share = df_share[df_share["Entity"] == "World"].copy()
    world_co2 = df_co2[df_co2["Entity"] == "World"].copy()

    global_summary = world_area[["Year", "Forest_Area_ha"]].merge(
        world_change[["Year", "Annual_Change_ha"]], on="Year", how="left"
    ).merge(
        world_share[["Year", "Forest_Share_pct"]], on="Year", how="left"
    ).merge(
        world_co2[["Year", "CO2_Emissions_tonnes"]], on="Year", how="left"
    )

    global_summary = global_summary[(global_summary["Year"] >= 1990) & (global_summary["Year"] <= 2025)].sort_values("Year").reset_index(drop=True)
    global_summary["Forest_Area_sqkm"] = global_summary["Forest_Area_ha"] / 100.0
    global_summary["Forest_Area_Mha"] = global_summary["Forest_Area_ha"] / 1_000_000.0
    global_summary["Annual_Change_sqkm"] = global_summary["Annual_Change_ha"] / 100.0
    global_summary["Annual_Change_Mha"] = global_summary["Annual_Change_ha"] / 1_000_000.0
    global_summary["CO2_Emissions_Mt"] = global_summary["CO2_Emissions_tonnes"] / 1_000_000.0
    global_summary["CO2_Emissions_Gt"] = global_summary["CO2_Emissions_tonnes"] / 1_000_000_000.0

    world_defor = df_defor[df_defor["Entity"] == "World"]
    world_exp = df_exp[df_exp["Entity"] == "World"]

    global_summary = global_summary.merge(world_defor[["Year", "Gross_Deforestation_ha"]], on="Year", how="left")
    global_summary = global_summary.merge(world_exp[["Year", "Gross_Expansion_ha"]], on="Year", how="left")
    global_summary["Gross_Deforestation_Mha"] = global_summary["Gross_Deforestation_ha"] / 1_000_000.0
    global_summary["Gross_Expansion_Mha"] = global_summary["Gross_Expansion_ha"] / 1_000_000.0

    global_path = os.path.join(PROC_DIR, "global_forest_summary.csv")
    global_summary.to_csv(global_path, index=False)
    print(f"Saved global summary: {global_path} ({len(global_summary)} rows)")

    # --- REGIONAL COMPARISON (Continents with area-weighted share) ---
    continents = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"]
    reg_rows = []
    for cont in continents:
        sub = panel[panel["Continent"] == cont]
        grouped = sub.groupby("Year").agg({
            "Forest_Area_ha": "sum",
            "Annual_Change_ha": "sum",
            "CO2_Emissions_tonnes": "sum",
            "Land_Area_ha": "sum"
        }).reset_index()
        grouped["Continent"] = cont
        # Area-weighted forest share
        grouped["Forest_Share_pct"] = np.where(
            grouped["Land_Area_ha"] > 0,
            (grouped["Forest_Area_ha"] / grouped["Land_Area_ha"]) * 100.0,
            np.nan
        )
        reg_rows.append(grouped)

    df_reg = pd.concat(reg_rows, ignore_index=True)
    df_reg["Forest_Area_sqkm"] = df_reg["Forest_Area_ha"] / 100.0
    df_reg["Forest_Area_Mha"] = df_reg["Forest_Area_ha"] / 1_000_000.0
    df_reg["Annual_Change_Mha"] = df_reg["Annual_Change_ha"] / 1_000_000.0
    df_reg["CO2_Emissions_Mt"] = df_reg["CO2_Emissions_tonnes"] / 1_000_000.0
    reg_path = os.path.join(PROC_DIR, "regional_comparison.csv")
    df_reg.to_csv(reg_path, index=False)
    print(f"Saved regional comparison: {reg_path} ({len(df_reg)} rows)")

    # --- TREE COVER LOSS DRIVERS (Curtis et al. / GFW) ---
    df_drivers = pd.read_csv(os.path.join(RAW_DIR, "tree_cover_loss_by_dominant_driver.csv"))
    driver_cols = [
        "Settlements and infrastructure",
        "Mining and energy industry",
        "Other natural disturbances",
        "Shifting cultivation",
        "Logging",
        "Permanent agriculture",
        "Wildfire"
    ]
    df_drivers["Total_Loss_ha"] = df_drivers[driver_cols].sum(axis=1)
    df_drivers = df_drivers.merge(geo_map[["ISO3", "Continent", "Sub_Region"]], left_on="Code", right_on="ISO3", how="left")
    df_drivers["Continent"] = df_drivers["Continent"].fillna("Global / Regional")
    drivers_path = os.path.join(PROC_DIR, "deforestation_drivers_processed.csv")
    df_drivers.to_csv(drivers_path, index=False)
    print(f"Saved drivers: {drivers_path} ({len(df_drivers)} rows)")

    # --- COMMODITY-DRIVEN DEFORESTATION (Pendrill et al. / FAO / GFW) ---
    df_comm = pd.read_csv(os.path.join(RAW_DIR, "drivers_deforestation_commodity.csv"))
    comm_cols = [
        "Beef",
        "Forestry (paper and wood)",
        "Palm oil",
        "Soy",
        "Cocoa and coffee",
        "Cereals",
        "Roots and tubers",
        "Other crops"
    ]
    df_comm["Total_Commodity_ha"] = df_comm[comm_cols].sum(axis=1)
    df_comm = df_comm.merge(geo_map[["ISO3", "Continent", "Sub_Region"]], left_on="Code", right_on="ISO3", how="left")
    df_comm["Continent"] = df_comm["Continent"].fillna("Global / Regional")
    comm_path = os.path.join(PROC_DIR, "commodity_drivers_processed.csv")
    df_comm.to_csv(comm_path, index=False)
    print(f"Saved commodity drivers: {comm_path} ({len(df_comm)} rows)")

    # --- COUNTRY HOTSPOTS AND RANKINGS ---
    p90 = panel[panel["Year"] == 1990][["ISO3", "Entity", "Continent", "Sub_Region", "Forest_Area_ha", "Forest_Share_pct"]].rename(
        columns={"Forest_Area_ha": "Forest_Area_1990_ha", "Forest_Share_pct": "Forest_Share_1990_pct"}
    )
    p20 = panel[panel["Year"] == 2020][["ISO3", "Forest_Area_ha", "Forest_Share_pct"]].rename(
        columns={"Forest_Area_ha": "Forest_Area_2020_ha", "Forest_Share_pct": "Forest_Share_2020_pct"}
    )
    p25 = panel[panel["Year"] == 2025][["ISO3", "Forest_Area_ha", "Forest_Share_pct"]].rename(
        columns={"Forest_Area_ha": "Forest_Area_2025_ha", "Forest_Share_pct": "Forest_Share_2025_pct"}
    )

    hotspots = p90.merge(p20, on="ISO3", how="inner").merge(p25, on="ISO3", how="left")
    hotspots["Forest_Area_Latest_ha"] = hotspots["Forest_Area_2025_ha"].fillna(hotspots["Forest_Area_2020_ha"])
    hotspots["Forest_Share_Latest_pct"] = hotspots["Forest_Share_2025_pct"].fillna(hotspots["Forest_Share_2020_pct"])

    hotspots["Net_Change_1990_to_Latest_ha"] = hotspots["Forest_Area_Latest_ha"] - hotspots["Forest_Area_1990_ha"]
    hotspots["Net_Change_1990_to_Latest_sqkm"] = hotspots["Net_Change_1990_to_Latest_ha"] / 100.0
    hotspots["Net_Change_1990_to_Latest_Mha"] = hotspots["Net_Change_1990_to_Latest_ha"] / 1_000_000.0
    hotspots["Pct_Change_Since_1990"] = (
        (hotspots["Forest_Area_Latest_ha"] - hotspots["Forest_Area_1990_ha"]) / hotspots["Forest_Area_1990_ha"].replace(0, np.nan)
    ) * 100.0

    recent_change = panel[panel["Year"] >= 2015].groupby("ISO3")["Annual_Change_ha"].mean().reset_index().rename(
        columns={"Annual_Change_ha": "Recent_Avg_Annual_Change_ha"}
    )
    hotspots = hotspots.merge(recent_change, on="ISO3", how="left")
    hotspots["Recent_Avg_Annual_Change_sqkm"] = hotspots["Recent_Avg_Annual_Change_ha"] / 100.0

    # Attach Dominant Satellite Driver (2001-2024 cumulative) per country
    c_drv = df_drivers[df_drivers["Code"].str.len() == 3].groupby("Code")[driver_cols].sum()
    c_drv_valid = c_drv[c_drv.sum(axis=1) > 0]
    dom_driver = c_drv_valid.idxmax(axis=1).reset_index()
    dom_driver.columns = ["ISO3", "Dominant_Driver"]
    c_drv_tot = c_drv.sum(axis=1).reset_index()
    c_drv_tot.columns = ["ISO3", "Total_Satellite_Loss_2001_2024_ha"]
    hotspots = hotspots.merge(dom_driver, on="ISO3", how="left").merge(c_drv_tot, on="ISO3", how="left")
    hotspots["Dominant_Driver"] = hotspots["Dominant_Driver"].fillna("Data Not Available")

    # Attach Dominant Commodity (2001-2023 cumulative) per country
    c_comm = df_comm[df_comm["Code"].str.len() == 3].groupby("Code")[comm_cols].sum()
    c_comm_valid = c_comm[c_comm.sum(axis=1) > 0]
    dom_comm = c_comm_valid.idxmax(axis=1).reset_index()
    dom_comm.columns = ["ISO3", "Dominant_Commodity"]
    hotspots = hotspots.merge(dom_comm, on="ISO3", how="left")
    hotspots["Dominant_Commodity"] = hotspots["Dominant_Commodity"].fillna("Data Not Available")

    def hotspot_tier(row):
        loss_mha = row["Net_Change_1990_to_Latest_Mha"]
        pct = row["Pct_Change_Since_1990"]
        if loss_mha <= -10.0 or (loss_mha <= -2.0 and pct <= -30.0):
            return "Severe Hotspot (Critical)"
        elif loss_mha <= -2.0 or (loss_mha <= -0.5 and pct <= -15.0):
            return "High Deforestation Hotspot"
        elif loss_mha < -0.1:
            return "Moderate Deforestation Area"
        elif loss_mha > 2.0:
            return "Major Net Forest Expansion (Gainer)"
        elif loss_mha >= 0.1:
            return "Moderate Forest Gain"
        else:
            return "Stable Forest Dynamics"

    hotspots["Hotspot_Status"] = hotspots.apply(hotspot_tier, axis=1)
    hotspots = hotspots.sort_values("Net_Change_1990_to_Latest_ha").reset_index(drop=True)
    hotspots_path = os.path.join(PROC_DIR, "country_hotspots.csv")
    hotspots.to_csv(hotspots_path, index=False)
    print(f"Saved country hotspots: {hotspots_path} ({len(hotspots)} rows)")

    # --- METADATA AND SOURCE AUDIT ---
    metadata = {
        "project": "Global Deforestation Analysis Dashboard (1990–2025)",
        "authoritative_sources": [
            {
                "name": "FAO Global Forest Resources Assessment (FRA 2020 / 2025)",
                "organization": "Food and Agriculture Organization of the United Nations (FAO)",
                "url": "https://www.fao.org/forest-resources-assessment/",
                "indicators": ["Total Forest Area (ha)", "Net Annual Forest Area Change (ha/yr)", "Gross Deforestation", "Gross Forest Expansion", "Share of Land Covered by Forest (%)"],
                "coverage": "235+ countries and territories, 1990–2025",
                "methodology": "National reporting, remote sensing surveys, peer-reviewed expert validation across 5-year intervals with annual trend harmonizations.",
                "type": "Directly Measured & Officially Reported Ground/Satellite Observation"
            },
            {
                "name": "Global Forest Watch / Curtis et al. (Science 2018)",
                "organization": "World Resources Institute (WRI) & University of Maryland",
                "url": "https://www.globalforestwatch.org/",
                "publication": "Curtis et al., Science 361, 1108–1111 (2018)",
                "indicators": ["Tree Cover Loss by Dominant Driver (Permanent agriculture, Logging, Shifting cultivation, Wildfire, Settlements/infrastructure, Mining)"],
                "coverage": "Global, 2001–2024",
                "methodology": "Machine-learning classification of Landsat satellite time series at 30-meter resolution identifying direct proximate physical drivers.",
                "type": "Measured Remote Sensing Direct Drivers"
            },
            {
                "name": "Agricultural Commodity Drivers of Deforestation (Pendrill et al. 2022)",
                "organization": "Chalmers University of Technology, Stockholm Environment Institute, FAO",
                "publication": "Pendrill et al., Environmental Research Letters (2022)",
                "indicators": ["Deforestation attributable to Beef, Soy, Palm Oil, Wood Fiber, Cocoa, Coffee, Cereals, Roots & Tubers"],
                "coverage": "Global & Tropical countries, 2001–2023",
                "methodology": "Coupling spatial land-use change mapping with FAOSTAT agricultural production data and physical supply-chain trade models.",
                "type": "Inferred Economic Attribution from Measured Spatial Clearing"
            },
            {
                "name": "Global Carbon Budget (Friedlingstein et al. 2023 / 2024)",
                "organization": "Global Carbon Project (GCP) & UN FAO",
                "url": "https://globalcarbonbudget.org/",
                "indicators": ["Annual CO2 Emissions from Land-Use Change (tonnes CO2/yr)"],
                "coverage": "Global and national, 1850–2024",
                "methodology": "Ensemble of bookkeeping models (BLUE, OSCAR, H&N) driven by FAO forest area change data and deforestation dynamics.",
                "type": "Biogeochemical Bookkeeping Modeling based on Measured Land-Use Changes"
            },
            {
                "name": "IUCN Red List Index",
                "organization": "International Union for Conservation of Nature (IUCN) & BirdLife International",
                "url": "https://www.iucnredlist.org/",
                "indicators": ["Red List Index (0.0 = all species extinct, 1.0 = all species least concern)"],
                "coverage": "Global and national, 1993–2025",
                "methodology": "Aggregate measure of extinction risk changes over time for birds, mammals, amphibians, corals, and cycads.",
                "type": "Expert-Assessed Conservation Metric"
            }
        ],
        "distinction_notice": {
            "measured_causes": "Curtis et al. drivers (permanent agriculture, shifting cultivation, logging, wildfire, settlements/infrastructure, mining) represent directly observed physical land-cover disturbances classified from 30m satellite imagery.",
            "inferred_causes": "Pendrill et al. commodity drivers (beef cattle ranching, soy, palm oil, forestry, cocoa/coffee) are inferred through econometric allocation models linking observed spatial clearance to national crop/livestock production statistics and international trade flows.",
            "data_availability_notes": "Official FAO national forest inventory reports are compiled periodically (1990, 2000, 2010, 2015, 2020) with annual harmonized updates through 2025. Direct driver data spans 2001–2024; commodity attribution spans 2001–2023. For missing observations, 'Data Not Available' is shown."
        }
    }

    meta_path = os.path.join(PROC_DIR, "metadata_sources.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata: {meta_path}")
    print("Preprocessing completed successfully!")


if __name__ == "__main__":
    preprocess()
