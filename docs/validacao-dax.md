# Validação DAX × Python

Referência: índices recalculados por `pipeline/indices.py` sobre os Parquet
(o mesmo código que gera `docs/referencia_indices.csv`), agregados com pandas
quando a medida é setorial. A comparação é feita por
`python -m pipeline validar-dax <tipo> <csv>`, que lê o CSV gravado pelo
Power BI Modeling MCP (vírgula decimal, cultura pt-BR do modelo).
Tolerância relativa e absoluta de 1e-6; branco no DAX = NaN no Python.

## Resultados (2026-09-23)

| Verificação | Tipo | Linhas | Divergências |
|---|---|---|---|
| 9 índices + Z + zona + tipo Fleuriet, todas as empresas-ano | `indices` | 6.266 | 0 |
| Idem, recorte das 5 empresas de `referencia_indices.csv` | manual | 55 | 0 |
| Mediana, Q1 e Q3 do setor para os 10 índices, por setor-ano | `benchmark` | 279 × 30 colunas | 0 |
| Percentil no setor para os 10 índices, 2024 | `percentil` | 633 | 0 |
| Matriz de migração de zona 2024 → 2025 | `migracao` | 11 células | 0 |
| Matriz de migração 2015 → 2025, no formato do visual (com colunas de ordem), após o defeito 2 | `migracao` | 11 células | 0 |
| Contagens por zona, % em risco, % com efeito tesoura, qualidade | manual | — | 0 |
| Quartil e Δ vs ano anterior, WEG (5410) 2024, via `[Valor do Índice]` | manual | 70 | 0 |

Detalhe das checagens manuais:

- Zonas (todas as empresas-ano): segura 2.207, cinzenta 1.938, risco 2.092,
  indeterminada 29 — iguais a `docs/conferencia-dados-reais.md`.
- `% em Risco` = 0,335418 (2.092 / 6.237); `% com Efeito Tesoura` = 0,199778
  (898 / 4.495, nulos fora do denominador).
- `Problemas de Qualidade` 1.268; `Empresas Excluídas` 217; `Empresas` 830.
- `Δ Empresas vs Ano Anterior` na zona risco, 2025: −7 (pandas: −7).
- WEG 2024: mediana do setor (Máquinas, Equipamentos, Veículos e Peças) da
  Liquidez Corrente 1,386293 e do Z 5,093053, iguais ao `groupby` do pandas;
  `Δ vs Ano Anterior` do Z −0,569428 = Z 2024 − Z 2023 de
  `referencia_indices.csv`; quartis coerentes com os percentis
  (0,75 → 3; 0,93 → 4; 0,13 → 1).

## Defeito encontrado e corrigido

A primeira versão dos itens de benchmark iterava
`FILTER ( VALUES ( dim_empresa[cd_cvm] ), NOT ISBLANK ( SELECTEDMEASURE () ) )`
direto dentro de `MEDIANX`/`PERCENTILEX.INC`. Numa consulta isolada o valor
saía certo; na consulta com as 30 colunas, 94 valores divergiam. Exemplo:
Holdings Diversificadas 2015, mediana do ROA −0,0786 em vez de −0,2634, que é
exatamente a mediana com as 10 empresas do setor **sem dado naquele ano**
contadas como zero. O resultado dependia da forma da consulta, então o filtro
de branco não era confiável dentro da consulta fundida.

Correção: materializar o valor por empresa antes de agregar, iterando só as
empresas com linha no fato:

```dax
VAR _valores =
    CALCULATETABLE (
        FILTER (
            ADDCOLUMNS ( VALUES ( fato_indicadores[cd_cvm] ), "@v", SELECTEDMEASURE () ),
            NOT ISBLANK ( [@v] )
        ),
        REMOVEFILTERS ( dim_empresa ),
        REMOVEFILTERS ( dim_zona ),
        VALUES ( dim_empresa[setor] )
    )
RETURN MEDIANX ( _valores, [@v] )
```

Mesmo padrão em Q1, Q3, Percentil e Quartil. Depois da correção: 0
divergências em todas as verificações acima.

## Defeito 2: coluna de ordenação na matriz de migração (2026-09-28)

No relatório, a matriz de migração mostrava só a diagonal (74/54/81/1 para
2015 → 2025), embora a validação de 2024 → 2025 tivesse passado. A consulta
que o visual envia, capturada com trace, agrupa também por
`zona_origem[ordem_origem]` e `dim_zona[ordem]`, as colunas de "classificar
por coluna". `[Migração de Zona]` trocava só o filtro de `dim_zona[zona]`
pela zona de origem, e o filtro de `dim_zona[ordem]` do destino continuava
ativo, prendendo a origem à mesma zona do destino.

Correção: `REMOVEFILTERS ( dim_zona )` antes de `dim_zona[zona] = _origem`
(mesmo ajuste em `[% em Risco]`, por prevenção). Revalidado com a consulta no
formato do visual (com as colunas de ordem), 2015 → 2025: 11 células, 0
divergências.

**Regra:** consultas de validação de medidas que filtram colunas de uma
dimensão com "classificar por coluna" devem incluir a coluna de ordem no
agrupamento, como o visual faz.

## Consultas

### Índices (`indices`)

```dax
EVALUATE
SUMMARIZECOLUMNS (
    dim_empresa[cd_cvm],
    dim_ano[ano],
    "liquidez_corrente", [Liquidez Corrente],
    "liquidez_seca", [Liquidez Seca],
    "endividamento_geral", [Endividamento Geral],
    "divida_liquida_pl", [Dívida Líquida / PL],
    "cobertura_juros", [Cobertura de Juros],
    "margem_ebit", [Margem EBIT],
    "margem_liquida", [Margem Líquida],
    "roa", [ROA],
    "roe", [ROE],
    "z", [Z''-EM],
    "zona", [Zona],
    "tipo_fleuriet", [Tipo Fleuriet (nº)]
)
```

### Benchmark (`benchmark`)

```dax
EVALUATE
VAR _m = TREATAS ( { "Mediana do Setor" }, Benchmark[Comparação] )
VAR _q1 = TREATAS ( { "Q1 do Setor" }, Benchmark[Comparação] )
VAR _q3 = TREATAS ( { "Q3 do Setor" }, Benchmark[Comparação] )
RETURN
SUMMARIZECOLUMNS (
    dim_setor[setor],
    dim_ano[ano],
    "liquidez_corrente_mediana", CALCULATE ( [Liquidez Corrente], _m ),
    "liquidez_corrente_q1", CALCULATE ( [Liquidez Corrente], _q1 ),
    "liquidez_corrente_q3", CALCULATE ( [Liquidez Corrente], _q3 ),
    -- ... mesmo trio para liquidez_seca, endividamento_geral, divida_liquida_pl,
    -- cobertura_juros, margem_ebit, margem_liquida, roa, roe e z
    "z_q3", CALCULATE ( [Z''-EM], _q3 )
)
```
(A versão completa, com as 30 colunas, está na Task 4 do plano
`docs/superpowers/plans/2026-09-23-powerbi-relatorio.md`.)

### Percentil (`percentil --ano 2024`)

```dax
EVALUATE
VAR _p = TREATAS ( { "Percentil no Setor" }, Benchmark[Comparação] )
RETURN
SUMMARIZECOLUMNS (
    dim_empresa[cd_cvm],
    dim_ano[ano],
    TREATAS ( { 2024 }, dim_ano[ano] ),
    "liquidez_corrente_pct", CALCULATE ( [Liquidez Corrente], _p ),
    -- ... idem para os demais índices e o Z
    "z_pct", CALCULATE ( [Z''-EM], _p ),
    "_zona", [Zona]
)
```

### Migração (`migracao --ano 2025 --ano-base 2015`)

```dax
EVALUATE
SUMMARIZECOLUMNS (
    dim_zona[zona], dim_zona[ordem],
    zona_origem[zona_origem], zona_origem[ordem_origem],
    TREATAS ( { 2025 }, dim_ano[ano] ),
    TREATAS ( { 2015 }, ano_base[ano_base] ),
    "n", [Migração de Zona]
)
```
