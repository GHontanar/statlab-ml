"""Textos de la interfaz, centralizados para poder traducirlos más adelante."""

APP_NAME = "StatLab"
OFFLINE_BADGE = "Solo en este equipo · sin conexión"

# Cabecera y menús
OPEN_DATA = "Abrir datos…"
SAVE_SESSION = "Guardar sesión"
TRY_EXAMPLE = "Probar con datos de ejemplo"
QUIT = "Salir"
MENU_FILE = "&Archivo"
MENU_VIEW = "&Ver"
MENU_HELP = "Ay&uda"
MENU_THEME = "Tema"
THEME_SYSTEM = "Seguir al sistema"
THEME_LIGHT = "Claro"
THEME_DARK = "Oscuro"
ABOUT = "Acerca de StatLab"
ABOUT_TEXT = (
    "<b>StatLab</b> {version}<br><br>"
    "Análisis estadístico para investigación clínica.<br>"
    "Todos los cálculos se hacen en este equipo: no se envía ningún dato por la red.<br><br>"
    "Construido con Qt {qt} (PySide6, LGPL v3), pyqtgraph, scikit-learn, pandas y numpy.<br>"
    "Fuente Inter (SIL Open Font License 1.1)."
)

# Barra lateral
SIDEBAR_TITLE = "Proceso"
STEP_DATA = "Datos"
STEP_VARIABLES = "Variables y filas"
STEP_EXPORT = "Exportar"
STEP_PENDING_HINT = "Pendiente"
STEP_DATA_HINT = "Abre un archivo CSV o Excel para empezar."

# Zona central
WELCOME_TITLE = "Abre un archivo de datos para empezar"
WELCOME_BODY = (
    "CSV, TSV o Excel, con una fila por paciente y una columna por variable. "
    "Se detectan automáticamente el separador, la coma decimal y los valores perdidos."
)
RESULTS_EMPTY = "Los resultados aparecerán aquí a medida que completes los pasos."

# Módulo k-means
KMEANS_NAME = "Clustering k-means"
KMEANS_DESC = "Grupos compactos alrededor de un centro. Rápido y el más usado."
GMM_NAME = "Mezclas gaussianas (GMM)"
GMM_DESC = "Grupos con forma y tamaño propios; da la probabilidad de pertenencia de cada paciente."
HIER_NAME = "Clustering jerárquico"
HIER_DESC = "Árbol de agrupamientos (dendrograma): se elige dónde cortarlo."
STEP_PREPROCESS = "Preprocesado"
STEP_CHOOSE_K = "Elegir k"
STEP_FINAL_MODEL = "Modelo final"

# Lectura de datos
OPEN_DIALOG_TITLE = "Abrir datos"
OPEN_DIALOG_FILTER = "Datos (*.csv *.tsv *.txt *.xlsx *.xlsm *.xls);;Todos los archivos (*)"
READ_ERROR_TITLE = "No se ha podido abrir el archivo"
READ_ERROR = "No he podido leer «{name}».\n\n{reason}"
READ_ERROR_GENERIC = (
    "Comprueba que es un CSV, TSV o Excel con una fila de cabecera y una fila por paciente."
)
READ_ENCODING = "La codificación del texto no es reconocible. Guárdalo como CSV UTF-8 desde Excel."
READ_TOO_SMALL = "El archivo tiene menos de 2 columnas o ninguna fila con datos."
XLS_UNSUPPORTED = "El formato .xls antiguo no está admitido. Ábrelo en Excel y guárdalo como .xlsx."
DATA_SUMMARY = "{name} · {rows} filas × {cols} columnas"
DATA_NA = "{n} celdas vacías (NA)"

# Roles de columna
ROLE_LABEL_MODEL = "MODELO"
ROLE_LABEL_DESCR = "DESCR."
ROLE_LABEL_ID = "ID"
ROLE_LABEL_LOG = "log"
ROLE_LABEL_NONE = "—"
ROLE_USE_MODEL = "Usar en el modelo"
ROLE_USE_DESCR = "Variable descriptiva"
ROLE_USE_ID = "Identificador"
ROLE_TOGGLE_LOG = "Aplicar log(1+x)"
ROLE_CLEAR = "Sin usar"
ROLE_SUMMARY = "Ver resumen y NA…"
SORT_ASC = "Ordenar de menor a mayor"
SORT_DESC = "Ordenar de mayor a menor"
SORT_CLEAR = "Orden original"
ROLE_NOT_NUMERIC = (
    "«{col}» no es numérica y no puede usarse en el modelo: en esta versión el modelo solo "
    "admite variables numéricas. Puedes usarla como variable descriptiva."
)
ROLE_ONE_ID = "Solo puede haber una columna identificador: elige una sola columna."
LOG_NOT_NUMERIC = "«{col}» no es numérica: no se le puede aplicar log."
LOG_NEGATIVE = "«{col}» tiene valores negativos: log(1+x) no está definido para ellos."

# Barras flotantes
FLOAT_COLUMNS = "{n} columna(s)"
FLOAT_MODEL = "Modelo"
FLOAT_DESCR = "Descriptivas"
FLOAT_LOG = "Aplicar log"
FLOAT_CLEAR_ROLE = "Quitar rol"
FLOAT_ROWS = "{n} fila(s) seleccionada(s)"
FLOAT_ONLY_THESE = "Analizar solo estas"
FLOAT_EXCLUDE = "Excluir del análisis"
FLOAT_SUBGROUP = "Guardar como subgrupo…"
FLOAT_CLEAR = "Limpiar"
SUBGROUP_TITLE = "Guardar subgrupo"
SUBGROUP_PROMPT = "Nombre del subgrupo ({n} filas):"
SUBGROUP_EMPTY_NAME = "El subgrupo necesita un nombre."
SUBGROUP_SAVED = "Subgrupo «{name}» guardado ({n} filas)."

# Paso 2 (variables y filas)
VARS_MODEL = "Modelo ({n})"
VARS_DESCR = "Descriptivas ({n})"
VARS_ID = "Identificador: {id}"
VARS_ROWS = "Filas: {rows}"
VARS_NONE = "ninguna"
VARS_HINT = "Se eligen con clic o arrastrando en la tabla. Clic derecho en una cabecera para más opciones."
VARS_SHORTCUTS = "Atajos: M modelo · D descriptiva · I identificador · L log · Esc limpiar"
VARS_USE_ALL_ROWS = "Usar todas las filas"
VARS_SUBGROUPS = "Subgrupos: {names}"
ROWS_ALL = "todas ({n})"
ROWS_SOME = "{n} de {total}"

# Resumen de columna
SUM_TITLE = "Resumen de «{col}»"
SUM_TYPE = "Tipo"
SUM_NUMERIC = "Numérica"
SUM_TEXT = "Texto / categórica"
SUM_N = "Valores presentes"
SUM_OF = "de"
SUM_NA = "Valores perdidos (NA)"
SUM_MEAN_SD = "Media (DE)"
SUM_MEDIAN_IQR = "Mediana [RIC]"
SUM_RANGE = "Mínimo – máximo"
SUM_DISTINCT = "Valores distintos"
SUM_NEGATIVE = "Valores negativos"
SUM_MORE_LEVELS = "{n} niveles más"
CLOSE = "Cerrar"

# Flujo de pasos
CONTINUE = "Continuar"
RECALCULATE = "Recalcular"
EDIT = "Editar"
CHANGE = "Cambiar"
STALE_NOTE = "Desactualizado: has cambiado un paso anterior."
STALE_BLOCKED = "Recalcula antes «{step}»."
RUNNING = "Calculando…"
CANCEL = "Cancelar"
CALC_ERROR = "No se ha podido completar el cálculo."
CALC_ERROR_DETAIL = "Ha ocurrido un error inesperado al calcular «{step}». Revisa los datos y vuelve a intentarlo."
NEXT_MILESTONE = "Este paso estará disponible en la próxima versión."
VAL_MIN_VARS = "Elige al menos 2 variables numéricas para el modelo (ahora hay {n})."
VAL_MIN_ROWS = "Solo hay {n} filas para analizar; se necesitan al menos {min}."
VAL_EMPTY_VAR = "Sin ningún valor en las filas elegidas: {cols}. Quítalas del modelo."

# Paso 3 (preprocesado)
PREP_MISSING = "Valores perdidos"
PREP_NEIGHBORS = "Vecinos"
PREP_SCALING = "Escalado"
PREP_RESULT = "{n} filas analizadas · {excl} excluidas · {imp} celdas imputadas"
PREP_SUMMARY_MISSING = "Perdidos: {method} ({imp} celdas imputadas)"
PREP_SUMMARY_MISSING_KNN = "Perdidos: KNN, {k} vecinos ({imp} celdas imputadas)"
PREP_SUMMARY_COMPLETE = "Perdidos: casos completos ({excl} filas excluidas)"
PREP_SUMMARY_SCALING = "Escalado: {method}"
PREP_LOG = "log(1+x): {cols}"
SCALING_SHORT = {"standard": "z-score", "robust": "robusto (mediana/RIC)", "none": "sin escalar"}
MISSING_SHORT = {"complete": "casos completos", "mean": "media", "median": "mediana", "knn": "KNN"}
HELP_MISSING = (
    "Cómo se rellenan los valores que faltan. KNN estima cada valor a partir de los pacientes más "
    "parecidos; «casos completos» descarta a quien tenga algún valor perdido en las variables del modelo."
)
HELP_NEIGHBORS = (
    "Cuántos pacientes parecidos se usan para estimar cada valor que falta. 5 es un buen punto de partida."
)
HELP_SCALING = (
    "Pone las variables en una escala comparable para que ninguna pese más solo por sus unidades. "
    "z-score es lo habitual; «robusto» resiste mejor los valores extremos."
)
PREP_MISSING_OPTIONS = {
    "knn": "KNN (pacientes parecidos)",
    "median": "Mediana",
    "mean": "Media",
    "complete": "Casos completos",
}
PREP_SCALING_OPTIONS = {"standard": "z-score", "robust": "Robusto (mediana/RIC)", "none": "Sin escalar"}

# Paso 4 (elegir k)
SWEEP_RANGE = "Rango de k"
SWEEP_RANGE_VALUE = "de {lo} a {hi}"
SWEEP_NINIT = "Inicializaciones"
SWEEP_SEED = "Semilla"
SWEEP_BOOT = "IC bootstrap de la silueta por k"
SWEEP_BOOT_B = "Remuestras por k"
SWEEP_RUN = "Calcular barrido de k"
SWEEP_SUMMARY = "k de {lo} a {hi} · {ninit} inicializaciones · semilla {seed}"
SWEEP_SUMMARY_BOOT = "IC bootstrap: {b} remuestras por k"
SWEEP_SUMMARY_K = "k elegido: {k}"
VAL_N_VS_KMAX = "Hay {n} filas analizadas: necesitas más que el k máximo ({k}). Reduce el rango de k."
VAL_NEED_PREP = "Completa antes el preprocesado."
HELP_RANGE = (
    "Cuántos grupos (clusters) se comparan. Se ajusta un modelo para cada k del rango y se comparan "
    "con varios índices. El máximo es 8."
)
SWEEP_COV = "Forma de los clusters (covarianza)"
HELP_COV = (
    "Completa: cada cluster puede tener su propio tamaño, forma y orientación (lo más flexible). "
    "Compartida: todos con la misma forma. Diagonal: sin correlaciones entre variables dentro del "
    "cluster. Esférica: redondos, como k-means. El gráfico de BIC compara las cuatro."
)
SWEEP_LINK = "Tipo de enlace"
HELP_LINK = (
    "Cómo se mide la distancia entre dos grupos al unirlos. Ward: une los grupos que menos aumentan "
    "la variabilidad interna (grupos compactos, el más usado). Promedio: distancia media entre sus "
    "pacientes. Completo: la mayor distancia entre sus pacientes."
)
HELP_NINIT = (
    "k-means empieza desde puntos al azar; se repite este número de veces y se queda con la mejor "
    "solución. 20 es suficiente casi siempre."
)
HELP_SEED = "Fija el azar para que el resultado sea idéntico cada vez que se repite el análisis."
HELP_BOOT = (
    "Repite el ajuste en remuestras de los pacientes para ver cuánto varía la silueta de cada k. "
    "Barras de error estrechas indican una estructura estable. Tarda más."
)

# Panel de resultados del barrido
BEST_K_TITLE = "Mejor k según cada índice"
BEST_K_SIL = "Silueta: k = {k}"
BEST_K_CH = "Calinski-Harabasz: k = {k}"
BEST_K_DB = "Davies-Bouldin: k = {k}"
BEST_K_ELBOW = "Codo ≈ {k}"
BEST_K_BIC = "BIC: k = {k}"
BEST_K_HEIGHT = "Mayor salto del árbol: k = {k}"
CHART_BIC = "BIC por k (menor es mejor)"
CHART_DENDRO = "Dendrograma (clic para cortar)"
AXIS_BIC = "BIC"
AXIS_HEIGHT = "Altura de fusión"
TIP_BIC = "k = {k} · BIC {v}"
CUT_LABEL = "corte: k = {k}"
COV_SHORT = {"full": "Completa", "tied": "Compartida", "diag": "Diagonal", "spherical": "Esférica"}
CRITERION_HEAD = {"inercia": "Inercia", "bic": "BIC", "altura": "Altura de fusión"}
BIC_BEST_COV = "Menor BIC de todos los tipos: covarianza {cov}, k = {k}."
CHART_ELBOW = "Método del codo"
CHART_SIL = "Silueta media por k"
AXIS_K = "Número de clusters (k)"
AXIS_INERTIA = "Inercia (suma de cuadrados intra)"
AXIS_SIL = "Silueta media"
TIP_ELBOW = "k = {k}\nInercia = {v}\nClic para elegir este k"
TIP_SIL = "k = {k}\nSilueta = {v}{ic}\nClic para elegir este k"
TIP_IC = " (IC95 % {lo}–{hi})"
INDEX_TABLE_HEAD = ["k", "Inercia", "Silueta", "IC95 % silueta", "Calinski-Harabasz", "Davies-Bouldin",
                    "Tamaño mín."]
INDEX_TABLE_NOTE = "Silueta y Calinski-Harabasz: mayor es mejor. Davies-Bouldin: menor es mejor."
CONTINUE_FINAL_TITLE = "Continuar con el modelo final"
CONTINUE_FINAL_BODY = (
    "k elegido: {k}. Haz clic en un punto de cualquiera de los dos gráficos para cambiarlo."
)
CONTINUE_FINAL_BUTTON = "Ir al modelo final"
RESULTS_STALE = "Estos resultados están desactualizados: recalcula el paso en la barra lateral."

# Paso 5 (modelo final)
FINAL_K = "k elegido"
FINAL_B = "Remuestras bootstrap"
FINAL_RUN = "Ajustar y validar"
FINAL_K_HINT = "También puedes elegir k haciendo clic en un punto del codo o de la silueta."
FINAL_SUMMARY = "k = {k} · {b} remuestras bootstrap"
FINAL_SUMMARY_RESULT = "Silueta media {sil} · tamaños {sizes}"
HELP_FINAL_K = "Número de grupos del modelo final. Elígelo con los índices del paso anterior y el criterio clínico."
HELP_FINAL_B = (
    "Cuántas veces se repite el ajuste en remuestras de los pacientes para medir la estabilidad de cada "
    "cluster y el intervalo de confianza de la silueta. Más remuestras, más precisión y más tiempo."
)
VAL_NEED_SWEEP = "Calcula antes el barrido de k."
TIP_PCA = "{cluster} · fila {row}\nClic para seleccionarla en la tabla"
AXIS_OBS = "Observaciones (ordenadas dentro de cada cluster)"
AXIS_SIL_OBS = "Silueta"
AXIS_CLUSTER = "Cluster"
AXIS_JACCARD = "Jaccard medio (IC95 %)"
AXIS_FREQ = "Remuestras"

# Panel del modelo final
KPI_SIL = "Silueta media"
KPI_SIL_NOTE = "De −1 a 1; > 0,5 estructura razonable"
KPI_CI = "IC95 % bootstrap"
KPI_CI_NOTE = "{b} remuestras"
KPI_ARI = "ARI medio vs bootstrap"
KPI_ARI_NOTE = "Concordancia con cada remuestra"
KPI_UNSTABLE = "Clusters poco estables"
KPI_UNSTABLE_VALUE = "{n} de {k}"
KPI_UNSTABLE_NOTE = "Jaccard < 0,75 (Hennig, 2007)"
SIZES = "Tamaños"
SIZE_ITEM = " · {n} ({pct})"
TAB_SUMMARY = "Resumen"
TAB_SILHOUETTE = "Silueta"
TAB_STABILITY = "Estabilidad"
TAB_SENSITIVITY = "Sensibilidad a la imputación"
TAB_DESCRIPTIVE = "Variables descriptivas"
TAB_MEMBERSHIP = "Pertenencia"
MEMBERSHIP_TITLE = "Probabilidad de pertenencia al cluster asignado"
MEMBERSHIP_NOTE = (
    "{n} pacientes tienen una probabilidad menor que {u}: están en la frontera entre dos perfiles "
    "(media de todos: {m})."
)
MEMBERSHIP_SELECT = "Seleccionar los {n} de frontera en la tabla"
MEMBERSHIP_SELECT_1 = "Seleccionar el paciente de frontera en la tabla"
MEMBERSHIP_NOTE_1 = (
    "1 paciente tiene una probabilidad menor que {u}: está en la frontera entre dos perfiles (media de todos: {m})."
)
AXIS_PATIENTS = "Pacientes"
FINAL_K_HINTS = {
    "kmeans": "También puedes elegir k haciendo clic en un punto del codo o de la silueta.",
    "gmm": "También puedes elegir k haciendo clic en un punto del BIC o de la silueta.",
    "jerarquico": "También puedes elegir k haciendo clic en el dendrograma (a la altura del corte) o en la silueta.",
}
AXIS_PROB = "Probabilidad máxima"
PCA_TITLE = "Proyección en componentes principales"
PCA_HINT = "Clic en un punto o arrastra un lazo para seleccionar esas filas en la tabla."
HEATMAP_TITLE = "Perfiles de los clusters (medias en z)"
HEATMAP_HINT = "Clic en una fila para ver la media (DE) en unidades originales."
HEATMAP_DETAIL = "{cluster} (n = {n}): {values}"
SIL_TITLE = "Silueta de cada observación"
SIL_NOTE = "Línea discontinua: silueta media ({mean}). Siluetas negativas: {neg} de las observaciones."
JACCARD_TITLE = "Estabilidad por cluster (Jaccard bootstrap)"
HIST_TITLE = "Silueta media en las remuestras"
STABILITY_HEAD = ["Cluster", "n", "Jaccard medio", "IC95 %", "Se disuelve (%)", "Interpretación"]
STABILITY_NOTE = (
    "Jaccard ≥ 0,85 muy estable; ≥ 0,75 estable; ≥ 0,60 indica un patrón, pero dudoso; < 0,60 inestable. "
    "«Se disuelve»: % de remuestras en que el cluster no se recupera (Jaccard < 0,5)."
)
SENS_TITLE = "Concordancia (ARI) entre las particiones obtenidas con cada método de imputación"
SENS_N = "Filas analizadas: {items}"
SENS_WARN = (
    "Algún par de métodos da particiones bastante distintas (ARI < 0,8): los clusters dependen de cómo "
    "se tratan los valores perdidos. Interprétalos con cautela."
)
SENS_OK = "Todos los métodos dan particiones muy parecidas (ARI ≥ 0,8): los clusters no dependen de la imputación."
DESC_EMPTY = "No hay variables descriptivas. Márcalas en la tabla (tecla D) y vuelve a ajustar el modelo."
DESC_HEAD_VAR = "Variable"
DESC_HEAD_LEVEL = "Nivel"
DESC_NOTE = "Mediana [RIC] para numéricas y n (%) para categóricas. Sin p-valores: es una descripción."
NO_TESTS_NOTE = (
    "Las variables del modelo no se comparan con contrastes de hipótesis: los clusters difieren en ellas "
    "por construcción."
)
HIGHLIGHT = "Resaltar:"
HIGHLIGHT_ALL = "Todos"
COL_CLUSTER = "cluster"
COL_SILHOUETTE = "silueta"
ROLE_LABEL_RESULT = "RESULTADO"

# Sesiones
SESSION_FILTER = "Sesión de StatLab (*.statlab)"
SESSION_OPEN = "Abrir sesión…"
SESSION_SAVE = "Guardar sesión"
SESSION_SAVE_AS = "Guardar sesión como…"
SESSION_NOTHING = "No hay nada que guardar todavía: abre un archivo de datos."
SESSION_INVALID = "El archivo no es una sesión de StatLab válida o está dañado."
SESSION_NEWER = (
    "Esta sesión se guardó con una versión más reciente de StatLab ({version}). Actualiza la aplicación "
    "para abrirla."
)
SESSION_OTHER_MODULE = "Esta sesión es de otro tipo de análisis («{modulo}») que esta versión no incluye."
SESSION_SAVED = (
    "Sesión guardada en «{name}». El archivo contiene los datos de los pacientes: guárdalo en una ubicación segura."
)
SESSION_PRIVACY = (
    "El archivo de sesión contiene los datos de los pacientes. Guárdalo en una ubicación segura "
    "(no en carpetas compartidas ni en la nube sin cifrar)."
)
SESSION_OPEN_ERROR_TITLE = "No se ha podido abrir la sesión"
SESSION_SAVE_ERROR_TITLE = "No se ha podido guardar la sesión"
UNSAVED_TITLE = "Cambios sin guardar"
UNSAVED_TEXT = "Hay cambios en el análisis que no se han guardado. ¿Quieres guardar la sesión antes?"
UNSAVED_SAVE = "Guardar"
UNSAVED_DISCARD = "No guardar"
UNSAVED_CANCEL = "Cancelar"

# Informe
REPORT_TITLE = "Informe de clustering k-means"
REPORT_TITLES = {"kmeans": "Informe de clustering k-means", "gmm": "Informe de mezclas gaussianas (GMM)",
                 "jerarquico": "Informe de clustering jerárquico"}
REPORT_COVER = "Archivo de datos: {fuente} · {n} filas × {cols} columnas · {n_model} filas en el modelo"
REPORT_DATE = "Fecha: {fecha} · StatLab {version}"
REPORT_PRIVACY = (
    "Este informe no incluye los datos individuales de los pacientes, salvo en forma agregada "
    "(tablas por cluster y proyección PCA)."
)
REPORT_PARAMS = "Parámetros del análisis"
REPORT_PARAM_HEAD = ["Parámetro", "Valor"]
REPORT_SWEEP = "Barrido de k"
REPORT_FINAL = "Modelo final"
REPORT_FIGURES = "Figuras"
REPORT_TABLES = "Perfiles, variables descriptivas y estabilidad"
REPORT_PROFILES = "Perfiles: media (DE) en unidades originales"
REPORT_SENS = "Sensibilidad a la imputación"
REPORT_METHODS = "Texto de métodos"
REPORT_METHODS_NOTE = "Párrafo listo para adaptar en un manuscrito."
REPORT_VERSIONS = "Versiones del software"
REPORT_VERSIONS_HEAD = ["Componente", "Versión"]
REPORT_KPI_HEAD = ["Indicador", "Valor"]
P_MODEL_VARS = "Variables del modelo"
P_LOG = "Transformación log(1+x)"
P_DESCR = "Variables descriptivas"
P_ID = "Identificador"
P_ROWS = "Filas analizadas"
P_MISSING = "Valores perdidos"
P_SCALING = "Escalado"
P_RANGE = "Rango de k"
P_NINIT = "Inicializaciones de k-means"
P_SEED = "Semilla"
P_SWEEP_BOOT = "IC bootstrap de la silueta por k"
P_K = "k elegido"
P_FINAL_B = "Remuestras bootstrap del modelo final"
NONE = "ninguna"
NO = "no"
YES_B = "sí ({b} remuestras por k)"
MISSING_KNN_LONG = "KNN, {k} vecinos"
FIG_ELBOW = "Método del codo: inercia por número de clusters."
FIG_BIC = "Criterio de información bayesiano (BIC) por número de componentes; en gris, otros tipos de covarianza."
FIG_DENDRO = "Dendrograma (últimas fusiones); línea discontinua: corte en el número de grupos elegido."
FIG_MEMBERSHIP = "Probabilidad de pertenencia al cluster asignado; en ámbar, pacientes de frontera."
FIG_SIL_K = "Silueta media por k (barras: IC95 % bootstrap)."
FIG_PCA = "Proyección en las dos primeras componentes principales; rombos: centroides."
FIG_HEATMAP = "Perfiles de los clusters: medias estandarizadas (z) de cada variable del modelo."
FIG_SIL_OBS = "Silueta de cada observación, ordenada dentro de cada cluster; línea discontinua: media."
FIG_JACCARD = "Jaccard medio por cluster con IC95 % bootstrap; referencias en 0,75 y 0,60 (Hennig, 2007)."
FIG_HIST = "Distribución de la silueta media en las remuestras bootstrap; línea discontinua: modelo final."
FINAL_REQUIRED = "Ajusta antes el modelo final (paso 5) para poder exportar."

# Paso 6 (exportar)
EXPORT_CSV = "Tabla con cluster y silueta (CSV)"
EXPORT_JSON = "Parámetros y resultados (JSON)"
EXPORT_MD = "Texto de métodos (.md)"
EXPORT_FIGURES = "Figuras (PNG 300 ppp y SVG)…"
EXPORT_PDF = "Informe PDF…"
EXPORT_DOCX = "Informe Word (.docx)…"
EXPORT_ALL = "Todo en una carpeta…"
EXPORT_HINT = (
    "El CSV, el JSON y la carpeta completa contienen los datos de los pacientes: guárdalos en un lugar seguro."
)
EXPORT_FOLDER = "Elige una carpeta"
EXPORT_DONE = "Exportado: {names}"
EXPORT_DONE_MORE = "{first} y {n} archivo(s) más en «{folder}»"
EXPORT_LAST = "Último exporte: {names}"
EXPORT_FILTERS = {
    "csv": "CSV (*.csv)",
    "json": "JSON (*.json)",
    "md": "Markdown (*.md)",
    "pdf": "PDF (*.pdf)",
    "docx": "Word (*.docx)",
}
EXPORT_NAMES = {
    "csv": "{base}_datos_con_clusters.csv",
    "json": "{base}_resultados.json",
    "md": "{base}_metodos.md",
    "pdf": "{base}_informe.pdf",
    "docx": "{base}_informe.docx",
}
EXPORT_WRITE_ERROR = (
    "No se ha podido escribir en «{path}». Comprueba que la carpeta existe, que tienes permiso y que el "
    "archivo no está abierto en otro programa."
)

# Lectura robusta (Excel)
READ_HEADER_ROW = "La cabecera está en la fila {row}: se han ignorado las filas de encima."
READ_TWO_HEADERS = "La cabecera ocupa dos filas (celdas combinadas): se han unido los nombres."
READ_TRAILING = "Se han ignorado {n} filas al final (totales o notas)."
READ_TRAILING_1 = "Se ha ignorado 1 fila al final (totales o notas)."

# Fórmulas
FORMULA_EMPTY = "Escribe una fórmula."
FORMULA_CHAR = "Hay un carácter que no entiendo («{char}», posición {pos})."
FORMULA_EXPECTED = "Falta «{what}» (posición {pos})."
FORMULA_INCOMPLETE = "La fórmula está incompleta."
FORMULA_UNEXPECTED = "No esperaba «{tok}» en la posición {pos}."
FORMULA_UNKNOWN_FUNC = "No conozco la función «{name}»."
FORMULA_NARGS = "La función {name} no lleva ese número de argumentos (se separan con «;»)."
FORMULA_NO_COLUMN = "No hay ninguna columna «{col}». Si el nombre tiene espacios, escríbelo entre corchetes: [{col}]."
FORMULA_NOT_NUMBER = "Hay texto donde se esperaba un número. Revisa el tipo de las columnas de la fórmula."
FORMULA_NOT_DATE = "Las funciones AÑOS, MESES y DIAS necesitan columnas de tipo fecha."
FORMULA_DATE_ARITH = "Para restar fechas usa AÑOS(inicio; fin), MESES(…) o DIAS(…)."
FORMULA_TEXT_ORDER = "Los textos solo se pueden comparar con = o <>."

# Receta de preparación
PREP_TYPE_NAMES = {
    "numerica": "numérica", "categorica": "categórica", "ordinal": "ordinal", "fecha": "fecha", "texto": "texto libre",
}
PREP_DATE_FORMATS = {"dma": "día/mes/año", "mda": "mes/día/año", "amd": "año-mes-día"}
PREP_NO_COLUMN = "La columna «{col}» ya no existe (¿se ha renombrado o quitado en un paso anterior?)."
PREP_BAD_TYPE = "Tipo de columna desconocido: {tipo}."
PREP_BAD_STEP = "Paso desconocido: {tipo}."
PREP_STEP_FAILED = "No se ha podido aplicar este paso ({detail})."
PREP_UNREADABLE = "{n} valores no se han podido leer y quedan como perdidos."
PREP_CUT_LABELS = "Hacen falta {n} etiquetas, una por intervalo."
PREP_ALL = "Todos"
PREP_ALL_COLUMNS = "todas las columnas"
PREP_NO_NAME = "Escribe el nombre de la nueva columna."
PREP_NAME_TAKEN = "Ya hay una columna «{col}»."
PREP_NO_REASON = "Escribe el motivo de la exclusión: aparecerá en el diagrama de flujo de pacientes."
PREP_EXCLUDE_NA = "En {n} filas falta el dato de la condición: no se excluyen."
PREP_DUPLICATE_REASON = "Duplicado"
PREP_NEGATIVE_TIME = "{n} tiempos negativos: revisa el orden de las fechas."
PREP_NO_FOLLOWUP = "En {n} filas falta la fecha de inicio o la de final: tiempo perdido."
PREP_DESC_TYPE = "«{col}» como {tipo}"
PREP_DESC_MISSING = "Perdidos en {cols}: {que}"
PREP_DESC_RECODE = "Recodificar «{col}» ({n} valores)"
PREP_DESC_UNITS = "«{col}» × {factor}"
PREP_DESC_CUT = "Categorizar «{col}» → {dest}"
PREP_DESC_DATES = "{dest} = tiempo de {a} a {b}"
PREP_DESC_FOLLOWUP = "Seguimiento: {t} y {e}"
PREP_DESC_EXCLUDE = "Excluir: {motivo} ({cond})"
PREP_DESC_DUPS = "Excluir duplicados ({cols})"
PREP_DESC_DROP = "Quitar {cols}"
PREP_DESC_RENAME = "Renombrar «{col}» → «{nombre}»"

# Revisión de calidad
Q_DUP_ROWS = "Filas duplicadas"
Q_DUP_ROWS_DETAIL = "{n} filas son copia exacta de otra anterior."
Q_DUP_ID = "Identificador repetido en «{col}»"
Q_DUP_ID_DETAIL = "{n} filas comparten identificador pero tienen datos distintos: revísalas a mano."
Q_EMPTY = "«{col}» está vacía"
Q_EMPTY_DETAIL = "No tiene ningún valor."
Q_DATE = "«{col}» parece una fecha"
Q_DATE_DETAIL = "Formato detectado: {fmt}."
Q_DATE_AMBIGUOUS = "No se distingue si es día/mes o mes/día (ningún valor pasa de 12): confirma el formato."
Q_NUMTEXT = "«{col}» tiene números guardados como texto"
Q_NUMTEXT_DETAIL = "Al convertirla, {n} valores no se podrían leer."
Q_NUMTEXT_DETAIL_OK = "Todos los valores se pueden convertir a número."
Q_NUMTEXT_LIMITS = "{n} valores llevan «<» o «>» (límite de detección)."
Q_CATS = "«{col}»: la misma categoría escrita de varias formas"
Q_CATS_DETAIL = "Por ejemplo {ej} (mayúsculas, espacios o tildes)."
Q_MISSING_CODE = "«{col}»: ¿{code} significa «perdido»?"
Q_MISSING_CODE_DETAIL = "{n} filas valen {code}, muy lejos del resto de valores."
Q_LIMITS = "«{col}»: valores fuera de los límites del diccionario"
Q_LIMITS_DETAIL = "{n} valores fuera de los límites plausibles."
Q_UNITS = "«{col}»: parece haber unidades mezcladas"
Q_UNITS_DETAIL = "{n} valores son unas {factor} veces mayores que el resto (¿g/L en vez de g/dL?)."
Q_MOSTLY_EMPTY = "«{col}» está casi vacía"
Q_MOSTLY_EMPTY_DETAIL = "Le falta el {p} % de los valores."
Q_CONSTANT = "«{col}» casi no varía"
Q_CONSTANT_DETAIL = "El {p} % de los valores es «{v}»."

# Diccionario
DICT_INVALID = "No he podido leer el diccionario. Debe ser un CSV o Excel con una fila por variable."
DICT_NO_VARIABLE = "El diccionario necesita una columna «variable» con el nombre de cada columna de los datos."
DICT_BAD_NUMBER = "«{value}» no es un número válido como límite."

# Mis fórmulas
MYF_INVALID = "El archivo no es una biblioteca de «Mis fórmulas» de StatLab."
MYF_NEWER = "La biblioteca es de una versión más reciente de StatLab."
MYF_UNMAPPED = "Indica qué columna corresponde a: {cols}."
Q_DICT_MISSING = "«{col}»: códigos de perdido del diccionario"
Q_DICT_MISSING_DETAIL = "{n} filas tienen un código que el diccionario define como perdido ({codes})."

# Modo «Preparar datos»
MODE_PREPARE = "1 · Preparar datos"
MODE_ANALYZE = "2 · Analizar"
PREP_SIDEBAR_TITLE = "Preparar datos"
PREP_FILE = "Archivo"
PREP_FILE_SUMMARY = "{name} · {rows} × {cols}"
PREP_FILE_SHEET = "Hoja «{sheet}» · cabecera en la fila {row}"
PREP_ORIGINAL_SAFE = "El archivo original no se modifica."
PREP_ADJUST = "Ajustar"
PREP_ADJUST_HIDE = "Ocultar"
PREP_SHEET = "Hoja"
PREP_HEADER_ROW = "Cabecera en la fila"
PREP_TWO_HEADER_ROWS = "Cabecera de dos filas"
PREP_DROP_TRAILING = "Ignorar totales al final"
PREP_QUALITY = "Revisión de calidad"
PREP_QUALITY_OK = "✓ Sin problemas detectados"
PREP_QUALITY_SUMMARY = "{n} avisos"
PREP_QUALITY_SUMMARY_1 = "1 aviso"
PREP_QUALITY_GRAVES = "{n} importantes"
PREP_QUALITY_GRAVES_1 = "1 importante"
PREP_SHOW_ALL = "Mostrar {n} más"
PREP_FIX = "Corregir"
PREP_SHOW_ROWS = "Ver {n} filas"
PREP_IGNORE = "Ignorar"
PREP_RECIPE = "Receta"
PREP_RECIPE_EMPTY = "Aún no hay cambios. Cada corrección o paso nuevo se añade aquí."
PREP_RECIPE_ERRORS = "{n} con error"
PREP_STEP_ACTIONS = "Acciones del paso"
PREP_DISABLE = "Desactivar"
PREP_ENABLE = "Activar"
PREP_ADD_STEP = "Añadir paso"
MYF_MENU = "Desde Mis fórmulas…"
PREP_STEP_OFF = "Desactivado"
PREP_MOVE_UP = "Subir"
PREP_MOVE_DOWN = "Bajar"
PREP_EDIT = "Editar"
PREP_DELETE = "Borrar"
PREP_CONTINUE = "Continuar al análisis →"
PREP_ERROR_TITLE = "No se ha podido aplicar el cambio"
PREP_PREVIEW = "Vista previa"
PREP_PREVIEW_CELLS = "{n} celdas cambian"
PREP_PREVIEW_CELLS_1 = "1 celda cambia"
PREP_PREVIEW_ROWS = "{n} filas excluidas"
PREP_PREVIEW_ROWS_1 = "1 fila excluida"
PREP_PREVIEW_NEWCOLS = "columna nueva {cols}"
PREP_PREVIEW_NOTHING = "Este paso no cambia nada en los datos actuales."
PREP_BEFORE = "antes"
PREP_AFTER = "después"
PREP_ROW = "Fila"
PREP_STATUS = "Estado"
PREP_EXCLUDED = "Excluida"
PREP_ADD = "Añadir a la receta"
PREP_SAVE = "Guardar cambios"
PREP_STEP_TITLES = {
    "tipo": "Tipo de columna",
    "perdidos": "Valores perdidos",
    "recodificar": "Recodificar categorías",
    "unidades": "Convertir unidades",
    "categorizar": "Categorizar por cortes",
    "calcular": "Nueva variable (calculadora)",
    "fechas": "Tiempo entre dos fechas",
    "seguimiento": "Tiempo de seguimiento y evento",
    "excluir": "Excluir filas",
    "duplicados": "Excluir duplicados",
    "renombrar": "Renombrar columna",
    "quitar": "Quitar columnas",
}
PREP_STEP_INTROS = {
    "tipo": "Fija cómo se lee una columna: número (también «<0,5», «12,3 mg/dL»), categoría, ordinal, fecha o texto.",
    "perdidos": "Convierte en perdidos los códigos que no son datos (999, -9…) o los valores que cumplan "
                "una condición.",
    "recodificar": "Une o renombra categorías: escribe el valor nuevo de cada una. Deja la casilla vacía para "
                   "convertirla en perdido.",
    "unidades": "Multiplica una columna por un factor, en todas las filas o solo en las que cumplan una condición "
                "(p. ej. Hb en g/L → g/dL: factor 0,1 si hb > 40).",
    "categorizar": "Crea una variable por intervalos. «18,5; 25; 30» da: < 18,5 · 18,5–25 · 25–30 · ≥ 30.",
    "calcular": "Crea una variable con una fórmula, como en Excel: coma decimal y «;» entre argumentos. Los nombres "
                "con espacios van entre corchetes: [fecha nacimiento].",
    "fechas": "Diferencia entre dos columnas de fecha (por ejemplo, edad a partir de la fecha de nacimiento).",
    "seguimiento": "Tiempo = fecha del evento (o, si no lo hubo, del último contacto) − fecha de inicio. "
                   "Evento = 1 si hay fecha del evento; 0 si no (censurado).",
    "excluir": "Las filas que cumplan la condición no entran en el análisis. No se borran: aparecen tachadas y "
               "con su motivo en el diagrama de flujo de pacientes.",
    "duplicados": "Excluye las filas repetidas (se conserva la primera). Sin columnas elegidas, compara la "
                  "fila entera.",
    "renombrar": "Cambia el nombre de una columna en la tabla de análisis.",
    "quitar": "Quita columnas de la tabla de análisis (siguen en el archivo original).",
}
F_COLUMN = "Columna"
F_COLUMNS = "Columnas"
F_TYPE = "Tipo"
F_DATE_FORMAT = "Formato de fecha"
F_LIMITS = "Valores con «<» o «>»"
F_LIMITS_VALUE = "Usar el número (<0,5 → 0,5)"
F_LIMITS_NA = "Dejarlos como perdidos"
F_ORDER = "Orden de las categorías"
F_ORDER_HELP = "De menor a mayor, separadas por «;». Ejemplo: Leve; Moderada; Grave"
F_MISSING_VALUES = "Códigos de perdido"
F_MISSING_HELP = "Separados por «;». Ejemplo: 999; -9"
F_CONDITION_OPTIONAL = "Condición (opcional)"
F_CONDITION_HELP = "Ejemplo: hb > 25"
F_RECODE = "Valores"
F_RECODE_HELP = "Escribe el valor nuevo en la tercera columna."
F_RECODE_OLD = "Valor actual"
F_RECODE_N = "n"
F_RECODE_NEW = "Valor nuevo"
F_RECODE_NOTHING = "No has cambiado ningún valor."
F_TARGET = "Nombre de la nueva columna"
F_TARGET_OPTIONAL = "Guardar en otra columna (opcional)"
F_FACTOR = "Factor"
F_FACTOR_HELP = "Ejemplos: 0,1 (g/L → g/dL) · 88,4 (creatinina mg/dL → µmol/L)"
F_UNITS_CONDITION_HELP = "Solo en las filas que la cumplan. Ejemplo: hb > 40"
F_CUT_MODE = "Cómo cortar"
F_CUT_POINTS = "Por cortes que eliges"
F_CUT_QUANTILES = "Por cuantiles (grupos de igual tamaño)"
F_CUTS = "Cortes"
F_CUTS_HELP = "Separados por «;». Cada intervalo incluye su límite inferior: [25, 30)."
F_QUANTILES = "Número de grupos"
F_LABELS_OPTIONAL = "Etiquetas (opcional)"
F_FORMULA = "Fórmula"
F_FORMULA_HELP = (
    "Operaciones + − * / ^ · comparaciones = <> < > <= >= · SI(condición; sí; no) · Y(…) · O(…) · MIN · MAX · "
    "LN · EXP · RAIZ · REDONDEAR · ESNA · AÑOS(inicio; fin) · MESES · DIAS"
)
F_SAVE_MYF = "Guardar también en «Mis fórmulas»"
F_INSERT_COLUMN = "Insertar columna…"
F_INSERT_FUNCTION = "Insertar función…"
F_DATE_START = "Fecha inicial"
F_DATE_END = "Fecha final"
F_UNIT = "Unidad"
F_NO_DATE_COLUMNS = "No hay columnas de fecha: fija antes el tipo «fecha»"
F_FU_START = "Fecha de inicio (inclusión)"
F_FU_EVENT = "Fecha del evento"
F_FU_LAST = "Fecha del último contacto"
F_FU_TIME_NAME = "Nombre de la columna de tiempo"
F_FU_EVENT_NAME = "Nombre de la columna de evento"
F_EXCLUDE_IF = "Excluir si"
F_EXCLUDE_HELP = "Ejemplos: edad < 18 · ESNA(hb) · Y(sexo = \"M\"; embarazo = \"Sí\")"
F_REASON = "Motivo"
F_REASON_HELP = "Aparece en el diagrama de flujo de pacientes. Ejemplo: Menores de 18 años"
F_DUP_COLUMNS = "Comparar por"
F_DUP_HELP = "Por ejemplo, el identificador. Sin ninguna elegida, compara la fila entera."
F_NEW_NAME = "Nombre nuevo"
F_REQUIRED = "Falta «{field}»."
F_BAD_NUMBER = "«{field}» debe ser un número."
F_BAD_NUMBERS = "Los cortes deben ser números separados por «;»."
F_MISSING_NOTHING = "Indica los códigos de perdido o una condición."
UNIT_YEARS = "años"
UNIT_MONTHS = "meses"
UNIT_DAYS = "días"

# Diagrama de flujo de pacientes
FLOW_TITLE = "Diagrama de flujo de pacientes"
FLOW_NOTE = "Se actualiza con las exclusiones de la receta y las que hagas en la tabla. Se incluye en el informe."
FLOW_TOTAL = "Registros en el archivo\nn = {n}"
FLOW_FINAL = "Analizados\nn = {n}"
FLOW_EXCLUDED = "{motivo}\nn = {n}"
FLOW_MANUAL = "Excluidos a mano en la tabla"
FLOW_OUTSIDE_SELECTION = "Fuera de «Analizar solo estas filas»"
FLOW_EXPORT = "Exportar figura…"
FLOW_FILTER = "Imagen PNG (*.png);;Imagen SVG (*.svg)"
REPORT_FLOW = "Pacientes"
REPORT_FLOW_CAPTION = "Diagrama de flujo de pacientes."
REPORT_PREP = "Preparación de los datos"
REPORT_PREP_HEAD = ("Paso", "Descripción")

# Diccionario (interfaz)
DICT_TITLE = "Diccionario de variables"
DICT_EDIT = "Editar diccionario…"
DICT_SUMMARY = "{n} de {total} variables descritas"
DICT_INTRO = (
    "Etiqueta y unidad se usan en tablas e informes. Los límites plausibles y los códigos de perdido "
    "alimentan la revisión de calidad. Categorías: 1=Hombre|2=Mujer. Varios códigos: 999|-9."
)
DICT_COLS = {
    "variable": "Variable", "etiqueta": "Etiqueta", "unidad": "Unidad", "descripcion": "Descripción",
    "minimo": "Mínimo", "maximo": "Máximo", "perdidos": "Códigos de perdido", "categorias": "Categorías",
}
DICT_IMPORT = "Importar…"
DICT_EXPORT = "Exportar…"
DICT_FILTER = "Excel (*.xlsx);;CSV (*.csv)"
DICT_IMPORT_UNKNOWN = "{n} variables del archivo no están en la tabla y no se han importado."

# Mis fórmulas (interfaz)
MYF_TITLE = "Mis fórmulas"
MYF_EMPTY = (
    "Aún no hay fórmulas guardadas. Al crear una variable con la calculadora, marca «Guardar también en "
    "Mis fórmulas» para reutilizarla en otros archivos."
)
MYF_INPUT = "Entrada «{name}»"
MYF_APPLY = "Añadir a la receta"
MYF_DELETE = "Borrar"
MYF_IMPORT = "Importar…"
MYF_EXPORT = "Exportar…"
MYF_FILTER = "Mis fórmulas de StatLab (*.json)"
MYF_IMPORTED = "{n} fórmulas nuevas y {m} sustituidas."
ROW_EXCLUDED_BY_RECIPE = "Excluida por la receta: {motivo}"
READ_OTHER_SHEET = "Los datos se han leído de la hoja «{sheet}» (las anteriores no tienen una tabla)."

Q_SHORT = {
    "duplicados": "Filas duplicadas",
    "id_duplicado": "identificador repetido",
    "vacia": "columna vacía",
    "fecha_texto": "fecha como texto",
    "numero_texto": "números como texto",
    "categorias": "valores escritos distinto",
    "codigo_perdido": "¿código de perdido?",
    "fuera_limites": "valores fuera de límites",
    "unidades": "unidades mezcladas",
    "casi_vacia": "casi vacía",
    "casi_constante": "casi no varía",
}
