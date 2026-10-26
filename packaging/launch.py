"""Punto de entrada del ejecutable empaquetado (PyInstaller)."""
import multiprocessing

from statlab.app import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
