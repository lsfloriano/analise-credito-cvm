import pytest

from pipeline import cadastro

CAB = "CNPJ_CIA;DENOM_SOCIAL;SIT;DT_INI_SIT;CD_CVM;SETOR_ATIV\n"


@pytest.mark.parametrize("entrada, esperado", [
    ("Energia Elétrica", "Energia Elétrica"),
    ("Emp. Adm. Part. - Energia Elétrica", "Energia Elétrica"),
    ("Emp. Adm. Part.-Bolsas de Valores/Mercadorias e Futuros", "Bolsas de Valores/Mercadorias e Futuros"),
    ("Emp. Adm. Part. - Máqs., Equip., Veíc. e Peças", "Máquinas, Equipamentos, Veículos e Peças"),
    ("Emp. Adm. Part. - Sem Setor Principal", "Holdings Diversificadas"),
    ("Emp. Adm. Participações", "Holdings Diversificadas"),
    ("  Bancos ", "Bancos"),
    (None, "Não Informado"),
    ("", "Não Informado"),
])
def test_limpar_setor(entrada, esperado):
    assert cadastro.limpar_setor(entrada) == esperado


def test_ler_cadastro_deduplica_preferindo_ativo_e_mais_recente(tmp_path):
    p = tmp_path / "cad.csv"
    p.write_bytes((CAB
        + "11;VELHA SA;CANCELADA;2020-01-01;5410;Emp. Adm. Part. - Máqs., Equip., Veíc. e Peças\n"
        + "11;WEG SA;ATIVO;2010-01-01;5410;Emp. Adm. Part. - Máqs., Equip., Veíc. e Peças\n"
        + "22;VALE S.A.;ATIVO;2001-01-01;4170;Extração Mineral\n"
        + "22;VALE S.A.;ATIVO;2015-01-01;4170;Extração Mineral\n"
        + "33;SEM SETOR SA;ATIVO;2015-01-01;77;\n").encode("latin-1"))

    df = cadastro.ler_cadastro(p)

    assert list(df.columns) == ["cd_cvm", "cnpj", "nome", "setor", "situacao"]
    assert df["cd_cvm"].is_unique
    r = df.set_index("cd_cvm")
    assert r.loc[5410, "nome"] == "WEG SA"
    assert r.loc[5410, "setor"] == "Máquinas, Equipamentos, Veículos e Peças"
    assert r.loc[4170, "situacao"] == "ATIVO"
    assert r.loc[77, "setor"] == "Não Informado"
