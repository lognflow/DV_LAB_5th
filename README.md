# Global Deforestation Analysis Dashboard (1990–2025)

A professional, interactive, and research-grade scientific intelligence dashboard and analytical suite investigating global forest dynamics, proximate and economic deforestation drivers, continental hotspots, and ecological cascades between 1990 and 2025.

Built with **Python 3.11**, **FastAPI**, **Uvicorn**, **HTML5/CSS3/JavaScript**, **Pandas**, **NumPy**, **Plotly**, **GeoPandas**, and **Jupyter Notebooks (.ipynb)**.

---

## 🌟 Executive Summary & Key Empirical Findings

1. **Cumulative Global Forest Contraction (1990–2025):**
   - Earth's total forest area contracted from **4,343.5 Million hectares (4.34 Billion ha)** in 1990 to **4,140.2 Million hectares (4.14 Billion ha)** in 2025.
   - The world has suffered a cumulative net loss of over **203.3 Million hectares**—an area larger than the combined landmass of Mexico and Indonesia.
   - Global terrestrial forest cover decreased from **31.8%** of Earth's land surface to **30.3%**.

2. **The Deceleration Paradox (Net vs. Gross Rates):**
   - Net global forest loss decelerated from **-10.7 Mha/year** in the 1990s to **-3.2 Mha/year** by 2020.
   - However, gross deforestation remains acutely elevated at **~8.5 Mha/year**, only partially counterbalanced numerically by **~5.3 Mha/year** of gross expansion and afforestation.
   - The net figure conceals severe ecological asymmetry: ancient, carbon-dense, hyper-biodiverse primary tropical rainforests continue to be eradicated, while gains often consist of secondary regrowth or commercial timber monocultures.

3. **National Hotspots of Forest Depletion:**
   - **Brazil (BRA):** The planetary epicenter of absolute forest loss, losing over **132.3 Million hectares** since 1990 across the Amazon rainforest and Cerrado savanna.
   - **Democratic Republic of the Congo (COD):** The core of the Congo Basin, losing over **24.5 Mha**, driven by shifting subsistence agriculture, woodfuel harvesting, and infrastructure expansion.
   - **Indonesia (IDN):** Primary clearing across Sumatra and Borneo for industrial oil palm and timber concessions, though showing marked deceleration since 2017 following moratoriums.
   - **Severe Relative Losses:** Countries like **Paraguay** (-32.4%) and **Myanmar** (-28.6%) have lost nearly a third of their entire national forest heritage in just 35 years.

4. **Dominant Proximate Drivers & Commodity Footprints:**
   - **Permanent Agriculture:** The leading direct cause of irreversible tropical forest conversion worldwide.
   - **Beef Cattle Ranching:** The single largest agricultural commodity driver globally, consuming more tropical forest area than palm oil, soy, and forestry combined.
   - **Wildfire Escalation:** Drastic climate-driven wildfire spikes have surged across Canada, Russia, and the western United States, turning boreal carbon sinks into major emission sources.

5. **Top Forest Regenerators (Gainers):**
   - **China (CHN):** Over **+60 Million hectares** gained through massive state-directed programs (*Three-North Shelterbelt / Great Green Wall* and *Grain for Green*).
   - **European Forest Transition:** France, Spain, and Italy have experienced consistent expansion driven by rural agricultural land abandonment and sustainable forestry policies.

6. **Environmental & Climate Cascades:**
   - Annual CO₂ emissions from land-use change and deforestation consistently range between **4.5 and 5.0 Gigatonnes CO₂/year** (~10–12% of total anthropogenic emissions).
   - The IUCN Red List Index shows precipitous survival declines in tropical forest frontier nations (Indonesia, Malaysia, Brazil, Peru), confirming catastrophic biodiversity loss.

---

## 🏛️ Authentic Data Sources & Scientific Audit

In strict accordance with empirical research standards, **no synthetic, dummy, or randomized data is utilized**. Every calculation and chart is derived directly from authoritative environmental databases:

| Source | Organization | Spatial Coverage | Time Horizon | Key Indicators | Methodology Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Global Forest Resources Assessment (FRA 2020/2025)** | Food and Agriculture Organization of the United Nations (FAO) | 235 Countries / Territories | 1990–2025 | Total Forest Area (ha), Net Annual Change (ha/yr), Gross Loss & Gain, Forest % of Land | Official national reports, remote sensing surveys, harmonized intervals |
| **Classifying Drivers of Global Forest Loss** | Global Forest Watch / Curtis et al. (*Science* 2018) | Global (Wall-to-wall 30m) | 2001–2024 | Tree cover loss by dominant driver (Agriculture, Logging, Wildfire, Shifting Cultivation, Mining, Urban) | Directly measured Landsat satellite time-series classification |
| **Commodity Attribution Models** | Pendrill et al. (2022) / FAOSTAT | Tropical & Subtropical | 2001–2023 | Beef, Soy, Palm Oil, Cocoa, Coffee, Cereals, Wood Fiber | Econometric attribution linking spatial clearance to trade flows |
| **Global Carbon Budget (2024)** | Global Carbon Project (GCP) & UN FAO | Global & National | 1850–2024 | Annual CO₂ emissions from land-use change (Gt CO₂/yr) | Biogeochemical bookkeeping ensemble models (BLUE, OSCAR, H&N) |
| **IUCN Red List of Threatened Species** | IUCN & BirdLife International | Global & National | 1993–2024 | Red List Index (0.0 = Extinct, 1.0 = Least Concern) | Aggregate species extinction risk across taxonomic groups |

---

## 💻 Architecture & Repository Layout

```
d:\DVLAB\
├── server.py                                    # FastAPI backend API & static frontend host
├── README.md                                    # Comprehensive documentation
├── frontend/                                    # Custom responsive HTML/CSS/JS dashboard UI
│   ├── index.html                               # Executive 6-tab single-page interface
│   ├── css/dashboard.css                        # Forest-green & crisp white high-contrast theme
│   └── js/dashboard.js                          # Interactive Plotly.js controller & fullscreen logic
├── data/
│   ├── raw/                                     # Original authentic datasets downloaded from official endpoints
│   │   ├── forest_area.csv
│   │   ├── annual_change_forest_area.csv
│   │   ├── annual_deforestation.csv
│   │   ├── annual_forest_expansion.csv
│   │   ├── tree_cover_loss_by_dominant_driver.csv
│   │   ├── drivers_deforestation_commodity.csv
│   │   ├── forest_area_share_land.csv
│   │   ├── annual_co2_land_use.csv
│   │   ├── red_list_index.csv
│   │   ├── country_regions.csv
│   │   └── countries.geojson
│   └── processed/                               # Cleaned, standardized analysis panels & tables
│       ├── country_forest_panel.csv             # Full country-level panel 1990–2025
│       ├── global_forest_summary.csv            # World totals & decadal trajectory
│       ├── regional_comparison.csv              # Continental comparisons (6 continents)
│       ├── deforestation_drivers_processed.csv  # Curtis et al. drivers by country/region
│       ├── commodity_drivers_processed.csv      # Agricultural commodities by country/region
│       ├── country_hotspots.csv                 # Cumulative loss rankings & hotspot classifications
│       └── metadata_sources.json                # Complete audit trail & definition caveats
├── notebooks/                                   # 7 Fully implemented & executed Jupyter Notebooks (.ipynb)
│   ├── 01_data_collection_and_preprocessing.ipynb
│   ├── 02_exploratory_data_analysis.ipynb
│   ├── 03_global_deforestation_analysis.ipynb
│   ├── 04_causes_of_deforestation.ipynb
│   ├── 05_country_and_regional_hotspots.ipynb
│   ├── 06_forest_recovery_and_environmental_impact.ipynb
│   └── 07_interactive_visualizations.ipynb
├── src/                                         # Reusable analytics, preprocessing & visualization modules
│   ├── charts.py                                # Plotly publication-grade chart builders
│   ├── utils.py                                 # KPI calculators, theme definitions & formatting
│   ├── download_data.py                         # Automated authentic data ingest pipeline
│   ├── preprocess_data.py                       # Data cleaning, unit harmonization & panel creation
│   ├── create_all_notebooks.py                  # Jupyter notebook generator script
│   └── execute_notebooks.py                     # Headless execution & output pre-computation engine
└── tests/
    └── test_dashboard.py                        # Automated pytest suite verifying calculations & charts
```

---

## 🚀 How to Run the Project

### 1. Launch the Interactive Web Dashboard
Run the FastAPI + Uvicorn server locally:
```powershell
uvicorn server:app --host 0.0.0.0 --port 8501
```
Open **`http://localhost:8501`** in any web browser.

### 2. Run the Jupyter Notebooks
Start the Jupyter Notebook environment:
```powershell
jupyter lab
# or
jupyter notebook
```
Navigate to `notebooks/` and open any of the 7 fully implemented `.ipynb` files. All cells are already pre-computed with charts, Markdown commentary, and data tables.

### 3. Run Automated Tests
Execute the verification test suite:
```powershell
pytest tests/test_dashboard.py -v
```

---

## 🖥️ Web Dashboard Feature Tour

The custom HTML/CSS/JavaScript dashboard features a collapsible left filter menu (with one-click Full Screen expansion), crisp dark-on-light typography, and 6 interactive views:

1. **🌐 Overview & Global Heatmap:**
   - 5 reactive KPI cards calculated dynamically for any country, continent selection, year range, and active deforestation cause.
   - Full-width **Global Forest Change Heatmap** with explicit **`🔴 DECREASED` / `🟢 INCREASED`** hover tooltips and click-to-inspect country jumping.
   - Global/scoped forest area trajectory (`1990–2025`), cause top countries / gross gain-vs-loss balance, and hierarchical **Continent → Country Treemap**.

2. **🏳️ Country-Wise Analytics:**
   - Country scorecard with direction badge (`DECREASED` / `INCREASED`), dominant physical driver, and top commodity driver.
   - GeoPandas spatial focus map + dual-axis trajectory + cause-specific country timeline + commodity/gross toggle.
   - Multi-Country Comparison (up to 6 countries, normalized `Start = 100` or absolute), Driver Fingerprint Radar Chart, and Annual Intensity Heatmap.

3. **🔍 Cause Analytics (Dynamic Graph Switching):**
   - When **`All Causes`** is selected: Direct Drivers Donut, Commodity Attribution Bar, Stacked Longitudinal Drivers (`2001–2024`), Continental × Driver Sunburst, and Country Intensity Heatmap.
   - When a **Specific Cause** is selected (*Wildfire*, *Permanent Agriculture*, *Logging*, *Shifting Cultivation*, *Mining*, *Urban*, *Beef*, *Palm Oil*, *Soy*, etc.): Dynamically renders a Cause-Specific Global Map, Top 12 Countries Driven by That Cause, Continental Trajectory Area Chart, Share of National Loss Bar, Spike Heatmap, and Top 25 Country Ranking Table.

4. **🔥 Hotspots & Recovery:**
   - Dynamic Top N loss & expansion country rankings, **1990 vs. 2025 Dumbbell Slope Chart**, Forest Change vs. Land-Use CO₂ Bubble Scatter Plot, and Forest Transition Recovery Curves.

5. **🌍 Regional & Impact:**
   - 6-Continent comparative trends with area-weighted forest share %, Land-Use CO₂ trajectories, and IUCN Red List Index biodiversity curves.

6. **📊 Data Explorer:**
   - Live search, filter, and one-click CSV download across all 6 core datasets.

---

## 📜 Scientific Methodology & Definition Notes

- **Hectare (ha):** Standard forestry unit. $1\text{ ha} = 10,000\text{ m}^2 = 0.01\text{ km}^2$.
- **Net Forest Change:** Net mathematical difference ($\Delta = \text{Gain} - \text{Loss}$) over a reporting period.
- **Gross Deforestation:** The conversion of forest to other land use (cropland, pasture, infrastructure) or the permanent reduction of tree canopy cover below 10%.
- **Gross Expansion:** Forest expansion through afforestation (planting trees on non-forest land) and natural regeneration on abandoned land.
- **Reporting Intervals:** Official FAO FRA assessments report harmonized five-year intervals with annual updates through 2023–2025.
- **Data Not Available:** Where authoritative historical data is absent or unmeasured for a specific territory/year, the dashboard explicitly reports **"Data Not Available"** rather than interpolating or inventing results.

