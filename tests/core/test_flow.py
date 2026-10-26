import pytest

from statlab.core.flow import EstadoPaso as E
from statlab.core.flow import FlujoPasos

IDS = ["datos", "variables", "prep", "k", "final", "exportar"]


def test_happy_path():
    f = FlujoPasos(IDS)
    assert f.activo == "datos" and f["variables"] == E.PENDIENTE
    assert f.completar("datos") == "variables"
    assert f.completar("variables") == "prep"
    assert f.completar("prep") == "k"
    assert [f[i] for i in IDS[:4]] == [E.HECHO, E.HECHO, E.HECHO, E.ACTIVO]


def test_cascade_invalidation_and_recalc():
    f = FlujoPasos(IDS)
    for p in IDS[:5]:
        f.completar(p)
    assert f.activo == "exportar"
    assert f.invalidar_despues("variables") == ["prep", "k", "final"]
    assert [f[i] for i in IDS] == [E.HECHO, E.HECHO, E.DESACTUALIZADO, E.DESACTUALIZADO, E.DESACTUALIZADO,
                                   E.PENDIENTE]
    assert not f.listo_para("k")
    assert f.completar("prep") is None  # el siguiente sigue desactualizado
    assert f.listo_para("k")


def test_active_after_stale_goes_pending():
    f = FlujoPasos(IDS)
    for p in IDS[:3]:
        f.completar(p)
    assert f.activo == "k"
    f.invalidar_despues("variables")
    assert f["prep"] == E.DESACTUALIZADO and f["k"] == E.PENDIENTE
    f.completar("prep")
    assert f.activo == "k"


def test_reopen():
    f = FlujoPasos(IDS)
    for p in IDS[:3]:
        f.completar(p)
    f.abrir("variables")
    assert f.activo == "variables" and f["k"] == E.PENDIENTE and f["prep"] == E.HECHO
    with pytest.raises(ValueError):
        f.abrir("final")
    g = FlujoPasos.from_dict(IDS, f.to_dict())
    assert g.to_dict() == f.to_dict()
