import numpy as np

INDICES = ["liquidez_corrente", "liquidez_seca", "endividamento_geral", "divida_liquida_pl",
           "cobertura_juros", "margem_ebit", "margem_liquida", "roa", "roe"]


def _div(num, den):
    return num / den.where(den != 0)


def calcular_indices(fato):
    f = fato
    pl_positivo = f["patrimonio_liquido"].where(f["patrimonio_liquido"] > 0)
    divida_liquida = (f["emprestimos_cp"] + f["emprestimos_lp"]
                      - f["caixa"] - f["aplicacoes_financeiras"])
    out = f[["cd_cvm", "ano"]].copy()
    out["liquidez_corrente"] = _div(f["ativo_circulante"], f["passivo_circulante"])
    out["liquidez_seca"] = _div(f["ativo_circulante"] - f["estoques"], f["passivo_circulante"])
    out["endividamento_geral"] = _div(f["passivo_circulante"] + f["passivo_nao_circulante"], f["ativo_total"])
    out["divida_liquida_pl"] = divida_liquida / pl_positivo
    # despesas financeiras vêm negativas na DRE da CVM
    out["cobertura_juros"] = _div(f["ebit"], np.abs(f["despesas_financeiras"]))
    out["margem_ebit"] = _div(f["ebit"], f["receita_liquida"])
    out["margem_liquida"] = _div(f["lucro_liquido"], f["receita_liquida"])
    out["roa"] = _div(f["lucro_liquido"], f["ativo_total"])
    out["roe"] = f["lucro_liquido"] / pl_positivo
    return out
