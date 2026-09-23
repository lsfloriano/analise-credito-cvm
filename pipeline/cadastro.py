import re

import pandas as pd

from pipeline import config

_PREFIXO_HOLDING = re.compile(r"^Emp\. Adm\. Part\.\s*-\s*")


def limpar_setor(setor):
    if setor is None or pd.isna(setor) or not str(setor).strip():
        return "Não Informado"
    s = _PREFIXO_HOLDING.sub("", str(setor).strip())
    return config.ALIAS_SETOR.get(s, s)


def ler_cadastro(path):
    cad = pd.read_csv(path, sep=";", encoding="latin-1", dtype=str)
    cad = cad.dropna(subset=["CD_CVM"]).copy()
    cad["cd_cvm"] = cad["CD_CVM"].astype(int)
    cad["_ativo"] = cad["SIT"].eq("ATIVO")
    cad["_dt"] = pd.to_datetime(cad["DT_INI_SIT"], errors="coerce")
    cad = (cad.sort_values(["cd_cvm", "_ativo", "_dt"], ascending=[True, False, False])
              .drop_duplicates("cd_cvm"))
    return pd.DataFrame({
        "cd_cvm": cad["cd_cvm"],
        "cnpj": cad["CNPJ_CIA"],
        "nome": cad["DENOM_SOCIAL"],
        "setor": cad["SETOR_ATIV"].map(limpar_setor),
        "situacao": cad["SIT"],
    }).reset_index(drop=True)
