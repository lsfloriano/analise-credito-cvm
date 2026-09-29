# Análise de crédito de companhias abertas (CVM)

Um pipeline em Python lê os demonstrativos financeiros que a CVM publica e
monta um modelo estrela em Parquet. Sobre ele, um relatório Power BI faz a
triagem de risco de crédito das companhias abertas brasileiras não
financeiras, de 2015 a 2025. A pergunta que o relatório tenta responder é a
do analista de crédito: essa empresa consegue honrar suas obrigações, e está
melhorando ou piorando?

A base tem 830 empresas e 6.266 empresas-ano, tiradas das DFP anuais. Além de
9 índices clássicos com comparação setorial, o relatório usa dois modelos de
crédito: o Altman Z''-EM e o Modelo Fleuriet, com o alerta de efeito tesoura.
Os números foram conferidos contra as demonstrações publicadas e por testes
unitários do pipeline, que cobrem as fórmulas do Z e do Fleuriet. Os índices
e benchmarks calculados em DAX foram comparados com o Python em todas as
6.266 empresas-ano, sem divergência.

![Triagem de risco](docs/screenshots/01-triagem.png)

## Os modelos de crédito

### Altman Z''-EM

É a versão do Z-score de Altman para mercados emergentes. Usa só valores
contábeis, sem valor de mercado:

```
X1 = (Ativo Circulante − Passivo Circulante) / Ativo Total          capital de giro
X2 = (Reservas de Lucros + Lucros Acumulados) / Ativo Total          lucros retidos
X3 = EBIT / Ativo Total                                              rentabilidade operacional
X4 = Patrimônio Líquido / (Passivo Circulante + Não Circulante)      alavancagem

Z''-EM = 3,25 + 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4
```

| Zona | Faixa | Leitura |
|---|---|---|
| Segura | Z > 5,85 | baixo risco de insolvência |
| Cinzenta | 4,15 ≤ Z ≤ 5,85 | atenção |
| Risco | Z < 4,15 | perfil parecido com o de empresas que quebraram |
| Indeterminada | sem faixa | falta componente, ou passivo exigível zero |

O modelo foi calibrado fora do Brasil, então aqui ele serve para decidir
quem olhar primeiro. Ele não estima a probabilidade de default.

### Modelo Fleuriet

O Fleuriet lê o balanço pelo capital de giro e separa o financiamento de
longo prazo, a operação e a tesouraria:

```
CDG = (Patrimônio Líquido + Passivo Não Circulante) − Ativo Não Circulante   capital de giro
T   = (Caixa + Aplicações Financeiras) − Empréstimos de Curto Prazo           saldo de tesouraria
NCG = CDG − T                                                                 necessidade de capital de giro
```

| Tipo | CDG | NCG | T | Situação |
|---|---|---|---|---|
| I | + | − | + | Excelente |
| II | + | + | + | Sólida |
| III | + | + | − | Insatisfatória |
| IV | − | + | − | Péssima |
| V | − | − | − | Muito ruim |
| VI | − | − | + | Alto risco |

O efeito tesoura acende quando a NCG cresce mais que o CDG por dois anos
seguidos. Nesse caso a empresa está financiando a operação com dívida de
curto prazo, e o saldo de tesouraria afunda. Quando faltam dois anos
anteriores comparáveis, o campo mostra "sem histórico". Esses casos ficam
fora do denominador da "% com alerta", porque falta de histórico não quer
dizer que o risco é baixo.

## O relatório

| Página | Para quê |
|---|---|
| Triagem de risco | Cartões por zona com a variação anual, matriz de migração entre zonas (o ano base pode ser escolhido) e tabela de empresas ordenada pelo Z, com zona, tipo Fleuriet e alerta de tesoura. Clique direito numa empresa e escolha *Detalhamento* para abrir a ficha. |
| Ficha da empresa | Z e zona, os 10 índices com a mediana e o quartil do setor e a variação anual, o Z ao longo do tempo com as faixas das zonas, e CDG, NCG e T por ano. |
| Panorama setorial | Q1, mediana e Q3 de qualquer índice por setor, e a % de empresas em risco ao longo do tempo. |
| Qualidade dos dados | O que o pipeline excluiu ou marcou, e por quê. |

| | |
|---|---|
| ![Ficha](docs/screenshots/02-ficha.png) | ![Panorama](docs/screenshots/03-panorama.png) |
| ![Qualidade](docs/screenshots/04-qualidade.png) | |

## Arquitetura

```
CVM (ZIP/CSV) → extrair → limpar → filtrar → contas_base → scores → exportar → Parquet → Power BI (PBIP)
```

Cada etapa do pipeline (`pipeline/`) é um módulo que recebe e devolve
DataFrames, e todas podem ser testadas sem rede. O pipeline baixa a DFP
anual de 2015 a 2025 e o cadastro da CVM, com cache e 3 tentativas. De cada
período fica só a versão mais recente, para tratar reapresentações. A escala
MIL vira reais, o consolidado é usado quando existe (o individual é o
fallback) e só entram as contas fixas do plano CVM. Instituições financeiras
saem, porque o layout do demonstrativo delas é outro, e também saem as
empresas sem cadastro ou com ativo total zero. Cada exclusão ou problema
vira uma linha no log de qualidade em vez de uma exceção.

O modelo semântico (`powerbi/`, formato PBIP/TMDL) é uma estrela:
`fato_indicadores`, com uma linha por empresa-ano, ligada a `dim_empresa`,
`dim_ano` e `dim_zona`, e `dim_setor` ligada a `dim_empresa`. Todas as
relações são 1:N com filtro unidirecional. No DAX:

- Os índices só são calculados para uma empresa-ano por vez. Num total, o
  numerador e o denominador somariam balanços de empresas diferentes, e o
  resultado não descreve empresa nenhuma.
- O grupo de cálculo `Benchmark` dá a mediana, Q1 e Q3, o percentil, o
  quartil e a variação anual do setor para qualquer índice. Com o seletor
  `[Valor do Índice]`, a comparação da ficha inteira cabe numa matriz.
- A matriz de migração compara as zonas de dois anos (por padrão, o ano
  anterior), com tabelas desconectadas para o ano base e a zona de origem.
- Na exibição, o Z fica limitado a ±25. Cerca de 7% das empresas-ano têm Z
  extremo por causa de ativo irrisório; o Z real continua disponível e é ele
  que define a zona.

O dicionário de métricas,
[`docs/dicionario-metricas.md`](docs/dicionario-metricas.md), explica cada
medida.

## Como rodar

Precisa de Python 3.13 e do Power BI Desktop, numa versão que abra PBIP.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt       # Windows; em Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pipeline run                 # baixa 2015–2025 e grava data/processed/*.parquet
```

`--anos 2020-2025` restringe o período, e `--forcar` baixa de novo os
arquivos que já estão em cache.

Depois:

1. Abra `powerbi/analise-credito-cvm.pbip` no Power BI Desktop.
2. Ajuste o parâmetro `PastaDados` para a sua pasta `data\processed\`, em
   *Página Inicial > Transformar dados > Editar parâmetros*. O caminho
   termina em barra invertida.
3. Clique em Atualizar.

Os testes rodam com `.venv/Scripts/python -m pytest` (82 testes, sem acesso
à rede).

## Verificação

| Verificação | Onde | Resultado |
|---|---|---|
| Testes unitários do pipeline e da validação | `tests/` | 82 passam |
| Ativo Total, PL e Lucro Líquido contra as DFP publicadas (WEG, Vale, Ambev, Magazine Luiza, Petrobras) | [`docs/conferencia-dados-reais.md`](docs/conferencia-dados-reais.md) | batem |
| Medidas DAX × Python: índices, Z, zona e tipo Fleuriet em todas as 6.266 empresas-ano; mediana e quartis por setor-ano; percentil; migração de zona | [`docs/validacao-dax.md`](docs/validacao-dax.md) | 0 divergências |
| QA do relatório: interações, detalhamento, totais, formatos, desempenho | checklist de QA | ok |

A comparação entre DAX e Python pode ser repetida. A consulta DAX roda no
modelo e o resultado vai para um CSV; `python -m pipeline validar-dax <tipo>
<csv>` compara esse CSV com os índices recalculados em Python. Foi assim que
apareceram os dois defeitos de DAX descritos em `docs/validacao-dax.md`.

## Limitações conhecidas

- Rodar com `--anos` parcial sobrescreve as saídas completas: `--anos 2024`
  deixa os Parquet só com 2024.
- Quando uma empresa troca a data de encerramento, pode haver dois exercícios
  no mesmo ano civil (cerca de 6 empresas-ano). Fica o de fim mais recente, e
  a DRE dele pode cobrir menos de 12 meses.
- As medianas setoriais contam controladoras (pelo consolidado) e controladas
  listadas como empresas separadas, então um mesmo grupo pode entrar mais de
  uma vez.
- Nas holdings, o EBIT inclui equivalência patrimonial, e muitas têm receita
  zero. Receita zero atinge 8,6% das empresas-ano, que ficam sem margens. Os
  12,7% com PL ≤ 0 ficam sem ROE e sem Dívida Líquida/PL.
- 434 empresas-ano têm |Z| > 25, quase sempre empresas sem operação. Na
  exibição elas aparecem como "< -25" ou "> 25".
- A Multilaser ficou de fora porque o CD_CVM da DFP não bate com o do
  cadastro, e o pipeline não tenta casar por CNPJ. As outras 19 empresas "sem
  cadastro" são emissores estrangeiros.
- Ficaram fora do escopo os dados trimestrais (ITR), os dados de mercado
  (cotação, valor de mercado), o EBITDA (a depreciação não é conta fixa),
  bancos e seguradoras, e o layout para celular.

## Documentação

- Spec de design: [`docs/superpowers/specs/2026-09-23-analise-credito-cvm-design.md`](docs/superpowers/specs/2026-09-23-analise-credito-cvm-design.md)
- Planos: [pipeline](docs/superpowers/plans/2026-09-23-pipeline-cvm.md) ·
  [relatório Power BI](docs/superpowers/plans/2026-09-23-powerbi-relatorio.md)
- [Dicionário de métricas](docs/dicionario-metricas.md) ·
  [Roteiro de visuais](docs/roteiro-visuais.md) ·
  [Validação DAX × Python](docs/validacao-dax.md) ·
  [Conferência com dados reais](docs/conferencia-dados-reais.md)

Fonte dos dados: [Dados Abertos CVM](https://dados.cvm.gov.br/), com a DFP
de companhias abertas e o cadastro.
