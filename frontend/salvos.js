// Página de proposições salvas (salvos.html). Depende de helpers.js e
// item-modal.js (RadarModal) já carregados antes.
(function () {
  const DADOS = window.RADAR_DADOS || [];
  const RANK = { alto: 0, "médio": 1, baixo: 2 };
  const REDUZIR_MOVIMENTO = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const el = {
    busca: document.getElementById('busca'),
    fOrdem: document.getElementById('fOrdem'),
    contagem: document.getElementById('contagem'),
    corpo: document.getElementById('corpo'),
  };

  RadarModal.setDados(DADOS);
  RadarModal.ligarCliquesGrid(el.corpo);
  window.__aoMudarSalvos = function () { atualizarContadorSalvos(); render(); };

  function itensSalvos() {
    const ids = new Set(getSalvos());
    return DADOS.filter(d => ids.has(d.id));
  }

  function aplicarFiltros() {
    const busca = el.busca.value.trim().toLowerCase();
    let itens = itensSalvos();
    if (busca) {
      itens = itens.filter(d => (d.pl + ' ' + d.resumo + ' ' + d.areas.join(' ') + ' ' + d.orgao)
        .toLowerCase().includes(busca));
    }
    const ordem = el.fOrdem.value;
    if (ordem === 'data_asc') itens.sort((a, b) => a.data.localeCompare(b.data));
    else if (ordem === 'impacto') itens.sort((a, b) => (RANK[a.nivel] ?? 3) - (RANK[b.nivel] ?? 3));
    else itens.sort((a, b) => b.data.localeCompare(a.data));
    return itens;
  }

  function pintar() {
    const itens = aplicarFiltros();
    el.contagem.innerHTML = itens.length
      ? `<b>${itens.length.toLocaleString('pt-BR')}</b> ${itens.length === 1 ? 'proposição salva' : 'proposições salvas'}`
      : '';
    el.corpo.innerHTML = itens.length
      ? itens.map((d, i) => RadarModal.itemHtml(d, Math.min(i, 12))).join('')
      : '<div class="vazio">Nenhuma proposição salva ainda.<br>Na <a href="index.html">lista principal</a>, use a estrela de cada registro para guardar aqui.</div>';
  }

  function render() {
    if (REDUZIR_MOVIMENTO || !document.startViewTransition) { pintar(); return; }
    document.startViewTransition(() => pintar());
  }

  function exportarCSV() {
    const itens = aplicarFiltros();
    const cabecalho = ['Casa', 'Proposição', 'Data', 'Impacto', 'Áreas', 'Órgão', 'Situação', 'Resumo', 'Link'];
    const linhas = [cabecalho].concat(itens.map(d => [
      d.casaLabel, d.pl, d.data, d.nivel || '', d.areas.join('; '),
      d.orgao || '', d.tramitacaoDesc || '', d.resumo, d.url,
    ]));
    const csv = linhas.map(l => l.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',')).join('\r\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'radar-legislativo-salvas.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  let debounce;
  el.busca.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(render, 140);
  });
  el.fOrdem.addEventListener('change', render);
  document.getElementById('exportar').addEventListener('click', exportarCSV);
  document.getElementById('limparTudo').addEventListener('click', () => {
    if (itensSalvos().length && confirm('Remover todas as proposições salvas?')) {
      setSalvos([]);
      atualizarContadorSalvos();
      render();
    }
  });

  atualizarContadorSalvos();
  pintar();
})();
