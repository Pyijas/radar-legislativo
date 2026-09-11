"""
Cliente para a agenda pública do Presidente da República, publicada em
gov.br/planalto.

Diferente do e-Agendas (ver discussão em 11/09/2026 — exige API com token
de usuário, ou automação via navegador, pra Vice-Presidência/Ministro da
Saúde/diretor da Anvisa), a agenda do Presidente tem página própria no site
do Planalto, **renderizada no servidor** (sem precisar de JavaScript) — dá
pra ler cada dia com uma requisição HTTP simples.

URL de um dia específico:
    https://www.gov.br/planalto/pt-br/acompanhe-o-planalto/agenda-do-presidente-da-republica-lula/agenda-do-presidente-da-republica/AAAA-MM-DD

Confirmado funcionando via teste direto em 11/09/2026, inclusive pra datas
passadas dentro da janela de dias pedida (ex: .../2026-09-08 devolveu 200
com a agenda daquele dia).

Cada compromisso na página tem: horário (`<time class="compromisso-
inicio">`), título (`<h2 class="compromisso-titulo">`) e local (`<div
class="compromisso-local">`) — server-rendered, parseado aqui com regex
simples (não é um XML/HTML bem-formado o bastante pra valer a pena um
parser DOM completo, e o padrão é estável o suficiente pra regex).

Limitação conhecida: só cobre o Presidente. Vice-Presidência, Ministro da
Saúde e diretor da Anvisa não têm uma página equivalente — só saem via
e-Agendas (bloqueado por enquanto, ver EXPANSAO-INTERNACIONAL.md) ou via
menção nas próprias notícias dos órgãos (ver src/saude_news_client.py e
src/anvisa_news_client.py, que já capturam bastante disso organicamente).
"""
from __future__ import annotations

import datetime as dt
import re

import requests

_URL_DIA = (
    "https://www.gov.br/planalto/pt-br/acompanhe-o-planalto/"
    "agenda-do-presidente-da-republica-lula/agenda-do-presidente-da-republica/{data}"
)
_TIMEOUT = 30
# O site do Planalto devolve 403 pro User-Agent padrão da lib requests
# ("python-requests/x.y") — precisa de um cabeçalho de navegador real.
# Confirmado em 11/09/2026: sem isso, toda requisição falha silenciosamente
# (RequestException capturada em _compromissos_do_dia), fazendo esse client
# sempre devolver zero compromissos sem erro visível.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

_PADRAO_ITEM = re.compile(r'<li class="item-compromisso-wrapper">(.*?)</li>', re.DOTALL)
_PADRAO_HORARIO = re.compile(r'<time class="compromisso-inicio">([^<]*)</time>')
_PADRAO_TITULO = re.compile(r'<h2 class="compromisso-titulo">(.*?)</h2>', re.DOTALL)
_PADRAO_LOCAL = re.compile(r'<div class="compromisso-local">([^<]*)</div>')


def listar_novas(dias: int) -> list[dict]:
    """
    Lista os compromissos públicos do Presidente nos últimos `dias` dias
    (incluindo hoje), já no formato de registro usado por
    main.py/storage.py para eventos de agenda (chaves: id_externo,
    autoridade, cargo, data, horario, titulo, local, url_origem).
    """
    hoje = dt.date.today()
    registros = []
    for i in range(dias):
        data = hoje - dt.timedelta(days=i)
        registros.extend(_compromissos_do_dia(data))
    return registros


def _compromissos_do_dia(data: dt.date) -> list[dict]:
    url = _URL_DIA.format(data=data.isoformat())
    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS)
        resp.raise_for_status()
    except requests.RequestException:
        return []  # dia sem agenda publicada (fim de semana, feriado etc.) — não é erro

    html = resp.text
    registros = []
    for i, bloco in enumerate(_PADRAO_ITEM.findall(html)):
        m_titulo = _PADRAO_TITULO.search(bloco)
        titulo = _limpar_html(m_titulo.group(1)) if m_titulo else ""
        if not titulo:
            continue
        m_horario = _PADRAO_HORARIO.search(bloco)
        m_local = _PADRAO_LOCAL.search(bloco)
        registros.append({
            "id_externo": f"presidente-{data.isoformat()}-{i}",
            "autoridade": "Presidente da República",
            "cargo": "Presidente da República",
            "data": data.isoformat(),
            "horario": m_horario.group(1).strip() if m_horario else None,
            "titulo": titulo,
            "local": _limpar_html(m_local.group(1)) if m_local else None,
            "url_origem": url,
        })
    return registros


def _limpar_html(texto: str) -> str:
    """Remove tags HTML residuais (ex: links dentro do título) e normaliza espaços."""
    sem_tags = re.sub(r"<[^>]+>", " ", texto)
    return re.sub(r"\s+", " ", sem_tags).strip()
