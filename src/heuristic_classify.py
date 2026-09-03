"""
Classificação heurística (sem IA) por palavras-chave.

Serve como camada sempre disponível e 100% gratuita: roda mesmo sem nenhuma
chave de API configurada, e também como fallback quando a IA falha (rate
limit, sem crédito, fora do ar). É deliberadamente mais grosseira que a
classificação por IA — não entende contexto, só detecta a presença de termos
na ementa/inteiro teor — então tende a super-detectar relevância. Serve para
nunca deixar o relatório vazio, não para substituir de vez a IA.

Suporta português (idioma="pt", padrão — Câmara/Senado) e inglês
(idioma="en" — Congresso dos EUA), com dois dicionários de termos
independentes.
"""
from __future__ import annotations

import re

# padrão (regex, case-insensitive) -> área impactada
_AREAS_PT = {
    r"farmac[êe]utic": "Indústria farmacêutica",
    r"medicamento": "Medicamentos",
    r"\bANVISA\b": "ANVISA / regulação sanitária",
    r"\bANS\b": "ANS / planos de saúde",
    r"plano(s)? de sa[úu]de": "Planos de saúde",
    r"operadora(s)? de sa[úu]de": "Operadoras de saúde",
    r"hospital": "Hospitais",
    r"\bSUS\b|sistema [úu]nico de sa[úu]de": "SUS / saúde pública",
    r"farm[áa]cia|drogaria": "Farmácias",
    r"vacina": "Imunização",
    r"insumo(s)? (hospitalar|m[ée]dico|farmac[êe]utico)": "Insumos de saúde",
    r"profissional(is)? de sa[úu]de|\bm[ée]dico(s)?\b|enfermeir": "Profissionais de saúde",
    r"\bpaciente": "Direitos do paciente",
    r"dispositivo(s)? m[ée]dico": "Dispositivos médicos",
    r"telemedicina|telessa[úu]de": "Telemedicina",
}

# padrão -> tipo de impacto (mesmos rótulos usados pela classificação por IA)
_TIPO_IMPACTO_PT = {
    r"tribut|imposto|isen[çc][ãa]o fiscal": "tributário",
    r"regulament|registro sanit[áa]rio|\bANVISA\b": "regulatório",
    r"trabalh|jornada|empregad": "trabalhista",
    r"concorr[êe]nc|mercado|monop[óo]lio": "concorrencial",
    r"or[çc]ament|gasto p[úu]blico|\bSUS\b": "orçamentário/gasto público",
    r"\bpaciente|consumidor|direito": "direitos do paciente/consumidor",
}

# Equivalentes em inglês, pro Congresso dos EUA. Os rótulos de saída ficam em
# português (mesmo vocabulário do restante do painel) — só o texto de entrada
# e os termos buscados é que são em inglês.
_AREAS_EN = {
    r"pharmac(y|eutical)": "Indústria farmacêutica",
    r"\bdrug(s)?\b|medication": "Medicamentos",
    r"\bFDA\b|food and drug administration": "FDA / regulação sanitária",
    r"health insurance|\bmedicare\b|\bmedicaid\b": "Planos de saúde",
    r"insurer|health plan": "Operadoras de saúde",
    r"hospital": "Hospitais",
    r"public health": "Saúde pública",
    r"\bpharmacy\b|\bpharmacies\b": "Farmácias",
    r"vaccin": "Imunização",
    r"medical (device|supply|supplies)": "Insumos de saúde",
    r"physician|\bnurse(s)?\b|health (care )?provider": "Profissionais de saúde",
    r"\bpatient": "Direitos do paciente",
    r"medical device": "Dispositivos médicos",
    r"telehealth|telemedicine": "Telemedicina",
}

_TIPO_IMPACTO_EN = {
    r"\btax\b|taxation|tax exemption": "tributário",
    r"regulat|\bFDA\b|licensure": "regulatório",
    r"labor|employment|workforce": "trabalhista",
    r"competition|market|antitrust|monopoly": "concorrencial",
    r"appropriation|federal spending|\bbudget\b|medicare|medicaid": "orçamentário/gasto público",
    r"\bpatient|consumer|\bright(s)?\b": "direitos do paciente/consumidor",
}

_DICIONARIOS = {
    "pt": (_AREAS_PT, _TIPO_IMPACTO_PT),
    "en": (_AREAS_EN, _TIPO_IMPACTO_EN),
}


def classificar(ementa: str, texto_inteiro_teor: str | None, idioma: str = "pt") -> dict:
    """Classificação por palavras-chave. Determinística, gratuita, nunca levanta erro."""
    areas_dict, tipos_dict = _DICIONARIOS.get(idioma, _DICIONARIOS["pt"])
    base = f"{ementa or ''}\n{texto_inteiro_teor or ''}"

    areas = sorted({rotulo for padrao, rotulo in areas_dict.items() if re.search(padrao, base, re.IGNORECASE)})
    tipos = sorted({rotulo for padrao, rotulo in tipos_dict.items() if re.search(padrao, base, re.IGNORECASE)})

    relevante = len(areas) > 0
    if len(areas) >= 3:
        nivel = "alto"
    elif len(areas) == 2:
        nivel = "médio"
    else:
        nivel = "baixo"

    return {
        "relevante": relevante,
        "justificativa_relevancia": (
            f"{len(areas)} termo(s) de saúde/farma detectado(s) por palavra-chave (sem IA)."
            if relevante else "Nenhum termo de saúde/farma detectado por palavra-chave (sem IA)."
        ),
        "resumo": None,  # sem IA não há como resumir com confiança — o relatório cai de volta para a ementa
        "areas_impactadas": areas,
        "tipo_impacto": tipos or ["outro"],
        "abrangencia": "setorial amplo" if len(areas) >= 3 else "nicho específico",
        "nivel_impacto": nivel,
    }
