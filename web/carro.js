// Desenho do carro visto de cima (à escala de um carro de 2026) com dano por peça e anéis de vida dos pneus.
/* exported blocoCarro */
const VERDE = '#5BE34A', AMARELO = '#E8D23A', LARANJA = '#F2A33A', VERMELHO = '#FF4D4D';
const corDano = (v) => v < 5 ? VERDE : v < 25 ? AMARELO : v < 50 ? LARANJA : VERMELHO;
const corVida = (l) => l >= 70 ? VERDE : l >= 50 ? AMARELO : l >= 30 ? LARANJA : VERMELHO;
const corTempPneu = (t) => t < 80 ? '#4DA3FF' : t <= 100 ? '#3DDC84' : t <= 108 ? '#FFB020' : '#FF4D4D';
const corTravao = (b) => b < 300 ? '#4DA3FF' : b <= 950 ? '#3DDC84' : b <= 1100 ? '#FFB020' : '#FF4D4D';

function blocoCarro(eu) {
  const d = eu.danos || {};
  const des = d.desgaste || [0, 0, 0, 0];
  const sup = eu.pneus_sup || [0, 0, 0, 0];
  const int = eu.pneus_int || [0, 0, 0, 0];
  const trv = eu.travoes || [0, 0, 0, 0];
  const C = 2 * Math.PI * 46;
  // arrays do jogo: 0 TE, 1 TD, 2 FE, 3 FD
  const pneu = (k) => {
    const vida = Math.max(0, Math.round(100 - des[k]));
    const c = corVida(vida);
    return { vida, c, f: c + '40', dash: (vida / 100 * C).toFixed(1) + ' ' + C.toFixed(1),
      s: sup[k], sc: corTempPneu(sup[k]), i: int[k], ic: corTempPneu(int[k]), b: trv[k], bc: corTravao(trv[k]) };
  };
  const FE = pneu(2), FD = pneu(3), TE = pneu(0), TD = pneu(1);
  const st = (v) => ({ v: v || 0, s: corDano(v || 0), f: corDano(v || 0) + '40' });
  const motorQuente = (eu.motor_temp || 0) > 125 ? VERMELHO : (eu.motor_temp || 0) > 115 ? LARANJA : null;
  const p = {
    fwl: st(d.asa_fe), fwr: st(d.asa_fd), rw: st(d.asa_tras), floor: st(d.fundo), diff: st(d.difusor),
    side: st(d.pontoes), gb: st(d.caixa), eng: motorQuente ? { v: d.motor || 0, s: motorQuente, f: motorQuente + '4D' } : st(d.motor),
  };
  const asaPainel = `
    <path d="M197.5 47 C 180 48 160 52 146 58 C 141.5 60 139.5 63.5 139.5 68 L 140.5 87 C 140.8 91 144.5 92.5 148 90.5 C 164 82.5 181 78.5 197.5 77.5 Z"></path>
    <path d="M197.5 62 C 181 63 162 68 141 75.5" fill="none" stroke-width="1.2"></path>
    <path d="M145.5 60.5 L 146.5 86.5" fill="none" stroke-width="1.2"></path>`;
  const anel = (t, nome, cx, cy) => `
    <circle cx="${cx}" cy="${cy}" r="47" fill="#0A0C0F" fill-opacity="0.75"></circle>
    <circle cx="${cx}" cy="${cy}" r="46" fill="none" stroke="${t.c}" stroke-opacity="0.35" stroke-width="2.5"></circle>
    <circle cx="${cx}" cy="${cy}" r="46" fill="none" stroke="${t.c}" stroke-width="6" stroke-linecap="round" stroke-dasharray="${t.dash}" transform="rotate(-90 ${cx} ${cy})" filter="url(#brilho)"></circle>`;
  const texto = (t, nome, cx, cy) => `
    <div class="abs w88 h88 ai-c jc-c tc" style="left:${cx - 44}px;top:${cy - 44}px;display:flex;flex-direction:column;line-height:1.1">
      <span class="f11 fw6 c-dim" style="letter-spacing:.14em">${nome}</span>
      <span class="f30 fw7 lh1" style="color:${t.c}">${t.vida}%</span>
      <span class="f12 fw6"><span style="color:${t.sc}">${t.s}°</span><span style="color:#6B7684"> | </span><span style="color:${t.ic}">${t.i}°</span></span>
      <span class="f11 c-dim">T <b style="color:${t.bc}">${t.b}°</b></span>
    </div>`;
  const etiquetaAsa = (x, y, w, alin, titulo, part) => `
    <div class="abs" style="left:${x}px;top:${y}px;width:${w}px;text-align:${alin};display:flex;flex-direction:column;line-height:1.1">
      <span class="f10 fw6 c-dim" style="letter-spacing:.12em">${titulo}</span>
      <span class="f17 fw7" style="color:${part.s}">${part.v}%</span>
    </div>`;
  const svg = `
  <svg class="abs" style="left:0;top:0" width="404" height="424" viewBox="0 0 404 424" role="img" aria-label="Carro visto de cima: peças coloridas pelo dano e pneus pela vida restante">
    <defs><filter id="brilho" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.4" result="b"></feGaussianBlur><feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge></filter></defs>
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
    <g filter="url(#brilho)" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round">
      <g fill="${p.floor.f}" stroke="${p.floor.s}"><path d="M178 180 C 166 182 156 190 152 204 L 150 222 C 149 260 150 296 152 316 C 154 326 158 334 163 338 L 163 356 L 241 356 L 241 338 C 246 334 250 326 252 316 C 254 296 255 260 254 222 L 252 204 C 248 190 238 182 226 180 Z"></path></g>
      <g fill="none" stroke="${p.floor.s}" stroke-width="1.2"><path d="M156 232 C 155 262 156 292 160 314 M248 232 C 249 262 248 292 244 314"></path><path d="M149 166 C 145 174 145 184 148 192 M255 166 C 259 174 259 184 256 192"></path></g>
      <g fill="${p.side.f}" stroke="${p.side.s}">
        <path d="M180 196 C 167 196 157 200 154 210 C 151 228 152 254 160 278 C 166 294 174 306 184 314 L 186 296 L 181 250 Z"></path>
        <path d="M224 196 C 237 196 247 200 250 210 C 253 228 252 254 244 278 C 238 294 230 306 220 314 L 218 296 L 223 250 Z"></path>
      </g>
      <g fill="none" stroke="${p.side.s}" stroke-width="1.2"><path d="M156 209 C 162 203 171 200 180 200 M248 209 C 242 203 233 200 224 200"></path><path d="M159 232 C 160 255 166 276 177 296 M245 232 C 244 255 238 276 227 296"></path></g>
      <g fill="#12161B" stroke="#8B95A5" stroke-width="1.5"><path d="M202 40 C 206 40 207 45 207 51 L 210 112 C 212 140 218 164 225 186 L 226 250 L 178 250 L 179 186 C 186 164 192 140 194 112 L 197 51 C 197 45 198 40 202 40 Z"></path></g>
      <g fill="none" stroke="#8B95A5" stroke-width="1.3">
        <path d="M202 48 L202 104" stroke-opacity="0.45"></path><rect x="190" y="196" width="24" height="44" rx="11"></rect>
        <circle cx="202" cy="226" r="6"></circle><path d="M188 216 C 188 198 195 189 202 189 C 209 189 216 198 216 216 M202 181 L202 189"></path>
        <ellipse cx="173" cy="206" rx="6" ry="2.8"></ellipse><ellipse cx="231" cy="206" rx="6" ry="2.8"></ellipse>
      </g>
      <g fill="${p.eng.f}" stroke="${p.eng.s}"><path d="M180 246 L 224 246 C 226 270 222 300 214 326 C 210 340 206 350 202 352 C 198 350 194 340 190 326 C 182 300 178 270 180 246 Z"></path></g>
      <g fill="${p.eng.s}" fill-opacity="0.5" stroke="none"><path d="M198 278 C 198 275 206 275 206 278 L 206 283 L 210 283 C 212 283 212 293 210 293 L 206 293 L 206 300 C 206 303 198 303 198 300 L 198 293 L 194 293 C 192 293 192 283 194 283 L 198 283 Z"></path></g>
      <g fill="none" stroke="${p.eng.s}" stroke-width="1.2"><ellipse cx="202" cy="254" rx="7" ry="4.5"></ellipse><path d="M202 308 L202 346"></path></g>
      <g fill="${p.diff.f}" stroke="${p.diff.s}"><path d="M170 360 L 234 360 L 236 380 C 236 384 233 386 229 386 L 175 386 C 171 386 168 384 168 380 Z"></path></g>
      <g fill="none" stroke="${p.diff.s}" stroke-width="1.2"><path d="M180 363 L180 384 M190 363 L190 384 M214 363 L214 384 M224 363 L224 384"></path></g>
      <g fill="${p.gb.f}" stroke="${p.gb.s}"><rect x="196" y="340" width="12" height="42" rx="5"></rect></g>
      <g fill="${p.rw.f}" stroke="${p.rw.s}">
        <path d="M170 395 C 186 392 218 392 234 395 L 234 400.5 C 218 397.5 186 397.5 170 400.5 Z"></path>
        <path d="M171 403 C 186 400.5 218 400.5 233 403 L 233 407 C 218 404.5 186 404.5 171 407 Z"></path>
        <path d="M172 409.5 C 186 407.5 218 407.5 232 409.5 L 230 413.5 C 216 411.5 188 411.5 174 413.5 Z"></path>
        <rect x="164" y="389" width="5" height="27" rx="2.5"></rect><rect x="235" y="389" width="5" height="27" rx="2.5"></rect>
      </g>
      <g fill="${p.fwl.f}" stroke="${p.fwl.s}">${asaPainel}</g>
      <g fill="${p.fwr.f}" stroke="${p.fwr.s}" transform="matrix(-1 0 0 1 404 0)">${asaPainel}</g>
      <g stroke-width="2">
        <rect x="135.5" y="97.5" width="19.6" height="49" rx="6" fill="${FE.f}" stroke="${FE.c}"></rect>
        <rect x="248.9" y="97.5" width="19.6" height="49" rx="6" fill="${FD.f}" stroke="${FD.c}"></rect>
        <rect x="135.5" y="335" width="26" height="50" rx="7" fill="${TE.f}" stroke="${TE.c}"></rect>
        <rect x="242.5" y="335" width="26" height="50" rx="7" fill="${TD.f}" stroke="${TD.c}"></rect>
      </g>
    </g>
    <g stroke="none">
      <rect x="156.5" y="113" width="4" height="18" rx="1.5" fill="${FE.bc}"></rect><rect x="243.5" y="113" width="4" height="18" rx="1.5" fill="${FD.bc}"></rect>
      <rect x="163" y="351" width="4" height="18" rx="1.5" fill="${TE.bc}"></rect><rect x="237" y="351" width="4" height="18" rx="1.5" fill="${TD.bc}"></rect>
    </g>
    ${anel(FE, 'FE', 54, 122)}${anel(FD, 'FD', 350, 122)}${anel(TE, 'TE', 54, 360)}${anel(TD, 'TD', 350, 360)}
  </svg>`;
  const html = `
  <div class="w404 h424" style="position:relative;align-self:center">
    ${svg}
    ${etiquetaAsa(96, 42, 40, 'right', 'ASA', p.fwl)}
    ${etiquetaAsa(268, 42, 40, 'left', 'ASA', p.fwr)}
    ${etiquetaAsa(245, 388, 58, 'left', 'ASA TRAS.', p.rw)}
    ${texto(FE, 'FE', 54, 122)}${texto(FD, 'FD', 350, 122)}${texto(TE, 'TE', 54, 360)}${texto(TD, 'TD', 350, 360)}
  </div>`;
  const motorTxt = `${eu.motor_temp ?? '—'}° · dano ${p.eng.v}%`;
  const chips = [
    ['Fundo', p.floor.s, p.floor.v + '%'], ['Pontões', p.side.s, p.side.v + '%'], ['Difusor', p.diff.s, p.diff.v + '%'],
    ['Caixa', p.gb.s, p.gb.v + '%'], ['Motor', p.eng.s, motorTxt, 'span 2'],
  ].map(([n, c, v, span]) => `
    <div class="ai-c g4 bg-cx r6 pd5-8 f13" style="grid-column:${span || 'auto'};display:flex;justify-content:space-between;border:1px solid #232B35">
      <span class="ai-c g5 c-dim" style="display:flex;white-space:nowrap"><span class="w7 h7 redondo" style="background:${c}"></span>${n}</span>
      <b class="f15" style="color:${c}">${v}</b>
    </div>`).join('');
  return { html, chips };
}
