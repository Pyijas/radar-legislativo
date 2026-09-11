"""
Cliente para o webservice público de tramitação do Congresso Nacional do
Chile, mantido pelo Senado (`tramitacion.senado.cl/wspublico`).

Documentação (páginas HTML com o formulário de teste, sem Swagger/OpenAPI):
https://opendata.camara.cl/ (seção "Servicios web del Senado")
https://tramitacion.senado.cl/wspublico/invoca_tramitacion_fecha.html
https://tramitacion.senado.cl/wspublico/invoca_proyecto.html

Não requer chave nem cadastro — confirmado funcionando via teste direto em
04/09/2026 (`?fecha=28/08/2026` devolveu 113 projetos com movimento na
semana, incluindo PLs de saúde/farma reconhecíveis por palavra-chave, ex:
"regular la comercialización de productos farmacéuticos").

Diferenças em relação às fontes do Brasil/EUA:

- Um único endpoint (`tramitacion.php?fecha=DD/MM/YYYY`) devolve TODOS os
  projetos que tiveram qualquer movimento desde a data informada — cobrindo
  as DUAS casas ao mesmo tempo (Cámara de Diputadas y Diputados e Senado),
  já com a tramitação completa (histórico de trâmites, autores, link do
  documento original) embutida na própria resposta, sem precisar de uma
  segunda chamada de detalhe (mesmo padrão do Senado brasileiro). Por isso,
  ao contrário de Câmara/Senado do Brasil, aqui NÃO existe duplicação entre
  casas a evitar — é uma fonte só, que já acompanha o projeto conforme ele
  muda de casa ao longo da tramitação.
- **Limite de ~1 mês pra trás**: o próprio formulário do serviço avisa
  "Esta fecha no puede exceder de un mes hacia atrás" — diferente da Câmara
  brasileira (aceita qualquer profundidade, só limita cada consulta a 90
  dias) e do Senado brasileiro (sem limite documentado). Na prática,
  `--dias` maior que `_MAX_DIAS` aqui não amplia o resultado: o valor é
  limitado antes da consulta. Pra backfill de histórico mais antigo, seria
  necessário outro endpoint (por boletim individual, projeto a projeto) —
  fora do escopo da coleta diária deste módulo.
- **Resposta é XML, não JSON** (serviço legado, sem Swagger) — parseado com
  `xml.etree.ElementTree`, da biblioteca padrão do Python (sem dependência
  nova no requirements.txt).
- **`link_mensaje_mocion`** (o documento original do projeto — mensagem do
  Executivo ou moção parlamentar) costuma ser um arquivo `.doc`, não PDF.
  `pdf_extract.extrair_texto()` tenta mesmo assim, mas falha graciosamente
  nesse caso (mesmo comportamento já documentado no README para PDFs
  escaneados) — a classificação cai de volta pro título do projeto, que já
  costuma ser descritivo o suficiente.
- Cada projeto é identificado por um "Número de Boletín" no formato
  `NNNNN-MM` (ex: `8654-15`), onde o sufixo `-MM` indica a matéria/área de
  origem, não um ano. Usado direto como `id_externo` e como `numero`; como
  não há um "ano" natural do próprio boletim, `ano` aqui guarda o ano de
  `fecha_ingreso` (data de apresentação).
- A "casa" atual do projeto é inferida do último trâmite registrado (campo
  `CAMARATRAMITE`: "C.Diputados" ou "Senado"), com fallback pro campo
  `camara_origen` (casa de origem) quando a lista de trâmites vem vazia.
"""
from __future__ import annotations

import datetime as dt
import xml.etree.ElementTree as ET
from typing import Any

import requests

BASE_URL = "https://tramitacion.senado.cl/wspublico/tramitacion.php"
_TIMEOUT = 30
_MAX_DIAS = 29  # o serviço não aceita fecha > ~1 mês atrás; 1 dia de margem de segurança

_CASA_POR_ETIQUETA = {"c.diputados": "camara", "senado": "senado"}
_URL_FICHA = "https://www.senado.cl/appsenado/templates/tramitacion/index.php?boletin_ini={boletin}"


def disponivel() -> bool:
    """Serviço público chileno, sem chave/cadastro necessário — sempre True."""
    return True


def _casa(etiqueta: str | None) -> str:
    return _CASA_POR_ETIQUETA.get((etiqueta or "").strip().lower(), "camara")


def _data_iso(data_cl: str | None) -> str | None:
    """'30/10/2012' -> '2012-10-30'. Tolera formato inesperado sem levantar erro."""
    if not data_cl:
        return None
    try:
        return dt.datetime.strptime(data_cl.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _texto(el: ET.Element | None, tag: str) -> str | None:
    if el is None:
        return None
    filho = el.find(tag)
    return (filho.text or "").strip() if filho is not None and filho.text else None


def _parse_autores(proyecto: ET.Element) -> str:
    nomes = [
        (p.text or "").strip()
        for p in proyecto.findall("./autores/autor/PARLAMENTARIO")
        if p.text and p.text.strip()
    ]
    return ", ".join(nomes)


def _parse_proyecto(proyecto: ET.Element) -> dict[str, Any] | None:
    desc = proyecto.find("descripcion")
    if desc is None:
        return None
    boletin = _texto(desc, "boletin")
    if not boletin:
        return None

    tramites = proyecto.findall("./tramitacion/tramite")
    ultimo = tramites[-1] if tramites else None
    casa = _casa(_texto(ultimo, "CAMARATRAMITE") if ultimo is not None else _texto(desc, "camara_origen"))

    fecha_ingreso_iso = _data_iso(_texto(desc, "fecha_ingreso"))
    titulo = _texto(desc, "titulo") or ""
    iniciativa = _texto(desc, "iniciativa")  # "Mensaje" (Executivo) ou "Moción" (parlamentar)
    estado = _texto(desc, "estado")
    ementa = titulo
    detalhes = " · ".join(x for x in (iniciativa, estado) if x)
    if detalhes:
        ementa = f"{titulo}\n\n[{detalhes}]"

    return {
        "id_externo": boletin,
        "casa": casa,
        "sigla_tipo": "Boletín",
        "numero": boletin,
        "ano": int(fecha_ingreso_iso[:4]) if fecha_ingreso_iso else None,
        "ementa": ementa,
        "data_apresentacao": fecha_ingreso_iso,
        "autores": _parse_autores(proyecto),
        "url_origem": _URL_FICHA.format(boletin=boletin),
        "url_inteiro_teor": _texto(desc, "link_mensaje_mocion"),
        "ultima_tramitacao_data": _data_iso(_texto(ultimo, "FECHA")) if ultimo is not None else fecha_ingreso_iso,
        "ultima_tramitacao_descricao": _texto(ultimo, "DESCRIPCIONTRAMITE") if ultimo is not None else estado,
        "orgao_atual": _texto(desc, "subetapa") or _texto(desc, "etapa"),
    }


def listar_novas(dias: int) -> list[dict]:
    """
    Lista projetos de lei do Congresso chileno (ambas as casas) que tiveram
    qualquer movimento nos últimos `dias` dias, já no formato de registro
    usado por main.py/storage.py — pronto pra classificar e salvar, sem
    precisar de uma segunda chamada de detalhe (mesmo padrão do Senado
    brasileiro).

    `dias` é limitado a `_MAX_DIAS` (o serviço não aceita datas mais
    antigas que ~1 mês) — ver limitação no docstring do módulo.
    """
    dias_efetivo = min(dias, _MAX_DIAS)
    fecha = (dt.date.today() - dt.timedelta(days=dias_efetivo)).strftime("%d/%m/%Y")

    resp = requests.get(BASE_URL, params={"fecha": fecha}, timeout=_TIMEOUT)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    registros = []
    for proyecto in root.findall("proyecto"):
        registro = _parse_proyecto(proyecto)
        if registro:
            registros.append(registro)
    return registros
