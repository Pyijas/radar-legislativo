"""
Cliente para as notícias da ANMAT — Administración Nacional de
Medicamentos, Alimentos y Tecnología Médica da Argentina, a agência
reguladora de medicamentos do país (equivalente à Anvisa).

Diferente da Anvisa/MS/ANS (gov.br), o site institucional da ANMAT
(argentina.gob.ar/anmat) não tem API REST nem sitemap de notícias — mas a
própria página institucional já lista as últimas notícias renderizadas em
HTML puro (título + data + link), sem precisar de JS nem de paginação
extra. Scraping simples por regex, no mesmo espírito do
src/agenda_presidente_client.py. Confirmado funcionando via teste direto em
11/09/2026.

Limitação: só traz as notícias mais recentes mostradas na página
institucional (não é uma listagem paginada completa), então não serve pra
backfill de histórico — só acompanhamento do que sai daqui pra frente,
mesma limitação que o Chile tem pra PLs.
"""
from __future__ import annotations

import datetime as dt
import re

import requests

BASE_URL = "https://www.argentina.gob.ar"
FONTE = "anmat"
_TIMEOUT = 30
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
}
_PADRAO_ITEM = re.compile(
    r"<a href=\"(/noticias/[^\"]+)\"[^>]*>\s*<div class=\"panel-body\">\s*"
    r"<time datetime='([^']+)'>.*?</time>\s*<h3>([^<]+)</h3>",
    re.S,
)


def listar_novas(dias: int) -> list[dict]:
    limite = dt.date.today() - dt.timedelta(days=dias)
    resp = requests.get(f"{BASE_URL}/anmat", headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()

    registros = []
    vistos = set()
    for caminho, data_str, titulo in _PADRAO_ITEM.findall(resp.text):
        if caminho in vistos:
            continue
        vistos.add(caminho)

        data_pub = _parse_data(data_str)
        if data_pub and data_pub < limite:
            continue

        registros.append({
            "fonte": FONTE,
            "id_externo": caminho.rstrip("/").rsplit("/", 1)[-1],
            "titulo": titulo.strip(),
            "resumo": None,  # a página institucional só traz o título, sem resumo
            "texto": None,
            "data_publicacao": data_pub.isoformat() if data_pub else None,
            "url_origem": BASE_URL + caminho,
            "autor": None,
        })

    return registros


def _parse_data(valor: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(valor[:10])
    except ValueError:
        return None
