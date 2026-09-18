// Página de monitoramento institucional (noticias.html): atos e
// publicações da Anvisa/Ministério da Saúde/ANS e agenda pública de
// autoridades. Depende de helpers.js (esc) já carregado antes.
//
// As agências reguladoras latino-americanas (ANMAT, DIGEMID, ISP, AGEMED,
// MSP) seguem sendo coletadas e classificadas no back-end, mas estão fora
// do painel desde 18/09/2026 — src/report.py não as exporta para dados.js.
(function () {
  const NOTICIAS = (window.RADAR_NOTICIAS || []).map(d => Object.assign({ tipo: 'noticia' }, d));
  const AGENDA = (window.RADAR_AGENDA || []).map(d => Object.assign(
    { tipo: 'agenda', fonte: 'agenda', fonteLabel: d.autoridade }, d
  ));
  const REDUZIR_MOVIMENTO = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ico = (nome) => '<svg class="ico"><use href="#ico-' + nome + '"/></svg>';

  const el = {
    busca: document.getElementById('busca'),
    fTipo: document.getElementById('fTipo'),
    fNivel: document.getElementById('fNivel'),
    fFonte: document.getElementById('fFonte'),
    limpar: document.getElementById('limpar'),
    kpis: document.getElementById('kpis'),
    contagem: document.getElementById('contagem'),
  };

  let kpisRenderizados = false;

  document.querySelectorAll('.segmented').forEach(seg => {
    seg.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      seg.dataset.value = btn.dataset.v;
      seg.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === btn));
      render();
    });
  });

  function cardNoticia(n, i) {
    return '<article class="mon-card" style="--i:' + i + '">' +
      '<div class="mon-card-topo">' +
        '<span class="orgao">' + esc(n.fonteLabel) + '</span>' +
        '<span class="badge ' + (n.nivel || 'sem') + '">' + esc(n.nivel || 'sem leitura') + '</span>' +
        '<span class="data">' + esc(n.data) + '</span>' +
      '</div>' +
      '<a class="titulo" href="' + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.titulo) + '</a>' +
      '<p class="justificativa">' + esc(n.justificativa || n.resumo) + '</p>' +
    '</article>';
  }

  function cardAgenda(e, i) {
    const quando = [e.data, e.horario].filter(Boolean).join(' · ');
    return '<article class="mon-card" style="--i:' + i + '">' +
      '<div class="mon-card-topo">' +
        '<span class="orgao">' + esc(e.autoridade) + '</span>' +
        '<span class="badge ' + (e.nivel || 'sem') + '">' + esc(e.nivel || 'sem leitura') + '</span>' +
        '<span class="data">' + esc(quando) + '</span>' +
      '</div>' +
      (e.url
        ? '<a class="titulo" href="' + esc(e.url) + '" target="_blank" rel="noopener">' + esc(e.titulo) + '</a>'
        : '<span class="titulo">' + esc(e.titulo) + '</span>') +
      (e.local ? '<div class="local">' + ico('local') + esc(e.local) + '</div>' : '') +
      '<p class="justificativa">' + esc(e.justificativa || e.resumo) + '</p>' +
    '</article>';
  }

  function filtrar(itens) {
    const busca = el.busca.value.trim().toLowerCase();
    const nivel = el.fNivel.dataset.value;
    const fonte = el.fFonte.value;
    return itens.filter(d => {
      if (nivel !== 'todos' && d.nivel !== nivel) return false;
      if (fonte !== 'todos' && d.fonte !== fonte) return false;
      if (busca) {
        const alvo = (d.titulo + ' ' + (d.autoridade || '') + ' ' + (d.local || '') + ' ' +
                      (d.fonteLabel || '') + ' ' + (d.justificativa || '')).toLowerCase();
        if (!alvo.includes(busca)) return false;
      }
      return true;
    });
  }

  function animarNumero(elemento, alvo) {
    if (REDUZIR_MOVIMENTO) { elemento.textContent = alvo.toLocaleString('pt-BR'); return; }
    const partida = parseInt(elemento.dataset.valor || '0', 10);
    elemento.dataset.valor = String(alvo);
    const inicio = performance.now();
    function passo(agora) {
      const t = Math.min(1, (agora - inicio) / 620);
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
      ['', itens.length, 'Registros'],
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

  function pintar() {
    const tipo = el.fTipo.dataset.value;
    const noticiasVisiveis = (tipo === 'todos' || tipo === 'noticia') ? filtrar(NOTICIAS) : [];
    const agendaVisivel = (tipo === 'todos' || tipo === 'agenda') ? filtrar(AGENDA) : [];
    const total = noticiasVisiveis.length + agendaVisivel.length;

    renderKpis(noticiasVisiveis.concat(agendaVisivel));
    el.contagem.innerHTML = `<b>${total.toLocaleString('pt-BR')}</b> ${total === 1 ? 'registro' : 'registros'}`;

    document.getElementById('ctgNoticias').textContent = noticiasVisiveis.length.toLocaleString('pt-BR');
    document.getElementById('gridNoticias').innerHTML = noticiasVisiveis.length
      ? noticiasVisiveis.map((n, i) => cardNoticia(n, Math.min(i, 12))).join('')
      : '<div class="monitor-vazio">Nenhum ato ou publicação com esses filtros.</div>';

    document.getElementById('ctgAgenda').textContent = agendaVisivel.length.toLocaleString('pt-BR');
    document.getElementById('gridAgenda').innerHTML = agendaVisivel.length
      ? agendaVisivel.map((e, i) => cardAgenda(e, Math.min(i, 12))).join('')
      : '<div class="monitor-vazio">Nenhum compromisso com esses filtros.</div>';
  }

  function render() {
    if (REDUZIR_MOVIMENTO || !document.startViewTransition) { pintar(); return; }
    document.startViewTransition(() => pintar());
  }

  let debounce;
  el.busca.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(render, 140);
  });
  el.fFonte.addEventListener('change', render);
  el.limpar.addEventListener('click', () => {
    el.busca.value = '';
    el.fFonte.value = 'todos';
    document.querySelectorAll('.segmented').forEach(seg => {
      seg.dataset.value = 'todos';
      seg.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    });
    render();
  });

  atualizarContadorSalvos();
  pintar();
})();
