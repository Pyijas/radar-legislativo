"""
Radar Legislativo — Saúde/Farma

Coleta projetos de lei federais (Câmara dos Deputados) recém apresentados sob o
tema Saúde. Classifica cada um por impacto em saúde/farma em duas camadas:

  1. Heurística por palavras-chave — sempre roda, 100% gratuita, determinística.
  2. IA (Anthropic ou Gemini) — roda por cima quando há chave configurada e
     sobrescreve a heurística com uma leitura mais precisa.

Uso:
    python main.py                      # últimos 7 dias, tipos PL e PLP
    python main.py --dias 15
    python main.py --tipos PL,PLP,MPV
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
from src import camara_client, heuristic_classify, pdf_extract, report, storage
from src.classify import ClassificacaoIndisponivel, classificar

console = Console()

_NIVEL_RANK = {"alto": 0, "médio": 1, "baixo": 2, None: 3}
_URL_FICHA = "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={id}"
_RELATORIO_HTML = Path(__file__).resolve().parent / "data" / "relatorio.html"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Radar Legislativo — Saúde/Farma")
    p.add_argument("--dias", type=int, default=7, help="janela de dias a partir de hoje (padrão: 7)")
    p.add_argument("--tipos", type=str, default="PL,PLP",
                   help="tipos de proposição, separados por vírgula (padrão: PL,PLP)")
    p.add_argument("--export", type=str, default=None, help="caminho de arquivo .csv para exportar o relatório")
    p.add_argument("--mostrar-todas", action="store_true",
                   help="inclui no relatório também os PLs marcados como não relevantes")
    p.add_argument("--sem-navegador", action="store_true",
                   help="não abre o relatório HTML automaticamente no navegador")
    p.add_argument("--sem-ia", action="store_true",
                   help="força classificação só por heurística, mesmo com chave de IA configurada "
                        "(use isso pra backfill de histórico grande, sem gastar cota de IA)")
    return p.parse_args()


def coletar_e_classificar(dias: int, tipos: list[str], tem_ia: bool) -> None:
    cod_tema = camara_client.find_cod_tema("Saúde")
    if cod_tema is None:
        console.print("[red]Não foi possível localizar o código do tema 'Saúde' na API da Câmara.[/red]")
        sys.exit(1)

    with console.status("Buscando proposições na API da Câmara dos Deputados..."):
        proposicoes = camara_client.list_novas_proposicoes(dias, cod_tema, tipos)

    novas = [p for p in proposicoes if not storage.ja_processada(p["id"])]
    console.print(f"[bold]{len(proposicoes)}[/bold] proposições encontradas no período, "
                  f"[bold]{len(novas)}[/bold] ainda não processadas.")

    for p in novas:
        try:
            detalhe = camara_client.get_detalhe(p["id"])
            autores = camara_client.get_autores(p["id"])
            ementa = detalhe.get("ementa", "") or ""
            url_inteiro_teor = detalhe.get("urlInteiroTeor")
            texto = pdf_extract.extrair_texto(url_inteiro_teor)

            registro = {
                "id": p["id"],
                "sigla_tipo": detalhe.get("siglaTipo", p.get("siglaTipo")),
                "numero": detalhe.get("numero", p.get("numero")),
                "ano": detalhe.get("ano", p.get("ano")),
                "ementa": ementa,
                "data_apresentacao": detalhe.get("dataApresentacao", p.get("dataApresentacao")),
                "autores": ", ".join(autores),
                "url_camara": _URL_FICHA.format(id=p["id"]),
                "url_inteiro_teor": url_inteiro_teor,
            }

            # Camada 1: heurística por palavras-chave, sempre roda e nunca falha.
            c = heuristic_classify.classificar(ementa, texto)
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
                    console.print(f"[yellow]Aviso:[/yellow] falha ao classificar PL {p['id']} por IA "
                                  f"(mantendo classificação heurística): {exc}")

            storage.salvar(registro)
        except Exception as exc:  # não deixa um item ruim derrubar a coleta inteira
            console.print(f"[red]Erro ao processar proposição {p.get('id')}:[/red] {exc}")


def montar_relatorio(mostrar_todas: bool) -> list:
    linhas = storage.listar_recentes(limite=5000)
    if not mostrar_todas:
        linhas = [l for l in linhas if l["relevante"] in (1, None)]
    linhas = sorted(linhas, key=lambda l: _NIVEL_RANK.get(l["nivel_impacto"], 3))
    return linhas


def imprimir_tabela(linhas: list) -> None:
    tabela = Table(title="Projetos de Lei — Saúde/Farma", show_lines=False)
    tabela.add_column("PL")
    tabela.add_column("Data")
    tabela.add_column("Ementa", max_width=45)
    tabela.add_column("Impacto")
    tabela.add_column("Áreas")
    tabela.add_column("Origem")

    for l in linhas:
        pl = f"{l['sigla_tipo']} {l['numero']}/{l['ano']}"
        ementa = (l["resumo"] or l["ementa"] or "")[:180]
        nivel = l["nivel_impacto"] or "—"
        cor = {"alto": "red", "médio": "yellow", "baixo": "green"}.get(nivel, "white")
        areas = l["areas_impactadas"] or ""
        origem = "IA" if l["fonte_classificacao"] == "ia" else "heurística"
        tabela.add_row(pl, l["data_apresentacao"] or "", ementa, f"[{cor}]{nivel}[/{cor}]", areas, origem)

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

    tem_ia = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY")) and not args.sem_ia
    if args.sem_ia:
        console.print("[cyan]ℹ️  --sem-ia ativo — classificando só por palavras-chave, IA desligada nesta execução.[/cyan]\n")
    elif not tem_ia:
        console.print(
            "[yellow]ℹ️  Nenhuma chave de IA configurada — classificando só por palavras-chave "
            "(heurística gratuita). Configure ANTHROPIC_API_KEY ou GEMINI_API_KEY em .env para "
            "habilitar a classificação por IA.[/yellow]\n"
        )

    coletar_e_classificar(args.dias, tipos, tem_ia)
    linhas = montar_relatorio(args.mostrar_todas)

    if not linhas:
        console.print("Nenhum PL relevante encontrado no período (use --mostrar-todas para ver todos).")
        return

    imprimir_tabela(linhas)
    caminho_html = report.gerar_html(linhas, _RELATORIO_HTML)
    console.print(f"\nRelatório visual: [bold]{caminho_html}[/bold]")
    if not args.sem_navegador:
        webbrowser.open(caminho_html.as_uri())

    if args.export:
        exportar_csv(linhas, args.export)


if __name__ == "__main__":
    main()
