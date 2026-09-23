# Análise de Crédito de Companhias Abertas (CVM) — Design

**Data:** 2026-09-23
**Status:** aprovado em conversa, aguardando revisão da spec escrita

## 1. Objetivo

Projeto de portfólio que une contabilidade e dados: um pipeline em Python
transforma os demonstrativos financeiros públicos da CVM em um modelo
estrela, e um relatório Power BI apoia a análise de **risco de crédito**
das companhias abertas brasileiras não financeiras.

**Persona:** analista de crédito. Pergunta central: *"essa empresa
consegue honrar suas obrigações — e está melhorando ou piorando?"*

**Diferencial em relação ao projeto anterior (`contabilidade-web`):**
dados reais em vez de sintéticos, Power BI/DAX como produto principal,
e modelos de análise de crédito (Altman Z''-EM e Modelo Fleuriet).

## 2. Escopo

**Dentro:**
- Todas as companhias abertas **não financeiras** com DFP entregue.
- Exercícios **2015 a 2025**, apenas **anual (DFP)**.
- Apenas **contas fixas** do plano CVM (`ST_CONTA_FIXA = 'S'`).
- Demonstrações **consolidadas**; individuais como fallback.

**Fora (YAGNI nesta versão):**
- ITR / dados trimestrais e LTM.
- Dados de mercado (cotação, valor de mercado, dividendos).
- EBITDA (depreciação não é conta fixa).
- Bancos, seguradoras e demais instituições financeiras (layout de
  demonstrativo diferente).
- Fato em granularidade de conta contábil.

## 3. Fontes de dados

| Fonte | URL base | Uso |
|---|---|---|
| DFP anual | `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip` | BPA, BPP, DRE, DFC (MD e MI), versões `_con` e `_ind` |
| Cadastro | `https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv` | Setor (`SETOR_ATIV`), situação (`SIT`), CNPJ, nome |

Formato: CSV `;`, encoding `latin-1`. Colunas relevantes dos
demonstrativos: `CNPJ_CIA`, `CD_CVM`, `DENOM_CIA`, `DT_REFER`, `VERSAO`,
`ESCALA_MOEDA`, `ORDEM_EXERC`, `DT_FIM_EXERC`, `CD_CONTA`, `DS_CONTA`,
`VL_CONTA`, `ST_CONTA_FIXA`.

## 4. Arquitetura

```
CVM (ZIP/CSV) → extrair → limpar → contas_base → scores → exportar → Parquet → Power BI (.pbip)
```

Cada etapa é um módulo Python isolado em `pipeline/`, com entrada e saída
em DataFrames, testável sem rede. Orquestração por CLI:
`python -m pipeline run [--anos 2015-2025]`.

### 4.1 `extrair`
- Baixa os ZIPs de DFP de cada ano e o CSV de cadastro para `data/raw/`.
- Cache: não baixa de novo arquivo já presente (flag `--forcar` para
  rebaixar).
- Falha de rede: 3 tentativas com backoff; depois, erro claro indicando
  URL e ano.

### 4.2 `limpar`
Regras, nesta ordem:
1. **Reapresentação:** para cada (empresa, `DT_REFER`, demonstrativo),
   manter somente o maior `VERSAO`.
2. **Exercício:** manter somente `ORDEM_EXERC = 'ÚLTIMO'`.
3. **Escala:** `ESCALA_MOEDA = 'MIL'` → `VL_CONTA × 1000`; `UNIDADE`
   inalterado. Saída sempre em reais.
4. **Consolidado vs individual:** por (empresa, ano), usar `_con` se
   existir com dados; senão `_ind`. Registrar em coluna `tipo_demonstrativo`
   (`consolidado` | `individual`).
5. **Contas fixas:** manter somente `ST_CONTA_FIXA = 'S'`.
6. **Ano:** `ano = year(DT_FIM_EXERC)`.
7. **Exclusões:** empresas de setores financeiros (lista explícita de
   valores de `SETOR_ATIV` em configuração) e registros com Ativo Total
   nulo ou zero. Cada exclusão por dado inválido vai para o log de
   qualidade.

### 4.3 `contas_base`
Pivota para uma linha por (empresa, ano) com as colunas:

| Coluna | Código CVM |
|---|---|
| `ativo_total` | 1 |
| `ativo_circulante` | 1.01 |
| `caixa` | 1.01.01 |
| `aplicacoes_financeiras` | 1.01.02 |
| `estoques` | 1.01.04 |
| `ativo_nao_circulante` | 1.02 |
| `passivo_total` | 2 |
| `passivo_circulante` | 2.01 |
| `emprestimos_cp` | 2.01.04 |
| `passivo_nao_circulante` | 2.02 |
| `emprestimos_lp` | 2.02.01 |
| `patrimonio_liquido` | 2.03 (no consolidado inclui não controladores) |
| `reservas_lucros` | 2.03.04 |
| `lucros_acumulados` | 2.03.05 |
| `receita_liquida` | 3.01 |
| `ebit` | 3.05 |
| `despesas_financeiras` | 3.06.02 |
| `lucro_liquido` | 3.11 |
| `fco` | 6.01 |

Os códigos devem ser confirmados contra os arquivos reais na primeira
tarefa de implementação (há variações conhecidas de layout entre anos e
entre consolidado/individual, ex. PL consolidado). Divergências viram
mapeamento explícito em configuração, não lógica espalhada. Conta
ausente → `NaN` + registro no log de qualidade.

### 4.4 `scores`
**Altman Z''-EM** (valores contábeis, mercados emergentes):

```
X1 = (ativo_circulante − passivo_circulante) / ativo_total
X2 = (reservas_lucros + lucros_acumulados) / ativo_total
X3 = ebit / ativo_total
X4 = patrimonio_liquido / (passivo_circulante + passivo_nao_circulante)
Z  = 3,25 + 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4
```
Zonas: `Z > 5,85` segura · `4,15 ≤ Z ≤ 5,85` cinzenta · `Z < 4,15` risco.
Se algum componente for `NaN` ou passivo exigível = 0 → `Z = NaN`, zona
`indeterminada`.

**Modelo Fleuriet:**
```
CDG = (patrimonio_liquido + passivo_nao_circulante) − ativo_nao_circulante
T   = (caixa + aplicacoes_financeiras) − emprestimos_cp
NCG = CDG − T
```
Classificação pelos sinais de (CDG, NCG, T):

| Tipo | CDG | NCG | T | Situação |
|---|---|---|---|---|
| I | + | − | + | Excelente |
| II | + | + | + | Sólida |
| III | + | + | − | Insatisfatória |
| IV | − | + | − | Péssima |
| V | − | − | − | Muito ruim |
| VI | − | − | + | Alto risco |

Zero é tratado como positivo. Combinações impossíveis por construção não
ocorrem porque `NCG = CDG − T`.

**Efeito tesoura:** flag `True` quando, por dois anos consecutivos,
`ΔNCG > ΔCDG` (equivalente a `T` cair, já que `ΔT = ΔCDG − ΔNCG`).
Exige os dois anos anteriores com o mesmo tipo de demonstrativo
(consolidado/individual); sem histórico comparável → nulo (não
`False`), para que o painel não leia ausência de dado como ausência
de risco.

### 4.5 `exportar`
Grava em `data/processed/`:
- `fato_indicadores.parquet` — (cd_cvm, ano) + contas base + X1..X4, Z,
  zona, CDG, NCG, T, tipo Fleuriet, flag tesoura.
- `dim_empresa.parquet` — cd_cvm, cnpj, nome, setor, situação,
  tipo_demonstrativo mais recente.
- `dim_setor.parquet` — setor (texto limpo).
- `qualidade.parquet` — cd_cvm, ano, etapa, problema.

`dim_ano` é gerada no Power BI (tabela calculada). Execução idempotente:
reexecutar sobrescreve as saídas sem duplicar.

## 5. Modelo Power BI

Estrela com `fato_indicadores` ligada a `dim_empresa` (cd_cvm) e `dim_ano`
(ano), e `dim_setor` ligada a `dim_empresa` — relações 1:N,
filtro unidirecional. `qualidade` fica desconectada (página técnica).

### 5.1 Medidas DAX
- **Índices:** Liquidez Corrente, Liquidez Seca, Endividamento Geral,
  Dívida Líquida / PL, Cobertura de Juros (EBIT / despesas financeiras),
  Margem EBIT, Margem Líquida, ROA, ROE.
- **Divisão segura:** denominador zero → `BLANK()`; PL ≤ 0 em índices
  sobre PL → `BLANK()` com medida auxiliar de aviso.
- **Benchmark:** Mediana do Setor (`MEDIANX` sobre empresas do mesmo
  setor, removendo filtro de empresa), Percentil e Quartil da empresa no
  setor, Δ vs ano anterior.
- **Triagem:** contagem por zona, matriz de migração entre dois anos
  (ano base selecionável).
- Todas as medidas documentadas no dicionário de métricas
  (`docs/dicionario-metricas.md`).

### 5.2 Páginas
1. **Triagem de risco** — filtros ano/setor/zona; cartões por zona com Δ;
   matriz de migração; tabela ordenável (empresa, Z, zona, tipo Fleuriet,
   ΔZ, alerta tesoura) com drill-through para a ficha.
2. **Ficha da empresa** — cartões de índices com mediana do setor e
   quartil; linha do Z com bandas de zona; barras CDG/NCG/T por ano com
   tipo Fleuriet; tooltips com fórmula e direção de leitura.
3. **Panorama setorial** — mediana e quartis por setor; % de empresas em
   risco por setor ao longo do tempo.
4. **Qualidade dos dados** (técnica) — contagem de problemas por etapa e
   ano, empresas excluídas.

## 6. Estrutura do repositório

```
analise-credito-cvm/
├── pipeline/        # extrair, limpar, contas_base, scores, exportar, cli, config
├── tests/           # pytest + amostras pequenas montadas à mão
├── data/raw/        # gitignored
├── data/processed/  # gitignored
├── powerbi/         # projeto .pbip (TMDL + report)
├── docs/            # specs, planos, dicionário de métricas, screenshots
├── requirements.txt # versões fixadas
└── README.md
```

Ambiente: Python 3.13 fixado desde o início, `.venv` local,
`requirements.txt` com versões pinadas (pandas, duckdb, pyarrow,
requests, pytest).

## 7. Testes e verificação

1. **Unitários (pytest), sem rede:** amostras sintéticas cobrindo
   reapresentação (duas versões), escala MIL vs UNIDADE, empresa sem
   consolidado, conta ausente, cada um dos seis tipos Fleuriet, as três
   zonas do Z e o caso indeterminado, efeito tesoura.
2. **Conferência com dados reais:** 3–5 empresas conhecidas — Ativo Total,
   PL e Lucro Líquido do pipeline batem com a DFP publicada.
3. **Validação cruzada DAX × Python:** o pipeline gera valores de
   referência de índices para as empresas da conferência; via MCP do
   Power BI, conferir que as medidas retornam os mesmos valores.
4. **QA do relatório** (checklist) antes dos screenshots.

Nada é declarado pronto sem essas quatro verificações executadas.

## 8. Entrega

README com contexto de negócio (o que são Z''-EM e Fleuriet e como ler),
arquitetura, screenshots das páginas e instruções para rodar. Forma de
publicação (Publish to Web, vídeo ou apenas prints) decidida ao final.

## 9. Riscos conhecidos

- **Variação de códigos de conta** entre anos e entre consolidado e
  individual → verificar na primeira tarefa e centralizar em mapeamento.
- **Classificação setorial da CVM** é heterogênea → limpeza leve e lista
  explícita de setores financeiros em configuração.
- **Exercícios que não terminam em dezembro** → ano derivado de
  `DT_FIM_EXERC`, aceito como aproximação.
- **Z''-EM calibrado fora do Brasil** → apresentado como indicador de
  triagem, não como previsão; dito explicitamente no README.
- **Dois exercícios no mesmo ano civil** (troca de data de encerramento,
  ~6 empresas-ano): mantém-se o de fim mais recente; DRE pode cobrir
  período menor que 12 meses.
