# Pendências herdadas pelo Plano B (Power BI e entrega)

Status em 2026-09-29: todas tratadas (✔) ou deixadas fora de escopo de
propósito (➖), com o registro abaixo.

## Decisões já tomadas (2026-09-23)
- **Divisão de trabalho:** o modelo semântico (Power Query dos Parquet, relações, `dim_ano`, medidas DAX, dicionário de métricas, validação DAX × `docs/referencia_indices.csv`) é construído e validado pelo Claude via Power BI Modeling MCP. Os **visuais das 4 páginas** são montados pelo Leonardo no Power BI Desktop, seguindo um roteiro página a página escrito pelo Claude, com revisão por print.
- MCP registrado no escopo local deste projeto, com o argumento `--start`. Abra o Claude Code a partir desta pasta.

Levantadas na revisão final do pipeline (2026-09-23).

## Contrato de dados para o DAX
- ✔ `despesas_financeiras` vem negativa na DRE, mas 44 empresas-ano têm valor positivo → `[Cobertura de Juros]` usa `ABS`, e bate com o Python em todas as empresas-ano (`docs/validacao-dax.md`).
- ✔ 8,6% das empresas-ano têm `receita_liquida = 0` → margens em branco e `[Aviso Receita]` na ficha.
- ✔ 12,7% das empresas-ano têm PL ≤ 0 → ROE e Dívida Líquida/PL em branco, com `[Aviso PL]` na ficha.
- ✔ EBIT (`3.05`) de holdings inclui equivalência patrimonial → ressalva em `dim_indice[leitura]` (dica da ficha), no dicionário e no README.
- ✔ Controladora e controladas juntas → decidido **aviso, sem filtro** (os dados não trazem a relação de controle): `[Nota Metodológica]` nas páginas Triagem e Panorama, dicionário e README.
- ✔ `efeito_tesoura` anulável → `[Efeito Tesoura]` mostra "sem histórico"; `[% com Efeito Tesoura]` tira os nulos do denominador (898 / 4.495 = 19,98%, validado).

## Entrega
- ✔ README (spec §8): contexto de negócio, arquitetura, como rodar, prints, verificação.
- ✔ O README avisa sobre `--anos` parcial e sobre os dois exercícios no mesmo ano civil (seção "Limitações conhecidas").
- ➖ Fallback por CNPJ no cadastro (Multilaser): fora desta versão, por afetar 1 empresa. Registrado nas limitações do README.

## Achados durante o Plano B
- ✔ Z extremo (|Z| > 25 em 434 empresas-ano, ativo irrisório ou passivo exigível quase zero) → medidas de exibição limitadas a ±25; o Z real define a zona e as medianas.
- ✔ Nome duplicado no cadastro (PRIO FORTE S.A., 23493 e 27740) → rótulo `dim_empresa[empresa]` = "nome (cd_cvm)".
- ✔ Defeitos de DAX encontrados pela validação (benchmark numa consulta fundida; coluna de ordenação na migração) → corrigidos e documentados em `docs/validacao-dax.md`.
