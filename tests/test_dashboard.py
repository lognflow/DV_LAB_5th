"""
Unit and Integration Tests for Global Deforestation Analytics Backend, Charts & Notebooks.
Verifies data pipeline, continental accuracy, dynamic KPIs, Global Heatmap Decreased/Increased
tooltips, FastAPI endpoints, cause-dynamic charts, and executed Jupyter notebooks.
"""

import os
import sys
import pytest
import pandas as pd
import nbformat
import plotly.graph_objects as go
from fastapi.testclient import TestClient

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_ROOT not in sys.path:
    sys.path.append(PROJ_ROOT)

import server
from src.utils import (
    load_processed_data,
    load_world_geodata,
    get_global_kpis,
    compute_dynamic_kpis
)
from src.charts import (
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
    create_country_deep_dive_chart,
    create_country_cause_radar,
    create_country_heatmap,
    create_forest_vs_emissions_scatter,
    create_country_treemap,
    create_slope_dumbbell_chart,
    create_environmental_impact_chart
)


@pytest.fixture(scope="module")
def dashboard_data():
    return load_processed_data()


@pytest.fixture(scope="module")
def api_client():
    return TestClient(server.app)


def test_processed_files_exist():
    """Verify all required processed files exist."""
    required = [
        "country_forest_panel.csv",
        "global_forest_summary.csv",
        "deforestation_drivers_processed.csv",
        "commodity_drivers_processed.csv",
        "country_hotspots.csv",
        "metadata_sources.json"
    ]
    proc_dir = os.path.join(PROJ_ROOT, "data", "processed")
    for fname in required:
        fpath = os.path.join(proc_dir, fname)
        assert os.path.exists(fpath), f"Missing processed file: {fname}"
        assert os.path.getsize(fpath) > 100, f"File {fname} is suspiciously small."


def test_continental_mapping_accuracy(dashboard_data):
    """Verify all 6 continents including South America match FAO 2020 totals."""
    df_panel = dashboard_data["country_panel"]
    reg_2020 = df_panel[df_panel["Year"] == 2020].groupby("Continent")["Forest_Area_Mha"].sum().to_dict()

    for cont in ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"]:
        assert cont in reg_2020, f"Missing continent: {cont}"

    assert abs(reg_2020["South America"] - 870.43) < 0.5
    assert abs(reg_2020["North America"] - 777.62) < 0.5
    assert abs(reg_2020["Africa"] - 676.86) < 0.5
    assert abs(reg_2020["Oceania"] - 183.30) < 0.5


def test_global_kpi_calculations(dashboard_data):
    """Verify global metrics and authentic values against FAO FRA benchmarks."""
    df_global = dashboard_data["global_summary"]
    kpis = get_global_kpis(df_global, target_year=2025)

    assert kpis["target_year"] == 2025
    assert 4_000_000_000 <= kpis["forest_area_ha"] <= 4_400_000_000
    assert kpis["net_change_since_1990_ha"] < -150_000_000
    assert 28.0 <= kpis["forest_share_pct"] <= 33.0


def test_dynamic_reactive_kpis(dashboard_data):
    """Verify reactive KPIs across country scope and specific cause filters."""
    df_panel = dashboard_data["country_panel"]
    df_drv = dashboard_data["drivers"]
    df_comm = dashboard_data["commodities"]

    k_bra = compute_dynamic_kpis(df_panel, df_drv, df_comm, 1990, 2025, ["South America"], "Brazil", "Wildfire")
    assert k_bra["iso3"] == "BRA"
    assert abs(k_bra["net_change_period_ha"] / 1e6 - (-132.36)) < 0.2
    assert k_bra["cause_loss_ha"] > 9_000_000
    assert 0 < k_bra["cause_share_pct"] < 100

    k_beef = compute_dynamic_kpis(df_panel, df_drv, df_comm, 2001, 2023, ["South America"], "Brazil", "Commodity: Beef (Cattle Ranching)")
    assert k_beef["cause_loss_ha"] > 20_000_000
    assert k_beef["cause_share_pct"] > 50.0


def test_global_heatmap_decreased_increased_labels(dashboard_data):
    """Verify the Global Heatmap explicitly marks countries as DECREASED or INCREASED."""
    fig = create_global_forest_heatmap(
        dashboard_data["country_panel"],
        df_hotspots=dashboard_data["hotspots"],
        start_year=1990,
        end_year=2025,
        snapshot_year=2020
    )
    assert isinstance(fig, go.Figure) and len(fig.data) > 0
    trace = fig.data[0]
    custom_statuses = [row[1] for row in trace.customdata]
    assert any("DECREASED" in s for s in custom_statuses)
    assert any("INCREASED" in s for s in custom_statuses)


def test_all_plotly_charts(dashboard_data):
    """Verify that all active chart generators produce valid figures."""
    df_panel = dashboard_data["country_panel"]
    df_global = dashboard_data["global_summary"]
    df_drivers = dashboard_data["drivers"]
    df_comm = dashboard_data["commodities"]
    df_hotspots = dashboard_data["hotspots"]

    figs = [
        create_global_forest_heatmap(df_panel, df_hotspots, 1990, 2025, 2020),
        create_world_choropleth(df_panel, year=2020, metric="Annual_Change_Mha", highlight_iso3="BRA"),
        create_cause_world_choropleth(df_drivers, "Wildfire", "Wildfire", (2001, 2024)),
        create_global_trend_chart(df_global),
        create_gain_vs_loss_chart(df_global),
        create_drivers_pie_chart(df_drivers, entity="World", year=2023),
        create_drivers_stacked_bar(df_drivers, entity="World"),
        create_commodity_breakdown_chart(df_comm, entity="World", year=2023),
        create_cause_top_countries_bar(df_drivers, "Wildfire", "Wildfire", (2001, 2024)),
        create_cause_trajectory_by_continent(df_drivers, "Permanent agriculture", "Permanent Agriculture", (2001, 2024)),
        create_cause_share_comparison(df_drivers, "Wildfire", "Wildfire", (2001, 2024)),
        create_top_countries_bar(df_hotspots, top_n=10, ascending=True),
        create_country_deep_dive_chart(df_panel, iso3="BRA"),
        create_country_cause_radar(df_drivers, ["BRA", "COD", "CAN"]),
        create_country_heatmap(df_drivers, "Wildfire", "Wildfire"),
        create_forest_vs_emissions_scatter(df_panel, year=2020),
        create_country_treemap(df_hotspots, mode="loss"),
        create_slope_dumbbell_chart(df_hotspots, top_n=10),
        create_environmental_impact_chart(df_global)
    ]

    for idx, fig in enumerate(figs):
        assert isinstance(fig, go.Figure), f"Chart {idx} is not a Plotly Figure"
        assert len(fig.data) > 0, f"Chart {idx} has no data traces"


def test_fastapi_frontend_and_endpoints(api_client):
    """Test custom web frontend routes and all interactive JSON/CSV endpoints."""
    # Static HTML and bundled Plotly JS
    r_home = api_client.get("/")
    assert r_home.status_code == 200
    assert "Global Deforestation" in r_home.text

    r_plotly = api_client.get("/vendor/plotly.min.js")
    assert r_plotly.status_code == 200
    assert len(r_plotly.content) > 1_000_000

    # Filters
    r_filt = api_client.get("/api/filters")
    assert r_filt.status_code == 200
    filt_json = r_filt.json()
    assert len(filt_json["continents"]) == 6
    assert len(filt_json["countries"]) > 200

    # Overview (Default + Focus Country + Unit switch)
    r_ov = api_client.post("/api/overview", json={"focus_country": "Brazil", "unit": "Square Kilometers (km²)"})
    assert r_ov.status_code == 200
    assert "bdata" not in r_ov.text
    ov_data = r_ov.json()
    assert len(ov_data["kpis"]) == 3
    assert all(k["label"] != "All Causes" for k in ov_data["kpis"])
    assert "km²" in ov_data["kpis"][0]["value"]
    assert "heatmap" in ov_data["charts"]

    # Overview Filtered to Asia + India + Hectares (verifies filtered heatmap renders colors cleanly)
    r_asia = api_client.post("/api/overview", json={
        "continents": ["Asia"],
        "focus_country": "India",
        "start_year": 1990,
        "end_year": 2025,
        "snapshot_year": 2025,
        "unit": "Hectares (ha)"
    })
    assert r_asia.status_code == 200
    assert "bdata" not in r_asia.text
    asia_hm = r_asia.json()["charts"]["heatmap"]
    assert len(asia_hm["data"]) >= 1
    # Trace 1 contains the official Survey of India boundary overlay
    assert any("india_soi_boundary" in str(tr.get("geojson", "")) for tr in asia_hm["data"])
    assert isinstance(asia_hm["data"][0]["z"], list)
    assert len(asia_hm["data"][0]["z"]) == 48
    assert asia_hm["layout"]["geo"].get("fitbounds") == "locations"
    ind_idx = asia_hm["data"][0]["locations"].index("IND")
    assert asia_hm["data"][0]["z"][ind_idx] > 8_000_000

    # Country Analytics (Brazil + India secondary view switching & accurate cattle label)
    r_ctry = api_client.post("/api/country", json={"primary_country": "Brazil", "cause": "Wildfire"})
    assert r_ctry.status_code == 200
    ctry_data = r_ctry.json()
    assert ctry_data["scorecard"]["direction"] == "DECREASED"
    assert len(ctry_data["scorecard"]["metrics"]) == 2
    assert "zoom_map" not in ctry_data["charts"]
    assert "compare_lines" not in ctry_data["charts"]
    assert "compare_radar" in ctry_data["charts"]

    r_ind_comm = api_client.post("/api/country", json={"primary_country": "India", "country_secondary_view": "commodity"})
    assert r_ind_comm.status_code == 200
    ind_comm = r_ind_comm.json()
    assert ind_comm["scorecard"]["direction"] == "INCREASED"
    assert ind_comm["scorecard"]["dominant_commodity"] == "Cattle (Beef, Leather & Pasture)"
    assert "Cattle (Beef, Leather & Pasture)" in [t["name"] for t in ind_comm["charts"]["secondary"]["data"]]

    r_ind_gross = api_client.post("/api/country", json={"primary_country": "India", "country_secondary_view": "gross"})
    assert r_ind_gross.status_code == 200
    assert "Gross Deforestation vs. Forest Expansion: India" in r_ind_gross.json()["charts"]["secondary"]["layout"]["title"]["text"]

    # Cause Analytics switching (All Causes vs Specific Cause) + Comparison in Causes
    r_all = api_client.post("/api/causes", json={"cause": "All Causes"})
    assert r_all.status_code == 200 and r_all.json()["mode"] == "all"
    assert "compare_radar" in r_all.json()["charts"]
    assert "compare_heatmap" in r_all.json()["charts"]

    r_wild = api_client.post("/api/causes", json={"cause": "Wildfire"})
    assert r_wild.status_code == 200
    wild_json = r_wild.json()
    assert wild_json["mode"] == "specific"
    assert "trajectory" in wild_json["charts"]
    assert "compare_radar" in wild_json["charts"]
    assert "compare_heatmap" in wild_json["charts"]
    assert len(wild_json["table"]) > 0

    r_beef = api_client.post("/api/causes", json={"cause": "Commodity: Beef (Cattle Ranching)"})
    assert r_beef.status_code == 200 and r_beef.json()["mode"] == "specific"

    # Hotspots Analytics
    assert api_client.post("/api/hotspots", json={"top_n": 10}).status_code == 200

    # Verify removed tabs are absent from DOM
    assert 'data-tab="regional"' not in r_home.text
    assert 'data-tab="data"' not in r_home.text
    assert 'data-tab="country"' not in r_home.text
    assert 'data-tab="overview"' in r_home.text
    assert 'data-tab="causes"' in r_home.text
    assert 'data-tab="hotspots"' in r_home.text
    assert 'id="chart-compare-radar"' in r_home.text
    assert 'id="chart-compare-heatmap"' in r_home.text

    # Snapshot Time Mode (Mutually exclusive single-year analysis)
    r_home = api_client.get("/")
    assert r_home.status_code == 200
    assert "no-store" in r_home.headers.get("cache-control", "")
    assert 'id="time-mode-btns"' in r_home.text
    assert 'data-tmode="snapshot"' in r_home.text
    assert 'id="group-year-range"' in r_home.text
    assert 'id="group-snapshot-year"' in r_home.text

    r_js = api_client.get("/static/js/dashboard.js")
    assert r_js.status_code == 200
    assert "dataset.tmode" in r_js.text and "dataset.mode" not in r_js.text
    assert "no-store" in r_js.headers.get("cache-control", "")

    r_snap_ov = api_client.post("/api/overview", json={
        "time_mode": "snapshot", "snapshot_year": 2020, "start_year": 1990, "end_year": 2025
    })
    assert r_snap_ov.status_code == 200 and "bdata" not in r_snap_ov.text
    snap_kpis = r_snap_ov.json()["kpis"]
    assert len(snap_kpis) == 3
    assert snap_kpis[0]["label"] == "Forest Area (2020)"
    assert snap_kpis[1]["label"] == "Annual Net Change (2020)"
    assert "Mha/yr" in snap_kpis[1]["value"]

    # Snapshot Year 1990 should transparently mark unavailable annual rate
    r_snap_1990 = api_client.post("/api/overview", json={"time_mode": "snapshot", "snapshot_year": 1990})
    assert r_snap_1990.status_code == 200
    kpis_1990 = r_snap_1990.json()["kpis"]
    assert len(kpis_1990) == 3
    assert kpis_1990[0]["label"] == "Forest Area (1990)"
    assert kpis_1990[1]["value"] == "Data Not Available"

    r_snap_ctry = api_client.post("/api/country", json={
        "time_mode": "snapshot", "snapshot_year": 2020, "primary_country": "Brazil", "cause": "Wildfire"
    })
    assert r_snap_ctry.status_code == 200
    assert len(r_snap_ctry.json()["scorecard"]["metrics"]) == 2
    assert r_snap_ctry.json()["scorecard"]["metrics"][0]["label"] == "Forest Area (2020)"

    r_snap_wild = api_client.post("/api/causes", json={
        "time_mode": "snapshot", "snapshot_year": 2023, "cause": "Wildfire"
    })
    assert r_snap_wild.status_code == 200
    wild_2023 = r_snap_wild.json()
    assert wild_2023["mode"] == "specific" and len(wild_2023["table"]) > 0
    assert wild_2023["table"][0]["Code"] == "CAN"

    r_snap_hot = api_client.post("/api/hotspots", json={"time_mode": "snapshot", "snapshot_year": 2020, "top_n": 10})
    assert r_snap_hot.status_code == 200
    hot_json = r_snap_hot.json()
    assert hot_json["time_mode"] == "snapshot" and hot_json["year_label"] == "2020"


def test_notebooks_exist_and_executed():
    """Verify all 7 notebooks exist and contain executed code cells with outputs."""
    notebook_files = [
        "01_data_collection_and_preprocessing.ipynb",
        "02_exploratory_data_analysis.ipynb",
        "03_global_deforestation_analysis.ipynb",
        "04_causes_of_deforestation.ipynb",
        "05_country_and_regional_hotspots.ipynb",
        "06_forest_recovery_and_environmental_impact.ipynb",
        "07_interactive_visualizations.ipynb"
    ]
    nb_dir = os.path.join(PROJ_ROOT, "notebooks")
    for nbfname in notebook_files:
        nb_path = os.path.join(nb_dir, nbfname)
        assert os.path.exists(nb_path), f"Missing notebook: {nbfname}"
        with open(nb_path, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
        code_cells = [c for c in nb.cells if c.cell_type == "code"]
        assert len(code_cells) > 0, f"Notebook {nbfname} has no code cells"
        cells_with_outputs = [c for c in code_cells if len(c.get("outputs", [])) > 0]
        assert len(cells_with_outputs) > 0, f"Notebook {nbfname} has no executed cell outputs"
