# StatLab Desktop · módulo k-means — documento de traspaso

> Para una nueva sesión de Claude Code. Este documento define el alcance, las decisiones ya cerradas
> y el plan. Va acompañado de `statlab-ml-prototipo.zip`, que contiene el motor de cálculo ya probado.
> **No reabras decisiones de la tabla "Decisiones cerradas" sin preguntar a Guzmán.**

## 1. Objetivo

Construir una **aplicación de escritorio en Python con PySide6** para análisis estadístico clínico
(StatLab), modular, cuyo **primer módulo es clustering k-means**. La usarán **clínicos no técnicos**:
interfaz gráfica, sin escribir código y sin LLM. Se abre con **doble clic**, sin terminal, en
**Windows y Linux** (prioritarios) y también en macOS.

Boceto visual de referencia (canvas con 3 pantallas, privado de Guzmán):
https://claude.ai/artifact/UCaaZUwGUHLy8mGazNniNC

1. **Barrido de k**: barra lateral con 6 pasos, tabla de datos con roles por columna, codo y silueta.
2. **Modelo final**: tabla con columna `cluster`, 4 cifras clave, pestaña Resumen (PCA + mapa de calor).
3. **Selección en la tabla**: arrastrar cabeceras o números de fila, barras flotantes, menú de rol.

El boceto es la referencia de distribución y estilo. Si hay contradicción, manda este documento.

## 2. Decisiones cerradas

| Tema | Decisión |
|---|---|
| Interfaz | PySide6 (Qt 6), estilizado con QSS sobre el estilo base **Fusion** (mismo aspecto en todos los SO) |
| Gráficos en la app | **pyqtgraph**, interactivos (clic en punto, lazo, hover) |
| Gráficos exportados | **matplotlib**, con la misma paleta, PNG 300 dpi y SVG |
| Distribución | Barra lateral de proceso + tabla de datos + panel de resultados, **visibles a la vez** |
| Selección | Clic, Mayús+clic, Ctrl/⌘+clic y **arrastrar** en cabeceras (columnas) y en números de fila (filas) |
| Usuarios | Clínicos no técnicos: ayudas contextuales, validaciones y mensajes claros |
| Arquitectura | StatLab **modular**: k-means es el primer módulo y los siguientes se enchufan sin tocar la base |
| Lenguaje natural / LLM | **No** en v1. Solo interfaz gráfica |
| Variables del modelo | **Solo numéricas** en v1. Las categóricas solo como descriptivas |
| Tamaño de datos | Hasta **~5.000 filas**: cálculo exacto (silueta sin submuestreo hasta 5.000) |
| Sesiones | «Guardar sesión» guarda **todo en un archivo**: datos, parámetros y resultados |
| Exportes | CSV + JSON + texto de métodos, **figuras PNG/SVG**, **informe PDF** e **informe Word (.docx)** |
| Empaquetado | PyInstaller, compilado por **GitHub Actions** (Windows, Linux, macOS) al publicar una versión |
| Repositorio | Repo nuevo **`statlab-desktop`** en el GitHub de Guzmán (`ghontanar`) |
| Idioma | Español. Textos centralizados para poder traducir más adelante |
| Privacidad | **Cero red**: sin telemetría, sin comprobar actualizaciones, fuentes empaquetadas |

## 3. Qué se reutiliza del prototipo (`statlab-ml-prototipo.zip`)

El prototipo es una versión en Streamlit. **Se reutiliza el motor y se descarta la interfaz.**

| Archivo | Qué hacer |
|---|---|
| `statlab_ml/kmeans_core.py` | **Reutilizar casi tal cual** → `src/statlab/core/kmeans.py`. Funciones puras y probadas |
| `tests/test_core.py` | Reutilizar (10 tests, pasan) y ajustar los imports |
| `ejemplo/datos_ejemplo.csv` | Reutilizar como datos de ejemplo integrados (240 filas sintéticas, `;` y coma decimal, ~6 % de NA) |
| `statlab_ml/plots.py` | **No** reutilizar el código (es Plotly). Sí conservar la paleta, los símbolos y las decisiones de cada gráfico |
| `statlab_ml/ui_kmeans.py`, `app.py`, `pages/`, `tests/test_app.py` | Descartar (Streamlit). Sirve de referencia del flujo y de los textos |

Ajustes pendientes en el motor:
- Subir `SILHOUETTE_MAX_N` de 4000 a 5000.
- Separar `read_table`/`coerce_decimal_commas` en `core/io.py`.
- Añadir progreso y cancelación cooperativa a los bucles de bootstrap. Los `progress` callbacks ya existen; falta un `should_cancel()`.

Lo que hace el motor (no reimplementar):
- `read_table`: CSV/TSV/Excel; detecta el separador y la coma decimal; tokens NA (`""`, `NA`, `nan`, `n/a`, `-`…).
- `prepare`: transformación log(1+x) opcional por variable; imputación por casos completos, media, mediana o KNN; escalado z-score, robusto o ninguno; avisos.
  - Con **KNN: escalar → imputar → re-escalar**, para que la distancia no la domine la variable de mayor rango.
- `sweep_k` (inercia, silueta, Calinski-Harabasz, Davies-Bouldin, tamaño mínimo) y `sweep_k_bootstrap` (IC95 % de la silueta por k).
- `fit_kmeans`: **renumera los clusters por tamaño** (C1 = el más grande) y reordena los centroides.
- `bootstrap_validate`, tipo *clusterboot* (Hennig 2007):
  - IC95 % de la silueta, evaluada sobre los **datos originales**, nunca sobre la remuestra, porque los duplicados la inflan.
  - Jaccard medio por cluster con su IC, % de remuestras en que el cluster "se disuelve" (Jaccard < 0,5) y ARI.
- `jaccard_label`: ≥ 0,85 muy estable, ≥ 0,75 estable, ≥ 0,60 dudoso, < 0,60 inestable.
- `cluster_profiles` (media (DE) en escala original + matriz z), `describe_external` (mediana [RIC] o n (%)), `pca_2d`.
- `imputation_sensitivity`: ARI entre las particiones obtenidas con cada método de imputación, sobre las filas comunes.
- `methods_text`: párrafo de métodos en español, listo para adaptar en un manuscrito.

## 4. Stack

- Python 3.12 · PySide6 · pyqtgraph · numpy · pandas · scikit-learn · openpyxl (Excel)
- matplotlib (figuras exportadas) · reportlab (PDF) · python-docx (Word)
- pytest + pytest-qt (tests de interfaz) · ruff
- PyInstaller en modo **onedir**: arranca más rápido que onefile y cumple mejor la LGPL de Qt.
- Gestión de dependencias con `uv` y `pyproject.toml`.
- **No** añadir pyarrow, QtWebEngine ni Plotly: aumentan mucho el tamaño y no se necesitan.

## 5. Arquitectura

```
statlab-desktop/
  pyproject.toml
  src/statlab/
    __main__.py            # python -m statlab
    app.py                 # QApplication, tema, fuente, ventana principal
    core/                  # SIN Qt: lógica pura y testeable
      io.py                # lectura de datos y detección de formato
      kmeans.py            # motor del prototipo
      session.py           # guardar/abrir archivo .statlab
      report/              # pdf.py, docx.py, figures.py (matplotlib)
    ui/
      theme/               # tokens.py (colores, espaciados), style.qss, fonts/Inter*.ttf, icons/*.svg
      main_window.py       # cabecera + barra lateral + zona central (tabla arriba, resultados abajo, QSplitter)
      data_table/          # QTableView + modelo pandas + delegates + barras flotantes + menú de rol
      sidebar/             # stepper de pasos (tarjetas plegables)
      charts/              # envoltorios pyqtgraph con la paleta (líneas, dispersión, heatmap, barras, histograma)
      widgets/             # interruptor, chips, tarjetas KPI, slider de rango, ayuda "?"
    modules/
      base.py              # interfaz AnalysisModule (ver abajo)
      kmeans/              # module.py, steps.py (widgets de cada paso), panels.py (resultados)
    workers.py             # QThreadPool/QRunnable con progreso y cancelación
    strings_es.py          # textos de la interfaz centralizados
  tests/                   # core (pytest) + ui (pytest-qt)
  packaging/statlab.spec, packaging/linux/statlab.desktop, packaging/windows/statlab.ico
  .github/workflows/build.yml
```

**Contrato de módulo** (`modules/base.py`). Así se enchufarán supervivencia, comparaciones, etc.:
- `id`, `nombre`, `icono`.
- `pasos()`: lista ordenada de pasos con su widget de parámetros, su resumen de una línea y su validación.
- Los pasos comunes (Datos, Variables y filas, Exportar) los aporta la base. El módulo aporta los suyos: en k-means, Preprocesado, Elegir k y Modelo final.
- `roles_admitidos()`: qué roles de columna usa el módulo. En k-means, Modelo (numérica), Descriptiva, Identificador y Log.
- `ejecutar(paso, contexto, progreso, cancelar)`: corre en un worker y devuelve un resultado serializable.
- `paneles(resultado)`: widgets del panel de resultados de cada paso.
- `exportar(resultado)`: aporta secciones al informe, figuras y tablas.

**Reglas**: `core/` no importa Qt; la UI nunca bloquea el hilo principal; todo cálculo es
determinista con la semilla; el estado de la sesión vive en un único objeto de modelo serializable.

## 6. Interfaz (detalle)

### Ventana
- **Cabecera**: logo y "StatLab", nombre del módulo, insignia "Solo en este equipo · sin conexión", y los botones «Abrir datos…» y «Guardar sesión».
- Debajo, tres zonas visibles a la vez:
  - **barra lateral de proceso** a la izquierda (≈320 px, redimensionable);
  - **tabla de datos** arriba a la derecha;
  - **panel de resultados** abajo a la derecha.
- La tabla y los resultados van en un `QSplitter` vertical que se puede ajustar.
- Modo claro y oscuro: sigue al sistema y se puede forzar en el menú Ver. Ambos se generan de los mismos tokens.

### Barra lateral: pasos
1. Datos · 2. Variables y filas · 3. Preprocesado · 4. Elegir k · 5. Modelo final · 6. Exportar.

- Estados visuales: **hecho** (✓ verde + resumen de una línea), **activo** (borde azul + controles), **pendiente** (atenuado) y **desactualizado** (aviso ámbar).
- Al cambiar un paso anterior, los posteriores pasan a *desactualizado*: conservan el resultado visible pero marcado, con un botón «Recalcular».
- Hacer clic en un paso hecho lo reabre para editarlo.
- El paso 2 se rellena **desde la tabla** (ver abajo) y muestra las etiquetas de rol en tiempo real: Modelo (n), Descriptivas (n), Identificador, Filas (todas o n seleccionadas).
- **Paso 3**: valores perdidos (casos completos, media, mediana o KNN con nº de vecinos 1–15) y escalado (z-score, robusto o ninguno). Muestra n analizadas, n excluidas y celdas imputadas, más los avisos del motor.
- **Paso 4**:
  - rango de k (slider doble, 2–8; el máximo es 8 por la paleta);
  - inicializaciones (20), semilla (2026);
  - interruptor «IC bootstrap de la silueta por k» con remuestras por k (20–200, por defecto 50);
  - botón «Calcular barrido de k».
- **Paso 5**: k elegido y remuestras bootstrap (50/100/200/500/1000, por defecto 200), con el botón «Ajustar y validar». El k también se elige haciendo clic en un punto del codo o de la silueta.
- **Paso 6**: botones de exportación (sección 8).

### Tabla de datos (componente clave)
- `QTableView` sobre un modelo pandas: ordenar por columna, cabeceras fijas, scroll fluido con 5.000 × 50.
- Fila extra bajo la cabecera con la **etiqueta de rol** de cada columna:
  - MODELO en azul, DESCR. en naranja, ID en gris, sin usar como "—";
  - "log" como insignia azul oscura junto a MODELO.
- Las columnas del modelo llevan un tinte azul suave. Los **NA** se ven en cursiva roja sobre rosa pálido.
- Gestos:
  - **clic** en una cabecera o número de fila selecciona esa columna o fila;
  - **arrastrar** por las cabeceras selecciona varias columnas, y por los números de fila, varias filas;
  - **Mayús+clic** selecciona un rango; **Ctrl/⌘+clic** añade o quita;
  - **clic derecho** en una cabecera abre el menú de rol (Usar en el modelo / Variable descriptiva / Identificador / Sin usar / Ver resumen y NA);
  - atajos **M D I L** (Modelo, Descriptiva, Identificador, alternar log) y **Esc** para limpiar.
- **Barra flotante de columnas** (oscura, con sombra, sobre la tabla): «n columnas · Modelo · Descriptivas · Aplicar log · Quitar rol».
- **Barra flotante de filas** (ámbar, abajo): «n filas seleccionadas · Analizar solo estas · Excluir del análisis · Guardar como subgrupo… · Limpiar».
- Si se asigna MODELO a una columna no numérica, no se aplica y se explica por qué (solo numéricas en v1).
- Tras el modelo final, la tabla gana las columnas `cluster` (pastilla con color y símbolo) y `silueta`. Encima aparecen botones «Resaltar: C1 · C2 · C3 · Todos»: las filas del cluster elegido se resaltan y las demás se atenúan.

### Panel de resultados
- **Tras el paso 4**:
  - etiquetas «Mejor k según cada índice» (silueta, Calinski-Harabasz, Davies-Bouldin, codo ≈);
  - gráfico del codo y gráfico de silueta por k con barras de IC; el k elegido va marcado con un anillo;
  - tabla de índices por k, con el mejor de cada columna en negrita;
  - tarjeta «Continuar con el modelo final».
- **Tras el paso 5**:
  - 4 tarjetas KPI: Silueta media, IC95 % bootstrap, ARI medio vs bootstrap, Clusters poco estables (Jaccard < 0,75);
  - tamaños de los clusters.
- **Pestañas** tras el paso 5:
  - **Resumen**:
    - PCA (CP1/CP2 con % de varianza; color **y** símbolo por cluster; centroides como rombos con borde y etiqueta);
    - mapa de calor de perfiles (z, divergente azul–gris–rojo, valor en cada celda);
    - **clic en un punto o lazo** selecciona esas filas en la tabla; **clic en una fila del mapa de calor** muestra la media (DE) en unidades originales.
  - **Silueta**: barras por observación, ordenadas dentro de cada cluster, con línea de la media y % de siluetas negativas.
  - **Estabilidad**: Jaccard medio por cluster con IC y líneas en 0,75 y 0,60; histograma bootstrap de la silueta; tabla con interpretación y % de disolución.
  - **Sensibilidad a la imputación**: matriz de ARI entre métodos, n por método y aviso si algún ARI es < 0,8.
  - **Variables descriptivas**: mediana [RIC] o n (%) por cluster, sin p-valores.
  - Aviso fijo: las variables del modelo **no se comparan con contrastes**, porque difieren por construcción.

### Ayudas para no técnicos
- Icono «?» en cada parámetro con una explicación de 1–2 frases en lenguaje clínico. Los textos están en `strings_es.py`.
- Mensajes de error humanos, sin trazas: menos de 2 variables, n ≤ k máx., variable vacía, archivo ilegible.
- Al primer arranque, una pantalla de bienvenida con «Abrir datos…» y «Probar con datos de ejemplo».
- Todos los cálculos largos muestran progreso y se pueden cancelar.

### Estilo (tokens; ver el boceto)
- **Fuente** Inter (400/500/600/700, empaquetada) y cifras tabulares en las tablas.
- **Superficies**:
  - fondo `#EEEDE9`, paneles `#FFFFFF`, barra lateral `#F7F6F3`;
  - bordes `#E2E1DC` y líneas de tabla `#EFEEEA`;
  - radios de 10–12 px en tarjetas y 8 px en botones.
- **Textos**: principal `#1C1C1A`, secundario `#55544F`, atenuado `#6E6D68`.
- **Acento** `#1F63BA`. Hecho `#1F7A4D`. NA `#9A3B2E` sobre `#FBF1EE`.
- **Roles**: MODELO `#DCE8FA`/`#174F96` · DESCR. `#FBE7D8`/`#8A3D10` · ID `#E6E5E1`/`#3F3E3A`.
- **Series**, en orden fijo y nunca cicladas: `#2a78d6 #eb6834 #1baf7a #eda100 #e87ba4 #008300 #6250d6 #e34948`.
- **Símbolos** por cluster: círculo, cuadrado, rombo, triángulo, x, cruz, estrella, triángulo invertido. El color nunca es el único canal.
- **Divergente**: `#1c5cab → #6da7ec → #f0efec → #ec8a88 → #c43a3a`. Texto blanco en celdas con |z| > 1,1.
- **Números en formato español**: coma decimal en la interfaz, los gráficos y los exportes.

## 7. Sesiones
- Archivo `.statlab`: un **zip** con `meta.json` (versión del formato y de la app, fecha), `data.csv` (los datos tal cual se cargaron), `state.json` (roles, filas, parámetros de cada paso, paso activo) y `results.json` (resultados serializados, incluidas las etiquetas).
- Al abrir, se restaura todo sin recalcular. Si la versión del formato es antigua, se migra o se avisa.
- **Nunca pickle**, porque puede ejecutar código arbitrario.
- Aviso al guardar: «El archivo contiene los datos de los pacientes; guárdalo en una ubicación segura».
- Sin autoguardado en v1. Al cerrar con cambios sin guardar, se pregunta.

## 8. Exportes
- **CSV** con `cluster` y `silueta` (`;` y coma decimal, UTF-8 con BOM para Excel), **JSON** de parámetros y resultados, **métodos** en .md.
- **Figuras** PNG a 300 dpi y SVG, con matplotlib y la misma paleta: codo, silueta por k, silueta por observación, PCA, mapa de calor, Jaccard e histograma bootstrap.
- **Informe PDF** (reportlab), **en este orden**: portada (fecha, archivo, n), parámetros, barrido de k, modelo final (KPIs), figuras, tablas de perfiles, descriptivas y estabilidad, sensibilidad, texto de métodos y versiones de las librerías.
- **Informe Word** (python-docx): el mismo contenido, editable.

## 9. Empaquetado y CI
- PyInstaller onedir, con Inter e iconos incluidos como datos.
- **Windows**: zip **portable**, que no necesita permisos de administrador (importante en los PCs del hospital), con `StatLab.exe`.
- **Linux**: tar.gz con un `.desktop`. AppImage queda como opcional más adelante.
- **macOS**: `.app` en un zip.
- GitHub Actions, con matriz `windows-latest`, `ubuntu-22.04` (por la glibc antigua) y `macos-latest`. Se dispara con cada etiqueta `v*` y adjunta los artefactos a la Release. En cada push ejecuta los tests (pytest-qt con `QT_QPA_PLATFORM=offscreen`).
- Riesgos conocidos:
  - el ejecutable de Windows sin firmar mostrará el aviso de SmartScreen, y el antivirus del hospital podría bloquearlo (documentarlo en el README; la firma de código queda fuera de v1);
  - PySide6 es LGPL: incluir su aviso de licencia y no enlazar Qt de forma estática.

## 10. Fuera de alcance en v1
LLM o lenguaje natural · categóricas en el modelo (k-prototypes/Gower) · otros algoritmos (jerárquico,
GMM, DBSCAN) · más de 8 clusters · datos > 5.000 filas · autoguardado · instalador MSI/firma de código ·
otros idiomas · otros módulos de StatLab (la arquitectura los permite, pero no se implementan).

## 11. Hitos y criterios de aceptación
1. **M0 · Andamiaje**: repo, `pyproject`, estructura, el motor movido con sus tests en verde, CI de tests, ventana vacía con el tema aplicado.
2. **M1 · Tabla**: carga CSV/Excel (incluido el de ejemplo); roles por clic, arrastre, menú y atajos; las dos barras flotantes; NA visibles; selección de filas.
3. **M2 · Pasos 1–3**: el stepper con sus estados y la invalidación en cascada; preprocesado con resumen y avisos.
4. **M3 · Barrido de k**: worker con progreso y cancelación, codo y silueta con IC, tabla de índices, elección de k por clic.
5. **M4 · Modelo final**: KPIs, pestañas, enlace PCA/lazo ↔ tabla, columna `cluster` y resaltado.
6. **M5 · Sesiones y exportes**: `.statlab` de ida y vuelta, CSV/JSON/métodos, figuras, PDF y DOCX.
7. **M6 · Empaquetado**: Actions genera los artefactos de los 3 SO; probado con doble clic en Windows y Linux; README para usuarios.

**Aceptación final**, sobre `datos_ejemplo.csv` con hb, vcm, plaquetas, neutrófilos, hbf y ferritina (log), KNN 5, z-score, k = 2–8 y semilla 2026:
- el barrido da silueta máxima en k = 2 (0,557) y Calinski-Harabasz máximo en k = 3;
- con k = 3, los clusters tienen 109 / 76 / 55 casos, con silueta media de 0,52 y Jaccard ≈ 1 en los tres;
- los clusters reproducen los fenotipos simulados A / C / B, salvo 1 caso A asignado a C2.

Además:
- La UI no se congela durante ningún cálculo.
- Cerrar y reabrir la sesión deja la pantalla idéntica.
- El .exe portable arranca en un Windows limpio sin Python instalado.

## 12. Cómo trabajar
- Al terminar cada hito, haz una captura de cada pantalla (pytest-qt `grab()`) para revisarla frente al boceto.
- Pregunta a Guzmán antes de cambiar una decisión de la sección 2 o de añadir dependencias pesadas.
- Commits pequeños por hito, en ramas `feat/mN-…`.
