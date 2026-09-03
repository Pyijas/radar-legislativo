"""
Cliente para a API de Dados Abertos da Câmara dos Deputados.

Documentação oficial: https://dadosabertos.camara.leg.br/swagger/api.html
Não requer autenticação para leitura.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import requests

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
_TIMEOUT = 30


def _get(path: str, params: dict | None = None) -> dict:
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=_TIMEOUT,
                         headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


def _get_all_pages(path: str, params: dict) -> list[dict]:
    """Segue a paginação da API (campo 'links' com rel=next) até esgotar."""
    itens = []
    params = dict(params)
    params.setdefault("itens", 100)
    params.setdefault("pagina", 1)
    while True:
        data = _get(path, params)
        dados = data.get("dados", [])
        itens.extend(dados)
        links = {l["rel"]: l["href"] for l in data.get("links", []) if "rel" in l}
        if "next" not in links or not dados:
            break
        params["pagina"] += 1
    return itens


def find_cod_tema(nome_tema: str) -> int | None:
    """Busca o código numérico de um tema (ex: 'Saúde') na tabela de referência da API."""
    data = _get("/referencias/proposicoes/codTema")
    for item in data.get("dados", []):
        if item.get("nome", "").strip().lower() == nome_tema.strip().lower():
            return int(item["cod"])
    return None


def list_novas_proposicoes(
    dias: int,
    cod_tema: int,
    siglas_tipo: list[str] | None = None,
) -> list[dict]:
    """
    Lista proposições apresentadas nos últimos `dias` dias, filtradas por tema.

    siglas_tipo: ex. ["PL", "PLP"]. Se None, traz todos os tipos de proposição.

    A API rejeita consultas com mais de ~3 meses de diferença entre as datas
    (erro 400 "A diferença entre as datas não pode ser maior que 3 meses"),
    então janelas maiores são quebradas em blocos de até 90 dias.
    """
    hoje = dt.date.today()
    inicio_total = hoje - dt.timedelta(days=dias)

    todas: list[dict] = []
    vistos: set[int] = set()
    fim_bloco = hoje
    while fim_bloco >= inicio_total:
        inicio_bloco = max(inicio_total, fim_bloco - dt.timedelta(days=89))
        params: dict[str, Any] = {
            "dataApresentacaoInicio": inicio_bloco.isoformat(),
            "dataApresentacaoFim": fim_bloco.isoformat(),
            "codTema": cod_tema,
            "ordem": "DESC",
            "ordenarPor": "id",  # API só aceita ordenar por 'id' (não por dataApresentacao)
        }
        if siglas_tipo:
            params["siglaTipo"] = siglas_tipo
        for item in _get_all_pages("/proposicoes", params):
            if item["id"] not in vistos:
                vistos.add(item["id"])
                todas.append(item)
        fim_bloco = inicio_bloco - dt.timedelta(days=1)

    return todas


def get_detalhe(id_proposicao: int) -> dict:
    data = _get(f"/proposicoes/{id_proposicao}")
    return data.get("dados", {})


def get_autores(id_proposicao: int) -> list[str]:
    data = _get(f"/proposicoes/{id_proposicao}/autores")
    return [a.get("nome", "") for a in data.get("dados", []) if a.get("nome")]
