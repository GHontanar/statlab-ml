from statlab import selftest


def test_self_test_passes(tmp_path, qapp):
    out = tmp_path / "resultado.txt"
    assert selftest.run(str(out)) == 0, out.read_text(encoding="utf-8")
    text = out.read_text(encoding="utf-8")
    assert "ventana: ok" in text and "análisis: ok" in text and "sesión: ok" in text and "OK en" in text
