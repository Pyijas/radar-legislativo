"""
Cliente para a agenda pública de autoridades via API oficial do e-Agendas
(CGU) — https://eagendas.cgu.gov.br/api/v2, documentada em
github.com/cgugovbr/eagendas-publico. Cobre autoridades que a agenda do
Presidente (src/agenda_presidente_client.py, scraping de gov.br/planalto,
sem token) não cobre: Ministro da Saúde, Ministro do MDIC e
Diretor-Presidente da Anvisa — pedido do usuário em 18/09/2026.

Precisa de EAGENDAS_TOKEN no .env — um token PESSOAL (ligado à conta
gov.br de quem gerou), obtido em eagendas.cgu.gov.br > perfil > "Meus
tokens". Sem essa variável, listar_novas() de cada autoridade
simplesmente devolve lista vazia (mesmo padrão de "fonte opcional sem
chave" do congress_client.py).

Como funciona a API: cada compromisso é registrado contra um "Agente
Público Obrigado" (apo_id), vinculado a um órgão (orgao_id) e a um cargo em
comissão (cargo_comissao_id — esse é o cargo em si, ex: "MINISTRO(A) DE
ESTADO DA SAÚDE"; o apo_id é a PESSOA que ocupa o cargo agora, e muda se a
pessoa trocar). _AUTORIDADES abaixo foi resolvido manualmente em 18/09/2026
via:

    GET /api/v2/orgaos?sigla=MS|MDIC|ANVISA          -> acha orgao_id
    GET /api/v2/agentes-publicos-obrigados?orgao_id=X&situacao=ativo
        -> lista todos os agentes ativos do órgão; procurar pelo
           cargo_comissao contendo "MINISTRO" ou "DIRETOR-PRESIDENTE"

Se a pessoa no cargo mudar (troca de ministro, por exemplo), o apo_id
antigo para de aparecer em situacao=ativo — repita a consulta acima pra
achar o apo_id novo e atualize _AUTORIDADES.
"""
from __future__ import annotations

import datetime as dt
import os

import requests

BASE_URL = "https://eagendas.cgu.gov.br/api/v2"
_TIMEOUT = 30
_URL_PUBLICA = "https://eagendas.cgu.gov.br/"

# Resolvido manualmente em 18/09/2026 (ver docstring do módulo pra como
# atualizar se a pessoa no cargo mudar).
_AUTORIDADES = {
    "ministro_saude": {"apo_id": 40732, "autoridade": "Alexandre Padilha", "cargo": "Ministro de Estado da Saúde"},
    "ministro_mdic": {"apo_id": 48764, "autoridade": "Marcio Elias Rosa", "cargo": "Ministro do Desenvolvimento, Indústria, Comércio e Serviços"},
    "diretor_anvisa": {"apo_id": 44867, "autoridade": "Leandro Safatle", "cargo": "Diretor-Presidente da Anvisa"},
}


def _token() -> str | None:
    return os.environ.get("EAGENDAS_TOKEN") or None


def _headers(token: str) -> dict:
    return {"Accept": "application/json", "Authorization": f"Bearer {token}"}


def listar_novas(dias: int) -> list[dict]:
    """Compromissos de TODAS as autoridades configuradas em _AUTORIDADES
    dos últimos `dias` dias, já no formato de registro usado por
    main.py/storage.py pra agenda (chaves: autoridade, cargo, id_externo,
    data, horario, titulo, local, url_origem). Lista vazia (sem erro) se
    EAGENDAS_TOKEN não estiver configurado."""
    token = _token()
    if not token:
        return []

    fim = dt.date.today()
    inicio = fim - dt.timedelta(days=dias)
    params_data = {
        "data_inicio": inicio.strftime("%d-%m-%Y"),
        "data_termino": fim.strftime("%d-%m-%Y"),
    }

    registros = []
    for chave_autoridade, info in _AUTORIDADES.items():
        resp = requests.get(
            f"{BASE_URL}/compromissos",
            params={**params_data, "apo_id": info["apo_id"]},
            headers=_headers(token), timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        corpo = resp.json()
        if not corpo.get("sucesso"):
            continue

        compromissos = corpo.get("resposta", {}).get("compromissos", [])
        for c in compromissos:
            titulo = c.get("assunto") or c.get("tipo_compromisso") or "Compromisso"
            registros.append({
                "autoridade": info["autoridade"],
                "cargo": info["cargo"],
                "id_externo": str(c.get("id")),
                "data": _iso(c.get("data_inicio")),
                "horario": c.get("hora_inicio") or "",
                "titulo": titulo,
                "local": c.get("local") or "",
                "url_origem": _URL_PUBLICA,
            })

    return registros


def _iso(data_br: str | None) -> str | None:
    """Converte DD-MM-AAAA (formato da API) pra AAAA-MM-DD (formato usado
    no resto do projeto)."""
    if not data_br:
        return None
    try:
        return dt.datetime.strptime(data_br, "%d-%m-%Y").date().isoformat()
    except ValueError:
        return None
