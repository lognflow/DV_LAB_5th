"""
Unit and Integration Tests for Global Deforestation Analysis Dashboard.
Verifies data pipeline, continental accuracy, dynamic KPI calculations,
country-wise and cause-specific charts, notebook execution, and app compilation.
"""

import os
import sys
import pytest
import pandas as pd
import nbformat
import plotly.graph_objects as go

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ_ROOT not in sys.path:
    sys.path.append(PROJ_ROOT)

from src.utils import (
    load_processed_data,
    load_world_geodata,
    get_global_kpis,
    compute_dynamic_kpis,
    CAUSE_METADATA
)
from src.charts import (
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


@pytest.fixture(scope="module")
def dashboard_data():
    return load_processed_data()


def test_processed_files_exist():
    """Verify all required processed files exist."""
    required = [
        "country_forest_panel.csv",
        "global_forest_summary.csv",
        "regional_comparison.csv",
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
    """Verify all 6 continents including South America are mapped accurately against FAO totals."""
    df_reg = dashboard_data["regional"]
    reg_2020 = df_reg[df_reg["Year"] == 2020].set_index("Continent")["Forest_Area_Mha"].to_dict()

    for cont in ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"]:
        assert cont in reg_2020, f"Missing continent: {cont}"

    # Verify exact match with FAO 2020 continental totals
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
    assert kpis["net_change_since_1990_mha"] < -150.0
    assert 28.0 <= kpis["forest_share_pct"] <= 33.0


def test_dynamic_reactive_kpis(dashboard_data):
    """Verify reactive KPIs across country scope and specific cause filters."""
    df_panel = dashboard_data["country_panel"]
    df_drv = dashboard_data["drivers"]
    df_comm = dashboard_data["commodities"]

    # Country-level KPI for Brazil + Wildfire
    k_bra = compute_dynamic_kpis(df_panel, df_drv, df_comm, 1990, 2025, ["South America"], "Brazil", "Wildfire")
    assert k_bra["iso3"] == "BRA"
    assert abs(k_bra["net_change_period_ha"] / 1e6 - (-132.36)) < 0.2
    assert k_bra["cause_loss_ha"] > 9_000_000
    assert 0 < k_bra["cause_share_pct"] < 100

    # Commodity cause filter (Beef)
    k_beef = compute_dynamic_kpis(df_panel, df_drv, df_comm, 2001, 2023, ["South America"], "Brazil", "Commodity: Beef (Cattle Ranching)")
    assert k_beef["cause_loss_ha"] > 20_000_000
    assert k_beef["cause_share_pct"] > 50.0


def test_country_hotspots(dashboard_data):
    """Verify top deforested and reforested countries and dominant drivers."""
    df_hotspots = dashboard_data["hotspots"]
    top_deforested = df_hotspots.head(10)["ISO3"].tolist()
    assert "BRA" in top_deforested
    assert "COD" in top_deforested
    assert "IDN" in top_deforested
    assert df_hotspots[df_hotspots["ISO3"] == "BRA"]["Dominant_Driver"].iloc[0] == "Permanent agriculture"

    top_reforested = df_hotspots.tail(10)["ISO3"].tolist()
    assert "CHN" in top_reforested


def test_all_plotly_charts(dashboard_data):
    """Verify that all original and new Plotly/GeoPandas chart generators produce valid figures."""
    df_panel = dashboard_data["country_panel"]
    df_global = dashboard_data["global_summary"]
    df_drivers = dashboard_data["drivers"]
    df_comm = dashboard_data["commodities"]
    df_hotspots = dashboard_data["hotspots"]
    df_reg = dashboard_data["regional"]
    gdf_world = load_world_geodata()

    figs = [
        create_world_choropleth(df_panel, year=2020, metric="Annual_Change_Mha", highlight_iso3="BRA"),
        create_cause_world_choropleth(df_drivers, "Wildfire", "Wildfire", (2001, 2024)),
        create_geopandas_country_zoom_map(gdf_world, df_panel, iso3="BRA", year=2020),
        create_global_trend_chart(df_global),
        create_gain_vs_loss_chart(df_global),
        create_drivers_pie_chart(df_drivers, entity="World", year=2023),
        create_drivers_stacked_bar(df_drivers, entity="World"),
        create_commodity_breakdown_chart(df_comm, entity="World", year=2023),
        create_cause_top_countries_bar(df_drivers, "Wildfire", "Wildfire", (2001, 2024)),
        create_cause_trajectory_by_continent(df_drivers, "Permanent agriculture", "Permanent Agriculture", (2001, 2024)),
        create_cause_share_comparison(df_drivers, "Wildfire", "Wildfire", (2001, 2024)),
        create_top_countries_bar(df_hotspots, top_n=10, ascending=True),
        create_regional_comparison_chart(df_reg, metric="Forest_Area_Mha"),
        create_country_deep_dive_chart(df_panel, iso3="BRA"),
        create_country_comparison_lines(df_panel, ["BRA", "IDN", "CHN"], normalize=True),
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


def test_streamlit_app_compilation():
    """Verify that app.py compiles cleanly without syntax error."""
    app_path = os.path.join(PROJ_ROOT, "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        code = f.read()
    compile(code, app_path, "exec")


def test_streamlit_apptest_interactive_filters():
    """Execute full Streamlit dashboard UI and verify reactive Country & Cause filter changes."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(os.path.join(PROJ_ROOT, "app.py"), default_timeout=45)
    at.run()
    assert not at.exception, f"Initial Streamlit load raised exception: {at.exception}"

    # Verify changing Deforestation Cause renders cause-specific graphs cleanly
    cause_box = [s for s in at.sidebar.selectbox if "Select Cause" in s.label][0]
    cause_box.select("Wildfire").run()
    assert not at.exception, f"Cause='Wildfire' raised exception: {at.exception}"

    # Verify changing to an inferred Commodity Cause
    cause_box = [s for s in at.sidebar.selectbox if "Select Cause" in s.label][0]
    cause_box.select("Commodity: Beef (Cattle Ranching)").run()
    assert not at.exception, f"Cause='Commodity: Beef' raised exception: {at.exception}"

    # Verify selecting Focus Country updates Country Analytics & Overview cleanly
    country_box = [s for s in at.sidebar.selectbox if "Focus Country" in s.label][0]
    country_box.select("Brazil").run()
    assert not at.exception, f"Focus Country='Brazil' raised exception: {at.exception}"

    # Verify switching unit display
    unit_radio = [r for r in at.sidebar.radio if "Measurement Unit" in r.label][0]
    unit_radio.set_value("Square Kilometers (km²)").run()
    assert not at.exception, f"Unit='km²' raised exception: {at.exception}"

