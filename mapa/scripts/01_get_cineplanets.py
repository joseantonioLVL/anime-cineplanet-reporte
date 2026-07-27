"""Extrae coords de Cineplanets en Lima + Callao vía Nominatim (OSM)."""
import json
import time
from math import radians, cos, sin, asin, sqrt
from pathlib import Path
import requests

OUT = Path(__file__).resolve().parent.parent / "data" / "cineplanets.geojson"

# Lima + Callao bbox (aprox): south, west, north, east
BBOX = (-12.55, -77.30, -11.55, -76.70)
HEADERS = {"User-Agent": "lvl-cineplanet-catchments/1.0 (research)"}

NOMINATIM = "https://nominatim.openstreetmap.org/search"

def in_bbox(lat, lon):
    return BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]

def haversine_m(a, b):
    lat1, lon1 = a; lat2, lon2 = b
    R = 6371000
    dlat = radians(lat2 - lat1); dlon = radians(lon2 - lon1)
    x = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(x))

def fetch():
    params = {
        "q": "Cineplanet",
        "countrycodes": "pe",
        "format": "json",
        "limit": 60,
        "addressdetails": 1,
    }
    r = requests.get(NOMINATIM, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def dedupe(records, threshold_m=400):
    """Merge points closer than threshold — keep the one with longer display_name."""
    keep = []
    for rec in sorted(records, key=lambda r: -len(r["display_name"])):
        dup = False
        for k in keep:
            if haversine_m((rec["lat"], rec["lon"]), (k["lat"], k["lon"])) < threshold_m:
                dup = True; break
        if not dup:
            keep.append(rec)
    return keep

def to_records(nom):
    out = []
    for x in nom:
        lat, lon = float(x["lat"]), float(x["lon"])
        if not in_bbox(lat, lon):
            continue
        a = x.get("address", {})
        distrito = (a.get("city_district") or a.get("suburb") or a.get("town")
                    or a.get("municipality") or a.get("city") or "")
        # Refine distrito: Nominatim often labels city_district as "Lima" and puts the real district in suburb
        # For Callao specifically:
        if a.get("state") == "Callao":
            distrito = a.get("city_district") or a.get("city") or distrito
        out.append({
            "lat": lat, "lon": lon,
            "name": x.get("name") or x.get("display_name","").split(",")[0],
            "display_name": x["display_name"],
            "distrito": distrito,
            "provincia": a.get("province") or a.get("county") or "",
            "region": a.get("state") or a.get("region") or "",
            "osm_id": x.get("osm_id"),
            "osm_type": x.get("osm_type"),
        })
    return out

def to_geojson(records):
    feats = []
    for i, r in enumerate(records, 1):
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {
                "id": f"CP{i:02d}",
                "name": r["name"],
                "distrito": r["distrito"],
                "provincia": r["provincia"],
                "region": r["region"],
                "display_name": r["display_name"],
                "osm_id": r["osm_id"],
                "osm_type": r["osm_type"],
            },
        })
    return {"type": "FeatureCollection", "features": feats}

if __name__ == "__main__":
    nom = fetch()
    print(f"Nominatim devolvió {len(nom)} resultados en Perú")
    recs = to_records(nom)
    print(f"En bbox Lima+Callao: {len(recs)}")
    recs = dedupe(recs)
    print(f"Tras deduplicar (<400m): {len(recs)}")
    gj = to_geojson(recs)
    OUT.write_text(json.dumps(gj, ensure_ascii=False, indent=2))
    print(f"\n{len(gj['features'])} Cineplanets finales:")
    for f in gj["features"]:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        print(f"  {p['id']}  {lat:.4f}, {lon:.4f}  {p['name']:<25}  {p['distrito']}")
    print(f"\n-> {OUT}")
