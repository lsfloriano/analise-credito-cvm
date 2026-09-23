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
from pipeline import validacao


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
    nome_por_empresa = limpo.sort_values("ano", kind="stable").groupby("cd_cvm")["nome"].last()
    problemas.insert(1, "nome", problemas["cd_cvm"].map(nome_por_empresa))
    caminhos = exportar(fato, cadastro, problemas, out_dir)
    print(f"{fato['cd_cvm'].nunique()} empresas, {len(fato)} empresas-ano, "
          f"{len(problemas)} problemas registrados -> {Path(out_dir)}")
    return caminhos


def referencia(cvms, *, out_dir=config.DATA_PROCESSED, saida=config.RAIZ / "docs" / "referencia_indices.csv"):
    fato = pd.read_parquet(Path(out_dir) / "fato_indicadores.parquet")
    ref = calcular_indices(fato[fato["cd_cvm"].isin(cvms)])
    ref = ref.merge(fato[["cd_cvm", "ano", "z", "zona", "tipo_fleuriet"]], on=["cd_cvm", "ano"])
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    ref.sort_values(["cd_cvm", "ano"]).to_csv(saida, index=False, float_format="%.6f")
    print(f"{len(ref)} linhas de referência -> {saida}")
    return saida


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


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m pipeline")
    sub = parser.add_subparsers(dest="comando", required=True)
    p_run = sub.add_parser("run", help="baixa, trata e exporta os Parquet")
    p_run.add_argument("--anos", default=f"{config.ANOS_PADRAO.start}-{config.ANOS_PADRAO.stop - 1}")
    p_run.add_argument("--forcar", action="store_true", help="rebaixa arquivos já em cache")
    p_ref = sub.add_parser("referencia", help="gera índices de referência para validar o DAX")
    p_ref.add_argument("--cvm", type=int, nargs="+", required=True)
    p_ref.add_argument("--saida", default=str(config.RAIZ / "docs" / "referencia_indices.csv"))
    p_val = sub.add_parser("validar-dax", help="compara o CSV de uma consulta DAX com o Python")
    p_val.add_argument("tipo", choices=["indices", "benchmark", "percentil", "migracao"])
    p_val.add_argument("csv")
    p_val.add_argument("--ano", type=int)
    p_val.add_argument("--ano-base", type=int)
    args = parser.parse_args(argv)

    if args.comando == "run":
        run(_parse_anos(args.anos), forcar=args.forcar)
    elif args.comando == "referencia":
        referencia(args.cvm, saida=args.saida)
    elif args.comando == "validar-dax":
        return validar_dax(args.tipo, args.csv, ano=args.ano, ano_base=args.ano_base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
