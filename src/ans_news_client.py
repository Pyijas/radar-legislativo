"""
Cliente para as notícias publicadas pela ANS em gov.br/ans.

Mesmo padrão do Ministério da Saúde (ver src/saude_news_client.py): a API
REST do Plone não está disponível publicamente nesse site (`++api++` dá
404), mas o **sitemap de notícias do Google** (`sitemap.xml`) funciona e
traz título + data de publicação prontos.

Confirmado funcionando via teste direto em 11/09/2026 (trouxe, por exemplo,
"ANS aprova mamografia digital sem restrição de idade" e "Diretor-presidente
da ANS destaca importância do combate a fraudes no setor de dispositivos
médicos" — essa segunda já é cobertura de agenda pública do diretor,
embutida na própria notícia).

Nota curiosa: em 11/09/2026 as notícias da ANS estavam publicadas sob o
caminho `/pt-br/assuntos/noticias-1/periodo-eleitoral/...` em vez do
`/noticias` esperado (que exige login) — provavelmente uma reorganização
temporária ligada a regras de comunicação institucional em período
eleitoral. Esse client não depende do caminho exato, só do sitemap.xml, que
segue funcionando independente de para onde as notícias sejam movidas.

Mesma limitação de janela de histórico do client do MS — não serve pra
backfill antigo, só acompanhamento do que sai a partir de agora.
"""
from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET

import requests

BASE_URL = "https://www.gov.br/ans"
_TIMEOUT = 30
_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
}


def listar_novas(dias: int) -> list[dict]:
    """
    Lista notícias da ANS publicadas nos últimos `dias` dias, no mesmo
    formato de registro usado por main.py/storage.py para notícias.
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
            "fonte": "ans",
            "id_externo": loc.rsplit("/", 1)[-1] or loc,
            "titulo": titulo,
            "resumo": None,
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
