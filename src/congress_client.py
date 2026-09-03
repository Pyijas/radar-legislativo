"""
Cliente para a API oficial do Congresso dos Estados Unidos (Library of
Congress / GPO): https://api.congress.gov/

Precisa de uma chave gratuita — cadastro simples (nome + e-mail, sem cartão)
em https://api.congress.gov/sign-up/. Configure em CONGRESS_API_KEY no
.env. Sem a chave, disponivel() retorna False e listar_novas() devolve uma
lista vazia — o resto do pipeline trata essa fonte como "desligada", do
mesmo jeito que já faz quando falta ANTHROPIC_API_KEY/GEMINI_API_KEY.

Diferença de forma em relação à Câmara/Senado brasileiros:

- A listagem (/v3/bill) não tem um filtro de "data de apresentação" direto
  documentado — o filtro disponível (fromDateTime/toDateTime) é por data da
  ÚLTIMA ATUALIZAÇÃO do projeto, não da apresentação original. Na prática
  isso ainda funciona bem pro nosso caso de uso (rodar todo dia e pegar o
  que mudou), só que um projeto antigo que só teve uma movimentação nova
  esta semana também aparece na lista — sem problema, porque o dedupe por
  (pais, casa, id_externo) evita reprocessar um que já classificamos antes.
- Não existe um filtro de tema/assunto ("Saúde"/"Health") na listagem — o
  campo policyArea só vem no detalhe de cada projeto (endpoint individual),
  não na lista. Por isso, igual à Câmara e ao Senado, a seleção de
  relevância é feita pela camada de heurística/IA em cima do texto (aqui em
  inglês), não por um filtro de tema na consulta — só que aqui isso importa
  mais: o volume de projetos novos nos EUA é bem maior que no Brasil, então
  rodar --dias grande pode consumir bastante da cota de requisições.
- "ementa" usa o título do projeto (title) + a área de política (policyArea)
  quando disponível; "texto_inteiro_teor" usa o resumo oficial do CRS
  (Congressional Research Service), via /summaries — não o PDF do texto
  integral (mais simples e mais confiável de extrair que os PDFs de texto
  legislativo dos EUA, que têm formatação bem mais variada que os do Brasil).
- Só cobre os tipos "hr" (House bill) e "s" (Senate bill) por padrão — exclui
  resoluções (hres/sres/hjres/sjres/hconres/sconres), que não têm força de
  lei, pro escopo ficar parecido com PL/PLP no Brasil.

Limite de requisições: a documentação oficial não detalha um número exato;
chaves emitidas via api.data.gov (que é quem processa o cadastro) costumam
ter um teto padrão da ordem de milhares de requisições por hora — não
deveria ser um problema pro uso diário deste projeto, mas vale monitorar se
for rodar um backfill grande de uma vez.
"""
from __future__ import annotations

import datetime as dt
import os
import re
from typing import Any

import requests

BASE_URL = "https://api.congress.gov/v3"
_TIMEOUT = 30
_TIPOS_PADRAO = ["hr", "s"]
_PAGINA = 250
_TETO_PAGINACAO = 5000  # trava de segurança pra não paginar indefinidamente

_CASA_POR_TIPO = {"hr": "house", "s": "senate"}
_CAMINHO_POR_TIPO = {"hr": "house-bill", "s": "senate-bill"}


def _api_key() -> str | None:
    return os.environ.get("CONGRESS_API_KEY")


def disponivel() -> bool:
    return bool(_api_key())


def _get(path: str, params: dict | None = None) -> Any:
    params = dict(params or {})
    params["api_key"] = _api_key()
    params.setdefault("format", "json")
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def casa_do_item(item: dict) -> str:
    return _CASA_POR_TIPO.get(str(item.get("type", "")).lower(), "outro")


def id_externo_do_item(item: dict) -> str:
    return f"{str(item.get('type', '')).lower()}{item.get('number')}-{item.get('congress')}"


def listar_novas(dias: int, siglas_tipo: list[str] | None = None) -> list[dict]:
    """
    Lista projetos de lei federais dos EUA atualizados nos últimos `dias`
    dias (ver limitação de data no docstring do módulo). Devolve os itens
    "crus" da API — chame get_detalhe() em cima de cada um antes de salvar,
    pra pegar ementa/autoria/tramitação completos.

    siglas_tipo: ex. ["hr", "s"] (minúsculo, como a API espera). Usa
    _TIPOS_PADRAO se None.
    """
    if not disponivel():
        return []

    siglas_tipo = [s.lower() for s in (siglas_tipo or _TIPOS_PADRAO)]
    agora = dt.datetime.now(dt.timezone.utc)
    inicio = agora - dt.timedelta(days=dias)
    params = {
        "fromDateTime": inicio.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "toDateTime": agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sort": "updateDate+desc",
        "limit": _PAGINA,
        "offset": 0,
    }
    itens: list[dict] = []
    while True:
        data = _get("/bill", params)
        bills = data.get("bills", [])
        itens.extend(bills)
        if len(bills) < _PAGINA or params["offset"] >= _TETO_PAGINACAO:
            break
        params["offset"] += _PAGINA

    return [b for b in itens if str(b.get("type", "")).lower() in siglas_tipo]


def _resumo_crs(congress, tipo: str, numero) -> str | None:
    """Resumo oficial do CRS (Congressional Research Service), quando existe.
    Faz o papel do 'texto_inteiro_teor' que a Câmara/Senado dão via PDF."""
    try:
        data = _get(f"/bill/{congress}/{tipo}/{numero}/summaries")
    except requests.RequestException:
        return None
    resumos = data.get("summaries") or []
    if not resumos:
        return None
    texto = resumos[-1].get("text") or ""  # API devolve em ordem cronológica; o último é o mais recente
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:15000] or None


def get_detalhe(item: dict) -> dict:
    """Recebe um item de listar_novas() e devolve o registro completo, no
    formato usado por main.py/storage.py (chaves: id_externo, casa, ementa,
    texto_inteiro_teor, data_apresentacao, autores, url_origem,
    url_inteiro_teor, ultima_tramitacao_data, ultima_tramitacao_descricao,
    orgao_atual, sigla_tipo, numero, ano)."""
    congress = item.get("congress")
    tipo = str(item.get("type", "")).lower()
    numero = item.get("number")

    detalhe = (_get(f"/bill/{congress}/{tipo}/{numero}") or {}).get("bill", {})
    policy_area = ((detalhe.get("policyArea") or {}).get("name")) or ""
    titulo = detalhe.get("title") or item.get("title") or ""
    ementa = f"{titulo}\n\n[Policy area: {policy_area}]" if policy_area else titulo

    sponsors = detalhe.get("sponsors") or []
    autores = ", ".join(s.get("fullName", "") for s in sponsors if s.get("fullName"))

    latest = detalhe.get("latestAction") or {}
    caminho = _CAMINHO_POR_TIPO.get(tipo, tipo)

    return {
        "id_externo": id_externo_do_item(item),
        "casa": casa_do_item(item),
        "sigla_tipo": tipo.upper(),
        "numero": str(numero),
        "ano": int(congress) if congress else None,  # aqui representa o nº do Congresso, não um ano-calendário
        "ementa": ementa,
        "texto_inteiro_teor": _resumo_crs(congress, tipo, numero),
        "data_apresentacao": detalhe.get("introducedDate"),
        "autores": autores,
        "url_origem": f"https://www.congress.gov/bill/{congress}th-congress/{caminho}/{numero}",
        "url_inteiro_teor": None,
        "ultima_tramitacao_data": latest.get("actionDate"),
        "ultima_tramitacao_descricao": latest.get("text"),
        "orgao_atual": None,
    }
