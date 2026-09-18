"""
Cliente para as notícias do MSP — Ministerio de Salud Pública do Uruguai
(a área de registro/regulação de medicamentos do país, División Evaluación
Sanitaria, funciona dentro do MSP — não é uma agência separada como Anvisa/
ANMAT/COFEPRIS).

O site institucional (gub.uy, plataforma Drupal do governo uruguaio) não
expõe API JSON pública nem RSS na seção de notícias, mas a página de
listagem já vem renderizada em HTML puro (título + data + resumo curto por
notícia), sem precisar de JS. Scraping por regex em dois estágios (primeiro
isola cada bloco <article>, depois extrai os campos de dentro — mesma
técnica do src/agenda_presidente_client.py), pra evitar que o regex "vaze"
de um item pro próximo. Confirmado funcionando via teste direto em
11/09/2026.

Limitação: só a primeira página da listagem (as notícias mais recentes),
sem paginação — suficiente pra acompanhamento contínuo, não pra backfill.
"""
from __future__ import annotations

import datetime as dt
import re

import requests

BASE_URL = "https://www.gub.uy"
_PATH_NOTICIAS = "/ministerio-salud-publica/comunicacion/noticias"
FONTE = "msp_uy"
_TIMEOUT = 30
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
}
_PADRAO_ARTIGO = re.compile(r'<article about="([^"]+)">(.*?)</article>', re.S)
_PADRAO_TITULO = re.compile(r'<h3 class="Media-title">\s*<a[^>]*>\s*([^<]+?)\s*</a>', re.S)
_PADRAO_DATA = re.compile(r'<span class="Box-info">([^<]+)</span>')
_PADRAO_RESUMO = re.compile(r"<p>([^<]*)</p>")


def listar_novas(dias: int) -> list[dict]:
    limite = dt.date.today() - dt.timedelta(days=dias)
    resp = requests.get(f"{BASE_URL}{_PATH_NOTICIAS}", headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()

    registros = []
    for caminho, bloco in _PADRAO_ARTIGO.findall(resp.text):
        m_titulo = _PADRAO_TITULO.search(bloco)
        m_data = _PADRAO_DATA.search(bloco)
        if not m_titulo or not m_data:
            continue

        data_pub = _parse_data(m_data.group(1).strip())
        if data_pub and data_pub < limite:
            continue

        m_resumo = _PADRAO_RESUMO.search(bloco)

        registros.append({
            "fonte": FONTE,
            "id_externo": caminho.rstrip("/").rsplit("/", 1)[-1],
            "titulo": m_titulo.group(1).strip(),
            "resumo": m_resumo.group(1).strip() if m_resumo else None,
            "texto": None,
            "data_publicacao": data_pub.isoformat() if data_pub else None,
            "url_origem": BASE_URL + caminho,
            "autor": None,
        })

    return registros


def _parse_data(valor: str) -> dt.date | None:
    try:
        return dt.datetime.strptime(valor, "%d/%m/%Y").date()
    except ValueError:
        return None
