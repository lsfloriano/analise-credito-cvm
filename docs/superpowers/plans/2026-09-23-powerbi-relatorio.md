# Relatório Power BI de Crédito (Plano B) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar os Parquet do pipeline num modelo semântico Power BI (PBIP) validado contra o Python, num relatório de 4 páginas e num README de portfólio.

**Architecture:** O modelo é construído **ao vivo** no Power BI Desktop aberto, via Power BI Modeling MCP (testado em 2026-09-23: criar tabela M + refresh + consulta DAX funcionam na instância local). O Desktop grava o PBIP (TMDL) em `powerbi/` a cada Ctrl+S. A validação DAX × Python é automatizada: o MCP grava o resultado de cada consulta DAX em CSV, e um novo módulo `pipeline/validacao.py` compara esse CSV com os índices recalculados pelo Python sobre **todas** as 6.266 empresas-ano (não só as 5 da conferência). Os visuais são montados pelo Leonardo seguindo `docs/roteiro-visuais.md`.

**Tech Stack:** Power BI Desktop (PBIP/TMDL), Power Query M (`Parquet.Document`), DAX (grupo de cálculo, `MEDIANX`, `PERCENTILEX.INC`), Python 3.13 + pandas 3.0.6 + pytest 9.1.1.

**Spec:** `docs/superpowers/specs/2026-09-23-analise-credito-cvm-design.md` (§5, §7, §8) e `docs/pendencias-plano-b.md`.

## Global Constraints

- Divisão de trabalho: modelo, DAX, dicionário e validação → Claude via MCP. **Visuais → Leonardo**, pelo roteiro, com revisão por print.
- Relações 1:N, filtro **unidirecional**; `qualidade` desconectada.
- Divisão segura: denominador zero → `BLANK()`; PL ≤ 0 em índices sobre PL → `BLANK()` com medida de aviso.
- `despesas_financeiras` entra com `ABS` na Cobertura de Juros.
- `efeito_tesoura` nulo = sem histórico comparável; o denominador da "% com alerta" usa só os não nulos.
- Visuais usam **colunas de dimensão** (`dim_empresa`, `dim_ano`, `dim_setor`, `dim_zona`), nunca `fato_indicadores[cd_cvm]`/`[ano]`: o filtro de fato não sobe para as dimensões, e as medidas de benchmark leem o setor em `dim_empresa`.
- Rótulo de empresa nos visuais: `dim_empresa[empresa]` = `nome (cd_cvm)`. Há um nome duplicado (PRIO FORTE S.A., CD_CVM 23493 e 27740).
- Nada é declarado pronto sem as 4 verificações da spec §7 executadas.
- Python: sempre `.venv/Scripts/python`; console cp1252 → `print` só com ASCII.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (ou o modelo que executou).
- Branch: `feat/powerbi`, criada a partir de `main` na pasta do projeto, sem worktree: o Desktop precisa abrir o PBIP no caminho real.

## Decisões deste plano (pendências resolvidas)

| Pendência | Decisão |
|---|---|
| Dupla contagem controladora/controladas | **Aviso**, sem filtro. Os dados não trazem a relação de controle, então um filtro exigiria um mapeamento manual fora do escopo. Medida `[Nota Metodológica]` num cartão de texto nas páginas 1 e 3. |
| EBIT de holdings com equivalência | Aviso na coluna `leitura` de `dim_indice` (Cobertura de Juros, Margem EBIT) e no dicionário. |
| Receita = 0 / PL ≤ 0 | Medidas `[Aviso Receita]` e `[Aviso PL]` na ficha. |
| Fallback por CNPJ (Multilaser) | **Fora** desta versão (1 empresa). Registrado no README como limitação conhecida. |
| Agregação dos índices | Cada índice só é calculado em contexto de **uma empresa-ano** (`COUNTROWS(fato_indicadores) = 1`). Visões setoriais usam os itens do grupo de cálculo (mediana, quartis), nunca razão de somas. |

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `powerbi/analise-credito-cvm.pbip` + `.SemanticModel/` + `.Report/` | Projeto Power BI (gerado pelo Desktop). |
| `pipeline/validacao.py` | Lê o CSV do MCP e compara com as referências do Python. |
| `pipeline/cli.py` | Novo subcomando `validar-dax`. |
| `tests/test_validacao.py` | Testes da comparação. |
| `docs/validacao-dax.md` | Registro das consultas DAX e dos resultados da comparação. |
| `docs/dicionario-metricas.md` | Dicionário de métricas (spec §5.1). |
| `docs/roteiro-visuais.md` | Roteiro página a página para o Leonardo. |
| `docs/screenshots/*.png` | Prints das 4 páginas. |
| `README.md` | Entrega (spec §8). |

## Convenções de MCP

- Conexão: `connection_operations` → `ListLocalInstances` → `Connect` com a `connectionString` retornada. Reconectar se o Desktop for reaberto (a porta muda).
- Resultado de `dax_query_operations` `Execute` vem como caminho de CSV em `%TEMP%\PowerBIModelingMCP\QueryResults\`. Cabeçalhos no formato `tabela[coluna]` ou `[alias]`. Passe `maxRows: 10000`.
- Depois de cada tarefa de modelo: pedir ao Leonardo **Ctrl+S** no Desktop, conferir `git status` em `powerbi/` e commitar.
- As tarefas 1–5 rodam na sessão principal (os agentes `implementer`/`task-reviewer` não têm as ferramentas do MCP). A Task 2 (Python) pode ir para o `implementer`.

---

### Task 0: Branch e PBIP vazio (Leonardo + Claude)

**Files:**
- Create: `powerbi/analise-credito-cvm.pbip` (via Desktop)

- [ ] **Step 1: Criar a branch**

```bash
git checkout -b feat/powerbi
```

- [ ] **Step 2: Leonardo salva o arquivo aberto como PBIP**

No Desktop: *Arquivo → Opções → Recursos de visualização*: confirmar **"Salvar como Projeto do Power BI (.pbip)"** e **"Armazenar modelo semântico usando o formato TMDL"** marcados (se não aparecerem, já são padrão). *Arquivo → Salvar como* → `C:\Users\LeonardoSantiagoFlor\projects\analise-credito-cvm\powerbi\analise-credito-cvm.pbip`.

- [ ] **Step 3: Conferir a estrutura e reconectar o MCP**

```bash
ls powerbi powerbi/analise-credito-cvm.SemanticModel/definition
git status --short powerbi
```
Esperado: `analise-credito-cvm.pbip`, `analise-credito-cvm.SemanticModel/definition/database.tmdl`, `model.tmdl`, nada em `.pbi/cache.abf` no status (gitignored). Depois, `ListLocalInstances` → `Connect` (o título da janela agora é `analise-credito-cvm`).

- [ ] **Step 4: Commit**

```bash
git add powerbi
git commit -m "feat: projeto Power BI vazio (PBIP/TMDL)"
```

---

### Task 1: Fonte de dados, tabelas Power Query, dimensões calculadas e relações

**Files:**
- Modify: `powerbi/analise-credito-cvm.SemanticModel/definition/**` (via MCP + Ctrl+S)

**Interfaces:**
- Produces: tabelas `fato_indicadores`, `dim_empresa` (+ coluna `empresa`), `dim_setor`, `qualidade`, `dim_ano`, `ano_base`, `dim_zona`, `zona_origem`, `dim_indice`, `Medidas`; parâmetro `PastaDados`. Nomes de colunas iguais aos do Parquet.

- [ ] **Step 1: Parâmetro `PastaDados`** (`named_expression_operations` → `CreateParameter`)

```json
{"operation": "CreateParameter", "definitions": [{"name": "PastaDados", "kind": "M",
  "description": "Pasta com os Parquet gerados por python -m pipeline run (termina em barra invertida).",
  "expression": "\"C:\\Users\\LeonardoSantiagoFlor\\projects\\analise-credito-cvm\\data\\processed\\\" meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]"}]}
```

- [ ] **Step 2: Tabelas de importação** (`table_operations` → `Create`, `mode: Import`)

Cada tabela usa esta expressão M, trocando o arquivo:

```m
let
    Fonte = Parquet.Document(File.Contents(PastaDados & "fato_indicadores.parquet"))
in
    Fonte
```

Colunas (`dataType`; todas `isNullable: true`; `summarizeBy: None` em todas as numéricas):

| Tabela | Arquivo | Colunas |
|---|---|---|
| `fato_indicadores` | `fato_indicadores.parquet` | `cd_cvm` Int64 (oculta), `ano` Int64 (oculta), `tipo_demonstrativo` String, `ativo_total`, `ativo_circulante`, `caixa`, `aplicacoes_financeiras`, `estoques`, `ativo_nao_circulante`, `passivo_total`, `passivo_circulante`, `emprestimos_cp`, `passivo_nao_circulante`, `emprestimos_lp`, `patrimonio_liquido`, `reservas_lucros`, `lucros_acumulados`, `receita_liquida`, `ebit`, `despesas_financeiras`, `lucro_liquido`, `fco`, `x1`, `x2`, `x3`, `x4`, `z`, `cdg`, `t`, `ncg` Double, `zona` String (oculta, usar `dim_zona`), `tipo_fleuriet` Int64, `situacao_fleuriet` String, `efeito_tesoura` Boolean |
| `dim_empresa` | `dim_empresa.parquet` | `cd_cvm` Int64 (oculta), `cnpj`, `nome`, `setor` (oculta, usar `dim_setor`), `situacao`, `tipo_demonstrativo` String |
| `dim_setor` | `dim_setor.parquet` | `setor` String |
| `qualidade` | `qualidade.parquet` | `cd_cvm` Int64, `nome` String, `ano` Int64, `etapa` String, `problema` String |

Coluna calculada em `dim_empresa` (`column_operations` → `Create`):

```dax
empresa = dim_empresa[nome] & " (" & dim_empresa[cd_cvm] & ")"
```

- [ ] **Step 3: Tabelas calculadas** (`table_operations` → `Create` com `daxExpression`)

```dax
dim_ano = SELECTCOLUMNS ( GENERATESERIES ( MIN ( fato_indicadores[ano] ), MAX ( fato_indicadores[ano] ), 1 ), "ano", [Value] )

ano_base = SELECTCOLUMNS ( dim_ano, "ano_base", dim_ano[ano] )

dim_zona = DATATABLE ( "zona", STRING, "ordem", INTEGER,
    { { "segura", 1 }, { "cinzenta", 2 }, { "risco", 3 }, { "indeterminada", 4 } } )

zona_origem = SELECTCOLUMNS ( dim_zona, "zona_origem", dim_zona[zona], "ordem_origem", dim_zona[ordem] )

Medidas = ROW ( "_", BLANK () )

dim_indice = DATATABLE (
    "ordem", INTEGER, "indice", STRING, "formato", STRING, "formula", STRING, "leitura", STRING,
    {
        { 1, "Liquidez Corrente", "0.00", "Ativo Circulante / Passivo Circulante",
          "Maior é melhor. Abaixo de 1, o ativo de curto prazo não cobre o passivo de curto prazo." },
        { 2, "Liquidez Seca", "0.00", "(Ativo Circulante - Estoques) / Passivo Circulante",
          "Maior é melhor. Liquidez sem depender da venda dos estoques." },
        { 3, "Endividamento Geral", "0.0%", "(Passivo Circulante + Passivo Não Circulante) / Ativo Total",
          "Menor é melhor. Parcela do ativo financiada por terceiros." },
        { 4, "Dívida Líquida / PL", "0.00", "(Empréstimos CP + Empréstimos LP - Caixa - Aplicações) / PL",
          "Menor é melhor. Negativo indica caixa líquido. Em branco se PL <= 0." },
        { 5, "Cobertura de Juros", "0.0""x""", "EBIT / |Despesas Financeiras|",
          "Maior é melhor. Abaixo de 1x, o resultado operacional não paga os juros. Em holdings o EBIT inclui equivalência patrimonial." },
        { 6, "Margem EBIT", "0.0%", "EBIT / Receita Líquida",
          "Maior é melhor. Em branco se a receita for zero (comum em holdings). Em holdings o EBIT inclui equivalência patrimonial." },
        { 7, "Margem Líquida", "0.0%", "Lucro Líquido / Receita Líquida",
          "Maior é melhor. Em branco se a receita for zero." },
        { 8, "ROA", "0.0%", "Lucro Líquido / Ativo Total", "Maior é melhor." },
        { 9, "ROE", "0.0%", "Lucro Líquido / PL", "Maior é melhor. Em branco se PL <= 0." },
        { 10, "Z''-EM", "0.00", "3,25 + 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4",
          "Maior é melhor. Acima de 5,85 segura; 4,15 a 5,85 cinzenta; abaixo de 4,15 risco. Indicador de triagem, não previsão." }
    }
)
```

Se a relação `fato_indicadores[ano] → dim_ano[ano]` (Step 4) acusar dependência circular por causa do `MIN`/`MAX`, troque por `GENERATESERIES ( 2015, 2025, 1 )` e registre no README que o intervalo segue `config.ANOS_PADRAO`.

Ajustes de coluna (`column_operations` → `Update`): `dim_zona[zona]` sortBy `ordem`; `zona_origem[zona_origem]` sortBy `ordem_origem`; `dim_indice[indice]` sortBy `ordem`; ocultar `dim_zona[ordem]`, `zona_origem[ordem_origem]`, `dim_indice[ordem]`, `dim_indice[formato]`, `Medidas[_]`. `summarizeBy: None` em `dim_ano[ano]` e `ano_base[ano_base]`.

- [ ] **Step 4: Relações** (`relationship_operations` → `Create`, todas `fromCardinality: Many`, `toCardinality: One`, `crossFilteringBehavior: OneDirection`)

| from | to |
|---|---|
| `fato_indicadores[cd_cvm]` | `dim_empresa[cd_cvm]` |
| `fato_indicadores[ano]` | `dim_ano[ano]` |
| `fato_indicadores[zona]` | `dim_zona[zona]` |
| `dim_empresa[setor]` | `dim_setor[setor]` |

- [ ] **Step 5: Refresh e conferência**

Refresh de `fato_indicadores`, `dim_empresa`, `dim_setor`, `qualidade` (as calculadas recalculam em seguida; se não, refresh `Calculate` nelas). Depois, execute:

```dax
EVALUATE
ROW (
    "fato", COUNTROWS ( fato_indicadores ),
    "empresas", COUNTROWS ( dim_empresa ),
    "setores", COUNTROWS ( dim_setor ),
    "qualidade", COUNTROWS ( qualidade ),
    "anos", COUNTROWS ( dim_ano ),
    "fato_sem_empresa", COUNTROWS ( FILTER ( fato_indicadores, ISBLANK ( RELATED ( dim_empresa[nome] ) ) ) ),
    "fato_sem_zona", COUNTROWS ( FILTER ( fato_indicadores, ISBLANK ( RELATED ( dim_zona[ordem] ) ) ) ),
    "empresa_sem_setor", COUNTROWS ( FILTER ( dim_empresa, ISBLANK ( RELATED ( dim_setor[setor] ) ) ) ),
    "tesoura_nula", COUNTROWS ( FILTER ( fato_indicadores, ISBLANK ( fato_indicadores[efeito_tesoura] ) ) ),
    "acento", LOOKUPVALUE ( dim_empresa[setor], dim_empresa[cd_cvm], 701 )
)
```
Esperado: `fato` 6266, `empresas` 830, `setores` 26, `qualidade` 1268, `anos` 11, os três "sem" = 0, `tesoura_nula` 1771, `acento` = `Educação`.

- [ ] **Step 6: Leonardo Ctrl+S; commit**

```bash
git add powerbi
git commit -m "feat: tabelas Power Query dos Parquet, dimensões calculadas e relações"
```

---

### Task 2: Módulo de validação DAX × Python (TDD, pode ir ao `implementer`)

**Files:**
- Create: `pipeline/validacao.py`
- Modify: `pipeline/cli.py` (subcomando `validar-dax`)
- Test: `tests/test_validacao.py`

**Interfaces:**
- Consumes: `pipeline.indices.calcular_indices(fato) -> DataFrame[cd_cvm, ano, *INDICES]`, `pipeline.indices.INDICES`.
- Produces:
  - `ler_resultado_dax(caminho) -> DataFrame` (cabeçalhos `tab[col]`/`[alias]` → `col`/`alias`)
  - `comparar(dax, ref, chaves, colunas, tol=1e-6) -> DataFrame[*chaves, coluna, dax, ref]` (vazio = tudo bate)
  - `referencia_indices(fato) -> DataFrame[cd_cvm, ano, *INDICES, z, zona, tipo_fleuriet]`
  - `referencia_benchmark(fato, empresas) -> DataFrame[setor, ano, {col}_mediana, {col}_q1, {col}_q3]` para `col` em `[*INDICES, "z"]`
  - `referencia_percentil(fato, empresas, ano) -> DataFrame[cd_cvm, ano, {col}_pct]`
  - `referencia_migracao(fato, ano_base, ano) -> DataFrame[zona, zona_origem, n]`
  - CLI: `python -m pipeline validar-dax {indices|benchmark|percentil|migracao} CSV [--ano N] [--ano-base N]`, sai 0 se bate, 1 se diverge.

- [ ] **Step 1: Testes que falham** — `tests/test_validacao.py`

```python
import math

import pandas as pd
import pytest

from pipeline import validacao


def test_ler_resultado_dax_normaliza_cabecalhos(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("dim_empresa[cd_cvm],dim_ano[ano],[liquidez_corrente]\n10,2024,1.5\n", encoding="utf-8-sig")
    df = validacao.ler_resultado_dax(p)
    assert list(df.columns) == ["cd_cvm", "ano", "liquidez_corrente"]
    assert df.iloc[0]["liquidez_corrente"] == 1.5


def _par(dax_val, ref_val):
    dax = pd.DataFrame({"cd_cvm": [1], "ano": [2024], "x": [dax_val]})
    ref = pd.DataFrame({"cd_cvm": [1], "ano": [2024], "x": [ref_val]})
    return validacao.comparar(dax, ref, ["cd_cvm", "ano"], ["x"])


def test_comparar_iguais_dentro_da_tolerancia():
    assert _par(1.0000000001, 1.0).empty


def test_comparar_nulo_dos_dois_lados_bate():
    assert _par(float("nan"), float("nan")).empty


def test_comparar_nulo_de_um_lado_diverge():
    d = _par(float("nan"), 2.0)
    assert len(d) == 1 and d.iloc[0]["coluna"] == "x"


def test_comparar_valor_diferente_diverge():
    assert len(_par(1.1, 1.0)) == 1


def test_comparar_texto():
    dax = pd.DataFrame({"k": [1, 2], "zona": ["risco", "segura"]})
    ref = pd.DataFrame({"k": [1, 2], "zona": ["risco", "cinzenta"]})
    d = validacao.comparar(dax, ref, ["k"], ["zona"])
    assert d["k"].tolist() == [2]


def test_comparar_linha_faltando_diverge():
    dax = pd.DataFrame({"k": [1], "x": [1.0]})
    ref = pd.DataFrame({"k": [1, 2], "x": [1.0, 2.0]})
    d = validacao.comparar(dax, ref, ["k"], ["x"])
    assert d["coluna"].tolist() == ["(linha)"]


def _fato():
    base = dict(ativo_total=100.0, ativo_circulante=50.0, estoques=0.0, passivo_circulante=25.0,
                passivo_nao_circulante=25.0, patrimonio_liquido=50.0, caixa=0.0,
                aplicacoes_financeiras=0.0, emprestimos_cp=0.0, emprestimos_lp=0.0,
                receita_liquida=100.0, ebit=10.0, despesas_financeiras=-5.0, lucro_liquido=5.0,
                z=5.0, zona="cinzenta", tipo_fleuriet=2)
    linhas = []
    for cd, ac, zona24, zona25 in [(1, 50.0, "risco", "risco"), (2, 75.0, "risco", "segura"),
                                   (3, 100.0, "segura", "segura")]:
        for ano, zona in [(2024, zona24), (2025, zona25)]:
            linhas.append({**base, "cd_cvm": cd, "ano": ano, "ativo_circulante": ac, "zona": zona})
    return pd.DataFrame(linhas)


EMPRESAS = pd.DataFrame({"cd_cvm": [1, 2, 3], "setor": ["A", "A", "A"]})


def test_referencia_indices_traz_scores():
    r = validacao.referencia_indices(_fato())
    assert {"liquidez_corrente", "z", "zona", "tipo_fleuriet"} <= set(r.columns)
    assert len(r) == 6


def test_referencia_benchmark_mediana_e_quartis():
    r = validacao.referencia_benchmark(_fato(), EMPRESAS)
    linha = r[(r["setor"] == "A") & (r["ano"] == 2024)].iloc[0]
    # liquidez corrente = 2, 3, 4
    assert linha["liquidez_corrente_mediana"] == pytest.approx(3.0)
    assert linha["liquidez_corrente_q1"] == pytest.approx(2.5)
    assert linha["liquidez_corrente_q3"] == pytest.approx(3.5)


def test_referencia_percentil_conta_menores_ou_iguais():
    r = validacao.referencia_percentil(_fato(), EMPRESAS, 2024).set_index("cd_cvm")
    assert r.loc[1, "liquidez_corrente_pct"] == pytest.approx(1 / 3)
    assert r.loc[3, "liquidez_corrente_pct"] == pytest.approx(1.0)


def test_referencia_migracao():
    r = validacao.referencia_migracao(_fato(), 2024, 2025)
    n = {(a, b): v for a, b, v in r[["zona", "zona_origem", "n"]].itertuples(index=False)}
    assert n == {("risco", "risco"): 1, ("segura", "risco"): 1, ("segura", "segura"): 1}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/Scripts/python -m pytest tests/test_validacao.py -v`
Expected: FAIL com `ImportError`/`AttributeError` (módulo não existe).

- [ ] **Step 3: Implementar** — `pipeline/validacao.py`

```python
import numpy as np
import pandas as pd

from pipeline.indices import INDICES, calcular_indices

COLUNAS_BENCHMARK = [*INDICES, "z"]


def ler_resultado_dax(caminho):
    df = pd.read_csv(caminho, encoding="utf-8-sig")
    df.columns = [c.rsplit("[", 1)[-1].rstrip("]") for c in df.columns]
    return df


def comparar(dax, ref, chaves, colunas, tol=1e-6):
    m = dax.merge(ref, on=chaves, how="outer", suffixes=("_dax", "_ref"), indicator=True)
    saida = [{**{k: r[k] for k in chaves}, "coluna": "(linha)", "dax": r["_merge"], "ref": None}
             for _, r in m[m["_merge"] != "both"].iterrows()]
    m = m[m["_merge"] == "both"]
    for col in colunas:
        a, b = m[f"{col}_dax"], m[f"{col}_ref"]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            a, b = a.astype(float), b.astype(float)
            iguais = (a.isna() & b.isna()) | np.isclose(a, b, rtol=tol, atol=tol)
        else:
            iguais = (a.isna() & b.isna()) | (a.astype(str) == b.astype(str))
        for _, r in m[~iguais].iterrows():
            saida.append({**{k: r[k] for k in chaves}, "coluna": col,
                          "dax": r[f"{col}_dax"], "ref": r[f"{col}_ref"]})
    return pd.DataFrame(saida, columns=[*chaves, "coluna", "dax", "ref"])


def referencia_indices(fato):
    return calcular_indices(fato).merge(
        fato[["cd_cvm", "ano", "z", "zona", "tipo_fleuriet"]], on=["cd_cvm", "ano"])


def _indices_com_setor(fato, empresas):
    ind = calcular_indices(fato).merge(fato[["cd_cvm", "ano", "z"]], on=["cd_cvm", "ano"])
    return ind.merge(empresas[["cd_cvm", "setor"]], on="cd_cvm")


def referencia_benchmark(fato, empresas):
    g = _indices_com_setor(fato, empresas).groupby(["setor", "ano"])[COLUNAS_BENCHMARK]
    partes = [g.median().add_suffix("_mediana"),
              g.quantile(0.25).add_suffix("_q1"),
              g.quantile(0.75).add_suffix("_q3")]
    return pd.concat(partes, axis=1).reset_index()


def referencia_percentil(fato, empresas, ano):
    ind = _indices_com_setor(fato[fato["ano"] == ano], empresas)
    out = ind[["cd_cvm", "ano"]].copy()
    for col in COLUNAS_BENCHMARK:
        # fração de empresas do setor com valor <= o da empresa (empates contam a favor)
        out[f"{col}_pct"] = ind.groupby("setor")[col].rank(pct=True, method="max")
    return out


def referencia_migracao(fato, ano_base, ano):
    base = fato.loc[fato["ano"] == ano_base, ["cd_cvm", "zona"]].rename(columns={"zona": "zona_origem"})
    atual = fato.loc[fato["ano"] == ano, ["cd_cvm", "zona"]]
    par = atual.merge(base, on="cd_cvm")
    return par.groupby(["zona", "zona_origem"]).size().rename("n").reset_index()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/Scripts/python -m pytest tests/test_validacao.py -v`
Expected: 11 passed.

- [ ] **Step 5: Subcomando CLI** — em `pipeline/cli.py`

Adicionar import `from pipeline import validacao` e a função:

```python
def validar_dax(tipo, csv, *, ano=None, ano_base=None, out_dir=config.DATA_PROCESSED):
    out_dir = Path(out_dir)
    fato = pd.read_parquet(out_dir / "fato_indicadores.parquet")
    empresas = pd.read_parquet(out_dir / "dim_empresa.parquet")
    dax = validacao.ler_resultado_dax(csv)
    if tipo == "indices":
        ref, chaves = validacao.referencia_indices(fato), ["cd_cvm", "ano"]
    elif tipo == "benchmark":
        ref, chaves = validacao.referencia_benchmark(fato, empresas), ["setor", "ano"]
    elif tipo == "percentil":
        ref, chaves = validacao.referencia_percentil(fato, empresas, ano), ["cd_cvm", "ano"]
    else:
        ref, chaves = validacao.referencia_migracao(fato, ano_base, ano), ["zona", "zona_origem"]
    colunas = [c for c in ref.columns if c not in chaves]
    div = validacao.comparar(dax, ref, chaves, colunas)
    print(f"{tipo}: {len(ref)} linhas de referencia x {len(dax)} do DAX, {len(div)} divergencias")
    if len(div):
        print(div.head(20).to_string(index=False))
    return 0 if div.empty else 1
```

No `main`, adicionar o parser e o despacho (substituir o `else:` atual por `elif args.comando == "referencia":` e acrescentar o ramo novo):

```python
    p_val = sub.add_parser("validar-dax", help="compara o CSV de uma consulta DAX com o Python")
    p_val.add_argument("tipo", choices=["indices", "benchmark", "percentil", "migracao"])
    p_val.add_argument("csv")
    p_val.add_argument("--ano", type=int)
    p_val.add_argument("--ano-base", type=int)
```
```python
    elif args.comando == "validar-dax":
        return validar_dax(args.tipo, args.csv, ano=args.ano, ano_base=args.ano_base)
```

Teste em `tests/test_validacao.py`:

```python
def test_cli_validar_dax_sai_1_quando_diverge(tmp_path):
    from pipeline import cli
    out = tmp_path / "out"
    out.mkdir()
    _fato().to_parquet(out / "fato_indicadores.parquet")
    EMPRESAS.to_parquet(out / "dim_empresa.parquet")
    csv = tmp_path / "dax.csv"
    csv.write_text("[zona],[zona_origem],[n]\nrisco,risco,1\nsegura,risco,1\nsegura,segura,2\n",
                   encoding="utf-8")
    assert cli.validar_dax("migracao", csv, ano=2025, ano_base=2024, out_dir=out) == 1
    csv.write_text("[zona],[zona_origem],[n]\nrisco,risco,1\nsegura,risco,1\nsegura,segura,1\n",
                   encoding="utf-8")
    assert cli.validar_dax("migracao", csv, ano=2025, ano_base=2024, out_dir=out) == 0
```

- [ ] **Step 6: Suíte completa**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tudo passa (suíte anterior + 12 novos).

- [ ] **Step 7: Commit**

```bash
git add pipeline/validacao.py pipeline/cli.py tests/test_validacao.py
git commit -m "feat: validação automatizada DAX x Python (validar-dax)"
```

---

### Task 3: Medidas de índices, scores e avisos + validação DAX × Python

**Files:**
- Modify: modelo (via MCP), `docs/validacao-dax.md` (create)

**Interfaces:**
- Consumes: tabelas da Task 1; `python -m pipeline validar-dax indices` da Task 2.
- Produces: medidas na tabela `Medidas` (nomes exatos abaixo), usadas pelas Tasks 4, 5 e pelo roteiro.

Todas em `tableName: Medidas`. `displayFolder` na coluna Pasta. Descrição = texto da coluna Descrição (vai para o dicionário na Task 6).

- [ ] **Step 1: Criar as medidas de índice** (`measure_operations` → `Create`, um lote)

| Medida | Pasta | Formato | Expressão | Descrição |
|---|---|---|---|---|
| `Liquidez Corrente` | Índices | `0.00` | `IF ( COUNTROWS ( fato_indicadores ) = 1, DIVIDE ( SUM ( fato_indicadores[ativo_circulante] ), SUM ( fato_indicadores[passivo_circulante] ) ) )` | Ativo Circulante / Passivo Circulante. Maior é melhor. |
| `Liquidez Seca` | Índices | `0.00` | `IF ( COUNTROWS ( fato_indicadores ) = 1, DIVIDE ( SUM ( fato_indicadores[ativo_circulante] ) - SUM ( fato_indicadores[estoques] ), SUM ( fato_indicadores[passivo_circulante] ) ) )` | (Ativo Circulante − Estoques) / Passivo Circulante. Maior é melhor. |
| `Endividamento Geral` | Índices | `0.0%` | `IF ( COUNTROWS ( fato_indicadores ) = 1, DIVIDE ( SUM ( fato_indicadores[passivo_circulante] ) + SUM ( fato_indicadores[passivo_nao_circulante] ), SUM ( fato_indicadores[ativo_total] ) ) )` | Passivo exigível / Ativo Total. Menor é melhor. |
| `Dívida Líquida / PL` | Índices | `0.00` | ver bloco abaixo | (Empréstimos CP + LP − Caixa − Aplicações) / PL. Em branco se PL ≤ 0. Menor é melhor. |
| `Cobertura de Juros` | Índices | `0.0"x"` | `IF ( COUNTROWS ( fato_indicadores ) = 1, DIVIDE ( SUM ( fato_indicadores[ebit] ), ABS ( SUM ( fato_indicadores[despesas_financeiras] ) ) ) )` | EBIT / \|Despesas Financeiras\|. ABS porque a DRE traz a despesa negativa (44 empresas-ano vêm positivas). Maior é melhor. |
| `Margem EBIT` | Índices | `0.0%` | `IF ( COUNTROWS ( fato_indicadores ) = 1, DIVIDE ( SUM ( fato_indicadores[ebit] ), SUM ( fato_indicadores[receita_liquida] ) ) )` | EBIT / Receita Líquida. Em branco com receita zero. |
| `Margem Líquida` | Índices | `0.0%` | `IF ( COUNTROWS ( fato_indicadores ) = 1, DIVIDE ( SUM ( fato_indicadores[lucro_liquido] ), SUM ( fato_indicadores[receita_liquida] ) ) )` | Lucro Líquido / Receita Líquida. Em branco com receita zero. |
| `ROA` | Índices | `0.0%` | `IF ( COUNTROWS ( fato_indicadores ) = 1, DIVIDE ( SUM ( fato_indicadores[lucro_liquido] ), SUM ( fato_indicadores[ativo_total] ) ) )` | Lucro Líquido / Ativo Total. |
| `ROE` | Índices | `0.0%` | ver bloco abaixo | Lucro Líquido / PL. Em branco se PL ≤ 0. |
| `Z''-EM` | Scores | `0.00` | `IF ( COUNTROWS ( fato_indicadores ) = 1, MAX ( fato_indicadores[z] ) )` | Altman Z''-EM calculado no pipeline. Triagem, não previsão. |
| `Zona` | Scores | — | `IF ( COUNTROWS ( fato_indicadores ) = 1, MAX ( fato_indicadores[zona] ) )` | Zona do Z''-EM: segura, cinzenta, risco ou indeterminada. |
| `Tipo Fleuriet (nº)` | Scores | `0` | `IF ( COUNTROWS ( fato_indicadores ) = 1, MAX ( fato_indicadores[tipo_fleuriet] ) )` | Tipo Fleuriet de 1 a 6 (oculta; usada na validação e em ordenação). |
| `Tipo Fleuriet` | Scores | — | ver bloco abaixo | Tipo Fleuriet em texto, ex. "II - Sólida". |
| `CDG` | Fleuriet | `#,0,,."mi"` | `IF ( COUNTROWS ( fato_indicadores ) = 1, SUM ( fato_indicadores[cdg] ) )` | Capital de Giro = (PL + Passivo Não Circulante) − Ativo Não Circulante. |
| `NCG` | Fleuriet | `#,0,,."mi"` | `IF ( COUNTROWS ( fato_indicadores ) = 1, SUM ( fato_indicadores[ncg] ) )` | Necessidade de Capital de Giro = CDG − T. |
| `Saldo de Tesouraria` | Fleuriet | `#,0,,."mi"` | `IF ( COUNTROWS ( fato_indicadores ) = 1, SUM ( fato_indicadores[t] ) )` | T = Caixa + Aplicações − Empréstimos CP. |
| `Efeito Tesoura` | Fleuriet | — | ver bloco abaixo | "alerta", "não" ou "sem histórico" (nulo não é ausência de risco). |
| `Aviso PL` | Avisos | — | ver bloco abaixo | Texto quando PL ≤ 0. |
| `Aviso Receita` | Avisos | — | ver bloco abaixo | Texto quando a receita líquida é zero. |
| `Nota Metodológica` | Avisos | — | ver bloco abaixo | Aviso fixo de dupla contagem e de uso como triagem. |
| `Limite Risco` | Scores | `0.00` | `4.15` | Limite inferior da zona cinzenta do Z''-EM. |
| `Limite Segura` | Scores | `0.00` | `5.85` | Limite superior da zona cinzenta do Z''-EM. |

Blocos:

```dax
-- Dívida Líquida / PL  (caixa nulo em 1 empresa-ano: sem ele não há dívida líquida)
VAR _pl = SUM ( fato_indicadores[patrimonio_liquido] )
VAR _caixa = SUM ( fato_indicadores[caixa] )
RETURN
    IF (
        COUNTROWS ( fato_indicadores ) = 1 && _pl > 0 && NOT ISBLANK ( _caixa ),
        DIVIDE (
            SUM ( fato_indicadores[emprestimos_cp] ) + SUM ( fato_indicadores[emprestimos_lp] )
                - _caixa - SUM ( fato_indicadores[aplicacoes_financeiras] ),
            _pl
        )
    )

-- ROE
VAR _pl = SUM ( fato_indicadores[patrimonio_liquido] )
RETURN
    IF ( COUNTROWS ( fato_indicadores ) = 1 && _pl > 0,
        DIVIDE ( SUM ( fato_indicadores[lucro_liquido] ), _pl ) )

-- Tipo Fleuriet
VAR _t = [Tipo Fleuriet (nº)]
RETURN
    IF ( NOT ISBLANK ( _t ),
        SWITCH ( _t, 1, "I", 2, "II", 3, "III", 4, "IV", 5, "V", 6, "VI" )
            & " - " & MAX ( fato_indicadores[situacao_fleuriet] ) )

-- Efeito Tesoura
VAR _f = SELECTEDVALUE ( fato_indicadores[efeito_tesoura] )
RETURN
    IF ( COUNTROWS ( fato_indicadores ) = 1,
        SWITCH ( TRUE (), ISBLANK ( _f ), "sem histórico", _f, "alerta", "não" ) )

-- Aviso PL
VAR _pl = SUM ( fato_indicadores[patrimonio_liquido] )
RETURN
    IF ( COUNTROWS ( fato_indicadores ) = 1 && NOT ISBLANK ( _pl ) && _pl <= 0,
        "PL negativo ou zero: ROE e Dívida Líquida/PL não são calculados." )

-- Aviso Receita
IF ( COUNTROWS ( fato_indicadores ) = 1 && SUM ( fato_indicadores[receita_liquida] ) = 0,
    "Receita líquida zero (comum em holdings): margens não são calculadas." )

-- Nota Metodológica
"Z''-EM e Fleuriet são indicadores de triagem, não previsão de default. Controladoras e controladas listadas aparecem como empresas separadas, o que pode contar o mesmo grupo mais de uma vez nas medianas setoriais."
```

Ocultar `Tipo Fleuriet (nº)`. Depois de criar tudo, `dax_query_operations` → `Validate` numa consulta que referencie cada medida, para pegar erro de sintaxe antes da validação numérica.

- [ ] **Step 2: Consulta de validação (todas as empresas-ano)** — `Execute`, `maxRows: 10000`

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

Observação: `SUMMARIZECOLUMNS` descarta linhas em que **todas** as medidas são branco. `[Zona]` nunca é branco numa empresa-ano existente, então as 6.266 linhas voltam.

- [ ] **Step 3: Comparar**

Run: `.venv/Scripts/python -m pipeline validar-dax indices "<caminho do CSV retornado>"`
Expected: `indices: 6266 linhas de referencia x 6266 do DAX, 0 divergencias` e exit 0. Se divergir, **diagnosticar** (systematic-debugging) antes de mexer: a referência é o Python já conferido com as DFPs publicadas.

- [ ] **Step 4: Checagem pontual das 5 empresas da conferência**

Run: `.venv/Scripts/python -c "import pandas as pd; from pipeline import validacao as v; d=v.ler_resultado_dax(r'<CSV>'); r=pd.read_csv('docs/referencia_indices.csv'); print(len(v.comparar(d[d.cd_cvm.isin(r.cd_cvm)], r, ['cd_cvm','ano'], [c for c in r.columns if c not in ('cd_cvm','ano')])))"`
Expected: `0`. Isso liga o resultado ao arquivo versionado citado na spec §7.3.

- [ ] **Step 5: Registrar em `docs/validacao-dax.md`**

```markdown
# Validação DAX × Python

Referência: índices recalculados por `pipeline/indices.py` sobre os Parquet
(mesmo código de `docs/referencia_indices.csv`). Comparação por
`python -m pipeline validar-dax`, tolerância relativa e absoluta de 1e-6;
branco no DAX = NaN no Python.

| Data | Verificação | Linhas | Divergências |
|---|---|---|---|
| 2026-09-23 | Índices, Z, zona, tipo Fleuriet — todas as empresas-ano | 6.266 | 0 |
| 2026-09-23 | Idem, recorte das 5 empresas de `referencia_indices.csv` | 55 | 0 |

## Consulta — índices
(colar a consulta DAX do Step 2)
```
(Preencher as contagens com o resultado real; se houver divergência explicada, listar cada uma.)

- [ ] **Step 6: Leonardo Ctrl+S; commit**

```bash
git add powerbi docs/validacao-dax.md
git commit -m "feat: medidas de índices, scores e avisos validadas contra o Python"
```

---

### Task 4: Benchmark setorial (grupo de cálculo + seletor de índice) + validação

**Files:**
- Modify: modelo (via MCP), `docs/validacao-dax.md`

**Interfaces:**
- Consumes: medidas da Task 3, `dim_indice`.
- Produces: grupo de cálculo `Benchmark`, coluna `Benchmark[Comparação]`, itens com os nomes exatos abaixo; medidas `Valor do Índice`, `Fórmula do Índice`, `Leitura do Índice`.

- [ ] **Step 1: Medidas do seletor**

```dax
-- Valor do Índice   (Pasta: Benchmark; formatStringExpression: SELECTEDVALUE ( dim_indice[formato], "0.00" ))
SWITCH (
    SELECTEDVALUE ( dim_indice[ordem] ),
    1, [Liquidez Corrente],
    2, [Liquidez Seca],
    3, [Endividamento Geral],
    4, [Dívida Líquida / PL],
    5, [Cobertura de Juros],
    6, [Margem EBIT],
    7, [Margem Líquida],
    8, [ROA],
    9, [ROE],
    10, [Z''-EM]
)

-- Fórmula do Índice   (Pasta: Benchmark)
SELECTEDVALUE ( dim_indice[formula] )

-- Leitura do Índice   (Pasta: Benchmark)
SELECTEDVALUE ( dim_indice[leitura] )
```
Descrições: "Valor do índice escolhido em dim_indice; combine com o grupo Benchmark." / "Fórmula do índice escolhido (tooltip)." / "Direção de leitura do índice escolhido (tooltip)."

- [ ] **Step 2: Grupo de cálculo `Benchmark`** (`calculation_group_operations`; rode `Help` primeiro para o formato exato). Coluna `Comparação`, `precedence: 10`. Se o MCP exigir, ativar `discourageImplicitMeasures` no modelo (`model_operations`). Itens, na ordem:

```dax
-- 0 "Valor"
SELECTEDMEASURE ()

-- 1 "Mediana do Setor"
CALCULATE (
    MEDIANX (
        FILTER ( VALUES ( dim_empresa[cd_cvm] ), NOT ISBLANK ( SELECTEDMEASURE () ) ),
        SELECTEDMEASURE ()
    ),
    REMOVEFILTERS ( dim_empresa ),
    REMOVEFILTERS ( dim_zona ),
    VALUES ( dim_empresa[setor] )
)

-- 2 "Q1 do Setor"   (mesmo corpo com PERCENTILEX.INC ( ..., SELECTEDMEASURE (), 0.25 ))
CALCULATE (
    PERCENTILEX.INC (
        FILTER ( VALUES ( dim_empresa[cd_cvm] ), NOT ISBLANK ( SELECTEDMEASURE () ) ),
        SELECTEDMEASURE (),
        0.25
    ),
    REMOVEFILTERS ( dim_empresa ),
    REMOVEFILTERS ( dim_zona ),
    VALUES ( dim_empresa[setor] )
)

-- 3 "Q3 do Setor"
CALCULATE (
    PERCENTILEX.INC (
        FILTER ( VALUES ( dim_empresa[cd_cvm] ), NOT ISBLANK ( SELECTEDMEASURE () ) ),
        SELECTEDMEASURE (),
        0.75
    ),
    REMOVEFILTERS ( dim_empresa ),
    REMOVEFILTERS ( dim_zona ),
    VALUES ( dim_empresa[setor] )
)

-- 4 "Percentil no Setor"   formatStringExpression: "0%"
VAR _v = SELECTEDMEASURE ()
VAR _valores =
    CALCULATETABLE (
        FILTER (
            ADDCOLUMNS ( VALUES ( dim_empresa[cd_cvm] ), "@v", SELECTEDMEASURE () ),
            NOT ISBLANK ( [@v] )
        ),
        REMOVEFILTERS ( dim_empresa ),
        REMOVEFILTERS ( dim_zona ),
        VALUES ( dim_empresa[setor] )
    )
VAR _n = COUNTROWS ( _valores )
VAR _ate = COUNTROWS ( FILTER ( _valores, [@v] <= _v ) )
RETURN IF ( NOT ISBLANK ( _v ) && _n > 0, DIVIDE ( _ate, _n ) )

-- 5 "Quartil no Setor"   formatStringExpression: "0"
VAR _v = SELECTEDMEASURE ()
VAR _valores =
    CALCULATETABLE (
        FILTER (
            ADDCOLUMNS ( VALUES ( dim_empresa[cd_cvm] ), "@v", SELECTEDMEASURE () ),
            NOT ISBLANK ( [@v] )
        ),
        REMOVEFILTERS ( dim_empresa ),
        REMOVEFILTERS ( dim_zona ),
        VALUES ( dim_empresa[setor] )
    )
VAR _n = COUNTROWS ( _valores )
VAR _p = DIVIDE ( COUNTROWS ( FILTER ( _valores, [@v] <= _v ) ), _n )
RETURN IF ( NOT ISBLANK ( _v ) && _n > 0, MIN ( 4, MAX ( 1, ROUNDUP ( _p * 4, 0 ) ) ) )

-- 6 "Δ vs Ano Anterior"
VAR _ano = MAX ( dim_ano[ano] )
VAR _atual = SELECTEDMEASURE ()
VAR _anterior = CALCULATE ( SELECTEDMEASURE (), dim_ano[ano] = _ano - 1 )
RETURN IF ( NOT ISBLANK ( _atual ) && NOT ISBLANK ( _anterior ), _atual - _anterior )
```

> **Corrigido na execução (2026-09-23):** a forma acima de Mediana/Q1/Q3 (`FILTER ( VALUES ( dim_empresa[cd_cvm] ), ... )` direto no agregador) divergiu em 94 valores na consulta de 30 colunas. No modelo, os itens 1–5 usam o padrão materializado sobre `VALUES ( fato_indicadores[cd_cvm] )` descrito em `docs/validacao-dax.md` (seção "Defeito encontrado e corrigido"). O TMDL em `powerbi/` é a fonte da verdade.

Leitura: Quartil 1 = valores mais baixos do setor; a direção (maior ou menor é melhor) vem de `[Leitura do Índice]`.

- [ ] **Step 3: Validar medianas e quartis** — `Execute`, `maxRows: 10000`

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
    "liquidez_seca_mediana", CALCULATE ( [Liquidez Seca], _m ),
    "liquidez_seca_q1", CALCULATE ( [Liquidez Seca], _q1 ),
    "liquidez_seca_q3", CALCULATE ( [Liquidez Seca], _q3 ),
    "endividamento_geral_mediana", CALCULATE ( [Endividamento Geral], _m ),
    "endividamento_geral_q1", CALCULATE ( [Endividamento Geral], _q1 ),
    "endividamento_geral_q3", CALCULATE ( [Endividamento Geral], _q3 ),
    "divida_liquida_pl_mediana", CALCULATE ( [Dívida Líquida / PL], _m ),
    "divida_liquida_pl_q1", CALCULATE ( [Dívida Líquida / PL], _q1 ),
    "divida_liquida_pl_q3", CALCULATE ( [Dívida Líquida / PL], _q3 ),
    "cobertura_juros_mediana", CALCULATE ( [Cobertura de Juros], _m ),
    "cobertura_juros_q1", CALCULATE ( [Cobertura de Juros], _q1 ),
    "cobertura_juros_q3", CALCULATE ( [Cobertura de Juros], _q3 ),
    "margem_ebit_mediana", CALCULATE ( [Margem EBIT], _m ),
    "margem_ebit_q1", CALCULATE ( [Margem EBIT], _q1 ),
    "margem_ebit_q3", CALCULATE ( [Margem EBIT], _q3 ),
    "margem_liquida_mediana", CALCULATE ( [Margem Líquida], _m ),
    "margem_liquida_q1", CALCULATE ( [Margem Líquida], _q1 ),
    "margem_liquida_q3", CALCULATE ( [Margem Líquida], _q3 ),
    "roa_mediana", CALCULATE ( [ROA], _m ),
    "roa_q1", CALCULATE ( [ROA], _q1 ),
    "roa_q3", CALCULATE ( [ROA], _q3 ),
    "roe_mediana", CALCULATE ( [ROE], _m ),
    "roe_q1", CALCULATE ( [ROE], _q1 ),
    "roe_q3", CALCULATE ( [ROE], _q3 ),
    "z_mediana", CALCULATE ( [Z''-EM], _m ),
    "z_q1", CALCULATE ( [Z''-EM], _q1 ),
    "z_q3", CALCULATE ( [Z''-EM], _q3 )
)
```
Run: `.venv/Scripts/python -m pipeline validar-dax benchmark "<CSV>"`
Expected: 0 divergências. (Referência: `groupby(setor, ano)` com `median`/`quantile` lineares = `PERCENTILEX.INC`.)

- [ ] **Step 4: Validar percentil (2024)**

```dax
EVALUATE
VAR _p = TREATAS ( { "Percentil no Setor" }, Benchmark[Comparação] )
RETURN
SUMMARIZECOLUMNS (
    dim_empresa[cd_cvm],
    dim_ano[ano],
    TREATAS ( { 2024 }, dim_ano[ano] ),
    "liquidez_corrente_pct", CALCULATE ( [Liquidez Corrente], _p ),
    "liquidez_seca_pct", CALCULATE ( [Liquidez Seca], _p ),
    "endividamento_geral_pct", CALCULATE ( [Endividamento Geral], _p ),
    "divida_liquida_pl_pct", CALCULATE ( [Dívida Líquida / PL], _p ),
    "cobertura_juros_pct", CALCULATE ( [Cobertura de Juros], _p ),
    "margem_ebit_pct", CALCULATE ( [Margem EBIT], _p ),
    "margem_liquida_pct", CALCULATE ( [Margem Líquida], _p ),
    "roa_pct", CALCULATE ( [ROA], _p ),
    "roe_pct", CALCULATE ( [ROE], _p ),
    "z_pct", CALCULATE ( [Z''-EM], _p ),
    "_zona", [Zona]
)
```
Run: `.venv/Scripts/python -m pipeline validar-dax percentil "<CSV>" --ano 2024`
Expected: 0 divergências (a coluna `_zona` só garante que toda empresa-ano de 2024 volte; ela não existe na referência e é ignorada). Se a comparação acusar `(linha)` por empresas de 2024 cujos percentis são todos brancos, conferir se `_zona` voltou.

- [ ] **Step 5: Conferência manual do Quartil e do Δ** — uma empresa (WEG, 5410, 2024):

```dax
EVALUATE
CALCULATETABLE (
    SUMMARIZECOLUMNS (
        dim_indice[indice],
        Benchmark[Comparação],
        "valor", [Valor do Índice]
    ),
    dim_empresa[cd_cvm] = 5410,
    dim_ano[ano] = 2024
)
```
Conferir que a linha `Liquidez Corrente` × `Mediana do Setor` (e a do Z) é igual ao valor do setor da WEG em 2024 no CSV do Step 3: isso prova que o grupo de cálculo age certo **através** de `[Valor do Índice]` (o SWITCH), que é como a ficha usa. Conferir à mão: `Quartil` = `ROUNDUP(Percentil*4)` limitado a 1–4; `Δ vs Ano Anterior` do Z = Z 2024 − Z 2023 de `docs/referencia_indices.csv`. Registrar as linhas do Z na `docs/validacao-dax.md`.

- [ ] **Step 6: Atualizar `docs/validacao-dax.md`** com as linhas "Mediana/Q1/Q3 por setor-ano" (número de linhas e 0 divergências), "Percentil 2024" e "Quartil e Δ — WEG 2024 (manual)", e as consultas.

- [ ] **Step 7: Leonardo Ctrl+S; commit**

```bash
git add powerbi docs/validacao-dax.md
git commit -m "feat: benchmark setorial por grupo de cálculo, validado contra o Python"
```

---

### Task 5: Medidas de triagem, migração, tesoura e qualidade + validação

**Files:**
- Modify: modelo (via MCP), `docs/validacao-dax.md`

**Interfaces:**
- Consumes: `dim_zona`, `zona_origem`, `ano_base`, `qualidade`.
- Produces: medidas abaixo (nomes exatos, pasta entre parênteses).

- [ ] **Step 1: Criar as medidas**

```dax
-- Empresas  (Triagem, formato 0)  "Número de empresas distintas no contexto."
DISTINCTCOUNT ( fato_indicadores[cd_cvm] )

-- Empresas-Ano  (Triagem, formato #,0)  "Número de linhas empresa-ano no contexto."
COUNTROWS ( fato_indicadores )

-- Δ Empresas vs Ano Anterior  (Triagem, formato +0;-0;0)
VAR _ano = MAX ( dim_ano[ano] )
VAR _anterior = CALCULATE ( [Empresas], dim_ano[ano] = _ano - 1 )
RETURN IF ( HASONEVALUE ( dim_ano[ano] ) && NOT ISBLANK ( _anterior ), [Empresas] - _anterior )

-- Δ Z''-EM  (Scores, formato +0.00;-0.00;0.00)  "Z do ano menos Z do ano anterior, mesma empresa."
VAR _ano = MAX ( dim_ano[ano] )
VAR _atual = [Z''-EM]
VAR _anterior = CALCULATE ( [Z''-EM], dim_ano[ano] = _ano - 1 )
RETURN IF ( NOT ISBLANK ( _atual ) && NOT ISBLANK ( _anterior ), _atual - _anterior )

-- % em Risco  (Triagem, formato 0.0%)  "Empresas-ano na zona risco / empresas-ano com Z calculado (exclui indeterminada)."
DIVIDE (
    CALCULATE ( COUNTROWS ( fato_indicadores ), dim_zona[zona] = "risco" ),
    CALCULATE ( COUNTROWS ( fato_indicadores ), dim_zona[zona] <> "indeterminada" )
)

-- % com Efeito Tesoura  (Triagem, formato 0.0%)  "Empresas-ano com alerta / empresas-ano com histórico comparável (nulos fora do denominador)."
DIVIDE (
    CALCULATE ( COUNTROWS ( fato_indicadores ), fato_indicadores[efeito_tesoura] = TRUE () ),
    CALCULATE ( COUNTROWS ( fato_indicadores ), NOT ISBLANK ( fato_indicadores[efeito_tesoura] ) )
)

-- Migração de Zona  (Triagem, formato 0)  "Empresas que estavam na zona de origem (linhas) no ano base e estão na zona da coluna no ano selecionado."
VAR _anoBase = SELECTEDVALUE ( ano_base[ano_base] )
VAR _origem = SELECTEDVALUE ( zona_origem[zona_origem] )
VAR _destino = VALUES ( fato_indicadores[cd_cvm] )
VAR _naOrigem =
    CALCULATETABLE (
        VALUES ( fato_indicadores[cd_cvm] ),
        dim_ano[ano] = _anoBase,
        dim_zona[zona] = _origem
    )
RETURN
    IF ( NOT ISBLANK ( _anoBase ) && NOT ISBLANK ( _origem ),
        COUNTROWS ( INTERSECT ( _destino, _naOrigem ) ) )

-- Cor da Zona  (Triagem)  "Cor hexadecimal da zona, para formatação condicional."
VAR _z = COALESCE ( [Zona], SELECTEDVALUE ( dim_zona[zona] ) )
RETURN SWITCH ( _z, "segura", "#2E7D32", "cinzenta", "#F9A825", "risco", "#C62828", "indeterminada", "#9E9E9E" )

-- Problemas de Qualidade  (Qualidade, formato #,0)  "Registros no log de qualidade do pipeline."
COUNTROWS ( qualidade )

-- Empresas Excluídas  (Qualidade, formato 0)  "Empresas distintas excluídas na etapa de filtro."
CALCULATE ( DISTINCTCOUNT ( qualidade[cd_cvm] ), qualidade[etapa] = "filtro" )
```

- [ ] **Step 2: Validar contagens contra a conferência**

```dax
EVALUATE
ROW (
    "segura", CALCULATE ( [Empresas-Ano], dim_zona[zona] = "segura" ),
    "cinzenta", CALCULATE ( [Empresas-Ano], dim_zona[zona] = "cinzenta" ),
    "risco", CALCULATE ( [Empresas-Ano], dim_zona[zona] = "risco" ),
    "indeterminada", CALCULATE ( [Empresas-Ano], dim_zona[zona] = "indeterminada" ),
    "pct_risco", [% em Risco],
    "pct_tesoura", [% com Efeito Tesoura],
    "problemas", [Problemas de Qualidade],
    "empresas", [Empresas]
)
```
Expected (de `docs/conferencia-dados-reais.md`): segura 2207, cinzenta 1938, risco 2092, indeterminada 29, `pct_risco` = 2092/6237 = 0,33542, `pct_tesoura` = 898/4495 = 0,19978, problemas 1268, empresas 830.

- [ ] **Step 3: Validar migração 2024 → 2025**

```dax
EVALUATE
SUMMARIZECOLUMNS (
    dim_zona[zona],
    zona_origem[zona_origem],
    TREATAS ( { 2025 }, dim_ano[ano] ),
    TREATAS ( { 2024 }, ano_base[ano_base] ),
    "n", [Migração de Zona]
)
```
Run: `.venv/Scripts/python -m pipeline validar-dax migracao "<CSV>" --ano 2025 --ano-base 2024`
Expected: 0 divergências.

- [ ] **Step 4: Validar Δ Empresas numa linha** — `EVALUATE ROW("d", CALCULATE([Δ Empresas vs Ano Anterior], dim_ano[ano] = 2025, dim_zona[zona] = "risco"))` e comparar com `pandas`: `(f[(f.ano==2025)&(f.zona=='risco')].cd_cvm.nunique() - f[(f.ano==2024)&(f.zona=='risco')].cd_cvm.nunique())`.

- [ ] **Step 5: Atualizar `docs/validacao-dax.md`**, Ctrl+S, commit

```bash
git add powerbi docs/validacao-dax.md
git commit -m "feat: medidas de triagem, migração, tesoura e qualidade validadas"
```

---

### Task 6: Dicionário de métricas

**Files:**
- Create: `docs/dicionario-metricas.md`

- [ ] **Step 1: Invocar a skill `metrics-documentation`** e seguir o formato dela.

- [ ] **Step 2: Extrair do modelo** (fonte única = descrições nas medidas):

```dax
EVALUATE
SELECTCOLUMNS (
    INFO.VIEW.MEASURES (),
    "medida", [Name], "pasta", [DisplayFolder], "descricao", [Description],
    "formato", [FormatString], "expressao", [Expression]
)
```
Conferir que nenhuma medida tem `descricao` vazia (exceto `Tipo Fleuriet (nº)`, oculta, que também deve ter).

- [ ] **Step 3: Escrever `docs/dicionario-metricas.md`**: uma seção por pasta (Índices, Scores, Fleuriet, Benchmark, Triagem, Avisos, Qualidade); para cada medida, nome, o que responde, fórmula em linguagem contábil, direção de leitura, regra de branco (PL ≤ 0, receita zero, denominador zero, uma empresa-ano) e DAX. Seção "Grupo de cálculo Benchmark" com cada item e o que ele faz com a medida. Seção "Limitações": dupla contagem controladora/controladas; EBIT de holdings com equivalência; nulo de tesoura ≠ sem risco; índices em branco fora de contexto empresa-ano.

- [ ] **Step 4: Commit**

```bash
git add docs/dicionario-metricas.md
git commit -m "docs: dicionário de métricas do modelo"
```

---

### Task 7: Roteiro de visuais → páginas montadas pelo Leonardo → revisão por print

**Files:**
- Create: `docs/roteiro-visuais.md`
- Modify: `powerbi/analise-credito-cvm.Report/**` (Leonardo, no Desktop)

- [ ] **Step 1: Escrever `docs/roteiro-visuais.md`** com este conteúdo (ajustar só se o modelo divergir):

Cabeçalho comum: tela 16:9 (1280×720); tema com as cores das zonas (`segura #2E7D32`, `cinzenta #F9A825`, `risco #C62828`, `indeterminada #9E9E9E`); faixa de título no topo; fonte Segoe UI; **sempre** colunas de dimensão nos visuais; `dim_ano[ano]` em segmentação de seleção única, sincronizada nas páginas 1–3.

**Página 1 — Triagem de risco**
| # | Visual | Campos | Configuração |
|---|---|---|---|
| 1 | Segmentação | `dim_ano[ano]` | lista suspensa, seleção única, padrão 2025 |
| 2 | Segmentação | `dim_setor[setor]` | lista suspensa, multisseleção, pesquisa |
| 3 | Segmentação | `dim_zona[zona]` | botões horizontais |
| 4–6 | Cartão (novo) ×3 | `[Empresas]` filtrado no visual por `dim_zona[zona]` = segura / cinzenta / risco; rótulo de referência `[Δ Empresas vs Ano Anterior]` | cor do valor = cor da zona |
| 7 | Matriz "Migração de zona" | Linhas `zona_origem[zona_origem]`, Colunas `dim_zona[zona]`, Valores `[Migração de Zona]` | segmentação `ano_base[ano_base]` ao lado (seleção única, padrão 2024); formatação condicional de fundo em escala; título dinâmico opcional |
| 8 | Tabela | `dim_empresa[empresa]`, `dim_setor[setor]`, `[Z''-EM]`, `[Zona]`, `[Tipo Fleuriet]`, `[Δ Z''-EM]`, `[Efeito Tesoura]` | ordenar por `[Z''-EM]` crescente; fundo de `[Zona]` por valor de campo `[Cor da Zona]`; ícones em `[Δ Z''-EM]` (seta verde > 0, vermelha < 0) |
| 9 | Cartão de texto | `[Nota Metodológica]` | rodapé, fonte 9 |
| 10 | Cartão | `[% com Efeito Tesoura]` | título "Alerta de efeito tesoura (entre empresas com histórico)" |

**Página 2 — Ficha da empresa** (destino de drill-through em `dim_empresa[empresa]`; manter "Manter todos os filtros" ligado)
| # | Visual | Campos | Configuração |
|---|---|---|---|
| 1 | Cartão | `dim_empresa[empresa]` + `dim_setor[setor]` + `dim_empresa[tipo_demonstrativo]` | cabeçalho |
| 2 | Cartões | `[Z''-EM]`, `[Zona]`, `[Tipo Fleuriet]`, `[Efeito Tesoura]` | `[Zona]` com cor de `[Cor da Zona]` |
| 3 | Matriz "Índices vs setor" | Linhas `dim_indice[indice]`; Colunas `Benchmark[Comparação]` filtrado no visual para Valor, Mediana do Setor, Quartil no Setor, Δ vs Ano Anterior; Valores `[Valor do Índice]` | dicas de ferramenta: `[Fórmula do Índice]`, `[Leitura do Índice]` |
| 4 | Linha "Z''-EM ao longo do tempo" | Eixo `dim_ano[ano]`; Valores `[Z''-EM]`, `[Limite Risco]`, `[Limite Segura]` | este visual **ignora** a segmentação de ano (Editar interações → nenhum); limites tracejados, cores de risco e segura; faixa entre eles = zona cinzenta |
| 5 | Colunas agrupadas "Fleuriet" | Eixo `dim_ano[ano]`; Valores `[CDG]`, `[NCG]`, `[Saldo de Tesouraria]` | também ignora a segmentação de ano; dica de ferramenta com `[Tipo Fleuriet]` |
| 6 | Cartões de texto | `[Aviso PL]`, `[Aviso Receita]` | somem quando em branco |
| 7 | Botão Voltar | — | canto superior esquerdo |

**Página 3 — Panorama setorial**
| # | Visual | Campos | Configuração |
|---|---|---|---|
| 1 | Segmentação | `dim_indice[indice]` | seleção única, padrão Z''-EM |
| 2 | Matriz | Linhas `dim_setor[setor]`; Colunas `Benchmark[Comparação]` filtrado para Q1 do Setor, Mediana do Setor, Q3 do Setor; Valores `[Valor do Índice]` | + coluna `[Empresas]` (em outra matriz ou como medida visual, se o grupo de cálculo interferir); barras de dados na mediana |
| 3 | Linha "% em risco" | Eixo `dim_ano[ano]`; Valores `[% em Risco]`; Legenda `dim_setor[setor]` | ignora a segmentação de ano; filtro do visual Top 6 setores por `[Empresas]`, ou pequenos múltiplos |
| 4 | Cartão de texto | `[Nota Metodológica]` | rodapé |

**Página 4 — Qualidade dos dados**
| # | Visual | Campos | Configuração |
|---|---|---|---|
| 1 | Barras empilhadas | Eixo `qualidade[ano]`; Legenda `qualidade[etapa]`; Valores `[Problemas de Qualidade]` | não sincronizar a segmentação de ano aqui |
| 2 | Barras | Eixo `qualidade[problema]`; Valores `[Problemas de Qualidade]` | ordenado decrescente |
| 3 | Cartões | `[Problemas de Qualidade]`, `[Empresas Excluídas]` | — |
| 4 | Tabela | `qualidade[nome]`, `qualidade[cd_cvm]`, `qualidade[ano]`, `qualidade[etapa]`, `qualidade[problema]` | filtro de página opcional por etapa |
| 5 | Caixa de texto | "Setores financeiros são excluídos por terem layout de demonstrativo diferente. 'Sem cadastro' são emissores estrangeiros e um caso de CD_CVM divergente (Multilaser)." | — |

Ao fim de cada página: Leonardo manda print, Claude confere contra o roteiro e contra números conhecidos (ex. 2025: cartões por zona somam as empresas de 2025; migração soma as empresas presentes nos dois anos).

- [ ] **Step 2: Commit do roteiro**

```bash
git add docs/roteiro-visuais.md
git commit -m "docs: roteiro de visuais das 4 páginas"
```

- [ ] **Step 3: Página por página** — Leonardo monta, manda o print, Claude revisa. Para cada número do print, conferir com uma consulta DAX via MCP no mesmo filtro (ex. cartão "risco" 2025 = `CALCULATE([Empresas], dim_ano[ano]=2025, dim_zona[zona]="risco")`). Correções de modelo via MCP; de visual, instrução ao Leonardo.

- [ ] **Step 4: Ctrl+S e commit ao fim de cada página**

```bash
git add powerbi
git commit -m "feat: página <n> - <nome> do relatório"
```

---

### Task 8: QA, screenshots, README e fechamento

**Files:**
- Create: `README.md`, `docs/screenshots/01-triagem.png`, `02-ficha.png`, `03-panorama.png`, `04-qualidade.png`
- Modify: `docs/pendencias-plano-b.md` (marcar cada item como tratado, com o link)

- [ ] **Step 1: Invocar `report-qa-checklist`** e percorrer o relatório com o Leonardo. Registrar achados e corrigir.

- [ ] **Step 2: Screenshots** — Leonardo exporta cada página (*Exportar → PDF* ou captura 1280×720) para `docs/screenshots/`. Ficha com uma empresa conhecida (WEG 2025).

- [ ] **Step 3: README.md** com estas seções:
  1. **Contexto de negócio** — a pergunta do analista de crédito; o que é Z''-EM (fórmula, zonas, calibrado fora do Brasil → triagem, não previsão); o que é Fleuriet (CDG, NCG, T, os 6 tipos, efeito tesoura e por que nulo ≠ sem risco).
  2. **Arquitetura** — o diagrama da spec §4; modelo estrela (tabelas e relações); grupo de cálculo Benchmark.
  3. **Como rodar** — Python 3.13, `.venv`, `pip install -r requirements.txt`, `python -m pipeline run`; abrir `powerbi/analise-credito-cvm.pbip`; **ajustar o parâmetro `PastaDados`** (Transformar dados → Parâmetros) para o caminho local; Atualizar.
  4. **Verificação** — testes (`pytest`), conferência com DFPs (`docs/conferencia-dados-reais.md`), validação DAX × Python (`docs/validacao-dax.md`, com a contagem de linhas e 0 divergências), QA.
  5. **Prints** das 4 páginas.
  6. **Limitações conhecidas** — `--anos` parcial sobrescreve as saídas completas; dois exercícios no mesmo ano civil (~6 empresas-ano) mantêm o mais recente; dupla contagem controladora/controladas; EBIT de holdings; 8,6% com receita zero e 12,7% com PL ≤ 0 (índices em branco); Multilaser fora por CD_CVM divergente (fallback por CNPJ não implementado); sem ITR, dados de mercado ou EBITDA.
  7. **Documentação** — links para spec, planos, dicionário, roteiro.

- [ ] **Step 4: Atualizar `docs/pendencias-plano-b.md`** — cada item com "✔ tratado em …".

- [ ] **Step 5: Verificação final** (skill `verification-before-completion`)

```bash
.venv/Scripts/python -m pytest -q
git status --short
```
Rodar de novo as consultas das Tasks 3–5 e o `validar-dax` (o modelo pode ter mudado nas correções da Task 7). Expected: pytest verde, 0 divergências em todas.

- [ ] **Step 6: Commit**

```bash
git add README.md docs
git commit -m "docs: README, screenshots e fechamento das pendências do Plano B"
```

- [ ] **Step 7: Deep review do branch** (agente `deep-reviewer`, Opus): DAX × spec §5, contrato de dados das pendências, README × comportamento real, TMDL (sem caminho quebrado, sem medida sem descrição). Corrigir os achados num único lote.

- [ ] **Step 8: `superpowers:finishing-a-development-branch`.**
