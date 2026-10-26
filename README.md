# StatLab

Aplicación de escritorio para análisis estadístico clínico. El primer módulo es
**clustering k-means**: barrido de k, modelo final, validación por bootstrap
(silueta, Jaccard por cluster tipo *clusterboot*), perfiles y sensibilidad a la
imputación. Pensada para clínicos: interfaz gráfica, sin escribir código, y
**sin conexión**: los datos nunca salen del equipo.

> Estado: **M5 · sesiones y exportes**. Análisis completo (datos → roles → preprocesado →
> barrido de k → modelo final) con sesiones `.statlab` que se reabren sin recalcular, y
> exportes: CSV con cluster y silueta, JSON, texto de métodos, figuras PNG/SVG e informes
> PDF y Word. Falta el empaquetado con PyInstaller (M6).
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
               fmt.py (números en español), kmeans.py (motor), session.py (.statlab),
               report/ (figuras matplotlib, PDF, Word, CSV/JSON/métodos)
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
