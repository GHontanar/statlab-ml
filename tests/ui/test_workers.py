import threading

from statlab.core.errors import ErrorUsuario
from statlab.core.kmeans import Cancelled
from statlab.workers import Tarea, lanzar


def _run(qtbot, fn):
    tarea = Tarea(fn)
    got = {}
    tarea.senales.terminado.connect(lambda r: got.update(ok=r))
    tarea.senales.fallido.connect(lambda m, u: got.update(fail=(m, u)))
    tarea.senales.cancelado.connect(lambda: got.update(cancel=True))
    lanzar(tarea)
    qtbot.waitUntil(lambda: bool(got), timeout=5000)
    return tarea, got


def test_result_and_progress(qtbot):
    seen = []

    def fn(progreso, cancelar):
        progreso(0.5)
        return 42

    tarea = Tarea(fn)
    tarea.senales.progreso.connect(seen.append)
    with qtbot.waitSignal(tarea.senales.terminado) as blocker:
        lanzar(tarea)
    assert blocker.args == [42]
    qtbot.waitUntil(lambda: seen == [0.5])


def test_user_error_vs_unexpected(qtbot):
    def user(progreso, cancelar):
        raise ErrorUsuario("Faltan datos")

    def boom(progreso, cancelar):
        raise RuntimeError("detalle interno")

    assert _run(qtbot, user)[1]["fail"] == ("Faltan datos", True)
    assert _run(qtbot, boom)[1]["fail"][1] is False


def test_cooperative_cancel(qtbot):
    started = threading.Event()

    def fn(progreso, cancelar):
        started.set()
        while not cancelar():
            pass
        raise Cancelled

    tarea = Tarea(fn)
    got = {}
    tarea.senales.cancelado.connect(lambda: got.update(cancel=True))
    lanzar(tarea)
    assert started.wait(5)
    tarea.cancelar()
    qtbot.waitUntil(lambda: got.get("cancel"), timeout=5000)
