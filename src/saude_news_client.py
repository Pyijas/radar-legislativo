"""
Cliente para as notícias publicadas pelo Ministério da Saúde em gov.br/saude.

Ao contrário da Anvisa, o site do MS não expõe a API REST do Plone
publicamente (`++api++` devolve 404, mesmo o site sendo Plone — parece
desabilitado deliberadamente nesse órgão específico; ver pesquisa em
11/09/2026). Em compensação, o MS publica um **sitemap de notícias do
Google** (`sitemap.xml`, no formato `news:*` do protocolo
news-sitemap) com título e data de publicação prontos — não precisa de
scraping de HTML nem de uma segunda chamada por notícia.

Confirmado funcionando via teste direto em 11/09/2026 (trouxe, por exemplo,
"Ministro da Saúde visita ampliação da fábrica da NOVAMED do grupo EMS em
Manaus/AM" — cobertura de agenda pública do ministro embutida na própria
notícia, ver EXPANSAO-INTERNACIONAL.md / discussão sobre agendas).

Limitação conhecida: o sitemap de notícias do Google normalmente só mantém
as publicações mais recentes (a especificação do protocolo recomenda até 2
dias, mas na prática o MS mantém uma janela maior — não documentada
oficialmente). Não é adequado para backfill de histórico antigo, só para
acompanhamento do que é publicado de agora em diante — mesma limitação que
o Chile tem pra PLs (ver src/chile_client.py).
"""
from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET

import requests

BASE_URL = "https://www.gov.br/saude"
_TIMEOUT = 30
_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}


def listar_novas(dias: int) -> list[dict]:
    """
    Lista notícias do Ministério da Saúde publicadas nos últimos `dias`
    dias, já no formato de registro usado por main.py/storage.py para
    notícias (chaves: id_externo, titulo, resumo, texto, data_publicacao,
    url_origem, autor).
    """
    limite = dt.date.today() - dt.timedelta(days=dias)

    resp = requests.get(f"{BASE_URL}/sitemap.xml", timeout=_TIMEOUT)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    registros = []
    for url_el in root.findall("sm:url", _NS):
        news_el = url_el.find("news:news", _NS)
        if news_el is None:
            continue

        data_str = news_el.findtext("news:publication_date", default="", namespaces=_NS)
        data_pub = _parse_data(data_str)
        if data_pub and data_pub < limite:
            continue

        loc = url_el.findtext("sm:loc", default="", namespaces=_NS)
        titulo = news_el.findtext("news:title", default="", namespaces=_NS)
        if not loc or not titulo:
            continue

        registros.append({
            "fonte": "saude",
            "id_externo": loc.rsplit("/", 1)[-1] or loc,
            "titulo": titulo,
            "resumo": None,  # o sitemap de notícias não traz resumo, só título
            "texto": None,
            "data_publicacao": data_pub.isoformat() if data_pub else None,
            "url_origem": loc,
            "autor": None,
        })

    return registros


def _parse_data(valor: str) -> dt.date | None:
    if not valor:
        return None
    try:
        return dt.date.fromisoformat(valor[:10])
    except ValueError:
        return None
