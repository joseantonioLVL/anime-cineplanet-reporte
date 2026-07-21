# Comunidad Anime × Cineplanet — Reporte

Investigación cuantitativa sobre fans de anime en Lima. 610 fans encuestados en 2 brazos:
**No Socios** (n=155) + **Socios activos de Cineplanet** (n=455).

## 🌐 Ver online

Portal principal (recomendado): **https://joseantoniolvl.github.io/anime-cineplanet-reporte/**

Reportes individuales:
- [Reporte No Socios](https://joseantoniolvl.github.io/anime-cineplanet-reporte/reporte_no_socios.html) — MaxDiff HB anclado + deep-dive top-3 + calculadora Juster
- [Reporte Socios](https://joseantoniolvl.github.io/anime-cineplanet-reporte/reporte_socios.html) — MaxDiff HB (sin ancla) + share of preference
- [Reporte Consolidado](https://joseantoniolvl.github.io/anime-cineplanet-reporte/reporte_consolidado.html) — Vista comparativa

## 📄 Documentación

- **[PROCESO.txt](PROCESO.txt)** — cómo se construyó el estudio (universo, filtros, instrumento, modelo)
- **[VALIDACION_HALLAZGOS.md](VALIDACION_HALLAZGOS.md)** — framework en 3 niveles: resultados → hallazgos → preguntas
- **[VALIDACION_HALLAZGOS.csv](VALIDACION_HALLAZGOS.csv)** — tabla de trazabilidad de los 19 hallazgos
- **[PREGUNTAS_INVESTIGACION_DIARIO.md](PREGUNTAS_INVESTIGACION_DIARIO.md)** — 18 preguntas cuali derivadas
- **[36_auditar_hallazgos.R](36_auditar_hallazgos.R)** — script reproducible de auditoría (19/19 OK)

## Metodología en 1 párrafo

MaxDiff Hierarchical Bayes con ChoiceModelR (R=20000 iter, use=10000, keep=10) sobre 16 conceptos.
No Socios incluye bloque de ancla (16 pseudo-tareas concepto vs NONE) que ancla la escala al umbral personal;
Socios NO tiene ancla y reporta share of preference (relativo). Segmentación K-means K=4 sobre escalas
psicométricas Reysen Fanship + FANDOM Community (Likert 1-7, sin escalar). Validación: rankings HB vs
conteo bruto r=0.994 (NS) / 0.998 (SC); reproducibilidad con otra seed r=0.9997.

LVL 2026 · joseantonio@lavictoria.pe
