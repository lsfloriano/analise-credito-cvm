import zipfile

import pytest

from pipeline import leitura

CABECALHO = ("CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
             "ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA")


def _csv(cd_conta, ds_conta, valor):
    linha = (f"00.000.000/0001-00;2024-12-31;1;EMPRESA X SA;001023;G;REAL;MIL;"
             f"ÚLTIMO;2024-12-31;{cd_conta};{ds_conta};{valor};S")
    return (CABECALHO + "\n" + linha + "\n").encode("latin-1")


def test_le_demonstrativos_con_e_ind(tmp_path):
    zp = tmp_path / "dfp.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("dfp_cia_aberta_BPA_con_2024.csv", _csv("1", "Ativo Total", "100.0000000000"))
        z.writestr("dfp_cia_aberta_BPP_ind_2024.csv", _csv("2.03", "Patrimônio Líquido", "40.0"))
        z.writestr("dfp_cia_aberta_DFC_MI_con_2024.csv", _csv("6.01", "Caixa Líquido", "7.0"))
        z.writestr("dfp_cia_aberta_DVA_con_2024.csv", _csv("7.01", "Receitas", "1.0"))  # ignorado

    df = leitura.ler_dfp(zp, 2024)

    assert len(df) == 3
    assert set(df["demonstrativo"]) == {"BP", "DFC"}
    assert sorted(df["tipo"]) == ["con", "con", "ind"]
    assert df.loc[df["CD_CONTA"] == "2.03", "DS_CONTA"].item() == "Patrimônio Líquido"
    assert df.loc[df["CD_CONTA"] == "1", "CD_CVM"].item() == "001023"
    assert set(leitura.COLUNAS) <= set(df.columns)


def test_zip_sem_demonstrativos_da_erro(tmp_path):
    zp = tmp_path / "vazio.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("outro.csv", "x")
    with pytest.raises(ValueError, match="vazio.zip"):
        leitura.ler_dfp(zp, 2024)
