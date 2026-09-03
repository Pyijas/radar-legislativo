"""
Cliente para a API de Dados Abertos do Senado Federal — INÍCIO DE INTEGRAÇÃO,
AINDA NÃO USADO PELO PIPELINE PRINCIPAL (main.py só usa a Câmara por enquanto).

Documentação: https://legis.senado.leg.br/dadosabertos/docs/index.html

O endpoint principal de matérias (/materia/atualizadas) está sendo
descontinuado pelo próprio Senado (desativação completa prevista, segundo os
metadados da própria API, pra fev/2026) em favor de um novo endpoint mais
limpo, /processo, que é o que este módulo já usa.

O que falta pra isso virar uma segunda fonte de verdade, ativa igual à
Câmara (ver README, seção "Preenchendo o histórico"):

1. Confirmar como filtrar por tema/assunto (ex: Saúde) nesse novo endpoint —
   testei um parâmetro `assunto=` na consulta e ele não pareceu filtrar de
   verdade (a resposta trouxe matérias sem relação com o termo buscado).
   Pode ser que o filtro correto seja por código de uma tabela de referência
   (como o `codTema` da Câmara) em vez de texto livre — precisa investigar a
   documentação oficial ou testar outros parâmetros.
2. Mapear os campos de tramitação/situação (`situacaoAtual`,
   `dataSituacaoAtual`) pro mesmo formato usado em storage.py
   (ultima_tramitacao_data/descricao, orgao_atual) — os nomes já são bem
   parecidos, deve ser um mapeamento direto.
3. Decidir como tratar matérias que tramitam nas duas casas (Câmara E
   Senado) pra não duplicar o mesmo PL no banco com dois registros
   diferentes — provavelmente por número de lei "oficial" ou por texto do
   `identificacao` (ex: "PL 5231/2026") batendo com o que já vem da Câmara.
4. Extrair texto do inteiro teor: o campo `urlDocumento` aponta pro PDF, mas
   o formato do link é diferente do usado na Câmara — o código de
   src/pdf_extract.py deve funcionar do mesmo jeito (é PDF puro), só precisa
   testar.
5. Adaptar heuristic_classify.py/classify.py: já são genéricos o bastante
   (recebem só ementa + texto), não deveriam precisar de mudança nenhuma.

O que já funciona, testado manualmente: buscar matérias apresentadas num
período (parâmetros de data) — ver `listar_novas_materias` abaixo. O
parâmetro `tipo` foi testado com `tipo=PL` e a resposta trouxe também
Requerimentos (REQ), então ou o filtro não funciona como o nome sugere, ou o
valor certo pra "Projeto de Lei" nesse endpoint não é literalmente "PL" —
precisa investigar a tabela de referência de tipos antes de confiar nesse
filtro. Por ora, `listar_novas_materias` filtra os tipos localmente, em
Python, depois de buscar (mais lento, mas correto).
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import requests

BASE_URL = "https://legis.senado.leg.br/dadosabertos"
_TIMEOUT = 30


def _get(path: str, params: dict | None = None) -> Any:
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=_TIMEOUT,
                         headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


def listar_novas_materias(dias: int, siglas_tipo: list[str] | None = None) -> list[dict]:
    """
    Lista matérias apresentadas nos últimos `dias` dias. Testado e
    funcionando em 03/09/2026 (retornou matérias reais, com ementa,
    situação atual e link do documento).

    siglas_tipo: ex. ["PL", "PLP"]. O filtro é feito localmente (client-side)
    comparando com o início do campo `identificacao` (ex: "PL 5231/2026"),
    já que o parâmetro `tipo` da própria API não filtrou corretamente num
    teste manual (ver docstring do módulo). Se None, traz todos os tipos.

    Ainda NÃO filtra por tema (ver item 1 do docstring do módulo) — traz
    todas as matérias do período, sem recorte de saúde/farma.
    """
    hoje = dt.date.today()
    inicio = hoje - dt.timedelta(days=dias)
    params = {
        "dataInicioApresentacao": inicio.isoformat(),
        "dataFimApresentacao": hoje.isoformat(),
    }
    dados = _get("/processo", params)
    materias = dados if isinstance(dados, list) else []
    if siglas_tipo:
        materias = [m for m in materias if str(m.get("identificacao", "")).split(" ")[0] in siglas_tipo]
    return materias
