"""Distrito shp Lima+Callao + población INEI 2017."""
import io
import json
import zipfile
from pathlib import Path
import requests
import geopandas as gpd
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)

# Fuente: geoperú-style GitHub open data (peru-geojson)
DISTRITAL_URL = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_distrital_simple.geojson"

# INEI Censo 2017 por distrito (ya en Dropbox/Bases/Censo17)
POB_DTA = Path.home() / "Library/CloudStorage/Dropbox/Bases/Censo17/poblacion_por_distrito.dta"

def main():
    print("Descargando shp distrital Perú...")
    r = requests.get(DISTRITAL_URL, timeout=60)
    r.raise_for_status()
    gj = r.json()
    gdf = gpd.GeoDataFrame.from_features(gj["features"], crs="EPSG:4326")
    print(f"  {len(gdf)} distritos Perú")
    print(f"  cols: {list(gdf.columns)}")

    # Filtrar Lima+Callao
    # Estructura típica: FIRST_IDPR, FIRST_NOMB, FIRST_NOMBDIST, IDPROV, etc.
    # Probamos varias cols
    prov_col = None
    for c in gdf.columns:
        if "PROV" in c.upper() and "NOMB" in c.upper():
            prov_col = c; break
    if not prov_col:
        for c in gdf.columns:
            if c.upper().startswith("NOMB") and "PROV" in c.upper():
                prov_col = c; break
    print(f"  provincia col: {prov_col}")

    if prov_col:
        mask = gdf[prov_col].astype(str).str.upper().isin(["LIMA", "CALLAO"])
    else:
        # fallback bbox Lima+Callao
        bbox = (-77.30, -12.55, -76.70, -11.55)
        mask = gdf.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]].index
        mask = gdf.index.isin(mask)
    lc = gdf[mask].copy()
    print(f"  Lima+Callao: {len(lc)} distritos")
    print(f"  primeros: {lc.head(3).to_dict(orient='records')}")

    lc.to_file(DATA / "distritos_lima_callao.geojson", driver="GeoJSON")
    print(f"-> {DATA / 'distritos_lima_callao.geojson'}")

    # Población INEI
    if POB_DTA.exists():
        pob = pd.read_stata(POB_DTA)
        print(f"\nPoblación INEI cols: {list(pob.columns)[:10]}")
        print(pob.head())
        pob.to_csv(DATA / "poblacion_distrito_inei2017.csv", index=False)
        print(f"-> {DATA / 'poblacion_distrito_inei2017.csv'}")
    else:
        print(f"\n(!) No encontré {POB_DTA}")

if __name__ == "__main__":
    main()
