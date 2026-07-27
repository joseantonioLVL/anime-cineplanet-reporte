# Catchments Cineplanet Lima + Callao — Análisis competitivo

Voronoi por tiempo en auto sobre 27 Cineplanets + 29 cines de otras 6 cadenas competidoras, con población estimada por WorldPop 2020 e INEI 2017 y métricas de competencia por cine.

**Mapa interactivo principal**: [`output/mapa_cineplanet_competencia.html`](output/mapa_cineplanet_competencia.html)  (3 vistas con toggle)
**Mapa Cineplanet-only original**: [`output/mapa_cineplanet_catchments.html`](output/mapa_cineplanet_catchments.html)

---

## Universo del análisis (Lima + Callao)

- **56 cines totales** de 7 cadenas
- **Cineplanet: 27** cines (verificados en deperu.com + lacartelera.pe + mirandolacartelera.com)
- **Cinestar: 11** · **Cinemark: 7** · **MovieTime: 4** · **Cinépolis: 3** · **UVK: 3** · **Cinerama: 1**

---

## Share territorial y poblacional (Voronoi por tiempo, ganador se lleva todo)

| Cadena | Cines | % Territorio | % Población | Pob por cine |
|---|---:|---:|---:|---:|
| **Cineplanet** | 27 | **87.7%** | **73.2%** | 311,480 |
| Cinestar | 10 | 7.7% | 12.1% | 138,836 |
| MovieTime | 4 | 1.8% | 4.4% | 127,405 |
| UVK | 3 | 1.2% | 4.4% | 167,867 |
| Cinemark | 5 | 1.0% | 3.6% | 82,942 |
| Cinépolis | 2 | 0.4% | 2.1% | 117,843 |
| Cinerama | 1 | 0.2% | 0.3% | 34,359 |

**Lectura**: Cineplanet domina en cobertura (73% de la población) pero **pierde 14 puntos entre territorio y población** — sus catchments incluyen desproporcionadamente zonas periurbanas de baja densidad (Ventanilla, Lurín, Comas 2). Los competidores capturan zonas más densas.

**Cinestar es el competidor principal** — solo Cinestar captura 12% de la población con 10 cines bien posicionados en Chorrillos, SJL, La Victoria, Breña y Lince.

---

## Cómo leer el mapa (3 vistas con toggle)

**Vista 1 — Solo Cineplanet** (default): Los 27 catchments Voronoi de Cineplanet como si no existiera competencia. Población coloreada en tonos rojos (más oscuro = más gente). Sirve para ver el mercado potencial máximo por sala.

**Vista 2 — Todas las cadenas**: Los 52 catchments de las 7 cadenas coloreados por cadena. Los puntos de cada cine son visibles como círculos del color de su cadena. Sirve para ver dónde manda cada operador.

**Vista 3 — Territorio ganado por competencia**: Los catchments Cineplanet en gris + las zonas donde otra cadena tiene el cine más cercano en tiempo, resaltadas con el color del competidor. Sirve para ver exactamente qué territorio pierde Cineplanet a cada rival.

Los círculos (📍) de cada cadena son toggleables independientemente en el control de capas.

**Panel lateral derecho** = tabla de share por cadena + top 10 Cineplanets con más territorio disputado.

---

## Top 5 Cineplanets más disputados (más población perdida a competencia)

| # | Cine | Distrito | Pob si no hubiera competencia | Pob competitiva | % retenido | Competidor + cercano |
|---|---|---|---:|---:|---:|---|
| 1 | Cineplanet Chorrillos | Chorrillos | 481K | 114K | 24% | Cinestar Chorrillos SP (1.2 km) |
| 2 | Cineplanet SJL | SJL | 664K | 315K | 47% | Cinestar SJL (1.3 km) |
| 3 | Cineplanet Mall del Sur | SJM | 380K | 41K | 11% | Cinestar Sur (0.6 km) |
| 4 | Cineplanet Centro Cívico | Lima | 299K | 26K | 9% | Cinestar Excelsior (53 m) |
| 5 | Cineplanet San Borja | San Borja | 304K | 69K | 23% | Cinestar Aviación (0.6 km) |

**Patrón claro**: **Cinestar es el competidor #1 de Cineplanet** en todos los cines más disputados. La competencia se libra sobre distancias muy cortas (50 m a 1.3 km).

---

## Cómo se construyó (metodología)

1. **Puntos de cines** (56): extraídos de OpenStreetMap vía Nominatim (Cinemark, Cinépolis, algunos Cinestar y MovieTime); geocodificación manual desde direcciones oficiales para el resto (Cinestar Comas/Chorrillos SP/Arenales/Chosica, UVK Panorama, Cinerama Pacífico).
2. **Grid**: Lima + Callao dividido en celdas de 1 km × 1 km (3,042 celdas dentro del polígono de los 49 distritos).
3. **Tiempo en auto**: matriz OSRM público (grafo OSM libre, sin tráfico) → 170,352 pares celda × cine (56 cines × 3042 celdas).
4. **Asignación competitiva**: cada celda se asigna al cine con menor tiempo de manejo, **sin importar la cadena**. Los polígonos se disuelven por cine.
5. **Voronoi Cineplanet-only** (para comparación): mismo procedimiento pero solo con los 27 CP.
6. **Población por catchment**:
   - **WorldPop 2020 constrained 100m** (fuente principal): raster satelital, capta solo áreas construidas.
   - **INEI Censo 2017** (validación): distribuida proporcional al área.
7. **Métricas competitivas por Cineplanet**:
   - `pob_cp_only` = población si CP no tuviera competencia (Voronoi CP-only)
   - `pob_competitivo` = población efectiva cuando entran los competidores
   - `pob_perdida` = `pob_cp_only − pob_competitivo`
   - `pct_pob_retenida` = `pob_competitivo / pob_cp_only`
   - `competidor` = cine no-CP más cercano en línea recta

---

## Limitaciones importantes

1. **Sin tráfico**: OSRM público usa velocidades libres. Tiempos reales en hora punta pueden ser 1.5-2× estos valores, especialmente en Panamericana Norte y Javier Prado.
2. **Solo auto**: no considera transporte público (Metro L1, Metropolitano, corredores) ni caminata. En Lima el 70% de fans probablemente no usa auto.
3. **Voronoi puro por proximidad**: no modela preferencia (marca, precio, calidad de sala, tipo de pantalla). Un fan puede preferir viajar más a su cine de siempre aunque haya otro más cerca.
4. **Grid 1 km**: la resolución mínima del análisis es 1 km. Fronteras de catchment tienen incertidumbre de ± 500 m.
5. **WorldPop constrained**: modela solo pixeles con construcción visible en imagen satelital 2020. Puede subestimar zonas nuevas.
6. **Set de cines**: 27 CP validados en 3 fuentes. Otras cadenas: geocodificadas por cruce OSM + direcciones oficiales; algunos cines de Cinestar pueden estar con precisión de ±100 m.

---

## Archivos

**Data**
- `data/cineplanets.geojson` — 27 puntos Cineplanet con id, nombre, distrito.
- `data/cines_all_chains.geojson` — 56 puntos de las 7 cadenas.
- `data/cines_other_chains.geojson` — 29 puntos solo de las cadenas competidoras.
- `data/distritos_lima_callao.geojson` — 49 polígonos INEI.
- `data/grid_cells.geojson` — 3,042 celdas 1 km.
- `data/worldpop_peru_2020.tif` — raster 100m constrained (23 MB).
- `data/poblacion_distrito_inei2017.csv` — ubigeo → habitantes.
- `data/osrm_matrix_all.parquet` — 170,352 pares (cell, cine_id_all, duration_s, distance_m).
- `data/osrm_matrix.parquet` — 82,134 pares solo Cineplanet (subset).

**Output**
- `output/mapa_cineplanet_competencia.html` — **mapa principal**, toggle 3 vistas (visualización principal).
- `output/mapa_cineplanet_catchments.html` — mapa original solo Cineplanet.
- `output/catchments.geojson` — 27 polígonos catchment CP-only.
- `output/catchments_all_chains.geojson` — 52 polígonos catchment competitivos.
- `output/catchments_summary.csv` — tabla CP-only.
- `output/share_por_cadena.csv` — share territorial y poblacional por cadena.
- `output/cineplanet_competencia.csv` — métricas competitivas por cada Cineplanet.
- `output/zonas_perdidas_por_brand.geojson` — territorio ganado por cada competidor.

**Scripts** (orden de ejecución)
- `scripts/01*_get_cineplanets.py` — coords de los 27 CP.
- `scripts/02_get_distritos.py` — shp distrital + población INEI.
- `scripts/03_compute_osrm_matrix.py` — grid + matriz CP-only.
- `scripts/04_build_catchments.py` — catchments CP-only + población.
- `scripts/05_folium_map.py` — mapa CP-only.
- `scripts/06b_complete_chains.py` — 29 cines de otras cadenas.
- `scripts/07_osrm_all_chains.py` — matriz OSRM 56 cines × 3042 celdas.
- `scripts/08_competition_analysis.py` — catchments competitivos + métricas.
- `scripts/09_folium_map_toggle.py` — mapa con toggle 3 vistas.
