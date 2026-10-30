"""«Mis fórmulas»: biblioteca personal de cálculos para reutilizarlos en otros archivos.

Se guarda fuera de las sesiones, en un JSON del equipo, y se puede exportar e
importar para compartirla. Una fórmula guardada conserva los nombres de columna
con los que se escribió (sus «entradas»); al aplicarla a otro archivo el usuario
indica qué columna es cada entrada. Nada se asigna automáticamente.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from statlab import strings_es as S
from statlab.core.errors import ErrorUsuario
from statlab.core.prep import formula
from statlab.core.prep.receta import Paso

TIPO = "statlab-mis-formulas"
VERSION = 1


@dataclass
class FormulaGuardada:
    nombre: str  # también es el nombre por defecto de la columna resultado
    formula: str
    descripcion: str = ""

    @property
    def entradas(self) -> list[str]:
        return formula.columnas(formula.analizar(self.formula))

    def paso(self, mapa: dict[str, str], destino: str | None = None) -> Paso:
        """Paso «calcular» con las entradas sustituidas por las columnas de este archivo."""
        faltan = [e for e in self.entradas if not mapa.get(e)]
        if faltan:
            raise ErrorUsuario(S.MYF_UNMAPPED.format(cols=", ".join(faltan)))
        texto = formula.renombrar(self.formula, mapa) if any(mapa[e] != e for e in self.entradas) else self.formula
        return Paso("calcular", {"destino": destino or self.nombre, "formula": texto, "origen": self.nombre})


@dataclass
class Biblioteca:
    formulas: list[FormulaGuardada] = field(default_factory=list)

    def get(self, nombre: str) -> FormulaGuardada | None:
        return next((f for f in self.formulas if f.nombre == nombre), None)

    def guardar_formula(self, f: FormulaGuardada) -> None:
        """Añade o sustituye (por nombre). Comprueba antes que la fórmula es válida."""
        if not f.nombre.strip():
            raise ErrorUsuario(S.PREP_NO_NAME)
        formula.analizar(f.formula)
        self.formulas = [x for x in self.formulas if x.nombre != f.nombre] + [f]
        self.formulas.sort(key=lambda x: x.nombre.casefold())

    def quitar(self, nombre: str) -> None:
        self.formulas = [x for x in self.formulas if x.nombre != nombre]

    def to_dict(self) -> dict:
        return {"tipo": TIPO, "version": VERSION, "formulas": [asdict(f) for f in self.formulas]}

    @classmethod
    def from_dict(cls, d: dict) -> Biblioteca:
        if d.get("tipo") != TIPO:
            raise ErrorUsuario(S.MYF_INVALID)
        if int(d.get("version", 0)) > VERSION:
            raise ErrorUsuario(S.MYF_NEWER)
        out = cls()
        for f in d.get("formulas", []):
            out.guardar_formula(FormulaGuardada(**f))
        return out

    def escribir(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)
        return path

    @classmethod
    def leer(cls, path: str | Path) -> Biblioteca:
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as e:
            raise ErrorUsuario(S.MYF_INVALID) from e

    def importar(self, otra: Biblioteca) -> tuple[int, int]:
        """Une otra biblioteca a esta. Devuelve (nuevas, sustituidas)."""
        nuevas = sustituidas = 0
        for f in otra.formulas:
            if self.get(f.nombre):
                sustituidas += 1
            else:
                nuevas += 1
            self.guardar_formula(f)
        return nuevas, sustituidas
