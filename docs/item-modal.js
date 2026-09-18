// Registro de proposição + painel de detalhe — compartilhado entre
// index.html (dashboard do Brasil) e salvos.html. Depende de helpers.js
// (esc/estaSalvo/alternarSalvo) já carregado antes.
//
// Uso: RadarModal.setDados(DADOS) uma vez com o array de PLs da página,
// depois RadarModal.itemHtml(d) pra montar o registro e
// RadarModal.ligarCliquesGrid(container) pra ligar os cliques.
'use strict';

const RadarModal = (function () {
  let PORID = new Map();

  const ico = (nome) => '<svg class="ico"><use href="#ico-' + nome + '"/></svg>';

  function setDados(dados) {
    PORID = new Map((dados || []).map(function (d) { return [d.id, d]; }));
  }

  function metaHtml(d, completo) {
    const meta = [];
    if (d.casaLabel) meta.push('<span>' + ico('instituicao') + esc(d.casaLabel) + '</span>');
    if (d.data) meta.push('<span>' + ico('calendario') + esc(d.data) + '</span>');
    if (d.orgao) meta.push('<span>' + ico('local') + esc(d.orgao) + '</span>');
    if (d.tramitacaoData) {
      const rotulo = completo && d.tramitacaoDesc
        ? esc(d.tramitacaoDesc) + ' — ' + esc(d.tramitacaoData)
        : esc(d.tramitacaoData);
      const tit = !completo && d.tramitacaoDesc ? ' title="' + esc(d.tramitacaoDesc) + '"' : '';
      meta.push('<span' + tit + '>' + ico('fluxo') + rotulo + '</span>');
    }
    return meta.join('');
  }

  function itemHtml(d, i) {
    const nivel = d.nivel || 'sem';
    const tags = d.areas.map(function (a) {
      return '<button class="tag" data-area="' + esc(a) + '">' + esc(a) + '</button>';
    }).join('');
    const salvo = estaSalvo(d.id);
    return '' +
      '<article class="item" data-id="' + esc(d.id) + '" style="--i:' + (i || 0) + '">' +
        '<div class="item-title">' +
          '<a href="' + esc(d.url) + '" target="_blank" rel="noopener">' + esc(d.pl) + '</a>' +
        '</div>' +
        '<div class="item-head-right">' +
          '<button class="star-btn ' + (salvo ? 'ativo' : '') + '" data-star="' + esc(d.id) + '" ' +
            'title="' + (salvo ? 'Remover dos salvos' : 'Salvar') + '" ' +
            'aria-label="' + (salvo ? 'Remover dos salvos' : 'Salvar') + '">' + ico('estrela') + '</button>' +
          '<span class="badge ' + nivel + '">' + esc(d.nivel || 'sem leitura') + '</span>' +
        '</div>' +
        '<div class="item-meta">' + metaHtml(d, false) + '</div>' +
        '<p class="resumo clamp">' + esc(d.resumo) + '</p>' +
        (tags ? '<div class="item-foot"><div class="tags">' + tags + '</div></div>' : '') +
      '</article>';
  }

  const modalEl = {
    badge: document.getElementById('modalBadge'),
    star: document.getElementById('modalStar'),
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
  };
  const elModalBackdrop = document.getElementById('modalBackdrop');
  const elModalClose = document.getElementById('modalClose');
  let ultimoFoco = null;

  function sincronizarEstrela(id, ativo) {
    document.querySelectorAll('[data-star="' + CSS.escape(id) + '"]').forEach(function (node) {
      node.classList.toggle('ativo', ativo);
      node.title = ativo ? 'Remover dos salvos' : 'Salvar';
      node.setAttribute('aria-label', node.title);
    });
  }

  function abrirModal(d) {
    ultimoFoco = document.activeElement;
    const nivel = d.nivel || 'sem';
    modalEl.badge.className = 'badge ' + nivel;
    modalEl.badge.textContent = d.nivel || 'sem leitura';
    modalEl.titulo.innerHTML = '<a href="' + esc(d.url) + '" target="_blank" rel="noopener">' + esc(d.pl) + '</a>';
    modalEl.meta.innerHTML = metaHtml(d, true);
    modalEl.resumo.textContent = d.resumo;

    if (d.justificativa) { modalEl.just.hidden = false; modalEl.just.textContent = d.justificativa; }
    else modalEl.just.hidden = true;

    if (d.areas.length) {
      modalEl.areasWrap.hidden = false;
      modalEl.areas.innerHTML = d.areas.map(function (a) {
        return '<button class="tag" data-area="' + esc(a) + '">' + esc(a) + '</button>';
      }).join('');
      modalEl.areas.querySelectorAll('.tag').forEach(function (node) {
        node.addEventListener('click', function () {
          fecharModal();
          if (window.__filtrarPorArea) window.__filtrarPorArea(node.dataset.area);
        });
      });
    } else modalEl.areasWrap.hidden = true;

    if (d.tipos.length) {
      modalEl.tiposWrap.hidden = false;
      modalEl.tipos.innerHTML = d.tipos.map(function (t) { return '<span class="tag">' + esc(t) + '</span>'; }).join('');
    } else modalEl.tiposWrap.hidden = true;

    if (d.abrangencia) { modalEl.abrangenciaWrap.hidden = false; modalEl.abrangencia.textContent = d.abrangencia; }
    else modalEl.abrangenciaWrap.hidden = true;

    if (d.autores) { modalEl.autoresWrap.hidden = false; modalEl.autores.textContent = d.autores; }
    else modalEl.autoresWrap.hidden = true;

    const salvo = estaSalvo(d.id);
    modalEl.star.classList.toggle('ativo', salvo);
    modalEl.star.title = salvo ? 'Remover dos salvos' : 'Salvar';
    modalEl.star.onclick = function () {
      const ativo = alternarSalvo(d.id);
      modalEl.star.classList.toggle('ativo', ativo);
      modalEl.star.title = ativo ? 'Remover dos salvos' : 'Salvar';
      sincronizarEstrela(d.id, ativo);
      if (window.__aoMudarSalvos) window.__aoMudarSalvos();
    };

    elModalBackdrop.classList.add('open');
    document.body.classList.add('modal-open');
    elModalClose.focus({ preventScroll: true });
  }

  function fecharModal() {
    elModalBackdrop.classList.remove('open');
    document.body.classList.remove('modal-open');
    if (ultimoFoco && ultimoFoco.focus) ultimoFoco.focus({ preventScroll: true });
  }

  elModalClose.addEventListener('click', fecharModal);
  elModalBackdrop.addEventListener('click', function (e) { if (e.target === elModalBackdrop) fecharModal(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && elModalBackdrop.classList.contains('open')) fecharModal();
  });

  // Delegação única por container: sobrevive a re-render da lista sem
  // precisar religar listener em cada card.
  function ligarCliquesGrid(container) {
    if (container.dataset.ligado) return;
    container.dataset.ligado = '1';
    container.addEventListener('click', function (e) {
      const tag = e.target.closest('.tag');
      if (tag && container.contains(tag)) {
        e.stopPropagation();
        if (window.__filtrarPorArea) window.__filtrarPorArea(tag.dataset.area);
        return;
      }
      const star = e.target.closest('[data-star]');
      if (star && container.contains(star)) {
        e.stopPropagation();
        const id = star.dataset.star;
        const ativo = alternarSalvo(id);
        sincronizarEstrela(id, ativo);
        if (window.__aoMudarSalvos) window.__aoMudarSalvos();
        return;
      }
      if (e.target.closest('a')) return;
      const item = e.target.closest('.item');
      if (!item) return;
      const d = PORID.get(item.dataset.id);
      if (d) abrirModal(d);
    });
  }

  return {
    setDados: setDados,
    itemHtml: itemHtml,
    ligarCliquesGrid: ligarCliquesGrid,
    abrirModal: abrirModal,
    fecharModal: fecharModal,
  };
})();
