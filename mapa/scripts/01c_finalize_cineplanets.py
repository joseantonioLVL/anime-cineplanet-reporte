"""Añade Salaverry y El Polo (confirmados en lacartelera.pe faltantes en Nominatim genérico)
y reasigna IDs consecutivos."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
gj = json.loads((DATA / "cineplanets.geojson").read_text())

extra = [
    {
        "lat": -12.0898845, "lon": -77.0527159,
        "name": "Cineplanet Salaverry",
        "distrito": "Jesús María",
        "display_name": "Real Plaza Salaverry, Av General Salaverry 2370, Jesús María",
        "source": "nominatim:Real Plaza Salaverry",
    },
    {
        "lat": -12.1013806, "lon": -76.9709242,
        "name": "Cineplanet El Polo",
        "distrito": "Santiago de Surco",
        "display_name": "Centro Comercial El Polo, Av El Polo 670-740, Surco",
        "source": "nominatim:CC El Polo",
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
            "provincia": "Lima" if e["distrito"] != "Ventanilla" else "Callao",
            "region": "Lima" if e["distrito"] != "Ventanilla" else "Callao",
            "display_name": e["display_name"],
            "source": e["source"],
        },
    })

# reasignar IDs por lat descendente (N a S)
feats = sorted(gj["features"], key=lambda f: -f["geometry"]["coordinates"][1])
for i, f in enumerate(feats, 1):
    f["properties"]["id"] = f"CP{i:02d}"

out = {"type": "FeatureCollection", "features": feats}
(DATA / "cineplanets.geojson").write_text(json.dumps(out, ensure_ascii=False, indent=2))

print(f"Total: {len(feats)} Cineplanets Lima+Callao")
for f in feats:
    p = f["properties"]; lon, lat = f["geometry"]["coordinates"]
    print(f"  {p['id']}  {lat:.4f}, {lon:.4f}  {p['name'][:28]:<28} {p.get('distrito','')}")
