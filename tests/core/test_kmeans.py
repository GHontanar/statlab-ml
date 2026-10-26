import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_blobs

from statlab.core import io as sio
from statlab.core import kmeans as kc


def make_df(n=300, k=3, na_frac=0.08, seed=1):
    X, y = make_blobs(n_samples=n, centers=k, n_features=4, cluster_std=1.0, random_state=seed)
    df = pd.DataFrame(X * [1, 10, 100, 0.1], columns=["hb", "plaquetas", "ldh", "pcr"])
    rng = np.random.default_rng(seed)
    mask = rng.random(df.shape) < na_frac
    df = df.mask(mask)
    df["grupo_real"] = y
    df["sexo"] = rng.choice(["M", "F"], n)
    return df, y


def test_prepare_methods():
    df, _ = make_df()
    cols = ["hb", "plaquetas", "ldh", "pcr"]
    for m in kc.IMPUTATION_METHODS:
        p = kc.prepare(df, cols, m, "standard", 5)
        assert not np.isnan(p.X).any()
        assert np.allclose(p.X.mean(axis=0), 0, atol=1e-8)
        if m == "complete":
            assert p.n_dropped > 0 and p.n_imputed_cells == 0
        else:
            assert p.n_imputed_cells > 0 and len(p.X) == len(df)


def test_prepare_errors():
    df, _ = make_df()
    with pytest.raises(ValueError):
        kc.prepare(df, ["hb"])
    df["vacia"] = np.nan
    with pytest.raises(ValueError):
        kc.prepare(df, ["hb", "vacia"])


def test_sweep_picks_true_k():
    df, _ = make_df(na_frac=0)
    p = kc.prepare(df, ["hb", "plaquetas", "ldh", "pcr"], "complete")
    sw = kc.sweep_k(p.X, range(2, 7))
    assert int(sw.loc[sw["Silueta"].idxmax(), "k"]) == 3


def test_relabel_by_size():
    lab = np.array([2, 2, 2, 0, 1, 1])
    new, _ = kc.relabel_by_size(lab, 3)
    assert list(new) == [0, 0, 0, 2, 1, 1]


def test_bootstrap_stable_clusters():
    df, y = make_df()
    p = kc.prepare(df, ["hb", "plaquetas", "ldh", "pcr"], "knn")
    km, lab = kc.fit_kmeans(p.X, 3)
    assert np.bincount(lab)[0] == np.bincount(lab).max()
    res = kc.bootstrap_validate(p.X, 3, lab, B=40, seed=0)
    assert res.jaccard.shape == (40, 3)
    assert (res.jaccard_mean > 0.85).all()
    lo, hi = res.silhouette_ci
    assert 0 < lo <= hi < 1
    assert np.nanmean(res.ari) > 0.9


def test_bootstrap_detects_instability():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 3))  # sin estructura
    _, lab = kc.fit_kmeans(X, 5)
    res = kc.bootstrap_validate(X, 5, lab, B=40, seed=0)
    assert res.jaccard_mean.min() < 0.75


def test_profiles_and_external():
    df, _ = make_df()
    cols = ["hb", "plaquetas", "ldh", "pcr"]
    p = kc.prepare(df, cols, "median")
    _, lab = kc.fit_kmeans(p.X, 3)
    rows = df.loc[p.row_index]
    desc, z = kc.cluster_profiles(rows, cols, p.X, lab)
    assert len(desc) == 4 and z.shape == (3, 4)
    ext = kc.describe_external(rows, ["sexo", "grupo_real"], lab)
    assert set(ext["Variable"]) == {"sexo", "grupo_real"}


def test_imputation_sensitivity_high_agreement():
    df, _ = make_df()
    mat, n = kc.imputation_sensitivity(df, ["hb", "plaquetas", "ldh", "pcr"], 3, "standard", 5)
    assert mat.shape == (4, 4)
    assert np.nanmin(mat.values) > 0.8


def test_decimal_comma_reading():
    raw = "id;hb;plq;sexo\n1;12,5;150;M\n2;9,8;NA;F\n3;11;220;M\n".encode("latin-1")
    df = sio.read_table("datos.csv", raw)
    assert df["hb"].dtype.kind == "f"
    assert df["hb"].tolist() == [12.5, 9.8, 11.0]
    assert df["plq"].isna().sum() == 1
    assert df["sexo"].dtype.kind in "OU" or pd.api.types.is_string_dtype(df["sexo"])


def test_methods_text():
    df, _ = make_df()
    p = kc.prepare(df, ["hb", "plaquetas", "ldh", "pcr"], "knn")
    _, lab = kc.fit_kmeans(p.X, 3)
    boot = kc.bootstrap_validate(p.X, 3, lab, B=10)
    t = kc.methods_text(p, 3, 20, 0, (2, 8), 0.6, boot)
    assert "k vecinos" in t and "Jaccard" in t


def test_cancellation_and_progress():
    df, _ = make_df(na_frac=0)
    p = kc.prepare(df, ["hb", "plaquetas", "ldh", "pcr"], "complete")
    _, lab = kc.fit_kmeans(p.X, 3)
    seen = []
    kc.sweep_k_bootstrap(p.X, [2, 3], B=4, progress=seen.append)
    assert seen == sorted(seen) and seen[-1] == pytest.approx(1.0)

    calls = {"n": 0}

    def cancel_after_two():
        calls["n"] += 1
        return calls["n"] > 2

    with pytest.raises(kc.Cancelled):
        kc.bootstrap_validate(p.X, 3, lab, B=50, should_cancel=cancel_after_two)
    assert calls["n"] == 3
    with pytest.raises(kc.Cancelled):
        kc.sweep_k(p.X, range(2, 6), should_cancel=lambda: True)


def test_silhouette_exact_up_to_5000():
    assert kc.SILHOUETTE_MAX_N == 5000


def test_elbow_k():
    assert kc.elbow_k([2, 3, 4, 5, 6, 7, 8], [630, 326, 289, 261, 232, 217, 202]) == 3
    assert kc.elbow_k([2, 3], [10, 5]) == 2
