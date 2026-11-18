/* F1 Dash — vista "Volante": o ecrã do tablet ao lado do volante (1180×820, o tamanho de um iPad deitado).
   Reproduz o design "Tablet · volante" e preenche-o com os dados do jogo. */
/* global esc, fmtV, fmtD, TC, TN, alertasAtivos */

const VL_LARG = 1180, VL_ALT = 820;

// ---- cores do design
const vlTemp = (t) => t < 80 ? '#4DA3FF' : t <= 100 ? '#3DDC84' : t <= 108 ? '#FFB020' : '#FF4D4D';
const vlTravao = (b) => b < 300 ? '#4DA3FF' : b <= 950 ? '#3DDC84' : b <= 1100 ? '#FFB020' : '#FF4D4D';
const VL_VERDE = '#5BE34A', VL_AMARELO = '#E8D23A', VL_LARANJA = '#F2A33A', VL_VERMELHO = '#FF4D4D';
const vlVida = (l) => l >= 70 ? VL_VERDE : l >= 50 ? VL_AMARELO : l >= 30 ? VL_LARANJA : VL_VERMELHO;
const vlDano = (v) => v < 5 ? VL_VERDE : v < 25 ? VL_AMARELO : v < 50 ? VL_LARANJA : VL_VERMELHO;
const VL_CIRC = 2 * Math.PI * 46;

function vlPneu(desgaste, sup, int, trav) {
  const vida = Math.max(0, Math.min(100, Math.round(100 - (desgaste || 0))));
  return { vida, s: Math.round(sup || 0), i: Math.round(int || 0), b: Math.round(trav || 0),
    sc: vlTemp(sup || 0), bc: vlTravao(trav || 0), wc: vlVida(vida), wf: vlVida(vida) + '40',
    dash: (vida / 100 * VL_CIRC).toFixed(1) + ' ' + VL_CIRC.toFixed(1) };
}
const vlPeca = (v) => ({ v: v || 0, f: vlDano(v || 0) + '40', s: vlDano(v || 0) });

// ---- conta-rotações: 22 segmentos (17 à esquerda e em cima, 5 da zona de troca de mudança à direita)
const VL_SEGMENTOS = [
  'M65.6 371.4 A210 210 0 0 1 54.6 358.6 L93.7 327.5 A160 160 0 0 0 102.1 337.3 Z',
  'M49.3 351.7 A210 210 0 0 1 29.8 319.2 L74.9 297.5 A160 160 0 0 0 89.7 322.2 Z',
  'M26.2 311.2 A210 210 0 0 1 14.4 275.3 L63.1 264.0 A160 160 0 0 0 72.1 291.4 Z',
  'M12.6 266.7 A210 210 0 0 1 9.0 229.1 L59.0 228.8 A160 160 0 0 0 61.7 257.5 Z',
  'M9.1 220.3 A210 210 0 0 1 13.9 182.8 L62.8 193.5 A160 160 0 0 0 59.1 222.1 Z',
  'M16.0 174.2 A210 210 0 0 1 28.9 138.7 L74.2 160.0 A160 160 0 0 0 64.3 187.0 Z',
  'M32.8 130.8 A210 210 0 0 1 53.3 99.0 L92.7 129.7 A160 160 0 0 0 77.2 154.0 Z',
  'M58.8 92.2 A210 210 0 0 1 85.8 65.7 L117.5 104.3 A160 160 0 0 0 97.0 124.5 Z',
  'M92.7 60.2 A210 210 0 0 1 124.8 40.3 L147.2 85.0 A160 160 0 0 0 122.8 100.2 Z',
  'M132.7 36.5 A210 210 0 0 1 168.5 24.2 L180.5 72.7 A160 160 0 0 0 153.3 82.1 Z',
  'M177.0 22.2 A210 210 0 0 1 214.6 18.0 L215.6 68.0 A160 160 0 0 0 187.0 71.2 Z',
  'M223.4 18.0 A210 210 0 0 1 261.0 22.2 L251.0 71.2 A160 160 0 0 0 222.4 68.0 Z',
  'M269.5 24.2 A210 210 0 0 1 305.3 36.5 L284.7 82.1 A160 160 0 0 0 257.5 72.7 Z',
  'M313.2 40.3 A210 210 0 0 1 345.3 60.2 L315.2 100.2 A160 160 0 0 0 290.8 85.0 Z',
  'M352.2 65.7 A210 210 0 0 1 379.2 92.2 L341.0 124.5 A160 160 0 0 0 320.5 104.3 Z',
  'M384.7 99.0 A210 210 0 0 1 405.2 130.8 L360.8 154.0 A160 160 0 0 0 345.3 129.7 Z',
  'M409.1 138.7 A210 210 0 0 1 422.0 174.2 L373.7 187.0 A160 160 0 0 0 363.8 160.0 Z',
  'M424.1 182.8 A210 210 0 0 1 428.9 220.3 L378.9 222.1 A160 160 0 0 0 375.2 193.5 Z',
  'M429.0 229.1 A210 210 0 0 1 425.4 266.7 L376.3 257.5 A160 160 0 0 0 379.0 228.8 Z',
  'M423.6 275.3 A210 210 0 0 1 411.8 311.2 L365.9 291.4 A160 160 0 0 0 374.9 264.0 Z',
  'M408.2 319.2 A210 210 0 0 1 388.7 351.7 L348.3 322.2 A160 160 0 0 0 363.1 297.5 Z',
  'M383.4 358.6 A210 210 0 0 1 357.3 386.0 L324.4 348.4 A160 160 0 0 0 344.3 327.5 Z',
];
const VL_ACESO = ['#F4FFF9', '#B8FFE0', '#7DFFC4', '#4DFFA8', '#2BFF8C', '#19F576', '#12EE62', '#16E84F', '#33E83F', '#5CEB32',
  '#8CF02A', '#C2F521', '#F2F21A', '#FFD21A', '#FFA41A', '#FF6A1A', '#FF2D2D',
  '#C34BFF', '#B05CFF', '#9D63FF', '#8A5CFF', '#7A55F0'];   // zona de troca de mudança: roxo, como a linha do design
const VL_APAGADO = ['#2B3038', '#292E35', '#272C33', '#252A30', '#23282E'];

function vlContaRotacoes(eu) {
  // as luzes acendem pela percentagem que o jogo envia (as mesmas do volante do carro)
  const acesas = Math.round(Math.max(0, Math.min(100, eu.luzes_rpm || 0)) / 100 * VL_SEGMENTOS.length);
  const acesos = [], apagados = [];
  VL_SEGMENTOS.forEach((d, k) => {
    if (k < acesas) acesos.push(`<path d="${d}" fill="${VL_ACESO[k]}"></path>`);
    else apagados.push(`<path d="${d}" fill="${VL_APAGADO[Math.max(0, k - 17)] || VL_APAGADO[0]}" stroke="#343B44" stroke-width="1"></path>`);
  });
  return `<g>${apagados.join('')}</g><g filter="url(#gGlow)">${acesos.join('')}</g>`;
}

// ---- carro visto de cima (o mesmo desenho do design, com os anéis da vida de cada pneu)
function vlCarro(eu) {
  const des = (eu.danos && eu.danos.desgaste) || [0, 0, 0, 0];
  const sup = eu.pneus_sup || [0, 0, 0, 0], int = eu.pneus_int || [0, 0, 0, 0], trv = eu.travoes || [0, 0, 0, 0];
  // ordem do jogo: 0 trás esq., 1 trás dir., 2 frente esq., 3 frente dir.
  const tFL = vlPneu(des[2], sup[2], int[2], trv[2]), tFR = vlPneu(des[3], sup[3], int[3], trv[3]);
  const tRL = vlPneu(des[0], sup[0], int[0], trv[0]), tRR = vlPneu(des[1], sup[1], int[1], trv[1]);
  const dn = eu.danos || {};
  const p = { fwl: vlPeca(dn.asa_fe), fwr: vlPeca(dn.asa_fd), rw: vlPeca(dn.asa_tras), floor: vlPeca(dn.fundo),
    diff: vlPeca(dn.difusor), side: vlPeca(dn.pontoes), gb: vlPeca(dn.caixa), eng: vlPeca(dn.motor) };
  const anel = (cx, cy, t) => `<g>
            <circle cx="${cx}" cy="${cy}" r="47" fill="#0A0C0F" fill-opacity="0.75"></circle>
            <circle cx="${cx}" cy="${cy}" r="46" fill="none" stroke="${t.wc}" stroke-opacity="0.35" stroke-width="2.5"></circle>
            <circle cx="${cx}" cy="${cy}" r="46" fill="none" stroke="${t.wc}" stroke-width="6" stroke-linecap="round" stroke-dasharray="${t.dash}" transform="rotate(-90 ${cx} ${cy})" filter="url(#carGlowT)"></circle>
          </g>`;
  const asa = (x, y, w, alin, titulo, peca) => `<div style="position: absolute; left: ${x}px; top: ${y}px; width: ${w}px;${alin ? ' text-align: right;' : ''} display: flex; flex-direction: column; line-height: 1.1">
            <span style="font-size: 10px; font-weight: 600; letter-spacing: .12em; color: #98A2B3">${titulo}</span>
            <span style="font-size: 17px; font-weight: 700; color: ${peca.s}">${peca.v}%</span>
          </div>`;
  const roda = (x, y, t, nome) => `<div style="position: absolute; left: ${x}px; top: ${y}px; width: 88px; height: 88px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0; text-align: center; line-height: 1.1">
            <span style="font-size: 30px; font-weight: 700; color: #FFFFFF; line-height: 1">${t.vida}%</span>
            <span style="font-size: 15px; font-weight: 700; color: ${t.sc}">${t.s}°C</span>
            <span style="font-size: 14px; font-weight: 700; color: ${t.wc}">${nome}</span>
          </div>`;
  return `<div style="width: 340px; height: 357px; flex: none">
        <div style="position: relative; width: 404px; height: 424px; transform: scale(0.84); transform-origin: top left">
        <svg width="404" height="424" viewBox="0 0 404 424" style="position: absolute; left: 0; top: 0" role="img" aria-label="Carro visto de cima: peças coloridas pelo dano e pneus pelo desgaste, com anéis do desgaste de cada pneu e as temperaturas">
          <defs>
            <filter id="carGlowT" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="2.4" result="b"></feGaussianBlur>
              <feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge>
            </filter>
          </defs>
          <g stroke="#4DA3FF" stroke-width="2" stroke-dasharray="1 5" stroke-linecap="round" opacity="0.8">
            <line x1="103" y1="122" x2="133" y2="122"></line><line x1="271" y1="122" x2="301" y2="122"></line>
            <line x1="103" y1="360" x2="133" y2="360"></line><line x1="271" y1="360" x2="301" y2="360"></line>
          </g>
          <g fill="none" stroke="#6B7684" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M155 114 L194 108 M155 130 L195 136 M156 122 L195 123"></path>
            <path d="M249 114 L210 108 M249 130 L209 136 M248 122 L209 123"></path>
            <path d="M161 352 L196 346 M161 368 L196 372 M162 360 L196 359"></path>
            <path d="M243 352 L208 346 M243 368 L208 372 M242 360 L208 359"></path>
            <path d="M202 382 L202 394"></path>
          </g>
          <g filter="url(#carGlowT)" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round">
            <g fill="${p.floor.f}" stroke="${p.floor.s}">
              <path d="M178 180 C 166 182 156 190 152 204 L 150 222 C 149 260 150 296 152 316 C 154 326 158 334 163 338 L 163 356 L 241 356 L 241 338 C 246 334 250 326 252 316 C 254 296 255 260 254 222 L 252 204 C 248 190 238 182 226 180 Z"></path>
            </g>
            <g fill="none" stroke="${p.floor.s}" stroke-width="1.2">
              <path d="M156 232 C 155 262 156 292 160 314 M248 232 C 249 262 248 292 244 314"></path>
              <path d="M149 166 C 145 174 145 184 148 192 M255 166 C 259 174 259 184 256 192"></path>
            </g>
            <g fill="${p.side.f}" stroke="${p.side.s}">
              <path d="M180 196 C 167 196 157 200 154 210 C 151 228 152 254 160 278 C 166 294 174 306 184 314 L 186 296 L 181 250 Z"></path>
              <path d="M224 196 C 237 196 247 200 250 210 C 253 228 252 254 244 278 C 238 294 230 306 220 314 L 218 296 L 223 250 Z"></path>
            </g>
            <g fill="none" stroke="${p.side.s}" stroke-width="1.2">
              <path d="M156 209 C 162 203 171 200 180 200 M248 209 C 242 203 233 200 224 200"></path>
              <path d="M159 232 C 160 255 166 276 177 296 M245 232 C 244 255 238 276 227 296"></path>
            </g>
            <g fill="#12161B" stroke="#8B95A5" stroke-width="1.5">
              <path d="M202 40 C 206 40 207 45 207 51 L 210 112 C 212 140 218 164 225 186 L 226 250 L 178 250 L 179 186 C 186 164 192 140 194 112 L 197 51 C 197 45 198 40 202 40 Z"></path>
            </g>
            <g fill="none" stroke="#8B95A5" stroke-width="1.3">
              <path d="M202 48 L202 104" stroke-opacity="0.45"></path>
              <rect x="190" y="196" width="24" height="44" rx="11"></rect>
              <circle cx="202" cy="226" r="6"></circle>
              <path d="M188 216 C 188 198 195 189 202 189 C 209 189 216 198 216 216 M202 181 L202 189"></path>
              <ellipse cx="173" cy="206" rx="6" ry="2.8"></ellipse>
              <ellipse cx="231" cy="206" rx="6" ry="2.8"></ellipse>
            </g>
            <g fill="${p.eng.f}" stroke="${p.eng.s}">
              <path d="M180 246 L 224 246 C 226 270 222 300 214 326 C 210 340 206 350 202 352 C 198 350 194 340 190 326 C 182 300 178 270 180 246 Z"></path>
            </g>
            <g fill="${p.eng.s}" fill-opacity="0.5" stroke="none">
              <path d="M198 278 C 198 275 206 275 206 278 L 206 283 L 210 283 C 212 283 212 293 210 293 L 206 293 L 206 300 C 206 303 198 303 198 300 L 198 293 L 194 293 C 192 293 192 283 194 283 L 198 283 Z"></path>
            </g>
            <g fill="none" stroke="${p.eng.s}" stroke-width="1.2">
              <ellipse cx="202" cy="254" rx="7" ry="4.5"></ellipse>
              <path d="M202 308 L202 346"></path>
            </g>
            <g fill="${p.diff.f}" stroke="${p.diff.s}">
              <path d="M170 360 L 234 360 L 236 380 C 236 384 233 386 229 386 L 175 386 C 171 386 168 384 168 380 Z"></path>
            </g>
            <g fill="none" stroke="${p.diff.s}" stroke-width="1.2">
              <path d="M180 363 L180 384 M190 363 L190 384 M214 363 L214 384 M224 363 L224 384"></path>
            </g>
            <g fill="${p.gb.f}" stroke="${p.gb.s}"><rect x="196" y="340" width="12" height="42" rx="5"></rect></g>
            <g fill="${p.rw.f}" stroke="${p.rw.s}">
              <path d="M170 395 C 186 392 218 392 234 395 L 234 400.5 C 218 397.5 186 397.5 170 400.5 Z"></path>
              <path d="M171 403 C 186 400.5 218 400.5 233 403 L 233 407 C 218 404.5 186 404.5 171 407 Z"></path>
              <path d="M172 409.5 C 186 407.5 218 407.5 232 409.5 L 230 413.5 C 216 411.5 188 411.5 174 413.5 Z"></path>
              <rect x="164" y="389" width="5" height="27" rx="2.5"></rect>
              <rect x="235" y="389" width="5" height="27" rx="2.5"></rect>
            </g>
            <g fill="${p.fwl.f}" stroke="${p.fwl.s}">
              <path d="M197.5 47 C 180 48 160 52 146 58 C 141.5 60 139.5 63.5 139.5 68 L 140.5 87 C 140.8 91 144.5 92.5 148 90.5 C 164 82.5 181 78.5 197.5 77.5 Z"></path>
              <path d="M197.5 62 C 181 63 162 68 141 75.5" fill="none" stroke-width="1.2"></path>
              <path d="M145.5 60.5 L 146.5 86.5" fill="none" stroke-width="1.2"></path>
            </g>
            <g fill="${p.fwr.f}" stroke="${p.fwr.s}" transform="matrix(-1 0 0 1 404 0)">
              <path d="M197.5 47 C 180 48 160 52 146 58 C 141.5 60 139.5 63.5 139.5 68 L 140.5 87 C 140.8 91 144.5 92.5 148 90.5 C 164 82.5 181 78.5 197.5 77.5 Z"></path>
              <path d="M197.5 62 C 181 63 162 68 141 75.5" fill="none" stroke-width="1.2"></path>
              <path d="M145.5 60.5 L 146.5 86.5" fill="none" stroke-width="1.2"></path>
            </g>
            <g stroke-width="2">
              <rect x="135.5" y="97.5" width="19.6" height="49" rx="6" fill="${tFL.wf}" stroke="${tFL.wc}"></rect>
              <rect x="248.9" y="97.5" width="19.6" height="49" rx="6" fill="${tFR.wf}" stroke="${tFR.wc}"></rect>
              <rect x="135.5" y="335" width="26" height="50" rx="7" fill="${tRL.wf}" stroke="${tRL.wc}"></rect>
              <rect x="242.5" y="335" width="26" height="50" rx="7" fill="${tRR.wf}" stroke="${tRR.wc}"></rect>
            </g>
            <g fill="none" stroke-width="0.9" stroke-opacity="0.45">
              <path d="M139.5 110 L151 110 M139.5 122 L151 122 M139.5 134 L151 134" stroke="${tFL.wc}"></path>
              <path d="M253 110 L264.5 110 M253 122 L264.5 122 M253 134 L264.5 134" stroke="${tFR.wc}"></path>
              <path d="M140 348 L157 348 M140 360 L157 360 M140 372 L157 372" stroke="${tRL.wc}"></path>
              <path d="M247 348 L264 348 M247 360 L264 360 M247 372 L264 372" stroke="${tRR.wc}"></path>
            </g>
          </g>
          <g stroke="none">
            <rect x="156.5" y="113" width="4" height="18" rx="1.5" fill="${tFL.bc}"></rect>
            <rect x="243.5" y="113" width="4" height="18" rx="1.5" fill="${tFR.bc}"></rect>
            <rect x="163" y="351" width="4" height="18" rx="1.5" fill="${tRL.bc}"></rect>
            <rect x="237" y="351" width="4" height="18" rx="1.5" fill="${tRR.bc}"></rect>
          </g>
          ${anel(54, 122, tFL)}${anel(350, 122, tFR)}${anel(54, 360, tRL)}${anel(350, 360, tRR)}
        </svg>
          ${asa(96, 42, 40, true, 'ASA', p.fwl)}${asa(268, 42, 40, false, 'ASA', p.fwr)}${asa(245, 388, 58, false, 'ASA TRAS.', p.rw)}
          ${roda(10, 78, tFL, 'FL')}${roda(306, 78, tFR, 'FR')}${roda(10, 316, tRL, 'RL')}${roda(306, 316, tRR, 'RR')}
        </div>
        </div>`;
}

// ---- pílula do estado da pista: bandeiras, Safety Car e os alertas mais importantes
const VL_PILULAS = {
  verde: ['#0C2416', '#2BB868', '#3DDC84'], amarelo: ['#2A2410', '#C9A50F', '#F5C518'], vermelho: ['#2A1215', '#FF4D4D', '#FF7A7A'],
  azul: ['#0F1E2E', '#3B82D0', '#4DA3FF'], cinza: ['#161B21', '#3A4450', '#98A2B3'],
};
function vlPilula(d) {
  const s = d.sessao, eu = d.eu;
  let texto = 'BANDEIRA VERDE', cor = 'verde';
  const al = alertasAtivos(d)[0];
  if (s.bandeira_vermelha) { texto = 'BANDEIRA VERMELHA'; cor = 'vermelho'; }
  else if (al && al.nivel === 'perigo') { texto = al.texto.toUpperCase(); cor = 'vermelho'; }
  else if (s.safety_car === 1) { texto = 'SAFETY CAR'; cor = 'amarelo'; }
  else if (s.safety_car === 2) { texto = 'VIRTUAL SAFETY CAR'; cor = 'amarelo'; }
  else if (al && al.nivel === 'aviso') { texto = al.texto.toUpperCase(); cor = al.id === 'azul' ? 'azul' : 'amarelo'; }
  else if (eu.bandeira === 2) { texto = 'BANDEIRA AZUL'; cor = 'azul'; }
  else if (s.safety_car === 3) { texto = 'VOLTA DE FORMAÇÃO'; cor = 'cinza'; }
  const [fundo, borda, c] = VL_PILULAS[cor];
  return `<span style="display: flex; align-items: center; gap: 10px; min-width: 0; background: ${fundo}; border: 1px solid ${borda}; color: ${c}; font-weight: 700; font-size: 19px; letter-spacing: .02em; padding: 7px 16px; border-radius: 12px; box-shadow: 0 0 14px ${c}33; white-space: nowrap; overflow: hidden; text-overflow: ellipsis"><span style="width: 14px; height: 14px; flex: none; border-radius: 50%; background: ${c}; box-shadow: 0 0 10px ${c}"></span><span style="overflow: hidden; text-overflow: ellipsis">${esc(texto)}</span></span>`;
}

// ---- setores da volta atual
function vlSetores(d) {
  const eu = d.eu, s = d.sessao;
  const meu = d.carros.find((c) => c.eu) || {};
  const ref = eu.melhor_setores || [];
  const sessao = eu.setores_sessao || [];
  const feitos = [eu.s1_ms, eu.s2_ms];
  const limites = s.setores_m || [];
  const dist = Math.max(0, meu.dist_volta || 0);
  return [0, 1, 2].map((k) => {
    const n = `Setor ${k + 1}`;
    const r = ref[k];
    const corRef = r && sessao[k] && r <= sessao[k] ? '#B57BFF' : '#3DDC84';
    if (k < (eu.setor || 0) && feitos[k]) {
      const t = feitos[k];
      const c = sessao[k] && t <= sessao[k] ? '#B57BFF' : (!r || t <= r) ? '#3DDC84' : '#F5C518';
      return { n, t: (t / 1000).toFixed(3), tc: c, c, sub: r ? `${fmtD(t - r)} vs tua melhor` : 'Sem referência', prog: '100%' };
    }
    if (k === (eu.setor || 0) && eu.estado_piloto !== 0) {
      const ini = k ? limites[k - 1] || 0 : 0, fim = limites[k] || 1;
      const prog = Math.max(0, Math.min(100, (dist - ini) / Math.max(fim - ini, 1) * 100));
      return { n, t: r ? (r / 1000).toFixed(3) : '—', tc: r ? corRef : '#98A2B3', c: '#B57BFF', sub: 'Referência · em curso', prog: prog.toFixed(0) + '%' };
    }
    return { n, t: r ? (r / 1000).toFixed(3) : '—', tc: r ? corRef : '#98A2B3', c: '#4DA3FF', sub: r ? 'Referência' : 'Sem referência', prog: '0%' };
  });
}

// ---- carros à frente e atrás
function vlVizinho(v, frente) {
  const titulo = frente ? 'À frente' : 'Atrás';
  if (!v) {
    return `<section class="p" style="padding: 10px 18px; display: flex; flex-direction: column">
        <span class="l">${titulo}</span>
        <div style="display: flex; align-items: baseline; justify-content: space-between"><b style="font-size: 36px; color: #6B7684">—</b><span style="font-size: 54px; font-weight: 700; line-height: 1.05; color: #6B7684">—</span></div>
        <span style="font-size: 17px; color: #6B7684; font-weight: 600">${frente ? 'Ninguém à frente' : 'Ninguém atrás'}</span>
      </section>`;
  }
  const cor = frente ? '#3DDC84' : '#FFB020';
  const dif = v.diferenca_volta;
  let tend = '&nbsp;', corT = '#98A2B3';
  if (dif != null) {
    if (frente) { tend = dif > 0 ? `▼ A recuperar ${dif.toFixed(2)} s/volta` : `▲ A perder ${Math.abs(dif).toFixed(2)} s/volta`; corT = dif > 0 ? '#3DDC84' : '#FFB020'; }
    else { tend = dif > 0 ? `▲ Aproxima-se ${dif.toFixed(2)} s/volta` : `▼ A afastar-se ${Math.abs(dif).toFixed(2)} s/volta`; corT = dif > 0 ? '#FFB020' : '#3DDC84'; }
  }
  return `<section class="p" style="padding: 10px 18px; display: flex; flex-direction: column">
        <span class="l">${titulo} · P${v.pos}</span>
        <div style="display: flex; align-items: baseline; justify-content: space-between"><b style="font-size: 36px">${esc(v.codigo)}</b><span style="font-size: 54px; font-weight: 700; line-height: 1.05; color: ${cor}">${v.gap_s.toFixed(3)}</span></div>
        <span style="font-size: 17px; color: ${corT}; font-weight: 600">${tend}</span>
      </section>`;
}

const vlRpm = (r) => String(Math.round(r || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
const vlMudanca = (g) => g == null ? '—' : g === 0 ? 'N' : g < 0 ? 'R' : String(g);

function renderVolante(d) {
  const eu = d.eu, s = d.sessao, cr = d.corrida || {};
  const acento = eu.cor || '#FFD12E';
  const total = s.voltas_total || 0;
  const volta = total ? Math.min(eu.volta, total) : eu.volta;
  const nCarros = d.carros.length;
  const ers = Math.max(0, Math.min(100, eu.ers_pct ?? 0));
  const margem = eu.margem_voltas;
  const delta = eu.delta_ms;
  const temDelta = delta != null;
  const bom = temDelta && delta <= 0;
  const caixaDelta = !temDelta ? ['#11161C', '#0B0F13', '#26303B', '#D5DCE4', '#98A2B3', 'none']
    : bom ? ['#0E2617', '#0A1A10', '#3DDC84', '#CFF5DD', '#3DDC84', '0 0 22px #3DDC8455'] : ['#2A1215', '#1A0B0D', '#FF4D4D', '#FFD6D6', '#FF4D4D', '0 0 22px #FF4D4D55'];
  const larg = temDelta ? Math.min(Math.abs(delta) / 500, 1) * 50 : 0;     // a barra vai até ±0.5 s
  const aero = eu.aero || {};
  const regras26 = aero.regras_2026 !== undefined ? aero.regras_2026 !== 0 : !!eu.aero;
  const aj = eu.ajuda || null;
  let aeroFrac = 0;
  if (regras26) aeroFrac = aero.modo === 1 || aero.disp ? 1 : aero.dist ? Math.max(0, 1 - aero.dist / 2000) : 0;
  else if (aj) aeroFrac = aj.disp ? 1 : aj.dist ? Math.max(0, 1 - aj.dist / 2000) : 0;
  const aeroDesc = regras26 ? (aero.modo === 1 ? 'Modo reta ativo' : aero.disp ? 'Modo reta disponível' : aero.dist ? `Modo reta disponível em ${aero.dist} metros` : 'Modo curva')
    : (aj && aj.disp ? 'DRS disponível' : aj && aj.dist ? `DRS disponível em ${aj.dist} metros` : 'DRS indisponível');
  const nomeAjuda = aj ? aj.nome.toUpperCase() : (regras26 ? 'OVERTAKE' : 'DRS');
  const ajudaTxt = aj && aj.ativo ? `${nomeAjuda} ATIVO` : aj && aj.disp ? `${nomeAjuda} DISPONÍVEL` : nomeAjuda;
  const ajudaLigada = aj && (aj.disp || aj.ativo);
  const setores = vlSetores(d);
  const vr = d.volta_rapida;
  const ultimaDif = eu.ultima_ms && eu.melhor_ms ? `${fmtD(eu.ultima_ms - eu.melhor_ms)} vs tua melhor` : '&nbsp;';
  const compCor = TC[eu.composto] || TC['?'];
  return `<div class="vl" style="width: ${VL_LARG}px; height: ${VL_ALT}px; box-sizing: border-box; padding: 14px; display: flex; flex-direction: column; gap: 12px; background: radial-gradient(ellipse at 50% 45%, #0E141B 0%, #05070A 75%); color: #F2F4F7; font-family: 'Barlow Semi Condensed', system-ui, sans-serif; font-variant-numeric: tabular-nums; overflow: hidden">

  <div style="height: 54px; display: grid; grid-template-columns: 196px 182px minmax(0, 1fr) 156px; gap: 10px">
    <div class="p" style="display: flex; align-items: center; justify-content: center; gap: 10px"><span class="l" style="font-size: 18px; color: #C9D1DB">POS</span><b style="font-size: 34px; color: ${acento}">P${eu.pos}</b><span style="font-size: 22px; color: #C9D1DB">/ ${nCarros}</span></div>
    <div class="p" style="display: flex; align-items: center; justify-content: center; gap: 10px"><span class="l" style="font-size: 18px; color: #C9D1DB">VOLTA</span><b style="font-size: 34px">${volta}</b><span style="font-size: 22px; color: #C9D1DB">/ ${total || '—'}</span></div>
    <div class="p" style="display: flex; align-items: center; gap: 12px; padding: 0 6px 0 16px; min-width: 0">
      <span style="width: 28px; height: 28px; flex: none; border-radius: 50%; border: 3px solid ${compCor}; box-sizing: border-box; display: inline-flex; align-items: center; justify-content: center; color: ${compCor}">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l3 7h7l-5.5 4.5 2 7.5-6.5-4.5-6.5 4.5 2-7.5L2 9h7z"></path></svg></span>
      <span style="font-size: 21px; font-weight: 600; white-space: nowrap">${TN[eu.composto] || '—'} · ${eu.idade ?? 0} voltas</span>
      <span style="flex: 1"></span>
      ${vlPilula(d)}
    </div>
    <div class="p" style="display: flex; align-items: center; justify-content: space-around; padding: 0 4px">
      <button type="button" class="ic" data-acao="definicoes" aria-label="Definições"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h9M17 7h3M4 17h3M11 17h9"></path><circle cx="15" cy="7" r="2.2"></circle><circle cx="9" cy="17" r="2.2"></circle></svg></button>
      <button type="button" class="ic" data-acao="ecra-inteiro" aria-label="Ecrã inteiro"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7"></path></svg></button>
      <button type="button" class="ic" data-acao="imagem" aria-label="Guardar imagem do ecrã"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"></path></svg></button>
    </div>
  </div>

  <div style="flex: 1; min-height: 0; display: grid; grid-template-columns: 350px minmax(0, 1fr) 340px; gap: 12px">

    <div style="display: flex; flex-direction: column; gap: 10px; min-height: 0">
      <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); grid-template-rows: 104px 78px; gap: 10px">
        <section class="p" style="padding: 10px 14px; display: flex; flex-direction: column; justify-content: space-between; border-color: #2D6FB8; box-shadow: 0 0 16px #4DA3FF33, inset 0 1px 0 #ffffff0d">
          <div style="display: flex; justify-content: space-between; align-items: flex-start"><span class="l">ERS</span>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="#4DA3FF" aria-hidden="true"><path d="M13 2L4 14h7l-1 8 9-12h-7z"></path></svg></div>
          <span style="font-size: 44px; font-weight: 700; line-height: .9; color: #4DA3FF">${eu.ers_pct ?? '—'}%</span>
          <div style="height: 8px; background: #1A2330; border-radius: 4px; overflow: hidden"><div style="width: ${ers}%; height: 100%; background: linear-gradient(90deg, #2F8CFF, #6CC0FF); border-radius: 4px"></div></div>
        </section>
        <section class="p" style="padding: 10px 14px; display: flex; flex-direction: column; justify-content: space-between">
          <div style="display: flex; justify-content: space-between; align-items: flex-start"><span class="l">Combustível</span>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#C9D1DB" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M4 21V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v16M3 21h12M6 9h6M14 10h2a2 2 0 0 1 2 2v4a1.5 1.5 0 0 0 3 0V8l-3-3"></path></svg></div>
          <span style="font-size: 44px; font-weight: 700; line-height: .9; color: ${margem == null ? '#F2F4F7' : margem >= 0 ? '#3DDC84' : '#FF4D4D'}">${margem == null ? '—' : (margem >= 0 ? '+' : '−') + Math.abs(margem).toFixed(2)}</span>
          <span style="font-size: 17px; color: #C9D1DB">voltas · ${eu.combustivel ?? '—'} kg</span>
        </section>
        <section class="p" style="padding: 8px 14px; display: flex; justify-content: space-between; align-items: center">
          <div style="display: flex; flex-direction: column"><span class="l">Travões</span><span style="font-size: 34px; font-weight: 700; line-height: 1.05">${eu.travao_bias ?? '—'}%</span></div>
          <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#98A2B3" stroke-width="1.5" aria-hidden="true"><circle cx="12" cy="12" r="9.5"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3"></path></svg>
        </section>
        <section class="p" style="padding: 8px 14px; display: flex; justify-content: space-between; align-items: center">
          <div style="display: flex; flex-direction: column"><span class="l">Motor</span><span style="font-size: 34px; font-weight: 700; line-height: 1.05">${eu.motor_temp ?? '—'}<span style="font-size: 18px; vertical-align: top">°C</span></span></div>
          <svg width="30" height="38" viewBox="0 0 24 24" fill="none" stroke="#98A2B3" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M10 14V5a2 2 0 0 1 4 0v9a4 4 0 1 1-4 0z"></path><path d="M12 9v7"></path></svg>
        </section>
      </div>
      <section class="p" style="flex: 1; min-height: 0; padding: 6px; display: flex; align-items: center; justify-content: center">
        ${vlCarro(eu)}
      </section>
    </div>

    <section style="position: relative; overflow: hidden">
      <svg style="position: absolute; inset: 0" width="438" height="588" viewBox="0 0 438 588" aria-hidden="true">
        <defs><filter id="fGlow" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="3" result="b"></feGaussianBlur><feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter>
          <radialGradient id="fFundo" cx="50%" cy="38%" r="65%"><stop offset="0" stop-color="#0E141B"></stop><stop offset="1" stop-color="#05070A"></stop></radialGradient></defs>
        <path d="M30 2 H408 Q436 2 436 30 V318 L390 556 Q384 586 354 586 H84 Q54 586 48 556 L2 318 V30 Q2 2 30 2 Z" fill="url(#fFundo)" stroke="#2F6FB0" stroke-width="1.6" stroke-opacity="0.8" filter="url(#fGlow)"></path>
      </svg>
      <svg style="position: absolute; left: 0; top: 4px" width="438" height="440" viewBox="0 0 438 440" aria-hidden="true">
        <defs>
          <filter id="gGlow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="5" result="b"></feGaussianBlur><feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter>
          <filter id="lGlow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.5" result="b"></feGaussianBlur><feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter>
        </defs>
        <path d="M114.8 335.9 A150 150 0 1 1 360.3 177.6" fill="none" stroke="#2BFF8C" stroke-width="2" stroke-opacity="0.6" filter="url(#lGlow)"></path>
        <path d="M422.6 147.3 A219 219 0 0 1 365.5 390.7" fill="none" stroke="#8A5CFF" stroke-width="2" stroke-opacity="0.85" filter="url(#lGlow)"></path>
        ${vlContaRotacoes(eu)}
      </svg>
      <span style="position: absolute; left: 0; right: 0; top: 116px; text-align: center; font-family: 'Poppins', sans-serif; font-size: 180px; font-weight: 700; line-height: 136px">${vlMudanca(eu.mudanca)}</span>
      <span style="position: absolute; left: 0; right: 0; top: 268px; text-align: center; font-family: 'Poppins', sans-serif; font-size: 96px; font-weight: 700; line-height: 80px; letter-spacing: -.02em" aria-label="${eu.velocidade ?? 0} km/h">${eu.velocidade ?? '—'}</span>
      <span style="position: absolute; left: 0; right: 0; top: 372px; text-align: center; font-family: 'Poppins', sans-serif; font-size: 28px; font-weight: 500; color: #B8C0CC">${vlRpm(eu.rpm)} rpm</span>
      <div style="position: absolute; left: 0; right: 0; bottom: 34px; display: flex; justify-content: center">
        <div style="display: flex; align-items: baseline; gap: 12px; padding: 8px 18px; border-radius: 12px; background: #0B1015; border: 1px solid #26303B">
          <span class="l" style="color: #98A2B3">Volta atual</span>
          <span style="font-size: 38px; font-weight: 700; line-height: 1">${fmtV(eu.atual_ms)}</span>
          ${temDelta ? `<span style="font-size: 18px; font-weight: 700; color: ${bom ? '#3DDC84' : '#FF4D4D'}">${fmtD(delta)}</span>` : ''}
        </div>
      </div>
    </section>

    <div style="display: flex; flex-direction: column; gap: 10px; min-height: 0">
      <section class="p" style="padding: 12px 18px; display: flex; flex-direction: column; background: linear-gradient(180deg, ${caixaDelta[0]} 0%, ${caixaDelta[1]} 100%); border: 2px solid ${caixaDelta[2]}; box-shadow: ${caixaDelta[5]}">
        <span class="l" style="color: ${caixaDelta[3]}">Delta · tua melhor volta</span>
        ${temDelta
    ? `<span style="font-size: 92px; font-weight: 700; line-height: 1; color: ${caixaDelta[4]}; text-align: center; text-shadow: 0 0 18px ${caixaDelta[4]}66">${fmtD(delta)}</span>`
    : `<span style="height: 92px; display: flex; align-items: center; justify-content: center; font-size: 30px; font-weight: 700; color: ${caixaDelta[4]}; white-space: nowrap">${eu.melhor_ms ? 'À espera de uma volta' : 'Sem volta de referência'}</span>`}
        <div style="height: 6px; background: ${bom || !temDelta ? '#163322' : '#3A1A1D'}; border-radius: 3px; position: relative; margin: 6px 0">
          <span style="position: absolute; left: 50%; top: -5px; width: 3px; height: 16px; background: ${caixaDelta[4]}; border-radius: 2px"></span>
          ${temDelta ? `<span style="position: absolute; ${bom ? `left: ${50 - larg}%` : 'left: 50%'}; width: ${larg}%; height: 100%; background: ${caixaDelta[4]}; border-radius: 3px"></span>` : ''}
        </div>
        <span style="font-size: 20px; color: ${caixaDelta[3]}">Previsão <b style="color: #FFFFFF; margin-left: 10px">${fmtV(eu.previsao_ms)}</b></span>
      </section>
      ${vlVizinho(cr.frente, true)}
      ${vlVizinho(cr.atras, false)}
      <section class="p" style="height: 50px; flex: none; padding: 0 16px; display: flex; align-items: center; gap: 14px">
        <span style="font-size: 26px; font-weight: 700; font-style: italic; color: #D5DCE4; letter-spacing: .02em; white-space: nowrap">${regras26 ? 'AERO' : 'DRS'}</span>
        <div style="flex: 1; height: 14px; background: #1A1F26; border-radius: 7px; overflow: hidden" role="img" aria-label="${esc(aeroDesc)}"><div style="width: ${(aeroFrac * 100).toFixed(0)}%; height: 100%; background: linear-gradient(90deg, #2BB868, #5BE38A); border-radius: 7px; box-shadow: 0 0 10px #3DDC8466"></div></div>
      </section>
      <span style="height: 54px; flex: none; display: flex; align-items: center; justify-content: center; gap: 12px; border-radius: 14px; ${ajudaLigada ? 'background: linear-gradient(180deg, #FFD84D, #F2B705); color: #1A1400; box-shadow: 0 0 22px #F2B70577' : 'background: #11161C; border: 1px solid #26303B; color: #6B7684'}; font-size: 23px; font-weight: 700; letter-spacing: .02em">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round" aria-hidden="true"><path d="M13 2L4 14h7l-1 8 9-12h-7z"></path></svg>${ajudaTxt}</span>
    </div>
  </div>

  <div style="height: 126px; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px">
    ${setores.map((st) => `<section class="p" style="position: relative; overflow: hidden; padding: 12px 12px 14px; display: flex; flex-direction: column; align-items: center; gap: 2px; border-top: 3px solid ${st.c}">
        <span class="l" style="color: ${st.c}; font-size: 17px">${st.n}</span>
        <span style="font-size: 44px; font-weight: 700; line-height: 1.05; color: ${st.tc}">${st.t}</span>
        <span style="font-size: 17px; color: #C9D1DB">${st.sub}</span>
        <div style="position: absolute; left: 8px; right: 8px; bottom: 6px; height: 5px; background: #1A1F26; border-radius: 3px; overflow: hidden"><div style="width: ${st.prog}; height: 100%; background: ${st.c}; border-radius: 3px"></div></div>
      </section>`).join('')}
    <section class="p" style="padding: 12px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px">
      <span class="l" style="font-size: 17px">Melhor volta</span>
      <span style="display: flex; align-items: center; gap: 8px; font-size: 44px; font-weight: 700; line-height: 1.05; color: #B57BFF">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 18h18l-1.6-10-4.9 4.6L12 5l-2.5 7.6L4.6 8z"></path></svg>${vr ? fmtV(vr.ms) : '—'}</span>
      <span style="font-size: 17px; color: #C9D1DB">${vr ? `${esc(vr.codigo)}${vr.volta ? ' · volta ' + vr.volta : ''}` : '&nbsp;'}</span>
    </section>
    <section class="p" style="padding: 12px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px">
      <span class="l" style="font-size: 17px">Última volta</span>
      <span style="font-size: 44px; font-weight: 700; line-height: 1.05">${fmtV(eu.ultima_ms)}</span>
      <span style="font-size: 17px; color: #C9D1DB">${ultimaDif}</span>
    </section>
  </div>
</div>`;
}

// ---- botões da barra de cima: ecrã inteiro e guardar imagem
function vlEcraInteiro() {
  const doc = document, el = doc.documentElement;
  const ativo = doc.fullscreenElement || doc.webkitFullscreenElement;
  try {
    if (ativo) (doc.exitFullscreen || doc.webkitExitFullscreen).call(doc);
    else if (el.requestFullscreen) el.requestFullscreen().catch(() => vlAviso('Este browser não deixa pôr em ecrã inteiro. No iPad, usa "Partilhar → Adicionar ao ecrã principal".'));
    else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
    else vlAviso('Este browser não deixa pôr em ecrã inteiro. No iPad, usa "Partilhar → Adicionar ao ecrã principal".');
  } catch (e) {
    vlAviso('Não consegui pôr em ecrã inteiro.');
  }
}

async function vlGuardarImagem() {
  // desenha o ecrã num canvas (SVG com o HTML lá dentro) e descarrega um PNG
  try {
    const alvo = document.querySelector('.vl');
    if (!alvo) return;
    const css = [...document.styleSheets].map((f) => {
      try { return [...f.cssRules].map((r) => r.cssText).join('\n'); } catch (e) { return ''; }   // folhas de outro site (fontes) não se podem ler
    }).join('\n');
    const html = new XMLSerializer().serializeToString(alvo);
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${VL_LARG}" height="${VL_ALT}"><foreignObject width="100%" height="100%"><div xmlns="http://www.w3.org/1999/xhtml"><style>${css}</style>${html}</div></foreignObject></svg>`;
    const img = new Image();
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    await img.decode();
    const canvas = document.createElement('canvas');
    canvas.width = VL_LARG * 2; canvas.height = VL_ALT * 2;
    const g = canvas.getContext('2d');
    g.scale(2, 2);
    g.drawImage(img, 0, 0);
    const blob = await new Promise((ok) => canvas.toBlob(ok, 'image/png'));
    if (!blob) throw new Error('sem imagem');
    const a = document.createElement('a');
    const agora = new Date();
    a.download = `f1dash-${agora.toISOString().slice(0, 19).replace(/[:T]/g, '-')}.png`;
    a.href = URL.createObjectURL(blob);
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    vlAviso('Imagem guardada');
  } catch (e) {
    vlAviso('Este browser não deixa guardar a imagem. No iPad, carrega no botão de cima e no de volume + ao mesmo tempo.');
  }
}

let vlTemporizador = null;
function vlAviso(texto) {
  let el = document.getElementById('aviso-volante');
  if (!el) {
    el = document.createElement('div');
    el.id = 'aviso-volante';
    el.setAttribute('role', 'status');
    document.body.appendChild(el);
  }
  el.textContent = texto;
  el.hidden = false;
  clearTimeout(vlTemporizador);
  vlTemporizador = setTimeout(() => { el.hidden = true; }, 4000);
}
