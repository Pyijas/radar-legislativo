// Página de PLs salvos (salvos.html). Depende de helpers.js e item-modal.js
// (RadarModal) já carregados antes.
(function () {
  const DADOS = window.RADAR_DADOS || [];
  const RANK = { alto: 0, "médio": 1, baixo: 2 };

  const el = {
    busca: document.getElementById('busca'),
    fOrdem: document.getElementById('fOrdem'),
    contagem: document.getElementById('contagem'),
    corpo: document.getElementById('corpo'),
  };

  RadarModal.setDados(DADOS);
  window.__aoMudarSalvos = function () { atualizarContadorSalvos(); render(); };

  function itensSalvos() {
    const ids = new Set(getSalvos());
    return DADOS.filter(d => ids.has(d.id));
  }

  function aplicarFiltros() {
    const busca = el.busca.value.trim().toLowerCase();
    let itens = itensSalvos();
    if (busca) {
      itens = itens.filter(d => (d.pl + ' ' + d.resumo + ' ' + d.areas.join(' ') + ' ' + d.orgao).toLowerCase().includes(busca));
    }
    const ordem = el.fOrdem.value;
    if (ordem === 'data_asc') itens.sort((a, b) => a.data.localeCompare(b.data));
    else if (ordem === 'impacto') itens.sort((a, b) => (RANK[a.nivel] ?? 3) - (RANK[b.nivel] ?? 3));
    else itens.sort((a, b) => b.data.localeCompare(a.data));
    return itens;
  }

  function render() {
    const itens = aplicarFiltros();
    el.contagem.innerHTML = itens.length ? `<b>${itens.length}</b> PL(s) salvo(s)` : '';
    el.corpo.innerHTML = itens.length
      ? itens.map(RadarModal.itemHtml).join('')
      : '<div class="vazio">Você ainda não salvou nenhum PL.<br>Volte à <a href="index.html">página inicial</a>, escolha um país e clique na estrela ☆ dos que quiser guardar aqui.</div>';
    RadarModal.ligarCliquesGrid(el.corpo);
  }

  function exportarCSV() {
    const itens = aplicarFiltros();
    const cabecalho = ['País', 'Casa', 'PL', 'Data', 'Impacto', 'Áreas', 'Órgão', 'Situação', 'Resumo', 'Link'];
    const linhas = [cabecalho].concat(itens.map(d => [
      d.paisNome, d.casaLabel, d.pl, d.data, d.nivel || '', d.areas.join('; '), d.orgao || '', d.tramitacaoDesc || '', d.resumo, d.url,
    ]));
    const csv = linhas.map(l => l.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',')).join('\r\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'pls_salvos.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  el.busca.addEventListener('input', render);
  el.fOrdem.addEventListener('change', render);
  document.getElementById('exportar').addEventListener('click', exportarCSV);
  document.getElementById('limparTudo').addEventListener('click', () => {
    if (itensSalvos().length && confirm('Remover todos os PLs salvos?')) {
      setSalvos([]);
      atualizarContadorSalvos();
      render();
    }
  });

  atualizarContadorSalvos();
  render();
})();
