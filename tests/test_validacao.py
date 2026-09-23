import math

import pandas as pd
import pytest

from pipeline import validacao


def test_ler_resultado_dax_normaliza_cabecalhos(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("dim_empresa[cd_cvm],dim_ano[ano],[liquidez_corrente]\n10,2024,1.5\n", encoding="utf-8-sig")
    df = validacao.ler_resultado_dax(p)
    assert list(df.columns) == ["cd_cvm", "ano", "liquidez_corrente"]
    assert df.iloc[0]["liquidez_corrente"] == 1.5


def _par(dax_val, ref_val):
    dax = pd.DataFrame({"cd_cvm": [1], "ano": [2024], "x": [dax_val]})
    ref = pd.DataFrame({"cd_cvm": [1], "ano": [2024], "x": [ref_val]})
    return validacao.comparar(dax, ref, ["cd_cvm", "ano"], ["x"])


def test_comparar_iguais_dentro_da_tolerancia():
    assert _par(1.0000000001, 1.0).empty


def test_comparar_nulo_dos_dois_lados_bate():
    assert _par(float("nan"), float("nan")).empty


def test_comparar_nulo_de_um_lado_diverge():
    d = _par(float("nan"), 2.0)
    assert len(d) == 1 and d.iloc[0]["coluna"] == "x"


def test_comparar_valor_diferente_diverge():
    assert len(_par(1.1, 1.0)) == 1


def test_comparar_texto():
    dax = pd.DataFrame({"k": [1, 2], "zona": ["risco", "segura"]})
    ref = pd.DataFrame({"k": [1, 2], "zona": ["risco", "cinzenta"]})
    d = validacao.comparar(dax, ref, ["k"], ["zona"])
    assert d["k"].tolist() == [2]


def test_comparar_linha_faltando_diverge():
    dax = pd.DataFrame({"k": [1], "x": [1.0]})
    ref = pd.DataFrame({"k": [1, 2], "x": [1.0, 2.0]})
    d = validacao.comparar(dax, ref, ["k"], ["x"])
    assert d["coluna"].tolist() == ["(linha)"]


def _fato():
    base = dict(ativo_total=100.0, ativo_circulante=50.0, estoques=0.0, passivo_circulante=25.0,
                passivo_nao_circulante=25.0, patrimonio_liquido=50.0, caixa=0.0,
                aplicacoes_financeiras=0.0, emprestimos_cp=0.0, emprestimos_lp=0.0,
                receita_liquida=100.0, ebit=10.0, despesas_financeiras=-5.0, lucro_liquido=5.0,
                z=5.0, zona="cinzenta", tipo_fleuriet=2)
    linhas = []
    for cd, ac, zona24, zona25 in [(1, 50.0, "risco", "risco"), (2, 75.0, "risco", "segura"),
                                   (3, 100.0, "segura", "segura")]:
        for ano, zona in [(2024, zona24), (2025, zona25)]:
            linhas.append({**base, "cd_cvm": cd, "ano": ano, "ativo_circulante": ac, "zona": zona})
    return pd.DataFrame(linhas)


EMPRESAS = pd.DataFrame({"cd_cvm": [1, 2, 3], "setor": ["A", "A", "A"]})


def test_referencia_indices_traz_scores():
    r = validacao.referencia_indices(_fato())
    assert {"liquidez_corrente", "z", "zona", "tipo_fleuriet"} <= set(r.columns)
    assert len(r) == 6


def test_referencia_benchmark_mediana_e_quartis():
    r = validacao.referencia_benchmark(_fato(), EMPRESAS)
    linha = r[(r["setor"] == "A") & (r["ano"] == 2024)].iloc[0]
    # liquidez corrente = 2, 3, 4
    assert linha["liquidez_corrente_mediana"] == pytest.approx(3.0)
    assert linha["liquidez_corrente_q1"] == pytest.approx(2.5)
    assert linha["liquidez_corrente_q3"] == pytest.approx(3.5)


def test_referencia_percentil_conta_menores_ou_iguais():
    r = validacao.referencia_percentil(_fato(), EMPRESAS, 2024).set_index("cd_cvm")
    assert r.loc[1, "liquidez_corrente_pct"] == pytest.approx(1 / 3)
    assert r.loc[3, "liquidez_corrente_pct"] == pytest.approx(1.0)


def test_referencia_migracao():
    r = validacao.referencia_migracao(_fato(), 2024, 2025)
    n = {(a, b): v for a, b, v in r[["zona", "zona_origem", "n"]].itertuples(index=False)}
    assert n == {("risco", "risco"): 1, ("segura", "risco"): 1, ("segura", "segura"): 1}


def test_cli_validar_dax_sai_1_quando_diverge(tmp_path):
    from pipeline import cli
    out = tmp_path / "out"
    out.mkdir()
    _fato().to_parquet(out / "fato_indicadores.parquet")
    EMPRESAS.to_parquet(out / "dim_empresa.parquet")
    csv = tmp_path / "dax.csv"
    csv.write_text("[zona],[zona_origem],[n]\nrisco,risco,1\nsegura,risco,1\nsegura,segura,2\n",
                   encoding="utf-8")
    assert cli.validar_dax("migracao", csv, ano=2025, ano_base=2024, out_dir=out) == 1
    csv.write_text("[zona],[zona_origem],[n]\nrisco,risco,1\nsegura,risco,1\nsegura,segura,1\n",
                   encoding="utf-8")
    assert cli.validar_dax("migracao", csv, ano=2025, ano_base=2024, out_dir=out) == 0
