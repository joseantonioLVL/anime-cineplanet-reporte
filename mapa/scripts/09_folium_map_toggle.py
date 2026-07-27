"""Mapa Folium con toggle entre 3 vistas:
  1. Solo Cineplanet — 27 catchments Voronoi por tiempo (visualización original)
  2. Todas las cadenas — 56 catchments coloreados por cadena
  3. Vista competencia — CP catchments en gris + zonas 'perdidas a la competencia' en color por cadena
"""
from pathlib import Path
import json
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
from branca.element import Template, MacroElement

DATA = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "output"

CENTER = [-12.05, -77.03]
ZOOM = 11

BRAND_COLORS = {
    "Cineplanet": "#e53935",   # rojo
    "Cinemark":   "#1e88e5",   # azul
    "Cinépolis":  "#8e24aa",   # morado
    "Cinestar":   "#43a047",   # verde
    "MovieTime":  "#f57c00",   # naranja
    "UVK":        "#00acc1",   # cyan
    "Cinerama":   "#6d4c41",   # marrón
}

def main():
    all_c = gpd.read_file(DATA / "cines_all_chains.geojson")
    catch_cp = gpd.read_file(OUT_DIR / "catchments.geojson")
    catch_all = gpd.read_file(OUT_DIR / "catchments_all_chains.geojson")
    comp_cp = pd.read_csv(OUT_DIR / "cineplanet_competencia.csv")
    share_brand = pd.read_csv(OUT_DIR / "share_por_cadena.csv")
    lost_zones = gpd.read_file(OUT_DIR / "zonas_perdidas_por_brand.geojson") if (OUT_DIR / "zonas_perdidas_por_brand.geojson").exists() else None

    m = folium.Map(location=CENTER, zoom_start=ZOOM, tiles="cartodbpositron", control_scale=True)
    Fullscreen().add_to(m)

    # ============================================================
    # CAPA 1: Solo Cineplanet
    # ============================================================
    pmax = float(catch_cp["pob_worldpop"].max())
    cmap_cp = LinearColormap(
        ["#fff5f0", "#fcbba1", "#fb6a4a", "#cb181d", "#67000d"],
        vmin=0, vmax=pmax, caption="Población (WorldPop 2020) — vista solo Cineplanet"
    )
    grp_cp = folium.FeatureGroup(name="Vista 1: Solo Cineplanet (Voronoi tiempo)", show=True)

    def style_cp(feat):
        pop = feat["properties"]["pob_worldpop"]
        return {"fillColor": cmap_cp(pop), "color": "#7f0000", "weight": 1.2, "fillOpacity": 0.55}

    tooltip_cp = folium.GeoJsonTooltip(
        fields=["cine_id","name","distrito","pob_worldpop","pob_inei","area_km2","dur_min_avg","dur_p50_min","dur_p90_min"],
        aliases=["Cine ID","Nombre","Distrito","Pob WorldPop","Pob INEI","Área km²","Tiempo prom (min)","Mediana (min)","P90 (min)"],
        localize=True, sticky=True,
    )
    folium.GeoJson(catch_cp.__geo_interface__, style_function=style_cp, tooltip=tooltip_cp,
                   highlight_function=lambda f: {"weight":3,"color":"#000","fillOpacity":0.75}).add_to(grp_cp)
    grp_cp.add_to(m)

    # ============================================================
    # CAPA 2: Todas las cadenas — catchments coloreados por brand
    # ============================================================
    grp_all = folium.FeatureGroup(name="Vista 2: Todas las cadenas (56 cines)", show=False)

    def style_all(feat):
        brand = feat["properties"]["brand"]
        color = BRAND_COLORS.get(brand, "#666")
        return {"fillColor": color, "color": "#333", "weight": 1.0, "fillOpacity": 0.55}

    tooltip_all = folium.GeoJsonTooltip(
        fields=["brand","name","distrito","pob_wp","area_km2","dur_min_avg","dur_p90"],
        aliases=["Cadena","Cine","Distrito","Población capturada","Área km²","Tiempo prom (min)","P90 (min)"],
        localize=True, sticky=True,
    )
    folium.GeoJson(catch_all.__geo_interface__, style_function=style_all, tooltip=tooltip_all,
                   highlight_function=lambda f: {"weight":3,"color":"#000","fillOpacity":0.75}).add_to(grp_all)
    grp_all.add_to(m)

    # ============================================================
    # CAPA 3: Vista competencia — CP en gris + zonas perdidas por competidor
    # ============================================================
    grp_comp = folium.FeatureGroup(name="Vista 3: Territorio ganado por competencia a CP", show=False)

    # CP en gris (fondo)
    folium.GeoJson(catch_cp.__geo_interface__,
                   style_function=lambda f: {"fillColor":"#bbbbbb","color":"#666","weight":0.8,"fillOpacity":0.35},
                   tooltip=folium.GeoJsonTooltip(
                       fields=["name","distrito","pob_worldpop"],
                       aliases=["Cineplanet","Distrito","Pob (si no hubiera competencia)"])
                   ).add_to(grp_comp)

    # Zonas perdidas coloreadas por brand ganador
    if lost_zones is not None and len(lost_zones) > 0:
        def style_lost(feat):
            b = feat["properties"]["brand"]
            return {"fillColor": BRAND_COLORS.get(b,"#666"), "color":"#111",
                    "weight":1.2, "fillOpacity":0.7}
        folium.GeoJson(lost_zones.__geo_interface__, style_function=style_lost,
                       tooltip=folium.GeoJsonTooltip(
                           fields=["brand","pob_wp"],
                           aliases=["Cadena que ganó territorio","Población en territorio ganado"],
                           localize=True)
                       ).add_to(grp_comp)
    grp_comp.add_to(m)

    # ============================================================
    # Puntos de cines (siempre visibles, agrupados por cadena)
    # ============================================================
    for brand, color in BRAND_COLORS.items():
        sub = all_c[all_c["brand"] == brand]
        if len(sub) == 0: continue
        grp = folium.FeatureGroup(name=f"📍 {brand} ({len(sub)} cines)", show=True)
        for _, r in sub.iterrows():
            popup = f"<b>{r['name']}</b><br><i>{r.get('distrito','')}</i><br>Cadena: <b>{brand}</b>"
            folium.CircleMarker(
                location=[r.geometry.y, r.geometry.x],
                radius=6, color="#111", weight=1.5,
                fillColor=color, fillOpacity=1.0,
                tooltip=r["name"], popup=folium.Popup(popup, max_width=260),
            ).add_to(grp)
        grp.add_to(m)

    cmap_cp.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # ============================================================
    # Panel lateral: share por cadena + top competencia
    # ============================================================
    share_html = "<table style='font-size:11px;border-collapse:collapse'>"
    share_html += "<tr style='background:#333;color:white'><th style='padding:3px 6px;text-align:left'>Cadena</th><th style='padding:3px 6px'>Cines</th><th style='padding:3px 6px'>% Territorio</th><th style='padding:3px 6px'>% Pob</th></tr>"
    for _, r in share_brand.iterrows():
        color = BRAND_COLORS.get(r["brand"], "#666")
        share_html += (f"<tr><td style='padding:3px 6px'>"
                       f"<span style='display:inline-block;width:10px;height:10px;background:{color};border-radius:2px;margin-right:4px'></span>"
                       f"{r['brand']}</td>"
                       f"<td style='padding:3px 6px;text-align:right'>{int(r['n_cines'])}</td>"
                       f"<td style='padding:3px 6px;text-align:right'>{r['share_area_pct']:.1f}%</td>"
                       f"<td style='padding:3px 6px;text-align:right'>{r['share_pob_pct']:.1f}%</td></tr>")
    share_html += "</table>"

    comp_tbl = comp_cp.nlargest(10, "pob_perdida")
    comp_html = "<table style='font-size:10.5px;border-collapse:collapse;margin-top:8px'>"
    comp_html += "<tr style='background:#333;color:white'><th style='padding:3px 6px;text-align:left'>Cineplanet</th><th style='padding:3px 6px'>% Pob retenida</th><th style='padding:3px 6px'>Pob perdida</th><th style='padding:3px 6px;text-align:left'>Competidor +cercano</th></tr>"
    for _, r in comp_tbl.iterrows():
        color = BRAND_COLORS.get(r["comp_brand"], "#666")
        comp_html += (f"<tr><td style='padding:3px 6px'>{r['name'][:25]} <span style='color:#888'>({r['distrito'][:12]})</span></td>"
                      f"<td style='padding:3px 6px;text-align:right'>{r['pct_pob_retenida']:.0f}%</td>"
                      f"<td style='padding:3px 6px;text-align:right'>{r['pob_perdida']:,.0f}</td>"
                      f"<td style='padding:3px 6px'><span style='color:{color}'>■</span> {r['competidor'][:25]}</td></tr>")
    comp_html += "</table>"

    side_html = f"""
    {{% macro html(this, kwargs) %}}
    <div style="position: fixed; top: 12px; right: 12px; z-index: 9999;
                background: white; padding: 10px 14px; border: 1px solid #ccc;
                border-radius: 6px; max-height: 88vh; overflow-y: auto;
                box-shadow: 0 2px 6px rgba(0,0,0,0.15); font-family: system-ui;
                width: 480px;">
      <div style="font-weight:700; margin-bottom:6px; font-size:13px; color:#8a1538">
        📊 Análisis Competitivo Cine Lima+Callao
      </div>
      <div style="font-size:11.5px; color:#666; margin-bottom:8px">
        Voronoi por tiempo en auto (OSRM sin tráfico) · grid 1km · población WorldPop 2020
      </div>
      <div style="font-weight:600; font-size:11.5px; margin:6px 0 4px 0; color:#333">
        Share territorial y poblacional por cadena
      </div>
      {share_html}
      <div style="font-weight:600; font-size:11.5px; margin:10px 0 4px 0; color:#333">
        Top 10 Cineplanets con más territorio disputado
      </div>
      <div style="font-size:11px; color:#666; margin-bottom:2px">
        "% Pob retenida" = cuánta pob mantiene el CP cuando entran los competidores
      </div>
      {comp_html}
    </div>
    {{% endmacro %}}
    """
    mac = MacroElement()
    mac._template = Template(side_html)
    m.get_root().add_child(mac)

    out = OUT_DIR / "mapa_cineplanet_competencia.html"
    m.save(str(out))
    print(f"-> {out}")
    print(f"   Cines: {len(all_c)} de 7 cadenas")
    print(f"   Cineplanet: 27 · Otras: {len(all_c)-27}")

if __name__ == "__main__":
    main()
