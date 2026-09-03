"""
Geração do relatório HTML — um painel interativo autocontido (HTML+CSS+JS
puro, sem dependências externas, sem servidor), com busca, filtros e
estatísticas em cima dos dados salvos no SQLite.
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
        "pl": f"{l['sigla_tipo']} {l['numero']}/{l['ano']}",
        "data": (l["data_apresentacao"] or "")[:10],
        "url": l["url_camara"] or "",
        "resumo": l["resumo"] or l["ementa"] or "",
        "nivel": l["nivel_impacto"],
        "areas": _parse_lista(l["areas_impactadas"]),
        "tipos": _parse_lista(l["tipo_impacto"]),
        "fonte": l["fonte_classificacao"],
        "autores": l["autores"] or "",
    }


def gerar_html(linhas: list, caminho: str | Path) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    dados = [_linha_para_dado(l) for l in linhas]
    # Evita que um "</script>" dentro de algum texto feche a tag prematuramente.
    dados_json = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")

    doc = f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar Legislativo — Saúde/Farma</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #f6f6f4; --card: #ffffff; --border: #e8e8e4; --text: #1a1a1a; --muted: #6b6b6b;
    --accent: #2b6cb0; --chip-bg: #edf2f7; --chip-text: #2d3748;
    --alto: #c0392b; --medio: #b7791f; --baixo: #2f855a; --sem: #718096;
    --ia: #2b6cb0; --heur: #805ad5;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #14151a; --card: #1c1d24; --border: #2c2d36; --text: #e8e8e8; --muted: #9a9a9a;
      --chip-bg: #2c2d3a; --chip-text: #cbd5e0;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 1.75rem;
          background: var(--bg); color: var(--text); }}
  h1 {{ font-size: 1.35rem; margin: 0 0 0.15rem; }}
  .meta {{ color: var(--muted); font-size: 0.82rem; margin-bottom: 1.25rem; }}

  .stats {{ display: flex; flex-wrap: wrap; gap: 0.6rem; margin-bottom: 1.1rem; }}
  .stat {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
           padding: 0.6rem 1rem; min-width: 92px; }}
  .stat .n {{ font-size: 1.3rem; font-weight: 700; line-height: 1.1; }}
  .stat .l {{ font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em; }}
  .stat.alto .n {{ color: var(--alto); }} .stat.medio .n {{ color: var(--medio); }} .stat.baixo .n {{ color: var(--baixo); }}

  .areas-chart {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
                  padding: 0.9rem 1.1rem; margin-bottom: 1.1rem; }}
  .areas-chart h2 {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; color: var(--muted);
                      margin: 0 0 0.6rem; font-weight: 600; }}
  .area-row {{ display: grid; grid-template-columns: 200px 1fr 2.2rem; align-items: center; gap: 0.5rem;
               font-size: 0.8rem; margin-bottom: 0.3rem; }}
  .area-row .barra-fundo {{ background: var(--chip-bg); border-radius: 4px; height: 9px; overflow: hidden; }}
  .area-row .barra {{ background: var(--accent); height: 100%; }}
  .area-row .cnt {{ text-align: right; color: var(--muted); }}
  .area-row .lbl {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }}
  .area-row .lbl:hover {{ text-decoration: underline; }}

  .filtros {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; align-items: center; }}
  .filtros input[type=text] {{ flex: 1; min-width: 200px; }}
  .filtros input, .filtros select {{ padding: 0.45rem 0.6rem; border-radius: 7px; border: 1px solid var(--border);
                                       background: var(--card); color: var(--text); font-size: 0.85rem; }}
  .filtros button {{ padding: 0.45rem 0.8rem; border-radius: 7px; border: 1px solid var(--border);
                      background: var(--card); color: var(--text); cursor: pointer; font-size: 0.85rem; }}
  .filtros button:hover {{ background: var(--chip-bg); }}
  .contagem {{ font-size: 0.78rem; color: var(--muted); margin-bottom: 0.6rem; }}

  table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 10px;
           overflow: hidden; border: 1px solid var(--border); }}
  th, td {{ text-align: left; padding: 0.65rem 0.85rem; border-bottom: 1px solid var(--border); vertical-align: top; }}
  th {{ background: var(--chip-bg); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em;
        color: var(--muted); position: sticky; top: 0; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:hover {{ background: color-mix(in srgb, var(--chip-bg) 55%, transparent); }}
  .pl a {{ font-weight: 600; color: var(--text); text-decoration: none; white-space: nowrap; }}
  .pl a:hover {{ text-decoration: underline; }}
  .data {{ font-size: 0.72rem; color: var(--muted); }}
  .resumo {{ max-width: 480px; font-size: 0.87rem; line-height: 1.4; }}
  .resumo.clamp {{ display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; cursor: pointer; }}
  .badge {{ display: inline-block; color: #fff; padding: 0.15rem 0.55rem; border-radius: 999px;
            font-size: 0.72rem; font-weight: 600; white-space: nowrap; }}
  .tag {{ display: inline-block; background: var(--chip-bg); color: var(--chip-text); padding: 0.1rem 0.5rem;
          border-radius: 5px; font-size: 0.72rem; margin: 0.1rem 0.25rem 0.1rem 0; cursor: pointer; }}
  .tag:hover {{ opacity: 0.75; }}
  .fonte {{ font-size: 0.72rem; font-weight: 600; white-space: nowrap; }}
  .rodape {{ display: flex; justify-content: center; margin-top: 1rem; }}
  .rodape button {{ padding: 0.55rem 1.4rem; border-radius: 999px; border: 1px solid var(--border);
                     background: var(--card); color: var(--text); cursor: pointer; font-size: 0.85rem; }}
  .rodape button:hover {{ background: var(--chip-bg); }}
  .vazio {{ text-align: center; color: var(--muted); padding: 2rem !important; }}
</style>
</head>
<body>
  <h1>Radar Legislativo — Saúde/Farma</h1>
  <div class="meta">Gerado em {gerado_em} · dados da Câmara dos Deputados, tema Saúde</div>

  <div class="stats" id="stats"></div>
  <div class="areas-chart">
    <h2>Áreas mais frequentes (no que está filtrado)</h2>
    <div id="areasChart"></div>
  </div>

  <div class="filtros">
    <input type="text" id="busca" placeholder="Buscar por texto, ementa, área...">
    <select id="fNivel">
      <option value="todos">Impacto: todos</option>
      <option value="alto">Alto</option>
      <option value="médio">Médio</option>
      <option value="baixo">Baixo</option>
    </select>
    <select id="fFonte">
      <option value="todos">Origem: todas</option>
      <option value="ia">IA</option>
      <option value="heuristica">Heurística</option>
    </select>
    <select id="fArea">
      <option value="todos">Área: todas</option>
    </select>
    <select id="fOrdem">
      <option value="data_desc">Mais recentes primeiro</option>
      <option value="data_asc">Mais antigos primeiro</option>
      <option value="impacto">Maior impacto primeiro</option>
    </select>
    <button id="limpar">Limpar filtros</button>
  </div>

  <div class="contagem" id="contagem"></div>
  <table>
    <thead>
      <tr><th>PL</th><th>Resumo / Ementa</th><th>Impacto</th><th>Áreas</th><th>Origem</th></tr>
    </thead>
    <tbody id="corpo"></tbody>
  </table>
  <div class="rodape" id="rodape"></div>

<script id="dados-radar" type="application/json">{dados_json}</script>
<script>
(function() {{
  const DADOS = JSON.parse(document.getElementById('dados-radar').textContent);
  const RANK = {{alto: 0, "médio": 1, baixo: 2}};
  const COR_NIVEL = {{alto: 'var(--alto)', "médio": 'var(--medio)', baixo: 'var(--baixo)'}};
  const ROTULO_FONTE = {{ia: 'IA', heuristica: 'Heurística'}};
  const COR_FONTE = {{ia: 'var(--ia)', heuristica: 'var(--heur)'}};
  const PAGE_SIZE = 50;

  const el = {{
    busca: document.getElementById('busca'),
    fNivel: document.getElementById('fNivel'),
    fFonte: document.getElementById('fFonte'),
    fArea: document.getElementById('fArea'),
    fOrdem: document.getElementById('fOrdem'),
    limpar: document.getElementById('limpar'),
    stats: document.getElementById('stats'),
    areasChart: document.getElementById('areasChart'),
    contagem: document.getElementById('contagem'),
    corpo: document.getElementById('corpo'),
    rodape: document.getElementById('rodape'),
  }};

  let paginaAtual = 1;

  // popula o select de áreas com todas as áreas distintas do dataset
  const todasAreas = Array.from(new Set(DADOS.flatMap(d => d.areas))).sort((a, b) => a.localeCompare(b, 'pt-BR'));
  for (const a of todasAreas) {{
    const opt = document.createElement('option');
    opt.value = a; opt.textContent = a;
    el.fArea.appendChild(opt);
  }}

  function esc(s) {{
    return String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
  }}

  function aplicarFiltros() {{
    const busca = el.busca.value.trim().toLowerCase();
    const nivel = el.fNivel.value;
    const fonte = el.fFonte.value;
    const area = el.fArea.value;

    let itens = DADOS.filter(d => {{
      if (nivel !== 'todos' && d.nivel !== nivel) return false;
      if (fonte !== 'todos' && d.fonte !== fonte) return false;
      if (area !== 'todos' && !d.areas.includes(area)) return false;
      if (busca) {{
        const alvo = (d.pl + ' ' + d.resumo + ' ' + d.areas.join(' ') + ' ' + d.autores).toLowerCase();
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

  function renderStats(itens) {{
    const porNivel = {{alto: 0, "médio": 0, baixo: 0}};
    let ia = 0, heur = 0;
    for (const d of itens) {{
      if (d.nivel in porNivel) porNivel[d.nivel]++;
      if (d.fonte === 'ia') ia++; else if (d.fonte === 'heuristica') heur++;
    }}
    el.stats.innerHTML = `
      <div class="stat"><div class="n">${{itens.length}}</div><div class="l">Total</div></div>
      <div class="stat alto"><div class="n">${{porNivel.alto}}</div><div class="l">Impacto alto</div></div>
      <div class="stat medio"><div class="n">${{porNivel["médio"]}}</div><div class="l">Impacto médio</div></div>
      <div class="stat baixo"><div class="n">${{porNivel.baixo}}</div><div class="l">Impacto baixo</div></div>
      <div class="stat"><div class="n">${{ia}}</div><div class="l">Via IA</div></div>
      <div class="stat"><div class="n">${{heur}}</div><div class="l">Via heurística</div></div>`;
  }}

  function renderAreasChart(itens) {{
    const contagem = new Map();
    for (const d of itens) for (const a of d.areas) contagem.set(a, (contagem.get(a) || 0) + 1);
    const top = Array.from(contagem.entries()).sort((a, b) => b[1] - a[1]).slice(0, 8);
    if (!top.length) {{ el.areasChart.innerHTML = '<div style="color:var(--muted); font-size:0.85rem;">Nenhuma área no filtro atual.</div>'; return; }}
    const max = top[0][1];
    el.areasChart.innerHTML = top.map(([nome, n]) => `
      <div class="area-row">
        <div class="lbl" data-area="${{esc(nome)}}" title="${{esc(nome)}} — clique pra filtrar">${{esc(nome)}}</div>
        <div class="barra-fundo"><div class="barra" style="width:${{(n / max * 100).toFixed(0)}}%"></div></div>
        <div class="cnt">${{n}}</div>
      </div>`).join('');
    el.areasChart.querySelectorAll('.lbl').forEach(node => {{
      node.addEventListener('click', () => {{ el.fArea.value = node.dataset.area; render(); }});
    }});
  }}

  function linhaHtml(d) {{
    const nivel = d.nivel || '—';
    const cor = COR_NIVEL[d.nivel] || 'var(--sem)';
    const tags = d.areas.map(a => `<span class="tag" data-area="${{esc(a)}}">${{esc(a)}}</span>`).join('');
    const origem = ROTULO_FONTE[d.fonte] || '—';
    const corFonte = COR_FONTE[d.fonte] || 'var(--sem)';
    return `
      <tr>
        <td class="pl">
          <a href="${{esc(d.url)}}" target="_blank" rel="noopener">${{esc(d.pl)}}</a>
          <div class="data">${{esc(d.data)}}</div>
        </td>
        <td class="resumo clamp" title="Clique para expandir">${{esc(d.resumo)}}</td>
        <td><span class="badge" style="background:${{cor}}">${{esc(nivel)}}</span></td>
        <td>${{tags}}</td>
        <td><span class="fonte" style="color:${{corFonte}}">${{esc(origem)}}</span></td>
      </tr>`;
  }}

  function render() {{
    paginaAtual = 1;
    renderPagina();
  }}

  function renderPagina() {{
    const itens = aplicarFiltros();
    renderStats(itens);
    renderAreasChart(itens);
    el.contagem.textContent = itens.length + ' PL(s) encontrados';

    const visiveis = itens.slice(0, paginaAtual * PAGE_SIZE);
    el.corpo.innerHTML = visiveis.length
      ? visiveis.map(linhaHtml).join('')
      : '<tr><td class="vazio" colspan="5">Nenhum PL encontrado com esses filtros.</td></tr>';

    el.corpo.querySelectorAll('.tag').forEach(node => {{
      node.addEventListener('click', () => {{ el.fArea.value = node.dataset.area; render(); }});
    }});
    el.corpo.querySelectorAll('.resumo').forEach(node => {{
      node.addEventListener('click', () => node.classList.toggle('clamp'));
    }});

    el.rodape.innerHTML = visiveis.length < itens.length
      ? `<button id="maisBtn">Mostrar mais (${{itens.length - visiveis.length}} restantes)</button>` : '';
    const maisBtn = document.getElementById('maisBtn');
    if (maisBtn) maisBtn.addEventListener('click', () => {{ paginaAtual++; renderPagina(); }});
  }}

  [el.busca].forEach(i => i.addEventListener('input', render));
  [el.fNivel, el.fFonte, el.fArea, el.fOrdem].forEach(i => i.addEventListener('change', render));
  el.limpar.addEventListener('click', () => {{
    el.busca.value = ''; el.fNivel.value = 'todos'; el.fFonte.value = 'todos';
    el.fArea.value = 'todos'; el.fOrdem.value = 'data_desc';
    render();
  }});

  render();
}})();
</script>
</body>
</html>"""

    caminho.write_text(doc, encoding="utf-8")
    return caminho
