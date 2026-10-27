# Datos de prueba

`cohorte_cardiometabolica_prueba.csv`: 400 pacientes **ficticios** (no son personas
reales), separador `;`, coma decimal, ~5 % de valores perdidos. Se regenera con
`uv run python ejemplos/generar_cohorte_prueba.py` (semilla fija, siempre igual).

| Rol en StatLab | Columnas |
|---|---|
| Identificador (I) | `id` |
| Modelo (M) | `imc`, `glucosa`, `hba1c`, `colesterol_ldl`, `trigliceridos`, `pcr`, `tas`, `creatinina` |
| Log (L) | `trigliceridos`, `pcr` (muy asimétricas) |
| Descriptiva (D) | `edad`, `sexo`, `tabaquismo`, `hospital`, `evento_cv_2a`, `perfil_simulado` |

`perfil_simulado` es la «respuesta correcta» (Sano, Metabólico, Inflamatorio, Renal):
no la metas en el modelo; ponla como descriptiva para ver si los clusters la recuperan.

Resultado esperado (KNN 5, z-score, k = 2–8): silueta, Calinski-Harabasz y
Davies-Bouldin coinciden en **k = 4** (silueta 0,47). Con k = 4: clusters de
152/125/62/61 pacientes que corresponden a Sano, Metabólico, Inflamatorio y Renal
(398 de 400 bien asignados) y Jaccard ≈ 1 en los cuatro.
