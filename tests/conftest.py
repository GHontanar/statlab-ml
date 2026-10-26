import os

# Los tests de interfaz corren sin pantalla (también en CI).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
