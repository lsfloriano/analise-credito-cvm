import pytest


@pytest.fixture
def linha_cvm():
    """Fábrica de uma linha crua no formato da CVM (tudo string, como lido do CSV)."""
    def _linha(cd_conta, valor, *, cd_cvm="001023", tipo="con", demonstrativo="BP",
               ds_conta="Conta", versao="1", escala="MIL", ordem="ÚLTIMO",
               dt_fim="2024-12-31", fixa="S", cnpj="00.000.000/0001-00", nome="EMPRESA X SA"):
        return {
            "CNPJ_CIA": cnpj, "CD_CVM": cd_cvm, "DENOM_CIA": nome, "VERSAO": versao,
            "ESCALA_MOEDA": escala, "ORDEM_EXERC": ordem, "DT_FIM_EXERC": dt_fim,
            "CD_CONTA": cd_conta, "DS_CONTA": ds_conta, "VL_CONTA": str(valor),
            "ST_CONTA_FIXA": fixa, "demonstrativo": demonstrativo, "tipo": tipo,
        }
    return _linha
