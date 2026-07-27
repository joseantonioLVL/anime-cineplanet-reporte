"""Mapa Folium final con UX mejorado:
  - Panel de bienvenida al abrir con las 3 vistas explicadas
  - Etiquetas con emojis y descripción de qué hace cada capa
  - Tooltips enriquecidos con línea de lectura
  - Insights destacados sobre el mapa (Chorrillos, SJL, San Borja disputados)
  - Botones prominentes para cambiar de vista
  - Panel lateral simplificado
"""
from pathlib import Path
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import Fullscreen, GroupedLayerControl
from branca.colormap import LinearColormap
from branca.element import Template, MacroElement

DATA = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "output"

CENTER = [-12.05, -77.03]
ZOOM = 11

BRAND_COLORS = {
    "Cineplanet": "#e53935",
    "Cinemark":   "#1e88e5",
    "Cinépolis":  "#8e24aa",
    "Cinestar":   "#43a047",
    "MovieTime":  "#f57c00",
    "UVK":        "#00acc1",
    "Cinerama":   "#6d4c41",
}

def build_tooltip_cp(feat):
    p = feat["properties"]
    return (f"<b>{p['name']}</b><br>"
            f"<i>{p['distrito']}</i><br>"
            f"👥 <b>{p['pob_worldpop']:,.0f}</b> habitantes en su zona<br>"
            f"⏱️ ~{p['dur_min_avg']:.0f} min en auto en promedio<br>"
            f"📏 {p['area_km2']:.0f} km²")

def main():
    all_c = gpd.read_file(DATA / "cines_all_chains.geojson")
    catch_cp = gpd.read_file(OUT_DIR / "catchments.geojson")
    catch_all = gpd.read_file(OUT_DIR / "catchments_all_chains.geojson")
    comp_cp = pd.read_csv(OUT_DIR / "cineplanet_competencia.csv")
    share_brand = pd.read_csv(OUT_DIR / "share_por_cadena.csv")
    lost_zones = gpd.read_file(OUT_DIR / "zonas_perdidas_por_brand.geojson") if (OUT_DIR / "zonas_perdidas_por_brand.geojson").exists() else None

    m = folium.Map(location=CENTER, zoom_start=ZOOM, tiles="cartodbpositron", control_scale=True)
    Fullscreen(position="topleft").add_to(m)

    # ============================================================
    # VISTA 1: Solo Cineplanet
    # ============================================================
    pmax = float(catch_cp["pob_worldpop"].max())
    cmap_cp = LinearColormap(
        ["#fff5f0", "#fcbba1", "#fb6a4a", "#cb181d", "#67000d"],
        vmin=0, vmax=pmax, caption="Población en la zona (WorldPop 2020)"
    )
    grp_cp = folium.FeatureGroup(name="🔴 Solo Cineplanet — territorio si no hubiera competencia", show=True)

    def style_cp(feat):
        pop = feat["properties"]["pob_worldpop"]
        return {"fillColor": cmap_cp(pop), "color": "#7f0000", "weight": 1.2, "fillOpacity": 0.55}

    # Enrich tooltip with reading line
    catch_cp_display = catch_cp.copy()
    catch_cp_display["lectura"] = catch_cp_display.apply(
        lambda r: (f"En un mundo sin competencia, {r['name']} sería el cine más cercano en auto "
                   f"para <b>{r['pob_worldpop']:,.0f}</b> personas ({r['area_km2']:.0f} km², "
                   f"tiempo promedio {r['dur_min_avg']:.0f} min)."), axis=1)

    tooltip_cp = folium.GeoJsonTooltip(
        fields=["name","distrito","pob_worldpop","area_km2","dur_min_avg","dur_p90_min","lectura"],
        aliases=["Cine","Distrito","👥 Población","📏 km²","⏱️ Tiempo prom (min)","⏱️ Tiempo p90 (10% más lejano)","📖 Lectura"],
        localize=True, sticky=True, max_width=350,
    )
    folium.GeoJson(catch_cp_display.__geo_interface__, style_function=style_cp, tooltip=tooltip_cp,
                   highlight_function=lambda f: {"weight":3,"color":"#000","fillOpacity":0.75}).add_to(grp_cp)
    grp_cp.add_to(m)

    # ============================================================
    # VISTA 2: Todas las cadenas
    # ============================================================
    grp_all = folium.FeatureGroup(name="🎨 Todas las cadenas — cada zona a su cine más cercano", show=False)

    def style_all(feat):
        brand = feat["properties"]["brand"]
        return {"fillColor": BRAND_COLORS.get(brand, "#666"), "color": "#333", "weight": 1.0, "fillOpacity": 0.6}

    catch_all_display = catch_all.copy()
    catch_all_display["lectura"] = catch_all_display.apply(
        lambda r: (f"Zona donde <b>{r['name']}</b> ({r['brand']}) es el cine más cercano en auto. "
                   f"Alcanza a <b>{r['pob_wp']:,.0f}</b> habitantes considerando la competencia real."), axis=1)

    tooltip_all = folium.GeoJsonTooltip(
        fields=["brand","name","distrito","pob_wp","area_km2","dur_min_avg","dur_p90","lectura"],
        aliases=["🎬 Cadena","Cine","Distrito","👥 Población alcanzada","📏 km²","⏱️ Tiempo prom","⏱️ Tiempo p90","📖 Lectura"],
        localize=True, sticky=True, max_width=350,
    )
    folium.GeoJson(catch_all_display.__geo_interface__, style_function=style_all, tooltip=tooltip_all,
                   highlight_function=lambda f: {"weight":3,"color":"#000","fillOpacity":0.8}).add_to(grp_all)
    grp_all.add_to(m)

    # ============================================================
    # VISTA 3: Competencia — CP gris + zonas perdidas
    # ============================================================
    grp_comp = folium.FeatureGroup(name="⚔️ Vista competencia — qué le quita cada rival a Cineplanet", show=False)

    folium.GeoJson(catch_cp.__geo_interface__,
                   style_function=lambda f: {"fillColor":"#bbbbbb","color":"#666","weight":0.8,"fillOpacity":0.35},
                   tooltip=folium.GeoJsonTooltip(
                       fields=["name","distrito","pob_worldpop"],
                       aliases=["Cineplanet","Distrito","👥 Pob si no hubiera competencia"])
                   ).add_to(grp_comp)

    if lost_zones is not None and len(lost_zones) > 0:
        lost_display = lost_zones.copy()
        lost_display["lectura"] = lost_display.apply(
            lambda r: (f"<b>{r['brand']}</b> le gana esta zona a Cineplanet: "
                       f"<b>{r['pob_wp']:,.0f}</b> personas prefieren (por tiempo en auto) "
                       f"un cine de {r['brand']} antes que el Cineplanet más cercano."), axis=1)

        def style_lost(feat):
            b = feat["properties"]["brand"]
            return {"fillColor": BRAND_COLORS.get(b,"#666"), "color":"#111", "weight":1.5, "fillOpacity":0.75}

        folium.GeoJson(lost_display.__geo_interface__, style_function=style_lost,
                       tooltip=folium.GeoJsonTooltip(
                           fields=["brand","pob_wp","lectura"],
                           aliases=["Cadena ganadora","Pob capturada","📖 Lectura"],
                           localize=True, max_width=350)
                       ).add_to(grp_comp)
    grp_comp.add_to(m)

    # ============================================================
    # PUNTOS DE CINES por cadena (toggleable)
    # ============================================================
    for brand, color in BRAND_COLORS.items():
        sub = all_c[all_c["brand"] == brand]
        if len(sub) == 0: continue
        grp = folium.FeatureGroup(name=f"📍 Cines {brand} ({len(sub)})", show=True)
        for _, r in sub.iterrows():
            popup = f"<b>{r['name']}</b><br><i>{r.get('distrito','')}</i><br>Cadena: <b>{brand}</b>"
            folium.CircleMarker(
                location=[r.geometry.y, r.geometry.x],
                radius=6, color="#111", weight=1.5,
                fillColor=color, fillOpacity=1.0,
                tooltip=r["name"], popup=folium.Popup(popup, max_width=260),
            ).add_to(grp)
        grp.add_to(m)

    # ============================================================
    # INSIGHTS DESTACADOS sobre el mapa (marcadores especiales en top disputados)
    # ============================================================
    top_disputados = comp_cp.nlargest(3, "pob_perdida")
    for _, r in top_disputados.iterrows():
        cine_pt = all_c[(all_c["brand"]=="Cineplanet") & (all_c["id"]==r["cine_id"])].iloc[0]
        lat, lon = cine_pt.geometry.y, cine_pt.geometry.x
        insight = (f"<b>⚠️ Zona muy disputada</b><br>"
                   f"<b>{r['name']}</b> ({r['distrito']})<br>"
                   f"Solo retiene <b>{r['pct_pob_retenida']:.0f}%</b> de su población potencial<br>"
                   f"Pierde <b>{r['pob_perdida']:,.0f}</b> personas a {r['comp_brand']}<br>"
                   f"Competidor: {r['competidor']} (a {r['comp_dist_m']:.0f} m)")
        folium.Marker(
            location=[lat + 0.005, lon],
            icon=folium.Icon(color="orange", icon="warning-sign", prefix="glyphicon"),
            tooltip="⚠️ Cineplanet muy disputado — clic para detalle",
            popup=folium.Popup(insight, max_width=300),
        ).add_to(m)

    cmap_cp.add_to(m)
    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    # ============================================================
    # PANEL DE BIENVENIDA — auto-shown al abrir el mapa
    # ============================================================
    welcome_html = """
    {% macro html(this, kwargs) %}
    <div id="welcome-modal" style="
         position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
         z-index: 10000; background: white; padding: 24px 28px;
         border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
         max-width: 520px; width: 90%; font-family: -apple-system, system-ui, sans-serif;">
      <div style="font-size: 20px; font-weight: 700; color: #8a1538; margin-bottom: 10px">
        🎬 Análisis Competitivo de Cines · Lima + Callao
      </div>
      <div style="font-size: 13.5px; color: #333; line-height: 1.55; margin-bottom: 14px">
        Analizamos <b>56 cines de 7 cadenas</b> (27 Cineplanet + 29 competidores) usando
        <b>tiempo de auto</b> a cada punto de Lima para responder:
        <b>¿dónde manda Cineplanet, dónde pierde y contra quién?</b>
      </div>

      <div style="background: #f9f4e8; border-left: 4px solid #b08d3a;
                  padding: 10px 14px; border-radius: 4px; margin-bottom: 14px; font-size: 12.5px">
        <b>Cómo usar el mapa</b> — arriba a la derecha están las 3 vistas. Elige cuál quieres ver:
      </div>

      <div style="display: grid; grid-template-columns: 1fr; gap: 8px; margin-bottom: 14px">
        <div style="display: flex; align-items: center; padding: 8px 12px; background: #fef4f4; border-radius: 6px; font-size: 12.5px">
          <div style="font-size: 22px; margin-right: 10px">🔴</div>
          <div>
            <b>Solo Cineplanet</b> — Cada zona coloreada por cuánta gente vive ahí,
            asumiendo que Cineplanet no tuviera competencia. Mercado potencial máximo.
          </div>
        </div>
        <div style="display: flex; align-items: center; padding: 8px 12px; background: #f0f4fa; border-radius: 6px; font-size: 12.5px">
          <div style="font-size: 22px; margin-right: 10px">🎨</div>
          <div>
            <b>Todas las cadenas</b> — Cada zona pintada del color de la cadena
            cuyo cine está más cerca en auto. Muestra el "reparto real" del mercado.
          </div>
        </div>
        <div style="display: flex; align-items: center; padding: 8px 12px; background: #f4f0f8; border-radius: 6px; font-size: 12.5px">
          <div style="font-size: 22px; margin-right: 10px">⚔️</div>
          <div>
            <b>Vista competencia</b> — Cineplanet en gris + zonas donde otra cadena
            gana coloreadas por rival. Ver qué territorio pierde CP y contra quién.
          </div>
        </div>
      </div>

      <div style="font-size: 12px; color: #666; margin-bottom: 14px; border-top: 1px solid #eee; padding-top: 10px">
        💡 Los <b>iconos ⚠️ naranjas</b> marcan los 3 Cineplanet más disputados. Haz clic para ver el detalle.<br>
        📍 Puedes prender/apagar los puntos de cada cadena por separado en el control de capas.<br>
        🖱️ Pasa el mouse por cualquier zona para ver su lectura interpretada.
      </div>

      <div style="margin-bottom: 14px; border-top: 1px solid #eee; padding-top: 10px; font-size: 12px; color: #666">
        📘 <b>La metodología completa</b> está siempre visible en el cuadro
        <b>"🔬 Metodología"</b> abajo a la derecha del mapa. Haz clic ahí para expandirla cuando quieras.
      </div>

      <button onclick="document.getElementById('welcome-modal').style.display='none'; document.getElementById('welcome-backdrop').style.display='none'"
              style="width: 100%; padding: 10px; background: #8a1538; color: white; border: none;
                     border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer">
        Empezar a explorar →
      </button>
    </div>
    <div id="welcome-backdrop" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                                        background: rgba(0,0,0,0.5); z-index: 9999"
         onclick="document.getElementById('welcome-modal').style.display='none'; this.style.display='none'"></div>

    <!-- Botón "?" para reabrir modal -->
    <button onclick="document.getElementById('welcome-modal').style.display='block'; document.getElementById('welcome-backdrop').style.display='block'"
            style="position: fixed; bottom: 20px; left: 20px; z-index: 9998;
                   width: 44px; height: 44px; border-radius: 50%; background: #8a1538;
                   color: white; border: none; font-size: 20px; font-weight: bold;
                   box-shadow: 0 2px 8px rgba(0,0,0,0.3); cursor: pointer"
            title="¿Cómo leer este mapa?">?</button>
    {% endmacro %}
    """
    welcome = MacroElement()
    welcome._template = Template(welcome_html)
    m.get_root().add_child(welcome)

    # ============================================================
    # PANEL LATERAL: share por cadena + top competidos
    # ============================================================
    share_rows = ""
    for _, r in share_brand.iterrows():
        color = BRAND_COLORS.get(r["brand"], "#666")
        bar_w = min(100, r["share_pob_pct"])
        share_rows += (f"<tr>"
                       f"<td style='padding:4px 6px'><span style='display:inline-block;width:11px;height:11px;background:{color};border-radius:2px;margin-right:5px;vertical-align:middle'></span><b>{r['brand']}</b></td>"
                       f"<td style='padding:4px 6px;text-align:right;color:#666'>{int(r['n_cines'])} cines</td>"
                       f"<td style='padding:4px 6px;text-align:right;font-weight:600'>{r['share_pob_pct']:.1f}%</td>"
                       f"<td style='padding:4px; width:60px'><div style='background:#eee;border-radius:3px;overflow:hidden;height:8px'><div style='background:{color};width:{bar_w}%;height:100%'></div></div></td>"
                       f"</tr>")

    comp_tbl = comp_cp.nlargest(5, "pob_perdida")
    comp_rows = ""
    for _, r in comp_tbl.iterrows():
        color = BRAND_COLORS.get(r["comp_brand"], "#666")
        comp_rows += (f"<tr><td style='padding:3px 6px'><b>{r['name'][:24]}</b><br><span style='color:#888;font-size:10px'>{r['distrito']}</span></td>"
                      f"<td style='padding:3px 6px;text-align:right'><b>{r['pct_pob_retenida']:.0f}%</b><br><span style='color:#888;font-size:10px'>retenido</span></td>"
                      f"<td style='padding:3px 6px'><span style='color:{color}'>●</span> {r['comp_brand']}</td></tr>")

    # PANEL LATERAL a la IZQUIERDA (no tapa el colormap ni el control de capas de la derecha)
    side_html = f"""
    {{% macro html(this, kwargs) %}}
    <div id="side-panel" style="position: fixed; top: 12px; left: 60px; z-index: 9997;
                background: white; padding: 12px 14px; border-radius: 8px;
                max-height: 88vh; overflow-y: auto; width: 300px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: system-ui, sans-serif;">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-weight:700; font-size:14px; color:#8a1538">📊 Cines Lima+Callao</div>
          <div style="font-size: 11px; color: #999">Voronoi por tiempo en auto · WorldPop 2020</div>
        </div>
        <button onclick="var p=document.getElementById('side-panel-body'); p.style.display = p.style.display==='none' ? 'block' : 'none'"
                style="background:none;border:1px solid #ccc;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px">−</button>
      </div>

      <div id="side-panel-body">
        <div style="font-weight:600; font-size:11px; margin:10px 0 4px 0; color:#333; text-transform:uppercase; letter-spacing:0.5px">
          🥇 Share de mercado (pob. capturada)
        </div>
        <table style="width:100%; font-size:11.5px; border-collapse:collapse">{share_rows}</table>

        <div style="font-weight:600; font-size:11px; margin:14px 0 4px 0; color:#333; text-transform:uppercase; letter-spacing:0.5px">
          ⚔️ Top 5 Cineplanets disputados
        </div>
        <table style="width:100%; font-size:11px; border-collapse:collapse">{comp_rows}</table>
        <div style="font-size: 10px; color: #999; margin-top: 4px; font-style: italic">
          "Retenido" = % de la pob potencial que efectivamente captura cuando entran competidores
        </div>
      </div>
    </div>

    <!-- INSIGHT strip abajo-centro (no tapa el layer control ni el colormap) -->
    <div id="view-banner" style="position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
                                    z-index: 9996; background: rgba(255,255,255,0.97);
                                    padding: 8px 18px; border-radius: 20px; max-width: 640px;
                                    box-shadow: 0 2px 8px rgba(0,0,0,0.15); font-family: system-ui;
                                    text-align: center; border: 1px solid #eee;">
      <span style="font-size: 12.5px; color: #333">
        🎬 <b>27 Cineplanet vs. 29 competidores</b> · Cineplanet capta <b style="color:#e53935">73%</b> de la población, Cinestar <b style="color:#43a047">12%</b>
      </span>
      <span style="font-size: 11px; color: #888; margin-left: 8px">
        · 💡 Cambia de vista arriba a la derecha ↗
      </span>
    </div>

    <!-- CUADRO PERSISTENTE DE METODOLOGÍA (abajo-derecha, siempre visible, expandible) -->
    <div id="metodologia-box" style="position: fixed; bottom: 20px; right: 20px; z-index: 9997;
                                       background: white; border-radius: 8px; width: 380px; max-width: 42vw;
                                       box-shadow: 0 4px 12px rgba(0,0,0,0.18); font-family: system-ui;
                                       border: 2px solid #8a1538;">
      <div onclick="var b=document.getElementById('meto-body'); var i=document.getElementById('meto-icon'); if(b.style.display==='none'){{b.style.display='block';i.textContent='▼';}}else{{b.style.display='none';i.textContent='▶';}}"
           style="cursor: pointer; padding: 10px 14px; background: #8a1538; color: white;
                  border-radius: 6px 6px 0 0; font-size: 13px; font-weight: 700;
                  display: flex; justify-content: space-between; align-items: center;
                  user-select: none">
        <span>🔬 Metodología del análisis (clic para expandir)</span>
        <span id="meto-icon" style="font-size: 11px">▶</span>
      </div>
      <div id="meto-body" style="display: none; padding: 14px 16px; font-size: 12.5px;
                                   color: #333; line-height: 1.6; max-height: 65vh; overflow-y: auto">

        <div style="background: #f5f5f5; padding: 10px 12px; border-radius: 6px; margin-bottom: 12px;
                    border-left: 3px solid #8a1538">
          <b>La pregunta central:</b> si dividimos Lima y Callao en pedacitos chicos,
          ¿cuál cine queda más cerca en auto de cada pedacito? Y luego, ¿cuánta gente vive en cada pedacito?
        </div>

        <p style="margin: 10px 0 4px 0; color: #8a1538"><b>Paso 1 · Ubicar los 56 cines</b></p>
        <p style="margin: 0 0 10px 12px">Buscamos las coordenadas exactas en 3 fuentes públicas
        (<i>deperu.com, lacartelera.pe, mirandolacartelera.com</i>). Los <b>27 Cineplanet</b> están en
        las 3 fuentes. Para los 29 competidores usamos OpenStreetMap; los 6 que OSM no tenía los ubicamos
        manualmente desde su dirección oficial.</p>

        <p style="margin: 10px 0 4px 0; color: #8a1538"><b>Paso 2 · Dividir Lima+Callao en una grilla</b></p>
        <p style="margin: 0 0 10px 12px">Trazamos una cuadrícula: cada cuadrado mide
        <b>1 km × 1 km</b>. Solo dejamos los que caen <b>dentro</b> del polígono de los 49 distritos INEI.
        Quedan <b>3,042 cuadraditos</b> que cubren toda el área urbana.</p>

        <p style="margin: 10px 0 4px 0; color: #8a1538"><b>Paso 3 · Tiempo en auto de cada cuadrado a cada cine</b></p>
        <p style="margin: 0 0 10px 12px">Usamos <b>OSRM</b> (Open Source Routing Machine),
        un motor de ruteo gratuito que corre sobre el grafo de calles de OpenStreetMap. Para cada
        cuadrado preguntamos: <i>"¿cuánto demora un auto en llegar al cine X?"</i> — son
        <b>170,352 rutas calculadas</b>. Como es OSM libre, usa <b>velocidades legales de las calles,
        no tráfico real</b> (o sea, es tiempo de "auto fluido a las 3 am").</p>

        <p style="margin: 10px 0 4px 0; color: #8a1538"><b>Paso 4 · Asignar cada cuadrado al cine con menor tiempo</b></p>
        <p style="margin: 0 0 10px 12px">Para cada cuadrado comparamos los 56 tiempos y nos quedamos con
        el cine que menos demora. Ese cuadrado "pertenece" a ese cine. Juntamos todos los cuadrados del
        mismo cine → <b>catchment</b>. Esto es Voronoi por tiempo (no por distancia recta): respeta las
        calles reales, así que en zonas con avenidas rápidas los catchments son más largos.</p>

        <p style="margin: 10px 0 4px 0; color: #8a1538"><b>Paso 5 · Contar la población de cada catchment</b></p>
        <p style="margin: 0 0 10px 12px">Cruzamos con <b>WorldPop 2020</b>: un raster satelital que
        estima cuánta gente vive en cada pixel de <b>100 × 100 m</b>. Sumamos todos los pixeles dentro
        de cada catchment. Control cruzado con el Censo INEI 2017 distribuido por distrito → los
        números coinciden en orden de magnitud.</p>

        <p style="margin: 10px 0 4px 0; color: #8a1538"><b>Paso 6 · Calcular la "pérdida" competitiva</b></p>
        <p style="margin: 0 0 10px 12px">Para cada Cineplanet calculamos <b>dos catchments</b>:
        <br>· <b>Aislado</b>: como si Cineplanet fuera el único operador (los 27 CP compitiendo entre sí).
        <br>· <b>Competitivo</b>: con los 56 cines corriendo; solo se queda con la gente para quien un Cineplanet sigue siendo el más cercano.
        <br>La diferencia = <b>pob perdida a la competencia</b>. El <b>% retenido</b> = catchment competitivo ÷ catchment aislado.</p>

        <div style="background: #fff8e1; border-left: 3px solid #f9a825; padding: 10px 12px;
                    margin-top: 12px; font-size: 12px; color: #5a4400; border-radius: 4px">
          <b>Qué NO estamos modelando</b>
          <br>· <b>Tráfico real</b>: los tiempos son a velocidad libre. En hora punta pueden ser 1.5–2× peores.
          <br>· <b>Otros modos</b>: solo auto. No incluimos Metro L1, Metropolitano, corredores ni caminata.
          <br>· <b>Preferencia de marca / precio / calidad</b>: asumimos que la gente elige por tiempo. Un fan puede viajar 15 min más por "su" cine.
          <br>· <b>Resolución 1 km</b>: fronteras entre catchments tienen ±500 m de imprecisión.
        </div>
      </div>
    </div>

    <!-- Etiquetas de LEYENDA explicando qué significa cada color de cadena -->
    <div id="brand-legend" style="position: fixed; bottom: 20px; left: 78px; z-index: 9995;
                                    background: white; padding: 8px 12px; border-radius: 6px;
                                    box-shadow: 0 2px 6px rgba(0,0,0,0.12); font-family: system-ui;
                                    font-size: 11px;">
      <div style="font-weight: 700; font-size: 11px; margin-bottom: 4px; color: #333">
        Colores por cadena
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2px 12px">
        <div><span style="display:inline-block;width:11px;height:11px;background:#e53935;border-radius:2px;vertical-align:middle;margin-right:4px"></span>Cineplanet</div>
        <div><span style="display:inline-block;width:11px;height:11px;background:#43a047;border-radius:2px;vertical-align:middle;margin-right:4px"></span>Cinestar</div>
        <div><span style="display:inline-block;width:11px;height:11px;background:#1e88e5;border-radius:2px;vertical-align:middle;margin-right:4px"></span>Cinemark</div>
        <div><span style="display:inline-block;width:11px;height:11px;background:#8e24aa;border-radius:2px;vertical-align:middle;margin-right:4px"></span>Cinépolis</div>
        <div><span style="display:inline-block;width:11px;height:11px;background:#f57c00;border-radius:2px;vertical-align:middle;margin-right:4px"></span>MovieTime</div>
        <div><span style="display:inline-block;width:11px;height:11px;background:#00acc1;border-radius:2px;vertical-align:middle;margin-right:4px"></span>UVK</div>
        <div><span style="display:inline-block;width:11px;height:11px;background:#6d4c41;border-radius:2px;vertical-align:middle;margin-right:4px"></span>Cinerama</div>
      </div>
    </div>
    {{% endmacro %}}
    """
    side = MacroElement()
    side._template = Template(side_html)
    m.get_root().add_child(side)

    out = OUT_DIR / "mapa_cineplanet_competencia.html"
    m.save(str(out))
    print(f"-> {out}")

if __name__ == "__main__":
    main()
