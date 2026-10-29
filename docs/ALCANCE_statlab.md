# StatLab · alcance después de la v0.1.0

> **Estado: propuesta.** Define hasta dónde puede llegar StatLab y en qué orden. Las decisiones
> marcadas con **⚠ Decide Guzmán** reabren una decisión cerrada del documento de traspaso
> (`HANDOFF_statlab-desktop.md`) o añaden una dependencia pesada: no se implementan sin su visto bueno.

## 1. Visión

StatLab pasa de ser «una app de k-means» a ser **un entorno de análisis clínico de escritorio,
sin código y sin conexión**, con tres módulos sobre una base común:

| Pregunta del clínico | Módulo | Contenido |
|---|---|---|
| ¿Cómo son mis pacientes y en qué difieren? | **Estadística clásica** | Tabla 1, contrastes, regresión inferencial, supervivencia |
| ¿Hay grupos que no conozco? | **ML no supervisado** | k-means, jerárquico, GMM, k-medoids… |
| ¿Puedo predecir un desenlace? | **ML supervisado** | Regresión logística penalizada, Random Forest, gradient boosting |

Alrededor de los tres módulos hay **herramientas transversales** que sirven a todos, con la
**preparación de datos** a la cabeza (§8), y otros **módulos de análisis** posteriores (§9).

La aplicación se organiza **por la pregunta, no por la técnica**. Una misma técnica puede aparecer
en dos módulos con otro objetivo. Por ejemplo, la regresión logística:

- en **estadística clásica** responde «¿este factor se asocia al desenlace?» y se informa con OR, IC y p;
- en **supervisado** es el modelo de referencia frente a RF y XGBoost, y se informa con AUC y calibración.

El cálculo se comparte y cambia lo que se informa.

Referencia de nivel: algo como **jamovi o JASP orientado a ML clínico**.

## 2. Principios (se mantienen de la v1)

- **Usuarios clínicos no técnicos:** pasos guiados, ayudas contextuales y mensajes humanos.
  Cada algoritmo trae **todo lo que lo acompaña**:
  - optimización y selección de parámetros;
  - validación y estabilidad;
  - datos faltantes;
  - perfiles e interpretación;
  - figuras, informe y texto de métodos.
- **Cero red:** los datos nunca salen del equipo.
- **Una sesión, un archivo** (`.statlab`): se puede abrir tal cual en otro equipo.
- **Buenas prácticas por defecto:** la interfaz evita los errores frecuentes en lugar de
  limitarse a explicarlos. Por ejemplo, impide la fuga de información entre entrenamiento y
  prueba y avisa cuando hay pocos eventos por variable.
- **Español**, con textos centralizados.

## 3. Techo del producto (lo que StatLab no será)

- **Solo datos tabulares:** nada de imágenes, texto libre, señales ni deep learning. Sin GPU.
- **Tamaño de datos:** hasta decenas de miles de filas. El límite de 5.000 filas de la v1 se
  revisará por algoritmo cuando se mida el rendimiento (⚠ Decide Guzmán).
- **Herramienta de investigación, no de decisión clínica.** Aplicar un modelo entrenado a un
  paciente nuevo para decidir su manejo convertiría StatLab en *software* sanitario regulado (MDR
  europeo). Propuesta: la app puede aplicar un modelo a un **conjunto de validación externo**,
  siempre con la etiqueta «uso en investigación» (⚠ Decide Guzmán).
- **Sin LLM ni lenguaje natural.** Se mantiene la decisión cerrada.

## 4. Base común (cambios necesarios en el núcleo)

Hoy la base sirve a un único módulo con un único análisis por sesión. Para el nuevo alcance necesita:

| Pieza | Hoy | Necesita |
|---|---|---|
| Roles de variable | Modelo, descriptiva, identificador, log | + **desenlace**, **tiempo** y **evento** (supervivencia), **agrupación** (comparar grupos) |
| Categóricas en el modelo | No (cerrado en v1) | Codificación *one-hot* y distancia de Gower (⚠ Decide Guzmán) |
| Preprocesado | Dentro del módulo k-means | **Pipeline reutilizable**: imputación, escalado, transformaciones, codificación. En supervisado se ajusta **dentro de cada partición** de validación |
| Sesión | Un análisis | **Varios análisis y «soluciones»** sobre el mismo dataset. Formato `.statlab` v2, con migración de las sesiones v1 |
| Pantalla inicial | «Abrir datos» | Más «¿Qué quieres hacer?», con las tres preguntas de la §1 |
| Informe | Un análisis | Secciones componibles: un informe puede reunir Tabla 1, clusters y comparación |
| Subgrupos de filas | Se guardan pero no se reutilizan | Analizar o comparar un subgrupo |
| Datos de la sesión | La tabla tal como se leyó | **Datos originales intactos + receta de preparación** (§8.1) que produce la tabla de análisis |

El contrato `AnalysisModule` (pasos, ejecución en segundo plano, paneles y exportes) se mantiene.
Cada algoritmo o análisis nuevo es un módulo que se enchufa a él.

## 5. Módulo ML no supervisado

### 5.1 Algoritmos

| Algoritmo | Selección de parámetros | Específico | Fase |
|---|---|---|---|
| **k-means** (hecho) | Silueta, Calinski-Harabasz, Davies-Bouldin, codo | Bootstrap de Jaccard | v0.1 |
| **Jerárquico aglomerativo** | Enlace (Ward, promedio, completo), punto de corte | Dendrograma interactivo; al cortarlo se actualizan los clusters | F2 |
| **GMM (mezclas gaussianas)** | BIC/AIC por k y tipo de covarianza | Probabilidad de pertenencia por paciente; pacientes de frontera | F2 |
| **k-medoids (PAM) con Gower** | Silueta | Variables categóricas en el modelo | F3 |
| HDBSCAN | Tamaño mínimo de cluster | Pacientes «ruido» | Más adelante |
| Análisis de clases latentes | BIC, entropía | Indicadores categóricos; dependencia nueva | Más adelante |
| UMAP para visualizar | — | Dependencia pesada (numba) | Más adelante (⚠ Decide Guzmán) |

Todos comparten:
- pasos de preprocesado, elección de parámetros, modelo final y exportar;
- estabilidad por bootstrap (Jaccard por cluster);
- perfiles y mapa de calor;
- PCA enlazado con la tabla;
- sensibilidad (§5.3);
- descriptivas por cluster;
- informe y métodos.

### 5.2 Comparación de soluciones (ARI)

Cada modelo final se guarda como una **solución** con nombre, por ejemplo «k-means · k=4» o
«GMM · k=4 · completa». Las soluciones aparecen en una lista de la barra lateral. Con dos o más se
activa **«Comparar soluciones»**, una herramienta de la sesión, no de un algoritmo.

- **Con tres o más soluciones:** una matriz de ARI entre todas. Al pulsar una casilla se abre la
  comparación de esa pareja.
- **Cifras clave:**
  - ARI con IC y etiqueta en lenguaje llano (umbrales de Steinley, 2004);
  - % de pacientes en el mismo grupo, emparejando clusters con el algoritmo húngaro (solo si A y B tienen el mismo k);
  - número de pacientes que cambian de grupo, con un botón que los selecciona en la tabla.
- **Pestañas:**
  - **Flujo (Sankey):** clic en una banda para seleccionar esos pacientes. Es la vista principal si A y B tienen distinto k.
  - **Tabla cruzada:** reordenada para que la diagonal muestre la concordancia.
  - **PCA:** discordantes resaltados.
  - **Perfiles enfrentados.**
  - **Discordantes:** incluye la probabilidad de pertenencia de GMM, que suele mostrar que los discordantes son pacientes de frontera.
- **Tabla de datos:** columnas `cluster_A`, `cluster_B` y `concordante`.
- **Avisos, no errores:**
  - si los pacientes difieren, se compara en la intersección;
  - si las variables difieren, se indica de forma visible;
  - un ARI ≤ 0 se presenta como «no mejor que el azar».
- **Dos IC, con nombres distintos:**
  - del acuerdo: bootstrap de pacientes con sus etiquetas, rápido y por defecto;
  - de estabilidad: reajustando ambos algoritmos, opcional.

**Dentro de una sesión**, cada análisis se muestra en su propia **pestaña**. Todas comparten los
datos y la receta, y la comparación elige A y B entre ellas.

#### Comparar con análisis de otras sesiones o de fuera de StatLab

Para el ARI, una solución es una lista **paciente → cluster**. Comparar análisis distintos
exige emparejar a los pacientes:

- **Columna identificador (rol I):** emparejamiento por ID. Es la vía normal. Con IDs duplicados
  no se compara y se avisa.
- **Sin ID pero con el mismo archivo** (misma huella, *hash*): emparejamiento por orden de fila.
- **Sin ID y con archivos distintos:** no se puede comparar, y se explica por qué.
- **Pacientes que no coinciden del todo:** se compara en la intersección, con el aviso de §5.2.
  Si la intersección es pequeña, el aviso es más fuerte.

**Importar solución** (F3). En «Comparar soluciones», el botón «Importar solución…» acepta:

- **otra sesión `.statlab`**, eligiendo una de sus soluciones;
- **un CSV con `id;cluster`**, para comparar con un análisis hecho fuera de StatLab (R, SPSS, un
  compañero) o con una clasificación clínica ya existente.

La solución importada es una **copia congelada**: solo las etiquetas y su procedencia («importada
de *cohorte_2025.statlab*, 29/10/2026»). No se actualiza si el original cambia, y el informe
indica su procedencia.

**Pestañas de sesiones** (más adelante). Varias sesiones abiertas a la vez, cada una en su pestaña
(como en un navegador); comparar con otra pestaña sería importar su solución sin pasar por un
archivo. Sirve para más que el ARI (trabajar en dos estudios, copiar una receta), pero cuesta más:

- cálculo en segundo plano por pestaña;
- aviso de cambios sin guardar por pestaña;
- memoria;
- qué hacer al cerrar una pestaña de la que depende una comparación (la comparación conserva una
  copia congelada, como al importar).

### 5.3 Análisis de sensibilidad

La solución elegida es la **base**: se fija y nunca se sustituye sola. El programa repite el
análisis **cambiando una decisión cada vez** y mide el acuerdo con la base usando el motor de §5.2.

- **Escenarios predefinidos (casillas):**
  - valores perdidos: mediana o solo casos completos;
  - escalado robusto;
  - quitar cada variable, una a una;
  - sin transformación log;
  - excluir valores atípicos (> 3 DE);
  - otras semillas;
  - submuestras del 80 %;
  - otro algoritmo con el mismo k.

  Antes de calcular se muestran el número de escenarios y el tiempo estimado. El k se mantiene fijo.
- **Cifras clave:** escenarios con acuerdo alto, ARI mínimo y su causa, y % de pacientes robustos
  (los que mantienen su grupo en al menos el 90 % de los escenarios).
- **Pestañas:**
  - **Resumen por decisión:** barras de ARI frente a la base; al pulsar una se abre la comparación A ⇄ B.
  - **Importancia de las variables:** el resultado de quitar cada una.
  - **Robustez por paciente:** histograma y PCA con degradado; columna `robustez_%` en la tabla.
  - **Estabilidad de los perfiles.**
- **Se reporta, no se elige:** un escenario puede guardarse como solución nueva, pero la base no
  cambia y el informe incluye todos los escenarios.
- **Semillas y submuestras** se muestran aparte, como referencia de cuánto varía la solución por
  azar, sin decisiones del analista.
- **Informe:** tabla de escenarios, gráfico resumen, texto automático de conclusiones y texto de métodos.
- La sensibilidad a la imputación que ya existe queda integrada aquí.

## 6. Módulo ML supervisado

### 6.1 Alcance inicial: clasificación binaria

| Modelo | Papel |
|---|---|
| **Regresión logística penalizada** (L1/L2/elastic net) | Referencia obligatoria: todo modelo complejo se compara con ella |
| **Random Forest** | Primer modelo no lineal |
| **Gradient boosting** | XGBoost (⚠ Decide Guzmán: dependencia pesada) o `HistGradientBoosting` de scikit-learn (sin dependencia nueva) |

### 6.2 Lo que acompaña a cada modelo

- **Validación:** partición en entrenamiento y prueba, o validación cruzada anidada. El preprocesado
  y la imputación se ajustan dentro de cada partición.
- **Optimización:** hiperparámetros con búsqueda en rejilla o aleatoria y rangos por defecto razonables.
- **Desbalance de clases:** pesos o umbral; nada de sobremuestreo sintético por defecto.
- **Métricas:**
  - AUC-ROC y AUC-PR con IC;
  - sensibilidad, especificidad, VPP y VPN en el umbral elegido;
  - Brier;
  - **curva de calibración**;
  - **análisis de curva de decisión**.
- **Interpretabilidad:**
  - importancia por permutación;
  - dependencia parcial;
  - SHAP (⚠ Decide Guzmán: dependencia).
- **Avisos:** eventos por variable, sobreajuste (métrica de entrenamiento mucho mejor que la de
  prueba), variables casi constantes o con casi todos los valores perdidos.
- **Comparación de modelos:** tabla y curvas ROC y de calibración superpuestas.
- **Sensibilidad:** el mismo panel que §5.3, midiendo el cambio de AUC y calibración en lugar del ARI.
- **Informe:** texto de métodos y lista de comprobación alineados con **TRIPOD+AI**.

### 6.3 Más adelante

Regresión (desenlace continuo), multiclase, supervivencia con ML (Random Survival Forest, que
reutiliza la base de §7.4) y validación externa en un segundo archivo.

## 7. Módulo Estadística clásica

| Bloque | Contenido |
|---|---|
| **7.1 Descriptiva** | **Tabla 1** por grupos (media/DE o mediana/RIC según la distribución, n y %, valores perdidos); exportable a Word con formato de revista |
| **7.2 Contrastes** | t de Student y de Welch, Mann-Whitney, ANOVA y Kruskal-Wallis (con post hoc), χ² y Fisher, pruebas pareadas (t pareada, Wilcoxon, McNemar), correlaciones (Pearson, Spearman), corrección por comparaciones múltiples. Elección guiada de la prueba según el tipo de variable y la distribución |
| **7.3 Regresión inferencial** | Lineal, logística y Poisson; OR, β o IRR con IC; diagnóstico de supuestos; colinealidad |
| **7.4 Supervivencia** | Kaplan-Meier con tabla de pacientes en riesgo, **log-rank**, **Cox** con HR e IC y **comprobación de riesgos proporcionales** (residuos de Schoenfeld). Más adelante, riesgos competitivos |
| **7.5 Más adelante** | Curvas ROC de pruebas diagnósticas, concordancia (kappa, CCI, Bland-Altman), cálculo de tamaño muestral |

**Supervivencia** se coloca en estadística clásica aunque esté a caballo entre módulos. El ML la
reutilizará con los mismos roles de tiempo y evento y la misma curva de Kaplan-Meier.

## 8. Herramientas transversales

### 8.1 Preparación de datos (prioritaria)

Un clínico pasa más tiempo limpiando el Excel que analizándolo. Hoy StatLab da por hecho que los
datos llegan limpios. La preparación es un **modo propio**, con su barra lateral de pasos, al que
se entra al abrir un archivo y al que se puede volver en cualquier momento.

**Principios:**

- **El archivo original nunca se modifica.** Cada cambio es un paso de una **receta** que se guarda
  en la sesión y se puede editar, desactivar, reordenar o borrar. La tabla de análisis es el
  resultado de aplicar la receta a los datos originales. La receta permite además las plantillas
  (§8.6) y exportar el análisis como script (§8.4).
- **Nada se corrige en silencio.** El programa detecta y propone; el usuario acepta, con una
  **vista previa** del antes y el después y el número de celdas afectadas.
- **Deshacer siempre.** Cambiar un paso de la receta marca como desactualizados los análisis que
  dependen de él, con la misma invalidación en cascada que ya tienen los pasos.

**Pasos:**

1. **Importación robusta**
   - elegir la hoja de un Excel;
   - cabecera que no está en la primera fila;
   - filas de totales o notas al final;
   - celdas combinadas;
   - varias cabeceras apiladas.

   Lo detecta el programa y se confirma en una vista previa.
2. **Revisión automática de calidad:** una lista de problemas, cada uno con su botón «Revisar».
   - **Duplicados**, de filas completas o de ID.
   - **Valores imposibles o improbables:** fuera de los límites que el usuario pone en el
     diccionario (§8.2).
   - **Unidades mezcladas:** por ejemplo, Hb en g/dL y g/L en la misma columna, detectada por una distribución bimodal con razón ×10. Se propone convertir, nunca se convierte sin confirmar.
   - **Categorías incoherentes:** «M», «Hombre», «varón », mayúsculas, espacios, tildes.
   - **Números guardados como texto:** «<0,5», «>200», «12,3 mg».
   - **Variables casi constantes o casi vacías.**
   - **Fechas ambiguas:** 03/04 puede ser dd/mm o mm/dd. Se decide por los valores mayores de 12 y, si no basta, se pregunta.
3. **Tipos y diccionario:** el tipo de cada columna (numérica, categórica, ordinal, fecha, ID, texto
   libre que no se analiza) y su entrada en el diccionario (§8.2).
4. **Recodificar:**
   - unir categorías arrastrándolas a un grupo;
   - ordenar categorías ordinales;
   - categorizar una numérica por cortes que define el usuario o por cuantiles (los cortes se
     pueden guardar en «Mis fórmulas»);
   - invertir ítems.
5. **Nuevas variables: los cálculos los define el usuario.** StatLab **no trae fórmulas clínicas**
   (ni IMC, ni filtrado glomerular, ni escalas); reconocer las variables de entrada de cada fórmula
   y asignarlas bien sería complicado e innecesario para el objetivo de la app.
   - **Calculadora visual**, sin escribir código: operaciones, condiciones (`SI`), `MIN`, `MAX`,
     `LN`, `EXP` y funciones de fecha. Lenguaje limitado: **nunca se ejecuta código**.
   - **Operaciones de fecha guiadas**, porque son genéricas y no fórmulas clínicas: diferencia
     entre fechas (edad a partir de la fecha de nacimiento) y **tiempo de seguimiento y evento a
     partir de fechas** (inclusión, evento, último contacto, censura).
   - Cada cálculo es un **paso de la receta**: se repite solo al reabrir la sesión o al reaplicar
     la receta a datos nuevos.
   - **«Mis fórmulas»:** cualquier cálculo se guarda en una biblioteca personal del equipo
     (fuera de la sesión) y se reutiliza en otros archivos. Al aplicarlo, el usuario indica una vez
     qué columna es cada entrada; nada se asigna automáticamente. La biblioteca se puede exportar
     e importar como archivo para compartirla con el equipo de investigación.
   - La fórmula es responsabilidad de quien la escribe; el texto de métodos la muestra tal cual.
6. **Unir archivos por ID**
   - con un informe de emparejamiento: cuántos casan, cuántos están solo en un archivo, IDs duplicados;
   - pasar de **formato largo a ancho** y viceversa, para medidas repetidas.
7. **Exclusiones con motivo:** cada filtro lleva un motivo («< 18 años», «sin analítica basal») y
   alimenta el **diagrama de flujo de pacientes** (§8.4).

### 8.2 Diccionario de variables y catálogo de referencia

**Diccionario del proyecto** (describe las columnas de este archivo): para cada variable, etiqueta,
unidad, descripción, límites plausibles, codificación de las categorías y valores que significan
«perdido» (p. ej. 999).

- Se define una vez y lo usan **todas las tablas, figuras e informes**: el informe dice
  «Hemoglobina (g/dL)», no `hb_gdl`.
- Se puede **importar y exportar** como CSV o Excel y reutilizar entre proyectos.

**Catálogo de referencia de variables** (lo que StatLab «sabe» de las variables clínicas
habituales). **Decidido: se deja para más adelante**, después de F8. Sin él, la revisión de calidad funciona igual con los límites que
el usuario ponga en el diccionario; el catálogo solo ahorra escribirlos.

- **Sugiere, nunca aplica solo:** «la columna `hb_gdl` parece Hemoglobina en g/dL; límites
  plausibles 3–25». Al aceptar, rellena el diccionario: nombre estándar, unidad y límites.
- Con eso se activan la detección de **valores fuera de límites** y de **unidades mezcladas**,
  con propuesta de conversión.
- Para cada variable: nombre estándar, sinónimos (hb, hgb, hemoglobina), unidad canónica,
  unidades alternativas con su factor de conversión y límites plausibles.
- **Núcleo pequeño hecho a mano:** unas 100 variables de analítica básica, constantes vitales y
  antropometría. Límites amplios y conservadores, revisados por un clínico.
- **Configurable:** el usuario corrige límites o añade variables en su catálogo personal (igual
  que «Mis fórmulas»), exportable para compartirlo.
- **Fuentes estándar** (⚠ Decide Guzmán, tras revisar licencias):
  - **NPU** (IFCC/IUPAC), terminología europea de laboratorio, descarga gratuita, ~16.000
    entradas: nombres y unidades. No trae límites plausibles; versión en español por confirmar.
  - **LOINC**: nombres, sinónimos y unidades, con traducción al español; licencia gratuita con
    atribución.
  - **UCUM**: conversiones entre unidades de la misma dimensión (g/dL ↔ g/L). Las conversiones
    masa ↔ molar dependen del peso molecular y se definen a mano.
  - **Ningún estándar da límites plausibles.** La base de datos de variación biológica de la EFLM
    no sirve para esto: da variación intra e interindividual, no nombres, unidades ni límites.

### 8.3 Datos faltantes a fondo

- **Exploración:** mapa de patrones de valores perdidos y comparación de pacientes con y sin datos
  para orientar si la pérdida es aleatoria.
- **Imputación múltiple (MICE):** combinación de resultados con las reglas de Rubin en los análisis
  de estadística clásica y opción de usarla en los de ML.
- Sustituye y amplía el KNN de la v1, que se mantiene como opción sencilla.

### 8.4 Reproducibilidad y trazabilidad

- **Diagrama de flujo de pacientes** (tipo STROBE), generado a partir de las exclusiones con motivo
  (§8.1, paso 7). Editable en textos y exportable al informe.
- **Registro** de cada paso, con fecha, versión de StatLab y huella (hash) del archivo de datos.
- **Exportar el análisis como script** (R o Python: ⚠ Decide Guzmán) que reproduce la receta y el
  análisis, para revisores y coautores.

### 8.5 Anonimización antes de compartir

- Seudonimizar IDs, con la tabla de correspondencia guardada aparte.
- Quitar identificadores directos.
- Desplazar fechas de forma coherente por paciente.
- Generalizar edad y códigos postales.
- **Aviso de combinaciones raras** que permitan reidentificar (comprobación de *k*-anonimato).
- Exporta una copia anonimizada; los datos originales no se tocan.

### 8.6 Plantillas de análisis

Guardar la receta y la configuración del análisis **sin los datos** y aplicarlas a un archivo nuevo
con las mismas columnas, por ejemplo la actualización anual de un registro. Si faltan o cambian
columnas, el programa lo dice antes de aplicar.

## 9. Otros módulos de análisis (después de los tres principales)

| Módulo | Contenido | Comentario |
|---|---|---|
| **Pruebas diagnósticas y escalas de riesgo** | ROC, comparación de AUC (DeLong), sensibilidad y especificidad con IC, **convertir una regresión en una escala de puntos**, nomogramas | Puente entre estadística clásica y supervisado: reutiliza casi todo |
| **Datos longitudinales** | Medidas repetidas: modelos mixtos, GEE, **trayectorias** (modelos de clases latentes de crecimiento) | Las trayectorias conectan con el no supervisado. Necesita el formato largo de §8.1 |
| **Inferencia causal observacional** | *Propensity score* (emparejamiento, IPTW), equilibrio entre grupos (diferencias estandarizadas, *love plot*), E-value | Muy demandado. Delicado para no técnicos: tendría que ser muy guiado |
| **Cuestionarios y escalas** | Análisis factorial exploratorio y confirmatorio, alfa de Cronbach, omega, validación de escalas | Habitual en enfermería y calidad de vida |
| **Diseño del estudio** | Tamaño muestral y potencia, listas de aleatorización | Se usa antes de tener datos: otra puerta de entrada a la app |
| **Concordancia** | Kappa, CCI, Bland-Altman | Pequeño (ya citado en §7.5) |
| Meta-análisis | Forest plot, heterogeneidad | Datos de estudios, no de pacientes: encaja peor. Solo si hay demanda |

## 10. Distribución en el hospital (bloqueante)

En la prueba de la v0.1.0, el antivirus del hospital **bloquea** StatLab; en un PC personal
funciona sin problemas. Antes de seguir hay que saber el mensaje exacto, porque hay dos causas posibles:

1. **Política de ejecución (AppLocker o similar):** solo se permiten programas instalados en
   `Archivos de programa`. Se arregla con un **instalador MSI** desplegable por informática.
2. **Falso positivo del antivirus** con un ejecutable de PyInstaller sin firmar. Vías, de menor a mayor coste:
   - que informática autorice la carpeta o el hash;
   - recompilar el arranque de PyInstaller y enviar el programa al fabricante como falso positivo;
   - **firma de código**: certificado con coste anual (⚠ Decide Guzmán).

Lo previsible es que en un hospital acaben haciendo falta el instalador y la firma. En la v1
quedaron fuera de alcance; ahora frenan la adopción.

## 11. Fases

Cada fase termina en una versión publicada, con tests en CI en los tres SO y el autodiagnóstico
(`--self-test`) ampliado.

| Fase | Versión | Contenido | Criterio de aceptación |
|---|---|---|---|
| **F1** | v0.2 | Distribución en el hospital (§10); medir el rendimiento con 5.000 filas | StatLab arranca en un PC del hospital; tiempos medidos y documentados |
| **F2** | v0.3 | **Preparación de datos**, núcleo (§8.1, pasos 1–5 y 7): receta no destructiva, revisión de calidad, tipos, recodificar, nuevas variables con fechas; **diccionario** (§8.2); **diagrama de flujo de pacientes** (§8.4) | Un Excel «sucio» de referencia (hoja 2, cabecera en la fila 3, unidades mezcladas, categorías incoherentes, fechas dd/mm) queda listo sin escribir código; la receta se reaplica idéntica al reabrir la sesión; una fórmula de «Mis fórmulas» se aplica a otro archivo asignando sus columnas |
| **F3** | v0.4 | Sesión con varias soluciones, cada análisis en su pestaña (`.statlab` v2 con migración); **jerárquico** y **GMM**; **comparación de soluciones** (§5.2), incluida **importar solución** de otra sesión o de un CSV `id;cluster` | Con la cohorte de prueba, k-means y GMM con k=4 dan un ARI ≥ 0,90 y el Sankey enlaza con la tabla; una solución importada de otra sesión y la misma exportada a CSV dan el mismo ARI; las sesiones v1 se abren |
| **F4** | v0.5 | **Sensibilidad** generalizada (§5.3); k-medoids con Gower | El informe incluye todos los escenarios y la conclusión automática; la robustez por paciente aparece en la tabla |
| **F5** | v0.6 | Base generalizada (roles, pipeline, pantalla «¿Qué quieres hacer?»); **Tabla 1** y **contrastes**; **datos faltantes a fondo** (§8.3) | La Tabla 1 exportada a Word coincide con R (`tableone`) en un dataset de referencia; MICE combinado coincide con R (`mice`) |
| **F6** | v0.7 | **Supervisado**: logística penalizada, RF, gradient boosting; validación, calibración, curva de decisión, interpretabilidad | Sin fuga de información (test específico); AUC y calibración coinciden con una referencia en scikit-learn |
| **F7** | v0.8 | **Supervivencia**: KM, log-rank y Cox; regresión inferencial (§7.3) | HR e IC coinciden con R (`survival`) en un dataset de referencia |
| **F8** | v0.9 | **Unir archivos** y formato largo/ancho (§8.1, paso 6); **plantillas** (§8.6); **pruebas diagnósticas y escalas de riesgo** (§9) | Una plantilla aplicada a un archivo nuevo da el mismo resultado que el análisis hecho a mano |
| Más adelante | — | Pestañas de sesiones (§5.2), catálogo de referencia de variables (§8.2), anonimización (§8.5), exportar como script (§8.4), resto de §9 (longitudinal, causal, cuestionarios, diseño, concordancia), §5.1 «Más adelante», §6.3, otros idiomas | — |

Orden pensado para **reutilizar al máximo**:
- F2 va primero porque todos los módulos parten de una tabla limpia, y la supervivencia necesita
  tiempos de seguimiento calculados a partir de fechas;
- F3 apoya los algoritmos nuevos en el motor de k-means;
- F4 apoya la sensibilidad en la comparación de soluciones;
- F5 construye la base que F6 y F7 necesitan (roles de desenlace, tiempo y evento; pipeline reutilizable);
- F8 reutiliza la receta de F2 para las plantillas, y supervisado y estadística clásica para las pruebas diagnósticas.

## 12. Dependencias previstas

| Dependencia | Para | Peso | Estado |
|---|---|---|---|
| pandas, openpyxl (ya incluidas) | Preparación de datos, uniones, formato largo/ancho | — | Disponible |
| scikit-learn, scipy (ya incluidas) | Jerárquico, GMM, RF, HistGradientBoosting, contrastes | — | Disponible |
| `statsmodels` | Regresión inferencial, Poisson, diagnósticos, MICE, modelos mixtos, GEE | Medio | ⚠ Decide Guzmán |
| `lifelines` | Kaplan-Meier, log-rank, Cox | Ligero (Python puro) | ⚠ Decide Guzmán |
| `scikit-learn-extra` o implementación propia | k-medoids | Ligero | ⚠ Decide Guzmán |
| `xgboost` | Gradient boosting | Pesado | ⚠ Decide Guzmán (alternativa sin coste: HistGradientBoosting) |
| `shap` | Interpretabilidad | Medio-pesado | ⚠ Decide Guzmán (alternativa: permutación y dependencia parcial) |
| `hdbscan`, `umap-learn`, clases latentes | Más adelante | Pesado | Más adelante |
| `factor_analyzer` / `semopy` | Análisis factorial exploratorio y confirmatorio (§9) | Ligero / medio | Más adelante |
| Datos NPU / LOINC / UCUM (no son librerías) | Nombres, sinónimos y unidades del catálogo de referencia (§8.2) | Un archivo de datos | Más adelante (licencias por revisar) |

## 13. Fuera de alcance

Deep learning, imágenes y texto libre de historias clínicas (procesamiento de lenguaje natural) ·
LLM o lenguaje natural en la interfaz · uso en decisiones clínicas sobre pacientes individuales ·
conexión a la historia clínica electrónica o a bases de datos en red · cálculo en la nube ·
colaboración en tiempo real.

## 14. Decisiones pendientes

1. ¿Qué mensaje exacto da el bloqueo en el hospital? (Decide si F1 es el instalador, la firma o ambos.)
2. ¿Se paga un certificado de firma de código?
3. ¿Se permiten las categóricas en el modelo? (Reabre una decisión cerrada de la v1.)
4. ¿Se puede aplicar un modelo a datos nuevos, y con qué limitaciones? (§3)
5. Dependencias de la §12, una por una.
6. ¿El límite de 5.000 filas se mantiene, o se fija por algoritmo tras medir el rendimiento?
7. ¿La preparación de datos (F2) va antes que los algoritmos no supervisados nuevos (F3), como propone este documento?
8. El script exportado (§8.4), ¿en R, en Python o en ambos?
9. Catálogo de referencia de variables (§8.2): **decidido, más adelante.** Cuando se retome:
   ¿con qué fuente (NPU o LOINC) y quién revisa los límites plausibles?
