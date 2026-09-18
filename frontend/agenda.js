// Agenda pública das autoridades (agenda.html): calendário de seleção +
// linha do tempo dos compromissos do período escolhido. Depende de
// helpers.js (esc) já carregado antes.
//
// Ficou em página própria em 18/09/2026: misturada às notícias, a agenda
// confundia — ela é navegada por data, não lida como lista de publicações.
(function () {
  const EVENTOS = window.RADAR_AGENDA || [];
  const MAX_DIAS = 14;
  const ico = (nome) => '<svg class="ico"><use href="#ico-' + nome + '"/></svg>';

  const el = {
    calMes: document.getElementById('calMes'),
    calGrid: document.getElementById('calGrid'),
    calAnterior: document.getElementById('calAnterior'),
    calProximo: document.getElementById('calProximo'),
    busca: document.getElementById('busca'),
    fAutoridade: document.getElementById('fAutoridade'),
    fNivel: document.getElementById('fNivel'),
    limpar: document.getElementById('limpar'),
    kpis: document.getElementById('kpis'),
    periodoTitulo: document.getElementById('periodoTitulo'),
    periodoResumo: document.getElementById('periodoResumo'),
    lista: document.getElementById('listaAgenda'),
  };

  // --- datas -----------------------------------------------------------
  // Tudo em horário local e via string 'aaaa-mm-dd': construir Date a partir
  // da string ISO direto joga pra UTC e faz o dia "andar" no fuso do Brasil.
  const pad = (n) => String(n).padStart(2, '0');
  const chaveDe = (d) => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  const paraData = (s) => {
    const [a, m, d] = s.split('-').map(Number);
    return new Date(a, m - 1, d);
  };
  const fmtLongo = new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' });
  const fmtCurto = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'long' });
  const fmtMes = new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' });

  function formatarHora(h) {
    const m = /(\d{1,2})\D*(\d{2})?/.exec(h || '');
    if (!m) return '';
    return pad(m[1]) + ':' + (m[2] || '00');
  }
  const minutosDe = (h) => {
    const t = formatarHora(h);
    return t ? Number(t.slice(0, 2)) * 60 + Number(t.slice(3)) : 24 * 60 + 1;
  };

  // --- índice ----------------------------------------------------------
  const porDia = new Map();
  for (const ev of EVENTOS) {
    if (!ev.data) continue;
    if (!porDia.has(ev.data)) porDia.set(ev.data, []);
    porDia.get(ev.data).push(ev);
  }
  const datasOrdenadas = Array.from(porDia.keys()).sort();
  const primeiraData = datasOrdenadas[0];
  const ultimaData = datasOrdenadas[datasOrdenadas.length - 1];

  const autoridades = Array.from(new Set(EVENTOS.map(e => e.autoridade).filter(Boolean)))
    .sort((a, b) => a.localeCompare(b, 'pt-BR'));
  for (const a of autoridades) {
    const opt = document.createElement('option');
    opt.value = a; opt.textContent = a;
    el.fAutoridade.appendChild(opt);
  }

  // --- estado ----------------------------------------------------------
  let mesVisivel = ultimaData ? paraData(ultimaData) : new Date();
  mesVisivel = new Date(mesVisivel.getFullYear(), mesVisivel.getMonth(), 1);
  let selecao = ultimaData ? { inicio: ultimaData, fim: ultimaData } : null;
  let ancora = ultimaData || null;
  let diasMostrados = MAX_DIAS;

  function passaFiltros(ev) {
    const busca = el.busca.value.trim().toLowerCase();
    const autoridade = el.fAutoridade.value;
    const nivel = el.fNivel.dataset.value;
    if (autoridade !== 'todos' && ev.autoridade !== autoridade) return false;
    if (nivel !== 'todos' && ev.nivel !== nivel) return false;
    if (busca) {
      const alvo = (ev.titulo + ' ' + (ev.local || '') + ' ' + (ev.autoridade || '') + ' ' +
                    (ev.cargo || '') + ' ' + (ev.justificativa || '')).toLowerCase();
      if (!alvo.includes(busca)) return false;
    }
    return true;
  }

  const noPeriodo = (data) => !selecao || (data >= selecao.inicio && data <= selecao.fim);

  function eventosVisiveis() {
    return EVENTOS.filter(ev => ev.data && noPeriodo(ev.data) && passaFiltros(ev));
  }

  // --- calendário ------------------------------------------------------
  const capitalizar = (s) => s.charAt(0).toUpperCase() + s.slice(1);

  function renderCalendario() {
    el.calMes.textContent = capitalizar(fmtMes.format(mesVisivel));

    const ano = mesVisivel.getFullYear();
    const mes = mesVisivel.getMonth();
    const primeiroDia = new Date(ano, mes, 1);
    const diasNoMes = new Date(ano, mes + 1, 0).getDate();
    const deslocamento = primeiroDia.getDay();
    const hoje = chaveDe(new Date());

    const celulas = [];
    // dias do mês anterior, só pra fechar a primeira semana
    const diasAntes = new Date(ano, mes, 0).getDate();
    for (let i = deslocamento - 1; i >= 0; i--) {
      celulas.push('<div class="cal-dia fora"><span class="num">' + (diasAntes - i) + '</span></div>');
    }

    for (let dia = 1; dia <= diasNoMes; dia++) {
      const data = ano + '-' + pad(mes + 1) + '-' + pad(dia);
      const doDia = (porDia.get(data) || []).filter(passaFiltros);
      const niveis = ['alto', 'médio', 'baixo'].filter(n => doDia.some(e => e.nivel === n));
      const classes = ['cal-dia'];
      if (doDia.length) classes.push('tem');
      if (selecao && data >= selecao.inicio && data <= selecao.fim) classes.push('sel');
      if (data === hoje) classes.push('hoje');
      const rotulo = doDia.length
        ? doDia.length + (doDia.length === 1 ? ' compromisso' : ' compromissos')
        : 'sem compromissos';
      celulas.push(
        '<button type="button" class="' + classes.join(' ') + '" data-data="' + data + '" ' +
        (doDia.length ? '' : 'disabled ') +
        'title="' + esc(fmtCurto.format(paraData(data)) + ' — ' + rotulo) + '">' +
          '<span class="num">' + dia + '</span>' +
          '<span class="cal-pontos">' +
            niveis.map(n => '<i class="cal-ponto ' + n + '"></i>').join('') +
          '</span>' +
        '</button>'
      );
    }

    // completa a última semana pra grade não ficar com buraco
    while (celulas.length % 7 !== 0) {
      const proximo = celulas.length - deslocamento - diasNoMes + 1;
      celulas.push('<div class="cal-dia fora"><span class="num">' + proximo + '</span></div>');
    }

    el.calGrid.innerHTML = celulas.join('');

    const limiteMin = primeiraData ? paraData(primeiraData) : null;
    const limiteMax = ultimaData ? paraData(ultimaData) : null;
    el.calAnterior.disabled = !!limiteMin &&
      new Date(ano, mes, 0) < new Date(limiteMin.getFullYear(), limiteMin.getMonth(), 1);
    el.calProximo.disabled = !!limiteMax &&
      new Date(ano, mes + 1, 1) > new Date(limiteMax.getFullYear(), limiteMax.getMonth(), 1);
  }

  el.calGrid.addEventListener('click', (e) => {
    const botao = e.target.closest('.cal-dia[data-data]');
    if (!botao) return;
    const data = botao.dataset.data;
    if (e.shiftKey && ancora) {
      selecao = { inicio: ancora < data ? ancora : data, fim: ancora < data ? data : ancora };
    } else {
      ancora = data;
      selecao = { inicio: data, fim: data };
    }
    diasMostrados = MAX_DIAS;
    marcarAtalho(null);
    render();
  });

  el.calAnterior.addEventListener('click', () => {
    mesVisivel = new Date(mesVisivel.getFullYear(), mesVisivel.getMonth() - 1, 1);
    renderCalendario();
  });
  el.calProximo.addEventListener('click', () => {
    mesVisivel = new Date(mesVisivel.getFullYear(), mesVisivel.getMonth() + 1, 1);
    renderCalendario();
  });

  function marcarAtalho(qual) {
    document.querySelectorAll('.cal-atalhos button').forEach(b => {
      b.classList.toggle('active', b.dataset.atalho === qual);
    });
  }

  document.querySelectorAll('.cal-atalhos button').forEach(botao => {
    botao.addEventListener('click', () => {
      const qual = botao.dataset.atalho;
      if (qual === 'tudo') {
        selecao = null;
      } else if (qual === 'ultimo-dia' && ultimaData) {
        selecao = { inicio: ultimaData, fim: ultimaData };
        ancora = ultimaData;
        mesVisivel = new Date(paraData(ultimaData).getFullYear(), paraData(ultimaData).getMonth(), 1);
      } else if (qual === 'semana' && ultimaData) {
        const fim = paraData(ultimaData);
        const inicio = new Date(fim.getFullYear(), fim.getMonth(), fim.getDate() - 6);
        selecao = { inicio: chaveDe(inicio), fim: chaveDe(fim) };
        mesVisivel = new Date(fim.getFullYear(), fim.getMonth(), 1);
      } else if (qual === 'mes') {
        const ano = mesVisivel.getFullYear(), mes = mesVisivel.getMonth();
        selecao = { inicio: chaveDe(new Date(ano, mes, 1)), fim: chaveDe(new Date(ano, mes + 1, 0)) };
      }
      diasMostrados = MAX_DIAS;
      marcarAtalho(qual);
      render();
    });
  });

  // --- lista -----------------------------------------------------------


  function tituloPeriodo() {
    if (!selecao) return 'Todo o período';
    if (selecao.inicio === selecao.fim) {
      const texto = fmtLongo.format(paraData(selecao.inicio));
      return texto.charAt(0).toUpperCase() + texto.slice(1);
    }
    return fmtCurto.format(paraData(selecao.inicio)) + ' — ' + fmtCurto.format(paraData(selecao.fim));
  }

  function compromissoHtml(ev) {
    const hora = formatarHora(ev.horario);
    const tituloTexto = esc(ev.titulo);
    return '<article class="compromisso">' +
      '<span class="hora' + (hora ? '' : ' sem') + '">' + (hora || '—') + '</span>' +
      '<span class="quem">' + esc(ev.autoridade) + '</span>' +
      '<span class="badge ' + (ev.nivel || 'sem') + '">' + esc(ev.nivel || 'sem leitura') + '</span>' +
      (ev.url
        ? '<a class="titulo" href="' + esc(ev.url) + '" target="_blank" rel="noopener">' + tituloTexto + '</a>'
        : '<span class="titulo">' + tituloTexto + '</span>') +
      (ev.local ? '<span class="local">' + ico('local') + esc(ev.local) + '</span>' : '') +
      (ev.justificativa ? '<p class="porque">' + esc(ev.justificativa) + '</p>' : '') +
    '</article>';
  }

  function pintar() {
    const itens = eventosVisiveis();
    renderKpis(el.kpis, itens, ['Compromissos', 'Alto impacto', 'Impacto médio', 'Sem efeito direto']);

    el.periodoTitulo.textContent = tituloPeriodo();
    const dias = new Set(itens.map(e => e.data)).size;
    el.periodoResumo.textContent = itens.length
      ? itens.length.toLocaleString('pt-BR') + (itens.length === 1 ? ' compromisso' : ' compromissos') +
        (dias > 1 ? ' · ' + dias + ' dias' : '')
      : '';

    const agrupado = new Map();
    for (const ev of itens) {
      if (!agrupado.has(ev.data)) agrupado.set(ev.data, []);
      agrupado.get(ev.data).push(ev);
    }
    const datas = Array.from(agrupado.keys()).sort().reverse();
    const visiveis = datas.slice(0, diasMostrados);

    if (!datas.length) {
      el.lista.innerHTML = '<div class="vazio">Nenhum compromisso neste período com os filtros atuais.<br>' +
        'Escolha outro dia no calendário ou use <strong>Todo o período</strong>.</div>';
      return;
    }

    let html = visiveis.map((data, i) => {
      const doDia = agrupado.get(data).slice().sort((a, b) => minutosDe(a.horario) - minutosDe(b.horario));
      const rotulo = fmtLongo.format(paraData(data));
      return '<section class="dia-bloco" style="--i:' + Math.min(i, 10) + '">' +
        '<div class="dia-rotulo">' + esc(rotulo.charAt(0).toUpperCase() + rotulo.slice(1)) + '</div>' +
        doDia.map(compromissoHtml).join('') +
      '</section>';
    }).join('');

    const restantes = datas.length - visiveis.length;
    if (restantes > 0) {
      html += '<div class="rodape-lista"><button id="maisDias">Carregar mais ' +
        restantes + (restantes === 1 ? ' dia' : ' dias') + '</button></div>';
    }
    el.lista.innerHTML = html;

    const maisBtn = document.getElementById('maisDias');
    if (maisBtn) maisBtn.addEventListener('click', () => { diasMostrados += MAX_DIAS; pintar(); });
  }

  function render() {
    renderCalendario();
    transicionar(pintar);
  }

  let debounce;
  el.busca.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(render, 140);
  });
  el.fAutoridade.addEventListener('change', render);
  document.querySelectorAll('.segmented').forEach(seg => {
    seg.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      seg.dataset.value = btn.dataset.v;
      seg.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === btn));
      render();
    });
  });
  el.limpar.addEventListener('click', () => {
    el.busca.value = '';
    el.fAutoridade.value = 'todos';
    el.fNivel.dataset.value = 'todos';
    el.fNivel.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.v === 'todos'));
    render();
  });

  atualizarContadorSalvos();
  renderCalendario();
  pintar();
})();
