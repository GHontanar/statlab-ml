"""Errores con un mensaje pensado para el usuario (se muestra tal cual, sin traza)."""


class ErrorUsuario(ValueError):
    """Problema de los datos o de los parámetros que el usuario puede resolver."""
