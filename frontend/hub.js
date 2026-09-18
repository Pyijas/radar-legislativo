// Página inicial (index.html): grade de países acompanhados + "em breve".
// Depende de helpers.js (esc, atualizarContadorSalvos) já carregado antes.
(function () {
  const DADOS = window.RADAR_DADOS || [];
  const PAISES = window.RADAR_PAISES || {};
  const EM_BREVE = window.RADAR_EM_BREVE || [];

  function statsDoPais(codigo) {
    const itens = DADOS.filter(function (d) { return d.pais === codigo; });
    const porNivel = { alto: 0, "médio": 0, baixo: 0 };
    for (const d of itens) if (d.nivel in porNivel) porNivel[d.nivel]++;
    return { total: itens.length, alto: porNivel.alto };
  }

  const linhas = Object.keys(PAISES).map(function (codigo) {
    return Object.assign({ codigo: codigo, info: PAISES[codigo] }, statsDoPais(codigo));
  });
  linhas.sort(function (a, b) { return (b.alto - a.alto) || (b.total - a.total); });

  function cardHtml(l, destaque) {
    const casas = Object.values(l.info.casas || {});
    const stats = l.total > 0
      ? '<div class="stats">' +
          '<div><span class="n">' + l.total.toLocaleString('pt-BR') + '</span><span class="l">Total</span></div>' +
          '<div><span class="n alto">' + l.alto.toLocaleString('pt-BR') + '</span><span class="l">Alto</span></div>' +
        '</div>'
      : '<div class="stats"><span class="aguardando">Aguardando primeira coleta…</span></div>';
    return '' +
      '<a class="pais-card' + (destaque ? ' destaque' : '') + '" href="pais.html?p=' + encodeURIComponent(l.codigo) + '">' +
        (destaque ? '<span class="destaque-tag">Mais relevante agora</span>' : '') +
        '<span class="flag">' + esc(l.info.bandeira) + '</span>' +
        '<div><h3>' + esc(l.info.nome) + '</h3><div class="casas-lista">' + esc(casas.join(' · ')) + '</div></div>' +
        stats +
      '</a>';
  }

  document.getElementById('paisesGrid').innerHTML = linhas.map(function (l, i) {
    return cardHtml(l, i === 0 && l.total > 0);
  }).join('');

  document.getElementById('emBreveGrid').innerHTML = EM_BREVE.map(function (p) {
    return '<div class="pais-card em-breve"><span class="em-breve-tag">Em breve</span>' +
      '<span class="flag">' + esc(p.bandeira) + '</span><div><h3>' + esc(p.nome) + '</h3></div></div>';
  }).join('');

  atualizarContadorSalvos();

  // Banner pro monitoramento institucional (notícias Brasil + mudanças
  // regulatórias da América Latina + agenda do Presidente — ver
  // noticias.html). Fica no hub (e não só dentro de pais.html?p=BR) porque
  // as 5 agências reguladoras latino-americanas não têm PLs rastreados,
  // então não aparecem em nenhum país-card acima — sem esse banner aqui,
  // esse conteúdo ficava invisível pra quem não soubesse a URL de cor.
  const totalMonitor = (window.RADAR_NOTICIAS || []).length + (window.RADAR_AGENDA || []).length;
  if (totalMonitor > 0) {
    const altoMonitor = (window.RADAR_NOTICIAS || []).concat(window.RADAR_AGENDA || []).filter(d => d.nivel === 'alto').length;
    document.getElementById('monBannerContagem').textContent =
      totalMonitor + (totalMonitor === 1 ? ' item relevante' : ' itens relevantes') + (altoMonitor ? ', ' + altoMonitor + ' de alto impacto' : '');
    document.getElementById('monitorBanner').hidden = false;
  }
})();
