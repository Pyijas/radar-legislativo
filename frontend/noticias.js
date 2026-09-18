// Atos e publicações dos reguladores (noticias.html): Anvisa, Ministério da
// Saúde e ANS. Depende de helpers.js (esc) já carregado antes.
//
// A agenda das autoridades saiu daqui em 18/09/2026 e virou agenda.html —
// ela é navegada por data, não lida como lista de publicações.
// As agências latino-americanas seguem sendo coletadas e classificadas no
// back-end, mas fora do painel (ver src/report.py).
(function () {
  const NOTICIAS = window.RADAR_NOTICIAS || [];

  const el = {
    busca: document.getElementById('busca'),
    fNivel: document.getElementById('fNivel'),
    fFonte: document.getElementById('fFonte'),
    limpar: document.getElementById('limpar'),
    kpis: document.getElementById('kpis'),
    contagem: document.getElementById('contagem'),
    grid: document.getElementById('gridNoticias'),
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

  function filtrar() {
    const busca = el.busca.value.trim().toLowerCase();
    const nivel = el.fNivel.dataset.value;
    const fonte = el.fFonte.value;
    return NOTICIAS.filter(d => {
      if (nivel !== 'todos' && d.nivel !== nivel) return false;
      if (fonte !== 'todos' && d.fonte !== fonte) return false;
      if (busca) {
        const alvo = (d.titulo + ' ' + (d.fonteLabel || '') + ' ' + (d.justificativa || '')).toLowerCase();
        if (!alvo.includes(busca)) return false;
      }
      return true;
    });
  }



  function pintar() {
    const itens = filtrar();
    renderKpis(el.kpis, itens, ['Publicações', 'Impacto alto', 'Impacto médio', 'Impacto baixo']);
    el.contagem.innerHTML = `<b>${itens.length.toLocaleString('pt-BR')}</b> ${itens.length === 1 ? 'publicação' : 'publicações'}`;
    el.grid.innerHTML = itens.length
      ? itens.map((n, i) => cardNoticia(n, Math.min(i, 12))).join('')
      : '<div class="vazio">Nenhuma publicação com esses filtros.<br>Use <strong>Limpar</strong> para voltar à lista completa.</div>';
  }

  function render() { transicionar(pintar); }

  let debounce;
  el.busca.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(render, 140);
  });
  el.fFonte.addEventListener('change', render);
  el.limpar.addEventListener('click', () => {
    el.busca.value = '';
    el.fFonte.value = 'todos';
    el.fNivel.dataset.value = 'todos';
    el.fNivel.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    render();
  });

  atualizarContadorSalvos();
  pintar();
})();
