"""Añade Plaza Santa Catalina + Canto Grande y reasigna IDs → 27 Cineplanets total."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
gj = json.loads((DATA / "cineplanets.geojson").read_text())

# Confirmados por 3 fuentes (deperu, lacartelera, mirandolacartelera)
extra = [
    {
        "lat": -12.0892615, "lon": -77.0202365,
        "name": "Cineplanet Plaza Santa Catalina",
        "distrito": "La Victoria",
        "display_name": "Plaza Santa Catalina, Calle Carlos Villarán 500, La Victoria",
        "source": "nominatim:Plaza Santa Catalina",
    },
    {
        # Real Plaza Canto Grande, Av Fernando Wiesse ~cdra 21, SJL
        "lat": -11.9720, "lon": -76.9980,
        "name": "Cineplanet Canto Grande",
        "distrito": "San Juan de Lurigancho",
        "display_name": "Real Plaza Canto Grande, Av. Fernando Wiesse cdra 21, SJL",
        "source": "manual:mirandolacartelera",
    },
]

for e in extra:
    gj["features"].append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [e["lon"], e["lat"]]},
        "properties": {
            "id": "temp",
            "name": e["name"],
            "distrito": e["distrito"],
            "provincia": "Callao" if e["distrito"] == "Ventanilla" else "Lima",
            "region": "Callao" if e["distrito"] == "Ventanilla" else "Lima",
            "display_name": e["display_name"],
            "source": e["source"],
        },
    })

# reasignar IDs N → S por latitud descendente
feats = sorted(gj["features"], key=lambda f: -f["geometry"]["coordinates"][1])
for i, f in enumerate(feats, 1):
    f["properties"]["id"] = f"CP{i:02d}"

(DATA / "cineplanets.geojson").write_text(
    json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False, indent=2)
)

print(f"Total: {len(feats)} Cineplanets Lima+Callao (verificados en deperu.com + lacartelera.pe + mirandolacartelera.com)")
for f in feats:
    p = f["properties"]; lon, lat = f["geometry"]["coordinates"]
    print(f"  {p['id']}  {lat:.4f}, {lon:.4f}  {p['name'][:30]:<30} {p.get('distrito','')}")
