# Conferência do pipeline com demonstrações publicadas

Execução completa em 2026-09-23 (`python -m pipeline run`, 2015–2025):
830 empresas, 6.266 empresas-ano, 1.258 registros no log de qualidade.

## Exercício 2024 — valores consolidados (R$ mil)

| Empresa (CD_CVM) | Métrica | Pipeline | Publicado | Resultado |
|---|---|---|---|---|
| WEG (5410) | Ativo Total | 41.489.701 | 41.489.701 | exato |
| WEG (5410) | Patrimônio Líquido | 23.125.217 | 23.125.217 | exato |
| WEG (5410) | Lucro Líquido | 6.318.763 | 6.318.763 | exato |
| Vale (4170) | Ativo Total | 496.325.000 | US$ 80.152 mi × PTAX 31/12/2024 6,1923 = R$ 496.325 mi | exato |
| Ambev (23264) | Lucro Líquido | 14.846.952 | R$ 14,8 bi | ok (arredondado) |
| Magazine Luiza (22470) | Lucro Líquido | 448.717 | R$ 448,7 mi | ok |
| Petrobras (9512) | Lucro Líquido | 37.009.000 | R$ 36,6 bi (atribuído aos controladores) | ok — ver nota |

**Nota Petrobras:** o valor divulgado na imprensa (R$ 36,6 bi) é o lucro
atribuído aos acionistas controladores (conta 3.11.01). O pipeline usa a
conta 3.11 — lucro consolidado do período, que inclui não controladores —
coerente com o Patrimônio Líquido consolidado (2.03), que também inclui
não controladores. Mesma convenção em todas as empresas.

Fontes:
- WEG: Demonstrações Financeiras 31/12/2025 e 2024, comparativo 2024 (RI WEG, api.mziq.com).
- Vale: Form 20-F FY2024, balanço consolidado em US$ (sec.gov); PTAX de fechamento 2024.
- Ambev: InfoMoney / CNN Brasil, resultados 4T24.
- Magazine Luiza: BPMoney, resultados 4T24.
- Petrobras: Agência Petrobras, "Petrobras lucra R$ 36,6 bilhões em 2024".

## Qualidade dos dados

| Etapa | Problema | Empresas-ano |
|---|---|---|
| filtro | setor financeiro | 1.155 |
| filtro | sem cadastro | 79 |
| filtro | ativo total nulo ou zero | 17 |
| filtro | layout não padrão | 5 |
| contas_base | conta ausente: fco | 1 |
| contas_base | conta ausente: caixa | 1 |

Distribuição: zonas Z — segura 2.207, risco 2.092, cinzenta 1.938,
indeterminada 29. Fleuriet — tipo II 2.315, I 1.052, V 951, III 854,
VI 680, IV 413. Efeito tesoura marcado em 929 empresas-ano.
Demonstrativo usado: consolidado 4.052, individual 2.214.

O universo inclui companhias abertas que só emitem dívida (sem ações
listadas); para análise de crédito elas são relevantes e foram mantidas.
