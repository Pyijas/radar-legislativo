"""
Radar Legislativo — Saúde/Farma

Coleta projetos de lei federais recém apresentados/atualizados em três
fontes — Câmara dos Deputados, Senado Federal (Brasil) e Congresso dos EUA
(House + Senate) — e classifica cada um por impacto em saúde/farma em duas
camadas:

  1. Heurística por palavras-chave (PT ou EN) — sempre roda, 100% gratuita,
     determinística.
  2. IA (Anthropic ou Gemini) — roda por cima quando há chave configurada e
     sobrescreve a heurística com uma leitura mais precisa.

Uso:
    python main.py                      # últimos 7 dias, todas as fontes disponíveis
    python main.py --dias 15
    python main.py --fontes camara,senado   # só Brasil, sem tentar os EUA
    python main.py --tipos PL,PLP,MPV       # tipos de proposição (só afeta a Câmara)
    python main.py --export relatorio.csv
    python main.py --mostrar-todas      # inclui também os marcados como não relevantes
    python main.py --sem-navegador      # não abre o relatório HTML automaticamente
    python main.py --sem-ia             # força heurística mesmo com chave de IA (backfill)
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import camara_client, congress_client, heuristic_classify, paises, pdf_extract, publish, report, senado_client, storage
from src.classify import ClassificacaoIndisponivel, classificar

console = Console()

_NIVEL_RANK = {"alto": 0, "médio": 1, "baixo": 2, None: 3}
_URL_FICHA_CAMARA = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id}"
_RELATORIO_HTML = Path(__file__).resolve().parent / "data" / "relatorio.html"
_FONTES_PADRAO = ["camara", "senado", "eua"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Radar Legislativo — Saúde/Farma")
    p.add_argument("--dias", type=int, default=7, help="janela de dias a partir de hoje (padrão: 7)")
    p.add_argument("--tipos", type=str, default="PL,PLP",
                   help="tipos de proposição, separados por vírgula — só afeta a Câmara (padrão: PL,PLP)")
    p.add_argument("--fontes", type=str, default=",".join(_FONTES_PADRAO),
                   help="fontes a coletar, separadas por vírgula: camara, senado, eua (padrão: todas)")
    p.add_argument("--export", type=str, default=None, help="caminho de arquivo .csv para exportar o relatório")
    p.add_argument("--mostrar-todas", action="store_true",
                   help="inclui no relatório também os PLs marcados como não relevantes")
    p.add_argument("--sem-navegador", action="store_true",
                   help="não abre o relatório HTML automaticamente no navegador")
    p.add_argument("--sem-ia", action="store_true",
                   help="força classificação só por heurística, mesmo com chave de IA configurada "
                        "(use isso pra backfill de histórico grande, sem gastar cota de IA)")
    return p.parse_args()


def _coletar_camara(dias: int, tipos: list[str]) -> list[dict]:
    cod_tema = camara_client.find_cod_tema("Saúde")
    if cod_tema is None:
        console.print("[red]Câmara: não foi possível localizar o código do tema 'Saúde'.[/red]")
        return []

    with console.status("Buscando proposições na API da Câmara dos Deputados..."):
        proposicoes = camara_client.list_novas_proposicoes(dias, cod_tema, tipos)

    novas = [p for p in proposicoes if not storage.ja_processada("BR", "camara", p["id"])]
    console.print(f"Câmara: [bold]{len(proposicoes)}[/bold] proposições encontradas no período, "
                  f"[bold]{len(novas)}[/bold] ainda não processadas.")

    registros = []
    for p in novas:
        try:
            detalhe = camara_client.get_detalhe(p["id"])
            autores = camara_client.get_autores(p["id"])
            ementa = detalhe.get("ementa", "") or ""
            url_inteiro_teor = detalhe.get("urlInteiroTeor")
            texto = pdf_extract.extrair_texto(url_inteiro_teor)
            status = detalhe.get("statusProposicao") or {}

            registros.append({
                "pais": "BR", "casa": "camara", "idioma": "pt",
                "id_externo": str(p["id"]),
                "sigla_tipo": detalhe.get("siglaTipo", p.get("siglaTipo")),
                "numero": str(detalhe.get("numero", p.get("numero"))),
                "ano": detalhe.get("ano", p.get("ano")),
                "ementa": ementa,
                "texto_inteiro_teor": texto,
                "data_apresentacao": detalhe.get("dataApresentacao", p.get("dataApresentacao")),
                "autores": ", ".join(autores),
                "url_origem": _URL_FICHA_CAMARA.format(id=p["id"]),
                "url_inteiro_teor": url_inteiro_teor,
                "ultima_tramitacao_data": status.get("dataHora"),
                "ultima_tramitacao_descricao": status.get("descricaoSituacao") or status.get("descricaoTramitacao"),
                "orgao_atual": status.get("siglaOrgao"),
            })
        except Exception as exc:  # não deixa um item ruim derrubar a coleta inteira
            console.print(f"[red]Câmara: erro ao processar proposição {p.get('id')}:[/red] {exc}")
    return registros


def _coletar_senado(dias: int, tipos: list[str]) -> list[dict]:
    with console.status("Buscando matérias na API do Senado Federal..."):
        try:
            materias = senado_client.listar_novas(dias)
        except Exception as exc:
            console.print(f"[red]Senado: erro ao consultar a API:[/red] {exc}")
            return []

    novas = [m for m in materias if not storage.ja_processada("BR", "senado", m["id_externo"])]
    console.print(f"Senado: [bold]{len(materias)}[/bold] matérias encontradas no período, "
                  f"[bold]{len(novas)}[/bold] ainda não processadas.")

    registros = []
    for m in novas:
        try:
            texto = pdf_extract.extrair_texto(m.get("url_inteiro_teor"))
            registros.append({**m, "pais": "BR", "casa": "senado", "idioma": "pt", "texto_inteiro_teor": texto})
        except Exception as exc:
            console.print(f"[red]Senado: erro ao processar matéria {m.get('id_externo')}:[/red] {exc}")
    return registros


def _coletar_eua(dias: int, tipos: list[str]) -> list[dict]:
    if not congress_client.disponivel():
        console.print(
            "[yellow]ℹ️  CONGRESS_API_KEY não configurada — pulando a coleta dos EUA. "
            "Cadastre uma chave grátis em https://api.congress.gov/sign-up/ e configure "
            "no .env para ativar essa fonte.[/yellow]"
        )
        return []

    with console.status("Buscando projetos na API do Congresso dos EUA..."):
        try:
            itens = congress_client.listar_novas(dias)
        except Exception as exc:
            console.print(f"[red]EUA: erro ao consultar a API do Congresso:[/red] {exc}")
            return []

    novos = [it for it in itens
             if not storage.ja_processada("US", congress_client.casa_do_item(it), congress_client.id_externo_do_item(it))]
    console.print(f"EUA: [bold]{len(itens)}[/bold] projetos encontrados no período, "
                  f"[bold]{len(novos)}[/bold] ainda não processados.")

    registros = []
    for it in novos:
        try:
            registro = congress_client.get_detalhe(it)
            registro["pais"] = "US"
            registro["idioma"] = "en"
            registros.append(registro)
        except Exception as exc:
            console.print(f"[red]EUA: erro ao processar {it.get('type')}{it.get('number')}-{it.get('congress')}:[/red] {exc}")
    return registros


_COLETORES = {
    "camara": _coletar_camara,
    "senado": _coletar_senado,
    "eua": _coletar_eua,
}


def _classificar_e_salvar(registros: list[dict], tem_ia: bool) -> None:
    for registro in registros:
        idioma = registro.get("idioma", "pt")
        ementa = registro.get("ementa", "") or ""
        texto = registro.get("texto_inteiro_teor")

        # Camada 1: heurística por palavras-chave, sempre roda e nunca falha.
        c = heuristic_classify.classificar(ementa, texto, idioma=idioma)
        registro.update(ia_disponivel=0, fonte_classificacao="heuristica", **c)

        # Camada 2: IA por cima, se configurada — substitui a heurística quando funciona.
        if tem_ia:
            try:
                c_ia = classificar(ementa, texto)
                registro.update(
                    ia_disponivel=1,
                    fonte_classificacao="ia",
                    relevante=c_ia["relevante"],
                    justificativa_relevancia=c_ia["justificativa_relevancia"],
                    resumo=c_ia["resumo"],
                    areas_impactadas=c_ia["areas_impactadas"],
                    tipo_impacto=c_ia["tipo_impacto"],
                    abrangencia=c_ia["abrangencia"],
                    nivel_impacto=c_ia["nivel_impacto"],
                )
            except ClassificacaoIndisponivel as exc:
                console.print(f"[yellow]Aviso:[/yellow] falha ao classificar {registro.get('pais')}/"
                              f"{registro.get('casa')} {registro.get('id_externo')} por IA "
                              f"(mantendo classificação heurística): {exc}")

        storage.salvar(registro)


def coletar_e_classificar(dias: int, tipos: list[str], tem_ia: bool, fontes: list[str]) -> None:
    for fonte in fontes:
        coletor = _COLETORES.get(fonte)
        if not coletor:
            console.print(f"[red]Fonte desconhecida: '{fonte}' (use camara, senado ou eua)[/red]")
            continue
        registros = coletor(dias, tipos)
        if registros:
            _classificar_e_salvar(registros, tem_ia)


def montar_relatorio(mostrar_todas: bool) -> list:
    linhas = storage.listar_recentes(limite=5000)
    if not mostrar_todas:
        linhas = [l for l in linhas if l["relevante"] in (1, None)]
    linhas = sorted(linhas, key=lambda l: _NIVEL_RANK.get(l["nivel_impacto"], 3))
    return linhas


def imprimir_tabela(linhas: list) -> None:
    tabela = Table(title="Projetos de Lei — Saúde/Farma", show_lines=False)
    tabela.add_column("País/Casa")
    tabela.add_column("PL")
    tabela.add_column("Data")
    tabela.add_column("Ementa", max_width=40)
    tabela.add_column("Impacto")
    tabela.add_column("Áreas")

    for l in linhas:
        pais_info = paises.PAISES.get(l["pais"], {})
        casa_label = pais_info.get("casas", {}).get(l["casa"], l["casa"])
        pais_casa = f"{pais_info.get('bandeira', '')} {casa_label}"
        pl = f"{l['sigla_tipo']} {l['numero']}/{l['ano']}"
        ementa = (l["resumo"] or l["ementa"] or "")[:180]
        nivel = l["nivel_impacto"] or "—"
        cor = {"alto": "red", "médio": "yellow", "baixo": "green"}.get(nivel, "white")
        areas = l["areas_impactadas"] or ""
        tabela.add_row(pais_casa, pl, l["data_apresentacao"] or "", ementa, f"[{cor}]{nivel}[/{cor}]", areas)

    console.print(tabela)


def exportar_csv(linhas: list, caminho: str) -> None:
    campos = linhas[0].keys() if linhas else []
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for l in linhas:
            writer.writerow(dict(l))
    console.print(f"Relatório exportado para [bold]{caminho}[/bold]")


def main() -> None:
    load_dotenv()
    args = parse_args()
    tipos = [t.strip().upper() for t in args.tipos.split(",") if t.strip()]
    fontes = [f.strip().lower() for f in args.fontes.split(",") if f.strip()]

    tem_ia = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY")) and not args.sem_ia
    if args.sem_ia:
        console.print("[cyan]ℹ️  --sem-ia ativo — classificando só por palavras-chave, IA desligada nesta execução.[/cyan]\n")
    elif not tem_ia:
        console.print(
            "[yellow]ℹ️  Nenhuma chave de IA configurada — classificando só por palavras-chave "
            "(heurística gratuita). Configure ANTHROPIC_API_KEY ou GEMINI_API_KEY em .env para "
            "habilitar a classificação por IA.[/yellow]\n"
        )

    coletar_e_classificar(args.dias, tipos, tem_ia, fontes)
    linhas = montar_relatorio(args.mostrar_todas)

    if not linhas:
        console.print("Nenhum PL relevante encontrado no período (use --mostrar-todas para ver todos).")
        return

    imprimir_tabela(linhas)
    caminho_html = report.gerar_html(linhas, _RELATORIO_HTML)
    console.print(f"\nRelatório visual: [bold]{caminho_html}[/bold]")
    if not args.sem_navegador:
        webbrowser.open(caminho_html.as_uri())

    publicado, msg_publicacao = publish.publicar(caminho_html)
    cor_msg = "green" if publicado else "yellow"
    console.print(f"[{cor_msg}]{msg_publicacao}[/{cor_msg}]")

    if args.export:
        exportar_csv(linhas, args.export)


if __name__ == "__main__":
    main()
