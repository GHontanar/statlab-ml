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

## 8. Distribución en el hospital (bloqueante)

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

## 9. Fases

Cada fase termina en una versión publicada, con tests en CI en los tres SO y el autodiagnóstico
(`--self-test`) ampliado.

| Fase | Versión | Contenido | Criterio de aceptación |
|---|---|---|---|
| **F1** | v0.2 | Distribución en el hospital (§8); medir el rendimiento con 5.000 filas | StatLab arranca en un PC del hospital; tiempos medidos y documentados |
| **F2** | v0.3 | Sesión con varias soluciones (`.statlab` v2 con migración); **jerárquico** y **GMM**; **comparación de soluciones** (§5.2) | Con la cohorte de prueba, k-means y GMM con k=4 dan un ARI ≥ 0,90 y el Sankey enlaza con la tabla; las sesiones v1 se abren |
| **F3** | v0.4 | **Sensibilidad** generalizada (§5.3); k-medoids con Gower | El informe incluye todos los escenarios y la conclusión automática; la robustez por paciente aparece en la tabla |
| **F4** | v0.5 | Base generalizada (roles, pipeline, pantalla «¿Qué quieres hacer?»); **Tabla 1** y **contrastes** | La Tabla 1 exportada a Word coincide con R (`tableone`) en un dataset de referencia |
| **F5** | v0.6 | **Supervisado**: logística penalizada, RF, gradient boosting; validación, calibración, curva de decisión, interpretabilidad | Sin fuga de información (test específico); AUC y calibración coinciden con una referencia en scikit-learn |
| **F6** | v0.7 | **Supervivencia**: KM, log-rank y Cox; regresión inferencial (§7.3) | HR e IC coinciden con R (`survival`) en un dataset de referencia |
| Más adelante | — | §5.1 «Más adelante», §6.3, §7.5, otros idiomas | — |

Orden pensado para **reutilizar al máximo**:
- F2 apoya los algoritmos nuevos en el motor de k-means;
- F3 apoya la sensibilidad en la comparación de soluciones;
- F4 construye la base que F5 y F6 necesitan (roles de desenlace, tiempo y evento; pipeline reutilizable).

## 10. Dependencias previstas

| Dependencia | Para | Peso | Estado |
|---|---|---|---|
| scikit-learn, scipy (ya incluidas) | Jerárquico, GMM, RF, HistGradientBoosting, contrastes | — | Disponible |
| `statsmodels` | Regresión inferencial, Poisson, diagnósticos | Medio | ⚠ Decide Guzmán |
| `lifelines` | Kaplan-Meier, log-rank, Cox | Ligero (Python puro) | ⚠ Decide Guzmán |
| `scikit-learn-extra` o implementación propia | k-medoids | Ligero | ⚠ Decide Guzmán |
| `xgboost` | Gradient boosting | Pesado | ⚠ Decide Guzmán (alternativa sin coste: HistGradientBoosting) |
| `shap` | Interpretabilidad | Medio-pesado | ⚠ Decide Guzmán (alternativa: permutación y dependencia parcial) |
| `hdbscan`, `umap-learn`, clases latentes | Más adelante | Pesado | Más adelante |

## 11. Fuera de alcance

Deep learning, imágenes y texto libre · LLM o lenguaje natural · uso en decisiones clínicas sobre
pacientes individuales · conexión a historias clínicas o bases de datos en red · cálculo en la nube ·
colaboración en tiempo real.

## 12. Decisiones pendientes

1. ¿Qué mensaje exacto da el bloqueo en el hospital? (Decide si F1 es el instalador, la firma o ambos.)
2. ¿Se paga un certificado de firma de código?
3. ¿Se permiten las categóricas en el modelo? (Reabre una decisión cerrada de la v1.)
4. ¿Se puede aplicar un modelo a datos nuevos, y con qué limitaciones? (§3)
5. Dependencias de la §10, una por una.
6. ¿El límite de 5.000 filas se mantiene, o se fija por algoritmo tras medir el rendimiento?
