"""
Interpretação e classificação de um projeto de lei via LLM.

Suporta dois provedores, escolhidos pela variável de ambiente LLM_PROVIDER
("anthropic" ou "gemini"). Se não for definida, usa "gemini" quando
GEMINI_API_KEY estiver presente, senão "anthropic" — assim quem só configurou
uma chave gratuita do Gemini não precisa mexer em mais nada.
"""
from __future__ import annotations

import json
import os
import time
from typing import List, Literal

from pydantic import BaseModel

_SYSTEM_PROMPT = """\
Você é um analista legislativo especializado em regulação de saúde e da indústria \
farmacêutica, cobrindo o Congresso Nacional do Brasil (Câmara dos Deputados e \
Senado Federal) e o Congresso dos Estados Unidos. Sua tarefa é ler a ementa (e, \
quando disponível, um trecho do inteiro teor ou resumo oficial) de um projeto de \
lei federal e avaliar objetivamente seu impacto potencial sobre o setor de \
saúde/farma — incluindo hospitais, planos de saúde, indústria farmacêutica, \
distribuidoras, farmácias, profissionais de saúde, agências reguladoras (ANVISA/ANS \
no Brasil, FDA/CMS nos EUA) e pacientes.

O texto de entrada pode estar em português ou em inglês (projetos dos EUA) — \
responda SEMPRE em português, independentemente do idioma do texto de entrada, \
para manter o painel consistente.

Seja criterioso: a maioria dos PLs tramitando não tem relação real com saúde/farma \
mesmo quando aparecem numa busca ampla por tema. Marque relevante=false sempre que \
o impacto for nulo, indireto ou puramente administrativo/simbólico (ex: datas \
comemorativas, homenagens, requerimentos de sessão especial).
"""

TipoImpacto = Literal[
    "tributário", "regulatório", "trabalhista", "concorrencial",
    "orçamentário/gasto público", "direitos do paciente/consumidor", "outro",
]
Abrangencia = Literal["nacional", "setorial amplo", "nicho específico"]
NivelImpacto = Literal["alto", "médio", "baixo"]


class ClassificacaoSchema(BaseModel):
    relevante: bool
    justificativa_relevancia: str
    resumo: str
    areas_impactadas: List[str]
    tipo_impacto: List[TipoImpacto]
    abrangencia: Abrangencia
    nivel_impacto: NivelImpacto


# Mesmo schema acima, em formato de "tool" para a API da Anthropic.
_TOOL_SCHEMA = {
    "name": "classificar_pl",
    "description": "Registra a classificação estruturada de um projeto de lei quanto ao impacto em saúde/farma.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevante": {
                "type": "boolean",
                "description": "true se o PL tem impacto real (direto ou indireto relevante) sobre saúde/farma.",
            },
            "justificativa_relevancia": {
                "type": "string",
                "description": "Uma frase explicando por que é (ou não é) relevante.",
            },
            "resumo": {
                "type": "string",
                "description": "Resumo em linguagem simples (2-4 frases) do que o PL propõe.",
            },
            "areas_impactadas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subsetores específicos afetados, ex: 'planos de saúde', 'indústria farmacêutica', 'farmácias', 'hospitais', 'ANVISA'.",
            },
            "tipo_impacto": {
                "type": "array",
                "items": {"type": "string", "enum": list(TipoImpacto.__args__)},
                "description": "Naturezas do impacto identificadas.",
            },
            "abrangencia": {
                "type": "string",
                "enum": list(Abrangencia.__args__),
                "description": "Abrangência do efeito do PL.",
            },
            "nivel_impacto": {
                "type": "string",
                "enum": list(NivelImpacto.__args__),
                "description": "Magnitude estimada do impacto caso o PL seja aprovado.",
            },
        },
        "required": ["relevante", "justificativa_relevancia", "resumo", "areas_impactadas",
                      "tipo_impacto", "abrangencia", "nivel_impacto"],
    },
}


class ClassificacaoIndisponivel(RuntimeError):
    pass


def _provider() -> str:
    explicito = os.environ.get("LLM_PROVIDER")
    if explicito:
        return explicito.strip().lower()
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return "anthropic"


def _montar_conteudo(ementa: str, texto_inteiro_teor: str | None) -> str:
    conteudo = f"EMENTA:\n{ementa}\n"
    if texto_inteiro_teor:
        conteudo += f"\nINTEIRO TEOR (trecho):\n{texto_inteiro_teor}\n"
    return conteudo


def _classificar_anthropic(conteudo: str) -> dict:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ClassificacaoIndisponivel("ANTHROPIC_API_KEY não configurada")

    default_headers = {}
    workspace_id = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    if workspace_id:
        default_headers["anthropic-workspace-id"] = workspace_id

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
    client = anthropic.Anthropic(api_key=api_key, default_headers=default_headers or None)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "classificar_pl"},
            messages=[{"role": "user", "content": conteudo}],
        )
    except anthropic.APIError as exc:
        raise ClassificacaoIndisponivel(str(exc)) from exc

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    raise ClassificacaoIndisponivel("resposta do modelo não trouxe classificação estruturada")


def _classificar_gemini(conteudo: str) -> dict:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ClassificacaoIndisponivel("GEMINI_API_KEY não configurada")

    model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=conteudo,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ClassificacaoSchema,
            ),
        )
    except Exception as exc:  # a lib do Gemini não tem uma classe de erro única e estável
        raise ClassificacaoIndisponivel(str(exc)) from exc

    if not response.text:
        raise ClassificacaoIndisponivel("resposta do modelo não trouxe classificação estruturada")
    return json.loads(response.text)


_ERROS_TRANSITORIOS = ("503", "UNAVAILABLE", "429", "overloaded", "rate limit", "high demand")


def _com_retry(fn, tentativas: int = 3, espera_inicial: float = 2.0) -> dict:
    """Repete a chamada em caso de erro transitório (sobrecarga/rate limit), com backoff simples."""
    for tentativa in range(tentativas):
        try:
            return fn()
        except ClassificacaoIndisponivel as exc:
            transitorio = any(marca in str(exc) for marca in _ERROS_TRANSITORIOS)
            if not transitorio or tentativa == tentativas - 1:
                raise
            time.sleep(espera_inicial * (2 ** tentativa))


def classificar(ementa: str, texto_inteiro_teor: str | None) -> dict:
    """Classifica um PL usando o provedor configurado. Levanta ClassificacaoIndisponivel em caso de erro."""
    conteudo = _montar_conteudo(ementa, texto_inteiro_teor)
    provider = _provider()
    if provider == "gemini":
        return _com_retry(lambda: _classificar_gemini(conteudo))
    if provider == "anthropic":
        return _com_retry(lambda: _classificar_anthropic(conteudo))
    raise ClassificacaoIndisponivel(f"LLM_PROVIDER desconhecido: '{provider}' (use 'anthropic' ou 'gemini')")
