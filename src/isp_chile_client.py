"""
Cliente para as notícias do ISP — Instituto de Salud Pública de Chile, a
agência reguladora de medicamentos do país (equivalente à Anvisa).

O site (ispch.gob.cl) é WordPress e expõe o feed RSS padrão em `/feed/` —
já vem com título, link, data (`pubDate`) e resumo (`description`) prontos,
sem precisar de scraping. Confirmado funcionando via teste direto em
11/09/2026.
"""
from __future__ import annotations

import datetime as dt

from src import rss_utils

BASE_URL = "https://www.ispch.gob.cl"
FONTE = "isp_cl"


def listar_novas(dias: int) -> list[dict]:
    limite = dt.date.today() - dt.timedelta(days=dias)
    itens = rss_utils.buscar_itens(f"{BASE_URL}/feed/")

    registros = []
    for item in itens:
        data_pub = rss_utils.parse_pub_date(rss_utils.texto_de(item, "pubDate"))
        if data_pub and data_pub < limite:
            continue

        link = rss_utils.texto_de(item, "link")
        titulo = rss_utils.texto_de(item, "title")
        if not link or not titulo:
            continue

        registros.append({
            "fonte": FONTE,
            "id_externo": rss_utils.slug_da_url(link),
            "titulo": titulo,
            "resumo": rss_utils.limpar_html(rss_utils.texto_de(item, "description")) or None,
            "texto": None,
            "data_publicacao": data_pub.isoformat() if data_pub else None,
            "url_origem": link,
            "autor": rss_utils.texto_de(item, "{http://purl.org/dc/elements/1.1/}creator") or None,
        })

    return registros
