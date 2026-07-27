"""Mapa interactivo Folium: cines + catchments + popups con métricas."""
import json
from pathlib import Path
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap

DATA = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "output"

CENTER = [-12.05, -77.03]
ZOOM = 11

def main():
    cines = gpd.read_file(DATA / "cineplanets.geojson")
    catch = gpd.read_file(OUT_DIR / "catchments.geojson")

    # colormap por población WorldPop
    pmax = float(catch["pob_worldpop"].max())
    pmin = float(catch["pob_worldpop"].min())
    cmap = LinearColormap(
        ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
        vmin=pmin, vmax=pmax, caption="Población catchment (WorldPop 2020)"
    )

    m = folium.Map(location=CENTER, zoom_start=ZOOM, tiles="cartodbpositron", control_scale=True)
    Fullscreen().add_to(m)

    # capa catchments
    def style_fn(feat):
        pop = feat["properties"]["pob_worldpop"]
        return {"fillColor": cmap(pop), "color": "#222", "weight": 1.2, "fillOpacity": 0.55}

    def highlight_fn(feat):
        return {"weight": 3, "color": "#000", "fillOpacity": 0.75}

    tooltip = folium.GeoJsonTooltip(
        fields=["cine_id", "name", "distrito", "pob_worldpop", "pob_inei",
                "area_km2", "dur_min_avg", "dur_p50_min", "dur_p90_min", "n_cells"],
        aliases=["Cine ID", "Nombre", "Distrito",
                 "Pob (WorldPop 2020)", "Pob (INEI 2017)",
                 "Área (km²)", "Tiempo prom (min)", "Tiempo mediana (min)",
                 "Tiempo p90 (min)", "Celdas 1km"],
        localize=True, sticky=True, labels=True,
    )

    def popup_html(row):
        return f"""
        <div style='font-family: system-ui; font-size: 13px; min-width: 240px'>
          <b>{row['name']}</b><br>
          <span style='color:#666'>{row['distrito']} · {row['cine_id']}</span>
          <hr style='margin: 4px 0'>
          <table style='font-size:12px'>
            <tr><td><b>Pob WorldPop 2020</b></td><td style='text-align:right'>{row['pob_worldpop']:,.0f}</td></tr>
            <tr><td><b>Pob INEI 2017</b></td><td style='text-align:right'>{row['pob_inei']:,.0f}</td></tr>
            <tr><td>Área</td><td style='text-align:right'>{row['area_km2']:.1f} km²</td></tr>
            <tr><td>Tiempo prom auto</td><td style='text-align:right'>{row['dur_min_avg']:.1f} min</td></tr>
            <tr><td>Tiempo mediana</td><td style='text-align:right'>{row['dur_p50_min']:.1f} min</td></tr>
            <tr><td>Tiempo p90</td><td style='text-align:right'>{row['dur_p90_min']:.1f} min</td></tr>
            <tr><td>Celdas 1km²</td><td style='text-align:right'>{row['n_cells']}</td></tr>
          </table>
        </div>
        """

    folium.GeoJson(
        catch.__geo_interface__,
        name="Catchments (tiempo en auto)",
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=tooltip,
        popup=folium.GeoJsonPopup(
            fields=["cine_id", "name", "distrito", "pob_worldpop", "pob_inei",
                    "area_km2", "dur_min_avg", "dur_p50_min", "dur_p90_min"],
            aliases=["Cine ID", "Nombre", "Distrito", "Pob WorldPop", "Pob INEI",
                     "Área km²", "Tiempo prom (min)", "Mediana (min)", "P90 (min)"],
            localize=True,
        ),
    ).add_to(m)

    # marcadores cines
    grp = folium.FeatureGroup(name="Cineplanets", show=True)
    for _, r in cines.iterrows():
        lon, lat = r.geometry.x, r.geometry.y
        # match con métricas
        row = catch[catch["cine_id"] == r["id"]].iloc[0] if (catch["cine_id"] == r["id"]).any() else None
        html = f"<b>{r['name']}</b><br><i>{r.get('distrito','')}</i>"
        if row is not None:
            html += f"<br>Pob catchment: <b>{row['pob_worldpop']:,.0f}</b>"
            html += f"<br>Área: {row['area_km2']:.1f} km²"
            html += f"<br>Tiempo prom: {row['dur_min_avg']:.1f} min"
        folium.CircleMarker(
            location=[lat, lon], radius=6, color="#b30000", fill=True,
            fillColor="#e34a33", fillOpacity=0.95, weight=2,
            tooltip=r["name"], popup=folium.Popup(html, max_width=280),
        ).add_to(grp)
    grp.add_to(m)

    cmap.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # tabla ranking (arriba a la derecha)
    tbl = catch.sort_values("pob_worldpop", ascending=False)
    tbl_html = "<table style='font-size:11px;border-collapse:collapse'>"
    tbl_html += "<tr style='background:#eee'><th style='padding:2px 4px'>Rank</th><th style='padding:2px 4px;text-align:left'>Cine</th><th style='padding:2px 4px'>Pob (WP)</th><th style='padding:2px 4px'>km²</th></tr>"
    for i, r in enumerate(tbl.itertuples(), 1):
        tbl_html += (f"<tr><td style='padding:2px 4px;text-align:center'>{i}</td>"
                     f"<td style='padding:2px 4px'>{r.name} <span style='color:#888'>({r.distrito})</span></td>"
                     f"<td style='padding:2px 4px;text-align:right'>{r.pob_worldpop:,.0f}</td>"
                     f"<td style='padding:2px 4px;text-align:right'>{r.area_km2:.0f}</td></tr>")
    tbl_html += "</table>"

    from branca.element import Template, MacroElement
    ranking_tpl = f"""
    {{% macro html(this, kwargs) %}}
    <div style="position: fixed; top: 12px; right: 12px; z-index: 9999;
                background: white; padding: 8px 10px; border: 1px solid #ccc;
                border-radius: 6px; max-height: 60vh; overflow-y: auto;
                box-shadow: 0 2px 6px rgba(0,0,0,0.15); font-family: system-ui;">
        <div style="font-weight:600; margin-bottom:4px; font-size:12px">Ranking catchment (pop WorldPop)</div>
        {tbl_html}
        <div style="font-size:10px;color:#888;margin-top:4px">Voronoi por tiempo en auto (OSRM) · grid 1km · {len(cines)} cines Lima+Callao</div>
    </div>
    {{% endmacro %}}
    """
    mac = MacroElement()
    mac._template = Template(ranking_tpl)
    m.get_root().add_child(mac)

    out = OUT_DIR / "mapa_cineplanet_catchments.html"
    m.save(str(out))
    print(f"-> {out}")
    print(f"Cines: {len(cines)}   Catchments: {len(catch)}")
    print(f"Pob total WorldPop: {catch['pob_worldpop'].sum():,.0f}")
    print(f"Pob total INEI    : {catch['pob_inei'].sum():,.0f}")

if __name__ == "__main__":
    main()
