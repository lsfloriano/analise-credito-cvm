# Roteiro de visuais — relatório de crédito CVM

Guia página a página para montar o relatório no Power BI Desktop sobre o
modelo de `powerbi/`. O modelo, as medidas e os números já estão validados
(`docs/validacao-dax.md`); aqui é só apresentação. Ao terminar cada página,
salve (Ctrl+S) e mande o print para revisão.

## Regras gerais

- **Tela:** 16:9, 1280 × 720 (*Formatar página → Configurações de tela*).
- **Tema:** comece do Fluent 2 e ajuste as cores de dados. As 4 cores de
  zona são fixas: segura `#2E7D32`, cinzenta `#F9A825`, risco `#C62828`,
  indeterminada `#9E9E9E`. Onde houver campo de zona na legenda, fixe essas
  cores manualmente.
- **Fonte:** Segoe UI; títulos de visual 12, rótulos 10, rodapés 9.
- **Faixa de título** no topo de cada página (caixa de texto, 40 px de
  altura): nome da página à esquerda e a segmentação de ano à direita.
- **Sempre colunas de dimensão:** empresa = `dim_empresa[empresa]` (que
  mostra "nome (cd_cvm)"); ano = `dim_ano[ano]`; setor = `dim_setor[setor]`;
  zona = `dim_zona[zona]`. Não use campos de `fato_indicadores` nos eixos:
  o filtro não sobe para as dimensões e o benchmark sai errado.
- **Medidas implícitas estão desligadas** por causa do grupo de cálculo.
  Todo valor numérico vem da tabela `Medidas`.
- **Segmentação de ano:** `dim_ano[ano]`, lista suspensa, **seleção única**,
  valor 2025. Sincronize nas páginas 1, 2 e 3 (*Exibir → Sincronizar
  segmentações*, com "sincronizar" e "visível" marcados nas três). A
  página 4 não usa.
- **Índices em branco são intencionais** (PL ≤ 0, receita zero, total de
  vários itens). Não troque o branco por zero.

---

## Página 1 — Triagem de risco

Pergunta: *quais empresas olhar primeiro, e o quadro está melhorando?*

| # | Visual | Campos | Configuração |
|---|---|---|---|
| 1 | Segmentação | `dim_ano[ano]` | a sincronizada (regras gerais) |
| 2 | Segmentação | `dim_setor[setor]` | lista suspensa, multisseleção, caixa de pesquisa ligada |
| 3 | Segmentação | `dim_zona[zona]` | estilo botões, horizontal. **Editar interações:** ela filtra **só** a tabela (#8); nos cartões (#4–6) e na matriz (#7), marque "nenhum" |
| 4 | Cartão (novo) "Zona segura" | Valor `[Empresas]`; filtro do visual `dim_zona[zona]` = segura; rótulo de referência `[Δ Empresas vs Ano Anterior]` | cor do valor `#2E7D32`; rótulo de referência com legenda "vs ano anterior" |
| 5 | Cartão (novo) "Zona cinzenta" | idem, com cinzenta | cor `#F9A825` |
| 6 | Cartão (novo) "Zona de risco" | idem, com risco | cor `#C62828` |
| 7 | Matriz "Migração de zona" | Linhas `zona_origem[zona_origem]`; Colunas `dim_zona[zona]`; Valores `[Migração de Zona]` | ao lado, segmentação `ano_base[ano_base]` (lista suspensa, seleção única, 2024, título "Ano base"). Fundo das células em escala de cor (branco → `#37474F`). Linhas = zona no ano base; colunas = zona no ano selecionado; a diagonal é quem ficou na mesma zona. Título: "Migração entre zonas (linha: ano base; coluna: ano selecionado)" |
| 8 | Tabela "Empresas" | `dim_empresa[empresa]`, `dim_setor[setor]`, `[Z''-EM (exibição)]`, `[Fora da Escala]`, `[Zona]`, `[Tipo Fleuriet]`, `[Δ Z''-EM (exibição)]`, `[Efeito Tesoura]` | ordenar por `[Z''-EM (exibição)]` crescente (piores primeiro; as fora da escala empatam em −25 e aparecem como "< -25"). Subtítulo: "Z limitado a ±25; Δ em branco = sem ano anterior ou fora da escala". Formatação condicional: fundo de `[Zona]` por **valor de campo** `[Cor da Zona]`, fonte branca; ícones em `[Δ Z''-EM (exibição)]` (seta verde se > 0, vermelha se < 0). Cabeçalhos: "Empresa", "Setor", "Z''-EM", "Z real", "Zona", "Fleuriet", "Δ Z", "Efeito tesoura" |
| 9 | Cartão (novo) | `[% com Efeito Tesoura]` | título "Com alerta de efeito tesoura", subtítulo "entre empresas com histórico comparável" |
| 10 | Cartão de texto (ou caixa de texto com valor dinâmico) | `[Nota Metodológica]` | rodapé, fonte 9, cinza |

**Drill-through:** botão direito numa linha da tabela → *Detalhamento →
Ficha da empresa* (configurado na página 2).

**Conferência no print (2025, sem filtro de setor):** os três cartões
somados, mais as indeterminadas, dão o total de empresas de 2025; a soma
da matriz é o número de empresas presentes em 2024 e 2025.

---

## Página 2 — Ficha da empresa

Pergunta: *essa empresa consegue honrar as obrigações, e está melhorando ou
piorando?*

**Configuração da página:** *Formatar página → Informações da página →
Tipo: Detalhamento*; campo de detalhamento `dim_empresa[empresa]`;
**"Manter todos os filtros" desligado.** Assim só a empresa vem pelo
detalhamento, e o ano vem da segmentação sincronizada (#2). Para montar sem
detalhamento, arraste uma empresa para o poço de detalhamento (ex.: "WEG S.A.
(5410)").

| # | Visual | Campos | Configuração |
|---|---|---|---|
| 1 | Cartão (novo), várias linhas | `dim_empresa[empresa]`, `dim_setor[setor]`, `dim_empresa[tipo_demonstrativo]`, `dim_empresa[situacao]` | cabeçalho, sem título |
| 2 | Segmentação | `dim_ano[ano]` | a sincronizada |
| 3 | Cartões (novo) ×4 | `[Z''-EM]`, `[Zona]`, `[Tipo Fleuriet]`, `[Efeito Tesoura]` | `[Zona]` com cor do valor por valor de campo `[Cor da Zona]` |
| 4 | Matriz "Índices vs setor" | Linhas `dim_indice[indice]`; Colunas `Benchmark[Comparação]`; Valores `[Valor do Índice]` | filtro do visual em `Benchmark[Comparação]`: Valor, Mediana do Setor, Quartil no Setor, Δ vs Ano Anterior. Dicas de ferramenta: `[Fórmula do Índice]`, `[Leitura do Índice]`. Desligue os totais. Cabeçalhos: "Empresa", "Mediana do setor", "Quartil (1–4)", "Δ ano". Os formatos (x, %, casas) já vêm do modelo |
| 5 | Gráfico de linhas "Z''-EM ao longo do tempo" | Eixo X `dim_ano[ano]` (categórico); Y `[Z''-EM (exibição)]`, `[Limite Risco]`, `[Limite Segura]`; dica de ferramenta `[Z''-EM]` (valor real) | Eixo Y fixo de −25 a 25, para todas as empresas ficarem na mesma escala. **Editar interações:** a segmentação de ano (#2) → "nenhum" neste visual. Z em `#37474F` com marcadores; Limite Risco tracejado `#C62828`; Limite Segura tracejado `#2E7D32`; a faixa entre eles é a zona cinzenta (subtítulo "entre as linhas: zona cinzenta") |
| 6 | Colunas agrupadas "Modelo Fleuriet" | Eixo X `dim_ano[ano]`; Y `[CDG]`, `[NCG]`, `[Saldo de Tesouraria]` | segmentação de ano → "nenhum" neste visual. Dica de ferramenta: `[Tipo Fleuriet]`. Legenda: "CDG", "NCG", "T". Rótulos de dados desligados (valores em R$ mi) |
| 7 | Cartões de texto ×2 | `[Aviso PL]`, `[Aviso Receita]` | sem fundo nem borda; ficam vazios quando não se aplicam |
| 8 | Botão Voltar | — | canto superior esquerdo |

**Conferência no print (WEG 2024):** Z 8,58, zona segura; Liquidez
Corrente 1,76 com mediana do setor 1,39; ΔZ −0,57.

---

## Página 3 — Panorama setorial

Pergunta: *como o setor está, e onde a empresa se encaixa?*

| # | Visual | Campos | Configuração |
|---|---|---|---|
| 1 | Segmentação | `dim_ano[ano]` | a sincronizada |
| 2 | Segmentação | `dim_indice[indice]` | lista suspensa, seleção única, valor Z''-EM, título "Índice" |
| 3 | Matriz "Distribuição do índice por setor" | Linhas `dim_setor[setor]`; Colunas `Benchmark[Comparação]`; Valores `[Valor do Índice]` | filtro do visual em `Benchmark[Comparação]`: Q1 do Setor, Mediana do Setor, Q3 do Setor. Barras de dados na mediana. Ordenar pela mediana. Desligue os totais. Cabeçalhos "Q1", "Mediana", "Q3" |
| 4 | Tabela ao lado da matriz, alinhada | `dim_setor[setor]`, `[Empresas]` | mesma ordem da matriz. Fica separada porque o grupo de cálculo transformaria `[Empresas]` dentro da matriz |
| 5 | Gráfico de linhas "% em zona de risco" | Eixo X `dim_ano[ano]`; Y `[% em Risco]`; Legenda `dim_setor[setor]` | segmentação de ano → "nenhum" neste visual. Filtro do visual: Top 6 de `dim_setor[setor]` por `[Empresas]` (ou pequenos múltiplos por setor, se preferir) |
| 6 | Cartão de texto | `[Nota Metodológica]` | rodapé |

---

## Página 4 — Qualidade dos dados (técnica)

Pergunta: *o que ficou de fora do pipeline, e por quê?*

| # | Visual | Campos | Configuração |
|---|---|---|---|
| 1 | Cartões (novo) ×2 | `[Problemas de Qualidade]`, `[Empresas Excluídas]` | — |
| 2 | Colunas empilhadas "Problemas por ano" | Eixo X `qualidade[ano]`; Legenda `qualidade[etapa]`; Y `[Problemas de Qualidade]` | — |
| 3 | Barras "Problemas por tipo" | Eixo Y `qualidade[tipo_problema]`; X `[Problemas de Qualidade]`; dica de ferramenta `qualidade[problema]` | ordenar decrescente; rótulos de dados ligados. `tipo_problema` junta "conta ausente: …" e "duplicata com valores divergentes: …" numa barra cada |
| 4 | Tabela | `qualidade[nome]`, `qualidade[cd_cvm]`, `qualidade[ano]`, `qualidade[etapa]`, `qualidade[problema]` | segmentação `qualidade[etapa]` ao lado |
| 5 | Caixa de texto | "Setores financeiros (bancos, seguradoras) ficam fora por terem layout de demonstrativo diferente. 'Sem cadastro' são emissores estrangeiros e um caso de código CVM divergente (Multilaser). Contas ausentes e duplicatas divergentes da fonte ficam registradas, não corrigidas." | fonte 10 |

**Conferência no print:** 1.268 problemas, 217 empresas excluídas.

---

## Ordem de montagem

Página 4 primeiro (mais simples, serve de aquecimento), depois 1, 2 e 3. A
página 2 depende do detalhamento configurado; teste o clique direito
**Detalhamento** na tabela da página 1 depois das duas prontas.
