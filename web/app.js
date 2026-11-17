/* F1 Dash — ecrãs do segundo monitor. Recebe os dados do servidor local (/stream) e desenha
   o ecrã certo para a sessão: corrida, qualificação ou treinos livres. */
/* global blocoCarro, corTempPneu, corDano */

const ecraEl = document.getElementById('ecra');
const palco = document.getElementById('palco');

// ------------------------------------------------------------------ definições guardadas
const def = carregarDef();
function carregarDef() {
  try {
    const d = JSON.parse(localStorage.getItem('f1dash') || '{}');
    return { ecra: d.ecra || 'auto', voltas: d.voltas || null, vista: d.vista || 'auto' };
  } catch (e) {
    return { ecra: 'auto', voltas: null, vista: 'auto' };
  }
}
function guardarDef() {
  try { localStorage.setItem('f1dash', JSON.stringify(def)); } catch (e) { /* sem armazenamento: fica só nesta sessão */ }
}

// ------------------------------------------------------------------ formatação
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtV = (ms) => (ms == null || ms <= 0) ? '—' : `${Math.floor(ms / 60000)}:${((ms % 60000) / 1000).toFixed(3).padStart(6, '0')}`;
const fmtS = (ms) => (ms == null || ms <= 0) ? '—' : (ms >= 60000 ? fmtV(ms) : (ms / 1000).toFixed(3));
const fmtD = (ms) => ms == null ? '—' : (ms < 0 ? '−' : '+') + (Math.abs(ms) / 1000).toFixed(3);
const fmtRel = (s) => (s < 0 ? '−' : '+') + Math.abs(s).toFixed(3);
const fmtRelogio = (seg) => {
  seg = Math.max(0, Math.round(seg || 0));
  const h = Math.floor(seg / 3600), m = Math.floor((seg % 3600) / 60), s = seg % 60;
  return (h ? h + ':' + String(m).padStart(2, '0') : String(m).padStart(2, '0')) + ':' + String(s).padStart(2, '0');
};
const TC = { S: '#FF3B3B', M: '#FFD12E', H: '#EDEDED', I: '#43D06B', W: '#3B8BFF', '?': '#98A2B3' };
const TN = { S: 'Macios', M: 'Médios', H: 'Duros', I: 'Intermédios', W: 'Chuva', '?': '—' };
const SETOR = { roxo: ['#B57BFF', '#221634'], verde: ['#3DDC84', '#0F2A1A'], amarelo: ['#F5C518', '#2A2410'], cinza: ['#3A4450', '#161B21'] };
const RODA = ['Trás esq.', 'Trás dir.', 'Frente esq.', 'Frente dir.'];
const pneu = (l, t = 20) => `<span class="pneu" style="width:${t}px;height:${t}px;border-color:${TC[l] || TC['?']};color:${TC[l] || TC['?']};font-size:${Math.round(t / 2)}px">${esc(l)}</span>`;
const pct = (v) => Math.max(0, Math.min(100, v || 0)) + '%';

// ------------------------------------------------------------------ peças comuns
function cabecalho(d, selo, cor, centro, pil) {
  const s = d.sessao;
  const [gp, circuito] = (s.pista || '').split(' · ');
  const prev = (s.previsao || []).map((p) => {
    const w = p.chuva >= 10 ? `Chuva ${p.chuva}%` : p.meteo;
    return `<div class="prev"><span class="f12 m">${p.min ? '+' + p.min + ' min' : 'Agora'}</span>
      <span class="f14 fw6" style="color:${p.chuva >= 10 ? '#4DA3FF' : '#F2F4F7'}">${esc(w)}</span></div>`;
  }).join('');
  return `<header class="cab">
    <div class="g14 row">
      <span class="selo" style="background:${cor}">${esc(selo)}</span>
      <div class="col"><span class="f22 fw7">${esc(gp)}</span><span class="f14 m">${esc(circuito || '')}</span></div>
    </div>
    <div class="cresce jc-c g14 row">${centro}</div>
    ${pil}
    <div class="g10 row">
      <div class="ai-e col"><span class="f16 fw6">Ar ${s.temp_ar}° · Pista ${s.temp_pista}°</span><span class="f13 m">${esc(s.meteo)}</span></div>
      ${prev}
    </div>
  </header>`;
}
function pilula(texto, cor, fundo, borda) {
  return `<span class="pilula" style="background:${fundo};border:1px solid ${borda};color:${cor}"><i style="background:${cor}"></i>${esc(texto)}</span>`;
}
function pilulaBandeira(d) {
  const sc = d.sessao.safety_car, b = d.eu.bandeira;
  if (d.sessao.bandeira_vermelha) return pilula('Bandeira vermelha', '#FF4D4D', '#2A1215', '#7A2228');
  if (sc === 1) return pilula('Safety Car', '#F5C518', '#2A2410', '#7A6410');
  if (sc === 2) return pilula('Virtual Safety Car', '#F5C518', '#2A2410', '#7A6410');
  if (sc === 3) return pilula('Volta de formação', '#98A2B3', '#161B21', '#2A333E');
  if (b === 3) return pilula('Bandeira amarela', '#F5C518', '#2A2410', '#7A6410');
  if (b === 2) return pilula('Bandeira azul', '#4DA3FF', '#0F1E2E', '#285E94');
  return pilula('Bandeira verde', '#3DDC84', '#0F2A1A', '#1F6B3D');
}
const ESTADOS = { 0: ['Na garagem', '#98A2B3', '#161B21', '#2A333E'], 1: ['Volta rápida', '#C9A0FF', '#221634', '#6B3FA8'],
  2: ['Volta de entrada', '#8CC4FF', '#0F1E2E', '#285E94'], 3: ['Volta de saída', '#8CC4FF', '#0F1E2E', '#285E94'], 4: ['Em pista', '#8CC4FF', '#0F1E2E', '#285E94'] };
function pilulaEstado(eu) { const e = ESTADOS[eu.estado_piloto] || ESTADOS[4]; return pilula(e[0], e[1], e[2], e[3]); }

function linhaPiloto(c, eu) {
  return `<span class="g7 mw0 row">${esc(c.codigo)}${c.eu ? `<span class="tu" style="background:${c.cor}">TU</span>` : ''}${c.penal ? `<span class="bg-ambar etq">+${c.penal}s</span>` : ''}${c.box ? '<span class="bg-azul etq">BOX</span>' : ''}</span>`;
}

function blocoCarroPainel(eu, titulo) {
  const b = blocoCarro(eu);
  return `<section class="pd14-18 g10 p" style="display:flex;flex-direction:column">
    <div class="row sb"><span class="l">${titulo}</span>
      <span class="g8 f16 row">${pneu(eu.composto)}${TN[eu.composto] || ''} · ${eu.idade ?? 0} voltas</span></div>
    ${b.html}
    <div class="cols3 g6 g">${b.chips}</div>
    <span class="f12 tc m">Peças: verde OK · amarelo/laranja dano · vermelho crítico — anel = vida do pneu · sup. | int. · T = travão</span>
  </section>`;
}

function grafico(series, w, h, rotulos) {
  const todos = series.flatMap((s) => s.v).filter((x) => x > 0);
  if (todos.length < 2) return `<div class="ai-c jc-c m" style="height:${h}px;display:flex">A recolher voltas…</div>`;
  let mn = Math.min(...todos), mx = Math.max(...todos);
  if (mx - mn < 400) { const c = (mx + mn) / 2; mn = c - 200; mx = c + 200; }
  const pts = (v) => v.map((x, i) => `${(10 + i * (w - 20) / Math.max(v.length - 1, 1)).toFixed(1)},${(15 + (x - mn) / (mx - mn) * (h - 30)).toFixed(1)}`).join(' ');
  const linhas = series.map((s) => `<polyline points="${pts(s.v)}" fill="none" stroke="${s.c}" stroke-width="${s.w || 2.5}" stroke-linejoin="round"></polyline>`).join('');
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(rotulos)}">
    <line x1="10" y1="15" x2="${w - 10}" y2="15" stroke="#232B35"></line><line x1="10" y1="${h / 2}" x2="${w - 10}" y2="${h / 2}" stroke="#232B35"></line>
    <line x1="10" y1="${h - 15}" x2="${w - 10}" y2="${h - 15}" stroke="#232B35"></line>${linhas}</svg>
    <div class="f13 row sb m"><span>Mais rápido ↑</span><span>${fmtV(mn)} – ${fmtV(mx)}</span></div>`;
}

// ------------------------------------------------------------------ CORRIDA
let modoTempos = 'me', autoTempos = true, ultimaTroca = Date.now();
let alturaUtil = 952;   // altura do ecrã abaixo do cabeçalho; encolhe quando aparece a barra de alertas
const MODOS = [['me', 'Para ti', 'Para ti'], ['leader', 'Líder', 'Ao líder'], ['interval', 'Intervalo', 'Interv.']];

function celulaTempo(c, eu, i) {
  if (modoTempos === 'leader') {
    if (c.pos === 1) return ['Líder', '#98A2B3'];
    return c.voltas_atras ? [`+${c.voltas_atras} V`, '#98A2B3'] : ['+' + (c.lider_ms / 1000).toFixed(3), '#F2F4F7'];
  }
  if (modoTempos === 'interval') {
    if (c.pos === 1) return ['Líder', '#98A2B3'];
    return ['+' + (c.frente_ms / 1000).toFixed(3), '#F2F4F7'];
  }
  if (c.eu) return ['—', '#98A2B3'];
  const dv = c.voltas_atras - eu.voltas_atras;
  if (dv) return [(dv > 0 ? '+' : '−') + Math.abs(dv) + ' V', '#98A2B3'];
  const s = (c.lider_ms - eu.lider_ms) / 1000;
  const perto = Math.abs(s) < 1;
  return [fmtRel(s), perto ? (s < 0 ? '#3DDC84' : '#FFB020') : '#F2F4F7'];
}

function renderCorrida(d) {
  const eu = d.eu, cr = d.corrida || {}, s = d.sessao;
  const meu = d.carros.find((c) => c.eu) || { voltas_atras: 0, lider_ms: 0 };
  const total = s.voltas_total || 0;
  const volta = Math.min(eu.volta, total || eu.volta);
  const colLabel = MODOS.find((m) => m[0] === modoTempos)[2];
  const n = d.carros.length;
  const alt = Math.max(28, Math.min(38, Math.floor((alturaUtil - 28 - 80) / Math.max(n, 1)) - 3));
  const linhas = d.carros.map((c, i) => {
    const [t, cor] = celulaTempo(c, meu, i);
    return `<div class="f18 tab" style="grid-template-columns:30px 6px minmax(0,1fr) 88px 66px 28px;height:${alt}px;background:${c.eu ? c.cor + '33' : 'transparent'};font-weight:${c.eu ? 700 : 500}">
      <span class="fw7 m">${c.pos}</span><span class="barra-eq" style="background:${c.cor}"></span>${linhaPiloto(c)}
      <span class="tr" style="color:${cor}">${t}</span>
      <span class="g6 row">${pneu(c.composto)}<span class="f15 m">${c.idade}</span></span>
      <span class="tr f15 m">${c.paragens}</span></div>`;
  }).join('');
  const aero = eu.aero || {};
  const regras26 = aero.regras_2026 !== 0;
  const nomeAjuda = regras26 ? 'Overtake' : 'DRS';
  const cartao = (v, frente) => {
    if (!v) return `<div class="pd16-22 p" ><span class="l">${frente ? 'Ninguém à frente' : 'Ninguém atrás'}</span></div>`;
    const dif = v.diferenca_volta;
    let tend = '';
    if (dif != null) {
      if (frente) tend = dif > 0 ? `▼ A recuperar ${dif.toFixed(2)} s/volta` : `▲ A perder ${Math.abs(dif).toFixed(2)} s/volta`;
      else tend = dif > 0 ? `▲ Aproxima-se ${dif.toFixed(2)} s/volta` : `▼ A afastar-se ${Math.abs(dif).toFixed(2)} s/volta`;
    }
    const corT = dif == null ? '#98A2B3' : (frente ? (dif > 0 ? '#3DDC84' : '#FFB020') : (dif > 0 ? '#FFB020' : '#3DDC84'));
    let ajuda = '';
    const aj = eu.ajuda;
    if (frente) ajuda = aj && aj.disp ? `${nomeAjuda} disponível` : v.gap_s < 1 ? `A menos de 1 s · ${nomeAjuda} na próxima deteção` : `${nomeAjuda} a ${(v.gap_s - 1).toFixed(3)} s`;
    else if (v.ajuda_disp) ajuda = `tem ${nomeAjuda} sobre ti`;
    const voltas = v.voltas_atras ? ` · ${v.voltas_atras} V` : '';
    return `<div class="pd16-22 g2 p col">
      <span class="l">${frente ? 'Carro à frente' : 'Carro atrás'} · P${v.pos}</span>
      <span class="f20"><b class="f24">${esc(v.codigo)}</b> <span class="m">· ${TN[v.composto] || '—'} · ${v.idade} voltas${voltas}</span></span>
      <span class="f56 fw7" style="line-height:1.05;color:${frente ? '#3DDC84' : '#FFB020'}">${v.gap_s.toFixed(3)} s</span>
      <span class="f15 fw6" style="color:${corT}">${tend || '&nbsp;'}</span>
      <span class="f15 m">${ajuda || '&nbsp;'}</span></div>`;
  };
  const ganho = (eu.grelha || 0) - eu.pos;
  const setores = (eu.setores_ultima || []).map((x, k) => {
    const [c, bg] = SETOR[x.cor] || SETOR.cinza;
    return `<div class="pd6-10 r6 col" style="background:${bg};border-top:3px solid ${c}"><span class="f13 fw6 m">S${k + 1} · última</span><span class="f22 fw7" style="color:${c}">${fmtS(x.ms)}</span></div>`;
  }).join('') || '<div class="m" style="grid-column:span 3;align-self:center">Setores aparecem no fim da primeira volta</div>';
  const vr = d.volta_rapida;
  const ritmoEu = eu.ritmo || [], ritmoF = cr.ritmo_frente || [];
  const janela = [];
  if (total) {
    for (let l = volta; l <= total; l++) {
      let c = '#232B35';
      if (l === volta) c = eu.cor;
      else if (s.box_ideal && l >= s.box_ideal && l <= (s.box_ultima || s.box_ideal)) c = '#3DDC84';
      else if (s.box_ultima && l > s.box_ultima && l <= s.box_ultima + 2) c = '#FFB020';
      janela.push(`<span class="cresce h12 r2" style="background:${c}"></span>`);
    }
  }
  const dn = eu.danos || {};
  const pu = [['Motor (ICE)', dn.ice], ['MGU-K', dn.mguk], ['Bateria (ES)', dn.es], ['Eletrónica (CE)', dn.ce], ['Turbo (TC)', dn.tc], ['Caixa', dn.caixa]];
  if (!regras26) pu.splice(2, 0, ['MGU-H', dn.mguh]);
  const corPU = (v) => v >= 60 ? '#FF4D4D' : v >= 40 ? '#FFB020' : '#3DDC84';
  const falhas = [dn.falha_ers && 'ERS', dn.falha_drs && 'DRS', dn.motor_partido && 'motor partido', dn.motor_gripado && 'motor gripado'].filter(Boolean);
  const modoERS = { 0: 'Desligado', 1: 'Médio', 2: 'Hotlap', 3: 'Boost' }[eu.ers_modo] || '—';
  let aeroTxt = '—', aeroCor = '#98A2B3';
  if (regras26 && eu.aero) {
    if (aero.modo === 1) { aeroTxt = 'Modo reta ativo'; aeroCor = '#3DDC84'; }
    else if (aero.disp) { aeroTxt = 'Modo reta disponível'; aeroCor = '#3DDC84'; }
    else if (aero.dist) { aeroTxt = `Modo reta em ${aero.dist} m`; aeroCor = '#F2F4F7'; }
    else aeroTxt = 'Modo curva';
  }
  const margem = eu.margem_voltas;
  const vidaJogo = eu.vida_fonte === 'do jogo';
  const vidaTxt = eu.vida_restante_voltas != null ? `${vidaJogo ? '' : '~'}${eu.vida_restante_voltas} voltas` : 'a calcular…';
  const reent = cr.reentrada;
  const corT = (x) => x > 125 ? '#FF4D4D' : x > 115 ? '#FFB020' : '#F2F4F7';
  return `${cabecalho(d, s.nome, eu.cor, `
      <span class="l">Volta</span><span class="f44 fw7 lh1">${volta}</span><span class="f24 m">/ ${total || '—'}</span>
      <div class="w260 barra" style="margin-left:12px"><div style="width:${total ? pct(volta / total * 100) : '0%'};background:${eu.cor}"></div></div>
      <span style="margin-left:8px" class="f16 m">${total ? `Faltam ${Math.max(total - volta, 0)} voltas` : ''}</span>`, pilulaBandeira(d))}
  <div class="cresce mh0 g16" style="display:grid;grid-template-columns:420px minmax(0,1fr) 470px">
    <section class="pd14-10 g3 mh0 oh p col">
      <div class="g6 row" style="padding:0 4px 8px">
        <span class="l" style="margin-right:auto">Tempos</span>
        ${MODOS.map((m) => `<button type="button" class="modo${modoTempos === m[0] ? ' on' : ''}" data-modo="${m[0]}">${m[1]}</button>`).join('')}
        <button type="button" class="f13 modo" data-auto="1" style="color:${autoTempos ? '#3DDC84' : '#98A2B3'}">Auto ${autoTempos ? '●' : '○'}</button>
      </div>
      <div class="pb6 bb tab" style="grid-template-columns:30px 6px minmax(0,1fr) 88px 66px 28px;border-radius:0">
        <span class="l">P</span><span></span><span class="l">Piloto</span><span class="tr l">${colLabel}</span><span class="l">Pneu</span><span class="tr l">Box</span></div>
      ${linhas}
    </section>

    <div class="g16 mh0 col">
      <div class="g16 g" style="grid-template-columns:minmax(0,1fr) 190px minmax(0,1fr)">
        ${cartao(cr.frente, true)}
        <div class="pd14 ai-c jc-c p col" style="border-color:${eu.cor}">
          <span class="l">Posição</span><span class="f88 fw7 lh1" style="color:${eu.cor}">P${eu.pos}</span>
          <span class="f15 m">Partida P${eu.grelha || '—'} · <span class="fw6" style="color:${ganho >= 0 ? '#3DDC84' : '#FF4D4D'}">${ganho >= 0 ? '+' : '−'}${Math.abs(ganho)}</span></span>
          <span class="f15 m">Ao líder <b class="c-claro">${eu.pos === 1 ? '—' : meu.voltas_atras ? `+${meu.voltas_atras} V` : '+' + (meu.lider_ms / 1000).toFixed(3)}</b></span>
        </div>
        ${cartao(cr.atras, false)}
      </div>
      <div class="pd14-20 g12 p g" style="grid-template-columns:repeat(4,minmax(0,1fr)) repeat(3,minmax(0,.72fr));align-items:end">
        <div class="col"><span class="l">Volta atual</span><span class="f30 fw7">${fmtV(eu.atual_ms)}</span>
          <span class="f14 fw6" style="color:${eu.delta_ms == null ? '#98A2B3' : eu.delta_ms <= 0 ? '#3DDC84' : '#FF4D4D'}">${eu.delta_ms == null ? (eu.invalida ? 'Volta inválida' : '—') : fmtD(eu.delta_ms) + ' vs melhor'}</span></div>
        <div class="col"><span class="l">Última</span><span class="f30 fw7">${fmtV(eu.ultima_ms)}</span><span class="f14 m">${eu.ultima_ms && eu.melhor_ms ? fmtD(eu.ultima_ms - eu.melhor_ms) + ' vs melhor' : '&nbsp;'}</span></div>
        <div class="col"><span class="l">Melhor</span><span class="f30 fw7 c-verde">${fmtV(eu.melhor_ms)}</span><span class="f14 m">${eu.melhor_volta_num ? 'Volta ' + eu.melhor_volta_num : '&nbsp;'}</span></div>
        <div class="col"><span class="l">Mais rápida</span><span class="f30 fw7 c-roxo">${vr ? fmtV(vr.ms) : '—'}</span><span class="f14 m">${vr ? esc(vr.codigo) + (vr.volta ? ' · volta ' + vr.volta : '') : '&nbsp;'}</span></div>
        ${setores}
      </div>
      <div class="cresce mh0 g16" style="display:grid;grid-template-columns:440px minmax(0,1fr)">
        ${blocoCarroPainel(eu, 'Carro')}
        <section class="pd16-22 g10 mw0 p col">
          <div class="row sb"><span class="l">Ritmo · últimas voltas</span>
            <span class="g14 f14 row"><span class="g6 row"><span class="w14 h3" style="background:${eu.cor}"></span>Tu</span>${cr.frente ? `<span class="g6 row"><span class="w14 h3 bg-dim"></span>${esc(cr.frente.codigo)} (à frente)</span>` : ''}</span></div>
          <div class="cresce mh0 col">${grafico([{ v: ritmoF, c: '#98A2B3' }, { v: ritmoEu, c: eu.cor, w: 3.5 }], 450, 300, 'Tempos por volta: o teu ritmo e o do carro da frente')}</div>
          <div class="cols3 g10 g">
            <div class="cx"><span class="f13 m">Tu · média 5 voltas</span><span class="f22 fw7" style="color:${eu.cor}">${fmtV(cr.meu_ritmo_ms)}</span></div>
            <div class="cx"><span class="f13 m">${cr.frente ? esc(cr.frente.codigo) + ' · à frente' : 'À frente'}</span><span class="f22 fw7">${fmtV(cr.frente && cr.frente.ritmo_ms)}</span></div>
            <div class="cx"><span class="f13 m">${cr.atras ? esc(cr.atras.codigo) + ' · atrás' : 'Atrás'}</span><span class="f22 fw7 c-ambar">${fmtV(cr.atras && cr.atras.ritmo_ms)}</span></div>
          </div>
        </section>
      </div>
    </div>

    <div class="g16 mh0 col">
      <section class="pd16-22 g9 p col">
        <span class="l">Estratégia</span>
        <div class="ai-b row sb"><span class="f17 m">Janela ideal de box</span>
          <span class="f30 fw7" style="color:${eu.cor}">${s.box_ideal ? `V${s.box_ideal} – V${s.box_ultima || s.box_ideal}` : '—'}</span></div>
        <div class="g3 row" aria-hidden="true">${janela.join('')}</div>
        <div class="f13 row sb m"><span>V${volta} (agora)</span><span>V${total}</span></div>
        ${s.chuva ? `<div class="f15 fw6 c-azul">Chuva ${s.chuva.chuva}% daqui a ${s.chuva.min} min — pensa nos intermédios</div>` : ''}
        ${cartaoPlano(cr.plano)}
        <div class="cols2 g10 g">
          <div class="cx"><span class="f13 m">Se parares agora</span><span class="f21 fw7">${reent ? 'Sais em P' + reent.pos : '—'}</span><span class="f14 m">${reent && reent.atras_de ? 'atrás de ' + esc(reent.atras_de) : ''}</span></div>
          <div class="cx"><span class="f13 m">${vidaJogo ? `Pneus · vida útil ${eu.vida_total_voltas}` : 'Vida dos pneus (até 70%)'}</span><span class="f21 fw7">${vidaTxt}</span><span class="f14 m">${[eu.pneu_limite != null ? RODA[eu.pneu_limite] + ' limita' : '', eu.desgaste_fonte && eu.desgaste_fonte !== 'esta sessão' ? esc(eu.desgaste_fonte) : ''].filter(Boolean).join(' · ')}</span></div>
        </div>
      </section>
      <section class="pd16-22 g10 p col">
        <div class="ai-b row sb"><span class="l">Unidade motriz · desgaste</span><span class="f15 m">Temp. motor <b class="f22" style="color:${corT(eu.motor_temp)}">${eu.motor_temp ?? '—'}°</b></span></div>
        <div class="cols3 g" style="column-gap:18px;row-gap:10px">
          ${pu.map(([nm, v]) => `<div class="g4 col"><div class="f15 row sb"><span class="m">${nm}</span><span class="fw7" style="color:${corPU(v || 0)}">${v ?? 0}%</span></div><div class="h5 barra"><div style="width:${pct(Math.max(v || 0, 1))};background:${corPU(v || 0)}"></div></div></div>`).join('')}
        </div>
        <span class="f14" style="color:${falhas.length ? '#FF4D4D' : '#98A2B3'}">${falhas.length ? 'Falha: ' + falhas.join(', ') : 'Falhas: nenhuma · motor e ERS OK'}</span>
      </section>
      <section class="pd16-22 g10 p col">
        <span class="l">Energia e combustível</span>
        <div class="ai-b row sb"><span class="f16 m">Bateria ERS · modo <b class="c-claro">${modoERS}</b></span><span class="f28 fw7 c-azul">${eu.ers_pct ?? '—'}%</span></div>
        <div class="h12 barra"><div class="bg-azul" style="width:${pct(eu.ers_pct)}"></div></div>
        <span class="f14 m">Recuperado nesta volta ${eu.ers_rec_mj ?? '—'} MJ · usado ${eu.ers_usado_mj ?? '—'} MJ${eu.ers_limite_mj ? ' · limite ' + eu.ers_limite_mj + ' MJ' : ''}</span>
        <div class="cols2 g10 g">
          <div class="cx"><span class="f13 m">${regras26 ? 'Aero ativa' : 'DRS'}</span><span class="f17 fw7" style="color:${aeroCor}">${regras26 ? aeroTxt : (eu.ajuda && eu.ajuda.disp ? 'Disponível' : eu.ajuda && eu.ajuda.dist ? `Em ${eu.ajuda.dist} m` : 'Indisponível')}</span>
            ${regras26 && aero.ovtk_ativo ? '<span class="f13 c-verde">Overtake ativo</span>' : ''}</div>
          <div class="cx"><span class="f13 m">Combustível</span><span class="f19 fw7" style="color:${margem == null ? '#F2F4F7' : margem >= 0 ? '#3DDC84' : '#FF4D4D'}">${margem == null ? '—' : (margem >= 0 ? '+' : '') + margem.toFixed(2) + ' voltas'}</span>
            <span class="f13 m">${eu.combustivel ?? '—'} kg no tanque</span></div>
        </div>
      </section>
      <section class="cresce mh0 pd16-22 g8 oh p col">
        <span class="l">Direção de corrida</span>
        ${(d.mensagens || []).map((m) => `<div class="g10 ai-c f16 g" style="grid-template-columns:42px 8px minmax(0,1fr)"><span class="fw6 m">V${m.volta}</span><span class="w8 h8 redondo" style="background:${m.cor}"></span><span>${esc(m.texto)}</span></div>`).join('') || '<span class="m">Sem mensagens</span>'}
      </section>
    </div>
  </div>`;
}

// ------------------------------------------------------------------ QUALIFICAÇÃO
function renderQuali(d) {
  const eu = d.eu, q = d.quali || {}, s = d.sessao;
  const porIdx = Object.fromEntries(d.carros.map((c) => [c.idx, c]));
  const ordem = (q.ordem || []).map((i) => porIdx[i]).filter(Boolean);
  const pole = q.pole_ms;
  const cores = { 0: '#3A4450', 1: '#B57BFF', 2: '#4DA3FF', 3: '#4DA3FF', 4: '#4DA3FF' };
  const alt = Math.max(30, Math.min(46, Math.floor((alturaUtil - 28 - 110) / Math.max(ordem.length, 1)) - 6));
  const linhas = ordem.map((c, k) => {
    const fora = q.corte && k >= q.corte;
    const corte = q.corte && k === q.corte ? `<div class="g10 pd4-8 row"><span class="cresce h2 bg-verm"></span><span class="f13 fw7 c-verm2" style="letter-spacing:.1em">LINHA DE CORTE · ${fmtV(q.corte_ms)}</span><span class="cresce h2 bg-verm"></span></div>` : '';
    return `${corte}<div class="f19 tab" style="grid-template-columns:30px 6px minmax(0,1fr) 98px 74px 14px;height:${alt}px;background:${c.eu ? c.cor + '33' : fora ? '#2A1215' : 'transparent'};font-weight:${c.eu ? 700 : 500}">
      <span class="fw7" style="color:${fora ? '#FF7A7A' : '#98A2B3'}">${k + 1}</span><span class="barra-eq" style="background:${c.cor}"></span>${linhaPiloto(c)}
      <span class="tr" style="color:${k === 0 ? '#B57BFF' : '#F2F4F7'}">${fmtV(c.melhor_ms)}</span>
      <span class="tr f16 m">${k === 0 || !c.melhor_ms || !pole ? '—' : fmtD(c.melhor_ms - pole)}</span>
      <span class="w10 h10 redondo" style="background:${cores[c.estado_piloto] || '#3A4450'}"></span></div>`;
  }).join('');
  const delta = eu.delta_ms;
  const deltaCor = delta == null ? '#98A2B3' : delta <= 0 ? '#3DDC84' : '#FF4D4D';
  const larg = delta == null ? 0 : Math.min(Math.abs(delta) / 1000, 1) * 50;
  const N = 8;
  const mini = eu.mini || [];
  const melhorSet = eu.melhor_setores || [];
  const atuais = [eu.s1_ms, eu.s2_ms, null];
  const secs = [0, 1, 2].map((k) => {
    const blocos = mini.slice(k * N, k * N + N).map((c) => `<span class="cresce h26 r3" style="background:${(SETOR[c] || SETOR.cinza)[0]}"></span>`).join('');
    const emPista = eu.estado_piloto > 0;
    const feito = emPista && atuais[k] && eu.setor > k;
    const ref = melhorSet[k];
    const cor = feito ? (ref && atuais[k] <= ref ? '#3DDC84' : '#F5C518') : (emPista && eu.setor === k ? '#F2F4F7' : '#98A2B3');
    return `<div class="g8 col"><div class="g3 row">${blocos}</div>
      <div class="ai-b row sb"><span class="f15 fw6 m">Setor ${k + 1}</span><span class="f28 fw7" style="color:${cor}">${feito ? fmtS(atuais[k]) : emPista && eu.setor === k ? 'em curso' : '—'}</span></div>
      <span class="f14 m">${ref ? 'Referência ' + fmtS(ref) + (feito ? ' · ' + fmtD(atuais[k] - ref) : '') : 'Sem referência ainda'}</span></div>`;
  }).join('');
  const prevPos = q.previsao_pos;
  const passa = q.corte ? (prevPos && prevPos <= q.corte ? 'passas o corte' : 'abaixo do corte') : '';
  const tent = q.tentativa || {};
  const traf = (q.trafego || []).map((t) => `<div class="g12 ai-c pd10-12 r6 bg-cx g" style="grid-template-columns:74px minmax(0,1fr) auto;border-left:4px solid ${t.alerta ? '#FFB020' : '#3A4450'}">
      <span class="f22 fw7">${esc(t.codigo)}</span><div class="col"><span class="f16">${t.frente ? 'À frente' : 'Atrás'} · ${esc(t.estado)}</span>
      <span class="f14 fw6" style="color:${t.alerta ? '#FFB020' : '#98A2B3'}">${esc(t.nota || 'Sem impacto nesta volta')}</span></div><span class="f22 fw7">${t.gap_s} s</span></div>`).join('') || (eu.estado_piloto === 0 ? '<span class="m">Estás na garagem</span>' : '<span class="m">Pista livre à tua volta</span>');
  const sup = eu.pneus_sup || [0, 0, 0, 0];
  const corAlvo = (t) => t < 90 ? '#4DA3FF' : t <= 105 ? '#3DDC84' : '#FF4D4D';
  const ordemR = [2, 3, 0, 1];
  const frio = ordemR.filter((k) => sup[k] < 90).map((k) => RODA[k].toLowerCase());
  const conj = (q.conjuntos || []).map((c) => `<div class="g12 ai-c g" style="grid-template-columns:26px minmax(0,1fr) auto;padding:6px 0;border-bottom:1px solid #1B222A">
      ${pneu(c.composto, 24)}<span class="f17">${TN[c.composto]} ${c.novo ? 'novos' : `usados · ${c.desgaste}%`}</span><span class="f17 fw6" style="color:${c.novo && c.composto === 'S' ? '#3DDC84' : '#F2F4F7'}">×${c.qtd}</span></div>`).join('') || '<span class="m">Sem dados de pneus ainda</span>';
  const elim = q.corte ? `eliminados P${q.corte + 1}–P${ordem.length}` : '';
  return `${cabecalho(d, 'Qualificação', eu.cor, `
      <span class="f22 fw7 pd6-12 r6 bg-claro c-escuro">${esc(s.nome)}</span>
      <span class="f48 fw7 lh1">${fmtRelogio(s.restante)}</span>
      <span class="f16 m">restantes${elim ? ' · ' + elim : ''}</span>`, pilulaEstado(eu))}
  <div class="cresce mh0 g16" style="display:grid;grid-template-columns:440px minmax(0,1fr) 480px">
    <section class="pd14-12 g6 mh0 oh p col">
      <div class="pb6 bb tab" style="grid-template-columns:30px 6px minmax(0,1fr) 98px 74px 14px;border-radius:0">
        <span class="l">P</span><span></span><span class="l">Piloto</span><span class="tr l">Melhor</span><span class="tr l">Dif.</span><span></span></div>
      ${linhas}
      <div class="mt-auto g16 f13 bt row m" style="padding:8px 8px 0">
        <span class="g6 row"><span class="w10 h10 redondo bg-roxo"></span>Volta rápida</span>
        <span class="g6 row"><span class="w10 h10 redondo bg-azul"></span>Saída/entrada</span>
        <span class="g6 row"><span class="w10 h10 redondo bg-cinza"></span>Garagem</span></div>
    </section>

    <div class="g16 mh0 col">
      <div class="cresce mh0 pd22-28 g24 ai-c p g" style="grid-template-columns:minmax(0,1fr) 300px">
        <div class="g6 col">
          <span class="l">Delta ao teu melhor tempo${eu.referencia_origem && eu.referencia_origem !== s.nome ? ' · referência da ' + esc(eu.referencia_origem) : ''}</span>
          ${delta == null ? `<span class="f44 fw7 c-dim" style="line-height:1.1">${eu.melhor_ms ? 'À espera da volta rápida' : 'Ainda sem volta de referência'}</span>` : `<span class="f150 fw7" style="line-height:.95;color:${deltaCor}">${fmtD(delta)}</span>`}
          <div class="h10 bg-linha r5" style="position:relative;margin-top:6px">
            <span class="abs w2 h18 bg-dim" style="left:50%;top:-4px"></span>
            <span class="abs r5" style="${delta != null && delta <= 0 ? 'right:50%' : 'left:50%'};width:${larg}%;height:100%;background:${deltaCor}"></span></div>
          <div class="f13 row sb m"><span>−1.0 s mais rápido</span><span>+1.0 s mais lento</span></div>
        </div>
        <div class="g12 col" style="border-left:1px solid #232B35;padding-left:24px">
          <div class="col"><span class="l">Previsão de volta</span><span class="f44 fw7">${fmtV(eu.previsao_ms)}</span>
            <span class="f17 fw6" style="color:${passa === 'abaixo do corte' ? '#FF7A7A' : '#3DDC84'}">${prevPos ? `→ P${prevPos}${passa ? ' · ' + passa : ''}` : ''}</span></div>
          <div class="col"><span class="l">Tempo de volta</span><span class="f30 fw6">${fmtV(eu.atual_ms)}</span></div>
        </div>
      </div>
      <div class="pd18-22 g14 p col">
        <div class="row sb"><span class="l">Mini-setores · volta atual</span>
          <span class="g14 f13 row m">
            <span class="g6 row"><span class="w14 h8 bg-roxo r2"></span>Melhor sessão</span>
            <span class="g6 row"><span class="w14 h8 bg-verde r2"></span>Melhor pessoal</span>
            <span class="g6 row"><span class="w14 h8 bg-amarelo r2"></span>Mais lento</span></span></div>
        <div class="cols3 g14 g">${secs}</div>
      </div>
      <div class="cols4 g16" style="display:grid">
        <div class="pd18-20 g4 p col"><span class="l">Melhor volta</span><span class="f36 fw7">${fmtV(eu.melhor_ms)}</span><span class="f15 m">P${(ordem.findIndex((c) => c.eu) + 1) || '—'} · ${TN[eu.composto] || ''}</span></div>
        <div class="pd18-20 g4 p col"><span class="l">Volta ideal</span><span class="f36 fw7 c-verde">${fmtV(q.ideal_ms)}</span><span class="f15 m">Soma dos teus melhores setores</span></div>
        <div class="pd18-20 g4 p col"><span class="l">Margem ao corte</span><span class="f36 fw7" style="color:${q.margem_ms == null ? '#98A2B3' : q.margem_ms > 0 ? '#FFB020' : '#FF4D4D'}">${q.margem_ms == null ? '—' : (q.margem_ms / 1000).toFixed(3) + ' s'}</span><span class="f15 m">${q.corte_seguinte ? (q.margem_ms >= 0 ? 'Acima' : 'Abaixo') + ' de P' + (q.corte + 1) + ' (' + esc(q.corte_seguinte) + ')' : 'Sem eliminação nesta sessão'}</span></div>
        <div class="pd18-20 g4 p col"><span class="l">Para a pole</span><span class="f36 fw7 c-roxo">${pole && eu.melhor_ms ? fmtD(eu.melhor_ms - pole) : '—'}</span><span class="f15 m">${esc(q.pole_codigo || '')} · ${fmtV(pole)}</span></div>
      </div>
      <div class="pd16-22 cols3 g24 p g">
        <div class="g6 col"><div class="ai-b row sb"><span class="l">Bateria ERS</span><span class="f24 fw7 c-azul">${eu.ers_pct ?? '—'}%</span></div>
          <div class="h12 barra"><div class="bg-azul" style="width:${pct(eu.ers_pct)}"></div></div>
          <span class="f15 m">Modo: <b class="c-claro">${{ 0: 'Desligado', 1: 'Médio', 2: 'Hotlap', 3: 'Boost' }[eu.ers_modo] || '—'}</b></span></div>
        <div class="g4 col"><span class="l">Combustível</span><span class="f24 fw7">${eu.combustivel ?? '—'} kg</span><span class="f15 m">Dá para ${eu.margem_voltas != null ? eu.margem_voltas.toFixed(1) : '—'} voltas</span></div>
        <div class="g4 col"><span class="l">Speed trap</span><span class="f24 fw7">${eu.speed_trap || '—'} km/h</span><span class="f15 m">Melhor da sessão ${Math.max(...d.carros.map((c) => c.speed_trap || 0)) || '—'} km/h</span></div>
      </div>
    </div>

    <div class="g16 mh0 col">
      <section class="pd18-22 g10 p col">
        <span class="l">Tempo e tentativas</span>
        <div class="g14 r8 pd12-14 row" style="background:${tent.ok ? '#0F2A1A' : '#2A1215'};border:1px solid ${tent.ok ? '#1F6B3D' : '#7A2228'}">
          <span class="w12 h12 redondo fixo" style="background:${tent.ok ? '#3DDC84' : '#FF4D4D'}"></span>
          <div class="col"><span class="f20 fw7">${tent.ok ? 'Ainda dá para mais 1 tentativa' : 'Já não dá para outra tentativa'}</span>
            <span class="f15 m">${tent.ok ? 'Sai do box até faltarem ' + fmtRelogio((tent.sair_ate_ms || 0) / 1000) : 'Aproveita esta volta'}</span></div></div>
        <div class="cols3 g8 f14 g m">
          <span>Volta saída<br><b class="f20 c-claro">${fmtRelogio((q.saida_ms || 0) / 1000)}</b></span>
          <span>Volta rápida<br><b class="f20 c-claro">${fmtRelogio((eu.melhor_ms || 0) / 1000)}</b></span>
          <span>Volta entrada<br><b class="f20 c-claro">${fmtRelogio((q.entrada_ms || 0) / 1000)}</b></span>
          ${q.tempos_box_fonte && q.tempos_box_fonte !== 'do jogo' ? `<span class="f13" style="grid-column:1/-1">Saída e entrada ${esc(q.tempos_box_fonte)}</span>` : ''}</div>
      </section>
      <section class="pd18-22 g10 p col"><span class="l">Tráfego na pista</span>${traf}</section>
      <section class="pd18-22 g10 p col">
        <span class="l">Temperatura dos pneus · alvo 90–105°</span>
        <div class="cols2 g10 g">
          ${ordemR.map((k) => `<div class="pd10-12 r6 bg-cx row sb" style="border:1px solid ${corAlvo(sup[k])}"><span class="f15 m">${RODA[k]}</span><span class="f26 fw7" style="color:${corAlvo(sup[k])}">${sup[k]}°</span></div>`).join('')}
        </div>
        <span class="f15 fw6" style="color:${frio.length ? '#4DA3FF' : '#3DDC84'}">${frio.length ? 'Fria: ' + frio.join(', ') + ' — aquece antes da volta' : 'Todos os pneus na janela'}</span>
      </section>
      <section class="cresce mh0 pd18-22 g8 oh p col"><span class="l">Conjuntos de pneus</span>${conj}</section>
    </div>
  </div>`;
}

// ------------------------------------------------------------------ TREINOS
function renderTreinos(d) {
  const eu = d.eu, t = d.treinos || {}, s = d.sessao;
  const prog = t.programa || [];
  const ativo = prog.findIndex((p) => !p.feito);
  const tarefas = prog.map((p, k) => {
    const on = k === ativo;
    return `<div class="tarefa" style="background:${on ? eu.cor + '1F' : 'transparent'};border-color:${on ? eu.cor : '#1B222A'}">
      <span class="w26 h26 redondo ai-c jc-c" style="display:inline-flex;background:${p.feito ? '#3DDC84' : 'transparent'};border:2px solid ${p.feito ? '#3DDC84' : on ? eu.cor : '#3A4450'};box-sizing:border-box">
        ${p.feito ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0A0C0F" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg>' : ''}</span>
      <div class="g2 col">
        <span class="f18 fw6" style="color:${p.feito ? '#98A2B3' : '#F2F4F7'}">${esc(p.nome)}</span>
        <span class="f14" style="color:${p.feito ? '#3DDC84' : '#98A2B3'}">${esc(p.detalhe)}</span>
        ${!p.feito && p.progresso > 0 ? `<div class="barra" style="margin-top:4px"><div style="width:${pct(p.progresso * 100)};background:${on ? eu.cor : '#98A2B3'}"></div></div>` : ''}
      </div></div>`;
  }).join('') || '<span class="m">À espera das primeiras voltas</span>';
  const stints = (t.stints || []).map((x, k) => `<div class="g8 ai-c f18 g" style="grid-template-columns:24px 40px 50px minmax(0,1fr) minmax(0,1fr);padding:6px 0;border-bottom:1px solid #1B222A">
      <span class="m">${k + 1}</span>${pneu(x.composto, 22)}<span>${x.voltas}</span><span class="tr">${fmtV(x.melhor_ms)}</span><span class="tr">${fmtV(x.media_ms)}</span></div>`).join('') || '<span class="m">Ainda sem stints</span>';
  const lg = t.longo;
  let longo = '<div class="m" style="margin:auto">Faz pelo menos 2 voltas seguidas no mesmo pneu para ver o ritmo de corrida</div>';
  if (lg) {
    lg.voltas = lg.voltas.slice(-10);
    const todos = lg.voltas.concat(lg.projecao);
    const mn = Math.min(...todos), mx = Math.max(...todos);
    const base = mn - 300;
    const h = (v) => Math.round(50 + (v - base) / Math.max(mx - base, 1) * 380);
    const barras = lg.voltas.map((v, k) => [v, true, k + 1]).concat(lg.projecao.map((v, k) => [v, false, lg.voltas.length + k + 1]))
      .map(([v, real, n]) => `<div class="cresce mw0 ai-c g8 jc-e col" style="height:100%">
        <span class="fw6" style="font-size:${lg.voltas.length > 8 ? 13 : 16}px;color:${real ? '#F2F4F7' : '#98A2B3'}">${fmtV(v)}</span>
        <div style="width:100%;height:${h(v)}px;background:${real ? eu.cor : 'transparent'};border:2px ${real ? 'solid' : 'dashed'} ${real ? eu.cor : '#98A2B3'};box-sizing:border-box;border-radius:6px 6px 2px 2px"></div>
        <span class="f14 m">V${n}</span></div>`).join('');
    longo = `<div class="cols4 g16 g">
        <div class="col"><span class="l">Média</span><span class="f40 fw7">${fmtV(lg.media_ms)}</span></div>
        <div class="col"><span class="l">Degradação</span><span class="f40 fw7 c-ambar">${fmtD(lg.degradacao_ms)} s</span><span class="f14 m">por volta</span></div>
        <div class="col"><span class="l">Consistência</span><span class="f40 fw7" style="color:${lg.consistencia_ms < 200 ? '#3DDC84' : '#FFB020'}">±${(lg.consistencia_ms / 1000).toFixed(2)} s</span><span class="f14 m">desvio padrão</span></div>
        <div class="col"><span class="l">Melhor do stint</span><span class="f40 fw7">${fmtV(lg.melhor_ms)}</span><span class="f14 m">volta ${lg.melhor_volta}</span></div></div>
      <div class="cresce mh0 ai-e bt" style="display:flex;gap:${lg.voltas.length > 8 ? 8 : 14}px;padding-top:12px" role="img" aria-label="Tempos por volta do stint atual e projeção das próximas 3 voltas">${barras}</div>
      <span class="f14 m">Barra mais alta = volta mais lenta · tracejado = projeção pela degradação</span>`;
  }
  const set = t.setores || [];
  const piorK = set.reduce((a, x, k) => (x.meu && x.melhor && (a < 0 || x.meu - x.melhor > set[a].meu - set[a].melhor) ? k : a), -1);
  const cmp = set.map((x, k) => {
    const dlt = x.meu && x.melhor ? x.meu - x.melhor : null;
    const c = dlt == null ? '#98A2B3' : dlt <= 0 ? '#B57BFF' : k === piorK ? '#FFB020' : '#F5C518';
    return `<div class="bg-cx r8 pd12-14 g2 col" style="border-top:3px solid ${c}">
      <span class="f14 fw6 m">Setor ${k + 1}</span><span class="f30 fw7" style="color:${c}">${dlt == null ? '—' : fmtD(dlt)}</span>
      <span class="f14 m">${dlt != null && dlt <= 0 ? 'Melhor da sessão · ' + fmtS(x.meu) : `Tu ${fmtS(x.meu)} · melhor ${fmtS(x.melhor)}`}</span></div>`;
  }).join('');
  const trapMelhor = t.speed_trap_melhor;
  const des = (eu.danos || {}).desgaste || [0, 0, 0, 0];
  const taxa = eu.desgaste_volta;
  const ordemR = [2, 3, 0, 1];
  const desg = ordemR.map((k) => {
    const r = taxa ? taxa[k] : null;
    const pior = eu.pneu_limite === k;
    return `<div class="bg-cx r6 pd10-12 g4 col" style="border:1px solid ${pior ? '#7A5410' : '#232B35'}">
      <div class="ai-b row sb"><span class="f14 m">${RODA[k]}</span><span class="f14 m">agora ${Math.round(des[k])}%</span></div>
      <span class="f26 fw7" style="color:${pior ? '#FFB020' : '#F2F4F7'}">${r == null ? '—' : r.toFixed(1) + '%'}<span class="f15 fw5 c-dim"> /volta</span></span></div>`;
  }).join('');
  const voltasCorrida = def.voltas || s.voltas_corrida || null;
  const fonteVoltas = def.voltas ? 'definido por ti' : (s.voltas_corrida_fonte || '');
  const consumo = eu.consumo_volta;
  const total = consumo && voltasCorrida ? (consumo * (voltasCorrida + 1)).toFixed(1) : null;
  const tabela = d.carros.filter((c) => c.melhor_ms).sort((a, b) => a.melhor_ms - b.melhor_ms);
  const melhor = tabela[0] ? tabela[0].melhor_ms : null;
  const minhaPos = tabela.findIndex((c) => c.eu);
  const visiveis = tabela.slice(0, 10);
  if (minhaPos >= 10) visiveis.push(tabela[minhaPos]);
  const linhasTab = visiveis.map((c) => `<div class="h36 f18 tab" style="grid-template-columns:30px 6px minmax(0,1fr) 96px 70px;background:${c.eu ? c.cor + '33' : 'transparent'};font-weight:${c.eu ? 700 : 500}">
      <span class="fw7 m">${tabela.indexOf(c) + 1}</span><span class="barra-eq" style="background:${c.cor}"></span>${linhaPiloto(c)}
      <span class="tr" style="color:${c.melhor_ms === melhor ? '#B57BFF' : '#F2F4F7'}">${fmtV(c.melhor_ms)}</span><span class="tr f15 m">${c.melhor_ms === melhor ? '—' : fmtD(c.melhor_ms - melhor)}</span></div>`).join('') || '<span class="m">Ainda sem tempos</span>';
  return `${cabecalho(d, s.nome, eu.cor, `
      <span class="f48 fw7 lh1">${fmtRelogio(s.restante)}</span>
      <span class="f16 m">restantes de ${fmtRelogio(s.duracao)}</span>
      <span class="w1 h32 bg-linha"></span><span class="l">Voltas</span><span class="f32 fw7">${Math.max(eu.volta - 1, 0)}</span>`, pilulaEstado(eu))}
  <div class="cresce mh0 g16" style="display:grid;grid-template-columns:440px minmax(0,1fr) 480px">
    <div class="g16 mh0 col">
      <section class="pd18-20 g10 p col"><div class="row sb"><span class="l">Programa da sessão</span><span class="f13 m">${s.proxima ? 'a seguir: ' + esc(s.proxima) : 'marca-se sozinho'}</span></div>${tarefas}</section>
      <section class="cresce mh0 pd18-20 g8 oh p col">
        <span class="l">Stints</span>
        <div class="g8 f12 fw6 pb6 bb g m" style="grid-template-columns:24px 40px 50px minmax(0,1fr) minmax(0,1fr);letter-spacing:.08em;text-transform:uppercase">
          <span>#</span><span>Pneu</span><span>Volt.</span><span class="tr">Melhor</span><span class="tr">Média</span></div>
        ${stints}
      </section>
    </div>
    <div class="g16 mh0 col">
      <section class="cresce mh0 pd20-24 g16 p col">
        <div class="col"><span class="l">Ritmo do stint atual</span><span class="f24 fw7">${lg ? `${TN[lg.composto]} · ${lg.voltas.length} voltas válidas · ${eu.combustivel ?? '—'} kg de combustível` : 'À espera de voltas'}</span></div>
        ${longo}
      </section>
      <section class="pd18-24 g12 p col">
        <div class="ai-b row sb"><span class="l">Os teus setores vs melhor da sessão</span>
          <span class="f16 fw6 c-ambar">${piorK >= 0 && set[piorK].meu - set[piorK].melhor > 0 ? `Foco: setor ${piorK + 1} — perdes ${((set[piorK].meu - set[piorK].melhor) / 1000).toFixed(3)} s` : ''}</span></div>
        <div class="cols4 g12 g">${cmp}
          <div class="bg-cx r8 pd12-14 g2 col" style="border-top:3px solid #F2F4F7"><span class="f14 fw6 m">Speed trap</span>
            <span class="f30 fw7">${eu.speed_trap || '—'} km/h</span><span class="f14 m">Melhor sessão ${trapMelhor || '—'} km/h</span></div></div>
      </section>
    </div>
    <div class="g16 mh0 col">
      <section class="pd18-22 g10 p col">
        <span class="l">Desgaste dos pneus por volta</span>
        <div class="cols2 g10 g">${desg}</div>
        <div class="ai-b row sb" style="padding-top:4px"><span class="f16 m">${eu.vida_fonte === 'do jogo' ? 'Vida útil deste composto (jogo)' : 'Vida útil estimada (até 70%)'}</span><span class="f26 fw7">${eu.vida_total_voltas != null ? (eu.vida_fonte === 'do jogo' ? '' : '~') + eu.vida_total_voltas + ' voltas' : 'a calcular…'}</span></div>
        <span class="f14 fw6 c-ambar">${eu.pneu_limite != null ? RODA[eu.pneu_limite] + ' é quem limita' : ''}${eu.desgaste_fonte && eu.desgaste_fonte !== 'esta sessão' ? `<span class="fw5 m"> · ${esc(eu.desgaste_fonte)}</span>` : ''}</span>
      </section>
      <section class="pd18-22 g10 p col">
        <span class="l">Combustível para a corrida</span>
        <div class="ai-b row sb"><span class="f16 m">Consumo médio</span><span class="f26 fw7">${consumo ? consumo.toFixed(2) + ' kg/volta' : 'a calcular…'}</span></div>
        <div class="ai-b row sb"><span class="f16 m">${voltasCorrida ? voltasCorrida + ' voltas + 1 de margem' : 'Voltas da corrida'}<br><span class="f13">${esc(fonteVoltas)}</span></span><span class="f26 fw7" style="color:${eu.cor}">${total ? total + ' kg' : '—'}</span></div>
        ${t.plano_corrida ? `<div class="ai-b row sb g8"><span class="f16 m">Estratégia provável</span><span class="f20 fw7 tr">${esc(textoStints(t.plano_corrida))}</span></div>` : ''}
        <span class="f14 m">${eu.consumo_fonte && eu.consumo_fonte !== 'esta sessão' ? `Consumo ${esc(eu.consumo_fonte)}, até teres voltas nesta sessão` : 'Consumo medido nas tuas voltas'} · voltas da corrida lidas automaticamente</span>
      </section>
      <section class="cresce mh0 pd18-22 g6 oh p col"><span class="l">Tabela da sessão</span>${linhasTab}</section>
    </div>
  </div>`;
}

// ------------------------------------------------------------------ espera
function renderEspera(d) {
  const recebidos = d && d.estatisticas ? d.estatisticas.pacotes : 0;
  const ignorados = d && d.estatisticas ? d.estatisticas.ignorados : 0;
  return `<div class="espera">
    <h1>${d && d.espectador ? 'A ver como espectador' : 'À espera do jogo…'}</h1>
    ${d && d.espectador ? '<p class="f22 m">O jogo ainda não indicou que carro estás a seguir. Escolhe um piloto na transmissão e o painel acompanha-o.</p>' : ''}
    <p class="f22 m">${recebidos ? `Já chegaram ${recebidos} pacotes, a preparar a sessão…` : ignorados ? `Estão a chegar dados (${ignorados}) mas num formato que não conheço — confirma o formato UDP no jogo.` : 'Ainda não chegou nenhum dado do jogo.'}</p>
    <ol>
      <li>No F1 25 abre <b>Definições → Definições de telemetria</b>.</li>
      <li><b>Telemetria UDP:</b> Ligada · <b>Modo de difusão:</b> Desligado.</li>
      <li><b>Endereço IP:</b> <code>127.0.0.1</code> se jogas neste PC, ou o IP deste PC se jogas na consola.</li>
      <li><b>Porta UDP:</b> <code>20777</code> · <b>Frequência:</b> 20 Hz ou mais.</li>
      <li><b>Formato UDP:</b> <code>2026</code> com o 2026 Season Pack (ou <code>2025</code> com os carros de 2025).</li>
      <li>Entra numa sessão — o ecrã muda sozinho para treinos, qualificação ou corrida.</li>
    </ol>
  </div>`;
}

// ------------------------------------------------------------------ alertas
// Cada alerta fica visível pelo menos 5 s, para não piscar quando um valor anda à volta do limite.
const alertasVistos = new Map();
function alertasAtivos(d) {
  const agora = Date.now();
  const lista = [...(d.alertas || [])];
  if (d.espectador && d.eu) lista.push({ id: 'espectador', nivel: 'info', texto: `Modo espectador — a seguir ${d.eu.codigo}` });
  for (const a of lista) alertasVistos.set(a.id || a.texto, { a, ate: agora + 5000 });
  for (const [k, v] of alertasVistos) if (v.ate < agora) alertasVistos.delete(k);
  const ordem = { perigo: 0, aviso: 1, info: 2 };
  return [...alertasVistos.values()].map((v) => v.a).sort((x, y) => ordem[x.nivel] - ordem[y.nivel]).slice(0, 3);
}
function barraAlertas(lista) {
  if (!lista.length) return '';
  return `<div class="alertas" role="status">${lista.map((a) => `<div class="alerta alerta-${a.nivel}"><i></i><span>${esc(a.texto)}</span></div>`).join('')}</div>`;
}

// ------------------------------------------------------------------ vista compacta (tablet e telemóvel)
function vistaCompacta() {
  if (def.vista === 'compacta') return true;
  if (def.vista === 'completa') return false;
  return window.innerWidth < 1200 || window.innerHeight > window.innerWidth;
}
const kCartao = (titulo, corpo, extra = '') => `<section class="k-cartao"${extra}><span class="l">${titulo}</span>${corpo}</section>`;
const kLinha = (a, b, cor) => `<div class="row sb ai-b g8"><span class="f16 m">${a}</span><span class="f22 fw7"${cor ? ` style="color:${cor}"` : ''}>${b}</span></div>`;
const corTemp = (t) => t < 90 ? '#4DA3FF' : t <= 105 ? '#3DDC84' : '#FF4D4D';
function kPneus(eu) {
  const sup = eu.pneus_sup || [0, 0, 0, 0];
  return `<div class="k-pneus">${[2, 3, 0, 1].map((k) => `<div class="cx"><span class="f13 m">${RODA[k]}</span><span class="f24 fw7" style="color:${corTemp(sup[k])}">${sup[k]}°</span></div>`).join('')}</div>`;
}
function kTopo(d, selo, centro, pil) {
  const s = d.sessao;
  const [gp] = (s.pista || '').split(' · ');
  return `<header class="k-topo"><span class="selo" style="background:${d.eu.cor}">${esc(selo)}</span>
    <span class="f20 fw7">${esc(gp)}</span><span class="k-centro">${centro}</span>${pil}</header>`;
}
function kTendencia(v, frente) {
  const dif = v.diferenca_volta;
  if (dif == null) return '&nbsp;';
  if (frente) return dif > 0 ? `<span class="c-verde">▼ recuperas ${dif.toFixed(2)} s/volta</span>` : `<span class="c-ambar">▲ perdes ${Math.abs(dif).toFixed(2)} s/volta</span>`;
  return dif > 0 ? `<span class="c-ambar">▲ aproxima-se ${dif.toFixed(2)} s/volta</span>` : `<span class="c-verde">▼ afasta-se ${Math.abs(dif).toFixed(2)} s/volta</span>`;
}

function compactoCorrida(d) {
  const eu = d.eu, cr = d.corrida || {}, s = d.sessao;
  const total = s.voltas_total || 0;
  const volta = Math.min(eu.volta, total || eu.volta);
  const ganho = (eu.grelha || 0) - eu.pos;
  const vizinho = (v, frente) => v
    ? `<span class="f20"><b>${esc(v.codigo)}</b> <span class="m">· P${v.pos} · ${TN[v.composto] || '—'} ${v.idade}V</span></span>
       <span class="k-grande" style="color:${frente ? '#3DDC84' : '#FFB020'}">${v.gap_s.toFixed(3)}<span class="f22"> s</span></span><span class="f15 fw6">${kTendencia(v, frente)}</span>`
    : `<span class="f20 m">${frente ? 'Ninguém à frente' : 'Ninguém atrás'}</span>`;
  const meuIdx = d.carros.findIndex((c) => c.eu);
  const meu = d.carros[meuIdx] || { lider_ms: 0, voltas_atras: 0 };
  const perto = d.carros.slice(Math.max(meuIdx - 3, 0), meuIdx + 4).map((c) => {
    const dv = c.voltas_atras - meu.voltas_atras;
    const t = c.eu ? '—' : dv ? (dv > 0 ? '+' : '−') + Math.abs(dv) + ' V' : fmtRel((c.lider_ms - meu.lider_ms) / 1000);
    return `<div class="k-fila${c.eu ? ' eu' : ''}" style="${c.eu ? `background:${c.cor}33` : ''}"><span class="m fw7">${c.pos}</span><span class="barra-eq" style="background:${c.cor}"></span>${linhaPiloto(c)}<span class="tr">${t}</span>${pneu(c.composto)}</div>`;
  }).join('');
  const vida = eu.vida_restante_voltas != null ? `~${eu.vida_restante_voltas} voltas` : 'a calcular…';
  const margem = eu.margem_voltas;
  return `${kTopo(d, s.nome, `<span class="f32 fw7">V${volta}</span><span class="f20 m">/ ${total || '—'}</span>`, pilulaBandeira(d))}
  <div class="k-grelha">
    ${kCartao('Posição', `<span class="k-grande" style="color:${eu.cor}">P${eu.pos}</span>
      <span class="f16 m">Partida P${eu.grelha || '—'} · <b style="color:${ganho >= 0 ? '#3DDC84' : '#FF4D4D'}">${ganho >= 0 ? '+' : '−'}${Math.abs(ganho)}</b></span>`, ` style="border-color:${eu.cor}"`)}
    ${kCartao('Carro à frente', vizinho(cr.frente, true))}
    ${kCartao('Carro atrás', vizinho(cr.atras, false))}
    ${kCartao('Tempos', `${kLinha('Volta atual', fmtV(eu.atual_ms))}
      ${kLinha('Delta', eu.delta_ms == null ? '—' : fmtD(eu.delta_ms), eu.delta_ms == null ? null : eu.delta_ms <= 0 ? '#3DDC84' : '#FF4D4D')}
      ${kLinha('Última', fmtV(eu.ultima_ms))}${kLinha('Melhor', fmtV(eu.melhor_ms), '#3DDC84')}`)}
    ${kCartao(`Pneus · ${TN[eu.composto] || '—'} · ${eu.idade ?? 0} voltas`, `${kPneus(eu)}${kLinha('Vida (até 70%)', vida)}
      ${eu.desgaste_fonte && eu.desgaste_fonte !== 'esta sessão' ? `<span class="f13 m">${esc(eu.desgaste_fonte)}</span>` : ''}`)}
    ${kCartao('Estratégia', `${kLinha('Janela de box', s.box_ideal ? `V${s.box_ideal}–V${s.box_ultima || s.box_ideal}` : '—', eu.cor)}
      ${kLinha('Se parares agora', cr.reentrada ? 'P' + cr.reentrada.pos : '—')}
      ${cr.plano ? `<span class="f16 fw7">${esc(textoPlano(cr.plano))}</span>` : ''}
      ${s.chuva ? `<span class="f15 fw6 c-azul">Chuva ${s.chuva.chuva}% daqui a ${s.chuva.min} min</span>` : ''}`)}
    ${kCartao('Energia', `${kLinha('Bateria ERS', (eu.ers_pct ?? '—') + '%', '#4DA3FF')}<div class="barra h12"><div style="width:${pct(eu.ers_pct)};background:#4DA3FF"></div></div>
      ${kLinha('Combustível', margem == null ? '—' : (margem >= 0 ? '+' : '') + margem.toFixed(2) + ' voltas', margem == null ? null : margem >= 0 ? '#3DDC84' : '#FF4D4D')}`)}
    ${kCartao('À tua volta', `<div class="col g4">${perto}</div>`)}
  </div>`;
}

function compactoQuali(d) {
  const eu = d.eu, q = d.quali || {}, s = d.sessao;
  const delta = eu.delta_ms;
  const deltaCor = delta == null ? '#98A2B3' : delta <= 0 ? '#3DDC84' : '#FF4D4D';
  const porIdx = Object.fromEntries(d.carros.map((c) => [c.idx, c]));
  const ordem = (q.ordem || []).map((i) => porIdx[i]).filter(Boolean);
  const minha = ordem.findIndex((c) => c.eu);
  const tent = q.tentativa || {};
  const prev = q.previsao_pos;
  const ref = eu.referencia_origem && eu.referencia_origem !== s.nome ? ` · referência: ${esc(eu.referencia_origem)}` : '';
  const filas = ordem.slice(Math.max(minha - 2, 0), minha + 3).map((c) => {
    const k = ordem.indexOf(c);
    const fora = q.corte && k >= q.corte;
    return `<div class="k-fila${c.eu ? ' eu' : ''}" style="${c.eu ? `background:${c.cor}33` : fora ? 'background:#2A1215' : ''}"><span class="fw7" style="color:${fora ? '#FF7A7A' : '#98A2B3'}">${k + 1}</span><span class="barra-eq" style="background:${c.cor}"></span>${linhaPiloto(c)}<span class="tr">${fmtV(c.melhor_ms)}</span><span></span></div>`;
  }).join('');
  return `${kTopo(d, s.nome, `<span class="f32 fw7">${fmtRelogio(s.restante)}</span>`, pilulaEstado(eu))}
  <div class="k-grelha">
    ${kCartao('Delta ao teu melhor' + ref, delta == null
      ? `<span class="f28 fw7 m">${eu.melhor_ms ? 'À espera da volta rápida' : 'Ainda sem referência'}</span>`
      : `<span class="k-grande" style="color:${deltaCor}">${fmtD(delta)}</span>`
      + `${kLinha('Previsão', fmtV(eu.previsao_ms))}${prev ? kLinha('Posição prevista', 'P' + prev, q.corte && prev > q.corte ? '#FF7A7A' : '#3DDC84') : ''}`, ' style="grid-column:1/-1"')}
    ${kCartao('Sessão', `${kLinha('Melhor volta', fmtV(eu.melhor_ms))}${kLinha('Posição', minha >= 0 ? 'P' + (minha + 1) : '—')}
      ${kLinha('Margem ao corte', q.margem_ms == null ? '—' : (q.margem_ms / 1000).toFixed(3) + ' s', q.margem_ms == null ? null : q.margem_ms > 0 ? '#FFB020' : '#FF4D4D')}
      ${kLinha('Para a pole', q.pole_ms && eu.melhor_ms ? fmtD(eu.melhor_ms - q.pole_ms) : '—', '#B57BFF')}`)}
    ${kCartao('Tentativas', `<span class="f22 fw7" style="color:${tent.ok ? '#3DDC84' : '#FF4D4D'}">${tent.ok ? 'Ainda dá para mais 1' : 'Já não dá para outra'}</span>
      <span class="f15 m">${tent.ok ? 'Sai do box até faltarem ' + fmtRelogio((tent.sair_ate_ms || 0) / 1000) : 'Aproveita esta volta'}</span>`)}
    ${kCartao('Temperatura dos pneus · alvo 90–105°', kPneus(eu))}
    ${kCartao('Tabela', `<div class="col g4">${filas || '<span class="m">Ainda sem tempos</span>'}</div>`)}
  </div>`;
}

function compactoTreinos(d) {
  const eu = d.eu, t = d.treinos || {}, s = d.sessao;
  const prog = t.programa || [];
  const ativa = prog.find((p) => !p.feito);
  const feitas = prog.filter((p) => p.feito).length;
  const lg = t.longo;
  const voltasCorrida = def.voltas || s.voltas_corrida || null;
  const consumo = eu.consumo_volta;
  const totalKg = consumo && voltasCorrida ? (consumo * (voltasCorrida + 1)).toFixed(1) : null;
  const taxa = eu.desgaste_volta;
  const set = t.setores || [];
  const piorK = set.reduce((a, x, k) => (x.meu && x.melhor && (a < 0 || x.meu - x.melhor > set[a].meu - set[a].melhor) ? k : a), -1);
  const foco = piorK >= 0 && set[piorK].meu - set[piorK].melhor > 0 ? `Setor ${piorK + 1}: perdes ${((set[piorK].meu - set[piorK].melhor) / 1000).toFixed(3)} s` : 'Sem setor a perder tempo';
  return `${kTopo(d, s.nome, `<span class="f32 fw7">${fmtRelogio(s.restante)}</span><span class="f16 m">· ${Math.max(eu.volta - 1, 0)} voltas</span>`, pilulaEstado(eu))}
  <div class="k-grelha">
    ${kCartao(`Programa · ${feitas} de ${prog.length} feitas`, ativa
      ? `<span class="f22 fw7">${esc(ativa.nome)}</span><span class="f15 m">${esc(ativa.detalhe)}</span><div class="barra"><div style="width:${pct(ativa.progresso * 100)};background:${eu.cor}"></div></div>`
      : '<span class="f22 fw7 c-verde">Programa completo</span>')}
    ${kCartao('Ritmo do stint', lg ? `${kLinha('Média', fmtV(lg.media_ms))}${kLinha('Degradação', fmtD(lg.degradacao_ms) + ' s/volta', '#FFB020')}
      ${kLinha('Consistência', '±' + (lg.consistencia_ms / 1000).toFixed(2) + ' s', lg.consistencia_ms < 200 ? '#3DDC84' : '#FFB020')}` : '<span class="f16 m">Faz 2 voltas seguidas no mesmo pneu</span>')}
    ${kCartao('Desgaste por volta', `<div class="k-pneus">${[2, 3, 0, 1].map((k) => `<div class="cx"><span class="f13 m">${RODA[k]}</span><span class="f24 fw7"${eu.pneu_limite === k ? ' style="color:#FFB020"' : ''}>${taxa ? taxa[k].toFixed(1) + '%' : '—'}</span></div>`).join('')}</div>
      ${kLinha('Vida estimada', eu.vida_total_voltas != null ? '~' + eu.vida_total_voltas + ' voltas' : 'a calcular…')}`)}
    ${kCartao('Combustível para a corrida', `${kLinha('Consumo', consumo ? consumo.toFixed(2) + ' kg/volta' : 'a calcular…')}
      ${kLinha(voltasCorrida ? voltasCorrida + ' voltas + 1' : 'Voltas da corrida', totalKg ? totalKg + ' kg' : '—', eu.cor)}
      ${t.plano_corrida ? kLinha('Estratégia', esc(textoStints(t.plano_corrida))) : ''}`)}
    ${kCartao('Foco', `<span class="f20 fw7 c-ambar">${foco}</span>${kLinha('Speed trap', (eu.speed_trap || '—') + ' km/h')}`)}
  </div>`;
}

function renderCompacto(d, qual) {
  if (qual === 'corrida' && d.corrida) return compactoCorrida(d);
  if (qual === 'qualificacao' && d.quali) return compactoQuali(d);
  if (qual === 'treinos' && d.treinos) return compactoTreinos(d);
  if (d.corrida) return compactoCorrida(d);
  if (d.quali) return compactoQuali(d);
  return compactoTreinos(d);
}

// ------------------------------------------------------------------ plano de corrida e resumo da sessão
const nomeConj = (st) => `${TN[st.composto] || st.composto} ${st.novo ? 'novos' : `usados (${st.desgaste}%)`}`;
function textoPlano(p) {
  if (!p) return '';
  if (!p.paragens) return 'Sem paragens até ao fim';
  return p.stints.slice(1).map((st, k) => `Box V${p.box[k]} → ${nomeConj(st)}`).join(' · ');
}
const textoStints = (p) => (p ? p.stints.map((st) => `${TN[st.composto] || st.composto} ${st.voltas}V`).join(' → ') : '');
function barraStints(stints) {
  const total = stints.reduce((a, s) => a + s.voltas, 0) || 1;
  return `<div class="row g4">${stints.map((st) => `<div class="f15 fw7 row jc-c r4" style="flex:${st.voltas / total};min-width:44px;height:30px;background:${TC[st.composto] || TC['?']};color:#0A0C0F">${esc(st.composto)} ${st.voltas}</div>`).join('')}</div>`;
}
function cartaoPlano(p) {
  if (!p) return '';
  const alt = p.alternativa;
  return `<div class="cx g2"><span class="f13 m">Plano · ${p.paragens} ${p.paragens === 1 ? 'paragem' : 'paragens'}${alt ? ` · com ${alt.paragens}: +${alt.mais_lento_s} s` : ''}</span>
    <span class="f18 fw7 c-claro">${esc(textoPlano(p))}</span>
    <span class="f13 m">Box custa ${p.perda_box_s} s · ${esc(p.perda_box_fonte)}</span></div>`;
}

function itensResumo(d) {
  const r = d.resumo, eu = d.eu;
  const itens = [];
  let sub = '';
  if (r.ecra === 'corrida') {
    const ganho = (r.grelha || 0) - r.posicao;
    sub = `Partida P${r.grelha || '—'} · <b style="color:${ganho >= 0 ? '#3DDC84' : '#FF4D4D'}">${ganho >= 0 ? '+' : '−'}${Math.abs(ganho)}</b>${r.resultado && r.resultado !== 'Terminou' ? ' · ' + esc(r.resultado) : ''}`;
  } else if (r.ecra === 'qualificacao') {
    sub = r.corte ? (r.passou ? `<span class="c-verde">Passaste o corte (top ${r.corte})</span>` : `<span class="c-verm2">Eliminado (corte em P${r.corte})</span>`) : 'Posição de partida';
  } else sub = 'Na tabela da sessão';
  itens.push(['Posição final', `<span class="k-grande" style="color:${eu.cor}">P${r.posicao}</span><span class="f18 m">${sub}</span>`]);
  itens.push(['Melhor volta', `<span class="f40 fw7 c-verde">${fmtV(r.melhor_ms)}</span>
    <span class="f16 m">${r.mais_rapida ? `Mais rápida: ${esc(r.mais_rapida.codigo)} ${fmtV(r.mais_rapida.ms)}` : ''}${r.para_pole_ms != null ? ` · pole ${fmtD(r.para_pole_ms)}` : ''}</span>`]);
  if (r.ecra === 'corrida') {
    itens.push(['Pontos', `<span class="f56 fw7">${r.pontos ?? '—'}</span><span class="f16 m">${r.tempo_total_s ? 'Tempo total ' + fmtV(r.tempo_total_s * 1000) : ''}${r.para_vencedor_s ? ` · +${r.para_vencedor_s.toFixed(3)} s do vencedor` : ''}</span>`]);
    itens.push(['Paragens e penalizações', `<span class="f40 fw7">${r.paragens ?? 0} ${r.paragens === 1 ? 'paragem' : 'paragens'}</span><span class="f16 m">${r.penalizacoes_s ? `+${r.penalizacoes_s} s de penalização` : 'Sem penalizações'}</span>`]);
  }
  if (r.stints && r.stints.length) itens.push(['Stints', `${barraStints(r.stints)}<span class="f16 m">${r.voltas} voltas</span>`]);
  if (r.tabela && r.tabela.length) {
    itens.push(['Classificação', `<div class="col g2">${r.tabela.map((c) => `<div class="k-fila${c.eu ? ' eu' : ''}" style="height:28px;${c.eu ? `background:${c.cor}33` : ''}">
      <span class="m fw7">${c.pos}</span><span class="barra-eq" style="background:${c.cor}"></span><span>${esc(c.codigo)}</span><span class="tr">${c.pontos} pts</span><span></span></div>`).join('')}</div>`]);
  }
  if (r.programa) {
    itens.push(['Programa', `<span class="f40 fw7${r.programa.feitas === r.programa.total ? ' c-verde' : ''}">${r.programa.feitas} de ${r.programa.total}</span>
      <span class="f16 m">${r.programa.falta.length ? 'Ficou por fazer: ' + r.programa.falta.map(esc).join(', ') : 'Tudo feito'}</span>`]);
  }
  if (r.ritmo) itens.push(['Ritmo de corrida', `<span class="f40 fw7">${fmtV(r.ritmo.media_ms)}</span><span class="f16 c-ambar fw6">${fmtD(r.ritmo.degradacao_ms)} s por volta</span>`]);
  if (r.consumo_volta || r.desgaste_volta) {
    itens.push(['Medições guardadas', `${r.consumo_volta ? kLinha('Consumo', r.consumo_volta.toFixed(2) + ' kg/volta') : ''}
      ${r.desgaste_volta ? kLinha('Desgaste (pior pneu)', Math.max(...r.desgaste_volta).toFixed(1) + '%/volta') : ''}
      <span class="f14 m">Ficam para as próximas sessões neste circuito</span>`]);
  }
  if (r.plano_corrida) itens.push(['Estratégia provável para a corrida', `<span class="f24 fw7">${esc(textoStints(r.plano_corrida))}</span><span class="f15 m">${esc(textoPlano(r.plano_corrida))}</span>`]);
  if (r.proxima) itens.push(['A seguir', `<span class="f40 fw7" style="color:${eu.cor}">${esc(r.proxima)}</span>`]);
  return itens;
}
function renderResumo(d) {
  const r = d.resumo;
  return `${cabecalho(d, 'Fim · ' + r.sessao, d.eu.cor, `<span class="f32 fw7">Resumo da sessão</span>${r.fonte ? `<span class="f15 m">${esc(r.fonte)}</span>` : ''}`, '')}
    <div class="resumo-grelha">${itensResumo(d).map(([t, c]) => kCartao(t, c)).join('')}</div>`;
}
function compactoResumo(d) {
  const r = d.resumo;
  return `${kTopo(d, 'Fim · ' + r.sessao, '<span class="f20 fw7">Resumo</span>', '')}
    <div class="k-grelha">${itensResumo(d).map(([t, c]) => kCartao(t, c)).join('')}</div>`;
}

// ------------------------------------------------------------------ ciclo
let ultimo = null;
function render() {
  const d = ultimo;
  if (!d || !d.pronto) { ecraEl.innerHTML = renderEspera(d); return; }
  if (autoTempos && Date.now() - ultimaTroca > 8000) {
    const k = MODOS.findIndex((m) => m[0] === modoTempos);
    modoTempos = MODOS[(k + 1) % MODOS.length][0];
    ultimaTroca = Date.now();
  }
  const qual = def.ecra === 'auto' ? d.ecra : def.ecra;
  const alertas = alertasAtivos(d);
  alturaUtil = 952 - (alertas.length ? 72 : 0);
  try {
    let html;
    if (d.resumo && def.ecra === 'auto') html = vistaCompacta() ? compactoResumo(d) : renderResumo(d);
    else if (vistaCompacta()) html = renderCompacto(d, qual);
    else if (qual === 'corrida' && d.corrida) html = renderCorrida(d);
    else if (qual === 'qualificacao' && d.quali) html = renderQuali(d);
    else if (qual === 'treinos' && d.treinos) html = renderTreinos(d);
    else if (d.corrida) html = renderCorrida(d);
    else if (d.quali) html = renderQuali(d);
    else html = renderTreinos(d);
    ecraEl.innerHTML = html.replace('</header>', '</header>' + barraAlertas(alertas));
  } catch (e) {
    console.error(e);
  }
  if (!d.ligado) {
    ecraEl.insertAdjacentHTML('beforeend', '<div class="abs c-verm2 pd8-16 r8 fw7" style="top:30px;left:50%;transform:translateX(-50%);background:#2A1215;border:1px solid #7A2228">Sem dados do jogo há mais de 3 s — jogo em pausa ou fechado?</div>');
  }
}

// O ecrã é redesenhado 5 vezes por segundo: um "click" precisa que o botão ainda exista quando largas o rato,
// por isso os botões reagem logo ao carregar (pointerdown). O "click" só serve para o teclado.
function acaoBotao(alvo) {
  const m = alvo.closest('[data-modo]');
  if (m) { modoTempos = m.dataset.modo; autoTempos = false; render(); return true; }
  if (alvo.closest('[data-auto]')) { autoTempos = !autoTempos; ultimaTroca = Date.now(); render(); return true; }
  return false;
}
ecraEl.addEventListener('pointerdown', (e) => { if (e.button === 0 && acaoBotao(e.target)) e.preventDefault(); });
ecraEl.addEventListener('click', (e) => { if (e.detail === 0) acaoBotao(e.target); });

function escalar() {
  const compacta = vistaCompacta();
  const mudou = document.documentElement.classList.contains('compacto') !== compacta;
  document.documentElement.classList.toggle('compacto', compacta);
  if (compacta) {
    ecraEl.style.transform = '';
  } else {
    const k = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    ecraEl.style.transform = `scale(${k})`;
  }
  if (mudou && ultimo) render();
}
window.addEventListener('resize', escalar);
escalar();

function ligar() {
  const es = new EventSource('/stream');
  es.onmessage = (ev) => { ultimo = JSON.parse(ev.data); render(); };
  es.onerror = () => { es.close(); ultimo = ultimo ? { ...ultimo, ligado: false } : null; render(); setTimeout(ligar, 2000); };
}
ligar();

// ------------------------------------------------------------------ painel de definições
const caixa = document.getElementById('definicoes');
document.getElementById('abrir-def').addEventListener('click', () => {
  document.getElementById('def-ecra').value = def.ecra;
  document.getElementById('def-vista').value = def.vista;
  document.getElementById('def-voltas').value = def.voltas || '';
  caixa.hidden = false;
});
document.getElementById('def-fechar').addEventListener('click', () => { caixa.hidden = true; });
document.getElementById('def-guardar').addEventListener('click', () => {
  def.ecra = document.getElementById('def-ecra').value;
  def.vista = document.getElementById('def-vista').value;
  const v = parseInt(document.getElementById('def-voltas').value, 10);
  def.voltas = v > 0 ? v : null;
  guardarDef();
  caixa.hidden = true;
  escalar();
  render();
});
