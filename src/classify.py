"""
Interpretação e classificação de um projeto de lei via LLM.

Suporta três provedores, escolhidos pela variável de ambiente LLM_PROVIDER
("anthropic", "gemini" ou "ollama"). Se não for definida, usa "gemini" quando
GEMINI_API_KEY estiver presente, senão "anthropic" — assim quem só configurou
uma chave gratuita do Gemini não precisa mexer em mais nada.

"ollama" roda um modelo local via Ollama (https://ollama.com/), sem chave de
API nem custo por token — precisa do serviço `ollama serve` rodando em
OLLAMA_BASE_URL (padrão http://localhost:11434) com o modelo de OLLAMA_MODEL
já baixado (`ollama pull <modelo>`). Mesmo prompt e mesmo schema estruturado
dos outros dois provedores — o resto do pipeline (main.py, storage.py,
report.py) não sabe nem precisa saber qual dos três gerou a classificação.
"""
from __future__ import annotations

import json
import os
import time
from typing import List, Literal

import requests
from pydantic import BaseModel, ValidationError

_SYSTEM_PROMPT = """\
Você é um analista de inteligência regulatória especializado em avaliar o impacto \
de projetos de lei sobre a INDÚSTRIA FARMACÊUTICA — fabricantes, distribuidoras e \
importadoras de medicamentos/vacinas/biológicos, farmácias, e os mecanismos \
regulatórios e comerciais que determinam registro, preço, patente, prescrição e \
acesso a esses produtos (ANVISA no Brasil, FDA/CMS nos EUA, ISP no Chile). Cobre o \
Congresso Nacional do Brasil (Câmara dos Deputados e Senado Federal), o Congresso \
dos Estados Unidos e o Congresso Nacional do Chile (Cámara de Diputadas y \
Diputados e Senado).

O texto de entrada pode estar em português, inglês (projetos dos EUA) ou espanhol \
(projetos do Chile) — responda SEMPRE em português, independentemente do idioma \
do texto de entrada, para manter o painel consistente.

CRITÉRIO DE RELEVÂNCIA — marque relevante=true quando o PL afeta a indústria \
farmacêutica por pelo menos um destes dois caminhos:

1. IMPACTO DIRETO: regula fabricação, registro sanitário, importação, \
   distribuição, comercialização, publicidade, preço, patente/concorrência com \
   genéricos, ensaios clínicos, prescrição/dispensação (ex: receita eletrônica), \
   uso compassivo/acesso expandido, ou cria/altera crime relacionado a \
   medicamentos (furto, falsificação, venda ilegal).

2. IMPACTO INDIRETO POR DEMANDA INDUZIDA: obriga (ou desobriga) planos de saúde, \
   seguradoras, SUS, Medicare/Medicaid, Isapre/Fonasa ou qualquer pagador a \
   cobrir/custear um medicamento, vacina ou tratamento farmacológico específico \
   — mesmo que o texto não mencione a indústria farmacêutica diretamente. Esse \
   tipo de mandato cria (ou remove) demanda garantida para quem fabrica aquele \
   produto. Exemplo: um PL que obriga planos de saúde a cobrir o tratamento X \
   impacta a indústria farmacêutica que produz X, ainda que a ementa fale só em \
   "planos de saúde". Quando classificar por esse caminho, deixe isso explícito \
   na justificativa (não só na área impactada) — diga qual produto/tratamento \
   tem a demanda afetada e por meio de qual pagador.

NÃO marque relevante=true só por tocar em saúde de forma genérica sem esse vínculo \
com produto ou tratamento farmacológico específico. NÃO contam, mesmo sendo PLs de \
saúde legítimos, por não gerarem efeito de negócio sobre a indústria farmacêutica: \
financiamento/remuneração hospitalar geral, programas de saúde mental ou \
reabilitação sem medicação associada, força de trabalho de saúde (mobilidade de \
médicos, agentes comunitários, licenciamento profissional), infraestrutura/ \
segurança predial de estabelecimentos de saúde, cobertura de serviços \
profissionais (consultas, terapias) sem produto farmacêutico atrelado, e \
benefícios fiscais/sociais a pacientes que não envolvem um medicamento ou \
tratamento farmacológico específico.

Seja criterioso: a maioria dos PLs de saúde tramitando não afeta a indústria \
farmacêutica mesmo quando aparecem numa busca ampla por tema de saúde. Marque \
relevante=false sempre que o impacto for nulo, puramente administrativo/simbólico \
(ex: datas comemorativas, homenagens), ou restrito a serviços/infraestrutura de \
saúde sem vínculo com um produto farmacêutico.
"""

_SYSTEM_PROMPT_MONITORAMENTO = """\
Você é um analista de inteligência regulatória especializado em avaliar o impacto \
sobre a INDÚSTRIA FARMACÊUTICA de notícias institucionais (Anvisa, Ministério da \
Saúde, ANS) e de compromissos da agenda pública de autoridades do governo federal \
brasileiro (Presidente, Vice-Presidente, Ministro da Saúde, diretor-presidente da \
Anvisa). Mesmo critério de relevância usado para projetos de lei — marque \
relevante=true quando o item afeta a indústria farmacêutica por pelo menos um \
destes caminhos:

1. IMPACTO DIRETO: aprovação/registro/recolhimento de medicamento, vacina ou \
   biológico nomeado; mudança de processo regulatório de registro/preço/patente; \
   acordo internacional de reconhecimento regulatório; recall ou ação de \
   fiscalização sobre medicamentos; visita ou reunião institucional com uma \
   empresa farmacêutica específica (inclusive concorrentes) ou evento do setor.

2. IMPACTO INDIRETO POR DEMANDA INDUZIDA: notícia ou compromisso sobre mandato \
   de cobertura de um medicamento/tratamento farmacológico específico por SUS, \
   planos de saúde ou outro pagador — mesmo sem mencionar a indústria \
   diretamente.

NÃO marque relevante=true para: campanhas de conscientização/vacinação em massa \
sem produto nomeado, infraestrutura/serviços de saúde (UTI, ambulância, mutirões \
com hospitais particulares), reuniões político-administrativas sem pauta \
farmacêutica, matérias de dispositivos médicos/diagnósticos/suplementos/cosméticos \
(não são medicamentos), ou compromissos de agenda sem relação com o setor.

Responda sempre em português. Se o item for uma notícia, "resumo" deve condensar o \
título/texto em 1-2 frases; se for um compromisso de agenda, "resumo" deve \
explicar por que o compromisso é ou não estrategicamente relevante pro setor.
"""

_SYSTEM_PROMPT_MUDANCA_REGULATORIA = """\
Você é um analista de inteligência regulatória. Você recebe notícias publicadas \
pelas agências reguladoras de medicamentos da América Latina (ANMAT/Argentina, \
DIGEMID/Peru, ISP/Chile, Ministério da Saúde/AGEMED da Bolívia, MSP/Uruguai, e \
eventualmente outras). O texto de entrada está em espanhol — responda SEMPRE em \
português, para manter o painel consistente com o resto do sistema.

ESCOPO — diferente do monitoramento do Brasil (que também cobre agenda/reuniões \
estratégicas), aqui o pedido é mais estrito: marque relevante=true SÓ quando a \
notícia representa uma MUDANÇA REGULATÓRIA OU NORMATIVA DE VERDADE — algo que \
altera, cria ou revoga uma regra que rege o setor farmacêutico naquele país. \
Exemplos do que CONTA:

- Nova resolução/regulamento/decreto sobre registro sanitário de medicamentos, \
  biológicos ou vacinas (requisitos, prazos, documentação).
- Mudança nas regras de fixação, controle ou reajuste de preço de medicamentos.
- Nova exigência (ou dispensa) de licença, certificação (ex: Boas Práticas de \
  Fabricação) ou inspeção para fabricar/importar/comercializar medicamentos.
- Mudança em regra de patente, exclusividade de dados, ou concorrência com \
  genéricos/biossimilares.
- Novo mandato (ou remoção de mandato) de cobertura de um medicamento/tratamento \
  específico por um pagador público ou plano de saúde do país.
- Acordo internacional de reconhecimento regulatório mútuo que muda o processo de \
  registro/importação.

O que NÃO CONTA (marque relevante=false), mesmo vindo da agência reguladora e \
mesmo envolvendo medicamentos — porque é aplicação/fiscalização de regra já \
existente, não uma mudança de regra: alerta de recolhimento (recall) ou proibição \
de um produto específico por não cumprir norma já vigente, apreensão/multa/ \
sanção contra uma empresa específica, inspeção de rotina, feira/campanha \
informativa ao público, participação em evento/congresso, estatística de \
produção/importação, e qualquer notícia de saúde genérica sem relação com regra \
regulatória de medicamentos (hospitais, força de trabalho, campanhas de \
conscientização, doenças sem produto farmacêutico nomeado).

Na dúvida entre "mudou uma regra" e "aplicaram uma regra que já existia", marque \
relevante=false — o objetivo aqui é rastrear só o que muda o jogo regulatório, \
não o noticiário operacional do dia a dia da agência.

"resumo" deve dizer, em 1-2 frases, QUAL regra mudou e o que passa a valer.
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
    "description": "Registra a classificação estruturada de um projeto de lei quanto ao impacto na indústria farmacêutica.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevante": {
                "type": "boolean",
                "description": "true se o PL afeta a indústria farmacêutica, direto (regulação/comercialização de medicamentos) ou por demanda induzida (mandato de cobertura de um tratamento farmacológico específico por planos/SUS/seguradoras).",
            },
            "justificativa_relevancia": {
                "type": "string",
                "description": "Uma frase explicando por que é (ou não é) relevante — se for por demanda induzida, cite o produto/tratamento e o pagador envolvido.",
            },
            "resumo": {
                "type": "string",
                "description": "Resumo em linguagem simples (2-4 frases) do que o PL propõe.",
            },
            "areas_impactadas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subsetores farmacêuticos específicos afetados, ex: 'indústria farmacêutica', 'medicamentos', 'farmácias', 'distribuidoras', 'ANVISA' — ou o pagador cuja cobertura obrigatória induz demanda, ex: 'planos de saúde', 'SUS', 'Isapres'.",
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


def _classificar_anthropic(conteudo: str, system_prompt: str = _SYSTEM_PROMPT) -> dict:
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
            system=system_prompt,
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


def _classificar_gemini(conteudo: str, system_prompt: str = _SYSTEM_PROMPT) -> dict:
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
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=ClassificacaoSchema,
            ),
        )
    except Exception as exc:  # a lib do Gemini não tem uma classe de erro única e estável
        raise ClassificacaoIndisponivel(str(exc)) from exc

    if not response.text:
        raise ClassificacaoIndisponivel("resposta do modelo não trouxe classificação estruturada")
    return json.loads(response.text)


def _classificar_ollama(conteudo: str, system_prompt: str = _SYSTEM_PROMPT) -> dict:
    """
    Classifica via um modelo local rodando no Ollama (https://ollama.com/) —
    sem chave de API, sem custo por token, 100% offline depois do modelo
    baixado. Precisa de `ollama serve` rodando (padrão: localhost:11434) e do
    modelo de OLLAMA_MODEL já baixado via `ollama pull <modelo>` (padrão:
    qwen2.5:7b-instruct — bom equilíbrio entre qualidade de instrução
    estruturada/JSON, suporte multilíngue PT/EN/ES e velocidade em hardware
    doméstico, ex: Apple Silicon com 16GB de RAM).

    Usa o endpoint /api/chat com `format` = o JSON Schema do
    ClassificacaoSchema (suportado desde o Ollama 0.5+), que força o modelo a
    responder só com um JSON validável contra esse schema — mesmo mecanismo
    de "saída estruturada" que os outros dois provedores usam, só que
    aplicado no lado do servidor local em vez de uma API paga.
    """
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")

    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conteudo},
                ],
                "format": ClassificacaoSchema.model_json_schema(),
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ClassificacaoIndisponivel(
            f"Ollama indisponível em {base_url} (rode 'ollama serve' e confirme "
            f"que o modelo '{model}' foi baixado com 'ollama pull {model}'): {exc}"
        ) from exc

    texto_resposta = (response.json().get("message") or {}).get("content")
    if not texto_resposta:
        raise ClassificacaoIndisponivel("Ollama não retornou conteúdo na resposta")

    try:
        dados = json.loads(texto_resposta)
        ClassificacaoSchema.model_validate(dados)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ClassificacaoIndisponivel(f"Ollama retornou JSON fora do schema esperado: {exc}") from exc

    return dados


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


def _classificar_com_prompt(conteudo: str, system_prompt: str) -> dict:
    """Despacha pro provedor configurado (mesmo mecanismo pra PL/notícia/agenda —
    só muda o system_prompt e o texto de entrada)."""
    provider = _provider()
    if provider == "gemini":
        return _com_retry(lambda: _classificar_gemini(conteudo, system_prompt))
    if provider == "anthropic":
        return _com_retry(lambda: _classificar_anthropic(conteudo, system_prompt))
    if provider == "ollama":
        # Sem retry por rate-limit (não existe num modelo local) — só deixa a
        # exceção subir direto se o serviço estiver fora do ar.
        return _classificar_ollama(conteudo, system_prompt)
    raise ClassificacaoIndisponivel(f"LLM_PROVIDER desconhecido: '{provider}' (use 'anthropic', 'gemini' ou 'ollama')")


def classificar(ementa: str, texto_inteiro_teor: str | None) -> dict:
    """Classifica um PL usando o provedor configurado. Levanta ClassificacaoIndisponivel em caso de erro."""
    conteudo = _montar_conteudo(ementa, texto_inteiro_teor)
    return _classificar_com_prompt(conteudo, _SYSTEM_PROMPT)


def classificar_noticia(titulo: str, resumo: str | None) -> dict:
    """Classifica uma notícia (Anvisa/Ministério da Saúde/ANS) quanto ao impacto
    na indústria farmacêutica — mesmo provedor/schema de classificar(), prompt
    ajustado pro tipo de conteúdo (ver _SYSTEM_PROMPT_MONITORAMENTO)."""
    conteudo = f"TÍTULO DA NOTÍCIA:\n{titulo}\n"
    if resumo:
        conteudo += f"\nRESUMO:\n{resumo}\n"
    return _classificar_com_prompt(conteudo, _SYSTEM_PROMPT_MONITORAMENTO)


def classificar_evento_agenda(titulo: str, autoridade: str, local: str | None) -> dict:
    """Classifica um compromisso de agenda pública de uma autoridade quanto ao
    impacto na indústria farmacêutica — mesmo mecanismo de classificar_noticia()."""
    conteudo = f"AUTORIDADE: {autoridade}\nCOMPROMISSO: {titulo}\n"
    if local:
        conteudo += f"LOCAL: {local}\n"
    return _classificar_com_prompt(conteudo, _SYSTEM_PROMPT_MONITORAMENTO)


def classificar_mudanca_regulatoria(titulo: str, resumo: str | None) -> dict:
    """Classifica uma notícia de agência reguladora latino-americana (ANMAT,
    DIGEMID, ISP, etc — ver main.py) quanto a ser ou não uma MUDANÇA
    REGULATÓRIA de verdade — critério mais estrito que classificar_noticia(),
    que também aceita sinal de agenda/estratégia (ver
    _SYSTEM_PROMPT_MUDANCA_REGULATORIA). Adicionada em 11/09/2026 a pedido do
    usuário: "é só pra oq alterou na lei"."""
    conteudo = f"TÍTULO DA NOTÍCIA:\n{titulo}\n"
    if resumo:
        conteudo += f"\nRESUMO:\n{resumo}\n"
    return _classificar_com_prompt(conteudo, _SYSTEM_PROMPT_MUDANCA_REGULATORIA)
