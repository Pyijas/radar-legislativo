"""
Geração do relatório HTML — um painel interativo autocontido (HTML+CSS+JS,
com Chart.js via CDN para os gráficos), com busca, filtros, estatísticas e
tendência ao longo do ano em cima dos dados salvos no SQLite.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def _parse_lista(valor):
    if not valor:
        return []
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except (TypeError, json.JSONDecodeError):
            return [valor]
    return list(valor)


def _linha_para_dado(l: dict) -> dict:
    """Converte uma linha do SQLite pro formato compacto consumido pelo JS do relatório."""
    return {
        "id": l["id"],
        "pl": f"{l['sigla_tipo']} {l['numero']}/{l['ano']}",
        "data": (l["data_apresentacao"] or "")[:10],
        "url": l["url_camara"] or "",
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


def gerar_html(linhas: list, caminho: str | Path) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    dados = [_linha_para_dado(l) for l in linhas]
    # Evita que um "</script>" dentro de algum texto feche a tag prematuramente.
    dados_json = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    gerado_em = datetime.now().strftime("%d/%m/%Y às %H:%M")

    doc = f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar Legislativo — Saúde/Farma</title>
<meta name="description" content="Monitoramento automático de projetos de lei federais com impacto no setor de saúde e farmacêutico, classificados por IA.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f5f6f8; --bg-soft: #eef0f3; --card: #ffffff; --border: #e4e6ea;
    --text: #14181f; --muted: #6b7280; --muted-2: #9aa1ab;
    --accent: #2563eb; --accent-soft: #eaf0fe;
    --chip-bg: #f1f3f6; --chip-text: #3a4150;
    --alto: #dc2626; --alto-soft: #fdecec; --medio: #d97706; --medio-soft: #fef3e2;
    --baixo: #16a34a; --baixo-soft: #eafaf0; --sem: #8b93a1;
    --ia: #2563eb; --heur: #7c3aed;
    --shadow: 0 1px 2px rgba(20,24,31,.04), 0 8px 24px -12px rgba(20,24,31,.10);
    --radius: 16px;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0d0f13; --bg-soft: #14171d; --card: #171a21; --border: #262b34;
      --text: #eef0f3; --muted: #9aa1ab; --muted-2: #6b7280;
      --accent: #5b8bf7; --accent-soft: #172242;
      --chip-bg: #1f2430; --chip-text: #c3c9d4;
      --alto-soft: #2a1518; --medio-soft: #2a2013; --baixo-soft: #12261a;
      --shadow: 0 1px 2px rgba(0,0,0,.3), 0 12px 28px -14px rgba(0,0,0,.6);
    }}
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    font-family: 'Inter', -apple-system, "Segoe UI", Roboto, sans-serif;
    margin: 0; background: var(--bg); color: var(--text);
    -webkit-font-smoothing: antialiased;
  }}
  a {{ color: inherit; }}

  /* ---------- topbar ---------- */
  .topbar {{
    position: sticky; top: 0; z-index: 20;
    display: flex; align-items: center; justify-content: space-between;
    gap: 1rem; padding: 0.9rem 1.75rem;
    background: color-mix(in srgb, var(--card) 88%, transparent);
    backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
  }}
  .brand {{ display: flex; align-items: center; gap: 0.65rem; }}
  .brand .dot {{ width: 10px; height: 10px; border-radius: 50%; background: var(--accent);
                 box-shadow: 0 0 0 4px var(--accent-soft); flex: none; }}
  .brand h1 {{ font-size: 1.05rem; font-weight: 700; margin: 0; letter-spacing: -0.01em; }}
  .brand .sub {{ font-size: 0.76rem; color: var(--muted); margin-top: 0.1rem; }}
  .topbar-right {{ display: flex; align-items: center; gap: 0.9rem; font-size: 0.78rem; color: var(--muted); }}
  .topbar-right a {{ display: inline-flex; align-items: center; gap: 0.35rem; text-decoration: none;
                      padding: 0.4rem 0.7rem; border-radius: 999px; border: 1px solid var(--border);
                      transition: background .15s, border-color .15s; }}
  .topbar-right a:hover {{ background: var(--chip-bg); border-color: var(--muted-2); }}
  .live {{ display: inline-flex; align-items: center; gap: 0.4rem; }}
  .live .pulse {{ width: 7px; height: 7px; border-radius: 50%; background: var(--baixo);
                  animation: pulse 2s ease-in-out infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: .45; transform: scale(1.3); }} }}

  .container {{ max-width: 1180px; margin: 0 auto; padding: 1.75rem; }}

  @keyframes rise {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  .rise {{ animation: rise .5s cubic-bezier(.16,1,.3,1) both; }}

  /* ---------- KPI cards ---------- */
  .kpis {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 0.8rem; margin-bottom: 1.4rem; }}
  .kpi {{ background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
          padding: 1rem 1.1rem; box-shadow: var(--shadow); position: relative; overflow: hidden; }}
  .kpi::before {{ content: ""; position: absolute; inset: 0 auto 0 0; width: 3px; background: var(--bar, var(--accent)); }}
  .kpi .n {{ font-size: 1.65rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; font-variant-numeric: tabular-nums; }}
  .kpi .l {{ font-size: 0.72rem; color: var(--muted); margin-top: 0.3rem; font-weight: 600;
             text-transform: uppercase; letter-spacing: 0.04em; }}
  .kpi.alto {{ --bar: var(--alto); }} .kpi.alto .n {{ color: var(--alto); }}
  .kpi.medio {{ --bar: var(--medio); }} .kpi.medio .n {{ color: var(--medio); }}
  .kpi.baixo {{ --bar: var(--baixo); }} .kpi.baixo .n {{ color: var(--baixo); }}
  .kpi.ia {{ --bar: var(--ia); }} .kpi.heur {{ --bar: var(--heur); }}

  /* ---------- charts ---------- */
  .charts {{ display: grid; grid-template-columns: 1.1fr 1.4fr 1.4fr; gap: 0.9rem; margin-bottom: 1.4rem; }}
  .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
            padding: 1.1rem 1.2rem; box-shadow: var(--shadow); }}
  .panel h2 {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted);
               margin: 0 0 0.8rem; font-weight: 700; }}
  .panel .chart-wrap {{ position: relative; height: 190px; }}

  /* ---------- filtros ---------- */
  .toolbar {{ display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; margin-bottom: 0.9rem; }}
  .search {{ position: relative; flex: 1; min-width: 220px; }}
  .search svg {{ position: absolute; left: 0.75rem; top: 50%; transform: translateY(-50%); opacity: 0.45; pointer-events: none; }}
  .search input {{ width: 100%; padding: 0.6rem 0.8rem 0.6rem 2.15rem; border-radius: 10px;
                    border: 1px solid var(--border); background: var(--card); color: var(--text); font-size: 0.88rem;
                    font-family: inherit; transition: border-color .15s, box-shadow .15s; }}
  .search input:focus {{ outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }}
  .segmented {{ display: inline-flex; background: var(--chip-bg); border-radius: 10px; padding: 3px; gap: 2px; }}
  .segmented button {{ border: none; background: transparent; color: var(--muted); font-size: 0.82rem; font-weight: 600;
                        padding: 0.42rem 0.75rem; border-radius: 8px; cursor: pointer; font-family: inherit;
                        transition: background .15s, color .15s; white-space: nowrap; }}
  .segmented button:hover {{ color: var(--text); }}
  .segmented button.active {{ background: var(--card); color: var(--text); box-shadow: var(--shadow); }}
  select.pill {{ padding: 0.55rem 0.8rem; border-radius: 10px; border: 1px solid var(--border);
                 background: var(--card); color: var(--text); font-size: 0.83rem; font-family: inherit; cursor: pointer; }}
  .clear-btn {{ border: 1px solid var(--border); background: var(--card); color: var(--muted); font-size: 0.82rem;
                padding: 0.55rem 0.85rem; border-radius: 10px; cursor: pointer; font-family: inherit; font-weight: 600;
                transition: color .15s, border-color .15s; }}
  .clear-btn:hover {{ color: var(--text); border-color: var(--muted-2); }}
  .contagem {{ font-size: 0.8rem; color: var(--muted); margin: 0.2rem 0 0.9rem; }}
  .contagem b {{ color: var(--text); }}

  /* ---------- lista de cards ---------- */
  #corpo {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 0.65rem; align-items: start; }}
  .item {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px;
           padding: 1rem 1.15rem; box-shadow: var(--shadow); transition: border-color .15s, transform .15s, box-shadow .15s;
           cursor: pointer; display: flex; flex-direction: column; }}
  .item:hover {{ border-color: var(--accent); transform: translateY(-2px);
                 box-shadow: 0 1px 2px rgba(20,24,31,.04), 0 14px 28px -14px color-mix(in srgb, var(--accent) 35%, transparent); }}
  .item-head {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 0.8rem; margin-bottom: 0.5rem; }}
  .item-title {{ display: flex; align-items: baseline; gap: 0.6rem; flex-wrap: wrap; }}
  .item-title a {{ font-weight: 700; text-decoration: none; font-size: 0.95rem; }}
  .item-title a:hover {{ text-decoration: underline; }}
  .item-title .data {{ font-size: 0.74rem; color: var(--muted-2); font-variant-numeric: tabular-nums; }}
  .item-meta {{ display: flex; flex-wrap: wrap; gap: 0.15rem 0.9rem; font-size: 0.73rem; color: var(--muted);
                margin-bottom: 0.55rem; font-variant-numeric: tabular-nums; }}
  .item-meta span {{ cursor: default; }}
  .badge {{ display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.2rem 0.65rem; border-radius: 999px;
            font-size: 0.72rem; font-weight: 700; white-space: nowrap; flex: none; }}
  .badge::before {{ content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }}
  .badge.alto {{ background: var(--alto-soft); color: var(--alto); }}
  .badge.médio {{ background: var(--medio-soft); color: var(--medio); }}
  .badge.baixo {{ background: var(--baixo-soft); color: var(--baixo); }}
  .badge.sem {{ background: var(--chip-bg); color: var(--sem); }}
  .resumo {{ font-size: 0.86rem; line-height: 1.5; color: var(--text); margin: 0 0 0.65rem; }}
  .resumo.clamp {{ display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
  .item-foot {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 0.35rem; }}
  .tag {{ font-size: 0.71rem; font-weight: 600; padding: 0.18rem 0.55rem; border-radius: 7px; cursor: pointer;
          background: var(--chip-bg); color: var(--chip-text); border: 1px solid transparent; transition: opacity .15s; }}
  .tag:hover {{ opacity: 0.72; }}
  .fonte {{ font-size: 0.71rem; font-weight: 700; display: inline-flex; align-items: center; gap: 0.3rem; }}
  .fonte::before {{ content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }}
  .fonte.ia {{ color: var(--ia); }} .fonte.heuristica {{ color: var(--heur); }}
  .toggle-hint {{ font-size: 0.7rem; color: var(--muted-2); cursor: pointer; user-select: none; }}

  .rodape-lista {{ display: flex; justify-content: center; margin: 1.3rem 0; }}
  .rodape-lista button {{ padding: 0.65rem 1.6rem; border-radius: 999px; border: 1px solid var(--border);
                     background: var(--card); color: var(--text); cursor: pointer; font-size: 0.85rem; font-weight: 600;
                     font-family: inherit; box-shadow: var(--shadow); transition: border-color .15s; }}
  .rodape-lista button:hover {{ border-color: var(--accent); color: var(--accent); }}
  .vazio {{ text-align: center; color: var(--muted); padding: 3rem 1rem; font-size: 0.9rem; grid-column: 1 / -1; }}

  /* ---------- modal de detalhe ---------- */
  .modal-backdrop {{ position: fixed; inset: 0; background: rgba(8,10,14,.55); backdrop-filter: blur(2px);
                      display: flex; align-items: flex-start; justify-content: center; padding: 4vh 1.25rem;
                      overflow-y: auto; z-index: 100; opacity: 0; pointer-events: none; transition: opacity .16s; }}
  .modal-backdrop.open {{ opacity: 1; pointer-events: auto; }}
  .modal {{ background: var(--card); border: 1px solid var(--border); border-radius: 20px; width: 100%; max-width: 640px;
            padding: 1.6rem 1.7rem 1.8rem; box-shadow: 0 30px 70px -24px rgba(0,0,0,.45);
            transform: translateY(14px) scale(.97); transition: transform .18s cubic-bezier(.16,1,.3,1); }}
  .modal-backdrop.open .modal {{ transform: translateY(0) scale(1); }}
  .modal-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 0.8rem; }}
  .modal-close {{ border: none; background: var(--chip-bg); color: var(--muted); width: 32px; height: 32px;
                  border-radius: 50%; cursor: pointer; font-size: 1rem; line-height: 1; flex: none;
                  transition: background .15s, color .15s; }}
  .modal-close:hover {{ background: var(--border); color: var(--text); }}
  .modal h2 {{ margin: 0.7rem 0 0; font-size: 1.2rem; letter-spacing: -0.01em; }}
  .modal h2 a {{ text-decoration: none; }}
  .modal h2 a:hover {{ text-decoration: underline; }}
  .modal-resumo {{ font-size: 0.92rem; line-height: 1.6; margin: 0.9rem 0; }}
  .modal-just {{ font-size: 0.82rem; color: var(--muted); background: var(--chip-bg); padding: 0.65rem 0.85rem;
                 border-radius: 10px; margin: 0.9rem 0; line-height: 1.5; }}
  .modal-section {{ margin: 1.1rem 0; }}
  .modal-section h4 {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted);
                        margin: 0 0 0.5rem; font-weight: 700; }}
  .modal-section p {{ margin: 0; font-size: 0.87rem; line-height: 1.5; color: var(--text); }}
  body.modal-open {{ overflow: hidden; }}

  footer {{ text-align: center; padding: 2rem 1rem 3rem; color: var(--muted-2); font-size: 0.76rem; }}
  footer a {{ color: var(--muted); text-decoration: underline; }}

  @media (max-width: 980px) {{
    .kpis {{ grid-template-columns: repeat(3, 1fr); }}
    .charts {{ grid-template-columns: 1fr; }}
  }}
  @media (max-width: 620px) {{
    .kpis {{ grid-template-columns: repeat(2, 1fr); }}
    .topbar {{ padding: 0.8rem 1rem; }}
    .container {{ padding: 1.1rem; }}
  }}
</style>
</head>
<body>
  <div class="topbar">
    <div class="brand">
      <span class="dot"></span>
      <div>
        <h1>Radar Legislativo</h1>
        <div class="sub">Saúde &amp; Farma no Congresso Nacional</div>
      </div>
    </div>
    <div class="topbar-right">
      <span class="live"><span class="pulse"></span> Atualizado {gerado_em}</span>
      <a href="https://github.com/Pyijas/radar-legislativo" target="_blank" rel="noopener">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>
        código-fonte
      </a>
    </div>
  </div>

  <div class="container">
    <div class="kpis rise" id="kpis"></div>

    <div class="charts rise" style="animation-delay:.05s">
      <div class="panel">
        <h2>Impacto</h2>
        <div class="chart-wrap"><canvas id="chartImpacto"></canvas></div>
      </div>
      <div class="panel">
        <h2>Áreas mais frequentes</h2>
        <div class="chart-wrap"><canvas id="chartAreas"></canvas></div>
      </div>
      <div class="panel">
        <h2>Novos PLs por mês</h2>
        <div class="chart-wrap"><canvas id="chartMeses"></canvas></div>
      </div>
    </div>

    <div class="toolbar rise" style="animation-delay:.1s">
      <div class="search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
        <input type="text" id="busca" placeholder="Buscar por texto, ementa, área, autor...">
      </div>
      <div class="segmented" id="fNivel" data-value="todos">
        <button data-v="todos" class="active">Todos</button>
        <button data-v="alto">Alto</button>
        <button data-v="médio">Médio</button>
        <button data-v="baixo">Baixo</button>
      </div>
      <div class="segmented" id="fFonte" data-value="todos">
        <button data-v="todos" class="active">Todas</button>
        <button data-v="ia">IA</button>
        <button data-v="heuristica">Heurística</button>
      </div>
      <select class="pill" id="fArea"><option value="todos">Área: todas</option></select>
      <select class="pill" id="fOrgao"><option value="todos">Órgão: todos</option></select>
      <select class="pill" id="fSituacao"><option value="todos">Situação: todas</option></select>
      <select class="pill" id="fOrdem">
        <option value="data_desc">Mais recentes</option>
        <option value="data_asc">Mais antigos</option>
        <option value="impacto">Maior impacto</option>
      </select>
      <button class="clear-btn" id="limpar">Limpar</button>
    </div>

    <div class="contagem" id="contagem"></div>
    <div id="corpo"></div>
    <div class="rodape-lista" id="rodape"></div>
  </div>

  <div class="modal-backdrop" id="modalBackdrop">
    <div class="modal" id="modal">
      <div class="modal-top">
        <span class="badge" id="modalBadge"></span>
        <button class="modal-close" id="modalClose" aria-label="Fechar">✕</button>
      </div>
      <h2 id="modalTitulo"></h2>
      <div class="item-meta" id="modalMeta"></div>
      <p class="modal-resumo" id="modalResumo"></p>
      <div class="modal-just" id="modalJust" hidden></div>
      <div class="modal-section" id="modalAreasWrap" hidden>
        <h4>Áreas impactadas</h4>
        <div class="tags" id="modalAreas"></div>
      </div>
      <div class="modal-section" id="modalTiposWrap" hidden>
        <h4>Tipo de impacto</h4>
        <div class="tags" id="modalTipos"></div>
      </div>
      <div class="modal-section" id="modalAbrangenciaWrap" hidden>
        <h4>Abrangência</h4>
        <p id="modalAbrangencia"></p>
      </div>
      <div class="modal-section" id="modalAutoresWrap" hidden>
        <h4>Autor(es)</h4>
        <p id="modalAutores"></p>
      </div>
      <div class="item-foot" style="margin-top:0.4rem">
        <span class="fonte" id="modalFonte"></span>
      </div>
    </div>
  </div>

  <footer>
    Dados públicos da API da Câmara dos Deputados · Classificação por IA (Anthropic/Gemini) com fallback heurístico
    · <a href="https://github.com/Pyijas/radar-legislativo" target="_blank" rel="noopener">ver código-fonte</a>
  </footer>

<script id="dados-radar" type="application/json">{dados_json}</script>
<script>
(function() {{
  const DADOS = JSON.parse(document.getElementById('dados-radar').textContent);
  const RANK = {{alto: 0, "médio": 1, baixo: 2}};
  const ROTULO_FONTE = {{ia: 'IA', heuristica: 'Heurística'}};
  const PAGE_SIZE = 24;
  const MESES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];

  const css = getComputedStyle(document.documentElement);
  const cor = (v) => css.getPropertyValue(v).trim();
  const COR_NIVEL = {{alto: cor('--alto'), "médio": cor('--medio'), baixo: cor('--baixo')}};

  const el = {{
    busca: document.getElementById('busca'),
    fNivel: document.getElementById('fNivel'),
    fFonte: document.getElementById('fFonte'),
    fArea: document.getElementById('fArea'),
    fOrgao: document.getElementById('fOrgao'),
    fSituacao: document.getElementById('fSituacao'),
    fOrdem: document.getElementById('fOrdem'),
    limpar: document.getElementById('limpar'),
    kpis: document.getElementById('kpis'),
    contagem: document.getElementById('contagem'),
    corpo: document.getElementById('corpo'),
    rodape: document.getElementById('rodape'),
    modalBackdrop: document.getElementById('modalBackdrop'),
    modalClose: document.getElementById('modalClose'),
  }};

  let paginaAtual = 1;
  let kpisRenderizados = false;

  const PORID = new Map(DADOS.map(d => [d.id, d]));

  function preencherSelect(select, valores, rotuloTodos) {{
    const opts = Array.from(new Set(valores)).filter(Boolean).sort((a, b) => a.localeCompare(b, 'pt-BR'));
    for (const v of opts) {{
      const opt = document.createElement('option');
      opt.value = v; opt.textContent = v;
      select.appendChild(opt);
    }}
  }}
  preencherSelect(el.fArea, DADOS.flatMap(d => d.areas));
  preencherSelect(el.fOrgao, DADOS.map(d => d.orgao));
  preencherSelect(el.fSituacao, DADOS.map(d => d.tramitacaoDesc));

  function esc(s) {{
    return String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
  }}

  function segValor(container) {{ return container.dataset.value; }}
  document.querySelectorAll('.segmented').forEach(seg => {{
    seg.addEventListener('click', (e) => {{
      const btn = e.target.closest('button');
      if (!btn) return;
      seg.dataset.value = btn.dataset.v;
      seg.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === btn));
      render();
    }});
  }});

  function aplicarFiltros() {{
    const busca = el.busca.value.trim().toLowerCase();
    const nivel = segValor(el.fNivel);
    const fonte = segValor(el.fFonte);
    const area = el.fArea.value;
    const orgao = el.fOrgao.value;
    const situacao = el.fSituacao.value;

    let itens = DADOS.filter(d => {{
      if (nivel !== 'todos' && d.nivel !== nivel) return false;
      if (fonte !== 'todos' && d.fonte !== fonte) return false;
      if (area !== 'todos' && !d.areas.includes(area)) return false;
      if (orgao !== 'todos' && d.orgao !== orgao) return false;
      if (situacao !== 'todos' && d.tramitacaoDesc !== situacao) return false;
      if (busca) {{
        const alvo = (d.pl + ' ' + d.resumo + ' ' + d.areas.join(' ') + ' ' + d.autores + ' ' + d.orgao).toLowerCase();
        if (!alvo.includes(busca)) return false;
      }}
      return true;
    }});

    const ordem = el.fOrdem.value;
    if (ordem === 'data_asc') itens.sort((a, b) => a.data.localeCompare(b.data));
    else if (ordem === 'impacto') itens.sort((a, b) => (RANK[a.nivel] ?? 3) - (RANK[b.nivel] ?? 3));
    else itens.sort((a, b) => b.data.localeCompare(a.data));

    return itens;
  }}

  function animarNumero(elemento, alvo) {{
    const inicio = performance.now();
    const duracao = 700;
    function passo(agora) {{
      const t = Math.min(1, (agora - inicio) / duracao);
      const ease = 1 - Math.pow(1 - t, 3);
      elemento.textContent = Math.round(alvo * ease).toLocaleString('pt-BR');
      if (t < 1) requestAnimationFrame(passo);
    }}
    requestAnimationFrame(passo);
  }}

  function renderKpis(itens) {{
    const porNivel = {{alto: 0, "médio": 0, baixo: 0}};
    let ia = 0, heur = 0;
    for (const d of itens) {{
      if (d.nivel in porNivel) porNivel[d.nivel]++;
      if (d.fonte === 'ia') ia++; else if (d.fonte === 'heuristica') heur++;
    }}
    const cards = [
      ['', itens.length, 'Total'],
      ['alto', porNivel.alto, 'Impacto alto'],
      ['medio', porNivel["médio"], 'Impacto médio'],
      ['baixo', porNivel.baixo, 'Impacto baixo'],
      ['ia', ia, 'Via IA'],
      ['heur', heur, 'Via heurística'],
    ];
    if (!kpisRenderizados) {{
      el.kpis.innerHTML = cards.map(([cls, n, l], i) =>
        `<div class="kpi ${{cls}}"><div class="n" data-i="${{i}}">0</div><div class="l">${{l}}</div></div>`
      ).join('');
      kpisRenderizados = true;
    }}
    cards.forEach(([, n], i) => animarNumero(el.kpis.querySelector(`[data-i="${{i}}"]`), n));
  }}

  let chImpacto, chAreas, chMeses;
  function renderCharts(itens) {{
    const porNivel = {{alto: 0, "médio": 0, baixo: 0}};
    for (const d of itens) if (d.nivel in porNivel) porNivel[d.nivel]++;

    const contagemAreas = new Map();
    for (const d of itens) for (const a of d.areas) contagemAreas.set(a, (contagemAreas.get(a) || 0) + 1);
    const topAreas = Array.from(contagemAreas.entries()).sort((a, b) => b[1] - a[1]).slice(0, 8).reverse();

    const porMes = new Array(12).fill(0);
    for (const d of itens) {{
      const m = parseInt(d.data.slice(5, 7), 10) - 1;
      if (m >= 0 && m < 12) porMes[m]++;
    }}

    const textoCor = cor('--muted');
    const gridCor = cor('--border');
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.color = textoCor;

    if (chImpacto) chImpacto.destroy();
    chImpacto = new Chart(document.getElementById('chartImpacto'), {{
      type: 'doughnut',
      data: {{
        labels: ['Alto', 'Médio', 'Baixo'],
        datasets: [{{ data: [porNivel.alto, porNivel["médio"], porNivel.baixo],
                      backgroundColor: [COR_NIVEL.alto, COR_NIVEL["médio"], COR_NIVEL.baixo],
                      borderWidth: 0, hoverOffset: 6 }}]
      }},
      options: {{
        maintainAspectRatio: false, cutout: '68%',
        plugins: {{ legend: {{ position: 'bottom', labels: {{ boxWidth: 8, boxHeight: 8, padding: 12, usePointStyle: true, pointStyle: 'circle' }} }} }}
      }}
    }});

    if (chAreas) chAreas.destroy();
    chAreas = new Chart(document.getElementById('chartAreas'), {{
      type: 'bar',
      data: {{
        labels: topAreas.map(a => a[0]),
        datasets: [{{ data: topAreas.map(a => a[1]), backgroundColor: cor('--accent'), borderRadius: 5, barThickness: 12 }}]
      }},
      options: {{
        indexAxis: 'y', maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ grid: {{ color: gridCor }}, ticks: {{ precision: 0 }} }},
          y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10.5 }} }} }}
        }}
      }}
    }});

    if (chMeses) chMeses.destroy();
    chMeses = new Chart(document.getElementById('chartMeses'), {{
      type: 'bar',
      data: {{
        labels: MESES,
        datasets: [{{ data: porMes, backgroundColor: cor('--accent'), borderRadius: 5, barThickness: 14 }}]
      }},
      options: {{
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ grid: {{ display: false }} }},
          y: {{ grid: {{ color: gridCor }}, ticks: {{ precision: 0 }} }}
        }}
      }}
    }});
  }}

  function itemHtml(d) {{
    const nivel = d.nivel || 'sem';
    const rotuloNivel = d.nivel || '—';
    const tags = d.areas.map(a => `<span class="tag" data-area="${{esc(a)}}">${{esc(a)}}</span>`).join('');
    const origem = ROTULO_FONTE[d.fonte] || '—';
    const meta = [`<span title="Data de apresentação">📅 ${{esc(d.data)}}</span>`];
    if (d.orgao) meta.push(`<span title="Órgão que está com a proposição agora">📍 ${{esc(d.orgao)}}</span>`);
    if (d.tramitacaoData) {{
      const tituloMov = d.tramitacaoDesc ? ` title="${{esc(d.tramitacaoDesc)}}"` : '';
      meta.push(`<span${{tituloMov}}>🔄 última mov. ${{esc(d.tramitacaoData)}}</span>`);
    }}
    return `
      <div class="item" data-id="${{d.id}}">
        <div class="item-head">
          <div class="item-title">
            <a href="${{esc(d.url)}}" target="_blank" rel="noopener">${{esc(d.pl)}}</a>
          </div>
          <span class="badge ${{nivel}}">${{esc(rotuloNivel)}}</span>
        </div>
        <div class="item-meta">${{meta.join('')}}</div>
        <p class="resumo clamp">${{esc(d.resumo)}}</p>
        <div class="item-foot">
          <div class="tags">${{tags}}</div>
          <span class="fonte ${{d.fonte || ''}}">${{esc(origem)}}</span>
        </div>
      </div>`;
  }}

  const modalEl = {{
    badge: document.getElementById('modalBadge'),
    titulo: document.getElementById('modalTitulo'),
    meta: document.getElementById('modalMeta'),
    resumo: document.getElementById('modalResumo'),
    just: document.getElementById('modalJust'),
    areasWrap: document.getElementById('modalAreasWrap'),
    areas: document.getElementById('modalAreas'),
    tiposWrap: document.getElementById('modalTiposWrap'),
    tipos: document.getElementById('modalTipos'),
    abrangenciaWrap: document.getElementById('modalAbrangenciaWrap'),
    abrangencia: document.getElementById('modalAbrangencia'),
    autoresWrap: document.getElementById('modalAutoresWrap'),
    autores: document.getElementById('modalAutores'),
    fonte: document.getElementById('modalFonte'),
  }};

  function abrirModal(d) {{
    const nivel = d.nivel || 'sem';
    modalEl.badge.className = `badge ${{nivel}}`;
    modalEl.badge.textContent = d.nivel || '—';
    modalEl.titulo.innerHTML = `<a href="${{esc(d.url)}}" target="_blank" rel="noopener">${{esc(d.pl)}}</a>`;

    const meta = [`<span>📅 ${{esc(d.data)}}</span>`];
    if (d.orgao) meta.push(`<span>📍 ${{esc(d.orgao)}}</span>`);
    if (d.tramitacaoData) meta.push(`<span>🔄 ${{esc(d.tramitacaoDesc || 'última movimentação')}} — ${{esc(d.tramitacaoData)}}</span>`);
    modalEl.meta.innerHTML = meta.join('');

    modalEl.resumo.textContent = d.resumo;

    if (d.justificativa) {{ modalEl.just.hidden = false; modalEl.just.textContent = '💡 ' + d.justificativa; }}
    else modalEl.just.hidden = true;

    if (d.areas.length) {{
      modalEl.areasWrap.hidden = false;
      modalEl.areas.innerHTML = d.areas.map(a => `<span class="tag" data-area="${{esc(a)}}">${{esc(a)}}</span>`).join('');
    }} else modalEl.areasWrap.hidden = true;

    if (d.tipos.length) {{
      modalEl.tiposWrap.hidden = false;
      modalEl.tipos.innerHTML = d.tipos.map(t => `<span class="tag">${{esc(t)}}</span>`).join('');
    }} else modalEl.tiposWrap.hidden = true;

    if (d.abrangencia) {{ modalEl.abrangenciaWrap.hidden = false; modalEl.abrangencia.textContent = d.abrangencia; }}
    else modalEl.abrangenciaWrap.hidden = true;

    if (d.autores) {{ modalEl.autoresWrap.hidden = false; modalEl.autores.textContent = d.autores; }}
    else modalEl.autoresWrap.hidden = true;

    const origem = ROTULO_FONTE[d.fonte] || '—';
    modalEl.fonte.className = `fonte ${{d.fonte || ''}}`;
    modalEl.fonte.textContent = origem;

    el.modalBackdrop.classList.add('open');
    document.body.classList.add('modal-open');
    el.modalBackdrop.querySelectorAll('.tag').forEach(node => {{
      node.addEventListener('click', () => {{ fecharModal(); el.fArea.value = node.dataset.area; render(); }});
    }});
  }}

  function fecharModal() {{
    el.modalBackdrop.classList.remove('open');
    document.body.classList.remove('modal-open');
  }}

  el.modalClose.addEventListener('click', fecharModal);
  el.modalBackdrop.addEventListener('click', (e) => {{ if (e.target === el.modalBackdrop) fecharModal(); }});
  document.addEventListener('keydown', (e) => {{ if (e.key === 'Escape') fecharModal(); }});

  function render() {{
    paginaAtual = 1;
    renderPagina();
  }}

  function renderPagina() {{
    const itens = aplicarFiltros();
    renderKpis(itens);
    renderCharts(itens);
    el.contagem.innerHTML = `<b>${{itens.length.toLocaleString('pt-BR')}}</b> PL(s) encontrados`;

    const visiveis = itens.slice(0, paginaAtual * PAGE_SIZE);
    el.corpo.innerHTML = visiveis.length
      ? visiveis.map(itemHtml).join('')
      : '<div class="vazio">Nenhum PL encontrado com esses filtros.</div>';

    el.corpo.querySelectorAll('.tag').forEach(node => {{
      node.addEventListener('click', (e) => {{ e.stopPropagation(); el.fArea.value = node.dataset.area; render(); }});
    }});
    el.corpo.querySelectorAll('.item').forEach(node => {{
      node.addEventListener('click', (e) => {{
        if (e.target.closest('a')) return; // deixa o link do PL navegar normalmente
        const d = PORID.get(Number(node.dataset.id));
        if (d) abrirModal(d);
      }});
    }});

    el.rodape.innerHTML = visiveis.length < itens.length
      ? `<button id="maisBtn">Mostrar mais (${{(itens.length - visiveis.length).toLocaleString('pt-BR')}} restantes)</button>` : '';
    const maisBtn = document.getElementById('maisBtn');
    if (maisBtn) maisBtn.addEventListener('click', () => {{ paginaAtual++; renderPagina(); }});
  }}

  el.busca.addEventListener('input', render);
  el.fArea.addEventListener('change', render);
  el.fOrgao.addEventListener('change', render);
  el.fSituacao.addEventListener('change', render);
  el.fOrdem.addEventListener('change', render);
  el.limpar.addEventListener('click', () => {{
    el.busca.value = '';
    el.fNivel.dataset.value = 'todos';
    el.fFonte.dataset.value = 'todos';
    el.fNivel.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    el.fFonte.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    el.fArea.value = 'todos'; el.fOrgao.value = 'todos'; el.fSituacao.value = 'todos'; el.fOrdem.value = 'data_desc';
    render();
  }});

  render();
}})();
</script>
</body>
</html>"""

    caminho.write_text(doc, encoding="utf-8")
    return caminho
