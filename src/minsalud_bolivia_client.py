"""
Cliente para as notícias do Ministério da Saúde e Esportes da Bolívia
(minsalud.gob.bo) — a AGEMED (Agencia Estatal de Medicamentos y
Tecnologías en Salud, a reguladora de medicamentos do país) não publica
feed próprio, mas suas resoluções/comunicados saem nas notícias do
Ministério, igual acontece com o Ministério da Saúde do Brasil (ver
src/saude_news_client.py) — por isso aqui também não filtramos por
palavra-chave na coleta, deixando a classificação (heurística + IA) decidir
o que é relevante pra indústria farmacêutica.

O site é Joomla e expõe RSS padrão em `/index.php?format=feed&type=rss`.
Confirmado funcionando via teste direto em 11/09/2026.
"""
from __future__ import annotations

import datetime as dt

from src import rss_utils

BASE_URL = "https://www.minsalud.gob.bo"
FONTE = "minsalud_bo"


def listar_novas(dias: int) -> list[dict]:
    limite = dt.date.today() - dt.timedelta(days=dias)
    itens = rss_utils.buscar_itens(f"{BASE_URL}/index.php?format=feed&type=rss")

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
            "autor": None,
        })

    return registros
