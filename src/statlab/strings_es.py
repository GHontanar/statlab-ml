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
