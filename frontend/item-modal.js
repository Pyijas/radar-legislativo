// Card de PL + modal de detalhes — compartilhado entre pais.html e
// salvos.html (as duas páginas que listam PLs individuais). Depende de
// helpers.js (esc/estaSalvo/alternarSalvo) já carregado antes.
//
// Uso: RadarModal.setDados(DADOS) uma vez com o array de PLs da página,
// depois RadarModal.itemHtml(d) pra montar o card e
// RadarModal.ligarCliquesGrid(container) pra ligar os cliques (abrir modal,
// alternar estrela, filtrar por tag) dentro de um container já renderizado.
'use strict';

const RadarModal = (function () {
  let PORID = new Map();

  function setDados(dados) {
    PORID = new Map((dados || []).map(function (d) { return [d.id, d]; }));
  }

  function itemHtml(d) {
    const nivel = d.nivel || 'sem';
    const rotuloNivel = d.nivel || '—';
    const tags = d.areas.map(function (a) { return '<span class="tag" data-area="' + esc(a) + '">' + esc(a) + '</span>'; }).join('');
    const meta = ['<span>' + esc(d.bandeira) + ' ' + esc(d.casaLabel) + '</span>', '<span>📅 ' + esc(d.data) + '</span>'];
    if (d.orgao) meta.push('<span>📍 ' + esc(d.orgao) + '</span>');
    if (d.tramitacaoData) {
      const tit = d.tramitacaoDesc ? (' title="' + esc(d.tramitacaoDesc) + '"') : '';
      meta.push('<span' + tit + '>🔄 última mov. ' + esc(d.tramitacaoData) + '</span>');
    }
    const salvo = estaSalvo(d.id);
    return '' +
      '<div class="item" data-id="' + esc(d.id) + '">' +
        '<div class="item-head">' +
          '<div class="item-title"><a href="' + esc(d.url) + '" target="_blank" rel="noopener">' + esc(d.pl) + '</a></div>' +
          '<div class="item-head-right">' +
            '<button class="star-btn ' + (salvo ? 'ativo' : '') + '" data-star="' + esc(d.id) + '" title="' + (salvo ? 'Remover dos salvos' : 'Salvar') + '">' + (salvo ? '★' : '☆') + '</button>' +
            '<span class="badge ' + nivel + '">' + esc(rotuloNivel) + '</span>' +
          '</div>' +
        '</div>' +
        '<div class="item-meta">' + meta.join('') + '</div>' +
        '<p class="resumo clamp">' + esc(d.resumo) + '</p>' +
        '<div class="item-foot"><div class="tags">' + tags + '</div></div>' +
      '</div>';
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

  function sincronizarEstrela(id, ativo) {
    document.querySelectorAll('[data-star="' + id + '"]').forEach(function (node) {
      node.classList.toggle('ativo', ativo);
      node.textContent = ativo ? '★' : '☆';
      node.title = ativo ? 'Remover dos salvos' : 'Salvar';
    });
  }

  function abrirModal(d) {
    const nivel = d.nivel || 'sem';
    modalEl.badge.className = 'badge ' + nivel;
    modalEl.badge.textContent = d.nivel || '—';
    modalEl.titulo.innerHTML = '<a href="' + esc(d.url) + '" target="_blank" rel="noopener">' + esc(d.pl) + '</a>';

    const meta = ['<span>' + esc(d.bandeira) + ' ' + esc(d.casaLabel) + '</span>', '<span>📅 ' + esc(d.data) + '</span>'];
    if (d.orgao) meta.push('<span>📍 ' + esc(d.orgao) + '</span>');
    if (d.tramitacaoData) meta.push('<span>🔄 ' + esc(d.tramitacaoDesc || 'última movimentação') + ' — ' + esc(d.tramitacaoData) + '</span>');
    modalEl.meta.innerHTML = meta.join('');

    modalEl.resumo.textContent = d.resumo;

    if (d.justificativa) { modalEl.just.hidden = false; modalEl.just.textContent = '💡 ' + d.justificativa; }
    else modalEl.just.hidden = true;

    if (d.areas.length) {
      modalEl.areasWrap.hidden = false;
      modalEl.areas.innerHTML = d.areas.map(function (a) { return '<span class="tag" data-area="' + esc(a) + '">' + esc(a) + '</span>'; }).join('');
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
    modalEl.star.textContent = salvo ? '★' : '☆';
    modalEl.star.title = salvo ? 'Remover dos salvos' : 'Salvar';
    modalEl.star.onclick = function () {
      const ativo = alternarSalvo(d.id);
      modalEl.star.classList.toggle('ativo', ativo);
      modalEl.star.textContent = ativo ? '★' : '☆';
      sincronizarEstrela(d.id, ativo);
      if (window.__aoMudarSalvos) window.__aoMudarSalvos();
    };

    elModalBackdrop.classList.add('open');
    document.body.classList.add('modal-open');
  }

  function fecharModal() {
    elModalBackdrop.classList.remove('open');
    document.body.classList.remove('modal-open');
  }

  elModalClose.addEventListener('click', fecharModal);
  elModalBackdrop.addEventListener('click', function (e) { if (e.target === elModalBackdrop) fecharModal(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fecharModal(); });

  function ligarCliquesGrid(container) {
    container.querySelectorAll('.tag').forEach(function (node) {
      node.addEventListener('click', function (e) {
        e.stopPropagation();
        if (window.__filtrarPorArea) window.__filtrarPorArea(node.dataset.area);
      });
    });
    container.querySelectorAll('[data-star]').forEach(function (node) {
      node.addEventListener('click', function (e) {
        e.stopPropagation();
        const id = node.dataset.star;
        const ativo = alternarSalvo(id);
        sincronizarEstrela(id, ativo);
        if (window.__aoMudarSalvos) window.__aoMudarSalvos();
      });
    });
    container.querySelectorAll('.item').forEach(function (node) {
      node.addEventListener('click', function (e) {
        if (e.target.closest('a') || e.target.closest('[data-star]')) return;
        const d = PORID.get(node.dataset.id);
        if (d) abrirModal(d);
      });
    });
  }

  return { setDados: setDados, itemHtml: itemHtml, ligarCliquesGrid: ligarCliquesGrid, abrirModal: abrirModal, fecharModal: fecharModal };
})();
