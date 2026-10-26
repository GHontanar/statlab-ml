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
