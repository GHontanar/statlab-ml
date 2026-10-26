import os
from pathlib import Path


def capture(widget, name: str) -> None:
    """Guarda una captura si STATLAB_CAPTURAS apunta a una carpeta."""
    folder = os.environ.get("STATLAB_CAPTURAS")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        assert widget.grab().save(str(Path(folder) / f"{name}.png"))
