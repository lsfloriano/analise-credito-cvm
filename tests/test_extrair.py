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
