"""
Cliente para as notícias publicadas pela Anvisa em gov.br/anvisa.

O site da Anvisa roda em Plone (CMS usado por vários órgãos do governo
federal) com a API REST do Plone habilitada (`++api++/@search`) — não
requer chave nem cadastro. Confirmado funcionando via teste direto em
11/09/2026 (trouxe, por exemplo, "Anvisa aprova novas indicações
terapêuticas para medicamento Trodelvy", publicada no mesmo dia).

Diferença em relação às outras fontes do projeto: isso não é um cliente de
API de dados abertos formal com schema documentado — é a mesma API REST
que o próprio site usa para montar a página, descoberta por engenharia
reversa (ver pesquisa em 11/09/2026). Pode quebrar se a Anvisa trocar de
CMS ou desabilitar a API publicamente, sem aviso prévio — diferente das
APIs de dados abertos (Câmara, Congress.gov) que têm contrato mais estável.

Cada notícia devolvida já tem título, resumo (`description`) e data de
publicação (`effective`) — não precisa de uma segunda chamada de detalhe
pra ter texto suficiente pra classificar. O corpo completo da notícia (HTML)
fica disponível se for preciso, mas não é buscado por padrão aqui (o
resumo costuma já ser suficiente, no mesmo espírito do resto do projeto).
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import requests

BASE_URL = "https://www.gov.br/anvisa"
_CAMINHO_NOTICIAS = "/pt-br/assuntos/noticias-anvisa"
_TIMEOUT = 30
_TETO_PAGINACAO = 500  # trava de segurança


def listar_novas(dias: int) -> list[dict]:
    """
    Lista notícias da Anvisa publicadas nos últimos `dias` dias, já no
    formato de registro usado por main.py/storage.py para notícias
    (chaves: id_externo, titulo, resumo, texto, data_publicacao, url_origem,
    autor).
    """
    limite = dt.date.today() - dt.timedelta(days=dias)
    params = {
        "path": _CAMINHO_NOTICIAS,
        "portal_type": "News Item",
        "b_size": 50,
        "sort_on": "effective",
        "sort_order": "descending",
    }
    itens: list[dict] = []
    b_start = 0
    while True:
        params["b_start"] = b_start
        resp = requests.get(f"{BASE_URL}/++api++/@search", params=params, timeout=_TIMEOUT,
                             headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        pagina = data.get("items", [])
        if not pagina:
            break

        parar = False
        for item in pagina:
            data_pub = _parse_data(item.get("effective"))
            if data_pub and data_pub.date() < limite:
                parar = True
                break
            itens.append(_para_registro(item, data_pub))

        if parar or len(pagina) < params["b_size"] or b_start >= _TETO_PAGINACAO:
            break
        b_start += params["b_size"]

    return itens


def _parse_data(valor: str | None) -> dt.datetime | None:
    if not valor:
        return None
    try:
        return dt.datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None


def _para_registro(item: dict[str, Any], data_pub: dt.datetime | None) -> dict:
    url = item.get("@id", "")
    return {
        "fonte": "anvisa",
        "id_externo": url.rsplit("/", 1)[-1] or url,
        "titulo": item.get("title") or "",
        "resumo": item.get("description") or "",
        "texto": None,  # corpo completo não é buscado por padrão (ver docstring do módulo)
        "data_publicacao": data_pub.date().isoformat() if data_pub else None,
        "url_origem": url,
        "autor": None,
    }
