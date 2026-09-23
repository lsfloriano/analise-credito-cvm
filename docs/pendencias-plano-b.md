# Pendências herdadas pelo Plano B (Power BI e entrega)

## Decisões já tomadas (2026-09-23)
- **Divisão de trabalho:** o modelo semântico (Power Query dos Parquet, relações, `dim_ano`, medidas DAX, dicionário de métricas, validação DAX × `docs/referencia_indices.csv`) é construído e validado pelo Claude via Power BI Modeling MCP. Os **visuais das 4 páginas** são montados pelo Leonardo no Power BI Desktop, seguindo um roteiro página a página escrito pelo Claude, com revisão por print.
- MCP registrado no escopo local deste projeto, com o argumento `--start`. Abra o Claude Code a partir desta pasta.

Levantadas na revisão final do pipeline (2026-09-23). O Plano B deve tratar cada item.

## Contrato de dados para o DAX
- `despesas_financeiras` vem negativa na DRE, mas 44 empresas-ano têm valor positivo. `pipeline/indices.py` usa `abs()`; a medida de Cobertura de Juros precisa usar `ABS` para bater com `docs/referencia_indices.csv`.
- 8,6% das empresas-ano têm `receita_liquida = 0` (56% em "Holdings Diversificadas") → margens em branco.
- 12,7% das empresas-ano têm PL ≤ 0 → ROE e Dívida Líquida/PL em branco, com aviso.
- EBIT (`3.05`) de holdings inclui resultado de equivalência patrimonial.
- Controladora (consolidado) e controladas listadas aparecem juntas → dupla contagem nas medianas setoriais. Decidir: filtro opcional ou aviso na página.
- `efeito_tesoura` é booleano anulável: nulo = sem histórico comparável (não é "sem risco"). A "% com alerta" deve usar só os não nulos no denominador.

## Entrega
- README (spec §8): contexto de negócio, arquitetura, como rodar, prints.
- README deve avisar: `--anos` parcial sobrescreve as saídas completas; dois exercícios no mesmo ano civil (~6 empresas-ano) mantêm o mais recente.
- Opcional: fallback por CNPJ no cadastro (Multilaser: CD_CVM 902123 na DFP vs 26034 no cadastro; os outros 19 "sem cadastro" são emissores estrangeiros).
