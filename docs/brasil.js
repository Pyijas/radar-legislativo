// Dashboard do Brasil (index.html): panorama, filtros e lista de
// proposições. Depende de helpers.js, item-modal.js (RadarModal) e do
// Chart.js (CDN) já carregados antes.
//
// Os dados já chegam filtrados só para o Brasil — a geração em
// src/report.py exporta apenas PLs brasileiros desde 18/09/2026 (EUA e
// Chile seguem implementados no back-end, mas fora do painel).
(function () {
  const DADOS = window.RADAR_DADOS || [];
  const RANK = { alto: 0, "médio": 1, baixo: 2 };
  const PAGE_SIZE = 20;
  const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  const REDUZIR_MOVIMENTO = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const css = getComputedStyle(document.documentElement);
  const cor = (v) => css.getPropertyValue(v).trim();

  const el = {
    busca: document.getElementById('busca'),
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
  RadarModal.ligarCliquesGrid(el.corpo);
  window.__filtrarPorArea = function (area) {
    el.fArea.value = area;
    render();
    document.getElementById('tituloListaPls').scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  window.__aoMudarSalvos = atualizarContadorSalvos;

  function preencherSelect(select, valores) {
    const opts = Array.from(new Set(valores)).filter(Boolean).sort((a, b) => a.localeCompare(b, 'pt-BR'));
    const frag = document.createDocumentFragment();
    for (const v of opts) {
      const opt = document.createElement('option');
      opt.value = v; opt.textContent = v;
      frag.appendChild(opt);
    }
    select.appendChild(frag);
  }
  preencherSelect(el.fArea, DADOS.flatMap(d => d.areas));
  preencherSelect(el.fOrgao, DADOS.map(d => d.orgao));
  preencherSelect(el.fSituacao, DADOS.map(d => d.tramitacaoDesc));

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
    const casa = el.fCasa.dataset.value;
    const nivel = el.fNivel.dataset.value;
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
    else if (ordem === 'impacto') itens.sort((a, b) => (RANK[a.nivel] ?? 3) - (RANK[b.nivel] ?? 3) || b.data.localeCompare(a.data));
    else itens.sort((a, b) => b.data.localeCompare(a.data));

    return itens;
  }

  function animarNumero(elemento, alvo) {
    if (REDUZIR_MOVIMENTO) {
      elemento.textContent = alvo.toLocaleString('pt-BR');
      return;
    }
    const partida = parseInt(elemento.dataset.valor || '0', 10);
    elemento.dataset.valor = String(alvo);
    const inicio = performance.now();
    const duracao = 620;
    function passo(agora) {
      const t = Math.min(1, (agora - inicio) / duracao);
      const ease = 1 - Math.pow(1 - t, 4);
      elemento.textContent = Math.round(partida + (alvo - partida) * ease).toLocaleString('pt-BR');
      if (t < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
  }

  function renderKpis(itens) {
    const porNivel = { alto: 0, "médio": 0, baixo: 0 };
    for (const d of itens) if (d.nivel in porNivel) porNivel[d.nivel]++;
    const cards = [
      ['', itens.length, 'Proposições'],
      ['alto', porNivel.alto, 'Impacto alto'],
      ['medio', porNivel["médio"], 'Impacto médio'],
      ['baixo', porNivel.baixo, 'Impacto baixo'],
    ];
    if (!kpisRenderizados) {
      el.kpis.innerHTML = cards.map(([cls, , rotulo], i) =>
        `<div class="kpi ${cls}"><span class="n" data-i="${i}" data-valor="0">0</span><span class="l">${rotulo}</span></div>`
      ).join('');
      kpisRenderizados = true;
    }
    cards.forEach(([, n], i) => animarNumero(el.kpis.querySelector(`[data-i="${i}"]`), n));
  }

  let chImpacto, chAreas, chMeses, ultimosItens = [];
  function renderCharts(itens) {
    ultimosItens = itens;
    const porNivel = { alto: 0, "médio": 0, baixo: 0 };
    for (const d of itens) if (d.nivel in porNivel) porNivel[d.nivel]++;

    const contagemAreas = new Map();
    for (const d of itens) for (const a of d.areas) contagemAreas.set(a, (contagemAreas.get(a) || 0) + 1);
    const topAreas = Array.from(contagemAreas.entries()).sort((a, b) => b[1] - a[1]).slice(0, 7).reverse();

    const porMes = new Array(12).fill(0);
    for (const d of itens) {
      const m = parseInt(d.data.slice(5, 7), 10) - 1;
      if (m >= 0 && m < 12) porMes[m]++;
    }

    Chart.defaults.font.family = "'IBM Plex Mono', monospace";
    Chart.defaults.font.size = 10;
    Chart.defaults.color = cor('--ink-3');
    Chart.defaults.animation = REDUZIR_MOVIMENTO ? false : { duration: 700, easing: 'easeOutQuart' };

    const gridCor = cor('--rule');
    const tooltipBase = {
      backgroundColor: cor('--ink'),
      titleColor: cor('--paper'),
      bodyColor: cor('--paper'),
      titleFont: { family: "'IBM Plex Sans', sans-serif", size: 11, weight: '500' },
      bodyFont: { family: "'IBM Plex Mono', monospace", size: 11 },
      padding: 9,
      cornerRadius: 3,
      displayColors: false,
    };

    if (chImpacto) chImpacto.destroy();
    chImpacto = new Chart(document.getElementById('chartImpacto'), {
      type: 'doughnut',
      data: {
        labels: ['Alto', 'Médio', 'Baixo'],
        datasets: [{
          data: [porNivel.alto, porNivel["médio"], porNivel.baixo],
          backgroundColor: [cor('--high'), cor('--mid'), cor('--low')],
          borderColor: cor('--surface'),
          borderWidth: 2,
          hoverOffset: 8,
        }],
      },
      options: {
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          tooltip: tooltipBase,
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 7, boxHeight: 7, padding: 14, usePointStyle: true, pointStyle: 'circle',
              font: { family: "'IBM Plex Mono', monospace", size: 10 },
            },
          },
        },
      },
    });

    if (chAreas) chAreas.destroy();
    chAreas = new Chart(document.getElementById('chartAreas'), {
      type: 'bar',
      data: {
        labels: topAreas.map(a => a[0]),
        datasets: [{
          data: topAreas.map(a => a[1]),
          backgroundColor: cor('--accent'),
          borderRadius: 2,
          barThickness: 11,
        }],
      },
      options: {
        indexAxis: 'y',
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: tooltipBase },
        scales: {
          x: { grid: { color: gridCor, drawTicks: false }, border: { display: false }, ticks: { precision: 0, padding: 6 } },
          y: {
            grid: { display: false },
            border: { display: false },
            ticks: {
              font: { size: 9.5 },
              padding: 4,
              // Sem isso o Chart.js corta o rótulo no meio da palavra quando
              // ele não cabe ("SUS / seguro públ..."); truncar por conta
              // própria mantém o começo legível e o tooltip traz o nome todo.
              callback: function (valor) {
                const texto = this.getLabelForValue(valor);
                return texto.length > 24 ? texto.slice(0, 23) + '…' : texto;
              },
            },
          },
        },
      },
    });

    if (chMeses) chMeses.destroy();
    chMeses = new Chart(document.getElementById('chartMeses'), {
      type: 'bar',
      data: {
        labels: MESES,
        datasets: [{
          data: porMes,
          backgroundColor: cor('--accent'),
          borderRadius: 2,
          barThickness: 13,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: tooltipBase },
        scales: {
          x: { grid: { display: false }, border: { color: gridCor }, ticks: { padding: 4 } },
          y: { grid: { color: gridCor, drawTicks: false }, border: { display: false }, ticks: { precision: 0, padding: 6 } },
        },
      },
    });
  }

  function pintarLista() {
    const itens = aplicarFiltros();
    renderKpis(itens);
    renderCharts(itens);
    el.contagem.innerHTML = `<b>${itens.length.toLocaleString('pt-BR')}</b> ${itens.length === 1 ? 'proposição' : 'proposições'}`;

    const visiveis = itens.slice(0, paginaAtual * PAGE_SIZE);
    el.corpo.innerHTML = visiveis.length
      ? visiveis.map((d, i) => RadarModal.itemHtml(d, Math.min(i % PAGE_SIZE, 12))).join('')
      : '<div class="vazio">Nenhuma proposição corresponde a esses filtros.<br>Ajuste a busca ou use <strong>Limpar</strong> para voltar à lista completa.</div>';

    const restantes = itens.length - visiveis.length;
    el.rodape.innerHTML = restantes > 0
      ? `<button id="maisBtn">Carregar mais ${restantes.toLocaleString('pt-BR')}</button>` : '';
    const maisBtn = document.getElementById('maisBtn');
    if (maisBtn) maisBtn.addEventListener('click', () => { paginaAtual++; pintarLista(); });
  }

  // View Transitions dão o crossfade entre estados de filtro sem
  // reimplementar FLIP na mão; onde não houver suporte, cai no render direto.
  function renderPagina() {
    if (REDUZIR_MOVIMENTO || !document.startViewTransition) { pintarLista(); return; }
    document.startViewTransition(() => pintarLista());
  }

  function render() {
    paginaAtual = 1;
    renderPagina();
  }

  let debounce;
  el.busca.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(render, 140);
  });
  [el.fArea, el.fOrgao, el.fSituacao, el.fOrdem].forEach(s => s.addEventListener('change', render));
  el.limpar.addEventListener('click', () => {
    el.busca.value = '';
    document.querySelectorAll('.segmented').forEach(seg => {
      seg.dataset.value = 'todos';
      seg.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    });
    el.fArea.value = 'todos'; el.fOrgao.value = 'todos';
    el.fSituacao.value = 'todos'; el.fOrdem.value = 'data_desc';
    render();
  });

  // Tema do sistema mudou: o Chart.js já desenhou com as cores antigas,
  // então refaz os gráficos com a paleta nova.
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    setTimeout(() => renderCharts(ultimosItens), 60);
  });

  atualizarContadorSalvos();
  pintarLista();

  const totalMonitor = (window.RADAR_NOTICIAS || []).length + (window.RADAR_AGENDA || []).length;
  if (totalMonitor > 0) {
    const alto = (window.RADAR_NOTICIAS || []).concat(window.RADAR_AGENDA || [])
      .filter(d => d.nivel === 'alto').length;
    document.getElementById('monBannerContagem').textContent =
      totalMonitor.toLocaleString('pt-BR') + ' registros' + (alto ? ', ' + alto + ' de alto impacto' : '');
    document.getElementById('monitorBanner').hidden = false;
  }
})();
