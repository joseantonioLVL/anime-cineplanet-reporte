"""Construye catchments por cine (grid cell → cine con min tiempo) y agrega población
desde INEI 2017 (distrito) y WorldPop 2020 (raster 100m)."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask as rio_mask
from shapely.geometry import shape as shp_shape
from shapely.ops import unary_union

DATA = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUT_DIR.mkdir(exist_ok=True)

def load_all():
    cines = gpd.read_file(DATA / "cineplanets.geojson")
    distritos = gpd.read_file(DATA / "distritos_lima_callao.geojson")
    grid = gpd.read_file(DATA / "grid_cells.geojson")
    mat = pd.read_parquet(DATA / "osrm_matrix.parquet")
    pob_inei = pd.read_csv(DATA / "poblacion_distrito_inei2017.csv")
    return cines, distritos, grid, mat, pob_inei

def assign_nearest(mat, cines):
    """Para cada cell, escoger el cine con min duración."""
    idx = mat.groupby("cell_id")["duration_s"].idxmin()
    nearest = mat.loc[idx].reset_index(drop=True)
    return nearest[["cell_id", "cine_id", "duration_s", "distance_m"]]

def worldpop_per_cell(grid, tif_path):
    """Sum WorldPop pop for each grid cell polygon. Grid se reproyecta al CRS del raster."""
    pop_vals = []
    with rasterio.open(tif_path) as src:
        grid_r = grid.to_crs(src.crs) if grid.crs != src.crs else grid
        for geom in grid_r.geometry:
            try:
                out, _ = rio_mask(src, [geom.__geo_interface__], crop=True, filled=False, all_touched=False, nodata=src.nodata)
                arr = out[0]
                if hasattr(arr, "mask"):
                    v = float(arr.data[(~arr.mask) & (arr.data > 0)].sum())
                else:
                    v = float(np.where(arr > 0, arr, 0).sum())
                pop_vals.append(max(0.0, v))
            except Exception:
                pop_vals.append(0.0)
    return pop_vals

def inei_per_cell(grid, distritos, pob_inei):
    """Reparte pob INEI (por ubigeo IDDIST) entre celdas por proporción de área."""
    d_utm = distritos[["IDDIST", "NOMBDIST", "geometry"]].to_crs(32718)
    g_utm = grid[["cell_id", "geometry"]].to_crs(32718)
    inter = gpd.overlay(g_utm, d_utm, how="intersection", keep_geom_type=True)
    inter["area_m2"] = inter.geometry.area
    dist_area = inter.groupby("IDDIST")["area_m2"].sum().rename("dist_area_m2")
    inter = inter.join(dist_area, on="IDDIST")
    inter["frac"] = inter["area_m2"] / inter["dist_area_m2"]

    # INEI: ubigeo (6 dig, string con leading zero) → conteo
    pob_inei = pob_inei.copy()
    pob_inei["ubigeo"] = pob_inei["ubigeo"].astype(str).str.zfill(6)
    pob_map = dict(zip(pob_inei["ubigeo"], pob_inei["conteo"]))
    inter["IDDIST_str"] = inter["IDDIST"].astype(str).str.zfill(6)
    inter["pob_dist"] = inter["IDDIST_str"].map(pob_map).fillna(0)
    inter["pob_cell"] = inter["pob_dist"] * inter["frac"]
    per_cell = inter.groupby("cell_id")["pob_cell"].sum()
    return per_cell.to_dict()

def build_catchments(grid_utm, nearest, cines):
    """Disolver grid por cine asignado → polígono catchment por cine."""
    g = grid_utm[["cell_id", "geometry"]].merge(nearest[["cell_id", "cine_id"]], on="cell_id", how="left")
    g = g.dropna(subset=["cine_id"])
    catch = g.dissolve(by="cine_id", as_index=False)
    catch["geometry"] = catch.geometry.simplify(80)
    catch = catch.to_crs(4326)
    catch = catch.merge(cines[["id", "name", "distrito"]].rename(columns={"id": "cine_id"}), on="cine_id")
    return catch

def main():
    cines, distritos, grid, mat, pob_inei = load_all()
    print(f"Cines: {len(cines)}  Distritos: {len(distritos)}  Grid: {len(grid)}  Matrix: {len(mat)}")

    nearest = assign_nearest(mat, cines)
    print(f"\nAsignación nearest lista: {len(nearest)} cells con cine")

    # WorldPop pop por celda
    print("\nWorldPop por celda...")
    grid["pob_worldpop"] = worldpop_per_cell(grid, DATA / "worldpop_peru_2020.tif")
    print(f"  total WorldPop en Lima+Callao: {grid['pob_worldpop'].sum():,.0f}")

    # INEI pop por celda (repartido por área)
    print("\nINEI por celda...")
    pob_inei_map = inei_per_cell(grid, distritos, pob_inei)
    grid["pob_inei"] = grid["cell_id"].map(pob_inei_map).fillna(0)
    print(f"  total INEI en Lima+Callao: {grid['pob_inei'].sum():,.0f}")

    # Merge nearest + pop
    grid = grid.merge(nearest, on="cell_id", how="left")
    grid.to_file(OUT_DIR / "grid_asignado.geojson", driver="GeoJSON")

    # Catchments dissolved
    print("\nDisolviendo catchments...")
    catch = build_catchments(grid.to_crs(32718), nearest, cines)

    # Agregar población + métricas por catchment
    per_cine = grid.dropna(subset=["cine_id"]).groupby("cine_id").agg(
        n_cells=("cell_id", "count"),
        pob_inei=("pob_inei", "sum"),
        pob_worldpop=("pob_worldpop", "sum"),
        dur_min_avg=("duration_s", lambda s: s.mean() / 60),
        dur_p50_min=("duration_s", lambda s: s.median() / 60),
        dur_p90_min=("duration_s", lambda s: s.quantile(0.9) / 60),
        dist_avg_km=("distance_m", lambda s: s.mean() / 1000),
    ).reset_index()
    catch = catch.merge(per_cine, on="cine_id")
    # area_km2 desde el polígono catchment en UTM
    catch["area_km2"] = catch.to_crs(32718).geometry.area.values / 1e6
    # densidad
    catch["dens_worldpop_km2"] = catch["pob_worldpop"] / catch["area_km2"]
    catch["dens_inei_km2"] = catch["pob_inei"] / catch["area_km2"]

    catch.to_file(OUT_DIR / "catchments.geojson", driver="GeoJSON")

    # Tabla
    tbl = catch.drop(columns=["geometry"]).sort_values("pob_worldpop", ascending=False)
    tbl.to_csv(OUT_DIR / "catchments_summary.csv", index=False)
    print("\n=== Ranking por población WorldPop ===")
    print(tbl.to_string(index=False))

    print(f"\n-> {OUT_DIR}/catchments.geojson")
    print(f"-> {OUT_DIR}/catchments_summary.csv")

if __name__ == "__main__":
    main()
