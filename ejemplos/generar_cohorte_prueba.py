"""Genera `cohorte_cardiometabolica_prueba.csv`: datos 100 % ficticios para probar StatLab.

Cuatro perfiles latentes (columna `perfil_simulado`, la «verdad» para comprobar
el clustering): sano, síndrome metabólico, inflamatorio y renal. Formato español:
separador `;`, coma decimal, UTF-8 con BOM, ~5 % de valores perdidos.

    uv run python ejemplos/generar_cohorte_prueba.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEMILLA = 2026
N = 400
# perfil: (proporción, medias de imc, glucosa, hba1c, ldl, trigliceridos, pcr, tas, creatinina)
PERFILES = {
    "Sano": (0.40, [23.5, 88, 5.2, 105, 90, 1.0, 118, 0.85]),
    "Metabólico": (0.27, [33.0, 145, 7.4, 150, 260, 3.5, 142, 0.95]),
    "Inflamatorio": (0.18, [25.0, 95, 5.6, 110, 120, 28.0, 125, 0.90]),
    "Renal": (0.15, [26.5, 110, 6.1, 125, 170, 6.0, 155, 2.6]),
}
DE = [2.5, 12, 0.5, 18, 0.30, 0.45, 10, 0.18]  # trigliceridos y pcr: DE en escala log
LOG = {4, 5}  # columnas con distribución log-normal
VARS = ["imc", "glucosa", "hba1c", "colesterol_ldl", "trigliceridos", "pcr", "tas", "creatinina"]
DECIMALES = [1, 0, 1, 0, 0, 1, 0, 2]


def generar(n: int = N, semilla: int = SEMILLA) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    nombres = list(PERFILES)
    perfil = rng.choice(nombres, size=n, p=[PERFILES[p][0] for p in nombres])
    filas = []
    for p in perfil:
        medias = PERFILES[p][1]
        valores = []
        for j, (m, s) in enumerate(zip(medias, DE, strict=True)):
            v = np.exp(rng.normal(np.log(m), s)) if j in LOG else rng.normal(m, s)
            if p == "Renal" and j == 7:  # creatinina renal más dispersa
                v = rng.normal(m, 0.6)
            valores.append(round(max(v, 0.1), DECIMALES[j]))
        filas.append(valores)
    df = pd.DataFrame(filas, columns=VARS)
    edad_media = {"Sano": 45, "Metabólico": 58, "Inflamatorio": 50, "Renal": 66}
    df.insert(0, "edad", [int(np.clip(rng.normal(edad_media[p], 11), 18, 92)) for p in perfil])
    df.insert(1, "sexo", rng.choice(["F", "M"], size=n))
    df.insert(0, "id", [f"C{i:04d}" for i in range(1, n + 1)])
    p_fuma = {"Sano": 0.15, "Metabólico": 0.35, "Inflamatorio": 0.30, "Renal": 0.25}
    df["tabaquismo"] = [rng.choice(["Nunca", "Exfumador", "Actual"], p=[1 - p_fuma[p] - 0.15, 0.15, p_fuma[p]])
                        for p in perfil]
    df["hospital"] = rng.choice(["Norte", "Sur", "Centro"], size=n)
    df["evento_cv_2a"] = [("Sí" if rng.random() < {"Sano": 0.03, "Metabólico": 0.15, "Inflamatorio": 0.08,
                                                   "Renal": 0.25}[p] else "No") for p in perfil]
    df["perfil_simulado"] = perfil
    # ~5 % de perdidos en analíticas y algo en tabaquismo
    for c in VARS:
        df.loc[rng.random(n) < 0.05, c] = np.nan
    df["tabaquismo"] = df["tabaquismo"].where(rng.random(n) >= 0.04)
    for c, d in zip(VARS, DECIMALES, strict=True):
        if d == 0:
            df[c] = df[c].round().astype("Int64")
    return df


if __name__ == "__main__":
    destino = Path(__file__).with_name("cohorte_cardiometabolica_prueba.csv")
    generar().to_csv(destino, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    print(f"Escrito {destino}")
