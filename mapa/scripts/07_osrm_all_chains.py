"""Matriz OSRM: cada celda del grid a cada cine de cualquier cadena (56 cines × 3042 celdas)."""
import time
import json
from pathlib import Path
import pandas as pd
import geopandas as gpd
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
BATCH = 60  # 56 cines + 60 celdas = 116 coords → ~2320 char URL, safe
OSRM_URL = "https://router.project-osrm.org/table/v1/driving"

def osrm_batch(src_coords, dest_coords, retries=3):
    n_src = len(src_coords); n_dst = len(dest_coords)
    all_c = src_coords + dest_coords
    coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in all_c)
    src_idx = ";".join(str(i) for i in range(n_src))
    dst_idx = ";".join(str(i) for i in range(n_src, n_src + n_dst))
    url = f"{OSRM_URL}/{coord_str}?sources={src_idx}&destinations={dst_idx}&annotations=duration,distance"
    for a in range(retries):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 429:
                time.sleep(5 * (a+1)); continue
            r.raise_for_status()
            d = r.json()
            if d.get("code") != "Ok":
                raise RuntimeError(str(d))
            return d
        except Exception as e:
            if a == retries - 1: raise
            print(f"    retry {a+1}: {e}"); time.sleep(3)

def main():
    all_c = gpd.read_file(DATA / "cines_all_chains.geojson")
    grid = gpd.read_file(DATA / "grid_cells.geojson")
    print(f"{len(all_c)} cines, {len(grid)} celdas → {len(all_c)*len(grid):,} pares")

    src_coords = [(f.geometry.x, f.geometry.y) for _, f in all_c.iterrows()]
    src_ids = all_c["id_all"].tolist()
    dst_coords = list(zip(grid.lon, grid.lat))
    dst_ids = grid.cell_id.tolist()

    n_batches = (len(dst_ids) + BATCH - 1) // BATCH
    print(f"Batches de {BATCH} celdas → {n_batches} requests\n")

    rows = []
    for bi in range(n_batches):
        s = bi * BATCH; e = min(s + BATCH, len(dst_ids))
        t0 = time.time()
        d = osrm_batch(src_coords, dst_coords[s:e])
        durs = d["durations"]; dists = d["distances"]
        for i, cid in enumerate(src_ids):
            for j, did in enumerate(dst_ids[s:e]):
                if durs[i][j] is None: continue
                rows.append((did, cid, durs[i][j], dists[i][j]))
        print(f"  batch {bi+1}/{n_batches}  {e-s} celdas  {time.time()-t0:.1f}s")
        time.sleep(1.0)

    mat = pd.DataFrame(rows, columns=["cell_id", "cine_id_all", "duration_s", "distance_m"])
    mat.to_parquet(DATA / "osrm_matrix_all.parquet", index=False)
    print(f"\n-> {DATA / 'osrm_matrix_all.parquet'}  ({len(mat):,} pares OK)")

if __name__ == "__main__":
    main()
