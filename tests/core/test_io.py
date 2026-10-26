import pandas as pd
import pytest

from statlab.core import io as sio
from statlab.core import kmeans as kc


def test_example_data_loads_with_decimal_commas():
    df = sio.read_example()
    assert df.shape == (240, 11)
    for col in ["edad", "hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]:
        assert df[col].dtype.kind == "f", col
    assert set(kc.numeric_columns(df)) >= {"hb", "ferritina"}
    assert "sexo" not in kc.numeric_columns(df)
    na_pct = df[["hb", "vcm", "plaquetas", "neutrofilos", "hbf", "ferritina"]].isna().mean().mean()
    assert 0.03 < na_pct < 0.09


@pytest.mark.parametrize("token", ["", "NA", "nan", "n/a", "-", "."])
def test_na_tokens(token):
    raw = f"a;b\n1,5;x\n{token};y\n2,5;z\n".encode()
    df = sio.read_table("t.csv", raw)
    assert df["a"].dtype.kind == "f"
    assert df["a"].isna().sum() == 1


def test_tsv_and_excel(tmp_path):
    df = sio.read_table("t.tsv", b"a\tb\n1\t2\n3\t4\n")
    assert df.shape == (2, 2)
    path = tmp_path / "t.xlsx"
    pd.DataFrame({"x": [1.5, 2.5], "y": ["a", "b"]}).to_excel(path, index=False)
    df = sio.read_path(path)
    assert df["x"].tolist() == [1.5, 2.5]
