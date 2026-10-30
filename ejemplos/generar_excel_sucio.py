"""Genera `registro_sucio_prueba.xlsx`: un Excel «sucio» y 100 % ficticio para probar
el modo «Preparar datos» de StatLab.

Parte de la cohorte de prueba (`cohorte_cardiometabolica_prueba.csv`) y le añade los
problemas típicos de un Excel clínico real:

- hoja de instrucciones delante; los datos están en la hoja «Registro»
- título y fila vacía antes de la cabecera; cabecera de dos filas (celdas combinadas)
- hemoglobina en g/dL, salvo un hospital que la registró en g/L
- sexo escrito de varias formas («M», «m », «Mujer»…) y tabaquismo con mayúsculas
- 999 como código de «sin dato» en la glucosa
- PCR con límite de detección («<0,5») guardada como texto
- fechas dd/mm/aaaa (inclusión, evento y último contacto) para calcular el seguimiento
- un paciente duplicado y una fila de totales al final

    uv run python ejemplos/generar_excel_sucio.py
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font

SEMILLA = 7
CARPETA = Path(__file__).parent


def generar() -> Path:
    rng = np.random.default_rng(SEMILLA)
    df = pd.read_csv(CARPETA / "cohorte_cardiometabolica_prueba.csv", sep=";", decimal=",", encoding="utf-8-sig")
    n = len(df)
    hb = np.round(rng.normal(13.5, 1.4, n), 1)
    sur = df["hospital"].eq("Sur").to_numpy()
    hb_txt = [int(round(v * 10)) if s else v for v, s in zip(hb, sur, strict=True)]  # g/L en el hospital Sur
    sexo = df["sexo"].map({"F": "Mujer", "M": "Hombre"}).to_numpy(dtype=object)
    for i in rng.choice(n, 25, replace=False):
        variantes = {"Mujer": ["M", "mujer", "MUJER "], "Hombre": ["H", "hombre", "Varón"]}
        sexo[i] = rng.choice(variantes[sexo[i]])
    tabaco = df["tabaquismo"].fillna("").to_numpy(dtype=object)
    for i in rng.choice(n, 20, replace=False):
        tabaco[i] = str(tabaco[i]).upper()
    glucosa = df["glucosa"].to_numpy(dtype=object)
    for i in rng.choice(n, 12, replace=False):
        glucosa[i] = 999
    pcr = [("<0,5" if (not pd.isna(v) and v < 0.5) else ("" if pd.isna(v) else f"{v:.1f}".replace(".", ",")))
           for v in df["pcr"]]
    inicio = [date(2019, 1, 1) + timedelta(days=int(d)) for d in rng.integers(0, 730, n)]
    evento = df["evento_cv_2a"].eq("Sí").to_numpy()
    f_evento = [(i + timedelta(days=int(rng.integers(30, 700)))) if e else None
                for i, e in zip(inicio, evento, strict=True)]
    f_ultimo = [i + timedelta(days=int(rng.integers(300, 900))) for i in inicio]

    wb = Workbook()
    nota = wb.active
    nota.title = "Instrucciones"
    nota["A1"] = "Registro cardiometabólico de prueba — DATOS FICTICIOS"
    nota["A2"] = "Los datos están en la hoja «Registro». Hb del hospital Sur en g/L. 999 = sin dato."
    ws = wb.create_sheet("Registro")
    ws["A1"] = "Registro cardiometabólico (datos ficticios, generados para probar StatLab)"
    ws["A1"].font = Font(bold=True)
    grupos = [("Paciente", 4), ("Analítica", 8), ("Hábitos", 1), ("Seguimiento", 3)]
    col = 1
    for nombre, ancho in grupos:
        ws.cell(row=3, column=col, value=nombre).font = Font(bold=True)
        ws.merge_cells(start_row=3, start_column=col, end_row=3, end_column=col + ancho - 1)
        col += ancho
    cabecera = ["id", "hospital", "edad", "sexo", "imc", "glucosa", "hba1c", "colesterol_ldl", "trigliceridos",
                "pcr", "hb", "creatinina", "tabaquismo", "fecha_inclusion", "fecha_evento", "fecha_ultimo_contacto"]
    for j, c in enumerate(cabecera, start=1):
        ws.cell(row=4, column=j, value=c).font = Font(bold=True)

    def celda(v):
        if v is None or (isinstance(v, float) and np.isnan(v)) or v == "":
            return None
        return v

    filas = list(range(n)) + [17]  # el paciente 18 aparece dos veces
    for r, i in enumerate(filas, start=5):
        valores = [df["id"][i], df["hospital"][i], int(df["edad"][i]), sexo[i], df["imc"][i], glucosa[i],
                   df["hba1c"][i], df["colesterol_ldl"][i], df["trigliceridos"][i], pcr[i], hb_txt[i],
                   df["creatinina"][i], tabaco[i], inicio[i].strftime("%d/%m/%Y"),
                   f_evento[i].strftime("%d/%m/%Y") if f_evento[i] else None, f_ultimo[i].strftime("%d/%m/%Y")]
        for j, v in enumerate(valores, start=1):
            ws.cell(row=r, column=j, value=celda(v))
    ws.cell(row=5 + len(filas), column=1, value="Total pacientes")
    ws.cell(row=5 + len(filas), column=2, value=len(filas))
    destino = CARPETA / "registro_sucio_prueba.xlsx"
    wb.save(destino)
    return destino


if __name__ == "__main__":
    print(f"Escrito {generar()}")
