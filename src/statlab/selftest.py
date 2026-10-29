"""Autocomprobación del paquete compilado: `StatLab --self-test resultado.txt`.

Recorre el análisis completo con los datos de ejemplo (sin pedir nada al usuario),
crea la ventana y exporta todos los formatos en una carpeta temporal. Si a
PyInstaller le faltó empaquetar un archivo de datos o un módulo, falla aquí.
Escribe el resultado en un archivo porque una app de ventana no tiene consola
en Windows.
"""
from __future__ import annotations

import tempfile
import time
import traceback
from pathlib import Path

CRITERIO = {"tamanos": [109, 76, 55], "silueta_2": 0.557}


def _pipeline(salida: Path) -> list[str]:
    from statlab.core import session as ses
    from statlab.core.dataset import Rol
    from statlab.core.prep.preparacion import de_ejemplo
    from statlab.core.prep.receta import Paso
    from statlab.core.report import exports as ex
    from statlab.modules.kmeans.module import KMeansModule, ajustar, barrer, preprocesar

    log = []
    mod = KMeansModule()
    e = mod.crear_estado()
    # Preparación: una variable calculada (no entra en el modelo, así que no cambia el criterio)
    e.preparacion = de_ejemplo()
    e.preparacion.receta.añadir(Paso("calcular", {"destino": "hb_vcm", "formula": "SI(vcm > 0; hb / vcm)"}))
    e.preparacion.diccionario.entrada("hb").etiqueta = "Hemoglobina"
    e.dataset, preparado = e.preparacion.dataset()
    assert not preparado.errores and "hb_vcm" in e.dataset.columnas
    log.append("preparación: ok")
    e.dataset.asignar_rol(["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"], Rol.MODELO)
    e.dataset.alternar_log(["ferritina"])
    e.dataset.asignar_rol(["edad", "sexo"], Rol.DESCRIPTIVA)
    e.resultados["preprocesado"] = preprocesar(e)
    e.params("elegir_k").update(bootstrap=False)
    sweep = barrer(e, lambda f: None, lambda: False)
    assert round(sweep["silueta"][0], 3) == CRITERIO["silueta_2"], sweep["silueta"][0]
    e.resultados["elegir_k"] = sweep
    e.params("modelo_final").update(k=3, B=10)
    final = ajustar(e, lambda f: None, lambda: False)
    assert final["tamanos"] == CRITERIO["tamanos"], final["tamanos"]
    e.resultados["modelo_final"] = final
    log.append("análisis: ok (109/76/55)")
    # GMM, jerárquico y comparación (scikit-learn mixture, SciPy hierarchy y optimize en el paquete)
    from statlab.core import clustering as clu
    from statlab.core import comparacion as cmp

    X = e.resultados["preprocesado"]["_preparado"].X
    gmm = clu.algoritmo("gmm").ajustar(X, 3, {"covarianza": "diag", "n_init": 2}, 1)
    jer = clu.algoritmo("jerarquico").ajustar(X, 3, {"enlace": "ward"}, 0)
    a = cmp.Solucion("GMM", gmm.labels.tolist(), list(range(len(X))), huella="x")
    b = cmp.Solucion("Jerárquico", jer.labels.tolist(), list(range(len(X))), huella="x")
    assert 0 <= cmp.comparar(a, b, B=20)["ari"] <= 1
    log.append("GMM, jerárquico y comparación: ok")
    files = ex.escribir("todo", mod.exportar(e), salida / "exportes", base="selftest")
    log.append(f"exportes: {len(files)} archivos")
    path = ses.guardar(salida / "sesion.statlab", e, mod.id)
    again = ses.abrir(path, mod.crear_estado, mod.id)
    assert again.resultados["modelo_final"]["tamanos"] == CRITERIO["tamanos"]
    log.append("sesión: ok")
    return log


def _window() -> str:
    from PySide6.QtCore import QTimer

    from statlab.app import create_app
    from statlab.modules import available_modules
    from statlab.ui.main_window import MainWindow

    app = create_app([])
    w = MainWindow(available_modules()[0])
    w.show()
    w.session.load_example()
    QTimer.singleShot(300, lambda: app.exit(0))  # quit() intentaría cerrar la ventana
    app.exec()
    assert w.data_panel.model.rowCount() == 240
    font = app.font().family()
    w.session.shutdown()  # sin close(): no debe preguntar por cambios sin guardar
    w.hide()
    w.deleteLater()
    return f"ventana: ok (fuente {font})"


def run(result_file: str | None) -> int:
    t0 = time.perf_counter()
    lines: list[str] = []
    code = 0
    try:
        lines.append(_window())
        with tempfile.TemporaryDirectory() as tmp:
            lines += _pipeline(Path(tmp))
        lines.append(f"OK en {time.perf_counter() - t0:.1f} s")
    except Exception:  # noqa: BLE001 - se informa todo en el archivo de resultado
        code = 1
        lines.append("FALLO")
        lines.append(traceback.format_exc())
    text = "\n".join(lines) + "\n"
    if result_file:
        Path(result_file).write_text(text, encoding="utf-8")
    else:
        try:
            print(text)
        except (AttributeError, OSError):  # sin consola
            pass
    return code
