# StatLab

Aplicación de escritorio para análisis estadístico clínico. El primer módulo es
**clustering**: k-means, mezclas gaussianas (GMM) y jerárquico, con barrido de k,
modelo final, validación por bootstrap (silueta, Jaccard por cluster tipo
*clusterboot*), perfiles, sensibilidad a la imputación, **comparación de
soluciones** (ARI), preparación de datos, sesiones guardables e informes PDF y Word. Pensada para clínicos:
interfaz gráfica, sin escribir código y **sin conexión**: los datos nunca salen
del equipo (no hay telemetría ni comprobación de actualizaciones).

## Para usuarios

### Descargar

En la página **Releases** del repositorio, descarga el paquete de tu sistema:

| Sistema | Archivo |
|---|---|
| Windows 10/11 (64 bits) | `StatLab-<versión>-windows-x64.zip` |
| Linux (x86-64; Ubuntu 22.04 o posterior y equivalentes) | `StatLab-<versión>-linux-x86_64.tar.gz` |
| macOS con Apple Silicon (M1 o posterior) | `StatLab-<versión>-macos-arm64.zip` |

No hace falta instalar Python ni nada más, ni permisos de administrador.

### Abrir

- **Windows**: descomprime el zip en una carpeta tuya (por ejemplo,
  `Documentos\StatLab`) y haz doble clic en `StatLab.exe`. La primera vez,
  Windows puede mostrar «Windows protegió su PC» (SmartScreen) porque el programa
  no está firmado: pulsa **Más información → Ejecutar de todas formas**. Si el
  antivirus del hospital lo bloquea, el servicio de informática tendrá que
  autorizar la carpeta de StatLab.
- **Linux**: `tar xzf StatLab-*.tar.gz` y doble clic en `StatLab` dentro de la
  carpeta. `./instalar-acceso-directo.sh` lo añade al menú de aplicaciones.
- **macOS**: descomprime y arrastra `StatLab.app` a Aplicaciones. La primera vez,
  **clic derecho → Abrir → Abrir** (no está firmado por Apple).

### Cómo se usa

1. **Datos**: «Abrir datos…» (CSV, TSV o Excel) o «Probar con datos de ejemplo».
   Al abrir un archivo se entra en **1 · Preparar datos** (selector de la cabecera):
   - **Archivo**: en Excel, la hoja y la fila de la cabecera (se detectan solas, también
     cabeceras de dos filas y filas de totales al final).
   - **Revisión de calidad**: duplicados, números guardados como texto («<0,5»), fechas,
     la misma categoría escrita de varias formas, códigos como 999, unidades mezcladas…
     Cada aviso propone una corrección que se ve antes de aplicarla; nada se cambia solo.
   - **Receta**: cada cambio es un paso que se puede desactivar, reordenar, editar o borrar.
     El archivo original nunca se modifica. «Añadir paso» incluye la calculadora de nuevas
     variables (fórmulas como en Excel: `peso / (talla/100)^2`), tiempo entre fechas,
     tiempo de seguimiento y evento, categorizar, recodificar y excluir filas con su motivo.
   - **Mis fórmulas**: guarda tus cálculos para reutilizarlos en otros archivos.
   - **Diccionario**: etiqueta, unidad, límites plausibles y códigos de perdido de cada
     variable (importable y exportable en Excel o CSV). Las etiquetas salen en el informe.
   - **Diagrama de flujo de pacientes**: se construye con las exclusiones y va al informe.

   Después, **2 · Analizar**:
2. **Variables y filas**: en la tabla, selecciona columnas (clic, arrastre,
   Mayús/Ctrl) y pulsa **M** (modelo), **D** (descriptiva), **I** (identificador)
   o **L** (log). Para filas, selecciona sus números y usa la barra ámbar.
3. **Preprocesado**: valores perdidos y escalado; el resultado se ve al momento.
4. **Elegir k**: «Calcular barrido de k» y haz clic en el punto del k elegido.
   En GMM se elige también la forma de los clusters (el gráfico de BIC compara las
   cuatro); en el jerárquico, el tipo de enlace, y el k se elige cortando el dendrograma.
5. **Modelo final**: «Ajustar y validar». Cifras clave, PCA (clic o lazo
   seleccionan filas en la tabla), perfiles, silueta, estabilidad, sensibilidad y
   descriptivas.
6. **Exportar**: informe PDF o Word, figuras, CSV con el cluster de cada paciente,
   JSON y texto de métodos.

**Varios análisis sobre los mismos datos**: «+ Nuevo análisis» abre otra pestaña
(k-means, GMM o jerárquico) con los mismos datos, roles y filas que el análisis activo;
la preparación de datos es común a todos. En GMM, la pestaña «Pertenencia» muestra la
probabilidad de cada paciente y permite seleccionar los de frontera.

**Comparar soluciones**: la pestaña «Comparar soluciones» calcula el índice de Rand
ajustado (ARI) entre dos soluciones, con su IC y su interpretación, el % de pacientes en el
mismo grupo, el flujo entre clusters (Sankey: clic en una banda para ver esos pacientes),
la tabla cruzada y la lista de los que cambian de grupo. También se pueden importar
soluciones de otra sesión `.statlab` o de un CSV con columnas `id` y `cluster` (por
ejemplo, de R o SPSS).

«Guardar sesión» guarda todo en un archivo `.statlab` que se vuelve a abrir tal
cual: el archivo original, la receta, el diccionario, todos los análisis y las soluciones
importadas.

En `ejemplos/` hay datos ficticios para probar: `cohorte_cardiometabolica_prueba.csv`
(limpio, 4 perfiles) y `registro_sucio_prueba.xlsx` (el mismo con los problemas típicos de
un Excel clínico, para practicar la preparación). **Ese archivo, el CSV y el JSON contienen los datos de los pacientes:
guárdalos en un lugar seguro.**

## Desarrollo

Requiere [uv](https://docs.astral.sh/uv/). uv instala Python 3.12 si hace falta.

```bash
uv sync                 # crea .venv con las dependencias
uv run statlab          # abre la aplicación (o: uv run python -m statlab)
uv run pytest           # tests del motor y de la interfaz
uv run ruff check src tests
uv run statlab --self-test resultado.txt   # análisis completo y exportes, sin ventana de por medio
```

En Linux, Qt necesita algunas librerías del sistema
(`libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3`). Para lanzar los
tests sin pantalla: `QT_QPA_PLATFORM=offscreen uv run pytest`. Con
`STATLAB_CAPTURAS=docs/capturas` los tests de interfaz guardan capturas.

### Empaquetado y versiones

```bash
uv sync --group build
uv run pyinstaller packaging/statlab.spec --noconfirm   # → dist/StatLab/ (o dist/StatLab.app)
```

El workflow **Build** (`.github/workflows/build.yml`) genera los tres paquetes
(Windows, Linux y macOS) con PyInstaller en modo *onedir*. Comprueba cada
ejecutable con `--self-test`, que recorre el análisis con los datos de ejemplo y
exporta todos los formatos. Para publicar una versión, cualquiera de estas vías:

- **Subir la versión** en `pyproject.toml` y `src/statlab/__init__.py` en una rama de
  trabajo e integrarla en `main` con una pull request: al llegar a `main` una versión que
  aún no tiene etiqueta, el workflow la crea y publica la Release con los tres paquetes.
- **Etiqueta**: `git tag v0.2.0 && git push origin v0.2.0`.
- **A mano**: pestaña *Actions* → *Build* → *Run workflow*, con `version` = `v0.2.0`
  (vacío = solo compilar; los paquetes quedan como artefactos del run).

El workflow **Tests** ejecuta ruff y pytest en cada push.

Limitaciones conocidas: el ejecutable no está firmado (SmartScreen en Windows,
Gatekeeper en macOS), y el paquete de macOS es solo para Apple Silicon.

## Estructura

```
src/statlab/
  core/        lógica pura, sin Qt: io.py (lectura), dataset.py (roles y filas),
               clustering.py (k-means, GMM, jerárquico), comparacion.py (ARI),
               prep/ (receta, fórmulas, revisión de calidad, diccionario, Mis fórmulas),
               flow.py (estados de los pasos), estado.py (estado de la sesión),
               fmt.py (números en español), kmeans.py (motor), session.py (.statlab),
               report/ (figuras matplotlib, PDF, Word, CSV/JSON/métodos)
  modules/     contrato AnalysisModule (base.py) y módulo kmeans/
  ui/          ventana, tabla de datos, barra lateral, prep/ (modo «Preparar datos»),
               tema (tokens, QSS, Inter, iconos)
  workers.py   cálculos en segundo plano (QThreadPool) con progreso y cancelación
  selftest.py  autocomprobación del paquete compilado
  strings_es.py  textos de la interfaz
  data/        datos de ejemplo integrados
packaging/     PyInstaller (statlab.spec), iconos, acceso directo de Linux, licencias
tests/         core/ (pytest) y ui/ (pytest-qt)
docs/          documento de traspaso, alcance (ALCANCE_statlab.md) y capturas de cada hito
ejemplos/      datos de prueba ficticios y sus generadores
prototipo/     versión Streamlit anterior, solo como referencia
```

## Licencias de terceros

StatLab incluye Qt (vía PySide6) bajo la **LGPL v3**, enlazado de forma dinámica
(las bibliotecas de Qt van como archivos separados dentro del paquete), y la
fuente Inter bajo la SIL Open Font License 1.1. Detalle y textos completos en
[`packaging/licenses/`](packaging/licenses/THIRD_PARTY_NOTICES.md), que se copian
dentro de cada paquete.
