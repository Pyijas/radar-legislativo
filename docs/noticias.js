// Página de monitoramento institucional (noticias.html): notícias da
// Anvisa/Ministério da Saúde/ANS, mudanças regulatórias das agências de
// medicamentos da América Latina, e a agenda pública do Presidente. Depende
// de helpers.js (esc) já carregado antes.
(function () {
  const FONTES_REGULATORIAS = new Set(['anmat', 'digemid', 'isp_cl', 'minsalud_bo', 'msp_uy']);

  const TODAS = (window.RADAR_NOTICIAS || []).map(d => Object.assign({ tipo: 'noticia' }, d));
  const NOTICIAS = TODAS.filter(d => !FONTES_REGULATORIAS.has(d.fonte));
  const REGULATORIO = TODAS.filter(d => FONTES_REGULATORIAS.has(d.fonte)).map(d => Object.assign({}, d, { tipo: 'regulatorio' }));
  const AGENDA = (window.RADAR_AGENDA || []).map(d => Object.assign({ tipo: 'agenda', fonte: 'agenda', fonteLabel: '🎩 ' + d.autoridade }, d));

  const el = {
    busca: document.getElementById('busca'),
    fTipo: document.getElementById('fTipo'),
    fNivel: document.getElementById('fNivel'),
    fFonte: document.getElementById('fFonte'),
    limpar: document.getElementById('limpar'),
    kpis: document.getElementById('kpis'),
  };

  document.querySelectorAll('.segmented').forEach(seg => {
    seg.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      seg.dataset.value = btn.dataset.v;
      seg.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === btn));
      render();
    });
  });

  function cardNoticia(n) {
    return '<div class="mon-card">' +
      '<div class="mon-card-topo"><span>' + esc(n.fonteLabel) + '</span>' +
      '<span class="badge ' + (n.nivel || 'sem') + '">' + esc(n.nivel || '—') + '</span>' +
      '<span class="data">' + esc(n.data) + '</span></div>' +
      '<a class="titulo" href="' + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.titulo) + '</a>' +
      '<p class="justificativa">' + esc(n.justificativa || n.resumo) + '</p>' +
    '</div>';
  }
  function cardAgenda(e) {
    return '<div class="mon-card">' +
      '<div class="mon-card-topo"><span>' + esc(e.autoridade) + '</span>' +
      '<span class="badge ' + (e.nivel || 'sem') + '">' + esc(e.nivel || '—') + '</span>' +
      '<span class="data">' + esc(e.data) + ' ' + esc(e.horario) + '</span></div>' +
      (e.url ? '<a class="titulo" href="' + esc(e.url) + '" target="_blank" rel="noopener">' + esc(e.titulo) + '</a>' : '<div class="titulo">' + esc(e.titulo) + '</div>') +
      (e.local ? '<div class="local">📍 ' + esc(e.local) + '</div>' : '') +
      '<p class="justificativa">' + esc(e.justificativa || e.resumo) + '</p>' +
    '</div>';
  }

  function filtrar(itens) {
    const busca = el.busca.value.trim().toLowerCase();
    const nivel = el.fNivel.dataset.value;
    const fonte = el.fFonte.value;
    return itens.filter(d => {
      if (nivel !== 'todos' && d.nivel !== nivel) return false;
      if (fonte !== 'todos' && d.fonte !== fonte) return false;
      if (busca) {
        const alvo = (d.titulo + ' ' + (d.autoridade || '') + ' ' + (d.local || '') + ' ' + d.justificativa).toLowerCase();
        if (!alvo.includes(busca)) return false;
      }
      return true;
    });
  }

  function renderKpis(itens) {
    const porNivel = { alto: 0, "médio": 0, baixo: 0 };
    for (const d of itens) if (d.nivel in porNivel) porNivel[d.nivel]++;
    const cards = [['', itens.length, 'Total'], ['alto', porNivel.alto, 'Alto'], ['medio', porNivel["médio"], 'Médio'], ['baixo', porNivel.baixo, 'Baixo']];
    el.kpis.innerHTML = cards.map(([cls, n, l]) => `<div class="kpi ${cls}"><div class="n">${n}</div><div class="l">${l}</div></div>`).join('');
  }

  function render() {
    const tipo = el.fTipo.dataset.value;
    const mostrarNoticias = tipo === 'todos' || tipo === 'noticia';
    const mostrarRegulatorio = tipo === 'todos' || tipo === 'regulatorio';
    const mostrarAgenda = tipo === 'todos' || tipo === 'agenda';

    const noticiasVisiveis = mostrarNoticias ? filtrar(NOTICIAS) : [];
    const regulatorioVisivel = mostrarRegulatorio ? filtrar(REGULATORIO) : [];
    const agendaVisivel = mostrarAgenda ? filtrar(AGENDA) : [];

    renderKpis(noticiasVisiveis.concat(regulatorioVisivel).concat(agendaVisivel));

    document.getElementById('ctgNoticias').textContent = '(' + noticiasVisiveis.length + ')';
    document.getElementById('gridNoticias').innerHTML = noticiasVisiveis.length
      ? noticiasVisiveis.map(cardNoticia).join('')
      : '<div class="monitor-vazio">Nenhuma notícia encontrada com esses filtros.</div>';

    document.getElementById('ctgRegulatorio').textContent = '(' + regulatorioVisivel.length + ')';
    document.getElementById('gridRegulatorio').innerHTML = regulatorioVisivel.length
      ? regulatorioVisivel.map(cardNoticia).join('')
      : '<div class="monitor-vazio">Nenhuma mudança regulatória encontrada com esses filtros.</div>';

    document.getElementById('ctgAgenda').textContent = '(' + agendaVisivel.length + ')';
    document.getElementById('gridAgenda').innerHTML = agendaVisivel.length
      ? agendaVisivel.map(cardAgenda).join('')
      : '<div class="monitor-vazio">Nenhum compromisso encontrado com esses filtros.</div>';
  }

  el.busca.addEventListener('input', render);
  el.fFonte.addEventListener('change', render);
  el.limpar.addEventListener('click', () => {
    el.busca.value = ''; el.fFonte.value = 'todos';
    el.fTipo.dataset.value = 'todos';
    el.fTipo.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    el.fNivel.dataset.value = 'todos';
    el.fNivel.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    render();
  });

  render();
})();
