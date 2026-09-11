"""Download e extração de texto do inteiro teor (PDF) de uma proposição."""
from __future__ import annotations

import io

import requests
from pypdf import PdfReader

_TIMEOUT = 30
_MAX_BYTES = 20 * 1024 * 1024  # 20 MB — proteção contra PDFs anormalmente grandes
_MAX_CHARS = 15_000  # limite de texto enviado ao modelo, para controlar custo/latência


def extrair_texto(url_inteiro_teor: str | None) -> str | None:
    """Baixa o PDF do inteiro teor e retorna o texto extraído (truncado), ou None se falhar."""
    if not url_inteiro_teor:
        return None
    try:
        resp = requests.get(url_inteiro_teor, timeout=_TIMEOUT, stream=True)
        resp.raise_for_status()
        conteudo = resp.raw.read(_MAX_BYTES + 1, decode_content=True)
        if len(conteudo) > _MAX_BYTES:
            return None  # PDF grande demais, melhor pular do que estourar custo/tempo

        reader = PdfReader(io.BytesIO(conteudo))
        partes = []
        total = 0
        for page in reader.pages:
            texto = page.extract_text() or ""
            partes.append(texto)
            total += len(texto)
            if total >= _MAX_CHARS:
                break
        texto_completo = "\n".join(partes).strip()
        return texto_completo[:_MAX_CHARS] if texto_completo else None
    except Exception:
        # PDF indisponível, corrompido ou digitalizado sem camada de texto (scan).
        # A classificação cai de volta para a ementa, que quase sempre já é suficiente.
        return None
