"""
Script to download authentic, publicly available deforestation datasets
from official sources (FAO FRA, Global Forest Watch / Curtis et al., 
Global Carbon Project, World Bank, IUCN).
"""

import os
import urllib.request
import time
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

DATASET_URLS = {
    "forest_area.csv": {
        "url": "https://ourworldindata.org/grapher/forest-area-km.csv",
        "source": "FAO Global Forest Resources Assessment (FRA)",
        "unit": "Hectares",
        "description": "Total forest area by country and region from 1990 to 2025"
    },
    "annual_change_forest_area.csv": {
        "url": "https://ourworldindata.org/grapher/annual-change-forest-area.csv",
        "source": "FAO Global Forest Resources Assessment (FRA)",
        "unit": "Hectares / year",
        "description": "Net annual change in forest area (loss or gain) from 1991 to 2025"
    },
    "annual_deforestation.csv": {
        "url": "https://ourworldindata.org/grapher/annual-deforestation.csv",
        "source": "FAO Global Forest Resources Assessment (FRA)",
        "unit": "Hectares / year",
        "description": "Gross annual deforestation rate across reporting periods"
    },
    "annual_forest_expansion.csv": {
        "url": "https://ourworldindata.org/grapher/annual-forest-expansion.csv",
        "source": "FAO Global Forest Resources Assessment (FRA)",
        "unit": "Hectares / year",
        "description": "Gross annual forest expansion (afforestation and natural regeneration)"
    },
    "tree_cover_loss_by_dominant_driver.csv": {
        "url": "https://ourworldindata.org/grapher/tree-cover-loss-by-dominant-driver.csv",
        "source": "Curtis et al. (Science 2018) / Global Forest Watch",
        "unit": "Hectares",
        "description": "Tree cover loss categorized by primary driver (commodity agriculture, logging, shifting cultivation, wildfire, urbanization, mining)"
    },
    "drivers_deforestation_commodity.csv": {
        "url": "https://ourworldindata.org/grapher/drivers-deforestation-commodity.csv",
        "source": "Pendrill et al. / FAO / Global Forest Watch",
        "unit": "Hectares",
        "description": "Deforestation driven by agricultural commodities (beef, soy, palm oil, wood fiber, cocoa, coffee)"
    },
    "forest_area_share_land.csv": {
        "url": "https://ourworldindata.org/grapher/forest-area-as-share-of-land-area.csv",
        "source": "FAO FRA / World Bank World Development Indicators",
        "unit": "% of total land area",
        "description": "Percentage of country or global land area covered by forest"
    },
    "annual_co2_land_use.csv": {
        "url": "https://ourworldindata.org/grapher/annual-co2-emissions-from-land-use-change.csv",
        "source": "Global Carbon Project / UN FAO",
        "unit": "Tonnes CO2 / year",
        "description": "Annual carbon dioxide emissions from land-use change and deforestation"
    },
    "red_list_index.csv": {
        "url": "https://ourworldindata.org/grapher/red-list-index.csv",
        "source": "IUCN / BirdLife International",
        "unit": "Index (0 to 1)",
        "description": "IUCN Red List Index measuring aggregate species survival status and biodiversity risk"
    },
    "countries.geojson": {
        "url": "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson",
        "source": "Natural Earth / Open Data",
        "unit": "Geospatial vector polygons",
        "description": "World country administrative boundaries with ISO-3 codes"
    }
}

def download_all():
    print(f"Starting download of {len(DATASET_URLS)} authentic datasets into {RAW_DIR}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DeforestationDashboard/1.0"}
    
    for filename, info in DATASET_URLS.items():
        filepath = os.path.join(RAW_DIR, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            print(f"  [ALREADY EXISTS] {filename} ({os.path.getsize(filepath):,} bytes)")
            continue
            
        print(f"  Downloading {filename} from {info['url']}...")
        try:
            req = urllib.request.Request(info["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
                with open(filepath, "wb") as f:
                    f.write(content)
            size = os.path.getsize(filepath)
            print(f"  [SUCCESS] {filename} downloaded ({size:,} bytes)")
        except Exception as e:
            print(f"  [ERROR] Failed to download {filename}: {e}")
        time.sleep(0.5)

if __name__ == "__main__":
    download_all()

