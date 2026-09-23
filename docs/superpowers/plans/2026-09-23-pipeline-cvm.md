# Pipeline CVM (Plano A) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pipeline Python que baixa as DFP da CVM (2015–2025), limpa, filtra as companhias não financeiras, calcula Z''-EM e Fleuriet e exporta um esquema estrela em Parquet pronto para o Power BI.

**Architecture:** Módulos pequenos em `pipeline/`, cada um recebendo e devolvendo DataFrames (sem rede exceto `extrair`), orquestrados por `python -m pipeline run`. Problemas de qualidade viram linhas em um DataFrame `problemas` (cd_cvm, ano, etapa, problema) em vez de exceções.

**Tech Stack:** Python 3.13, pandas 3.0.6, pyarrow 25.0.1, requests 2.34.2, pytest 9.1.1.

**Spec:** `docs/superpowers/specs/2026-09-23-analise-credito-cvm-design.md`

**Escopo deste plano:** seções 3, 4, 6 e 7 (itens 1–2) da spec. O modelo e o relatório Power BI (seção 5 e item 7.3–7.4) ficam para o **Plano B**, escrito depois que os Parquet reais existirem.

## Global Constraints

- Python 3.13 em `.venv` local; dependências **pinadas** em `requirements.txt` com as versões acima.
- Anos padrão: 2015 a 2025 inclusive.
- Somente contas com `ST_CONTA_FIXA = 'S'`; somente `ORDEM_EXERC = 'ÚLTIMO'`.
- Valores de saída sempre em **reais** (`MIL` × 1000).
- Consolidado quando existir com Ativo Total ≠ 0; senão individual.
- CSVs da CVM: separador `;`, encoding `latin-1`.
- `CD_CVM` vem com zeros à esquerda na DFP (`"001023"`) e sem no cadastro (`"25224"`): **sempre** converter para `int` na coluna `cd_cvm`.
- Z''-EM: `Z = 3,25 + 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4`; zonas `Z > 5,85` segura, `4,15 ≤ Z ≤ 5,85` cinzenta, `Z < 4,15` risco, NaN indeterminada.
- Fleuriet: `CDG = (PL + PNC) − ANC`, `T = (caixa + aplicações) − empréstimos CP`, `NCG = CDG − T`; zero conta como positivo.
- Nomes de colunas e valores categóricos em português, snake_case, exatamente como neste plano.
- Testes nunca acessam a rede.

## Fatos verificados nos dados reais (2015 e 2024)

- Arquivos no ZIP: `dfp_cia_aberta_{DEM}_{con|ind}_{ano}.csv` com DEM ∈ BPA, BPP, DRE, DFC_MI, DFC_MD (há outros que ignoramos).
- Colunas usadas: `CNPJ_CIA, CD_CVM, DENOM_CIA, VERSAO, ESCALA_MOEDA, ORDEM_EXERC, DT_FIM_EXERC, CD_CONTA, DS_CONTA, VL_CONTA, ST_CONTA_FIXA` (presentes em todos os demonstrativos). `VL_CONTA` usa ponto decimal: `"1388864529.0000000000"`.
- ~20 companhias/ano usam layout de banco/seguradora: `2.03` = "Passivos Financeiros ao Custo Amortizado" ou "Provisões", `3.05` = "Resultado Antes dos Tributos sobre o Lucro". O padrão tem `2.03` = "Patrimônio Líquido Consolidado"/"Patrimônio Líquido" e `3.05` = "Resultado Antes do Resultado Financeiro e dos Tributos".
- Cadastro tem 111 `CD_CVM` duplicados (mesma empresa, registros repetidos) e `SETOR_ATIV` com prefixo "Emp. Adm. Part. - " para holdings.
- CD_CVM de referência: Petrobras 9512, Vale 4170, WEG 5410, Ambev 23264, Magazine Luiza 22470.

## Estrutura de arquivos

```
pipeline/__init__.py       vazio
pipeline/__main__.py       chama cli.main()
pipeline/config.py         caminhos, URLs, mapeamento de contas, setores, layout
pipeline/extrair.py        download com cache e retry
pipeline/leitura.py        lê os CSVs de dentro do ZIP da DFP
pipeline/limpar.py         versão, exercício, escala, con/ind, contas fixas
pipeline/cadastro.py       lê cadastro, deduplica, limpa setor
pipeline/filtros.py        exclui financeiras, layout não padrão, AT inválido
pipeline/contas_base.py    pivota para uma linha por empresa-ano
pipeline/scores.py         Z''-EM, Fleuriet, efeito tesoura
pipeline/indices.py        índices de referência (espelho das futuras medidas DAX)
pipeline/exportar.py       grava os Parquet
pipeline/cli.py            comandos run e referencia
tests/...                  um arquivo de teste por módulo
```

---

### Task 1: Scaffold, config e download

**Files:**
- Create: `.gitignore`, `requirements.txt`, `pytest.ini`, `pipeline/__init__.py`, `pipeline/config.py`, `pipeline/extrair.py`, `tests/__init__.py`, `tests/test_extrair.py`

**Interfaces:**
- Produces: `config.RAIZ`, `config.DATA_RAW`, `config.DATA_PROCESSED`, `config.ANOS_PADRAO`, `config.URL_DFP`, `config.URL_CADASTRO`, `config.DEMONSTRATIVOS`, `config.CONTAS`, `config.CONTAS_OPCIONAIS`, `config.SETORES_FINANCEIROS`, `config.ALIAS_SETOR`, `config.LAYOUT_ESPERADO`; `extrair.ErroDownload`, `extrair.baixar(url, destino, *, forcar=False, tentativas=3, espera=2.0, get=requests.get) -> Path`, `extrair.baixar_tudo(anos, raw_dir=config.DATA_RAW, *, forcar=False, get=requests.get) -> tuple[dict[int, Path], Path]`

- [ ] **Step 1: Criar ambiente e arquivos base**

```powershell
python --version   # deve ser 3.13.x
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
```

`requirements.txt`:
```
pandas==3.0.6
pyarrow==25.0.1
requests==2.34.2
pytest==9.1.1
```

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
```

`.gitignore`:
```
.venv/
__pycache__/
.pytest_cache/
data/
*.pbix
powerbi/**/.pbi/localSettings.json
powerbi/**/.pbi/cache.abf
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
```

`pipeline/__init__.py` e `tests/__init__.py`: arquivos vazios.

`pipeline/config.py`:
```python
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
```

- [ ] **Step 2: Escrever os testes do download**

`tests/test_extrair.py`:
```python
import pytest
import requests

from pipeline import extrair


class FakeResp:
    def __init__(self, content=b"dados", status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


def test_baixa_e_grava_arquivo(tmp_path):
    chamadas = []

    def get(url, timeout):
        chamadas.append(url)
        return FakeResp(b"conteudo")

    destino = tmp_path / "sub" / "a.zip"
    out = extrair.baixar("http://x/a.zip", destino, get=get, espera=0)
    assert out == destino
    assert destino.read_bytes() == b"conteudo"
    assert chamadas == ["http://x/a.zip"]


def test_usa_cache_quando_arquivo_existe(tmp_path):
    destino = tmp_path / "a.zip"
    destino.write_bytes(b"antigo")

    def get(url, timeout):
        raise AssertionError("não deveria baixar")

    extrair.baixar("http://x/a.zip", destino, get=get, espera=0)
    assert destino.read_bytes() == b"antigo"


def test_forcar_rebaixa(tmp_path):
    destino = tmp_path / "a.zip"
    destino.write_bytes(b"antigo")
    extrair.baixar("http://x/a.zip", destino, forcar=True,
                   get=lambda url, timeout: FakeResp(b"novo"), espera=0)
    assert destino.read_bytes() == b"novo"


def test_tenta_de_novo_e_depois_consegue(tmp_path):
    respostas = [FakeResp(status=503), FakeResp(b"ok")]
    extrair.baixar("http://x/a.zip", tmp_path / "a.zip",
                   get=lambda url, timeout: respostas.pop(0), espera=0)
    assert (tmp_path / "a.zip").read_bytes() == b"ok"


def test_falha_depois_das_tentativas_cita_url(tmp_path):
    def get(url, timeout):
        raise requests.ConnectionError("sem rede")

    with pytest.raises(extrair.ErroDownload, match="dfp_cia_aberta_2019.zip"):
        extrair.baixar("http://x/dfp_cia_aberta_2019.zip", tmp_path / "a.zip",
                       get=get, tentativas=3, espera=0)
    assert not (tmp_path / "a.zip").exists()


def test_baixar_tudo_monta_nomes(tmp_path):
    urls = []

    def get(url, timeout):
        urls.append(url)
        return FakeResp()

    dfps, cad = extrair.baixar_tudo([2015, 2016], tmp_path, get=get)
    assert dfps == {2015: tmp_path / "dfp_cia_aberta_2015.zip",
                    2016: tmp_path / "dfp_cia_aberta_2016.zip"}
    assert cad == tmp_path / "cad_cia_aberta.csv"
    assert urls[0].endswith("/DFP/DADOS/dfp_cia_aberta_2015.zip")
    assert urls[-1].endswith("/CAD/DADOS/cad_cia_aberta.csv")
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.venv\Scripts\python -m pytest tests/test_extrair.py -v`
Expected: FAIL com `ModuleNotFoundError`/`AttributeError` para `pipeline.extrair`.

- [ ] **Step 4: Implementar**

`pipeline/extrair.py`:
```python
import time
from pathlib import Path

import requests

from pipeline import config


class ErroDownload(RuntimeError):
    pass


def baixar(url, destino, *, forcar=False, tentativas=3, espera=2.0, get=requests.get):
    destino = Path(destino)
    if destino.exists() and destino.stat().st_size > 0 and not forcar:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    ultimo_erro = None
    for i in range(tentativas):
        try:
            resp = get(url, timeout=120)
            resp.raise_for_status()
            parcial = destino.with_name(destino.name + ".part")
            parcial.write_bytes(resp.content)
            parcial.replace(destino)
            return destino
        except requests.RequestException as erro:
            ultimo_erro = erro
            if i < tentativas - 1:
                time.sleep(espera * (2 ** i))
    raise ErroDownload(f"falha ao baixar {url} após {tentativas} tentativas: {ultimo_erro}")


def baixar_tudo(anos, raw_dir=config.DATA_RAW, *, forcar=False, get=requests.get):
    raw_dir = Path(raw_dir)
    dfps = {
        ano: baixar(config.URL_DFP.format(ano=ano), raw_dir / f"dfp_cia_aberta_{ano}.zip",
                    forcar=forcar, get=get)
        for ano in anos
    }
    cadastro = baixar(config.URL_CADASTRO, raw_dir / "cad_cia_aberta.csv", forcar=forcar, get=get)
    return dfps, cadastro
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv\Scripts\python -m pytest tests/test_extrair.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt pytest.ini pipeline tests
git commit -m "feat: scaffold do pipeline, config e download com cache/retry"
```

---

### Task 2: Leitura do ZIP e limpeza

**Files:**
- Create: `pipeline/leitura.py`, `pipeline/limpar.py`, `tests/conftest.py`, `tests/test_leitura.py`, `tests/test_limpar.py`

**Interfaces:**
- Consumes: `config.DEMONSTRATIVOS`
- Produces:
  - `leitura.COLUNAS: list[str]`; `leitura.ler_dfp(zip_path, ano) -> DataFrame` com as colunas CVM de `COLUNAS` (strings) + `demonstrativo` ("BP"|"DRE"|"DFC") + `tipo` ("con"|"ind").
  - `limpar.COLUNAS_SAIDA = ["cd_cvm", "cnpj", "nome", "ano", "dt_fim", "tipo_demonstrativo", "demonstrativo", "cd_conta", "ds_conta", "valor"]`; `limpar.limpar(bruto) -> DataFrame` com essas colunas: `cd_cvm` int, `ano` int, `dt_fim` datetime, `tipo_demonstrativo` "consolidado"|"individual", `valor` float em reais.
  - `tests/conftest.py`: fixture `linha_cvm` (fábrica de dicts de linha CVM crua).

- [ ] **Step 1: Fixture compartilhada**

`tests/conftest.py`:
```python
import pytest


@pytest.fixture
def linha_cvm():
    """Fábrica de uma linha crua no formato da CVM (tudo string, como lido do CSV)."""
    def _linha(cd_conta, valor, *, cd_cvm="001023", tipo="con", demonstrativo="BP",
               ds_conta="Conta", versao="1", escala="MIL", ordem="ÚLTIMO",
               dt_fim="2024-12-31", fixa="S", cnpj="00.000.000/0001-00", nome="EMPRESA X SA"):
        return {
            "CNPJ_CIA": cnpj, "CD_CVM": cd_cvm, "DENOM_CIA": nome, "VERSAO": versao,
            "ESCALA_MOEDA": escala, "ORDEM_EXERC": ordem, "DT_FIM_EXERC": dt_fim,
            "CD_CONTA": cd_conta, "DS_CONTA": ds_conta, "VL_CONTA": str(valor),
            "ST_CONTA_FIXA": fixa, "demonstrativo": demonstrativo, "tipo": tipo,
        }
    return _linha
```

- [ ] **Step 2: Testes de leitura**

`tests/test_leitura.py`:
```python
import zipfile

import pytest

from pipeline import leitura

CABECALHO = ("CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
             "ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA")


def _csv(cd_conta, ds_conta, valor):
    linha = (f"00.000.000/0001-00;2024-12-31;1;EMPRESA X SA;001023;G;REAL;MIL;"
             f"ÚLTIMO;2024-12-31;{cd_conta};{ds_conta};{valor};S")
    return (CABECALHO + "\n" + linha + "\n").encode("latin-1")


def test_le_demonstrativos_con_e_ind(tmp_path):
    zp = tmp_path / "dfp.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("dfp_cia_aberta_BPA_con_2024.csv", _csv("1", "Ativo Total", "100.0000000000"))
        z.writestr("dfp_cia_aberta_BPP_ind_2024.csv", _csv("2.03", "Patrimônio Líquido", "40.0"))
        z.writestr("dfp_cia_aberta_DFC_MI_con_2024.csv", _csv("6.01", "Caixa Líquido", "7.0"))
        z.writestr("dfp_cia_aberta_DVA_con_2024.csv", _csv("7.01", "Receitas", "1.0"))  # ignorado

    df = leitura.ler_dfp(zp, 2024)

    assert len(df) == 3
    assert set(df["demonstrativo"]) == {"BP", "DFC"}
    assert sorted(df["tipo"]) == ["con", "con", "ind"]
    assert df.loc[df["CD_CONTA"] == "2.03", "DS_CONTA"].item() == "Patrimônio Líquido"
    assert df.loc[df["CD_CONTA"] == "1", "CD_CVM"].item() == "001023"
    assert set(leitura.COLUNAS) <= set(df.columns)


def test_zip_sem_demonstrativos_da_erro(tmp_path):
    zp = tmp_path / "vazio.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("outro.csv", "x")
    with pytest.raises(ValueError, match="vazio.zip"):
        leitura.ler_dfp(zp, 2024)
```

- [ ] **Step 3: Testes de limpeza**

`tests/test_limpar.py`:
```python
import pandas as pd
import pytest

from pipeline import limpar


def _df(linhas):
    return pd.DataFrame(linhas)


def test_colunas_e_tipos(linha_cvm):
    out = limpar.limpar(_df([linha_cvm("1", "100.0")]))
    assert list(out.columns) == limpar.COLUNAS_SAIDA
    r = out.iloc[0]
    assert r["cd_cvm"] == 1023
    assert r["ano"] == 2024
    assert r["tipo_demonstrativo"] == "consolidado"


def test_escala_mil_vira_reais_e_unidade_mantem(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "100.0", escala="MIL"),
        linha_cvm("1", "100.0", cd_cvm="000002", escala="UNIDADE"),
    ]))
    assert out.set_index("cd_cvm")["valor"].to_dict() == {1023: 100_000.0, 2: 100.0}


def test_escala_desconhecida_da_erro(linha_cvm):
    with pytest.raises(ValueError, match="ESCALA_MOEDA"):
        limpar.limpar(_df([linha_cvm("1", "1.0", escala="MILHAO")]))


def test_mantem_so_ultimo_exercicio_e_contas_fixas(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "100.0"),
        linha_cvm("1", "90.0", ordem="PENÚLTIMO", dt_fim="2023-12-31"),
        linha_cvm("1.01.99", "5.0", fixa="N"),
    ]))
    assert out["cd_conta"].tolist() == ["1"]
    assert out["valor"].tolist() == [100_000.0]


def test_reapresentacao_fica_com_maior_versao(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "100.0", versao="1"),
        linha_cvm("1", "120.0", versao="2"),
    ]))
    assert out["valor"].tolist() == [120_000.0]


def test_prefere_consolidado_quando_existe(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "100.0", tipo="con"),
        linha_cvm("1", "80.0", tipo="ind"),
    ]))
    assert out["tipo_demonstrativo"].tolist() == ["consolidado"]
    assert out["valor"].tolist() == [100_000.0]


def test_usa_individual_quando_consolidado_nao_existe_ou_zerado(linha_cvm):
    out = limpar.limpar(_df([
        linha_cvm("1", "80.0", tipo="ind", cd_cvm="000001"),
        linha_cvm("1", "0.0", tipo="con", cd_cvm="000002"),
        linha_cvm("1", "70.0", tipo="ind", cd_cvm="000002"),
    ]))
    res = out.set_index("cd_cvm")
    assert res.loc[1, "tipo_demonstrativo"] == "individual"
    assert res.loc[2, "tipo_demonstrativo"] == "individual"
    assert res.loc[2, "valor"] == 70_000.0


def test_ano_vem_do_fim_do_exercicio(linha_cvm):
    out = limpar.limpar(_df([linha_cvm("1", "1.0", dt_fim="2024-03-31")]))
    assert out["ano"].item() == 2024
```

- [ ] **Step 4: Rodar e ver falhar**

Run: `.venv\Scripts\python -m pytest tests/test_leitura.py tests/test_limpar.py -v`
Expected: FAIL (módulos inexistentes).

- [ ] **Step 5: Implementar**

`pipeline/leitura.py`:
```python
import zipfile

import pandas as pd

from pipeline import config

COLUNAS = ["CNPJ_CIA", "CD_CVM", "DENOM_CIA", "VERSAO", "ESCALA_MOEDA", "ORDEM_EXERC",
           "DT_FIM_EXERC", "CD_CONTA", "DS_CONTA", "VL_CONTA", "ST_CONTA_FIXA"]


def ler_dfp(zip_path, ano):
    partes = []
    with zipfile.ZipFile(zip_path) as z:
        nomes = set(z.namelist())
        for arquivo, grupo in config.DEMONSTRATIVOS.items():
            for tipo in ("con", "ind"):
                nome = f"dfp_cia_aberta_{arquivo}_{tipo}_{ano}.csv"
                if nome not in nomes:
                    continue
                with z.open(nome) as f:
                    df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str, usecols=COLUNAS)
                df["demonstrativo"] = grupo
                df["tipo"] = tipo
                partes.append(df)
    if not partes:
        raise ValueError(f"nenhum demonstrativo encontrado em {zip_path}")
    return pd.concat(partes, ignore_index=True)
```

`pipeline/limpar.py`:
```python
import numpy as np
import pandas as pd

COLUNAS_SAIDA = ["cd_cvm", "cnpj", "nome", "ano", "dt_fim", "tipo_demonstrativo",
                 "demonstrativo", "cd_conta", "ds_conta", "valor"]

ESCALAS = {"MIL": 1000.0, "UNIDADE": 1.0}


def limpar(bruto):
    df = bruto[(bruto["ORDEM_EXERC"] == "ÚLTIMO") & (bruto["ST_CONTA_FIXA"] == "S")].copy()

    df["cd_cvm"] = df["CD_CVM"].astype(int)
    df["dt_fim"] = pd.to_datetime(df["DT_FIM_EXERC"])
    df["ano"] = df["dt_fim"].dt.year.astype(int)
    df["versao"] = df["VERSAO"].astype(int)

    # reapresentação: só a maior versão de cada demonstrativo
    maior = df.groupby(["cd_cvm", "ano", "tipo", "demonstrativo"])["versao"].transform("max")
    df = df[df["versao"] == maior].copy()

    escala = df["ESCALA_MOEDA"].map(ESCALAS)
    if escala.isna().any():
        invalidas = sorted(df.loc[escala.isna(), "ESCALA_MOEDA"].unique())
        raise ValueError(f"ESCALA_MOEDA desconhecida: {invalidas}")
    df["valor"] = df["VL_CONTA"].astype(float) * escala

    # consolidado quando existe com Ativo Total diferente de zero; senão individual
    com_con = df[(df["tipo"] == "con") & (df["CD_CONTA"] == "1") & (df["valor"] != 0)]
    chaves_con = com_con[["cd_cvm", "ano"]].drop_duplicates().assign(_tem_con=True)
    df = df.merge(chaves_con, on=["cd_cvm", "ano"], how="left")
    usar = np.where(df["_tem_con"].eq(True), "con", "ind")
    df = df[df["tipo"] == usar].copy()
    df["tipo_demonstrativo"] = df["tipo"].map({"con": "consolidado", "ind": "individual"})

    df = df.rename(columns={"CNPJ_CIA": "cnpj", "DENOM_CIA": "nome",
                            "CD_CONTA": "cd_conta", "DS_CONTA": "ds_conta"})
    return df[COLUNAS_SAIDA].reset_index(drop=True)
```

- [ ] **Step 6: Rodar e ver passar**

Run: `.venv\Scripts\python -m pytest -v`
Expected: todos passam (6 de extrair + 2 de leitura + 8 de limpar).

- [ ] **Step 7: Commit**

```bash
git add pipeline/leitura.py pipeline/limpar.py tests/conftest.py tests/test_leitura.py tests/test_limpar.py
git commit -m "feat: leitura do ZIP da DFP e regras de limpeza"
```

---

### Task 3: Cadastro e filtros

**Files:**
- Create: `pipeline/cadastro.py`, `pipeline/filtros.py`, `tests/test_cadastro.py`, `tests/test_filtros.py`

**Interfaces:**
- Consumes: `limpar.limpar` output (colunas `limpar.COLUNAS_SAIDA`); `config.ALIAS_SETOR`, `config.SETORES_FINANCEIROS`, `config.LAYOUT_ESPERADO`
- Produces:
  - `cadastro.limpar_setor(setor) -> str`; `cadastro.ler_cadastro(path) -> DataFrame[cd_cvm:int, cnpj, nome, setor, situacao]`, uma linha por `cd_cvm`.
  - `filtros.COLUNAS_PROBLEMAS = ["cd_cvm", "ano", "etapa", "problema"]`; `filtros.filtrar(limpo, cadastro) -> tuple[DataFrame, DataFrame]` = (linhas de `limpo` das empresas-ano válidas, mesmas colunas; problemas com `COLUNAS_PROBLEMAS`, `etapa="filtro"`).
  - Textos de `problema` (exatos): `"sem cadastro"`, `"setor financeiro"`, `"layout não padrão"`, `"ativo total nulo ou zero"`. Cada empresa-ano excluída gera exatamente uma linha, com o primeiro motivo nessa ordem.

- [ ] **Step 1: Testes do cadastro**

`tests/test_cadastro.py`:
```python
import pytest

from pipeline import cadastro

CAB = "CNPJ_CIA;DENOM_SOCIAL;SIT;DT_INI_SIT;CD_CVM;SETOR_ATIV\n"


@pytest.mark.parametrize("entrada, esperado", [
    ("Energia Elétrica", "Energia Elétrica"),
    ("Emp. Adm. Part. - Energia Elétrica", "Energia Elétrica"),
    ("Emp. Adm. Part.-Bolsas de Valores/Mercadorias e Futuros", "Bolsas de Valores/Mercadorias e Futuros"),
    ("Emp. Adm. Part. - Máqs., Equip., Veíc. e Peças", "Máquinas, Equipamentos, Veículos e Peças"),
    ("Emp. Adm. Part. - Sem Setor Principal", "Holdings Diversificadas"),
    ("Emp. Adm. Participações", "Holdings Diversificadas"),
    ("  Bancos ", "Bancos"),
    (None, "Não Informado"),
    ("", "Não Informado"),
])
def test_limpar_setor(entrada, esperado):
    assert cadastro.limpar_setor(entrada) == esperado


def test_ler_cadastro_deduplica_preferindo_ativo_e_mais_recente(tmp_path):
    p = tmp_path / "cad.csv"
    p.write_bytes((CAB
        + "11;VELHA SA;CANCELADA;2020-01-01;5410;Emp. Adm. Part. - Máqs., Equip., Veíc. e Peças\n"
        + "11;WEG SA;ATIVO;2010-01-01;5410;Emp. Adm. Part. - Máqs., Equip., Veíc. e Peças\n"
        + "22;VALE S.A.;ATIVO;2001-01-01;4170;Extração Mineral\n"
        + "22;VALE S.A.;ATIVO;2015-01-01;4170;Extração Mineral\n"
        + "33;SEM SETOR SA;ATIVO;2015-01-01;77;\n").encode("latin-1"))

    df = cadastro.ler_cadastro(p)

    assert list(df.columns) == ["cd_cvm", "cnpj", "nome", "setor", "situacao"]
    assert df["cd_cvm"].is_unique
    r = df.set_index("cd_cvm")
    assert r.loc[5410, "nome"] == "WEG SA"
    assert r.loc[5410, "setor"] == "Máquinas, Equipamentos, Veículos e Peças"
    assert r.loc[4170, "situacao"] == "ATIVO"
    assert r.loc[77, "setor"] == "Não Informado"
```

- [ ] **Step 2: Testes dos filtros**

`tests/test_filtros.py`:
```python
import pandas as pd

from pipeline import filtros, limpar


def _limpo(linhas):
    base = {"cnpj": "x", "nome": "X", "dt_fim": pd.Timestamp("2024-12-31"),
            "tipo_demonstrativo": "consolidado", "demonstrativo": "BP"}
    return pd.DataFrame([{**base, **l} for l in linhas])[limpar.COLUNAS_SAIDA]


def _empresa(cd, ano=2024, at=100.0, ds_pl="Patrimônio Líquido Consolidado",
             ds_ebit="Resultado Antes do Resultado Financeiro e dos Tributos"):
    return [
        {"cd_cvm": cd, "ano": ano, "cd_conta": "1", "ds_conta": "Ativo Total", "valor": at},
        {"cd_cvm": cd, "ano": ano, "cd_conta": "2.03", "ds_conta": ds_pl, "valor": 40.0},
        {"cd_cvm": cd, "ano": ano, "cd_conta": "3.05", "ds_conta": ds_ebit, "valor": 10.0},
    ]


CAD = pd.DataFrame({
    "cd_cvm": [1, 2, 3, 4],
    "cnpj": ["a", "b", "c", "d"],
    "nome": ["A", "B", "C", "D"],
    "setor": ["Energia Elétrica", "Bancos", "Alimentos", "Alimentos"],
    "situacao": ["ATIVO"] * 4,
})


def test_mantem_empresa_valida():
    filtrado, problemas = filtros.filtrar(_limpo(_empresa(1)), CAD)
    assert set(filtrado["cd_cvm"]) == {1}
    assert len(filtrado) == 3
    assert problemas.empty
    assert list(problemas.columns) == filtros.COLUNAS_PROBLEMAS


def test_exclui_e_registra_cada_motivo():
    linhas = (_empresa(1)
              + _empresa(2)                                                    # banco
              + _empresa(3, ds_pl="Passivos Financeiros ao Custo Amortizado")  # layout
              + _empresa(4, at=0.0)                                            # AT zero
              + _empresa(99))                                                  # sem cadastro
    filtrado, problemas = filtros.filtrar(_limpo(linhas), CAD)

    assert set(filtrado["cd_cvm"]) == {1}
    motivos = problemas.set_index("cd_cvm")["problema"].to_dict()
    assert motivos == {
        2: "setor financeiro",
        3: "layout não padrão",
        4: "ativo total nulo ou zero",
        99: "sem cadastro",
    }
    assert set(problemas["etapa"]) == {"filtro"}
    assert set(problemas["ano"]) == {2024}


def test_layout_exige_as_duas_contas():
    linhas = [l for l in _empresa(1) if l["cd_conta"] != "3.05"]
    filtrado, problemas = filtros.filtrar(_limpo(linhas), CAD)
    assert filtrado.empty
    assert problemas["problema"].tolist() == ["layout não padrão"]


def test_filtra_por_empresa_ano():
    linhas = _empresa(1, ano=2023, at=0.0) + _empresa(1, ano=2024)
    filtrado, problemas = filtros.filtrar(_limpo(linhas), CAD)
    assert set(filtrado["ano"]) == {2024}
    assert problemas[["cd_cvm", "ano"]].values.tolist() == [[1, 2023]]
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.venv\Scripts\python -m pytest tests/test_cadastro.py tests/test_filtros.py -v`
Expected: FAIL (módulos inexistentes).

- [ ] **Step 4: Implementar**

`pipeline/cadastro.py`:
```python
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
```

Nota: `.map(limpar_setor)` sobre coluna com NaN chama a função com NaN — `pd.isna` cobre esse caso.

`pipeline/filtros.py`:
```python
import numpy as np
import pandas as pd

from pipeline import config

COLUNAS_PROBLEMAS = ["cd_cvm", "ano", "etapa", "problema"]


def filtrar(limpo, cadastro):
    chaves = limpo[["cd_cvm", "ano"]].drop_duplicates().reset_index(drop=True)
    setor = chaves["cd_cvm"].map(cadastro.set_index("cd_cvm")["setor"])

    indice = pd.MultiIndex.from_frame(chaves)
    layout_ok = np.ones(len(chaves), dtype=bool)
    for cod, trecho in config.LAYOUT_ESPERADO.items():
        certas = limpo[(limpo["cd_conta"] == cod)
                       & limpo["ds_conta"].str.contains(trecho, regex=False, na=False)]
        tuplas = list(certas[["cd_cvm", "ano"]].itertuples(index=False, name=None))
        layout_ok &= indice.isin(tuplas)

    at = (limpo[limpo["cd_conta"] == "1"].groupby(["cd_cvm", "ano"])["valor"].first()
          .reindex(indice))
    at_invalido = (at.isna() | (at == 0)).to_numpy()

    motivo = np.select(
        [setor.isna().to_numpy(),
         setor.isin(config.SETORES_FINANCEIROS).to_numpy(),
         ~layout_ok,
         at_invalido],
        ["sem cadastro", "setor financeiro", "layout não padrão", "ativo total nulo ou zero"],
        default="",
    )

    excluidas = chaves[motivo != ""].assign(etapa="filtro", problema=motivo[motivo != ""])
    validas = chaves[motivo == ""]
    filtrado = limpo.merge(validas, on=["cd_cvm", "ano"], how="inner")
    return filtrado.reset_index(drop=True), excluidas[COLUNAS_PROBLEMAS].reset_index(drop=True)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv\Scripts\python -m pytest -v`
Expected: todos passam.

- [ ] **Step 6: Commit**

```bash
git add pipeline/cadastro.py pipeline/filtros.py tests/test_cadastro.py tests/test_filtros.py
git commit -m "feat: cadastro com setor limpo e filtros de empresas não financeiras"
```

---

### Task 4: Contas base e scores (Z''-EM, Fleuriet, tesoura)

**Files:**
- Create: `pipeline/contas_base.py`, `pipeline/scores.py`, `tests/test_contas_base.py`, `tests/test_scores.py`

**Interfaces:**
- Consumes: saída de `filtros.filtrar` (colunas `limpar.COLUNAS_SAIDA`); `config.CONTAS`, `config.CONTAS_OPCIONAIS`; `filtros.COLUNAS_PROBLEMAS`
- Produces:
  - `contas_base.montar_contas_base(filtrado) -> tuple[DataFrame, DataFrame]` = (colunas `["cd_cvm", "ano", "tipo_demonstrativo", *config.CONTAS]`, uma linha por empresa-ano; problemas com `etapa="contas_base"`, `problema="conta ausente: <coluna>"`).
  - `scores.calcular_z(df)`, `scores.classificar_fleuriet(df)`, `scores.marcar_tesoura(df)`, `scores.calcular_scores(df)` — cada uma devolve cópia com colunas novas: `x1, x2, x3, x4, z, zona` / `cdg, ncg, t, tipo_fleuriet (Int64 1–6 ou NA), situacao_fleuriet` / `efeito_tesoura (bool)`.
  - `scores.SITUACAO_FLEURIET: dict[int, str]`.

- [ ] **Step 1: Testes de contas base**

`tests/test_contas_base.py`:
```python
import math

import pandas as pd

from pipeline import config, contas_base, limpar


def _filtrado(contas, cd=1, ano=2024, dt="2024-12-31"):
    return pd.DataFrame([
        {"cd_cvm": cd, "cnpj": "x", "nome": "X", "ano": ano, "dt_fim": pd.Timestamp(dt),
         "tipo_demonstrativo": "consolidado", "demonstrativo": "BP",
         "cd_conta": cod, "ds_conta": "d", "valor": v}
        for cod, v in contas.items()
    ])[limpar.COLUNAS_SAIDA]


def _todas(valor=1.0):
    return {cod: valor for cod in config.CONTAS.values()}


def test_uma_linha_por_empresa_ano_com_todas_as_colunas():
    cb, problemas = contas_base.montar_contas_base(_filtrado(_todas()))
    assert list(cb.columns) == ["cd_cvm", "ano", "tipo_demonstrativo", *config.CONTAS]
    assert len(cb) == 1
    assert cb.loc[0, "tipo_demonstrativo"] == "consolidado"
    assert problemas.empty


def test_mapeia_codigo_para_coluna():
    contas = _todas()
    contas["2.03"] = 40.0
    contas["3.05"] = 12.0
    cb, _ = contas_base.montar_contas_base(_filtrado(contas))
    assert cb.loc[0, "patrimonio_liquido"] == 40.0
    assert cb.loc[0, "ebit"] == 12.0


def test_opcional_ausente_vira_zero_sem_problema():
    contas = _todas()
    del contas["1.01.04"]  # estoques
    cb, problemas = contas_base.montar_contas_base(_filtrado(contas))
    assert cb.loc[0, "estoques"] == 0.0
    assert problemas.empty


def test_essencial_ausente_vira_nan_e_registra():
    contas = _todas()
    del contas["6.01"]  # fco
    cb, problemas = contas_base.montar_contas_base(_filtrado(contas))
    assert math.isnan(cb.loc[0, "fco"])
    assert problemas.to_dict("records") == [
        {"cd_cvm": 1, "ano": 2024, "etapa": "contas_base", "problema": "conta ausente: fco"}
    ]


def test_duplicata_no_mesmo_ano_fica_com_exercicio_mais_recente():
    antigo = _filtrado(_todas(1.0), dt="2024-03-31")
    novo = _filtrado(_todas(2.0), dt="2024-12-31")
    cb, _ = contas_base.montar_contas_base(pd.concat([novo, antigo], ignore_index=True))
    assert len(cb) == 1
    assert cb.loc[0, "ativo_total"] == 2.0
```

- [ ] **Step 2: Testes dos scores**

`tests/test_scores.py`:
```python
import math

import pandas as pd
import pytest

from pipeline import scores


def _base(**kw):
    """Empresa-ano com contas base neutras; sobrescreva o que o teste precisa."""
    linha = {
        "cd_cvm": 1, "ano": 2024,
        "ativo_total": 100.0, "ativo_circulante": 50.0, "passivo_circulante": 30.0,
        "passivo_nao_circulante": 20.0, "ativo_nao_circulante": 50.0,
        "patrimonio_liquido": 50.0, "reservas_lucros": 10.0, "lucros_acumulados": 0.0,
        "ebit": 10.0, "caixa": 5.0, "aplicacoes_financeiras": 5.0, "emprestimos_cp": 4.0,
    }
    linha.update(kw)
    return linha


def test_formula_do_z():
    r = scores.calcular_z(pd.DataFrame([_base()])).iloc[0]
    assert r["x1"] == pytest.approx(0.20)   # (50-30)/100
    assert r["x2"] == pytest.approx(0.10)   # (10+0)/100
    assert r["x3"] == pytest.approx(0.10)   # 10/100
    assert r["x4"] == pytest.approx(1.00)   # 50/(30+20)
    assert r["z"] == pytest.approx(3.25 + 6.56 * 0.2 + 3.26 * 0.1 + 6.72 * 0.1 + 1.05 * 1.0)


def test_tres_zonas():
    df = scores.calcular_z(pd.DataFrame([
        _base(),                                     # z = 6.61 → segura
        _base(ativo_circulante=30.0),                # x1=0 → z = 5.298 → cinzenta
        _base(ativo_circulante=10.0, ebit=-30.0),    # z negativo → risco
    ]))
    assert df["zona"].tolist() == ["segura", "cinzenta", "risco"]


def test_limites_exatos_das_zonas():
    z = pd.Series([5.85, 4.15, 5.8500001, 4.1499999])
    assert scores._zona(z).tolist() == ["cinzenta", "cinzenta", "segura", "risco"]


def test_z_indeterminado_quando_exigivel_zero_ou_componente_nan():
    df = scores.calcular_z(pd.DataFrame([
        _base(passivo_circulante=0.0, passivo_nao_circulante=0.0),
        _base(ebit=float("nan")),
    ]))
    assert math.isnan(df.loc[0, "z"])
    assert df["zona"].tolist() == ["indeterminada", "indeterminada"]


def _fleuriet(cdg, t):
    """Monta contas que produzem exatamente o CDG e o T pedidos (NCG = CDG - T)."""
    # CDG = PL + PNC - ANC  com PNC=0, ANC=100  → PL = CDG + 100
    # T = caixa + aplic - emp_cp  com aplic=0, emp_cp=100 → caixa = T + 100
    return _base(patrimonio_liquido=cdg + 100.0, passivo_nao_circulante=0.0,
                 ativo_nao_circulante=100.0, caixa=t + 100.0,
                 aplicacoes_financeiras=0.0, emprestimos_cp=100.0)


@pytest.mark.parametrize("cdg, t, tipo, situacao", [
    (10.0, 30.0, 1, "Excelente"),        # ncg = -20 → (+,-,+)
    (30.0, 10.0, 2, "Sólida"),           # ncg = 20  → (+,+,+)
    (10.0, -5.0, 3, "Insatisfatória"),   # ncg = 15  → (+,+,-)
    (-10.0, -30.0, 4, "Péssima"),        # ncg = 20  → (-,+,-)
    (-30.0, -10.0, 5, "Muito ruim"),     # ncg = -20 → (-,-,-)
    (-10.0, 5.0, 6, "Alto risco"),       # ncg = -15 → (-,-,+)
    (0.0, 0.0, 2, "Sólida"),             # zero conta como positivo
])
def test_seis_tipos_fleuriet(cdg, t, tipo, situacao):
    r = scores.classificar_fleuriet(pd.DataFrame([_fleuriet(cdg, t)])).iloc[0]
    assert r["cdg"] == pytest.approx(cdg)
    assert r["t"] == pytest.approx(t)
    assert r["ncg"] == pytest.approx(cdg - t)
    assert r["tipo_fleuriet"] == tipo
    assert r["situacao_fleuriet"] == situacao


def test_fleuriet_indeterminado_com_nan():
    r = scores.classificar_fleuriet(pd.DataFrame([_base(patrimonio_liquido=float("nan"))])).iloc[0]
    assert pd.isna(r["tipo_fleuriet"])
    assert pd.isna(r["situacao_fleuriet"])


def _serie(pares, cd=1, ano0=2020):
    """pares = [(cdg, ncg), ...] em anos consecutivos a partir de ano0."""
    return pd.DataFrame([{"cd_cvm": cd, "ano": ano0 + i, "cdg": c, "ncg": n}
                         for i, (c, n) in enumerate(pares)])


def test_tesoura_exige_dois_anos_seguidos():
    # 2021: ΔNCG=10 > ΔCDG=0 ; 2022: ΔNCG=10 > ΔCDG=0 → tesoura em 2022
    df = scores.marcar_tesoura(_serie([(100, 50), (100, 60), (100, 70)]))
    assert df["efeito_tesoura"].tolist() == [False, False, True]


def test_tesoura_nao_marca_com_um_ano_so():
    df = scores.marcar_tesoura(_serie([(100, 50), (100, 60), (120, 60)]))
    assert df["efeito_tesoura"].tolist() == [False, False, False]


def test_tesoura_respeita_buraco_na_serie_e_empresas_diferentes():
    a = _serie([(100, 50), (100, 60)], cd=1, ano0=2020)          # 2020, 2021
    b = _serie([(100, 70)], cd=1, ano0=2023)                     # 2023 (2022 falta)
    c = _serie([(100, 50), (100, 60), (100, 70)], cd=2)          # outra empresa
    df = scores.marcar_tesoura(pd.concat([a, b, c], ignore_index=True))
    assert df["efeito_tesoura"].tolist() == [False, False, False, False, False, True]


def test_calcular_scores_junta_tudo():
    df = scores.calcular_scores(pd.DataFrame([_base()]))
    for col in ["z", "zona", "cdg", "ncg", "t", "tipo_fleuriet", "situacao_fleuriet", "efeito_tesoura"]:
        assert col in df.columns
```

Cheque rápido das contas de `test_tres_zonas`: linha 1 → x1=0.2, x2=0.1, x3=0.1, x4=1.0 → z = 3.25+1.312+0.326+0.672+1.05 = 6.61 (segura). Linha 2 → x1=0 → z = 5.298 (cinzenta). Linha 3 → x1=(10−30)/100=−0.2, x3=−0.3 → z = 3.25−1.312+0.326−2.016+1.05 = 1.298 (risco).

- [ ] **Step 3: Rodar e ver falhar**

Run: `.venv\Scripts\python -m pytest tests/test_contas_base.py tests/test_scores.py -v`
Expected: FAIL (módulos inexistentes).

- [ ] **Step 4: Implementar**

`pipeline/contas_base.py`:
```python
import pandas as pd

from pipeline import config
from pipeline.filtros import COLUNAS_PROBLEMAS


def montar_contas_base(filtrado):
    coluna_por_codigo = {cod: col for col, cod in config.CONTAS.items()}
    chaves = pd.MultiIndex.from_frame(filtrado[["cd_cvm", "ano"]].drop_duplicates())

    x = filtrado[filtrado["cd_conta"].isin(coluna_por_codigo)].copy()
    x["coluna"] = x["cd_conta"].map(coluna_por_codigo)
    # se a empresa tiver dois exercícios no mesmo ano civil, vale o de fim mais recente
    x = x.sort_values("dt_fim").drop_duplicates(["cd_cvm", "ano", "coluna"], keep="last")

    cb = (x.pivot(index=["cd_cvm", "ano"], columns="coluna", values="valor")
            .reindex(index=chaves, columns=list(config.CONTAS)))
    cb.columns.name = None

    essenciais = [c for c in config.CONTAS if c not in config.CONTAS_OPCIONAIS]
    problemas = []
    for col in essenciais:
        for cd_cvm, ano in cb.index[cb[col].isna()]:
            problemas.append({"cd_cvm": cd_cvm, "ano": ano, "etapa": "contas_base",
                              "problema": f"conta ausente: {col}"})

    opcionais = list(config.CONTAS_OPCIONAIS)
    cb[opcionais] = cb[opcionais].fillna(0.0)

    tipo = (filtrado.sort_values("dt_fim").groupby(["cd_cvm", "ano"])["tipo_demonstrativo"].last())
    cb.insert(0, "tipo_demonstrativo", tipo.reindex(cb.index))
    cb = cb.reset_index()
    return cb, pd.DataFrame(problemas, columns=COLUNAS_PROBLEMAS)
```

`pipeline/scores.py`:
```python
import numpy as np
import pandas as pd

LIMITE_SEGURA = 5.85
LIMITE_RISCO = 4.15

SITUACAO_FLEURIET = {1: "Excelente", 2: "Sólida", 3: "Insatisfatória",
                     4: "Péssima", 5: "Muito ruim", 6: "Alto risco"}

# (cdg >= 0, ncg >= 0, t >= 0) -> tipo
_TIPOS = {(True, False, True): 1, (True, True, True): 2, (True, True, False): 3,
          (False, True, False): 4, (False, False, False): 5, (False, False, True): 6}


def _zona(z):
    return pd.Series(
        np.select([z.isna(), z > LIMITE_SEGURA, z >= LIMITE_RISCO],
                  ["indeterminada", "segura", "cinzenta"], default="risco"),
        index=z.index,
    )


def calcular_z(df):
    df = df.copy()
    at = df["ativo_total"].where(df["ativo_total"] != 0)
    exigivel = df["passivo_circulante"] + df["passivo_nao_circulante"]
    df["x1"] = (df["ativo_circulante"] - df["passivo_circulante"]) / at
    df["x2"] = (df["reservas_lucros"] + df["lucros_acumulados"]) / at
    df["x3"] = df["ebit"] / at
    df["x4"] = df["patrimonio_liquido"] / exigivel.where(exigivel != 0)
    df["z"] = 3.25 + 6.56 * df["x1"] + 3.26 * df["x2"] + 6.72 * df["x3"] + 1.05 * df["x4"]
    df["zona"] = _zona(df["z"])
    return df


def classificar_fleuriet(df):
    df = df.copy()
    df["cdg"] = (df["patrimonio_liquido"] + df["passivo_nao_circulante"]) - df["ativo_nao_circulante"]
    df["t"] = (df["caixa"] + df["aplicacoes_financeiras"]) - df["emprestimos_cp"]
    df["ncg"] = df["cdg"] - df["t"]
    tipos = [
        pd.NA if pd.isna(cdg) or pd.isna(t) else _TIPOS.get((cdg >= 0, ncg >= 0, t >= 0), pd.NA)
        for cdg, ncg, t in zip(df["cdg"], df["ncg"], df["t"])
    ]
    df["tipo_fleuriet"] = pd.array(tipos, dtype="Int64")
    df["situacao_fleuriet"] = df["tipo_fleuriet"].map(SITUACAO_FLEURIET)
    return df


def marcar_tesoura(df):
    df = df.copy()
    base = df[["cd_cvm", "ano", "cdg", "ncg"]].reset_index(drop=True)
    anterior = (base.assign(ano=base["ano"] + 1)
                    .rename(columns={"cdg": "cdg_ant", "ncg": "ncg_ant"}))
    m = base.merge(anterior, on=["cd_cvm", "ano"], how="left")
    m["piorou"] = (m["ncg"] - m["ncg_ant"]) > (m["cdg"] - m["cdg_ant"])
    piorou_ant = (m[["cd_cvm", "ano", "piorou"]].assign(ano=m["ano"] + 1)
                    .rename(columns={"piorou": "piorou_ant"}))
    m = m.merge(piorou_ant, on=["cd_cvm", "ano"], how="left")
    df["efeito_tesoura"] = (m["piorou"] & m["piorou_ant"].eq(True)).to_numpy(dtype=bool)
    return df


def calcular_scores(df):
    return marcar_tesoura(classificar_fleuriet(calcular_z(df)))
```

Nota: `merge(how="left")` preserva a ordem das linhas da esquerda e, como `(cd_cvm, ano)` é único, não duplica linhas — por isso o `to_numpy()` alinha com `df`.

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv\Scripts\python -m pytest -v`
Expected: todos passam.

- [ ] **Step 6: Commit**

```bash
git add pipeline/contas_base.py pipeline/scores.py tests/test_contas_base.py tests/test_scores.py
git commit -m "feat: contas base por empresa-ano e scores Z''-EM, Fleuriet e tesoura"
```

---

### Task 5: Índices de referência, exportação e CLI

**Files:**
- Create: `pipeline/indices.py`, `pipeline/exportar.py`, `pipeline/cli.py`, `pipeline/__main__.py`, `tests/test_indices.py`, `tests/test_exportar.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `extrair.baixar_tudo`, `leitura.ler_dfp`, `limpar.limpar`, `cadastro.ler_cadastro`, `filtros.filtrar`, `contas_base.montar_contas_base`, `scores.calcular_scores`
- Produces:
  - `indices.INDICES: list[str]` = `["liquidez_corrente", "liquidez_seca", "endividamento_geral", "divida_liquida_pl", "cobertura_juros", "margem_ebit", "margem_liquida", "roa", "roe"]`; `indices.calcular_indices(fato) -> DataFrame[cd_cvm, ano, *INDICES]`. Estas fórmulas são o contrato que as medidas DAX do Plano B precisam reproduzir.
  - `exportar.exportar(fato, cadastro, problemas, out_dir) -> dict[str, Path]` gravando `fato_indicadores.parquet`, `dim_empresa.parquet`, `dim_setor.parquet`, `qualidade.parquet`.
  - `cli.run(anos, *, forcar=False, raw_dir=config.DATA_RAW, out_dir=config.DATA_PROCESSED, get=requests.get) -> dict[str, Path]`; `cli.main(argv=None) -> int`; comandos `python -m pipeline run [--anos 2015-2025] [--forcar]` e `python -m pipeline referencia --cvm 9512 4170 ... [--saida docs/referencia_indices.csv]`.

- [ ] **Step 1: Testes dos índices**

`tests/test_indices.py`:
```python
import math

import pandas as pd
import pytest

from pipeline import indices


def _fato(**kw):
    linha = {
        "cd_cvm": 1, "ano": 2024,
        "ativo_total": 200.0, "ativo_circulante": 80.0, "estoques": 20.0,
        "passivo_circulante": 40.0, "passivo_nao_circulante": 60.0,
        "patrimonio_liquido": 100.0, "caixa": 10.0, "aplicacoes_financeiras": 5.0,
        "emprestimos_cp": 15.0, "emprestimos_lp": 30.0,
        "receita_liquida": 400.0, "ebit": 50.0, "despesas_financeiras": -25.0,
        "lucro_liquido": 20.0,
    }
    linha.update(kw)
    return pd.DataFrame([linha])


def test_formulas():
    r = indices.calcular_indices(_fato()).iloc[0]
    assert r["liquidez_corrente"] == pytest.approx(2.0)       # 80/40
    assert r["liquidez_seca"] == pytest.approx(1.5)           # (80-20)/40
    assert r["endividamento_geral"] == pytest.approx(0.5)     # (40+60)/200
    assert r["divida_liquida_pl"] == pytest.approx(0.3)       # (15+30-10-5)/100
    assert r["cobertura_juros"] == pytest.approx(2.0)         # 50/|−25|
    assert r["margem_ebit"] == pytest.approx(0.125)           # 50/400
    assert r["margem_liquida"] == pytest.approx(0.05)         # 20/400
    assert r["roa"] == pytest.approx(0.1)                     # 20/200
    assert r["roe"] == pytest.approx(0.2)                     # 20/100


def test_colunas():
    assert list(indices.calcular_indices(_fato()).columns) == ["cd_cvm", "ano", *indices.INDICES]


def test_denominador_zero_vira_nan():
    r = indices.calcular_indices(_fato(passivo_circulante=0.0, receita_liquida=0.0,
                                       despesas_financeiras=0.0)).iloc[0]
    for col in ["liquidez_corrente", "liquidez_seca", "margem_ebit", "margem_liquida", "cobertura_juros"]:
        assert math.isnan(r[col]), col


def test_pl_nao_positivo_anula_indices_sobre_pl():
    r = indices.calcular_indices(_fato(patrimonio_liquido=-10.0)).iloc[0]
    assert math.isnan(r["roe"])
    assert math.isnan(r["divida_liquida_pl"])
    assert not math.isnan(r["roa"])
```

- [ ] **Step 2: Testes de exportação e CLI**

`tests/test_exportar.py`:
```python
import pandas as pd

from pipeline import exportar


def test_grava_quatro_parquets(tmp_path):
    fato = pd.DataFrame({"cd_cvm": [1, 1, 2], "ano": [2023, 2024, 2024],
                         "tipo_demonstrativo": ["individual", "consolidado", "consolidado"],
                         "z": [5.0, 6.0, 3.0]})
    cadastro = pd.DataFrame({"cd_cvm": [1, 2, 3], "cnpj": ["a", "b", "c"], "nome": ["A", "B", "C"],
                             "setor": ["Alimentos", "Energia Elétrica", "Bancos"],
                             "situacao": ["ATIVO"] * 3})
    problemas = pd.DataFrame({"cd_cvm": [3], "ano": [2024], "etapa": ["filtro"],
                              "problema": ["setor financeiro"]})

    caminhos = exportar.exportar(fato, cadastro, problemas, tmp_path / "out")

    assert sorted(caminhos) == ["dim_empresa", "dim_setor", "fato_indicadores", "qualidade"]
    dim = pd.read_parquet(caminhos["dim_empresa"]).set_index("cd_cvm")
    assert sorted(dim.index) == [1, 2]                       # só quem está na fato
    assert dim.loc[1, "tipo_demonstrativo"] == "consolidado"  # o do ano mais recente
    assert pd.read_parquet(caminhos["dim_setor"])["setor"].tolist() == ["Alimentos", "Energia Elétrica"]
    assert len(pd.read_parquet(caminhos["fato_indicadores"])) == 3
    assert pd.read_parquet(caminhos["qualidade"])["problema"].tolist() == ["setor financeiro"]


def test_reexecutar_sobrescreve(tmp_path):
    fato = pd.DataFrame({"cd_cvm": [1], "ano": [2024], "tipo_demonstrativo": ["consolidado"]})
    cad = pd.DataFrame({"cd_cvm": [1], "cnpj": ["a"], "nome": ["A"], "setor": ["X"], "situacao": ["ATIVO"]})
    vazio = pd.DataFrame(columns=["cd_cvm", "ano", "etapa", "problema"])
    exportar.exportar(fato, cad, vazio, tmp_path)
    c = exportar.exportar(fato, cad, vazio, tmp_path)
    assert len(pd.read_parquet(c["fato_indicadores"])) == 1
```

`tests/test_cli.py` (ponta a ponta com ZIP e cadastro sintéticos, sem rede):
```python
import zipfile

import pandas as pd

from pipeline import cli, config

CAB = ("CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
       "ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA\n")

DESCRICOES = {"2.03": "Patrimônio Líquido Consolidado",
              "3.05": "Resultado Antes do Resultado Financeiro e dos Tributos"}


def _zip(path, ano):
    arquivos = {"BPA": "1", "BPP": "2", "DRE": "3", "DFC_MI": "6"}
    with zipfile.ZipFile(path, "w") as z:
        for dem, prefixo in arquivos.items():
            linhas = [
                f"11;{ano}-12-31;1;EMPRESA A;000010;G;REAL;MIL;ÚLTIMO;{ano}-12-31;"
                f"{cod};{DESCRICOES.get(cod, 'Conta')};100.0;S\n"
                for cod in config.CONTAS.values()
                if cod.split(".")[0] == prefixo
            ]
            z.writestr(f"dfp_cia_aberta_{dem}_con_{ano}.csv", (CAB + "".join(linhas)).encode("latin-1"))


def test_run_ponta_a_ponta(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for ano in (2023, 2024):
        _zip(raw / f"dfp_cia_aberta_{ano}.zip", ano)
    (raw / "cad_cia_aberta.csv").write_bytes(
        ("CNPJ_CIA;DENOM_SOCIAL;SIT;DT_INI_SIT;CD_CVM;SETOR_ATIV\n"
         "11;EMPRESA A SA;ATIVO;2010-01-01;10;Alimentos\n").encode("latin-1"))

    def get(url, timeout):
        raise AssertionError("não deveria baixar: arquivos estão em cache")

    caminhos = cli.run([2023, 2024], raw_dir=raw, out_dir=tmp_path / "out", get=get)

    fato = pd.read_parquet(caminhos["fato_indicadores"])
    assert fato[["cd_cvm", "ano"]].values.tolist() == [[10, 2023], [10, 2024]]
    assert (fato["ativo_total"] == 100_000.0).all()
    assert set(fato["zona"]) <= {"segura", "cinzenta", "risco", "indeterminada"}


def test_parse_anos():
    assert list(cli._parse_anos("2015-2017")) == [2015, 2016, 2017]
    assert list(cli._parse_anos("2020")) == [2020]
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.venv\Scripts\python -m pytest tests/test_indices.py tests/test_exportar.py tests/test_cli.py -v`
Expected: FAIL (módulos inexistentes).

- [ ] **Step 4: Implementar**

`pipeline/indices.py`:
```python
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
```

`pipeline/exportar.py`:
```python
from pathlib import Path

import pandas as pd


def exportar(fato, cadastro, problemas, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tipo_recente = fato.sort_values("ano").groupby("cd_cvm")["tipo_demonstrativo"].last()
    dim_empresa = cadastro[cadastro["cd_cvm"].isin(fato["cd_cvm"].unique())].copy()
    dim_empresa["tipo_demonstrativo"] = dim_empresa["cd_cvm"].map(tipo_recente)
    dim_setor = pd.DataFrame({"setor": sorted(dim_empresa["setor"].unique())})

    tabelas = {
        "fato_indicadores": fato,
        "dim_empresa": dim_empresa,
        "dim_setor": dim_setor,
        "qualidade": problemas,
    }
    caminhos = {}
    for nome, df in tabelas.items():
        caminho = out_dir / f"{nome}.parquet"
        df.reset_index(drop=True).to_parquet(caminho, index=False)
        caminhos[nome] = caminho
    return caminhos
```

`pipeline/cli.py`:
```python
import argparse
import sys
from pathlib import Path

import pandas as pd
import requests

from pipeline import config
from pipeline.cadastro import ler_cadastro
from pipeline.contas_base import montar_contas_base
from pipeline.exportar import exportar
from pipeline.extrair import baixar_tudo
from pipeline.filtros import filtrar
from pipeline.indices import calcular_indices
from pipeline.leitura import ler_dfp
from pipeline.limpar import limpar
from pipeline.scores import calcular_scores


def _parse_anos(texto):
    if "-" in texto:
        ini, fim = texto.split("-")
        return range(int(ini), int(fim) + 1)
    return range(int(texto), int(texto) + 1)


def run(anos, *, forcar=False, raw_dir=config.DATA_RAW, out_dir=config.DATA_PROCESSED,
        get=requests.get):
    dfps, caminho_cad = baixar_tudo(anos, raw_dir, forcar=forcar, get=get)
    cadastro = ler_cadastro(caminho_cad)
    limpo = pd.concat([limpar(ler_dfp(p, ano)) for ano, p in dfps.items()], ignore_index=True)
    filtrado, prob_filtro = filtrar(limpo, cadastro)
    cb, prob_contas = montar_contas_base(filtrado)
    fato = calcular_scores(cb)
    problemas = pd.concat([prob_filtro, prob_contas], ignore_index=True)
    caminhos = exportar(fato, cadastro, problemas, out_dir)
    print(f"{fato['cd_cvm'].nunique()} empresas, {len(fato)} empresas-ano, "
          f"{len(problemas)} problemas registrados → {Path(out_dir)}")
    return caminhos


def referencia(cvms, *, out_dir=config.DATA_PROCESSED, saida=config.RAIZ / "docs" / "referencia_indices.csv"):
    fato = pd.read_parquet(Path(out_dir) / "fato_indicadores.parquet")
    ref = calcular_indices(fato[fato["cd_cvm"].isin(cvms)])
    ref = ref.merge(fato[["cd_cvm", "ano", "z", "zona", "tipo_fleuriet"]], on=["cd_cvm", "ano"])
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    ref.sort_values(["cd_cvm", "ano"]).to_csv(saida, index=False, float_format="%.6f")
    print(f"{len(ref)} linhas de referência → {saida}")
    return saida


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m pipeline")
    sub = parser.add_subparsers(dest="comando", required=True)
    p_run = sub.add_parser("run", help="baixa, trata e exporta os Parquet")
    p_run.add_argument("--anos", default=f"{config.ANOS_PADRAO.start}-{config.ANOS_PADRAO.stop - 1}")
    p_run.add_argument("--forcar", action="store_true", help="rebaixa arquivos já em cache")
    p_ref = sub.add_parser("referencia", help="gera índices de referência para validar o DAX")
    p_ref.add_argument("--cvm", type=int, nargs="+", required=True)
    p_ref.add_argument("--saida", default=str(config.RAIZ / "docs" / "referencia_indices.csv"))
    args = parser.parse_args(argv)

    if args.comando == "run":
        run(_parse_anos(args.anos), forcar=args.forcar)
    else:
        referencia(args.cvm, saida=args.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`pipeline/__main__.py`:
```python
import sys

from pipeline.cli import main

sys.exit(main())
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.venv\Scripts\python -m pytest -v`
Expected: todos passam.

- [ ] **Step 6: Commit**

```bash
git add pipeline tests
git commit -m "feat: índices de referência, exportação Parquet e CLI"
```

---

### Task 6: Execução real e conferência com as DFP publicadas

Esta task é executada pelo **controlador** (sessão principal), não por um subagente isolado: exige rede, julgamento sobre os dados reais e consulta às demonstrações publicadas.

**Files:**
- Create: `docs/conferencia-dados-reais.md`, `docs/referencia_indices.csv` (gerado)
- Modify: `pipeline/config.py` somente se a conferência revelar variação de layout/setor não prevista (cada ajuste com teste novo em Task correspondente)

- [ ] **Step 1: Rodar o pipeline completo**

Run: `.venv\Scripts\python -m pipeline run`
Expected: 11 ZIPs + cadastro em `data/raw/`, quatro Parquet em `data/processed/`, resumo impresso com ~350–450 empresas.

- [ ] **Step 2: Inspecionar a qualidade**

```powershell
.venv\Scripts\python -c "import pandas as pd; q=pd.read_parquet('data/processed/qualidade.parquet'); print(q.groupby(['etapa','problema']).size().sort_values(ascending=False).head(20)); f=pd.read_parquet('data/processed/fato_indicadores.parquet'); print(f.groupby('ano').size()); print(f.zona.value_counts()); print(f.tipo_fleuriet.value_counts(dropna=False))"
```

Checar: nenhum ano com contagem muito fora da média; "sem cadastro" pequeno; "conta ausente" concentrado em poucas contas (se uma conta falta para muitas empresas, é variação de layout → investigar e corrigir o mapeamento antes de seguir); distribuição de zonas plausível (não 100% numa zona).

- [ ] **Step 3: Gerar referência das 5 empresas**

Run: `.venv\Scripts\python -m pipeline referencia --cvm 9512 4170 5410 23264 22470`

- [ ] **Step 4: Conferir contra as demonstrações publicadas**

Para cada uma das 5 empresas, no exercício 2024, comparar Ativo Total, Patrimônio Líquido e Lucro Líquido do `fato_indicadores` com os valores das demonstrações financeiras publicadas (site de RI ou sistema Empresas.NET da CVM). Tolerância: diferença < 0,1% (arredondamento). Registrar a tabela em `docs/conferencia-dados-reais.md` com fonte de cada número.

- [ ] **Step 5: Commit**

```bash
git add docs/conferencia-dados-reais.md docs/referencia_indices.csv
git commit -m "docs: conferência do pipeline com demonstrações publicadas"
```

---

## Depois deste plano

**Plano B — Power BI** (escrito quando Task 6 estiver concluída): projeto `.pbip` em `powerbi/`, Power Query lendo os Parquet de `data/processed/`, relações do esquema estrela, `dim_ano`, medidas DAX (índices espelhando `pipeline/indices.py`, mediana/quartil do setor, migração de zona), as quatro páginas da spec, dicionário de métricas, validação cruzada DAX × `docs/referencia_indices.csv` via MCP e checklist de QA.
