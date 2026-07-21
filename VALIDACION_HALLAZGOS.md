# Framework de validación: resultados → hallazgos → preguntas

**Fecha**: 2026-07-21
**Alcance**: 19 hallazgos cuantitativos derivados de los 4 reportes
**Estado global**: 19/19 hallazgos verificados OK contra los CSVs fuente

---

## El problema

Un estudio cuantitativo produce 3 capas de output que se pueden mezclar:

- **Resultados**: los números crudos que salen de las estimaciones (61.3%, η²=0.132, r=0.994).
- **Hallazgos**: la lectura interpretativa que hacemos de esos números ("Viajes VIP es el top-1 en No Socios").
- **Preguntas de investigación**: los "por qué" que quedan abiertos y motivan investigación adicional (cuali, deep-dive, etc.).

Sin un framework de validación, es fácil que un hallazgo "circule" en el equipo sin que nadie recuerde exactamente qué número lo sostiene, y las preguntas de investigación se conviertan en intuiciones no aterrizadas en la data.

---

## Framework en cascada — 3 niveles

```
Nivel 3: PREGUNTAS DE INVESTIGACIÓN
  ↑ deben derivar verificablemente de →
Nivel 2: HALLAZGOS (interpretaciones)
  ↑ deben derivar verificablemente de →
Nivel 1: RESULTADOS (los números)
```

Cada nivel se valida contra el anterior. Si un hallazgo tiene pregunta pero no resultado, la pregunta es especulación. Si un resultado no está bien estimado, todo lo que se apoya en él es inseguro.

---

## Nivel 1 — Validez de resultados

### Criterios

| Chequeo | Cómo se verifica | Estado en este estudio |
|---|---|---|
| Convergencia MCMC | Acceptance rate ~0.30; RLH mediana > baseline random | ✅ 0.30 / 0.60 vs 0.31 random (NS), 0.625 vs 0.25 (SC) |
| Reproducibilidad | Correr con seed distinto y comparar | ✅ Pearson 0.9997 (NS), verificado en `14_validar_reproducibilidad_hb_v2.R` |
| Cross-check contra métrica cruda | HB vs conteo bruto best-worst | ✅ r=0.994 (NS), r=0.998 (SC) |
| Sensibilidad a supuestos arbitrarios | 4 escenarios de tope S/130 | ✅ Ranking idéntico, ninguna variable cambia categoría |
| Auditoría de números en outputs | Recomputo manual vs CSVs | ✅ 14/14 números clave verificados (`26_auditar_numeros_html.R`) |
| Umbrales estadísticos convencionales | η² Cohen, Cramer V Cohen | ✅ 0.01/0.06/0.14 y 0.1/0.3/0.5 |

### Riesgos identificados que quedan

- **Bases chicas**: Fan Aislado n=8, Charlas n=3, Playlist n=7 — marcados explícitamente en cada aparición.
- **Métricas distintas por brazo**: %umbral (No Socios, con ancla) vs share (Socios, sin ancla). Comparables ordinalmente, NO en magnitud.
- **Sustitución cruzada Juster**: el %incremental no distingue "visita 100% nueva" de "sustitución de otro cine". Documentado en el reporte No Socios.
- **Muestras no aleatorias**: los dos brazos son de conveniencia (reclutados por canales digitales / desde base CP). Los IC y tests deben interpretarse como referenciales de la muestra, no del universo Lima.

---

## Nivel 2 — Validez de hallazgos

### Criterios

Para que una afirmación sea "hallazgo válido" (no "opinión con datos"):

1. **Trazabilidad exacta**: cada número mencionado tiene fuente en un CSV/tabla del reporte
2. **Consistencia**: el mismo número no aparece con valores distintos en distintos archivos
3. **Base suficiente**: n adecuado para la afirmación; base chica flaggeada
4. **Sin sobre-generalización**: la afirmación no extiende más allá del universo/muestra
5. **Sin editorial**: solo lo que el dato sostiene, sin agregar interpretación causal no probada
6. **Robusto a supuestos alternos**: si el hallazgo cambia con supuestos plausibles distintos, marcarlo como frágil

### Cómo aplicamos la validación (auditoría automatizada)

El script `36_auditar_hallazgos.R` en `04_analisis/`:

- Carga los CSVs de `bases_finales/` (fuente única de verdad)
- Para cada hallazgo, RECOMPUTA el número que lo sostiene
- Compara contra el número afirmado en el hallazgo
- Marca `OK` / `REVISAR` / `FAIL`
- Genera `VALIDACION_HALLAZGOS.csv` con la tabla de trazabilidad

**Resultado actual**: 19/19 hallazgos OK.

### Tabla resumen de trazabilidad

| ID | Hallazgo | Prioridad | Chequeo | Estado |
|---|---|---|---|---|
| H1_NS | Cine anime no discrimina en No Socios | alta | η² < 0.03 & p > 0.05 | ✅ |
| H1_SC | Cine anime no discrimina en Socios | alta | η² < 0.03 & p > 0.05 | ✅ |
| H2 | Top-1 conceptual difiere: Viajes VIP (NS) vs Clásicos (SC) | alta | C08=61% NS, C03=22.2% SC | ✅ |
| H3 | Fan Aislado 3× más grande en SC (16.5% vs 5.2%) | alta | Conteos + IC Wilson NS | ✅ |
| H4 | Fan Intermedio SC solitario (R=6.61, F=3.79) | media | Medias por perfil | ✅ |
| H5 | Silhouette 0.53 (NS) vs 0.46 (SC) | baja | K-means recomputado | ✅ |
| H6 | Festival CP×Crunchy #2 en ambos brazos | alta | Rankings | ✅ |
| H7 | Viajes VIP 54% incremental | alta | Deep-dive slots 1-3 | ✅ |
| H8 | Membresía Socio 10.9% share en SC (vs 41% umbral NS) | media | Share of preference vs %umbral | ✅ |
| H9 | Conciertos 89% credibilidad, solo #5 demanda | baja | believ_top2 + rank | ✅ |
| H10 | Playlist y Charlas bottom en ambos brazos | media | Rankings bottom-3 | ✅ |
| H11 | Sustitución cruzada no capturada por Juster | alta | Limitación instrumento | ✅ |
| H12 | group_size promedio 3-5 | media | Media por concepto | ✅ |
| H13 | Festival: 56% amigos anime; Charlas: 100% partner (n=3) | media | grepl multi-select | ✅ |
| H14 | Callao valora Museo más | baja | Media util por zona | ✅ |
| H15 | Mujeres valoran más Conciertos (η²=0.085) | media | ANOVA por sexo | ✅ |
| H16 | Usuarios Crunchyroll: +24pp en Festival | baja | Multi-select platforms | ✅ |
| H17 | 26% de No Socios usan fansubs | media | 41/155 | ✅ |
| H18 | Frecuencia anime: Cramer V=0.22 en SC | baja | Chi² | ✅ |

### Cómo interpretar el "OK"

`OK` significa: el número afirmado coincide (con tolerancia) con el recomputo desde el CSV fuente. **NO significa**:

- Que el hallazgo sea "verdad definitiva" (los riesgos siguen aplicando).
- Que la interpretación causal sea correcta (correlación ≠ causalidad).
- Que se generalice al universo Lima (muestras no aleatorias).

`REVISAR` significa: el número difiere. Puede ser por redondeo distinto, cambio de metodología, o error real. Requiere revisión manual.

`FAIL` significa: el chequeo no pudo ejecutarse (error de código, columna faltante). Requiere debug.

---

## Nivel 3 — Validez de preguntas de investigación

### Criterios

Para que una pregunta de investigación sea "válida" (no "curiosidad al aire"):

1. **Deriva verificable de un hallazgo con estado OK** — no de intuición externa.
2. **Es abordable con el instrumento cualitativo actual** — el diario WhatsApp de 5 días con 32 participantes puede aportar evidencia.
3. **Genera decisión** — la respuesta afecta una acción concreta (targeting, priorización de concepto, etc.).
4. **Está bien scoped** — específica, no una "gran pregunta abstracta" que no puede responderse.

### Ejemplo aplicado

```
Hallazgo (Nivel 2): H3 — Fan Aislado es 3× más grande en Socios (16.5% vs 5.2%)
  Nivel 1 (resultado): 8/155 vs 75/455; IC 95% NS = [2.7%, 10.0%]
  Riesgos: base chica NS, muestras no aleatorias

Pregunta de investigación derivada (Nivel 3):
  "¿Qué caracteriza al socio de Cineplanet fan de anime que no se identifica
   como fan intenso?"

Validez de la pregunta:
  ✅ Deriva de H3 (que está OK)
  ✅ Abordable con el diario: los participantes tienen perfil identificable ex-ante
     (Reysen bajo + FANDOM bajo + freq/horas altas)
  ✅ Genera decisión: afecta targeting de comunicación de Membresía Anime,
     mensaje de "socio anime" vs "socio general", diseño de contenido
  ✅ Scoped: pregunta sobre un perfil específico, no "todo el anime"
```

Documento completo con las 18 preguntas: `PREGUNTAS_INVESTIGACION_DIARIO.md`.

---

## Cómo re-correr la validación

Cada vez que se agregue un hallazgo nuevo o cambie un número en los reportes:

```bash
Rscript /Users/jose/Library/CloudStorage/Dropbox/LVL/Anime/04_analisis/36_auditar_hallazgos.R
```

Genera:
- Reporte en consola con `OK / REVISAR / FAIL` por hallazgo
- `VALIDACION_HALLAZGOS.csv` con la tabla detallada (id, hallazgo, prioridad, estado, número esperado, número calculado, detalle, riesgos)

Para agregar un hallazgo nuevo al chequeo: seguir el patrón de `reg("HN", "texto", function() { ... })` en el script.

---

## Nota metodológica: qué NO valida este framework

- **Validez externa**: si los hallazgos se generalizan al universo Lima. Requiere un estudio con muestreo probabilístico.
- **Causalidad**: los hallazgos son asociaciones, no relaciones causales.
- **Interpretación cualitativa**: qué significa cada patrón. Eso lo hace el investigador con soporte del diario cuali.
- **Business case**: si un hallazgo justifica una decisión de negocio. Eso requiere costos, riesgos y contexto competitivo que no están en el estudio.

Este framework valida **consistencia interna**: que lo que decimos que los datos dicen es efectivamente lo que los datos dicen. Es el mínimo indispensable para tener una conversación de negocio honesta.

---

## Archivos relacionados

- `04_analisis/36_auditar_hallazgos.R` — script de auditoría automatizada
- `04_analisis/VALIDACION_HALLAZGOS.csv` — tabla de trazabilidad
- `04_analisis/PREGUNTAS_INVESTIGACION_DIARIO.md` — 18 preguntas derivadas
- `04_analisis/bases_finales/` — CSVs fuente de verdad + HTMLs + PROCESO.txt
- `04_analisis/bases_finales/PROCESO.txt` — proceso completo del estudio
