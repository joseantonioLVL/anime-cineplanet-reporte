"""Completa los cines de otras cadenas con coords manuales para los que Nominatim
no encontró. Fuentes: sitios oficiales, Google Maps, deperu.com.

Salida: data/cines_all_chains.geojson con Cineplanet + otras cadenas."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Coords ya obtenidas por Nominatim en 06_get_all_chains.py (18 cines)
NOMINATIM_HITS = [
    ("Cinemark", "Jockey Plaza",       -12.0862, -76.9754, "Santiago de Surco"),
    ("Cinemark", "MegaPlaza",          -11.9946, -77.0631, "Independencia"),
    ("Cinemark", "Mallplaza Angamos",  -12.1115, -77.0118, "Surquillo"),
    ("Cinemark", "Plaza Lima Sur",     -12.1729, -77.0130, "Chorrillos"),
    ("Cinemark", "San Miguel",         -12.0769, -77.0827, "San Miguel"),
    ("Cinemark", "Mallplaza Comas",    -11.9363, -77.0655, "Comas"),
    ("Cinemark", "Gamarra",            -12.0709, -77.0125, "La Victoria"),
    ("Cinépolis", "Plaza Norte",       -12.0062, -77.0588, "Independencia"),
    ("Cinépolis", "Santa Anita",       -12.0563, -76.9711, "Santa Anita"),
    ("Cinépolis", "Larcomar",          -12.1322, -77.0302, "Miraflores"),
    ("Cinestar", "SJL",                -12.0061, -77.0048, "San Juan de Lurigancho"),
    ("Cinestar", "UNI",                -12.0125, -77.0516, "Rímac"),
    ("Cinestar", "Sur",                -12.1524, -76.9769, "San Juan de Miraflores"),
    ("MovieTime", "Chorrillos",        -12.1967, -77.0120, "Chorrillos"),
    ("MovieTime", "VES Unicachi",      -12.2013, -76.9639, "Villa El Salvador"),
    ("MovieTime", "VES1",              -12.1974, -76.9641, "Villa El Salvador"),
    ("MovieTime", "Premium Basadre",   -12.0940, -77.0382, "San Isidro"),
    ("UVK",       "El Agustino",       -12.0408, -77.0031, "El Agustino"),
    ("Cinestar", "Aviación",           -12.0846, -77.0039, "San Borja"),
    ("Cinestar", "Benavides",          -12.1312, -76.9783, "Santiago de Surco"),
    ("Cinestar", "Excelsior",          -12.0497, -77.0340, "Lima"),
    ("Cinestar", "Breña",              -12.0552, -77.0501, "Breña"),
    ("UVK",       "San Martín",        -12.0495, -77.0371, "Lima"),
]

# Coords manuales (basados en direcciones públicas + Google Maps)
MANUAL_COORDS = [
    ("Cinestar", "Comas",              -11.9420, -77.0625, "Comas"),         # Av Tupac Amaru cdra 40
    ("Cinestar", "Chorrillos SP",      -12.1729, -77.0035, "Chorrillos"),    # Av Guardia Civil cdra 8, Real Plaza Chorrillos
    ("Cinestar", "Arenales",           -12.0862, -77.0355, "Lince"),         # CC Arenales, Jr Arenales cdra 17
    ("Cinestar", "Chosica",            -11.9350, -76.7020, "Lurigancho-Chosica"),  # centro Chosica
    ("UVK",       "Platino Panorama",  -12.1524, -76.9902, "Santiago de Surco"),   # CC Panorama Bratislava
    ("Cinerama",  "Pacífico",          -12.1210, -77.0299, "Miraflores"),    # Ovalo Miraflores, Av José Larco
]

def main():
    # cargar Cineplanet
    cp = json.loads((DATA / "cineplanets.geojson").read_text())
    for f in cp["features"]:
        f["properties"]["brand"] = "Cineplanet"
        f["properties"]["sala"] = f["properties"].get("name", "")

    # combinar otras cadenas
    all_others = NOMINATIM_HITS + MANUAL_COORDS
    other_feats = []
    for i, (brand, sala, lat, lon, distrito) in enumerate(all_others, 1):
        other_feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "id": f"O{i:02d}",
                "brand": brand,
                "sala": sala,
                "name": f"{brand} {sala}",
                "distrito": distrito,
                "source": "manual" if (brand, sala, lat, lon, distrito) in MANUAL_COORDS else "nominatim",
            },
        })

    # bbox filter Lima+Callao
    BBOX = (-12.55, -77.30, -11.55, -76.70)
    def in_bbox(f):
        lon, lat = f["geometry"]["coordinates"]
        return BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]
    other_feats = [f for f in other_feats if in_bbox(f)]

    # merge Cineplanet + others
    all_feats = cp["features"] + other_feats
    for i, f in enumerate(all_feats, 1):
        f["properties"]["id_all"] = f"X{i:03d}"

    out = {"type": "FeatureCollection", "features": all_feats}
    (DATA / "cines_all_chains.geojson").write_text(json.dumps(out, ensure_ascii=False, indent=2))

    # también guardar solo other chains (para el mapa)
    other_out = {"type": "FeatureCollection", "features": other_feats}
    (DATA / "cines_other_chains.geojson").write_text(json.dumps(other_out, ensure_ascii=False, indent=2))

    # resumen por cadena
    from collections import Counter
    cnt = Counter(f["properties"]["brand"] for f in all_feats)
    print("Cines por cadena (Lima + Callao):")
    for brand, n in cnt.most_common():
        print(f"  {brand:12}: {n}")
    print(f"  TOTAL       : {sum(cnt.values())}")
    print(f"\n-> {DATA / 'cines_all_chains.geojson'}")
    print(f"-> {DATA / 'cines_other_chains.geojson'}")

if __name__ == "__main__":
    main()
