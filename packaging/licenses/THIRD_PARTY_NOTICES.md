# Componentes de terceros

StatLab se distribuye junto con estos componentes. Cada uno mantiene su propia licencia.

| Componente | Licencia |
|---|---|
| Qt 6 (a través de PySide6 y Shiboken6) | GNU LGPL v3 — ver `LGPL-3.0.txt` y `GPL-3.0.txt` |
| Python | PSF License |
| NumPy, pandas, SciPy, scikit-learn, joblib, threadpoolctl | BSD |
| Matplotlib | Matplotlib License (basada en la PSF) |
| pyqtgraph | MIT |
| ReportLab | BSD |
| python-docx, openpyxl | MIT |
| lxml | BSD |
| Pillow | MIT-CMU (HPND) |
| Fuente Inter | SIL Open Font License 1.1 — ver `Inter-OFL-1.1.txt` |

## Qt y la LGPL

StatLab usa Qt bajo los términos de la GNU Lesser General Public License v3. Qt se
enlaza de forma **dinámica**: sus bibliotecas compartidas están como archivos
independientes dentro de la carpeta de la aplicación (`_internal/PySide6/…`), y se
pueden sustituir por otra versión compatible de Qt/PySide6 sin recompilar StatLab.

El código fuente de Qt está disponible en <https://code.qt.io> y
<https://download.qt.io/official_releases/qt/>; el de PySide6, en
<https://code.qt.io/cgit/pyside/pyside-setup.git/>.
