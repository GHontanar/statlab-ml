# StatLab

Aplicación de escritorio para análisis estadístico clínico. El primer módulo es
**clustering k-means**: barrido de k, modelo final, validación por bootstrap
(silueta, Jaccard por cluster tipo *clusterboot*), perfiles y sensibilidad a la
imputación. Pensada para clínicos: interfaz gráfica, sin escribir código, y
**sin conexión**: los datos nunca salen del equipo.

> Estado: **M2 · pasos 1–3**. Se cargan datos, se asignan roles desde la tabla y se
> preprocesan (valores perdidos y escalado) con vista previa; la barra lateral marca
> cada paso como hecho, activo, pendiente o desactualizado. El barrido de k y el
> modelo final llegan en los siguientes hitos.
> Plan completo en [`docs/HANDOFF_statlab-desktop.md`](docs/HANDOFF_statlab-desktop.md).

## Desarrollo

Requiere [uv](https://docs.astral.sh/uv/). uv instala Python 3.12 si hace falta.

```bash
uv sync                 # crea .venv con las dependencias
uv run statlab          # abre la aplicación (o: uv run python -m statlab)
uv run pytest           # tests del motor y de la interfaz
uv run ruff check src tests
```

En Linux, Qt necesita algunas librerías del sistema
(`libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3`). Para lanzar los
tests sin pantalla: `QT_QPA_PLATFORM=offscreen uv run pytest`. Con
`STATLAB_CAPTURAS=docs/capturas` los tests de interfaz guardan capturas.

## Estructura

```
src/statlab/
  core/        lógica pura, sin Qt: io.py (lectura), dataset.py (roles y filas),
               flow.py (estados de los pasos), estado.py (estado de la sesión),
               fmt.py (números en español), kmeans.py (motor)
  modules/     contrato AnalysisModule (base.py) y módulo kmeans/
  ui/          ventana, tabla de datos, barra lateral, tema (tokens, QSS, Inter, iconos)
  workers.py   cálculos en segundo plano (QThreadPool) con progreso y cancelación
  strings_es.py  textos de la interfaz
  data/        datos de ejemplo integrados
tests/         core/ (pytest) y ui/ (pytest-qt)
prototipo/     versión Streamlit anterior, solo como referencia
```

## Licencias de terceros

- Qt for Python (PySide6), bajo LGPL v3; se enlaza de forma dinámica.
- Fuente Inter, bajo SIL Open Font License 1.1 (`src/statlab/ui/theme/fonts/Inter-LICENSE.txt`).
