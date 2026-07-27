"""Genera grid Lima+Callao (dentro del polígono) y computa tiempo en auto
desde cada Cineplanet a cada celda usando OSRM público.

Guarda:
  data/grid_cells.geojson (celdas con centroide y distrito)
  data/osrm_matrix.parquet (celda_id × cine_id → duracion_seg, distancia_m)
"""
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import Point, box

DATA = Path(__file__).resolve().parent.parent / "data"

GRID_SIZE_M = 1000  # 1 km grid
BATCH_DEST = 80     # celdas por request (25 cines + 80 celdas = 105 coords ~ 2100 char URL)
OSRM_URL = "https://router.project-osrm.org/table/v1/driving"

def load():
    cines = gpd.read_file(DATA / "cineplanets.geojson")
    distritos = gpd.read_file(DATA / "distritos_lima_callao.geojson")
    return cines, distritos

def build_grid(distritos, cell_size_m=GRID_SIZE_M):
    d_utm = distritos.to_crs(32718)
    minx, miny, maxx, maxy = d_utm.total_bounds
    xs = np.arange(minx, maxx, cell_size_m)
    ys = np.arange(miny, maxy, cell_size_m)
    cells = [box(x, y, x + cell_size_m, y + cell_size_m) for x in xs for y in ys]
    grid = gpd.GeoDataFrame(geometry=cells, crs=32718)
    dissolved = d_utm.union_all()
    grid = grid[grid.geometry.intersects(dissolved)].reset_index(drop=True)
    cents_utm = grid.geometry.centroid
    grid["utm_x"] = cents_utm.x.values
    grid["utm_y"] = cents_utm.y.values

    # asignar distrito por centroide
    dist_col = None
    for c in distritos.columns:
        if c.upper() in ("NOMBDIST", "DISTRITO") or "NOMBDIST" in c.upper():
            dist_col = c; break
    if not dist_col:
        for c in distritos.columns:
            if "NOMB" in c.upper() and "DIST" in c.upper():
                dist_col = c; break
    print(f"  distrito col: {dist_col}")
    cent_gdf = gpd.GeoDataFrame(geometry=cents_utm.values, crs=32718)
    joined = gpd.sjoin(cent_gdf, d_utm[[dist_col, "geometry"]] if dist_col else d_utm[["geometry"]],
                       how="left", predicate="within")
    grid["distrito"] = joined[dist_col].values if dist_col else ""

    cent_ll = grid.to_crs(4326).geometry.centroid
    grid["lat"] = cent_ll.y.values
    grid["lon"] = cent_ll.x.values
    grid["cell_id"] = [f"C{i:05d}" for i in range(len(grid))]
    return grid

def osrm_batch(cines_coords, dest_coords, retries=3):
    """cines_coords, dest_coords: list of (lon, lat)."""
    n_src = len(cines_coords)
    n_dst = len(dest_coords)
    all_coords = cines_coords + dest_coords
    coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in all_coords)
    src_idx = ";".join(str(i) for i in range(n_src))
    dst_idx = ";".join(str(i) for i in range(n_src, n_src + n_dst))
    url = f"{OSRM_URL}/{coord_str}?sources={src_idx}&destinations={dst_idx}&annotations=duration,distance"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=45)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1)); continue
            r.raise_for_status()
            d = r.json()
            if d.get("code") != "Ok":
                raise RuntimeError(f"OSRM: {d}")
            return d
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"    retry {attempt+1}: {e}")
            time.sleep(3)

def main():
    cines, distritos = load()
    print(f"{len(cines)} cines, {len(distritos)} distritos")
    print("Construyendo grid...")
    grid = build_grid(distritos, GRID_SIZE_M)
    print(f"  {len(grid)} celdas dentro de Lima+Callao")
    grid.to_file(DATA / "grid_cells.geojson", driver="GeoJSON")

    cine_coords = [(f["geometry"].x, f["geometry"].y) for _, f in cines.iterrows()]
    cine_ids = cines["id"].tolist()
    cells_ll = list(zip(grid.lon, grid.lat))
    cell_ids = grid.cell_id.tolist()

    print(f"\nOSRM: {len(cine_ids)} cines × {len(cell_ids)} celdas = {len(cine_ids)*len(cell_ids):,} pares")
    print(f"  batches de {BATCH_DEST} celdas → {(len(cell_ids)+BATCH_DEST-1)//BATCH_DEST} requests\n")

    rows = []
    n_batches = (len(cell_ids) + BATCH_DEST - 1) // BATCH_DEST
    for bi in range(n_batches):
        start = bi * BATCH_DEST
        stop = min(start + BATCH_DEST, len(cell_ids))
        dests = cells_ll[start:stop]
        did = cell_ids[start:stop]
        t0 = time.time()
        d = osrm_batch(cine_coords, dests)
        durs = d["durations"]     # [n_src][n_dst]
        dists = d["distances"]
        for i, cid in enumerate(cine_ids):
            for j, sid in enumerate(did):
                dur = durs[i][j]; dis = dists[i][j]
                if dur is None:
                    continue
                rows.append((sid, cid, dur, dis))
        dt = time.time() - t0
        print(f"  batch {bi+1}/{n_batches}  {len(dests)} celdas  {dt:.1f}s")
        time.sleep(1.0)  # rate limit friendly

    mat = pd.DataFrame(rows, columns=["cell_id", "cine_id", "duration_s", "distance_m"])
    mat.to_parquet(DATA / "osrm_matrix.parquet", index=False)
    print(f"\n-> {DATA / 'osrm_matrix.parquet'}  ({len(mat):,} pares OK)")

if __name__ == "__main__":
    main()
