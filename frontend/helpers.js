// Funções compartilhadas por todas as páginas do painel: seleção salva no
// localStorage, escape de HTML (o conteúdo vem do banco e é injetado via
// innerHTML) e o wrapper de transição de estado.
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

const PREFERE_MENOS_MOVIMENTO = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Conta até o valor novo.
//
// Dois cuidados que o caminho ingênuo não tem:
// - o rAF fica guardado no elemento e é cancelado a cada chamada; sem isso,
//   dois filtros em sequência deixam duas animações concorrendo no mesmo
//   dígito e quem termina por último fixa o número da contagem errada;
// - requestAnimationFrame não roda em aba oculta (página aberta em segundo
//   plano, com Cmd+clique ou ao restaurar sessão). Sem a escrita direta e o
//   timer de segurança abaixo, o indicador ficaria parado em zero até o
//   usuário mexer na página.
function animarNumero(elemento, alvo) {
  if (elemento.__raf) cancelAnimationFrame(elemento.__raf);
  if (elemento.__timer) clearTimeout(elemento.__timer);
  elemento.dataset.valor = String(alvo);

  const escrever = (v) => { elemento.textContent = Math.round(v).toLocaleString('pt-BR'); };

  if (PREFERE_MENOS_MOVIMENTO || document.visibilityState !== 'visible') {
    escrever(alvo);
    return;
  }

  const partida = parseInt(elemento.textContent.replace(/\D/g, '') || '0', 10);
  const inicio = performance.now();
  function passo(agora) {
    const t = Math.min(1, (agora - inicio) / 620);
    escrever(partida + (alvo - partida) * (1 - Math.pow(1 - t, 4)));
    elemento.__raf = t < 1 ? requestAnimationFrame(passo) : null;
  }
  elemento.__raf = requestAnimationFrame(passo);
  elemento.__timer = setTimeout(function () {
    if (elemento.__raf) { cancelAnimationFrame(elemento.__raf); elemento.__raf = null; }
    if (elemento.dataset.valor === String(alvo)) escrever(alvo);
  }, 800);
}

// Faixa de indicadores no topo das páginas. `rotulos` traz os quatro textos
// na ordem total, alto, médio, baixo.
function renderKpis(container, itens, rotulos) {
  const porNivel = { alto: 0, "médio": 0, baixo: 0 };
  for (const d of itens) if (d.nivel in porNivel) porNivel[d.nivel]++;
  const valores = [itens.length, porNivel.alto, porNivel["médio"], porNivel.baixo];
  const classes = ['', 'alto', 'medio', 'baixo'];

  if (!container.dataset.pronto) {
    container.innerHTML = classes.map(function (cls, i) {
      return '<div class="kpi ' + cls + '">' +
        '<span class="n" data-i="' + i + '">0</span>' +
        '<span class="l">' + esc(rotulos[i]) + '</span></div>';
    }).join('');
    container.dataset.pronto = '1';
  }
  valores.forEach(function (n, i) {
    animarNumero(container.querySelector('[data-i="' + i + '"]'), n);
  });
}

// Troca de estado (filtro, seleção de data) com crossfade nativo.
// Quando o usuário clica rápido, uma transição interrompe a anterior e a
// API rejeita as promises da abortada — sem estes catch isso vira
// "Uncaught (in promise) InvalidStateError" no console, mesmo com a tela
// atualizando normalmente.
function transicionar(pintar) {
  if (PREFERE_MENOS_MOVIMENTO || !document.startViewTransition) {
    pintar();
    return;
  }
  const t = document.startViewTransition(pintar);
  t.ready.catch(function () {});
  t.finished.catch(function () {});
  t.updateCallbackDone.catch(function () {});
}
