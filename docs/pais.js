// Página de um país (pais.html?p=BR, ?p=US, ...): KPIs, gráficos, filtros e
// grade de PLs. Depende de helpers.js e item-modal.js (RadarModal) já
// carregados antes, e do Chart.js (CDN, só incluído nesta página).
(function () {
  const params = new URLSearchParams(location.search);
  const PAIS = (params.get('p') || 'BR').toUpperCase();
  const PAIS_INFO = (window.RADAR_PAISES || {})[PAIS] || { nome: PAIS, bandeira: '', casas: {} };
  const DADOS = (window.RADAR_DADOS || []).filter(function (d) { return d.pais === PAIS; });
  const RANK = { alto: 0, "médio": 1, baixo: 2 };
  const PAGE_SIZE = 24;
  const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

  document.title = (PAIS_INFO.bandeira ? PAIS_INFO.bandeira + ' ' : '') + PAIS_INFO.nome + ' — Radar Legislativo';
  document.getElementById('marcaTitulo').textContent = (PAIS_INFO.bandeira ? PAIS_INFO.bandeira + ' ' : '') + PAIS_INFO.nome;
  document.getElementById('marcaSub').textContent = 'Saúde & Farma no Congresso';

  const css = getComputedStyle(document.documentElement);
  const cor = (v) => css.getPropertyValue(v).trim();
  const COR_NIVEL = { alto: cor('--alto'), "médio": cor('--medio'), baixo: cor('--baixo') };

  const el = {
    busca: document.getElementById('busca'),
    fCasaWrap: document.getElementById('fCasaWrap'),
    fCasa: document.getElementById('fCasa'),
    fNivel: document.getElementById('fNivel'),
    fArea: document.getElementById('fArea'),
    fOrgao: document.getElementById('fOrgao'),
    fSituacao: document.getElementById('fSituacao'),
    fOrdem: document.getElementById('fOrdem'),
    limpar: document.getElementById('limpar'),
    kpis: document.getElementById('kpis'),
    contagem: document.getElementById('contagem'),
    corpo: document.getElementById('corpo'),
    rodape: document.getElementById('rodape'),
  };

  let paginaAtual = 1;
  let kpisRenderizados = false;

  RadarModal.setDados(DADOS);
  window.__filtrarPorArea = function (area) { el.fArea.value = area; render(); };
  window.__aoMudarSalvos = atualizarContadorSalvos;

  const casasEntries = Object.entries(PAIS_INFO.casas || {});
  if (casasEntries.length > 1) {
    el.fCasaWrap.hidden = false;
    el.fCasa.innerHTML = '<button data-v="todos" class="active">Todas as casas</button>' +
      casasEntries.map(function (e) { return '<button data-v="' + esc(e[0]) + '">' + esc(e[1]) + '</button>'; }).join('');
  }

  function preencherSelect(select, valores) {
    const opts = Array.from(new Set(valores)).filter(Boolean).sort((a, b) => a.localeCompare(b, 'pt-BR'));
    for (const v of opts) {
      const opt = document.createElement('option');
      opt.value = v; opt.textContent = v;
      select.appendChild(opt);
    }
  }
  preencherSelect(el.fArea, DADOS.flatMap(d => d.areas));
  preencherSelect(el.fOrgao, DADOS.map(d => d.orgao));
  preencherSelect(el.fSituacao, DADOS.map(d => d.tramitacaoDesc));

  function segValor(container) { return container.dataset.value; }
  document.querySelectorAll('.segmented').forEach(seg => {
    seg.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      seg.dataset.value = btn.dataset.v;
      seg.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === btn));
      render();
    });
  });

  function aplicarFiltros() {
    const busca = el.busca.value.trim().toLowerCase();
    const casa = segValor(el.fCasa);
    const nivel = segValor(el.fNivel);
    const area = el.fArea.value;
    const orgao = el.fOrgao.value;
    const situacao = el.fSituacao.value;

    let itens = DADOS.filter(d => {
      if (casa !== 'todos' && d.casa !== casa) return false;
      if (nivel !== 'todos' && d.nivel !== nivel) return false;
      if (area !== 'todos' && !d.areas.includes(area)) return false;
      if (orgao !== 'todos' && d.orgao !== orgao) return false;
      if (situacao !== 'todos' && d.tramitacaoDesc !== situacao) return false;
      if (busca) {
        const alvo = (d.pl + ' ' + d.resumo + ' ' + d.areas.join(' ') + ' ' + d.autores + ' ' + d.orgao).toLowerCase();
        if (!alvo.includes(busca)) return false;
      }
      return true;
    });

    const ordem = el.fOrdem.value;
    if (ordem === 'data_asc') itens.sort((a, b) => a.data.localeCompare(b.data));
    else if (ordem === 'impacto') itens.sort((a, b) => (RANK[a.nivel] ?? 3) - (RANK[b.nivel] ?? 3));
    else itens.sort((a, b) => b.data.localeCompare(a.data));

    return itens;
  }

  function animarNumero(elemento, alvo) {
    const inicio = performance.now();
    const duracao = 700;
    function passo(agora) {
      const t = Math.min(1, (agora - inicio) / duracao);
      const ease = 1 - Math.pow(1 - t, 3);
      elemento.textContent = Math.round(alvo * ease).toLocaleString('pt-BR');
      if (t < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
  }

  function renderKpis(itens) {
    const porNivel = { alto: 0, "médio": 0, baixo: 0 };
    for (const d of itens) if (d.nivel in porNivel) porNivel[d.nivel]++;
    const cards = [
      ['', itens.length, 'Total'],
      ['alto', porNivel.alto, 'Impacto alto'],
      ['medio', porNivel["médio"], 'Impacto médio'],
      ['baixo', porNivel.baixo, 'Impacto baixo'],
    ];
    if (!kpisRenderizados) {
      el.kpis.innerHTML = cards.map(([cls, n, l], i) =>
        `<div class="kpi ${cls}"><div class="n" data-i="${i}">0</div><div class="l">${l}</div></div>`
      ).join('');
      kpisRenderizados = true;
    }
    cards.forEach(([, n], i) => animarNumero(el.kpis.querySelector(`[data-i="${i}"]`), n));
  }

  let chImpacto, chAreas, chMeses;
  function renderCharts(itens) {
    const porNivel = { alto: 0, "médio": 0, baixo: 0 };
    for (const d of itens) if (d.nivel in porNivel) porNivel[d.nivel]++;

    const contagemAreas = new Map();
    for (const d of itens) for (const a of d.areas) contagemAreas.set(a, (contagemAreas.get(a) || 0) + 1);
    const topAreas = Array.from(contagemAreas.entries()).sort((a, b) => b[1] - a[1]).slice(0, 8).reverse();

    const porMes = new Array(12).fill(0);
    for (const d of itens) {
      const m = parseInt(d.data.slice(5, 7), 10) - 1;
      if (m >= 0 && m < 12) porMes[m]++;
    }

    const textoCor = cor('--muted');
    const gridCor = cor('--border');
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.color = textoCor;

    if (chImpacto) chImpacto.destroy();
    chImpacto = new Chart(document.getElementById('chartImpacto'), {
      type: 'doughnut',
      data: {
        labels: ['Alto', 'Médio', 'Baixo'],
        datasets: [{ data: [porNivel.alto, porNivel["médio"], porNivel.baixo],
                      backgroundColor: [COR_NIVEL.alto, COR_NIVEL["médio"], COR_NIVEL.baixo],
                      borderWidth: 0, hoverOffset: 6 }]
      },
      options: {
        maintainAspectRatio: false, cutout: '68%',
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 8, boxHeight: 8, padding: 12, usePointStyle: true, pointStyle: 'circle' } } }
      }
    });

    if (chAreas) chAreas.destroy();
    chAreas = new Chart(document.getElementById('chartAreas'), {
      type: 'bar',
      data: {
        labels: topAreas.map(a => a[0]),
        datasets: [{ data: topAreas.map(a => a[1]), backgroundColor: cor('--accent'), borderRadius: 5, barThickness: 12 }]
      },
      options: {
        indexAxis: 'y', maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: gridCor }, ticks: { precision: 0 } },
          y: { grid: { display: false }, ticks: { font: { size: 10.5 } } }
        }
      }
    });

    if (chMeses) chMeses.destroy();
    chMeses = new Chart(document.getElementById('chartMeses'), {
      type: 'bar',
      data: {
        labels: MESES,
        datasets: [{ data: porMes, backgroundColor: cor('--accent'), borderRadius: 5, barThickness: 14 }]
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: gridCor }, ticks: { precision: 0 } }
        }
      }
    });
  }

  function render() {
    paginaAtual = 1;
    renderPagina();
  }

  function renderPagina() {
    const itens = aplicarFiltros();
    renderKpis(itens);
    renderCharts(itens);
    el.contagem.innerHTML = `<b>${itens.length.toLocaleString('pt-BR')}</b> PL(s) encontrados`;

    const visiveis = itens.slice(0, paginaAtual * PAGE_SIZE);
    el.corpo.innerHTML = visiveis.length
      ? visiveis.map(RadarModal.itemHtml).join('')
      : '<div class="vazio">Nenhum PL encontrado com esses filtros.<br>Se a base pra ' + esc(PAIS_INFO.nome) + ' ainda está vazia, é porque a coleta dessa fonte é recente — volte em breve.</div>';
    RadarModal.ligarCliquesGrid(el.corpo);

    el.rodape.innerHTML = visiveis.length < itens.length
      ? `<button id="maisBtn">Mostrar mais (${(itens.length - visiveis.length).toLocaleString('pt-BR')} restantes)</button>` : '';
    const maisBtn = document.getElementById('maisBtn');
    if (maisBtn) maisBtn.addEventListener('click', () => { paginaAtual++; renderPagina(); });
  }

  el.busca.addEventListener('input', render);
  el.fArea.addEventListener('change', render);
  el.fOrgao.addEventListener('change', render);
  el.fSituacao.addEventListener('change', render);
  el.fOrdem.addEventListener('change', render);
  el.limpar.addEventListener('click', () => {
    el.busca.value = '';
    el.fCasa.dataset.value = 'todos';
    el.fCasa.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    el.fNivel.dataset.value = 'todos';
    el.fNivel.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    el.fArea.value = 'todos'; el.fOrgao.value = 'todos'; el.fSituacao.value = 'todos'; el.fOrdem.value = 'data_desc';
    render();
  });

  atualizarContadorSalvos();
  render();

  // Banner pro monitoramento institucional (notícias Anvisa/MS/ANS + agenda
  // do Presidente — página própria, ver noticias.html) — só faz sentido pro
  // Brasil, já que todas essas fontes são brasileiras.
  if (PAIS === 'BR') {
    const total = (window.RADAR_NOTICIAS || []).length + (window.RADAR_AGENDA || []).length;
    if (total > 0) {
      const alto = (window.RADAR_NOTICIAS || []).concat(window.RADAR_AGENDA || []).filter(d => d.nivel === 'alto').length;
      document.getElementById('monBannerContagem').textContent =
        total + (total === 1 ? ' item relevante' : ' itens relevantes') + (alto ? ', ' + alto + ' de alto impacto' : '');
      document.getElementById('monitorBanner').hidden = false;
    }
  }
})();
