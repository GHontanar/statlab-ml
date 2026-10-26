"""Punto de entrada: QApplication, tema, fuente y ventana principal."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from statlab import __version__
from statlab import strings_es as S
from statlab.modules import available_modules
from statlab.ui import theme
from statlab.ui.main_window import MainWindow
from statlab.ui.theme import icons
from statlab.ui.theme import tokens as tk


def create_app(argv: list[str] | None = None) -> QApplication:
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(S.APP_NAME)
    app.setApplicationDisplayName(S.APP_NAME)
    app.setOrganizationName("StatLab")
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("statlab")
    app.setWindowIcon(icons.icon("logo", accent=tk.LIGHT["accent"]))
    theme.setup(app, MainWindow.theme_mode())
    return app


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    if "--self-test" in args:
        from statlab import selftest

        i = args.index("--self-test")
        return selftest.run(args[i + 1] if i + 1 < len(args) else None)
    app = create_app(argv)
    window = MainWindow(available_modules()[0])
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
