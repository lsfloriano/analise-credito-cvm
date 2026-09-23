from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA_RAW = RAIZ / "data" / "raw"
DATA_PROCESSED = RAIZ / "data" / "processed"

ANOS_PADRAO = range(2015, 2026)

URL_DFP = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
URL_CADASTRO = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"

# arquivo dentro do ZIP -> grupo usado no pipeline
DEMONSTRATIVOS = {"BPA": "BP", "BPP": "BP", "DRE": "DRE", "DFC_MI": "DFC", "DFC_MD": "DFC"}

# coluna da tabela contas_base -> código de conta fixa CVM
CONTAS = {
    "ativo_total": "1",
    "ativo_circulante": "1.01",
    "caixa": "1.01.01",
    "aplicacoes_financeiras": "1.01.02",
    "estoques": "1.01.04",
    "ativo_nao_circulante": "1.02",
    "passivo_total": "2",
    "passivo_circulante": "2.01",
    "emprestimos_cp": "2.01.04",
    "passivo_nao_circulante": "2.02",
    "emprestimos_lp": "2.02.01",
    "patrimonio_liquido": "2.03",
    "reservas_lucros": "2.03.04",
    "lucros_acumulados": "2.03.05",
    "receita_liquida": "3.01",
    "ebit": "3.05",
    "despesas_financeiras": "3.06.02",
    "lucro_liquido": "3.11",
    "fco": "6.01",
}

# ausência significa "a empresa não tem esse item": preenche com 0 sem registrar problema
CONTAS_OPCIONAIS = {
    "aplicacoes_financeiras", "estoques", "emprestimos_cp", "emprestimos_lp",
    "reservas_lucros", "lucros_acumulados", "despesas_financeiras",
}

# setores já limpos (ver cadastro.limpar_setor) excluídos da análise
SETORES_FINANCEIROS = {
    "Bancos",
    "Seguradoras e Corretoras",
    "Intermediação Financeira",
    "Arrendamento Mercantil",
    "Securitização de Recebíveis",
    "Crédito Imobiliário",
    "Factoring",
    "Bolsas de Valores/Mercadorias e Futuros",
}

# variações de nome de setor (depois de remover o prefixo de holding) -> nome canônico
ALIAS_SETOR = {
    "Const. Civil, Mat. Const. e Decoração": "Construção Civil, Mat. Constr. e Decoração",
    "Máqs., Equip., Veíc. e Peças": "Máquinas, Equipamentos, Veículos e Peças",
    "Serviços médicos": "Serviços Médicos",
    "Sem Setor Principal": "Holdings Diversificadas",
    "Emp. Adm. Participações": "Holdings Diversificadas",
}

# código -> trecho que a descrição precisa conter no layout de empresa não financeira
LAYOUT_ESPERADO = {
    "2.03": "Patrimônio Líquido",
    "3.05": "Resultado Antes do Resultado Financeiro",
}
