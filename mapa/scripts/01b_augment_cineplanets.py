"""Complementa la lista de Cineplanets con búsquedas por nombre específico
y con Overpass (fallback con retries). Cineplanet tiene ~30 cines en Lima+Callao,
Nominatim genérico devolvió 23."""
import json
import time
from math import radians, cos, sin, asin, sqrt
from pathlib import Path
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
BASE = DATA / "cineplanets.geojson"
OUT = DATA / "cineplanets.geojson"  # overwrite

HEADERS = {"User-Agent": "lvl-cineplanet-catchments/1.0 (research)"}
BBOX = (-12.55, -77.30, -11.55, -76.70)

# Cines conocidos que suelen faltar; buscar por texto en Nominatim
KNOWN_NAMES = [
    "Cineplanet Jockey Plaza",
    "Cineplanet Alcázar Lima",
    "Cineplanet Mall del Sur Lima",
    "Cineplanet Salaverry Lima",
    "Cineplanet Norte Lima",
    "Cineplanet Bellavista Callao",
    "Cineplanet Puruchuco Ate",
    "Cineplanet Puente Piedra",
    "Cineplanet Los Olivos",
    "Cineplanet UNI Lima",
    "Cineplanet Brasil Lima",
    "Cineplanet Villa El Salvador",
    "Cineplanet MegaPlaza",
    "Cineplanet Barranco",
    "Cineplanet Ventanilla",
    "Cineplanet Real Plaza Salaverry",
    "Cineplanet Plaza Norte Lima",
    "Cineplanet Mall Aventura Santa Anita",
    "Cineplanet Mall Aventura San Juan de Lurigancho",
    "Cineplanet Real Plaza Puruchuco",
    "Cineplanet Real Plaza Villa María",
    "Cineplanet Real Plaza Guardia Civil Chorrillos",
]

NOMINATIM = "https://nominatim.openstreetmap.org/search"

def haversine_m(a, b):
    lat1, lon1 = a; lat2, lon2 = b
    R = 6371000
    dlat = radians(lat2 - lat1); dlon = radians(lon2 - lon1)
    x = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(x))

def in_bbox(lat, lon):
    return BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]

def nom_search(q):
    p = {"q": q, "countrycodes": "pe", "format": "json", "limit": 5, "addressdetails": 1}
    try:
        r = requests.get(NOMINATIM, params=p, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  err {q}: {e}")
        return []

def try_overpass():
    q = f"""
[out:json][timeout:60];
(
  nwr["name"~"Cineplanet",i]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out center tags;
"""
    for url in ["https://overpass-api.de/api/interpreter",
                "https://overpass.kumi.systems/api/interpreter",
                "https://z.overpass-api.de/api/interpreter"]:
        try:
            print(f"Overpass: {url}")
            r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=60)
            r.raise_for_status()
            return r.json().get("elements", [])
        except Exception as e:
            print(f"  falló: {e}")
            time.sleep(2)
    return []

def main():
    gj = json.loads(BASE.read_text())
    pts = [(f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0], f["properties"]) for f in gj["features"]]
    added = 0

    # 1) búsquedas por nombre
    print("\n=== Nominatim búsquedas por nombre ===")
    for name in KNOWN_NAMES:
        res = nom_search(name)
        time.sleep(1.1)  # rate limit Nominatim
        for x in res:
            lat, lon = float(x["lat"]), float(x["lon"])
            disp = x.get("display_name","")
            if not in_bbox(lat, lon):
                continue
            if "Cineplanet" not in disp:
                continue
            # dedup
            if any(haversine_m((lat, lon), (p[0], p[1])) < 350 for p in pts):
                continue
            a = x.get("address", {})
            distrito = (a.get("city_district") or a.get("suburb") or a.get("town")
                        or a.get("city") or "")
            pts.append((lat, lon, {
                "id": f"CPx{added+1:02d}",
                "name": x.get("name") or name,
                "distrito": distrito,
                "provincia": a.get("province") or a.get("county") or "",
                "region": a.get("state") or "",
                "display_name": disp,
                "osm_id": x.get("osm_id"),
                "osm_type": x.get("osm_type"),
                "source": f"nominatim:{name}",
            }))
            added += 1
            print(f"  + {name}: {lat:.4f},{lon:.4f} {distrito}")

    # 2) Overpass fallback
    print("\n=== Overpass ===")
    elems = try_overpass()
    for el in elems:
        if el["type"] == "node":
            lat, lon = el["lat"], el["lon"]
        else:
            c = el.get("center") or {}
            lat, lon = c.get("lat"), c.get("lon")
        if lat is None or not in_bbox(lat, lon):
            continue
        if any(haversine_m((lat, lon), (p[0], p[1])) < 350 for p in pts):
            continue
        tags = el.get("tags", {})
        pts.append((lat, lon, {
            "id": f"CPo{added+1:02d}",
            "name": tags.get("name","Cineplanet"),
            "distrito": "", "provincia": "", "region": "",
            "display_name": tags.get("addr:full") or tags.get("addr:street",""),
            "osm_id": el["id"], "osm_type": el["type"],
            "source": "overpass",
        }))
        added += 1
        print(f"  + Overpass: {lat:.4f},{lon:.4f} {tags.get('name','')}")

    print(f"\nAgregados: {added}. Total: {len(pts)}")

    # reescribir con IDs consecutivos
    feats = []
    for i, (lat, lon, p) in enumerate(sorted(pts, key=lambda x: (x[0], x[1])), 1):
        p = dict(p); p["id"] = f"CP{i:02d}"
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": p,
        })
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                              ensure_ascii=False, indent=2))
    print(f"\n-> {OUT}  ({len(feats)} cines)")
    for f in feats:
        p = f["properties"]; lon, lat = f["geometry"]["coordinates"]
        print(f"  {p['id']}  {lat:.4f}, {lon:.4f}  {p.get('name','')[:30]:<30}  {p.get('distrito','')}")

if __name__ == "__main__":
    main()
