// Funções compartilhadas por todas as páginas (hub, país, notícias, salvos):
// controle dos PLs salvos (localStorage) e escape de HTML pra evitar XSS ao
// injetar texto vindo do banco nos cards/modal via innerHTML.
'use strict';

const SALVOS_KEY = 'radar_salvos_v2';

function getSalvos() {
  try { return JSON.parse(localStorage.getItem(SALVOS_KEY) || '[]'); } catch (e) { return []; }
}
function setSalvos(arr) {
  try { localStorage.setItem(SALVOS_KEY, JSON.stringify(arr)); } catch (e) {}
}
function estaSalvo(id) { return getSalvos().includes(id); }
function alternarSalvo(id) {
  let arr = getSalvos();
  if (arr.includes(id)) arr = arr.filter(x => x !== id); else arr.push(id);
  setSalvos(arr);
  atualizarContadorSalvos();
  return arr.includes(id);
}
function atualizarContadorSalvos() {
  const n = getSalvos().length;
  document.querySelectorAll('.contador-salvos').forEach(function (el) { el.textContent = n; });
}
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
  });
}
