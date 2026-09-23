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
