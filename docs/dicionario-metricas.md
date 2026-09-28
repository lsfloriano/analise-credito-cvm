# Dicionário de métricas

Modelo: `powerbi/analise-credito-cvm.SemanticModel` (tabela `Medidas` e grupo
de cálculo `Benchmark`). Responsável: Leonardo Santiago Floriano.
Última revisão: 2026-09-23. A descrição de cada medida no modelo repete a
definição curta daqui. **Mudou uma medida? Atualize esta página no mesmo
commit.** O DAX completo está no TMDL (`definition/tables/Medidas.tmdl`,
`Benchmark.tmdl`); a validação contra o Python está em `docs/validacao-dax.md`.

Páginas: **T** = Triagem de risco · **F** = Ficha da empresa ·
**P** = Panorama setorial · **Q** = Qualidade dos dados.

## Regras que valem para todas as medidas de índice e score

- **Uma empresa-ano por vez.** Índices, Z, zona, Fleuriet e tesoura só
  retornam valor quando o contexto tem exatamente uma linha do fato
  (`COUNTROWS ( fato_indicadores ) = 1`). Num total ou numa linha de setor, o
  valor fica em branco de propósito: somar numeradores e denominadores de
  empresas diferentes não é um índice de ninguém. Para visões setoriais, use o
  grupo de cálculo `Benchmark`.
- **Divisão segura.** Denominador zero ou ausente → branco (`DIVIDE`).
- **PL ≤ 0** → ROE e Dívida Líquida/PL em branco (12,7% das empresas-ano),
  com texto em `[Aviso PL]`.
- **Receita líquida zero** → margens em branco (8,6% das empresas-ano; 56% em
  Holdings Diversificadas), com texto em `[Aviso Receita]`.
- **Valores em reais**, já convertidos da escala MIL pelo pipeline.
- **Consolidado quando existe**, individual como fallback
  (`dim_empresa[tipo_demonstrativo]`).
- Use sempre colunas de dimensão nos visuais (`dim_empresa`, `dim_ano`,
  `dim_setor`, `dim_zona`), nunca `fato_indicadores[cd_cvm]` ou `[ano]`.

## Índices (pasta Índices)

| Medida | Definição | Leitura | Brancos | Páginas |
|---|---|---|---|---|
| Liquidez Corrente | Ativo Circulante / Passivo Circulante | Maior é melhor; < 1 = o ativo de curto prazo não cobre o passivo de curto prazo | PC = 0 | F, P |
| Liquidez Seca | (Ativo Circulante − Estoques) / Passivo Circulante | Maior é melhor; liquidez sem depender de vender estoques | PC = 0 | F, P |
| Endividamento Geral | (Passivo Circulante + Passivo Não Circulante) / Ativo Total | Menor é melhor; parcela do ativo financiada por terceiros | AT = 0 | F, P |
| Dívida Líquida / PL | (Empréstimos CP + Empréstimos LP − Caixa − Aplicações) / PL | Menor é melhor; negativo = caixa líquido | PL ≤ 0; caixa ausente (1 empresa-ano) | F, P |
| Cobertura de Juros | EBIT / \|Despesas Financeiras\| | Maior é melhor; < 1x = o operacional não paga os juros | despesa financeira = 0 | F, P |
| Margem EBIT | EBIT / Receita Líquida | Maior é melhor | receita = 0 | F, P |
| Margem Líquida | Lucro Líquido / Receita Líquida | Maior é melhor | receita = 0 | F, P |
| ROA | Lucro Líquido / Ativo Total | Maior é melhor | AT = 0 | F, P |
| ROE | Lucro Líquido / PL | Maior é melhor | PL ≤ 0 | F, P |

Notas:

- **Cobertura de Juros usa `ABS`.** A DRE da CVM traz a despesa financeira
  negativa, mas 44 empresas-ano vêm com sinal positivo. `ABS` deixa as duas
  formas com o mesmo significado, igual ao pipeline.
- **EBIT de holdings** (conta 3.05) inclui o resultado de equivalência
  patrimonial. Por isso Cobertura de Juros e Margem EBIT de holdings não são
  comparáveis às de empresas operacionais.
- **Lucro Líquido** é a conta 3.11, o lucro consolidado do período, que
  inclui não controladores. É coerente com o PL consolidado (2.03), que
  também inclui. Por isso pode diferir do "lucro atribuído aos
  controladores" divulgado na imprensa (caso Petrobras em
  `docs/conferencia-dados-reais.md`).

DAX-padrão (exemplo; as demais seguem a mesma forma):

```dax
Liquidez Corrente =
IF ( COUNTROWS ( fato_indicadores ) = 1,
    DIVIDE ( SUM ( fato_indicadores[ativo_circulante] ), SUM ( fato_indicadores[passivo_circulante] ) ) )
```

## Scores (pasta Scores)

| Medida | Definição | Páginas |
|---|---|---|
| Z''-EM | Altman Z''-EM para mercados emergentes, calculado no pipeline: `3,25 + 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4`. X1 = capital de giro / AT; X2 = (reservas de lucros + lucros acumulados) / AT; X3 = EBIT / AT; X4 = PL / passivo exigível. **Triagem, não previsão**: o modelo foi calibrado fora do Brasil. | T, F |
| Zona | segura (Z > 5,85), cinzenta (4,15 ≤ Z ≤ 5,85), risco (Z < 4,15), indeterminada (componente ausente ou passivo exigível zero, 29 empresas-ano) | T, F |
| Δ Z''-EM | Z do ano − Z do ano anterior, mesma empresa; branco sem ano anterior | T |
| Z''-EM (exibição) | O Z preso entre −25 e +25, para gráficos, ícones e ordenação. Fora da faixa aparece como "< -25" ou "> 25" (formato dinâmico). 434 empresas-ano (7%; 33 em 2025) estão fora, em geral por ativo irrisório (ex.: ativo de R$ 86) ou passivo exigível quase zero, que fazem os X explodirem. Zona e medianas usam o Z real | T, F |
| Δ Z''-EM (exibição) | Δ Z só quando o Z do ano e o do anterior estão dentro de ±25; em branco se faltar o ano anterior **ou** se algum estiver fora da escala (um Δ de −5.643 não informa nada) | T |
| Tipo Fleuriet | "I - Excelente" … "VI - Alto risco", pelos sinais de (CDG, NCG, T); zero conta como positivo | T, F |
| Tipo Fleuriet (nº) | *Auxiliar, oculta.* O tipo de 1 a 6, usado na validação | — |
| Limite Risco / Limite Segura | Constantes 4,15 e 5,85, para as linhas de referência do gráfico do Z | F |

## Fleuriet (pasta Fleuriet)

| Medida | Definição | Páginas |
|---|---|---|
| CDG | Capital de Giro = (PL + Passivo Não Circulante) − Ativo Não Circulante. Recursos de longo prazo que sobram para financiar o giro | F |
| NCG | Necessidade de Capital de Giro = CDG − T | F |
| Saldo de Tesouraria | T = (Caixa + Aplicações Financeiras) − Empréstimos CP | F |
| Efeito Tesoura | "alerta" quando, por dois anos seguidos, ΔNCG > ΔCDG (T caindo); "não"; ou **"sem histórico"** quando faltam os dois anos anteriores com o mesmo tipo de demonstrativo. *Sem histórico não é ausência de risco.* | T, F |

## Benchmark (pasta Benchmark e grupo de cálculo `Benchmark`)

| Medida | Definição | Páginas |
|---|---|---|
| Valor do Índice | O índice escolhido em `dim_indice[indice]`: um seletor que troca a medida (SWITCH). Formato vem de `dim_indice[formato]` | F, P |
| Fórmula do Índice | Fórmula do índice escolhido, para tooltip | F |
| Leitura do Índice | Direção de leitura (maior/menor é melhor) e ressalvas do índice escolhido, para tooltip | F |

Itens do grupo de cálculo `Benchmark[Comparação]`, que se aplicam a qualquer
medida de índice ou score:

| Item | O que faz com a medida | Observações |
|---|---|---|
| Valor | Nada: a própria medida | |
| Mediana do Setor | Mediana da medida entre as empresas do **mesmo setor** no mesmo ano | Ignora filtros de empresa e de zona; mantém setor e ano. Empresas com a medida em branco ficam fora. |
| Q1 do Setor / Q3 do Setor | 1º e 3º quartis (`PERCENTILEX.INC` 0,25 e 0,75, interpolação linear) | Idem |
| Percentil no Setor | Fração das empresas do setor com valor **menor ou igual** ao da empresa (0–100%) | Empates contam a favor da empresa |
| Quartil no Setor | 1 (valores mais baixos) a 4 (mais altos), = ⌈percentil × 4⌉ | **Não** diz se é bom: para Endividamento e Dívida Líquida/PL, quartil 1 é o melhor. Ver `[Leitura do Índice]`. |
| Δ vs Ano Anterior | Valor do ano − valor do ano anterior, mesmo contexto | Para índices em %, o resultado está em pontos percentuais |

Implementação: os itens setoriais montam primeiro uma tabela
(empresa → valor) só com as empresas que têm linha no fato, e depois agregam
(`MEDIANX`/`PERCENTILEX.INC` sobre ela). A forma direta, iterando
`dim_empresa`, dava resultado errado numa consulta com muitas colunas; o
caso está documentado em `docs/validacao-dax.md`.

## Triagem (pasta Triagem)

| Medida | Definição | Páginas |
|---|---|---|
| Empresas | Empresas distintas no contexto | T, P |
| Empresas-Ano | Linhas empresa-ano no contexto | — |
| Δ Empresas vs Ano Anterior | Empresas no ano − empresas no ano anterior, mesmo filtro (ex.: cartão da zona risco). Mistura migração de zona com entrada e saída de empresas do universo | T |
| % em Risco | Empresas-ano na zona risco / empresas-ano com Z calculado. A zona indeterminada fica fora do denominador | P |
| % com Efeito Tesoura | Empresas-ano com alerta / empresas-ano com histórico comparável. **Nulos fora do denominador** (1.771 empresas-ano sem histórico) | T |
| Migração de Zona | Empresas que estavam na zona da linha (`zona_origem`) no ano de `ano_base` e estão na zona da coluna (`dim_zona`) no ano selecionado. Só conta empresas presentes nos dois anos | T |
| Cor da Zona | Hexadecimal da zona (segura #2E7D32, cinzenta #F9A825, risco #C62828, indeterminada #9E9E9E), para formatação condicional | T, F |

## Avisos (pasta Avisos)

| Medida | Quando aparece | Páginas |
|---|---|---|
| Aviso PL | PL ≤ 0 na empresa-ano | F |
| Aviso Receita | Receita líquida = 0 na empresa-ano | F |
| Fora da Escala | "Z real: …" quando \|Z\| > 25 (para a coluna ou tooltip ao lado de `[Z''-EM (exibição)]`) | T, F |
| Nota Metodológica | Sempre: triagem, não previsão; dupla contagem controladora/controladas | T, P |

## Qualidade (pasta Qualidade)

| Medida | Definição | Páginas |
|---|---|---|
| Problemas de Qualidade | Registros no log de qualidade do pipeline (`qualidade`, tabela desconectada) | Q |
| Empresas Excluídas | Empresas distintas excluídas na etapa `filtro`: setor financeiro, sem cadastro, ativo total nulo ou zero, layout não padrão | Q |

## Limitações

- **Dupla contagem nas medianas setoriais.** Controladoras (consolidado) e
  controladas listadas aparecem como empresas separadas. Os dados da CVM
  usados aqui não trazem a relação de controle, por isso não há filtro; o
  aviso está em `[Nota Metodológica]`.
- **Holdings:** EBIT com equivalência patrimonial e receita frequentemente
  zero.
- **Efeito tesoura nulo ≠ sem risco.**
- **Dois exercícios no mesmo ano civil** (~6 empresas-ano): vale o de fim mais
  recente, e a DRE pode cobrir menos de 12 meses.
