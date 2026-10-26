import os
from pathlib import Path

from PySide6.QtWidgets import QApplication


def capture(widget, name: str) -> None:
    """Guarda una captura si STATLAB_CAPTURAS apunta a una carpeta."""
    folder = os.environ.get("STATLAB_CAPTURAS")
    if folder:
        for _ in range(3):  # dejar que se apliquen los cambios de layout pendientes
            QApplication.processEvents()
        Path(folder).mkdir(parents=True, exist_ok=True)
        assert widget.grab().save(str(Path(folder) / f"{name}.png"))
