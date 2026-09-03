"""
Cliente para a API de Dados Abertos do Senado Federal.

Documentação: https://legis.senado.leg.br/dadosabertos/docs/index.html

O endpoint principal de matérias (/materia/atualizadas) está sendo
descontinuado pelo próprio Senado em favor de um endpoint mais novo e mais
limpo, /processo, que é o que este módulo usa — confirmado funcionando via
teste direto em 03/09/2026.

Ao contrário da Câmara (onde a listagem só traz um resumo e é preciso um
segundo request por proposição pra pegar ementa/tramitação/autoria), o
/processo do Senado já devolve tudo que precisamos num único request por
período — então não existe (nem é necessário) um get_detalhe() aqui.

Mapeamento de campos usado por listar_novas():
  identificacao      -> "PL 2/2026" etc. — dividido em sigla_tipo/numero/ano
  ementa             -> ementa
  dataApresentacao   -> data_apresentacao
  autoria            -> autores (já vem como texto único, pode ter vários nomes)
  id (= codigoMateria) -> id_externo
  situacaoAtual      -> ultima_tramitacao_descricao
  dataSituacaoAtual  -> ultima_tramitacao_data
  enteIdentificador  -> orgao_atual (ex: "PLEN", "CEDP" — órgão/instância atual)
  urlDocumento       -> url_inteiro_teor (PDF puro, confirmado por Content-Type)

A ficha pública de cada matéria segue o padrão
https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigoMateria}
(confirmado por HTTP 200 num teste direto) — usado como url_origem.

Limitação conhecida: o parâmetro `assunto=` da API não filtrou corretamente
num teste manual (trouxe matérias sem relação com o termo buscado), então
não há filtro de tema no lado do servidor — igual à Câmara, a seleção de
relevância fica por conta da camada de heurística/IA em cima do texto
completo, não de um filtro de tema na consulta.

Limitação conhecida: matérias que também tramitam na Câmara (ou vice-versa)
não são deduplicadas entre as duas fontes — aparecem como registros
separados, um por casa (`casa='senado'` aqui, `casa='camara'` na Câmara).
Isso é intencional: o usuário pediu pra manter câmara e senado separados na
interface, então duplicar não é um bug a corrigir aqui.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import requests

BASE_URL = "https://legis.senado.leg.br/dadosabertos"
_URL_FICHA = "https://www25.senado.leg.br/web/atividade/materias/-/materia/{id}"
_TIMEOUT = 30

_TIPOS_PADRAO = ["PL", "PLP", "PLN", "PEC"]


def _get(path: str, params: dict | None = None) -> Any:
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=_TIMEOUT,
                         headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


def _parse_identificacao(identificacao: str) -> tuple[str, str, int | None]:
    """'PL 2/2026' -> ('PL', '2', 2026). Tolera formatos inesperados sem levantar erro."""
    partes = str(identificacao or "").split(" ", 1)
    sigla = partes[0] if partes else ""
    numero, ano = "", None
    if len(partes) > 1 and "/" in partes[1]:
        numero, _, ano_str = partes[1].partition("/")
        try:
            ano = int(ano_str)
        except ValueError:
            ano = None
    return sigla, numero, ano


def listar_novas(dias: int, siglas_tipo: list[str] | None = None) -> list[dict]:
    """
    Lista matérias do Senado Federal apresentadas nos últimos `dias` dias, já
    no formato de registro usado por main.py/storage.py (pronto pra
    classificar e salvar — sem precisar de uma segunda chamada de detalhe).

    siglas_tipo: ex. ["PL", "PLP"]. Filtrado localmente (client-side)
    comparando com o início de `identificacao`, porque o parâmetro `tipo` da
    API não filtrou corretamente num teste manual. Usa _TIPOS_PADRAO se None.
    Só entram matérias de autoria do próprio Senado (casaIdentificadora=="SF")
    — matérias de "CN" (Congresso Nacional, ex: Medidas Provisórias, que
    tramitam nas duas casas em sessão conjunta) ficam de fora por ora, pra
    não misturar um terceiro tipo de "casa" na interface.
    """
    siglas_tipo = siglas_tipo or _TIPOS_PADRAO
    hoje = dt.date.today()
    inicio = hoje - dt.timedelta(days=dias)
    params = {
        "dataInicioApresentacao": inicio.isoformat(),
        "dataFimApresentacao": hoje.isoformat(),
    }
    dados = _get("/processo", params)
    materias = dados if isinstance(dados, list) else []

    registros = []
    for m in materias:
        if m.get("casaIdentificadora") != "SF":
            continue
        sigla, numero, ano = _parse_identificacao(m.get("identificacao"))
        if sigla not in siglas_tipo:
            continue
        id_externo = m.get("id") or m.get("codigoMateria")
        registros.append({
            "id_externo": str(id_externo),
            "sigla_tipo": sigla,
            "numero": numero,
            "ano": ano,
            "ementa": m.get("ementa") or "",
            "data_apresentacao": m.get("dataApresentacao"),
            "autores": m.get("autoria") or "",
            "url_origem": _URL_FICHA.format(id=id_externo),
            "url_inteiro_teor": m.get("urlDocumento"),
            "ultima_tramitacao_data": m.get("dataSituacaoAtual"),
            "ultima_tramitacao_descricao": m.get("situacaoAtual"),
            "orgao_atual": m.get("enteIdentificador"),
        })
    return registros
