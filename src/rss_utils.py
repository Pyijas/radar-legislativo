"""
Helper compartilhado pelos clientes de notícia que usam feed RSS padrão
(WordPress ou Joomla, que é o caso de metade das agências regulatórias
latino-americanas pesquisadas em 11/09/2026 — ver src/isp_chile_client.py,
src/digemid_client.py e src/minsalud_bolivia_client.py). Um feed RSS 2.0 já
traz título/data/link/resumo prontos, então não precisa de scraping de HTML
nem de uma segunda chamada por notícia — mesma vantagem que o sitemap de
notícias do Google tem pra src/saude_news_client.py.
"""
from __future__ import annotations

import datetime as dt
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

_TIMEOUT = 30
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
}
_TAG_RE = re.compile(r"<[^>]+>")


def buscar_itens(url_feed: str) -> list[ET.Element]:
    """Baixa um feed RSS 2.0 e devolve a lista de elementos <item>."""
    resp = requests.get(url_feed, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    canal = root.find("channel")
    return canal.findall("item") if canal is not None else []


def texto_de(item: ET.Element, tag: str) -> str:
    el = item.find(tag)
    return (el.text or "").strip() if el is not None and el.text else ""


def limpar_html(valor: str, limite: int = 600) -> str:
    """Tira tags HTML de dentro de <description> (alguns feeds, como o do
    Ministério da Saúde da Bolívia, mandam HTML ali dentro) e corta num
    tamanho razoável pra não inflar o resumo com o texto inteiro do post."""
    sem_tags = _TAG_RE.sub(" ", valor)
    sem_tags = re.sub(r"\s+", " ", sem_tags).strip()
    return sem_tags[:limite]


def parse_pub_date(valor: str) -> dt.date | None:
    """<pubDate> de RSS segue RFC 822 (ex: 'Tue, 08 Sep 2026 15:18:41 +0000')."""
    if not valor:
        return None
    try:
        return parsedate_to_datetime(valor).date()
    except (TypeError, ValueError):
        return None


def slug_da_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1] or url
