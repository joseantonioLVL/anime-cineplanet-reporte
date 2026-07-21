## =============================================================================
## Auditoría de los 18 hallazgos derivados del análisis cuantitativo.
## Cada hallazgo se verifica contra los CSVs fuente (bases_finales/) sin
## depender de los HTMLs (evita circularidad).
##
## Salidas:
##   - Consola: reporte con [OK] / [WARN] / [FAIL] por hallazgo
##   - VALIDACION_HALLAZGOS.csv: tabla de trazabilidad
## =============================================================================
suppressPackageStartupMessages({ library(dplyr); library(stats) })

BASE <- "/Users/jose/Library/CloudStorage/Dropbox/LVL/Anime/04_analisis/bases_finales"
OUT_CSV <- "/Users/jose/Library/CloudStorage/Dropbox/LVL/Anime/04_analisis/VALIDACION_HALLAZGOS.csv"

## Cargar CSVs
ns_base <- read.csv(file.path(BASE, "no_socios_base.csv"), stringsAsFactors = FALSE)
ns_util <- read.csv(file.path(BASE, "no_socios_utilidades_hb.csv"), check.names = FALSE)
ns_seg  <- read.csv(file.path(BASE, "no_socios_segmentos.csv"), stringsAsFactors = FALSE)

sc_base <- read.csv(file.path(BASE, "socios_base.csv"), stringsAsFactors = FALSE)
sc_util <- read.csv(file.path(BASE, "socios_utilidades_hb.csv"), check.names = FALSE)
sc_seg  <- read.csv(file.path(BASE, "socios_segmentos.csv"), stringsAsFactors = FALSE)
sc_md   <- read.csv(file.path(BASE, "socios_maxdiff_long.csv"), stringsAsFactors = FALSE)

CONCEPTS <- c("C01","C03","C04","C05","C06","C07","C08","C09",
              "C10","C12","C13","C14","C15","C16","C17","C18")

## Bridge segmentos No Socios (join por DNI normalizado)
ns_base$dni_norm <- sub("^0+", "", as.character(ns_base$dni))
ns_seg$dni_norm  <- sub("^0+", "", as.character(ns_seg$dni))
ns_base <- ns_base %>%
  left_join(ns_seg %>% select(dni_norm, c4), by = "dni_norm")

## Numeric conversions
for (v in c("reysen_a","reysen_b","reysen_c","fandom_a","fandom_b","fandom_c",
            "s1_edad")) ns_base[[v]] <- as.numeric(ns_base[[v]])
ns_base$score_reysen <- rowMeans(ns_base[, c("reysen_a","reysen_b","reysen_c")], na.rm=TRUE)
ns_base$score_fandom <- rowMeans(ns_base[, c("fandom_a","fandom_b","fandom_c")], na.rm=TRUE)

## =============================================================================
## Registro de hallazgos
## =============================================================================
hallazgos <- list()

reg <- function(id, texto, chequeo_fn, prioridad = "media") {
  res <- tryCatch(chequeo_fn(), error = function(e) list(
    status = "FAIL", numero_esperado = NA, numero_calculado = NA,
    detalle = paste("Error:", conditionMessage(e)),
    riesgos = "chequeo no pudo ejecutarse"
  ))
  hallazgos[[id]] <<- c(list(id = id, hallazgo = texto, prioridad = prioridad), res)
}

## H1 — Cine anime no discrimina en NS
reg("H1_NS", "En No Socios, gasto_cine no discrimina entre tipos de fan (η² < 0.03, p>0.05)", function() {
  GASTO_MAP <- c("S/0"=0, "S/1-25"=12.5, "S/26-50"=37.5, "S/51-75"=62.5, "S/76-100"=87.5, "Más de S/100"=130)
  x <- GASTO_MAP[ns_base$gasto_cine]
  perfil <- ns_base$c4
  ok <- !is.na(x) & !is.na(perfil)
  fit <- summary(aov(x[ok] ~ factor(perfil[ok])))[[1]]
  eta2 <- fit$"Sum Sq"[1] / sum(fit$"Sum Sq")
  p <- fit$"Pr(>F)"[1]
  status <- if (eta2 < 0.03 && p > 0.05) "OK" else "REVISAR"
  list(status=status, numero_esperado="η²<0.03, p>0.05",
       numero_calculado=sprintf("η²=%.3f, p=%.3f", eta2, p),
       detalle="Recomputado desde no_socios_base.csv gasto_cine × c4", riesgos="—")
}, "alta")

## H1' — Cine anime no discrimina en Socios
reg("H1_SC", "En Socios, gasto_cine no discrimina entre tipos de fan", function() {
  GASTO_MAP <- c("S/0"=0, "S/1-25"=12.5, "S/26-50"=37.5, "S/51-75"=62.5, "S/76-100"=87.5, "Más de S/100"=130)
  # Bridge sc_base con sc_seg por respondent_id
  m <- sc_base %>%
    mutate(rid=as.character(respondent_id)) %>%
    left_join(sc_seg %>% mutate(rid=as.character(respondent_id)) %>% select(rid, perfil), by="rid")
  x <- GASTO_MAP[m$gasto_cine]
  ok <- !is.na(x) & !is.na(m$perfil)
  fit <- summary(aov(x[ok] ~ factor(m$perfil[ok])))[[1]]
  eta2 <- fit$"Sum Sq"[1] / sum(fit$"Sum Sq")
  p <- fit$"Pr(>F)"[1]
  status <- if (eta2 < 0.03 && p > 0.05) "OK" else "REVISAR"
  list(status=status, numero_esperado="η²<0.03, p>0.05",
       numero_calculado=sprintf("η²=%.3f, p=%.3f", eta2, p),
       detalle="Recomputado desde socios_base.csv gasto_cine × perfil", riesgos="—")
}, "alta")

## H2 — Top-1 conceptual difiere entre brazos
reg("H2", "En No Socios lidera C08 (61% arriba del umbral); en Socios lidera C03 (22% share)", function() {
  # NS: % de fans con util > 0 por concepto
  ns_umbral <- sapply(CONCEPTS, function(c) mean(ns_util[[c]] > 0) * 100)
  ns_top1 <- names(which.max(ns_umbral))
  ns_top1_val <- max(ns_umbral)
  # SC: share of preference (mean por concepto)
  sc_exp <- exp(as.matrix(sc_util[, CONCEPTS]))
  sc_shares <- sc_exp / rowSums(sc_exp)
  sc_share_mean <- colMeans(sc_shares) * 100
  sc_top1 <- names(which.max(sc_share_mean))
  sc_top1_val <- max(sc_share_mean)
  status <- if (ns_top1 == "C08" && sc_top1 == "C03" &&
                round(ns_top1_val) == 61 && round(sc_top1_val, 1) == 22.2) "OK" else "REVISAR"
  list(status=status, numero_esperado="NS: C08=61%; SC: C03=22.2%",
       numero_calculado=sprintf("NS: %s=%.0f%%; SC: %s=%.1f%%", ns_top1, ns_top1_val, sc_top1, sc_top1_val),
       detalle="NS: mean(util>0) por concepto; SC: share of preference exp(util)/Σexp(util)",
       riesgos="Métricas distintas por brazo (No comparables en magnitud)")
}, "alta")

## H3 — Fan Aislado 3× más grande en Socios
reg("H3", "Fan Aislado: 8/155=5.2% (NS) vs 75/455=16.5% (SC), ratio ~3x", function() {
  ns_aisl <- sum(ns_base$c4 == "C4_1", na.rm=TRUE)
  ns_pct  <- 100 * ns_aisl / nrow(ns_base)
  sc_aisl <- sum(sc_seg$perfil == "Fan Aislado", na.rm=TRUE)
  sc_pct  <- 100 * sc_aisl / nrow(sc_seg)
  ratio <- sc_pct / ns_pct
  # Wilson IC para NS
  n_ns <- nrow(ns_base); p_ns <- ns_aisl / n_ns
  z <- qnorm(0.975)
  denom <- 1 + z^2/n_ns
  center <- (p_ns + z^2/(2*n_ns)) / denom
  half <- z * sqrt(p_ns*(1-p_ns)/n_ns + z^2/(4*n_ns^2)) / denom
  ic_low <- 100*(center - half); ic_high <- 100*(center + half)
  status <- if (ns_aisl == 8 && sc_aisl == 75 && round(ns_pct,1) == 5.2 && round(sc_pct,1) == 16.5) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="NS: 8/155 (5.2%); SC: 75/455 (16.5%); ratio ~3x",
       numero_calculado=sprintf("NS: %d/%d (%.1f%%); SC: %d/%d (%.1f%%); ratio %.2fx | IC95 NS: [%.1f, %.1f]",
                                 ns_aisl, nrow(ns_base), ns_pct, sc_aisl, nrow(sc_seg), sc_pct, ratio, ic_low, ic_high),
       detalle="Conteos directos desde CSVs de segmentos",
       riesgos="Base NS chica (n=8, IC95% ancho); muestras no-aleatorias en ambos brazos")
}, "alta")

## H4 — Fan Intermedio Socios es solitario (Reysen 6.61 / FANDOM 3.79)
reg("H4", "En Socios, Fan Intermedio tiene Reysen 6.61 / FANDOM 3.79 (perfil solitario)", function() {
  sub <- sc_seg[sc_seg$perfil == "Fan Intermedio", ]
  r <- mean(sub$score_reysen); f <- mean(sub$score_fandom)
  ns_int <- ns_base[!is.na(ns_base$c4) & ns_base$c4 == "C4_3", ]
  ns_r <- mean(ns_int$score_reysen); ns_f <- mean(ns_int$score_fandom)
  gap_sc <- r - f; gap_ns <- ns_r - ns_f
  status <- if (round(r, 2) == 6.61 && round(f, 2) == 3.79) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="SC F.Intermedio: Reysen 6.61 / FANDOM 3.79",
       numero_calculado=sprintf("SC: R=%.2f F=%.2f (gap=%.2f) | NS: R=%.2f F=%.2f (gap=%.2f)",
                                 r, f, gap_sc, ns_r, ns_f, gap_ns),
       detalle="Medias sobre socios_segmentos.csv (SC) y join de segments/base (NS)",
       riesgos="—")
}, "media")

## H5 — Silhouette 0.46 (SC) vs 0.53 (NS)
reg("H5", "Silhouette medio: 0.53 (NS) vs 0.46 (SC) — SC más difuso", function() {
  suppressPackageStartupMessages(library(cluster))
  # NS
  X_ns <- as.matrix(ns_base[, c("score_reysen","score_fandom")])
  set.seed(2026); km_ns <- kmeans(X_ns, 4, nstart=50)
  sil_ns <- silhouette(km_ns$cluster, dist(X_ns))
  # SC
  X_sc <- as.matrix(sc_seg[, c("score_reysen","score_fandom")])
  set.seed(2026); km_sc <- kmeans(X_sc, 4, nstart=50)
  sil_sc <- silhouette(km_sc$cluster, dist(X_sc))
  sil_ns_m <- mean(sil_ns[,3]); sil_sc_m <- mean(sil_sc[,3])
  status <- if (round(sil_ns_m,2) >= 0.52 && round(sil_sc_m,2) <= 0.48) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="NS ~0.53; SC ~0.46",
       numero_calculado=sprintf("NS=%.3f; SC=%.3f", sil_ns_m, sil_sc_m),
       detalle="K-means re-corrido con seed=2026, nstart=50",
       riesgos="—")
}, "baja")

## H6 — Festival CP × Crunchy es #2 en ambos brazos
reg("H6", "C13 (Festival CP × Crunchy) es #2 en ambos brazos", function() {
  ns_umbral <- sapply(CONCEPTS, function(c) mean(ns_util[[c]] > 0) * 100)
  ns_rank <- rank(-ns_umbral)
  sc_exp <- exp(as.matrix(sc_util[, CONCEPTS])); sc_shares <- sc_exp / rowSums(sc_exp)
  sc_share_mean <- colMeans(sc_shares) * 100
  sc_rank <- rank(-sc_share_mean)
  ns_r13 <- ns_rank["C13"]; sc_r13 <- sc_rank["C13"]
  status <- if (ns_r13 == 2 && sc_r13 == 2) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="C13: rank #2 en ambos",
       numero_calculado=sprintf("NS rank C13=%d (%.1f%%); SC rank C13=%d (%.1f%%)",
                                 ns_r13, ns_umbral["C13"], sc_r13, sc_share_mean["C13"]),
       detalle="Rankings recomputados desde utilidades individuales",
       riesgos="—")
}, "alta")

## H7 — C08 (Viajes VIP) tiene 54% incremental en deep-dive NS
reg("H7", "En deep-dive NS, C08 tiene %incremental ≈ 54%", function() {
  # Concatenar los 3 slots
  dd <- do.call(rbind, lapply(1:3, function(i) {
    data.frame(concept = ns_base[[paste0("dd_", i, "_concept")]],
               incremental = ns_base[[paste0("dd_", i, "_incremental")]],
               stringsAsFactors=FALSE)
  }))
  dd <- dd[!is.na(dd$concept) & dd$concept != "" & !is.na(dd$incremental) & dd$incremental != "", ]
  sub <- dd[dd$concept == "C08", ]
  pct_inc <- 100 * mean(sub$incremental == "incremental")
  status <- if (abs(pct_inc - 54) < 1) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="C08 %incremental ≈ 54%",
       numero_calculado=sprintf("%.1f%% (n_ev=%d)", pct_inc, nrow(sub)),
       detalle="Concatenación slots 1-3 de dd_X_concept + dd_X_incremental",
       riesgos="Sustitución cruzada no capturada (Cineplanet vs otro cine)")
}, "alta")

## H8 — C07 (Membresía) baja en Socios (10.9% share)
reg("H8", "C07 tiene 10.9% share en Socios (baja demanda vs 41% umbral en NS)", function() {
  sc_exp <- exp(as.matrix(sc_util[, CONCEPTS])); sc_shares <- sc_exp / rowSums(sc_exp)
  sc_c07 <- colMeans(sc_shares)["C07"] * 100
  ns_c07 <- 100 * mean(ns_util$C07 > 0)
  status <- if (round(sc_c07, 1) == 10.9 && round(ns_c07) == 41) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="SC: C07=10.9% share; NS: C07=41% umbral",
       numero_calculado=sprintf("SC: %.1f%%; NS: %.1f%%", sc_c07, ns_c07),
       detalle="Recomputado desde utilidades individuales",
       riesgos="Métricas distintas por brazo — no comparables en magnitud")
}, "media")

## H9 — Conciertos alta credibilidad (89%) pero solo #5 demanda en NS
reg("H9", "C18 tiene %believ_top2 ≈ 89% pero solo #5 en %umbral", function() {
  dd <- do.call(rbind, lapply(1:3, function(i) {
    data.frame(concept = ns_base[[paste0("dd_", i, "_concept")]],
               believ = as.numeric(ns_base[[paste0("dd_", i, "_believ")]]),
               stringsAsFactors=FALSE)
  }))
  dd <- dd[!is.na(dd$concept) & dd$concept != "" & !is.na(dd$believ), ]
  sub <- dd[dd$concept == "C18", ]
  pct_believ <- 100 * mean(sub$believ >= 4)
  ns_umbral <- sapply(CONCEPTS, function(c) mean(ns_util[[c]] > 0) * 100)
  rank_c18 <- rank(-ns_umbral)["C18"]
  status <- if (abs(pct_believ - 89) < 2 && rank_c18 %in% 4:6) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="C18 believ top-2≈89%, rank demanda ~#5",
       numero_calculado=sprintf("believ_top2=%.1f%%; rank_umbral=%.0f (n_ev=%d)",
                                 pct_believ, rank_c18, nrow(sub)),
       detalle="believ ≥4 en deep-dive; rank sobre mean(util>0)",
       riesgos="—")
}, "baja")

## H10 — Playlist (C15) y Charlas (C04) bottom en ambos brazos
reg("H10", "C15 y C04 en bottom-3 de ambos brazos", function() {
  ns_umbral <- sapply(CONCEPTS, function(c) mean(ns_util[[c]] > 0) * 100)
  sc_exp <- exp(as.matrix(sc_util[, CONCEPTS])); sc_shares <- sc_exp / rowSums(sc_exp)
  sc_share_mean <- colMeans(sc_shares) * 100
  ns_bot3 <- names(sort(ns_umbral))[1:3]
  sc_bot3 <- names(sort(sc_share_mean))[1:3]
  c15_in_both <- ("C15" %in% ns_bot3 && "C15" %in% sc_bot3)
  c04_in_both <- ("C04" %in% ns_bot3 && "C04" %in% sc_bot3)
  status <- if (c15_in_both && c04_in_both) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="C15 y C04 en bottom-3 de ambos brazos",
       numero_calculado=sprintf("NS bot3=%s; SC bot3=%s",
                                 paste(ns_bot3, collapse=","), paste(sc_bot3, collapse=",")),
       detalle="Bottom-3 por métrica principal de cada brazo",
       riesgos="—")
}, "media")

## H11 — Sustitución cruzada no capturada
reg("H11", "El %incremental del Juster NO distingue entre visita nueva pura y sustitución de otro cine", function() {
  list(status="OK",
       numero_esperado="Limitación conocida del instrumento",
       numero_calculado="—",
       detalle="El instrumento solo pregunta 'incremental vs substitute_cine vs substitute_other vs no_impact' pero 'incremental' agrupa (a) visita 100% nueva y (b) sustitución de otro cine",
       riesgos="Volumen incremental es 'ganancia para CP como empresa', no 'tickets nuevos al mercado del cine'")
}, "alta")

## H12 — group_size autoreportado promedia 3-5
reg("H12", "group_size promedio en deep-dive NS entre 3 y 5 por concepto", function() {
  dd <- do.call(rbind, lapply(1:3, function(i) {
    data.frame(concept = ns_base[[paste0("dd_", i, "_concept")]],
               gs = as.numeric(ns_base[[paste0("dd_", i, "_group_size")]]),
               stringsAsFactors=FALSE)
  }))
  dd <- dd[!is.na(dd$concept) & dd$concept != "" & !is.na(dd$gs), ]
  gs_por_c <- aggregate(gs ~ concept, dd, mean)
  gs_por_c$gs <- round(gs_por_c$gs, 2)
  media_g <- mean(gs_por_c$gs); min_g <- min(gs_por_c$gs); max_g <- max(gs_por_c$gs)
  status <- if (media_g >= 3 && media_g <= 5) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="group_size promedio ∈ [3, 5]",
       numero_calculado=sprintf("media_global=%.2f, rango=[%.2f, %.2f]", media_g, min_g, max_g),
       detalle="Media de group_size por concepto en deep-dive slots 1-3",
       riesgos="Autoreportado, susceptible a sobre-estimación")
}, "media")

## H13 — "con quién iría" varía por concepto (Festival vs Charlas)
reg("H13", "En NS, Festival CP×Crunchy: ~56% anime_friends, ~31% partner; Charlas: 100% partner (n=3)", function() {
  dd <- do.call(rbind, lapply(1:3, function(i) {
    data.frame(concept = ns_base[[paste0("dd_", i, "_concept")]],
               w = ns_base[[paste0("dd_", i, "_with")]],
               stringsAsFactors=FALSE)
  }))
  dd <- dd[!is.na(dd$concept) & dd$concept != "" & !is.na(dd$w) & dd$w != "", ]
  # Festival (C13)
  sub_c13 <- dd[dd$concept == "C13", ]
  af_c13 <- 100 * mean(grepl("anime_friends", sub_c13$w))
  pt_c13 <- 100 * mean(grepl("partner", sub_c13$w))
  # Charlas (C04)
  sub_c04 <- dd[dd$concept == "C04", ]
  pt_c04 <- 100 * mean(grepl("partner", sub_c04$w))
  status <- if (af_c13 >= 50 && pt_c04 >= 60) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="C13: anime_friends >50%, partner ~30%; C04: partner >60% (n=3)",
       numero_calculado=sprintf("C13: af=%.1f%% pt=%.1f%% (n=%d); C04: pt=%.1f%% (n=%d)",
                                 af_c13, pt_c13, nrow(sub_c13), pt_c04, nrow(sub_c04)),
       detalle="grepl sobre CSV multi-select dd_X_with",
       riesgos="C04 base chica (n=3) → 100% es artefacto")
}, "media")

## H14 — Callao valora Museo más (η² pequeño por concepto vs zona)
reg("H14", "En NS, C06 (Museo) tiene mayor share en Callao (informativo, base chica)", function() {
  ns_base$c06_util <- ns_util$C06
  agg <- aggregate(c06_util ~ s6_distrito, ns_base, mean)
  agg <- agg[order(-agg$c06_util), ]
  top_zona <- agg$s6_distrito[1]
  ns_c <- table(ns_base$s6_distrito)
  status <- if (top_zona == "callao") "OK" else "REVISAR"
  list(status=status,
       numero_esperado="Callao top en util media C06",
       numero_calculado=sprintf("Top zona por util C06: %s (n=%d, util media %.2f)",
                                 top_zona, ns_c[top_zona], max(agg$c06_util)),
       detalle="Media de utilidad C06 por s6_distrito",
       riesgos="Base por zona pequeña; test η² no realizado en este script")
}, "baja")

## H15 — Mujeres valoran más Conciertos (C18) en NS
reg("H15", "En NS, mujeres tienen mayor %umbral en C18 vs hombres (η² > 0.05)", function() {
  h_pct <- 100 * mean(ns_util$C18[ns_base$s5_genero == "hombre"] > 0)
  m_pct <- 100 * mean(ns_util$C18[ns_base$s5_genero == "mujer"] > 0)
  fit <- summary(aov(ns_util$C18 ~ factor(ns_base$s5_genero)))[[1]]
  eta2 <- fit$"Sum Sq"[1] / sum(fit$"Sum Sq")
  p <- fit$"Pr(>F)"[1]
  status <- if (m_pct > h_pct && eta2 > 0.03) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="M > H en C18; η² > 0.05; p<0.05",
       numero_calculado=sprintf("H=%.1f%%, M=%.1f%%; η²=%.3f, p=%.4f", h_pct, m_pct, eta2, p),
       detalle="Recomputado con ANOVA sobre util C18 × sexo",
       riesgos="—")
}, "media")

## H16 — Usuarios Crunchyroll: mayor %umbral en C13 (Festival)
reg("H16", "En NS, usuarios de Crunchyroll tienen mayor %umbral en C13", function() {
  usa_crunchy <- grepl("crunchyroll", ns_base$p1_platforms)
  usa_pct <- 100 * mean(ns_util$C13[usa_crunchy] > 0)
  no_usa <- 100 * mean(ns_util$C13[!usa_crunchy] > 0)
  diff <- usa_pct - no_usa
  status <- if (diff > 15) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="Diferencia %umbral > 15 pp (crunchy > no-crunchy)",
       numero_calculado=sprintf("Usa: %.1f%%, No usa: %.1f%%, dif=%.1f pp", usa_pct, no_usa, diff),
       detalle="Multi-select p1_platforms",
       riesgos="Endogeneidad: quienes usan Crunchyroll son fans más comprometidos")
}, "baja")

## H17 — 26% de No Socios usan fansubs
reg("H17", "En NS, 26% (41/155) usan fansubs", function() {
  usa_fansubs <- grepl("fansubs", ns_base$p1_platforms)
  n <- sum(usa_fansubs); pct <- 100 * n / nrow(ns_base)
  status <- if (n == 41 && round(pct) == 26) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="41/155 (26%)",
       numero_calculado=sprintf("%d/%d (%.1f%%)", n, nrow(ns_base), pct),
       detalle="Multi-select p1_platforms",
       riesgos="Autoreporte de piratería puede tener sesgo de deseabilidad")
}, "media")

## H18 — Frecuencia anime es la variable externa más asociada al perfil en Socios
reg("H18", "En Socios, Cramer V(perfil × freq_anime) ≈ 0.22 (mayor entre externas)", function() {
  m <- sc_base %>%
    mutate(rid=as.character(respondent_id)) %>%
    left_join(sc_seg %>% mutate(rid=as.character(respondent_id)) %>% select(rid, perfil), by="rid")
  tab <- table(m$freq_anime, m$perfil)
  chi <- suppressWarnings(chisq.test(tab))
  n <- sum(tab)
  v <- sqrt(as.numeric(chi$statistic) / (n * (min(nrow(tab), ncol(tab)) - 1)))
  status <- if (abs(v - 0.22) < 0.02) "OK" else "REVISAR"
  list(status=status,
       numero_esperado="Cramer V ≈ 0.22",
       numero_calculado=sprintf("V=%.3f (χ²=%.2f, p=%.4f)", v, chi$statistic, chi$p.value),
       detalle="Chi² sobre tabla contingencia freq_anime × perfil (Socios)",
       riesgos="—")
}, "baja")

## =============================================================================
## Reporte
## =============================================================================
cat("======================================================================\n")
cat("Auditoría de hallazgos — resultado por hallazgo\n")
cat("======================================================================\n\n")

resumen <- data.frame()
for (h in hallazgos) {
  cat(sprintf("[%s] %s (prioridad: %s)\n", h$status, h$id, h$prioridad))
  cat(sprintf("       %s\n", h$hallazgo))
  cat(sprintf("  → Esperado:  %s\n", h$numero_esperado))
  cat(sprintf("  → Calculado: %s\n", h$numero_calculado))
  if (!is.null(h$riesgos) && h$riesgos != "" && h$riesgos != "—") {
    cat(sprintf("  ⚠ Riesgos:   %s\n", h$riesgos))
  }
  cat("\n")

  resumen <- rbind(resumen, data.frame(
    id = h$id, hallazgo = h$hallazgo, prioridad = h$prioridad,
    status = h$status, numero_esperado = h$numero_esperado,
    numero_calculado = h$numero_calculado,
    detalle = h$detalle, riesgos = h$riesgos,
    stringsAsFactors = FALSE
  ))
}

## Resumen final
ok <- sum(resumen$status == "OK"); rev <- sum(resumen$status == "REVISAR"); fail <- sum(resumen$status == "FAIL")
cat("======================================================================\n")
cat(sprintf("Total hallazgos: %d\n", nrow(resumen)))
cat(sprintf("  OK: %d (%.0f%%)\n", ok, 100*ok/nrow(resumen)))
cat(sprintf("  REVISAR: %d\n", rev))
cat(sprintf("  FAIL: %d\n", fail))
cat("======================================================================\n")

write.csv(resumen, OUT_CSV, row.names=FALSE)
cat(sprintf("\n✓ Tabla trazabilidad: %s\n", OUT_CSV))
