"""Geocodifica todos los cines de todas las cadenas en Lima+Callao vía Nominatim.

Fuentes cruzadas: lacartelera.pe, deperu.com, mirandolacartelera.com.
Guarda: data/cines_all_chains.geojson (Cineplanet + Cinemark + Cinépolis + Cinestar + MovieTime + UVK + otros).
"""
import json
import time
from math import radians, cos, sin, asin, sqrt
from pathlib import Path
import requests

DATA = Path(__file__).resolve().parent.parent / "data"
HEADERS = {"User-Agent": "lvl-cine-catchments/1.0 (research)"}
NOMINATIM = "https://nominatim.openstreetmap.org/search"
BBOX = (-12.55, -77.30, -11.55, -76.70)

# Lista curada: (brand, name, address_or_mall_for_geocoding, distrito)
CINES = [
    # ---------- Cinemark (7) ----------
    ("Cinemark", "Jockey Plaza",       "Jockey Plaza Santiago de Surco Lima", "Santiago de Surco"),
    ("Cinemark", "MegaPlaza",          "MegaPlaza Independencia Lima",         "Independencia"),
    ("Cinemark", "Mallplaza Angamos",  "Mallplaza Angamos Surquillo Lima",     "Surquillo"),
    ("Cinemark", "Plaza Lima Sur",     "Plaza Lima Sur Chorrillos Lima",       "Chorrillos"),
    ("Cinemark", "San Miguel",         "Plaza San Miguel Lima",                "San Miguel"),
    ("Cinemark", "Mallplaza Comas",    "Mall Plaza Comas Lima",                "Comas"),
    ("Cinemark", "Gamarra",            "Gamarra Plaza La Victoria Lima",       "La Victoria"),

    # ---------- Cinépolis (3) ----------
    ("Cinépolis", "Plaza Norte",       "Plaza Norte Independencia Lima",       "Independencia"),
    ("Cinépolis", "Santa Anita",       "Mall Aventura Santa Anita Lima",       "Santa Anita"),
    ("Cinépolis", "Larcomar",          "Larcomar Miraflores Lima",             "Miraflores"),

    # ---------- Cinestar (11) ----------
    ("Cinestar", "Aviación",           "Cinestar Aviación La Victoria Lima",   "La Victoria"),
    ("Cinestar", "Benavides",          "Cinestar Benavides Surco Lima",        "Santiago de Surco"),
    ("Cinestar", "Excelsior",          "Cinestar Excelsior Jr Union Lima",     "Lima"),
    ("Cinestar", "Breña",              "Cinestar Breña Av Venezuela Lima",     "Breña"),
    ("Cinestar", "Comas",              "Cinestar Comas Av Tupac Amaru",        "Comas"),
    ("Cinestar", "San Juan de Lurigancho","Cinestar San Juan Lurigancho Lima", "San Juan de Lurigancho"),
    ("Cinestar", "UNI",                "Cinestar UNI Rimac Lima",              "Rímac"),
    ("Cinestar", "Chorrillos SP",      "Cinestar Chorrillos Av Guardia Civil Lima","Chorrillos"),
    ("Cinestar", "Sur",                "Cinestar Sur San Juan Miraflores Lima","San Juan de Miraflores"),
    ("Cinestar", "Chosica",            "Chosica Lurigancho Lima",              "Lurigancho-Chosica"),
    ("Cinestar", "Arenales",           "Cinestar Arenales Lince Lima",         "Lince"),

    # ---------- MovieTime (4) ----------
    ("MovieTime", "Chorrillos",        "MovieTime Chorrillos Lima",            "Chorrillos"),
    ("MovieTime", "VES Unicachi",      "Unicachi Villa El Salvador Lima",      "Villa El Salvador"),
    ("MovieTime", "VES1",              "MovieTime Villa El Salvador Lima",     "Villa El Salvador"),
    ("MovieTime", "Premium Basadre",   "Basadre San Isidro Lima",              "San Isidro"),

    # ---------- UVK (3) ----------
    ("UVK", "Platino Panorama",        "UVK Panorama Santiago de Surco Lima",  "Santiago de Surco"),
    ("UVK", "San Martín",              "UVK San Martin Jr Ocoña Lima",         "Lima"),
    ("UVK", "El Agustino",             "UVK El Agustino Lima",                 "El Agustino"),

    # ---------- Cinerama ----------
    ("Cinerama", "Pacífico",           "Cinerama Pacifico Miraflores Ovalo Lima", "Miraflores"),
]

def in_bbox(lat, lon):
    return BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]

def haversine_m(a, b):
    lat1, lon1 = a; lat2, lon2 = b
    R = 6371000
    dlat = radians(lat2 - lat1); dlon = radians(lon2 - lon1)
    x = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*R*asin(sqrt(x))

def nom_search(q, limit=3):
    p = {"q": q, "countrycodes": "pe", "format": "json", "limit": limit, "addressdetails": 1}
    try:
        r = requests.get(NOMINATIM, params=p, headers=HEADERS, timeout=15)
        return r.json()
    except Exception:
        return []

def main():
    feats = []
    fallbacks = []
    for brand, name, q, distrito in CINES:
        res = nom_search(q)
        time.sleep(1.1)
        hits = [x for x in res if in_bbox(float(x["lat"]), float(x["lon"]))]
        if hits:
            x = hits[0]
            lat, lon = float(x["lat"]), float(x["lon"])
            src = f"nominatim:{q}"
            disp = x.get("display_name", "")[:100]
        else:
            fallbacks.append((brand, name, q, distrito))
            print(f"  MISSED: {brand} · {name}  ({q})")
            continue
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "brand": brand, "name": f"{brand} {name}",
                "sala": name, "distrito": distrito,
                "display_name": disp, "source": src,
            },
        })
        print(f"  OK {brand:10} · {name:30} {lat:.4f},{lon:.4f}")

    print(f"\nTotal geocodificados: {len(feats)} / {len(CINES)}")
    if fallbacks:
        print(f"Sin match ({len(fallbacks)}): revisar manualmente")
        for f in fallbacks:
            print(f"  - {f}")

    # dedup por proximidad < 200m dentro de la misma cadena
    keep = []
    for f in feats:
        lat, lon = f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]
        dup = False
        for k in keep:
            klat, klon = k["geometry"]["coordinates"][1], k["geometry"]["coordinates"][0]
            if k["properties"]["brand"] == f["properties"]["brand"]:
                if haversine_m((lat, lon), (klat, klon)) < 200:
                    dup = True; break
        if not dup:
            keep.append(f)
    print(f"Tras dedup por brand+prox: {len(keep)}")

    # asignar id
    for i, f in enumerate(sorted(keep, key=lambda x: (x["properties"]["brand"], x["properties"]["sala"])), 1):
        f["properties"]["id"] = f"O{i:02d}"

    out = {"type": "FeatureCollection", "features": keep}
    (DATA / "cines_other_chains.geojson").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n-> {DATA / 'cines_other_chains.geojson'}")

if __name__ == "__main__":
    main()
