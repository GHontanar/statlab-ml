import subprocess
import sys


def test_core_does_not_import_qt():
    code = (
        "import sys, statlab.core.io, statlab.core.kmeans; "
        "import statlab.core.prep.preparacion, statlab.core.prep.calidad, statlab.core.prep.mis_formulas; "
        "bad = [m for m in sys.modules if m.startswith(('PySide6', 'pyqtgraph'))]; "
        "sys.exit(1 if bad else 0)"
    )
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
