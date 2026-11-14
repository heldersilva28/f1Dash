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
    return { ecra: d.ecra || 'auto', voltas: d.voltas || null };
  } catch (e) {
    return { ecra: 'auto', voltas: null };
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
    return `<div class="prev"><span style="font-size:12px" class="m">${p.min ? '+' + p.min + ' min' : 'Agora'}</span>
      <span style="font-size:14px;font-weight:600;color:${p.chuva >= 10 ? '#4DA3FF' : '#F2F4F7'}">${esc(w)}</span></div>`;
  }).join('');
  return `<header class="cab">
    <div class="row" style="gap:14px">
      <span class="selo" style="background:${cor}">${esc(selo)}</span>
      <div class="col"><span style="font-size:22px;font-weight:700">${esc(gp)}</span><span style="font-size:14px" class="m">${esc(circuito || '')}</span></div>
    </div>
    <div class="row" style="flex:1;justify-content:center;gap:14px">${centro}</div>
    ${pil}
    <div class="row" style="gap:10px">
      <div class="col" style="align-items:flex-end"><span style="font-size:16px;font-weight:600">Ar ${s.temp_ar}° · Pista ${s.temp_pista}°</span><span style="font-size:13px" class="m">${esc(s.meteo)}</span></div>
      ${prev}
    </div>
  </header>`;
}
function pilula(texto, cor, fundo, borda) {
  return `<span class="pilula" style="background:${fundo};border:1px solid ${borda};color:${cor}"><i style="background:${cor}"></i>${esc(texto)}</span>`;
}
function pilulaBandeira(d) {
  const sc = d.sessao.safety_car, b = d.eu.bandeira;
  if (sc === 1) return pilula('Safety Car', '#F5C518', '#2A2410', '#7A6410');
  if (sc === 2) return pilula('Virtual Safety Car', '#F5C518', '#2A2410', '#7A6410');
  if (sc === 3) return pilula('Volta de formação', '#98A2B3', '#161B21', '#2A333E');
  if (b === 3) return pilula('Bandeira amarela', '#F5C518', '#2A2410', '#7A6410');
  if (b === 4) return pilula('Bandeira vermelha', '#FF4D4D', '#2A1215', '#7A2228');
  if (b === 2) return pilula('Bandeira azul', '#4DA3FF', '#0F1E2E', '#285E94');
  return pilula('Bandeira verde', '#3DDC84', '#0F2A1A', '#1F6B3D');
}
const ESTADOS = { 0: ['Na garagem', '#98A2B3', '#161B21', '#2A333E'], 1: ['Volta rápida', '#C9A0FF', '#221634', '#6B3FA8'],
  2: ['Volta de entrada', '#8CC4FF', '#0F1E2E', '#285E94'], 3: ['Volta de saída', '#8CC4FF', '#0F1E2E', '#285E94'], 4: ['Em pista', '#8CC4FF', '#0F1E2E', '#285E94'] };
function pilulaEstado(eu) { const e = ESTADOS[eu.estado_piloto] || ESTADOS[4]; return pilula(e[0], e[1], e[2], e[3]); }

function linhaPiloto(c, eu) {
  return `<span class="row" style="gap:7px;min-width:0">${esc(c.codigo)}${c.eu ? `<span class="tu" style="background:${c.cor}">TU</span>` : ''}${c.penal ? `<span class="etq" style="background:#FFB020">+${c.penal}s</span>` : ''}${c.box ? '<span class="etq" style="background:#4DA3FF">BOX</span>' : ''}</span>`;
}

function blocoCarroPainel(eu, titulo) {
  const b = blocoCarro(eu);
  return `<section class="p" style="padding:14px 18px;display:flex;flex-direction:column;gap:10px">
    <div class="row sb"><span class="l">${titulo}</span>
      <span class="row" style="gap:8px;font-size:16px">${pneu(eu.composto)}${TN[eu.composto] || ''} · ${eu.idade ?? 0} voltas</span></div>
    ${b.html}
    <div class="g" style="grid-template-columns:repeat(3,minmax(0,1fr));gap:6px">${b.chips}</div>
    <span style="font-size:12px;text-align:center" class="m">Peças: verde OK · amarelo/laranja dano · vermelho crítico — anel = vida do pneu · sup. | int. · T = travão</span>
  </section>`;
}

function grafico(series, w, h, rotulos) {
  const todos = series.flatMap((s) => s.v).filter((x) => x > 0);
  if (todos.length < 2) return `<div class="m" style="height:${h}px;display:flex;align-items:center;justify-content:center">A recolher voltas…</div>`;
  let mn = Math.min(...todos), mx = Math.max(...todos);
  if (mx - mn < 400) { const c = (mx + mn) / 2; mn = c - 200; mx = c + 200; }
  const pts = (v) => v.map((x, i) => `${(10 + i * (w - 20) / Math.max(v.length - 1, 1)).toFixed(1)},${(15 + (x - mn) / (mx - mn) * (h - 30)).toFixed(1)}`).join(' ');
  const linhas = series.map((s) => `<polyline points="${pts(s.v)}" fill="none" stroke="${s.c}" stroke-width="${s.w || 2.5}" stroke-linejoin="round"></polyline>`).join('');
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(rotulos)}">
    <line x1="10" y1="15" x2="${w - 10}" y2="15" stroke="#232B35"></line><line x1="10" y1="${h / 2}" x2="${w - 10}" y2="${h / 2}" stroke="#232B35"></line>
    <line x1="10" y1="${h - 15}" x2="${w - 10}" y2="${h - 15}" stroke="#232B35"></line>${linhas}</svg>
    <div class="row sb m" style="font-size:13px"><span>Mais rápido ↑</span><span>${fmtV(mn)} – ${fmtV(mx)}</span></div>`;
}

// ------------------------------------------------------------------ CORRIDA
let modoTempos = 'me', autoTempos = true, ultimaTroca = Date.now();
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
  const alt = Math.max(28, Math.min(38, Math.floor((952 - 28 - 80) / Math.max(n, 1)) - 3));
  const linhas = d.carros.map((c, i) => {
    const [t, cor] = celulaTempo(c, meu, i);
    return `<div class="tab" style="grid-template-columns:30px 6px minmax(0,1fr) 88px 66px 28px;height:${alt}px;background:${c.eu ? c.cor + '33' : 'transparent'};font-size:18px;font-weight:${c.eu ? 700 : 500}">
      <span class="m" style="font-weight:700">${c.pos}</span><span class="barra-eq" style="background:${c.cor}"></span>${linhaPiloto(c)}
      <span style="text-align:right;color:${cor}">${t}</span>
      <span class="row" style="gap:6px">${pneu(c.composto)}<span class="m" style="font-size:15px">${c.idade}</span></span>
      <span class="m" style="text-align:right;font-size:15px">${c.paragens}</span></div>`;
  }).join('');
  const aero = eu.aero || {};
  const regras26 = aero.regras_2026 !== 0;
  const nomeAjuda = regras26 ? 'Overtake' : 'DRS';
  const cartao = (v, frente) => {
    if (!v) return `<div class="p" style="padding:16px 22px" ><span class="l">${frente ? 'Ninguém à frente' : 'Ninguém atrás'}</span></div>`;
    const dif = v.diferenca_volta;
    let tend = '';
    if (dif != null) {
      if (frente) tend = dif > 0 ? `▼ A recuperar ${dif.toFixed(2)} s/volta` : `▲ A perder ${Math.abs(dif).toFixed(2)} s/volta`;
      else tend = dif > 0 ? `▲ Aproxima-se ${dif.toFixed(2)} s/volta` : `▼ A afastar-se ${Math.abs(dif).toFixed(2)} s/volta`;
    }
    const corT = dif == null ? '#98A2B3' : (frente ? (dif > 0 ? '#3DDC84' : '#FFB020') : (dif > 0 ? '#FFB020' : '#3DDC84'));
    let ajuda = '';
    if (frente) ajuda = v.gap_s < 1 ? `${nomeAjuda} ao alcance` : `${nomeAjuda} a ${(v.gap_s - 1).toFixed(3)} s`;
    else if (v.gap_s < 1) ajuda = `tem ${nomeAjuda} sobre ti`;
    const voltas = v.voltas_atras ? ` · ${v.voltas_atras} V` : '';
    return `<div class="p col" style="padding:16px 22px;gap:2px">
      <span class="l">${frente ? 'Carro à frente' : 'Carro atrás'} · P${v.pos}</span>
      <span style="font-size:20px"><b style="font-size:24px">${esc(v.codigo)}</b> <span class="m">· ${TN[v.composto] || '—'} · ${v.idade} voltas${voltas}</span></span>
      <span style="font-size:56px;font-weight:700;line-height:1.05;color:${frente ? '#3DDC84' : '#FFB020'}">${v.gap_s.toFixed(3)} s</span>
      <span style="font-size:15px;font-weight:600;color:${corT}">${tend || '&nbsp;'}</span>
      <span style="font-size:15px" class="m">${ajuda || '&nbsp;'}</span></div>`;
  };
  const ganho = (eu.grelha || 0) - eu.pos;
  const setores = (eu.setores_ultima || []).map((x, k) => {
    const [c, bg] = SETOR[x.cor] || SETOR.cinza;
    return `<div class="col" style="padding:6px 10px;border-radius:6px;background:${bg};border-top:3px solid ${c}"><span style="font-size:13px;font-weight:600" class="m">S${k + 1} · última</span><span style="font-size:22px;font-weight:700;color:${c}">${fmtS(x.ms)}</span></div>`;
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
      janela.push(`<span style="flex:1;height:12px;border-radius:2px;background:${c}"></span>`);
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
  const vidaTxt = eu.vida_restante_voltas != null ? `~${eu.vida_restante_voltas} voltas` : 'a calcular…';
  const reent = cr.reentrada;
  const corT = (x) => x > 125 ? '#FF4D4D' : x > 115 ? '#FFB020' : '#F2F4F7';
  return `${cabecalho(d, s.nome, eu.cor, `
      <span class="l">Volta</span><span style="font-size:44px;font-weight:700;line-height:1">${volta}</span><span style="font-size:24px" class="m">/ ${total || '—'}</span>
      <div class="barra" style="width:260px;margin-left:12px"><div style="width:${total ? pct(volta / total * 100) : '0%'};background:${eu.cor}"></div></div>
      <span style="font-size:16px;margin-left:8px" class="m">${total ? `Faltam ${Math.max(total - volta, 0)} voltas` : ''}</span>`, pilulaBandeira(d))}
  <div style="flex:1;min-height:0;display:grid;grid-template-columns:420px minmax(0,1fr) 470px;gap:16px">
    <section class="p col" style="padding:14px 10px;gap:3px;min-height:0;overflow:hidden">
      <div class="row" style="gap:6px;padding:0 4px 8px">
        <span class="l" style="margin-right:auto">Tempos</span>
        ${MODOS.map((m) => `<button type="button" class="modo${modoTempos === m[0] ? ' on' : ''}" data-modo="${m[0]}">${m[1]}</button>`).join('')}
        <button type="button" class="modo" data-auto="1" style="font-size:13px;color:${autoTempos ? '#3DDC84' : '#98A2B3'}">Auto ${autoTempos ? '●' : '○'}</button>
      </div>
      <div class="tab" style="grid-template-columns:30px 6px minmax(0,1fr) 88px 66px 28px;padding-bottom:6px;border-bottom:1px solid #232B35;border-radius:0">
        <span class="l">P</span><span></span><span class="l">Piloto</span><span class="l" style="text-align:right">${colLabel}</span><span class="l">Pneu</span><span class="l" style="text-align:right">Box</span></div>
      ${linhas}
    </section>

    <div class="col" style="gap:16px;min-height:0">
      <div class="g" style="grid-template-columns:minmax(0,1fr) 190px minmax(0,1fr);gap:16px">
        ${cartao(cr.frente, true)}
        <div class="p col" style="padding:14px;align-items:center;justify-content:center;border-color:${eu.cor}">
          <span class="l">Posição</span><span style="font-size:88px;font-weight:700;line-height:1;color:${eu.cor}">P${eu.pos}</span>
          <span style="font-size:15px" class="m">Partida P${eu.grelha || '—'} · <span style="color:${ganho >= 0 ? '#3DDC84' : '#FF4D4D'};font-weight:600">${ganho >= 0 ? '+' : '−'}${Math.abs(ganho)}</span></span>
          <span style="font-size:15px" class="m">Ao líder <b style="color:#F2F4F7">${eu.pos === 1 ? '—' : meu.voltas_atras ? `+${meu.voltas_atras} V` : '+' + (meu.lider_ms / 1000).toFixed(3)}</b></span>
        </div>
        ${cartao(cr.atras, false)}
      </div>
      <div class="p g" style="padding:14px 20px;grid-template-columns:repeat(4,minmax(0,1fr)) repeat(3,minmax(0,.72fr));gap:12px;align-items:end">
        <div class="col"><span class="l">Volta atual</span><span style="font-size:30px;font-weight:700">${fmtV(eu.atual_ms)}</span>
          <span style="font-size:14px;font-weight:600;color:${eu.delta_ms == null ? '#98A2B3' : eu.delta_ms <= 0 ? '#3DDC84' : '#FF4D4D'}">${eu.delta_ms == null ? (eu.invalida ? 'Volta inválida' : '—') : fmtD(eu.delta_ms) + ' vs melhor'}</span></div>
        <div class="col"><span class="l">Última</span><span style="font-size:30px;font-weight:700">${fmtV(eu.ultima_ms)}</span><span style="font-size:14px" class="m">${eu.ultima_ms && eu.melhor_ms ? fmtD(eu.ultima_ms - eu.melhor_ms) + ' vs melhor' : '&nbsp;'}</span></div>
        <div class="col"><span class="l">Melhor</span><span style="font-size:30px;font-weight:700;color:#3DDC84">${fmtV(eu.melhor_ms)}</span><span style="font-size:14px" class="m">${eu.melhor_volta_num ? 'Volta ' + eu.melhor_volta_num : '&nbsp;'}</span></div>
        <div class="col"><span class="l">Mais rápida</span><span style="font-size:30px;font-weight:700;color:#B57BFF">${vr ? fmtV(vr.ms) : '—'}</span><span style="font-size:14px" class="m">${vr ? esc(vr.codigo) + (vr.volta ? ' · volta ' + vr.volta : '') : '&nbsp;'}</span></div>
        ${setores}
      </div>
      <div style="flex:1;min-height:0;display:grid;grid-template-columns:440px minmax(0,1fr);gap:16px">
        ${blocoCarroPainel(eu, 'Carro')}
        <section class="p col" style="padding:16px 22px;gap:10px;min-width:0">
          <div class="row sb"><span class="l">Ritmo · últimas voltas</span>
            <span class="row" style="gap:14px;font-size:14px"><span class="row" style="gap:6px"><span style="width:14px;height:3px;background:${eu.cor}"></span>Tu</span>${cr.frente ? `<span class="row" style="gap:6px"><span style="width:14px;height:3px;background:#98A2B3"></span>${esc(cr.frente.codigo)} (à frente)</span>` : ''}</span></div>
          <div style="flex:1;min-height:0" class="col">${grafico([{ v: ritmoF, c: '#98A2B3' }, { v: ritmoEu, c: eu.cor, w: 3.5 }], 450, 300, 'Tempos por volta: o teu ritmo e o do carro da frente')}</div>
          <div class="g" style="grid-template-columns:repeat(3,minmax(0,1fr));gap:10px">
            <div class="cx"><span style="font-size:13px" class="m">Tu · média 5 voltas</span><span style="font-size:22px;font-weight:700;color:${eu.cor}">${fmtV(cr.meu_ritmo_ms)}</span></div>
            <div class="cx"><span style="font-size:13px" class="m">${cr.frente ? esc(cr.frente.codigo) + ' · à frente' : 'À frente'}</span><span style="font-size:22px;font-weight:700">${fmtV(cr.frente && cr.frente.ritmo_ms)}</span></div>
            <div class="cx"><span style="font-size:13px" class="m">${cr.atras ? esc(cr.atras.codigo) + ' · atrás' : 'Atrás'}</span><span style="font-size:22px;font-weight:700;color:#FFB020">${fmtV(cr.atras && cr.atras.ritmo_ms)}</span></div>
          </div>
        </section>
      </div>
    </div>

    <div class="col" style="gap:16px;min-height:0">
      <section class="p col" style="padding:16px 22px;gap:9px">
        <span class="l">Estratégia</span>
        <div class="row sb" style="align-items:baseline"><span style="font-size:17px" class="m">Janela ideal de box</span>
          <span style="font-size:30px;font-weight:700;color:${eu.cor}">${s.box_ideal ? `V${s.box_ideal} – V${s.box_ultima || s.box_ideal}` : '—'}</span></div>
        <div class="row" style="gap:3px" aria-hidden="true">${janela.join('')}</div>
        <div class="row sb m" style="font-size:13px"><span>V${volta} (agora)</span><span>V${total}</span></div>
        <div class="g" style="grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">
          <div class="cx"><span style="font-size:13px" class="m">Se parares agora</span><span style="font-size:21px;font-weight:700">${reent ? 'Sais em P' + reent.pos : '—'}</span><span style="font-size:14px" class="m">${reent && reent.atras_de ? 'atrás de ' + esc(reent.atras_de) : ''}</span></div>
          <div class="cx"><span style="font-size:13px" class="m">Vida dos pneus (até 70%)</span><span style="font-size:21px;font-weight:700">${vidaTxt}</span><span style="font-size:14px" class="m">${eu.pneu_limite != null ? RODA[eu.pneu_limite] + ' limita' : ''}</span></div>
        </div>
      </section>
      <section class="p col" style="padding:16px 22px;gap:10px">
        <div class="row sb" style="align-items:baseline"><span class="l">Unidade motriz · desgaste</span><span style="font-size:15px" class="m">Temp. motor <b style="font-size:22px;color:${corT(eu.motor_temp)}">${eu.motor_temp ?? '—'}°</b></span></div>
        <div class="g" style="grid-template-columns:repeat(3,minmax(0,1fr));column-gap:18px;row-gap:10px">
          ${pu.map(([nm, v]) => `<div class="col" style="gap:4px"><div class="row sb" style="font-size:15px"><span class="m">${nm}</span><span style="font-weight:700;color:${corPU(v || 0)}">${v ?? 0}%</span></div><div class="barra" style="height:5px"><div style="width:${pct(Math.max(v || 0, 1))};background:${corPU(v || 0)}"></div></div></div>`).join('')}
        </div>
        <span style="font-size:14px;color:${falhas.length ? '#FF4D4D' : '#98A2B3'}">${falhas.length ? 'Falha: ' + falhas.join(', ') : 'Falhas: nenhuma · motor e ERS OK'}</span>
      </section>
      <section class="p col" style="padding:16px 22px;gap:10px">
        <span class="l">Energia e combustível</span>
        <div class="row sb" style="align-items:baseline"><span style="font-size:16px" class="m">Bateria ERS · modo <b style="color:#F2F4F7">${modoERS}</b></span><span style="font-size:28px;font-weight:700;color:#4DA3FF">${eu.ers_pct ?? '—'}%</span></div>
        <div class="barra" style="height:12px"><div style="width:${pct(eu.ers_pct)};background:#4DA3FF"></div></div>
        <span style="font-size:14px" class="m">Recuperado nesta volta ${eu.ers_rec_mj ?? '—'} MJ · usado ${eu.ers_usado_mj ?? '—'} MJ${eu.ers_limite_mj ? ' · limite ' + eu.ers_limite_mj + ' MJ' : ''}</span>
        <div class="g" style="grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">
          <div class="cx"><span style="font-size:13px" class="m">${regras26 ? 'Aero ativa' : 'DRS'}</span><span style="font-size:17px;font-weight:700;color:${aeroCor}">${regras26 ? aeroTxt : (cr.frente && cr.frente.gap_s < 1 ? 'Disponível' : 'Indisponível')}</span>
            ${regras26 && aero.ovtk_ativo ? '<span style="font-size:13px;color:#3DDC84">Overtake ativo</span>' : ''}</div>
          <div class="cx"><span style="font-size:13px" class="m">Combustível</span><span style="font-size:19px;font-weight:700;color:${margem == null ? '#F2F4F7' : margem >= 0 ? '#3DDC84' : '#FF4D4D'}">${margem == null ? '—' : (margem >= 0 ? '+' : '') + margem.toFixed(2) + ' voltas'}</span>
            <span style="font-size:13px" class="m">${eu.combustivel ?? '—'} kg no tanque</span></div>
        </div>
      </section>
      <section class="p col" style="flex:1;min-height:0;padding:16px 22px;gap:8px;overflow:hidden">
        <span class="l">Direção de corrida</span>
        ${(d.mensagens || []).map((m) => `<div class="g" style="grid-template-columns:42px 8px minmax(0,1fr);gap:10px;align-items:center;font-size:16px"><span class="m" style="font-weight:600">V${m.volta}</span><span style="width:8px;height:8px;border-radius:50%;background:${m.cor}"></span><span>${esc(m.texto)}</span></div>`).join('') || '<span class="m">Sem mensagens</span>'}
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
  const alt = Math.max(30, Math.min(46, Math.floor((952 - 28 - 110) / Math.max(ordem.length, 1)) - 6));
  const linhas = ordem.map((c, k) => {
    const fora = q.corte && k >= q.corte;
    const corte = q.corte && k === q.corte ? `<div class="row" style="gap:10px;padding:4px 8px"><span style="flex:1;height:2px;background:#FF4D4D"></span><span style="font-size:13px;font-weight:700;letter-spacing:.1em;color:#FF7A7A">LINHA DE CORTE · ${fmtV(q.corte_ms)}</span><span style="flex:1;height:2px;background:#FF4D4D"></span></div>` : '';
    return `${corte}<div class="tab" style="grid-template-columns:30px 6px minmax(0,1fr) 98px 74px 14px;height:${alt}px;background:${c.eu ? c.cor + '33' : fora ? '#2A1215' : 'transparent'};font-size:19px;font-weight:${c.eu ? 700 : 500}">
      <span style="font-weight:700;color:${fora ? '#FF7A7A' : '#98A2B3'}">${k + 1}</span><span class="barra-eq" style="background:${c.cor}"></span>${linhaPiloto(c)}
      <span style="text-align:right;color:${k === 0 ? '#B57BFF' : '#F2F4F7'}">${fmtV(c.melhor_ms)}</span>
      <span class="m" style="text-align:right;font-size:16px">${k === 0 || !c.melhor_ms || !pole ? '—' : fmtD(c.melhor_ms - pole)}</span>
      <span style="width:10px;height:10px;border-radius:50%;background:${cores[c.estado_piloto] || '#3A4450'}"></span></div>`;
  }).join('');
  const delta = eu.delta_ms;
  const deltaCor = delta == null ? '#98A2B3' : delta <= 0 ? '#3DDC84' : '#FF4D4D';
  const larg = delta == null ? 0 : Math.min(Math.abs(delta) / 1000, 1) * 50;
  const N = 8;
  const mini = eu.mini || [];
  const melhorSet = eu.melhor_setores || [];
  const atuais = [eu.s1_ms, eu.s2_ms, null];
  const secs = [0, 1, 2].map((k) => {
    const blocos = mini.slice(k * N, k * N + N).map((c) => `<span style="flex:1;height:26px;border-radius:3px;background:${(SETOR[c] || SETOR.cinza)[0]}"></span>`).join('');
    const emPista = eu.estado_piloto > 0;
    const feito = emPista && atuais[k] && eu.setor > k;
    const ref = melhorSet[k];
    const cor = feito ? (ref && atuais[k] <= ref ? '#3DDC84' : '#F5C518') : (emPista && eu.setor === k ? '#F2F4F7' : '#98A2B3');
    return `<div class="col" style="gap:8px"><div class="row" style="gap:3px">${blocos}</div>
      <div class="row sb" style="align-items:baseline"><span style="font-size:15px;font-weight:600" class="m">Setor ${k + 1}</span><span style="font-size:28px;font-weight:700;color:${cor}">${feito ? fmtS(atuais[k]) : emPista && eu.setor === k ? 'em curso' : '—'}</span></div>
      <span style="font-size:14px" class="m">${ref ? 'Referência ' + fmtS(ref) + (feito ? ' · ' + fmtD(atuais[k] - ref) : '') : 'Sem referência ainda'}</span></div>`;
  }).join('');
  const prevPos = q.previsao_pos;
  const passa = q.corte ? (prevPos && prevPos <= q.corte ? 'passas o corte' : 'abaixo do corte') : '';
  const tent = q.tentativa || {};
  const traf = (q.trafego || []).map((t) => `<div class="g" style="grid-template-columns:74px minmax(0,1fr) auto;gap:12px;align-items:center;padding:10px 12px;border-radius:6px;background:#0E1216;border-left:4px solid ${t.alerta ? '#FFB020' : '#3A4450'}">
      <span style="font-size:22px;font-weight:700">${esc(t.codigo)}</span><div class="col"><span style="font-size:16px">${t.frente ? 'À frente' : 'Atrás'} · ${esc(t.estado)}</span>
      <span style="font-size:14px;font-weight:600;color:${t.alerta ? '#FFB020' : '#98A2B3'}">${esc(t.nota || 'Sem impacto nesta volta')}</span></div><span style="font-size:22px;font-weight:700">${t.gap_s} s</span></div>`).join('') || (eu.estado_piloto === 0 ? '<span class="m">Estás na garagem</span>' : '<span class="m">Pista livre à tua volta</span>');
  const sup = eu.pneus_sup || [0, 0, 0, 0];
  const corAlvo = (t) => t < 90 ? '#4DA3FF' : t <= 105 ? '#3DDC84' : '#FF4D4D';
  const ordemR = [2, 3, 0, 1];
  const frio = ordemR.filter((k) => sup[k] < 90).map((k) => RODA[k].toLowerCase());
  const conj = (q.conjuntos || []).map((c) => `<div class="g" style="grid-template-columns:26px minmax(0,1fr) auto;gap:12px;align-items:center;padding:6px 0;border-bottom:1px solid #1B222A">
      ${pneu(c.composto, 24)}<span style="font-size:17px">${TN[c.composto]} ${c.novo ? 'novos' : `usados · ${c.desgaste}%`}</span><span style="font-size:17px;font-weight:600;color:${c.novo && c.composto === 'S' ? '#3DDC84' : '#F2F4F7'}">×${c.qtd}</span></div>`).join('') || '<span class="m">Sem dados de pneus ainda</span>';
  const elim = q.corte ? `eliminados P${q.corte + 1}–P${ordem.length}` : '';
  return `${cabecalho(d, 'Qualificação', eu.cor, `
      <span style="font-size:22px;font-weight:700;padding:6px 12px;border-radius:6px;background:#F2F4F7;color:#0A0C0F">${esc(s.nome)}</span>
      <span style="font-size:48px;font-weight:700;line-height:1">${fmtRelogio(s.restante)}</span>
      <span style="font-size:16px" class="m">restantes${elim ? ' · ' + elim : ''}</span>`, pilulaEstado(eu))}
  <div style="flex:1;min-height:0;display:grid;grid-template-columns:440px minmax(0,1fr) 480px;gap:16px">
    <section class="p col" style="padding:14px 12px;gap:6px;min-height:0;overflow:hidden">
      <div class="tab" style="grid-template-columns:30px 6px minmax(0,1fr) 98px 74px 14px;padding-bottom:6px;border-bottom:1px solid #232B35;border-radius:0">
        <span class="l">P</span><span></span><span class="l">Piloto</span><span class="l" style="text-align:right">Melhor</span><span class="l" style="text-align:right">Dif.</span><span></span></div>
      ${linhas}
      <div class="row m" style="margin-top:auto;gap:16px;font-size:13px;padding:8px 8px 0;border-top:1px solid #232B35">
        <span class="row" style="gap:6px"><span style="width:10px;height:10px;border-radius:50%;background:#B57BFF"></span>Volta rápida</span>
        <span class="row" style="gap:6px"><span style="width:10px;height:10px;border-radius:50%;background:#4DA3FF"></span>Saída/entrada</span>
        <span class="row" style="gap:6px"><span style="width:10px;height:10px;border-radius:50%;background:#3A4450"></span>Garagem</span></div>
    </section>

    <div class="col" style="gap:16px;min-height:0">
      <div class="p g" style="flex:1;min-height:0;padding:22px 28px;grid-template-columns:minmax(0,1fr) 300px;gap:24px;align-items:center">
        <div class="col" style="gap:6px">
          <span class="l">Delta ao teu melhor tempo</span>
          ${delta == null ? `<span style="font-size:44px;font-weight:700;line-height:1.1;color:#98A2B3">${eu.melhor_ms ? 'À espera da volta rápida' : 'Ainda sem volta de referência'}</span>` : `<span style="font-size:150px;font-weight:700;line-height:.95;color:${deltaCor}">${fmtD(delta)}</span>`}
          <div style="height:10px;background:#232B35;border-radius:5px;position:relative;margin-top:6px">
            <span style="position:absolute;left:50%;top:-4px;width:2px;height:18px;background:#98A2B3"></span>
            <span style="position:absolute;${delta != null && delta <= 0 ? 'right:50%' : 'left:50%'};width:${larg}%;height:100%;background:${deltaCor};border-radius:5px"></span></div>
          <div class="row sb m" style="font-size:13px"><span>−1.0 s mais rápido</span><span>+1.0 s mais lento</span></div>
        </div>
        <div class="col" style="gap:12px;border-left:1px solid #232B35;padding-left:24px">
          <div class="col"><span class="l">Previsão de volta</span><span style="font-size:44px;font-weight:700">${fmtV(eu.previsao_ms)}</span>
            <span style="font-size:17px;font-weight:600;color:${passa === 'abaixo do corte' ? '#FF7A7A' : '#3DDC84'}">${prevPos ? `→ P${prevPos}${passa ? ' · ' + passa : ''}` : ''}</span></div>
          <div class="col"><span class="l">Tempo de volta</span><span style="font-size:30px;font-weight:600">${fmtV(eu.atual_ms)}</span></div>
        </div>
      </div>
      <div class="p col" style="padding:18px 22px;gap:14px">
        <div class="row sb"><span class="l">Mini-setores · volta atual</span>
          <span class="row m" style="gap:14px;font-size:13px">
            <span class="row" style="gap:6px"><span style="width:14px;height:8px;background:#B57BFF;border-radius:2px"></span>Melhor sessão</span>
            <span class="row" style="gap:6px"><span style="width:14px;height:8px;background:#3DDC84;border-radius:2px"></span>Melhor pessoal</span>
            <span class="row" style="gap:6px"><span style="width:14px;height:8px;background:#F5C518;border-radius:2px"></span>Mais lento</span></span></div>
        <div class="g" style="grid-template-columns:repeat(3,minmax(0,1fr));gap:14px">${secs}</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px">
        <div class="p col" style="padding:18px 20px;gap:4px"><span class="l">Melhor volta</span><span style="font-size:36px;font-weight:700">${fmtV(eu.melhor_ms)}</span><span style="font-size:15px" class="m">P${(ordem.findIndex((c) => c.eu) + 1) || '—'} · ${TN[eu.composto] || ''}</span></div>
        <div class="p col" style="padding:18px 20px;gap:4px"><span class="l">Volta ideal</span><span style="font-size:36px;font-weight:700;color:#3DDC84">${fmtV(q.ideal_ms)}</span><span style="font-size:15px" class="m">Soma dos teus melhores setores</span></div>
        <div class="p col" style="padding:18px 20px;gap:4px"><span class="l">Margem ao corte</span><span style="font-size:36px;font-weight:700;color:${q.margem_ms == null ? '#98A2B3' : q.margem_ms > 0 ? '#FFB020' : '#FF4D4D'}">${q.margem_ms == null ? '—' : (q.margem_ms / 1000).toFixed(3) + ' s'}</span><span style="font-size:15px" class="m">${q.corte_seguinte ? (q.margem_ms >= 0 ? 'Acima' : 'Abaixo') + ' de P' + (q.corte + 1) + ' (' + esc(q.corte_seguinte) + ')' : 'Sem eliminação nesta sessão'}</span></div>
        <div class="p col" style="padding:18px 20px;gap:4px"><span class="l">Para a pole</span><span style="font-size:36px;font-weight:700;color:#B57BFF">${pole && eu.melhor_ms ? fmtD(eu.melhor_ms - pole) : '—'}</span><span style="font-size:15px" class="m">${esc(q.pole_codigo || '')} · ${fmtV(pole)}</span></div>
      </div>
      <div class="p g" style="padding:16px 22px;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px">
        <div class="col" style="gap:6px"><div class="row sb" style="align-items:baseline"><span class="l">Bateria ERS</span><span style="font-size:24px;font-weight:700;color:#4DA3FF">${eu.ers_pct ?? '—'}%</span></div>
          <div class="barra" style="height:12px"><div style="width:${pct(eu.ers_pct)};background:#4DA3FF"></div></div>
          <span style="font-size:15px" class="m">Modo: <b style="color:#F2F4F7">${{ 0: 'Desligado', 1: 'Médio', 2: 'Hotlap', 3: 'Boost' }[eu.ers_modo] || '—'}</b></span></div>
        <div class="col" style="gap:4px"><span class="l">Combustível</span><span style="font-size:24px;font-weight:700">${eu.combustivel ?? '—'} kg</span><span style="font-size:15px" class="m">Dá para ${eu.margem_voltas != null ? eu.margem_voltas.toFixed(1) : '—'} voltas</span></div>
        <div class="col" style="gap:4px"><span class="l">Speed trap</span><span style="font-size:24px;font-weight:700">${eu.speed_trap || '—'} km/h</span><span style="font-size:15px" class="m">Melhor da sessão ${Math.max(...d.carros.map((c) => c.speed_trap || 0)) || '—'} km/h</span></div>
      </div>
    </div>

    <div class="col" style="gap:16px;min-height:0">
      <section class="p col" style="padding:18px 22px;gap:10px">
        <span class="l">Tempo e tentativas</span>
        <div class="row" style="gap:14px;background:${tent.ok ? '#0F2A1A' : '#2A1215'};border:1px solid ${tent.ok ? '#1F6B3D' : '#7A2228'};border-radius:8px;padding:12px 14px">
          <span style="width:12px;height:12px;border-radius:50%;background:${tent.ok ? '#3DDC84' : '#FF4D4D'};flex:none"></span>
          <div class="col"><span style="font-size:20px;font-weight:700">${tent.ok ? 'Ainda dá para mais 1 tentativa' : 'Já não dá para outra tentativa'}</span>
            <span style="font-size:15px" class="m">${tent.ok ? 'Sai do box até faltarem ' + fmtRelogio((tent.sair_ate_ms || 0) / 1000) : 'Aproveita esta volta'}</span></div></div>
        <div class="g m" style="grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;font-size:14px">
          <span>Volta saída<br><b style="font-size:20px;color:#F2F4F7">${fmtRelogio((q.saida_ms || 0) / 1000)}</b></span>
          <span>Volta rápida<br><b style="font-size:20px;color:#F2F4F7">${fmtRelogio((eu.melhor_ms || 0) / 1000)}</b></span>
          <span>Volta entrada<br><b style="font-size:20px;color:#F2F4F7">${fmtRelogio((q.entrada_ms || 0) / 1000)}</b></span></div>
      </section>
      <section class="p col" style="padding:18px 22px;gap:10px"><span class="l">Tráfego na pista</span>${traf}</section>
      <section class="p col" style="padding:18px 22px;gap:10px">
        <span class="l">Temperatura dos pneus · alvo 90–105°</span>
        <div class="g" style="grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">
          ${ordemR.map((k) => `<div class="row sb" style="padding:10px 12px;border-radius:6px;background:#0E1216;border:1px solid ${corAlvo(sup[k])}"><span style="font-size:15px" class="m">${RODA[k]}</span><span style="font-size:26px;font-weight:700;color:${corAlvo(sup[k])}">${sup[k]}°</span></div>`).join('')}
        </div>
        <span style="font-size:15px;font-weight:600;color:${frio.length ? '#4DA3FF' : '#3DDC84'}">${frio.length ? 'Fria: ' + frio.join(', ') + ' — aquece antes da volta' : 'Todos os pneus na janela'}</span>
      </section>
      <section class="p col" style="flex:1;min-height:0;padding:18px 22px;gap:8px;overflow:hidden"><span class="l">Conjuntos de pneus</span>${conj}</section>
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
      <span style="width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:${p.feito ? '#3DDC84' : 'transparent'};border:2px solid ${p.feito ? '#3DDC84' : on ? eu.cor : '#3A4450'};box-sizing:border-box">
        ${p.feito ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0A0C0F" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg>' : ''}</span>
      <div class="col" style="gap:2px">
        <span style="font-size:18px;font-weight:600;color:${p.feito ? '#98A2B3' : '#F2F4F7'}">${esc(p.nome)}</span>
        <span style="font-size:14px;color:${p.feito ? '#3DDC84' : '#98A2B3'}">${esc(p.detalhe)}</span>
        ${!p.feito && p.progresso > 0 ? `<div class="barra" style="margin-top:4px"><div style="width:${pct(p.progresso * 100)};background:${on ? eu.cor : '#98A2B3'}"></div></div>` : ''}
      </div></div>`;
  }).join('') || '<span class="m">À espera das primeiras voltas</span>';
  const stints = (t.stints || []).map((x, k) => `<div class="g" style="grid-template-columns:24px 40px 50px minmax(0,1fr) minmax(0,1fr);gap:8px;align-items:center;font-size:18px;padding:6px 0;border-bottom:1px solid #1B222A">
      <span class="m">${k + 1}</span>${pneu(x.composto, 22)}<span>${x.voltas}</span><span style="text-align:right">${fmtV(x.melhor_ms)}</span><span style="text-align:right">${fmtV(x.media_ms)}</span></div>`).join('') || '<span class="m">Ainda sem stints</span>';
  const lg = t.longo;
  let longo = '<div class="m" style="margin:auto">Faz pelo menos 2 voltas seguidas no mesmo pneu para ver o ritmo de corrida</div>';
  if (lg) {
    lg.voltas = lg.voltas.slice(-10);
    const todos = lg.voltas.concat(lg.projecao);
    const mn = Math.min(...todos), mx = Math.max(...todos);
    const base = mn - 300;
    const h = (v) => Math.round(50 + (v - base) / Math.max(mx - base, 1) * 380);
    const barras = lg.voltas.map((v, k) => [v, true, k + 1]).concat(lg.projecao.map((v, k) => [v, false, lg.voltas.length + k + 1]))
      .map(([v, real, n]) => `<div class="col" style="flex:1;min-width:0;align-items:center;gap:8px;height:100%;justify-content:flex-end">
        <span style="font-size:${lg.voltas.length > 8 ? 13 : 16}px;font-weight:600;color:${real ? '#F2F4F7' : '#98A2B3'}">${fmtV(v)}</span>
        <div style="width:100%;height:${h(v)}px;background:${real ? eu.cor : 'transparent'};border:2px ${real ? 'solid' : 'dashed'} ${real ? eu.cor : '#98A2B3'};box-sizing:border-box;border-radius:6px 6px 2px 2px"></div>
        <span style="font-size:14px" class="m">V${n}</span></div>`).join('');
    longo = `<div class="g" style="grid-template-columns:repeat(4,minmax(0,1fr));gap:16px">
        <div class="col"><span class="l">Média</span><span style="font-size:40px;font-weight:700">${fmtV(lg.media_ms)}</span></div>
        <div class="col"><span class="l">Degradação</span><span style="font-size:40px;font-weight:700;color:#FFB020">${fmtD(lg.degradacao_ms)} s</span><span style="font-size:14px" class="m">por volta</span></div>
        <div class="col"><span class="l">Consistência</span><span style="font-size:40px;font-weight:700;color:${lg.consistencia_ms < 200 ? '#3DDC84' : '#FFB020'}">±${(lg.consistencia_ms / 1000).toFixed(2)} s</span><span style="font-size:14px" class="m">desvio padrão</span></div>
        <div class="col"><span class="l">Melhor do stint</span><span style="font-size:40px;font-weight:700">${fmtV(lg.melhor_ms)}</span><span style="font-size:14px" class="m">volta ${lg.melhor_volta}</span></div></div>
      <div style="flex:1;min-height:0;display:flex;align-items:flex-end;gap:${lg.voltas.length > 8 ? 8 : 14}px;padding-top:12px;border-top:1px solid #232B35" role="img" aria-label="Tempos por volta do stint atual e projeção das próximas 3 voltas">${barras}</div>
      <span style="font-size:14px" class="m">Barra mais alta = volta mais lenta · tracejado = projeção pela degradação</span>`;
  }
  const set = t.setores || [];
  const piorK = set.reduce((a, x, k) => (x.meu && x.melhor && (a < 0 || x.meu - x.melhor > set[a].meu - set[a].melhor) ? k : a), -1);
  const cmp = set.map((x, k) => {
    const dlt = x.meu && x.melhor ? x.meu - x.melhor : null;
    const c = dlt == null ? '#98A2B3' : dlt <= 0 ? '#B57BFF' : k === piorK ? '#FFB020' : '#F5C518';
    return `<div class="col" style="background:#0E1216;border-radius:8px;padding:12px 14px;border-top:3px solid ${c};gap:2px">
      <span style="font-size:14px;font-weight:600" class="m">Setor ${k + 1}</span><span style="font-size:30px;font-weight:700;color:${c}">${dlt == null ? '—' : fmtD(dlt)}</span>
      <span style="font-size:14px" class="m">${dlt != null && dlt <= 0 ? 'Melhor da sessão · ' + fmtS(x.meu) : `Tu ${fmtS(x.meu)} · melhor ${fmtS(x.melhor)}`}</span></div>`;
  }).join('');
  const trapMelhor = t.speed_trap_melhor;
  const des = (eu.danos || {}).desgaste || [0, 0, 0, 0];
  const taxa = eu.desgaste_volta;
  const ordemR = [2, 3, 0, 1];
  const desg = ordemR.map((k) => {
    const r = taxa ? taxa[k] : null;
    const pior = eu.pneu_limite === k;
    return `<div class="col" style="background:#0E1216;border-radius:6px;padding:10px 12px;gap:4px;border:1px solid ${pior ? '#7A5410' : '#232B35'}">
      <div class="row sb" style="align-items:baseline"><span style="font-size:14px" class="m">${RODA[k]}</span><span style="font-size:14px" class="m">agora ${Math.round(des[k])}%</span></div>
      <span style="font-size:26px;font-weight:700;color:${pior ? '#FFB020' : '#F2F4F7'}">${r == null ? '—' : r.toFixed(1) + '%'}<span style="font-size:15px;font-weight:500;color:#98A2B3"> /volta</span></span></div>`;
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
  const linhasTab = visiveis.map((c) => `<div class="tab" style="grid-template-columns:30px 6px minmax(0,1fr) 96px 70px;height:36px;background:${c.eu ? c.cor + '33' : 'transparent'};font-size:18px;font-weight:${c.eu ? 700 : 500}">
      <span class="m" style="font-weight:700">${tabela.indexOf(c) + 1}</span><span class="barra-eq" style="background:${c.cor}"></span>${linhaPiloto(c)}
      <span style="text-align:right;color:${c.melhor_ms === melhor ? '#B57BFF' : '#F2F4F7'}">${fmtV(c.melhor_ms)}</span><span class="m" style="text-align:right;font-size:15px">${c.melhor_ms === melhor ? '—' : fmtD(c.melhor_ms - melhor)}</span></div>`).join('') || '<span class="m">Ainda sem tempos</span>';
  return `${cabecalho(d, s.nome, eu.cor, `
      <span style="font-size:48px;font-weight:700;line-height:1">${fmtRelogio(s.restante)}</span>
      <span style="font-size:16px" class="m">restantes de ${fmtRelogio(s.duracao)}</span>
      <span style="width:1px;height:32px;background:#232B35"></span><span class="l">Voltas</span><span style="font-size:32px;font-weight:700">${Math.max(eu.volta - 1, 0)}</span>`, pilulaEstado(eu))}
  <div style="flex:1;min-height:0;display:grid;grid-template-columns:440px minmax(0,1fr) 480px;gap:16px">
    <div class="col" style="gap:16px;min-height:0">
      <section class="p col" style="padding:18px 20px;gap:10px"><div class="row sb"><span class="l">Programa da sessão</span><span style="font-size:13px" class="m">marca-se sozinho</span></div>${tarefas}</section>
      <section class="p col" style="flex:1;min-height:0;padding:18px 20px;gap:8px;overflow:hidden">
        <span class="l">Stints</span>
        <div class="g m" style="grid-template-columns:24px 40px 50px minmax(0,1fr) minmax(0,1fr);gap:8px;font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;padding-bottom:6px;border-bottom:1px solid #232B35">
          <span>#</span><span>Pneu</span><span>Volt.</span><span style="text-align:right">Melhor</span><span style="text-align:right">Média</span></div>
        ${stints}
      </section>
    </div>
    <div class="col" style="gap:16px;min-height:0">
      <section class="p col" style="flex:1;min-height:0;padding:20px 24px;gap:16px">
        <div class="col"><span class="l">Ritmo do stint atual</span><span style="font-size:24px;font-weight:700">${lg ? `${TN[lg.composto]} · ${lg.voltas.length} voltas válidas · ${eu.combustivel ?? '—'} kg de combustível` : 'À espera de voltas'}</span></div>
        ${longo}
      </section>
      <section class="p col" style="padding:18px 24px;gap:12px">
        <div class="row sb" style="align-items:baseline"><span class="l">Os teus setores vs melhor da sessão</span>
          <span style="font-size:16px;font-weight:600;color:#FFB020">${piorK >= 0 && set[piorK].meu - set[piorK].melhor > 0 ? `Foco: setor ${piorK + 1} — perdes ${((set[piorK].meu - set[piorK].melhor) / 1000).toFixed(3)} s` : ''}</span></div>
        <div class="g" style="grid-template-columns:repeat(4,minmax(0,1fr));gap:12px">${cmp}
          <div class="col" style="background:#0E1216;border-radius:8px;padding:12px 14px;border-top:3px solid #F2F4F7;gap:2px"><span style="font-size:14px;font-weight:600" class="m">Speed trap</span>
            <span style="font-size:30px;font-weight:700">${eu.speed_trap || '—'} km/h</span><span style="font-size:14px" class="m">Melhor sessão ${trapMelhor || '—'} km/h</span></div></div>
      </section>
    </div>
    <div class="col" style="gap:16px;min-height:0">
      <section class="p col" style="padding:18px 22px;gap:10px">
        <span class="l">Desgaste dos pneus por volta</span>
        <div class="g" style="grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">${desg}</div>
        <div class="row sb" style="align-items:baseline;padding-top:4px"><span style="font-size:16px" class="m">Vida útil estimada (até 70%)</span><span style="font-size:26px;font-weight:700">${eu.vida_total_voltas != null ? '~' + eu.vida_total_voltas + ' voltas' : 'a calcular…'}</span></div>
        <span style="font-size:14px;font-weight:600;color:#FFB020">${eu.pneu_limite != null ? RODA[eu.pneu_limite] + ' é quem limita' : ''}</span>
      </section>
      <section class="p col" style="padding:18px 22px;gap:10px">
        <span class="l">Combustível para a corrida</span>
        <div class="row sb" style="align-items:baseline"><span style="font-size:16px" class="m">Consumo médio</span><span style="font-size:26px;font-weight:700">${consumo ? consumo.toFixed(2) + ' kg/volta' : 'a calcular…'}</span></div>
        <div class="row sb" style="align-items:baseline"><span style="font-size:16px" class="m">${voltasCorrida ? voltasCorrida + ' voltas + 1 de margem' : 'Voltas da corrida'}<br><span style="font-size:13px">${esc(fonteVoltas)}</span></span><span style="font-size:26px;font-weight:700;color:${eu.cor}">${total ? total + ' kg' : '—'}</span></div>
        <span style="font-size:14px" class="m">Consumo medido nas tuas voltas · voltas da corrida lidas automaticamente</span>
      </section>
      <section class="p col" style="flex:1;min-height:0;padding:18px 22px;gap:6px;overflow:hidden"><span class="l">Tabela da sessão</span>${linhasTab}</section>
    </div>
  </div>`;
}

// ------------------------------------------------------------------ espera
function renderEspera(d) {
  const recebidos = d && d.estatisticas ? d.estatisticas.pacotes : 0;
  const ignorados = d && d.estatisticas ? d.estatisticas.ignorados : 0;
  return `<div class="espera">
    <h1>À espera do jogo…</h1>
    <p style="font-size:22px" class="m">${recebidos ? `Já chegaram ${recebidos} pacotes, a preparar a sessão…` : ignorados ? `Estão a chegar dados (${ignorados}) mas num formato que não conheço — confirma o formato UDP no jogo.` : 'Ainda não chegou nenhum dado do jogo.'}</p>
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
  try {
    if (qual === 'corrida' && d.corrida) ecraEl.innerHTML = renderCorrida(d);
    else if (qual === 'qualificacao' && d.quali) ecraEl.innerHTML = renderQuali(d);
    else if (qual === 'treinos' && d.treinos) ecraEl.innerHTML = renderTreinos(d);
    else if (d.corrida) ecraEl.innerHTML = renderCorrida(d);
    else if (d.quali) ecraEl.innerHTML = renderQuali(d);
    else ecraEl.innerHTML = renderTreinos(d);
  } catch (e) {
    console.error(e);
  }
  if (!d.ligado) {
    ecraEl.insertAdjacentHTML('beforeend', '<div style="position:absolute;top:30px;left:50%;transform:translateX(-50%);background:#2A1215;border:1px solid #7A2228;color:#FF7A7A;padding:8px 16px;border-radius:8px;font-weight:700">Sem dados do jogo há mais de 3 s — jogo em pausa ou fechado?</div>');
  }
}

ecraEl.addEventListener('click', (e) => {
  const m = e.target.closest('[data-modo]');
  if (m) { modoTempos = m.dataset.modo; autoTempos = false; render(); return; }
  if (e.target.closest('[data-auto]')) { autoTempos = !autoTempos; ultimaTroca = Date.now(); render(); return; }
});

function escalar() {
  const k = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
  ecraEl.style.transform = `scale(${k})`;
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
  document.getElementById('def-voltas').value = def.voltas || '';
  caixa.hidden = false;
});
document.getElementById('def-fechar').addEventListener('click', () => { caixa.hidden = true; });
document.getElementById('def-guardar').addEventListener('click', () => {
  def.ecra = document.getElementById('def-ecra').value;
  const v = parseInt(document.getElementById('def-voltas').value, 10);
  def.voltas = v > 0 ? v : null;
  guardarDef();
  caixa.hidden = true;
  render();
});
