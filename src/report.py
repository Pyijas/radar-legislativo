"""
Geração do painel HTML — quatro páginas estáticas compartilhando os mesmos
dados via dados.js e a mesma lógica de card/modal:

  index.html     hub: escolha de país (com contagem de PLs e destaque pro
                 mais relevante no momento), mais os países pesquisados mas
                 ainda não implementados, como "em breve".
  pais.html      dashboard completo de um país (?p=BR, ?p=US, ...), com
                 filtro por casa legislativa quando o país tem mais de uma
                 (Câmara/Senado no Brasil, House/Senate nos EUA).
  noticias.html  monitoramento institucional do Brasil: notícias da Anvisa/
                 Ministério da Saúde/ANS + agenda pública do Presidente.
  salvos.html    só os PLs marcados pelo usuário, de qualquer país/casa.

O HTML/CSS/JS de verdade vive em arquivos próprios dentro de frontend/ (na
raiz do projeto) — este módulo NÃO tem CSS/JS embutido em strings Python.
Ele só faz duas coisas: (1) converte as linhas do banco pro JSON consumido
pelo JS (dados.js) e (2) monta a casca de cada página substituindo um
punhado de placeholders ($TITULO, $CORPO, ...) nos templates de frontend/
via string.Template — sem nenhuma lógica de apresentação aqui.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from string import Template

from src import paises

REPO_URL = "https://github.com/Pyijas/radar-legislativo"

_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
_ARQUIVOS_ESTATICOS = [
    "estilos.css", "helpers.js", "item-modal.js",
    "brasil.js", "noticias.js", "agenda.js", "salvos.js",
]
_CHART_CDN_TPL = '<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>\n'

# --- Escopo do painel -------------------------------------------------------
# Em 18/09/2026 o usuário pediu pra deixar só o Brasil no ar ("retira tudo dos
# outros países por enquanto, deixa off"). A coleta e a classificação de EUA,
# Chile e das agências reguladoras latino-americanas continuam implementadas e
# funcionando (ver main.py) — o que muda é só o que sai daqui pro dados.js.
# Pra religar: acrescente os códigos/fontes nos dois conjuntos abaixo — a
# página do país e a seção da América Latina saíram do frontend, então voltar
# ao modo multi-país pede também restaurar frontend/hub.* do histórico do git.
_PAISES_ATIVOS = {"BR"}
_FONTES_NOTICIA_ATIVAS = {"anvisa", "saude", "ans"}


def _parse_lista(valor):
    if not valor:
        return []
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except (TypeError, json.JSONDecodeError):
            return [valor]
    return list(valor)


def _rotulo_pl(l: dict) -> str:
    if l["pais"] == "US":
        # aqui "ano" guarda o número do Congresso (ex: 119), não um ano-calendário
        return f"{l['sigla_tipo']} {l['numero']} ({l['ano']}º Congresso)"
    if l["pais"] == "CL":
        # "numero" já é o boletim completo (ex: "8654-15"), sem separação por ano
        return f"{l['sigla_tipo']} {l['numero']}"
    return f"{l['sigla_tipo']} {l['numero']}/{l['ano']}"


def _linha_para_dado(l: dict) -> dict:
    """Converte uma linha do SQLite pro formato compacto consumido pelo JS do relatório."""
    pais_info = paises.PAISES.get(l["pais"], {})
    casa_label = pais_info.get("casas", {}).get(l["casa"], l["casa"])
    return {
        "id": l["chave"],
        "pais": l["pais"],
        "casa": l["casa"],
        "casaLabel": casa_label,
        "pl": _rotulo_pl(l),
        "data": (l["data_apresentacao"] or "")[:10],
        "url": l["url_origem"] or "",
        "ementa": l["ementa"] or "",
        "resumo": l["resumo"] or l["ementa"] or "",
        "justificativa": l["justificativa_relevancia"] or "",
        "nivel": l["nivel_impacto"],
        "abrangencia": l["abrangencia"] or "",
        "areas": _parse_lista(l["areas_impactadas"]),
        "tipos": _parse_lista(l["tipo_impacto"]),
        "fonte": l["fonte_classificacao"],
        "autores": l["autores"] or "",
        "tramitacaoData": (l["ultima_tramitacao_data"] or "")[:10],
        "tramitacaoDesc": l["ultima_tramitacao_descricao"] or "",
        "orgao": l["orgao_atual"] or "",
    }


_FONTE_NOTICIA_LABEL = {
    "anvisa": "Anvisa",
    "saude": "Ministério da Saúde",
    "ans": "ANS",
    # Agências reguladoras da América Latina — coletadas e classificadas, mas
    # fora do painel por ora (ver _FONTES_NOTICIA_ATIVAS).
    "anmat": "ANMAT · Argentina",
    "digemid": "DIGEMID · Peru",
    "isp_cl": "ISP · Chile",
    "minsalud_bo": "AGEMED · Bolívia",
    "msp_uy": "MSP · Uruguai",
}


def _linha_noticia_para_dado(n: dict) -> dict:
    """Mesma ideia de _linha_para_dado(), mas pra notícias institucionais
    (Anvisa/Ministério da Saúde/ANS — ver src/anvisa_news_client.py e
    afins). Formato mais simples que o de PL: não tem casa/tramitação."""
    return {
        "id": n["chave"],
        "fonte": n["fonte"],
        "fonteLabel": _FONTE_NOTICIA_LABEL.get(n["fonte"], n["fonte"]),
        "titulo": n["titulo"] or "",
        "resumo": n["resumo_ia"] or n["resumo"] or n["titulo"] or "",
        "justificativa": n["justificativa_relevancia"] or "",
        "nivel": n["nivel_impacto"],
        "areas": _parse_lista(n["areas_impactadas"]),
        "tipos": _parse_lista(n["tipo_impacto"]),
        "fonteClassificacao": n["fonte_classificacao"],
        "data": (n["data_publicacao"] or "")[:10],
        "url": n["url_origem"] or "",
    }


def _linha_evento_para_dado(e: dict) -> dict:
    """Mesma ideia, pra eventos de agenda pública de autoridades (ver
    src/agenda_presidente_client.py)."""
    return {
        "id": e["chave"],
        "autoridade": e["autoridade"] or "",
        "cargo": e["cargo"] or "",
        "titulo": e["titulo"] or "",
        "local": e["local"] or "",
        "resumo": e["resumo_ia"] or e["titulo"] or "",
        "justificativa": e["justificativa_relevancia"] or "",
        "nivel": e["nivel_impacto"],
        "areas": _parse_lista(e["areas_impactadas"]),
        "tipos": _parse_lista(e["tipo_impacto"]),
        "fonteClassificacao": e["fonte_classificacao"],
        "data": e["data"] or "",
        "horario": e["horario"] or "",
        "url": e["url_origem"] or "",
    }


def _copiar_estaticos(destino: Path) -> None:
    """Copia CSS/JS de frontend/ pra pasta de saída (data/ ou docs/). São
    arquivos estáticos — não têm nada gerado por linha do banco — só
    precisam estar ao lado do HTML pra funcionar, então isso é uma cópia
    simples, não uma "geração"."""
    for nome in _ARQUIVOS_ESTATICOS:
        shutil.copy(_FRONTEND / nome, destino / nome)


def _pagina(nome_corpo: str, *, titulo: str, subtitulo: str, topbar_extra: str,
            script_pagina: str, scripts_antes: str = "", versao: str = "0") -> str:
    """Monta uma página a partir de frontend/_base.html (a casca: topbar,
    container, modal, footer, scripts) + frontend/<nome_corpo>.body.html (o
    conteúdo específico daquela página), substituindo os placeholders $X —
    sem nenhum CSS/JS embutido aqui, só referências <link>/<script src>
    pros arquivos de frontend/ (copiados ao lado pelo _copiar_estaticos)."""
    corpo_tpl = Template((_FRONTEND / f"{nome_corpo}.body.html").read_text(encoding="utf-8"))
    corpo_html = corpo_tpl.safe_substitute(REPO_URL=REPO_URL)

    modal_html = (_FRONTEND / "_modal.html").read_text(encoding="utf-8")

    base_tpl = Template((_FRONTEND / "_base.html").read_text(encoding="utf-8"))
    return base_tpl.substitute(
        TITULO=titulo, SUBTITULO=subtitulo, TOPBAR_EXTRA=topbar_extra,
        CORPO=corpo_html, MODAL_HTML=modal_html, REPO_URL=REPO_URL,
        SCRIPTS_ANTES=scripts_antes, SCRIPT_PAGINA=script_pagina, VERSAO=versao,
    )


def _script_tag(nome: str, versao: str) -> str:
    return f'<script src="{nome}?v={versao}"></script>\n'


def _ico(nome: str) -> str:
    """Ícone do sprite SVG definido em frontend/_base.html. O painel não usa
    emoji em lugar nenhum — ver comentário no topo de frontend/estilos.css."""
    return f'<svg class="ico"><use href="#ico-{nome}"/></svg>'


def _link_salvos(ativo: bool = False) -> str:
    classe = ' class="is-active"' if ativo else ""
    return (
        f'<a href="salvos.html"{classe}>' + _ico("estrela") +
        '<span>Salvas</span><span class="contador-salvos">0</span></a>'
    )


def _nav(atual: str) -> str:
    """Menu das quatro páginas, marcando a atual. `atual` é a chave do corpo
    (brasil, noticias, agenda, salvos)."""
    itens = [
        ("brasil", "index.html", "doc", "Proposições"),
        ("noticias", "noticias.html", "radar", "Atos"),
        ("agenda", "agenda.html", "calendario", "Agenda"),
    ]
    partes = []
    for chave, href, icone, rotulo in itens:
        classe = ' class="is-active"' if chave == atual else ""
        partes.append(f'<a href="{href}"{classe}>{_ico(icone)}<span>{rotulo}</span></a>')
    partes.append(_link_salvos(atual == "salvos"))
    return "".join(partes)


def gerar_html(linhas: list, caminho: str | Path, noticias: list | None = None,
                eventos_agenda: list | None = None) -> Path:
    """Gera as três páginas do painel — dashboard do Brasil em `caminho`
    (index.html), noticias.html e salvos.html ao lado — e copia os arquivos
    estáticos de frontend/ pra junto delas. Retorna o caminho do index, que é
    o que main.py abre no navegador e publish.py copia como entrada do site.

    Só o Brasil entra no painel (ver _PAISES_ATIVOS/_FONTES_NOTICIA_ATIVAS):
    as linhas de EUA/Chile e das agências latino-americanas são filtradas
    aqui, não na consulta — assim continuam no banco, prontas pra voltar."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    _copiar_estaticos(caminho.parent)

    dados = [_linha_para_dado(l) for l in linhas if l["pais"] in _PAISES_ATIVOS]
    dados_noticias = [
        _linha_noticia_para_dado(n) for n in (noticias or [])
        if n["fonte"] in _FONTES_NOTICIA_ATIVAS
    ]
    dados_agenda = [_linha_evento_para_dado(e) for e in (eventos_agenda or [])]
    dados_json = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    noticias_json = json.dumps(dados_noticias, ensure_ascii=False).replace("</", "<\\/")
    agenda_json = json.dumps(dados_agenda, ensure_ascii=False).replace("</", "<\\/")
    (caminho.parent / "dados.js").write_text(
        f"window.RADAR_DADOS = {dados_json};\n"
        f"window.RADAR_NOTICIAS = {noticias_json};\n"
        f"window.RADAR_AGENDA = {agenda_json};\n",
        encoding="utf-8",
    )

    agora = datetime.now()
    gerado_em = agora.strftime("%d/%m/%Y, %H:%M")
    # Cache-busting pros arquivos estáticos (dados.js muda toda geração; os
    # demais raramente, mas custa nada versionar todos junto): sem isso, o
    # navegador pode continuar servindo uma cópia antiga até um hard-refresh.
    versao = agora.strftime("%Y%m%d%H%M%S")

    _gerar_brasil_html(caminho, gerado_em, versao)
    _gerar_noticias_html(caminho.parent / "noticias.html", gerado_em, versao)
    _gerar_agenda_html(caminho.parent / "agenda.html", gerado_em, versao)
    _gerar_salvos_html(caminho.parent / "salvos.html", versao)
    return caminho


def _gerar_brasil_html(caminho: Path, gerado_em: str, versao: str) -> Path:
    """Dashboard de proposições do Brasil — é a página inicial desde
    18/09/2026 (antes o index era um hub de escolha de país)."""
    topbar = f'<span class="live"><span class="pulse"></span>{gerado_em}</span>' + _nav("brasil")
    scripts_antes = (
        _CHART_CDN_TPL
        + _script_tag("helpers.js", versao)
        + _script_tag("item-modal.js", versao)
    )
    doc = _pagina(
        "brasil", titulo="Radar Legislativo — Saúde e Farma",
        subtitulo="Brasil", topbar_extra=topbar, script_pagina="brasil.js",
        scripts_antes=scripts_antes, versao=versao,
    )
    caminho.write_text(doc, encoding="utf-8")
    return caminho


def _gerar_noticias_html(caminho: Path, gerado_em: str, versao: str) -> Path:
    """Atos e publicações da Anvisa, do Ministério da Saúde e da ANS. A
    agenda das autoridades saiu daqui em 18/09/2026 — ver
    _gerar_agenda_html()."""
    topbar = f'<span class="live"><span class="pulse"></span>{gerado_em}</span>' + _nav("noticias")
    doc = _pagina(
        "noticias", titulo="Atos e publicações — Radar Legislativo",
        subtitulo="Reguladores", topbar_extra=topbar, script_pagina="noticias.js",
        scripts_antes=_script_tag("helpers.js", versao), versao=versao,
    )
    caminho.write_text(doc, encoding="utf-8")
    return caminho


def _gerar_agenda_html(caminho: Path, gerado_em: str, versao: str) -> Path:
    """Agenda pública das autoridades em página própria, com calendário de
    seleção de dias — pedido do usuário em 18/09/2026: dentro da lista de
    notícias ela confundia, porque agenda se navega por data."""
    topbar = f'<span class="live"><span class="pulse"></span>{gerado_em}</span>' + _nav("agenda")
    doc = _pagina(
        "agenda", titulo="Agenda das autoridades — Radar Legislativo",
        subtitulo="Compromissos", topbar_extra=topbar, script_pagina="agenda.js",
        scripts_antes=_script_tag("helpers.js", versao), versao=versao,
    )
    caminho.write_text(doc, encoding="utf-8")
    return caminho


def _gerar_salvos_html(caminho: Path, versao: str = "0") -> Path:
    topbar = _nav("salvos")
    scripts_antes = _script_tag("helpers.js", versao) + _script_tag("item-modal.js", versao)
    doc = _pagina(
        "salvos", titulo="Salvas — Radar Legislativo", subtitulo="Sua seleção",
        topbar_extra=topbar, script_pagina="salvos.js",
        scripts_antes=scripts_antes, versao=versao,
    )
    caminho.write_text(doc, encoding="utf-8")
    return caminho
