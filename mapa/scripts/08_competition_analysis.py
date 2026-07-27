"""Analiza competencia:
  1. Catchments Voronoi por tiempo con TODAS las cadenas
  2. Métricas por Cineplanet: pob en catchment solo-CP vs. catchment competitivo, competidor más cercano
  3. Métricas por cadena: cines, área capturada, población capturada, share
"""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask as rio_mask

DATA = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "output"

def wp_per_geom(geoms, tif_path):
    """Suma WorldPop dentro de cada geometría."""
    out = []
    with rasterio.open(tif_path) as src:
        if hasattr(geoms, "crs") and geoms.crs != src.crs:
            geoms = geoms.to_crs(src.crs)
        for g in geoms:
            try:
                arr, _ = rio_mask(src, [g.__geo_interface__], crop=True, filled=False, nodata=src.nodata)
                a = arr[0]
                if hasattr(a, "mask"):
                    v = float(a.data[(~a.mask) & (a.data > 0)].sum())
                else:
                    v = float(np.where(a > 0, a, 0).sum())
                out.append(max(0.0, v))
            except Exception:
                out.append(0.0)
    return out

def main():
    all_c = gpd.read_file(DATA / "cines_all_chains.geojson")
    grid = gpd.read_file(DATA / "grid_cells.geojson")
    mat_all = pd.read_parquet(DATA / "osrm_matrix_all.parquet")
    catch_cp = gpd.read_file(OUT_DIR / "catchments.geojson")

    # Etiquetar mat_all con brand
    id_to_brand = dict(zip(all_c["id_all"], all_c["brand"]))
    id_to_cpid = dict(zip(all_c["id_all"], all_c["id"]))  # CP01..CP27 para Cineplanet
    mat_all["brand"] = mat_all["cine_id_all"].map(id_to_brand)

    print(f"Cines: {len(all_c)}  Grid: {len(grid)}  Matriz all: {len(mat_all):,}")

    # ==== 1. Nearest ANY cine por celda ====
    idx = mat_all.groupby("cell_id")["duration_s"].idxmin()
    nearest_all = mat_all.loc[idx][["cell_id", "cine_id_all", "duration_s", "distance_m", "brand"]].reset_index(drop=True)
    all_c_meta = all_c[["id_all", "sala", "name", "distrito"]].rename(columns={"id_all":"cine_id_all"})
    nearest_all = nearest_all.merge(all_c_meta, on="cine_id_all")

    # ==== 2. Nearest Cineplanet por celda (derivado desde mat_all filtrando brand) ====
    mat_cp = mat_all[mat_all["brand"] == "Cineplanet"].copy()
    mat_cp["cine_id"] = mat_cp["cine_id_all"].map(id_to_cpid)
    idx_cp = mat_cp.groupby("cell_id")["duration_s"].idxmin()
    nearest_cp = mat_cp.loc[idx_cp][["cell_id", "cine_id", "duration_s", "distance_m"]].reset_index(drop=True)
    nearest_cp = nearest_cp.rename(columns={"duration_s": "dur_cp", "distance_m": "dist_cp"})

    # Unir: cada celda con cine cp más cercano + cine cualquiera más cercano
    joined = grid[["cell_id", "geometry"]].merge(nearest_all, on="cell_id").merge(nearest_cp, on="cell_id")

    # Delta tiempo (positive = competidor más cerca)
    joined["ganada_por_cp"] = joined["brand"] == "Cineplanet"
    joined["delta_dur_min"] = (joined["dur_cp"] - joined["duration_s"]) / 60  # positivo = CP más lejos

    # ==== 3. Población por celda (WorldPop) ====
    print("Calculando WorldPop por celda...")
    joined["pob_wp"] = wp_per_geom(joined.geometry, DATA / "worldpop_peru_2020.tif")

    # ==== 4. Catchments competitivos por cine (todas las cadenas) ====
    # dissolver por cine_id_all
    g_utm = joined.to_crs(32718)
    catch_all = g_utm.dissolve(by="cine_id_all", as_index=False)
    catch_all["geometry"] = catch_all.geometry.simplify(80)
    catch_all = catch_all.to_crs(4326)
    catch_all = catch_all[["cine_id_all","brand","name","distrito","geometry"]]

    # Métricas por cine competitivo
    per_cine_comp = joined.groupby("cine_id_all").agg(
        n_cells=("cell_id","count"),
        pob_wp=("pob_wp","sum"),
        dur_min_avg=("duration_s", lambda s: s.mean()/60),
        dur_p50=("duration_s", lambda s: s.median()/60),
        dur_p90=("duration_s", lambda s: s.quantile(0.9)/60),
    ).reset_index()
    catch_all = catch_all.merge(per_cine_comp, on="cine_id_all")
    catch_all["area_km2"] = catch_all.to_crs(32718).geometry.area / 1e6

    catch_all.to_file(OUT_DIR / "catchments_all_chains.geojson", driver="GeoJSON")
    print(f"-> catchments_all_chains.geojson  ({len(catch_all)} cines)")

    # ==== 5. Métricas por CADENA ====
    per_brand = catch_all.groupby("brand").agg(
        n_cines=("cine_id_all","count"),
        area_km2=("area_km2","sum"),
        pob_wp=("pob_wp","sum"),
    ).reset_index()
    total_area = per_brand["area_km2"].sum()
    total_pob = per_brand["pob_wp"].sum()
    per_brand["share_area_pct"] = per_brand["area_km2"] / total_area * 100
    per_brand["share_pob_pct"] = per_brand["pob_wp"] / total_pob * 100
    per_brand["pob_per_cine"] = per_brand["pob_wp"] / per_brand["n_cines"]
    per_brand = per_brand.sort_values("share_pob_pct", ascending=False)
    per_brand.to_csv(OUT_DIR / "share_por_cadena.csv", index=False)

    print("\n=== Share territorial y poblacional por cadena ===")
    print(per_brand.to_string(index=False))

    # ==== 6. Métricas de competencia por CADA Cineplanet ====
    # Para cada catchment CP-only: cuánta población efectivamente captura en universo competitivo
    # (o sea, la intersección del catchment CP-only con el catchment competitivo del mismo cine)
    # Simplificación: comparar pob_wp del catchment CP-only vs pob_wp del catchment competitivo del mismo cine
    cp_only = catch_cp[["cine_id","name","distrito","pob_worldpop","area_km2","dur_min_avg"]].copy()
    cp_only = cp_only.rename(columns={"pob_worldpop":"pob_cp_only","area_km2":"area_cp_only","dur_min_avg":"dur_cp_only"})

    # match Cineplanet id CP01..CP27 → cine_id_all X001..X027 (los primeros 27)
    cp_all_map = dict(zip(all_c[all_c["brand"]=="Cineplanet"]["id"],
                          all_c[all_c["brand"]=="Cineplanet"]["id_all"]))
    cp_only["cine_id_all"] = cp_only["cine_id"].map(cp_all_map)

    comp = cp_only.merge(catch_all[["cine_id_all","pob_wp","area_km2","dur_min_avg","dur_p90"]].rename(
        columns={"pob_wp":"pob_competitivo","area_km2":"area_competitivo","dur_min_avg":"dur_competitivo","dur_p90":"dur_comp_p90"}
    ), on="cine_id_all")
    comp["pob_perdida"] = comp["pob_cp_only"] - comp["pob_competitivo"]
    comp["pct_pob_retenida"] = comp["pob_competitivo"] / comp["pob_cp_only"] * 100
    comp["area_perdida"] = comp["area_cp_only"] - comp["area_competitivo"]
    comp["pct_area_retenida"] = comp["area_competitivo"] / comp["area_cp_only"] * 100

    # Competidor más cercano por Cineplanet (por distancia entre puntos)

    # Para cada cine CP, buscar el competidor con celdas más cercanas en promedio
    # Simplificación: distancia entre puntos de cines
    cp_pts = all_c[all_c["brand"]=="Cineplanet"][["id","geometry"]].to_crs(32718)
    other_pts = all_c[all_c["brand"]!="Cineplanet"][["brand","name","sala","geometry"]].to_crs(32718)

    nearest_comp = []
    for _, cp in cp_pts.iterrows():
        d = other_pts.distance(cp["geometry"])
        i = d.idxmin()
        r = other_pts.loc[i]
        nearest_comp.append({
            "cine_id": cp["id"],
            "competidor": r["name"],
            "comp_brand": r["brand"],
            "comp_dist_m": float(d.loc[i]),
        })
    nc = pd.DataFrame(nearest_comp)
    comp = comp.merge(nc, on="cine_id")

    comp = comp[["cine_id","name","distrito",
                  "pob_cp_only","pob_competitivo","pob_perdida","pct_pob_retenida",
                  "area_cp_only","area_competitivo","pct_area_retenida",
                  "dur_cp_only","dur_competitivo",
                  "competidor","comp_brand","comp_dist_m"]]
    comp = comp.sort_values("pob_perdida", ascending=False)
    comp.to_csv(OUT_DIR / "cineplanet_competencia.csv", index=False)

    print("\n=== Top 5 Cineplanets con más población 'perdida' a la competencia ===")
    print(comp.head(5).to_string(index=False))

    # ==== 7. Cell-level: pintar solo las zonas "perdidas por CP" con brand ganador ====
    joined["perdida"] = ~joined["ganada_por_cp"]
    lost = joined[joined["perdida"]].copy()
    if len(lost) > 0:
        lost_utm = lost.to_crs(32718)
        # dissolver por brand ganador
        lost_by_brand = lost_utm[["brand","geometry"]].dissolve(by="brand", as_index=False)
        lost_by_brand["geometry"] = lost_by_brand.geometry.simplify(100)
        lost_by_brand = lost_by_brand.to_crs(4326)
        lost_by_brand["pob_wp"] = [
            joined[(joined["perdida"]) & (joined["brand"]==b)]["pob_wp"].sum()
            for b in lost_by_brand["brand"]
        ]
        lost_by_brand.to_file(OUT_DIR / "zonas_perdidas_por_brand.geojson", driver="GeoJSON")
        print(f"\n-> zonas_perdidas_por_brand.geojson ({len(lost_by_brand)} cadenas competidoras)")

    print("\nGenerados en output/:")
    print("  - catchments_all_chains.geojson")
    print("  - share_por_cadena.csv")
    print("  - cineplanet_competencia.csv")
    print("  - zonas_perdidas_por_brand.geojson")

if __name__ == "__main__":
    main()
