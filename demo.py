"""Simulador: envia pacotes UDP iguais aos do jogo (formato 2026) para experimentar o painel sem jogar.

    python f1dash.py --demo corrida | qualificacao | treinos
"""
import math
import random
import socket
import struct
import time
from array import array

from telemetria import pacotes as P

FMT = 2026
N = P.MAX_CARROS[FMT]
L = 7004.0                  # Spa-Francorchamps
S2, S3 = 2120.0, 5290.0     # início dos setores 2 e 3 (m)
FRAC = (0.283, 0.457, 0.260)
PISTA_ID = 10
VOLTAS_CORRIDA = 44
UID = random.getrandbits(63)

# piloto, equipa (id 2026), cor principal, ritmo base (ms)
GRELHA = [
    ('Max VERSTAPPEN', 478, (54, 113, 198), 106050), ('Charles LECLERC', 477, (232, 0, 45), 106200),
    ('Lando NORRIS', 484, (255, 128, 0), 106310), ('Oscar PIASTRI', 484, (255, 128, 0), 106330),
    ('George RUSSELL', 476, (39, 244, 210), 106280), ('Lewis HAMILTON', 477, (232, 0, 45), 106420),
    ('Fernando ALONSO', 480, (34, 153, 113), 106520), ('Carlos SAINZ', 479, (100, 196, 255), 106560),
    ('Pierre GASLY', 481, (0, 147, 204), 106640), ('Alexander ALBON', 479, (100, 196, 255), 106660),
    ('Andrea Kimi ANTONELLI', 476, (39, 244, 210), 106600), ('Isack HADJAR', 478, (54, 113, 198), 106700),
    ('Nico HULKENBERG', 485, (187, 10, 48), 106760), ('Esteban OCON', 483, (182, 186, 189), 106800),
    ('Lance STROLL', 480, (34, 153, 113), 106840), ('Liam LAWSON', 482, (102, 146, 255), 106820),
    ('Oliver BEARMAN', 483, (182, 186, 189), 106880), ('Gabriel BORTOLETO', 485, (187, 10, 48), 106900),
    ('Franco COLAPINTO', 481, (0, 147, 204), 106960), ('Arvid LINDBLAD', 482, (102, 146, 255), 106980),
    ('Sergio PEREZ', 486, (229, 231, 235), 107050), ('Valtteri BOTTAS', 486, (229, 231, 235), 107150),
]
JOGADOR = 2   # jogas com um piloto que já existe (Lando Norris, McLaren)


def cab(pid, t, frame):
    return P.CABECALHO.pack(FMT, 25, 1, 25, 1, pid, UID, t, frame, frame, JOGADOR, 255)


class Carro:
    def __init__(self, i, nome, equipa, cor, base):
        self.i, self.nome, self.equipa, self.cor = i, nome, equipa, cor
        self.base = 106000 + (base - 106050) * 1.8   # diferenças de ritmo realistas entre equipas
        self.dist_total = 0.0
        self.volta = 1
        self.t_volta = 0.0
        self.volta_alvo = base
        self.s1 = self.s2 = 0
        self.ultima = 0
        self.historico = []          # (tempo, s1, s2, s3, valida)
        self.stints = []             # (fim, composto)
        self.composto = 17
        self.idade = 0
        self.paragens = 0
        self.plano_box = []
        self.box_ate = 0.0
        self.estado_piloto = 4
        self.grelha = i + 1
        self.ativo = True
        self.invalida = False
        self.penal = 0
        self.marcas = array('d')     # tempo de sessão a cada 10 m de distância total
        self.plano = []              # qualificação/treinos: lista de (tipo_volta)
        self.na_garagem_ate = 0.0
        self.speed_trap = 0.0
        self.terminou = False        # corrida: cortou a meta depois do líder (o jogo passa o resultado a "terminou")
        self.t_fim = None

    @property
    def dist_volta(self):
        return self.dist_total - (self.volta - 1) * L


class Simulador:
    def __init__(self, modo):
        self.modo = modo
        self.t = 0.0
        self.frame = 0
        self.carros = [Carro(i, *g) for i, g in enumerate(GRELHA)]
        while len(self.carros) < N:   # o formato 2026 tem 24 lugares; a grelha tem 22 carros
            c = Carro(len(self.carros), '', 0, (0, 0, 0), 110000)
            c.ativo = False
            self.carros.append(c)
        self.eventos = []
        self.mais_rapida = None
        self.hist_idx = 0
        self.rng = random.Random(7)
        self.desgaste = [0.0] * 4
        self.bandeira_xadrez = False
        self.pos_voltas = {}         # volta -> posição de cada carro ao começar essa volta (pacote de posições)
        self.fim_enviado = 0         # quantas vezes já mandou a classificação final (o jogo repete-a)
        self.taxa_desgaste = [1.4, 1.6, 1.9, 2.3]   # TE, TD, FE, FD (% por volta)
        self.combustivel = 70.0
        if modo == 'corrida':
            self.tipo, self.duracao = 15, 7200
            self._preparar_corrida()
        elif modo == 'qualificacao':
            self.tipo, self.duracao = 6, 900
            self._preparar_quali()
        else:
            self.tipo, self.duracao = 2, 3600
            self._preparar_treinos()

    # ---------------------------------------------------------------- preparação
    def _preparar_corrida(self):
        ordem = list(range(len(GRELHA)))
        self.rng.shuffle(ordem)
        ordem.sort(key=lambda k: self.carros[k].base + self.rng.uniform(-150, 150))
        for pos, k in enumerate(ordem):
            c = self.carros[k]
            c.grelha = pos + 1
            c.dist_total = -8.0 * pos
            c.volta = 0 if pos else 1
            c.composto = 16 if pos < 10 else 18
            lap_box = self.rng.choice([8, 9, 11, 13, 16, 18, 19])
            c.plano_box = [lap_box, lap_box + self.rng.choice([14, 16, 18])] if c.composto == 16 else [26 + self.rng.randint(0, 6)]
            c.stints = []
        self.combustivel = 1.58 * (VOLTAS_CORRIDA + 1) + 0.6
        self.carros[JOGADOR].plano_box = [8, 30]

    def _preparar_quali(self):
        for k, c in enumerate(self.carros[:len(GRELHA)]):
            c.ativo = k < 16 or k == JOGADOR
            c.estado_piloto = 0
            c.composto = 16
            c.na_garagem_ate = self.rng.uniform(5, 200)
        self.combustivel = 6.5

    def _preparar_treinos(self):
        for k, c in enumerate(self.carros[:len(GRELHA)]):
            c.estado_piloto = 0
            c.composto = self.rng.choice([16, 17, 18])
            c.na_garagem_ate = self.rng.uniform(5, 400)
        self.combustivel = 40.0

    # ---------------------------------------------------------------- simulação
    def _nova_volta_alvo(self, c):
        ritmo = c.base
        ritmo += c.idade * (55 if c.composto == 16 else 35 if c.composto == 17 else 22)
        ritmo -= (450 if c.composto == 16 else 200 if c.composto == 17 else 0)
        if self.modo == 'corrida':
            ritmo += 900 * (VOLTAS_CORRIDA - c.volta) / VOLTAS_CORRIDA   # combustível
        if self.modo != 'corrida':
            if c.estado_piloto == 3:
                ritmo *= 1.18
            elif c.estado_piloto == 2:
                ritmo *= 1.22
        c.volta_alvo = ritmo + self.rng.gauss(0, 140)

    def _velocidade(self, c):
        d = c.dist_volta % L
        alvo = c.volta_alvo / 1000
        if d < S2:
            return S2 / (alvo * FRAC[0])
        if d < S3:
            return (S3 - S2) / (alvo * FRAC[1])
        return (L - S3) / (alvo * FRAC[2])

    def _marcar(self, c):
        idx = int(max(c.dist_total, 0) // 10)
        while len(c.marcas) <= idx:
            c.marcas.append(self.t)

    def passo(self, dt):
        self.t += dt
        self.frame += 1
        for c in self.carros:
            if not c.ativo:
                continue
            if c.terminou:
                continue                    # depois da bandeira de xadrez o carro fica parado
            if self.t < c.box_ate:
                c.t_volta += dt * 1000      # parado na box: o cronómetro da volta continua (como no jogo)
                continue
            if self.t < c.na_garagem_ate:
                continue
            if self.modo != 'corrida' and c.estado_piloto == 0:
                # sai da garagem: volta de saída
                c.estado_piloto = 3
                c.t_volta = 0
                c.dist_total = (c.volta - 1) * L
                self._nova_volta_alvo(c)
            v = self._velocidade(c)
            c.dist_total += v * dt
            c.t_volta += dt * 1000
            if c.volta == 0:          # partida: a volta 1 começa ao cruzar a linha
                if c.dist_total >= 0:
                    c.volta = 1
                    c.t_volta = 0
                self._marcar(c)
                continue
            dv = c.dist_volta
            if dv >= S2 and not c.s1 and c.volta >= 1:
                c.s1 = int(c.t_volta)
            if dv >= S3 and not c.s2 and c.volta >= 1:
                c.s2 = int(c.t_volta) - c.s1
            if 6400 < dv < 6500:
                c.speed_trap = max(c.speed_trap, 318 + (107000 - c.base) / 60 + self.rng.uniform(0, 4))
            self._marcar(c)
            if dv >= L:
                self._fechar_volta(c)
        if self.modo == 'corrida':
            self._desgaste_jogador(dt)
        elif self.carros[JOGADOR].estado_piloto in (1, 2, 3):
            self._desgaste_jogador(dt)

    def _desgaste_jogador(self, dt):
        c = self.carros[JOGADOR]
        if self.t < c.box_ate or c.estado_piloto == 0:
            return
        frac = dt * 1000 / c.volta_alvo
        for k in range(4):
            self.desgaste[k] += self.taxa_desgaste[k] * frac
        self.combustivel = max(0.0, self.combustivel - 1.58 * frac)

    def _fechar_volta(self, c):
        tempo = int(c.t_volta)
        s3 = tempo - c.s1 - c.s2
        valida = not c.invalida
        c.historico.append((tempo, c.s1, c.s2, s3, valida))
        c.ultima = tempo
        if valida and (self.mais_rapida is None or tempo < self.mais_rapida) and (self.modo == 'corrida' or c.estado_piloto == 1):
            self.mais_rapida = tempo
            if self.modo == 'corrida' and c.volta > 1:
                self.eventos.append(b'FTLP' + struct.pack('<Bf', c.i, tempo / 1000).ljust(12, b'\x00'))
        c.volta += 1
        c.idade += 1
        c.t_volta = 0
        c.s1 = c.s2 = 0
        if self.modo == 'corrida':
            if c.volta - 1 >= VOLTAS_CORRIDA or self.bandeira_xadrez:
                if not self.bandeira_xadrez:
                    self.bandeira_xadrez = True
                    self.eventos.append(b'CHQF'.ljust(16, b'\x00'))
                c.terminou, c.t_fim = True, self.t
                c.volta -= 1                # o jogo não começa outra volta depois da meta
                return
            ordem = self._ordem()
            linha = self.pos_voltas.setdefault(c.volta, [0] * N)
            linha[c.i] = next(k for k, x in enumerate(ordem) if x is c) + 1
        c.invalida = self.rng.random() < 0.04 and self.modo != 'corrida'
        if self.modo == 'corrida':
            if c.plano_box and c.volta - 1 == c.plano_box[0]:
                c.plano_box.pop(0)
                c.stints.append((c.volta - 1, c.composto))
                c.paragens += 1
                c.box_ate = self.t + 21.4
                c.composto = 17 if c.composto == 16 else 18
                c.idade = 0
                if c.i == JOGADOR:
                    self.desgaste = [0.0] * 4
            if c.i == 9 and c.volta == 22 and not c.penal:
                c.penal = 5
                self.eventos.append(b'PENA' + bytes([4, 7, c.i, 255, 5, 22, 0]).ljust(12, b'\x00'))
        else:
            # qualificação / treinos: saída -> rápida -> entrada -> garagem
            if c.estado_piloto == 3:
                c.estado_piloto = 1
            elif c.estado_piloto == 1:
                limite = 1 if self.modo == 'qualificacao' else (8 if c.i == JOGADOR else self.rng.choice([1, 2, 5, 8]))
                feitas = sum(1 for _ in c.historico[-limite:])
                if self.modo == 'qualificacao' or len(c.historico) % (limite + 2) == 0:
                    c.estado_piloto = 2
            elif c.estado_piloto == 2:
                c.estado_piloto = 0
                c.na_garagem_ate = self.t + self.rng.uniform(60, 240)
                c.stints.append((c.volta - 1, c.composto))
                if self.modo == 'treinos':
                    c.composto = self.rng.choice([16, 17, 18])
                c.idade = 0
                if c.i == JOGADOR:
                    self.desgaste = [0.0] * 4
                    self.combustivel = 6.5 if self.modo == 'qualificacao' else 40.0
        self._nova_volta_alvo(c)

    # ---------------------------------------------------------------- posições e diferenças
    def _ordem(self):
        ativos = [c for c in self.carros if c.ativo]
        if self.modo == 'corrida':
            return sorted(ativos, key=lambda c: (0, c.t_fim) if c.terminou else (1, -c.dist_total))

        def melhor(c):
            t = [h[0] for h in c.historico if h[4] and h[0] < c.base * 1.1]
            return min(t) if t else 1e12
        return sorted(ativos, key=lambda c: (melhor(c), c.i))

    def _gap(self, de, para):
        """Tempo (ms) entre o carro `para` (à frente) e o `de` (atrás) no mesmo ponto da pista."""
        idx = int(max(de.dist_total, 0) // 10)
        if idx < len(para.marcas):
            return max(0, int((self.t - para.marcas[idx]) * 1000))
        return 0

    # ---------------------------------------------------------------- pacotes
    def pacotes(self):
        t, f = self.t, self.frame
        out = []
        ordem = self._ordem()
        pos = {c.i: k + 1 for k, c in enumerate(ordem)}
        lider = ordem[0]
        # Lap data
        b = bytearray(cab(2, t, f))
        for c in self.carros:
            if not c.ativo:
                b += P.LAP.pack(*([0] * 13 + [0] * 15 + [0, 0, 0, 0.0, 255]))
                continue
            k = pos[c.i]
            frente = ordem[k - 2] if k > 1 else None
            g_lider = self._gap(c, lider) if self.modo == 'corrida' and c is not lider else 0
            g_frente = self._gap(c, frente) if self.modo == 'corrida' and frente else 0
            na_box = self.t < c.box_ate
            b += P.LAP.pack(
                c.ultima, int(c.t_volta), c.s1 % 60000, c.s1 // 60000, c.s2 % 60000, c.s2 // 60000,
                g_frente % 60000, g_frente // 60000, g_lider % 60000, g_lider // 60000,
                float(c.dist_volta if c.volta >= 1 else c.dist_total), float(c.dist_total), 0.0,
                k, max(c.volta, 1), 2 if na_box else 0, c.paragens, 0 if c.dist_volta < S2 else 1 if c.dist_volta < S3 else 2,
                int(c.invalida), c.penal, 0, 0, 0, 0, c.grelha, c.estado_piloto, 3 if c.terminou else 2, 1 if na_box else 0,
                0, 0, 0, float(c.speed_trap), 255)
        b += bytes([255, 255])
        out.append(bytes(b))
        # Telemetria (todos), telemetria 2, estado, danos
        osc = math.sin(self.t / 3)
        tb = bytearray(cab(6, t, f))
        t2 = bytearray(cab(16, t, f))
        eb = bytearray(cab(7, t, f))
        db = bytearray(cab(10, t, f))
        for c in self.carros:
            eu = c.i == JOGADOR
            vel = int(self._velocidade(c) * 3.6 * (1 + 0.15 * osc)) if c.ativo else 0
            sup = [92 + 2 * osc, 94 + 2 * osc, 96 + 3 * osc, 104 + 3 * osc] if eu else [90, 90, 90, 90]
            inner = [97, 99, 101, 108] if eu else [95, 95, 95, 95]
            trav = [540 + 80 * osc, 551 + 80 * osc, 612 + 120 * osc, 655 + 120 * osc]
            tb += P.TELEMETRIA[FMT].pack(vel, 0.8, 0.0, 0.0, 0, 7, 11000, 0, 60, 0,
                                         *[int(x) for x in trav], *[int(x) for x in sup], *inner, 112,
                                         23.0 if True else 0, 23.0, 21.0, 21.0, 0, 0, 0, 0)
            ovtk = 1 if (eu and self.modo == 'corrida') else 0
            t2 += P.TELEMETRIA2.pack(0, 0, 420 if eu else 0, ovtk, 0, 0, 1, 0)
            comb = self.combustivel if eu else 30.0
            voltas_rest = VOLTAS_CORRIDA - max(c.volta, 1) + 1
            margem = comb / 1.58 - voltas_rest if self.modo == 'corrida' else comb / 1.58
            eb += P.ESTADO[FMT].pack(0, 0, 1, 56, 0, float(comb), 110.0, float(margem), 13000, 4000, 8, 0, 0,
                                     {16: 17, 17: 18, 18: 19}.get(c.composto, 18), c.composto, c.idade, 1,
                                     500000.0, 120000.0, 2.48e6 + 3e5 * osc, 1 if self.modo == 'corrida' else 2,
                                     1.6e6, 0.0, 4.0e6, 1.9e6, 0)
            des = [round(x, 1) for x in self.desgaste] if eu else [10.0] * 4
            db += P.DANOS.pack(*des, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                               0, 8 if eu else 0, 0, 3 if eu else 0, 0, 0, 0, 0, 0, 2 if eu else 0,
                               0, 12, 9, 18, 15, 20, 0, 0)
        tb += bytes([255, 255, 0])
        out += [bytes(tb), bytes(t2), bytes(eb), bytes(db)]
        # Histórico de um carro por pacote (como o jogo faz)
        c = self.carros[self.hist_idx % N]
        self.hist_idx += 1
        out.append(self._historico(c, t, f))
        # Sessão (2x por segundo)
        if self.frame % 10 == 0:
            out.append(self._sessao(t, f))
        if self.frame % 40 == 0:
            out.append(self._participantes(t, f))
            out.append(self._conjuntos(t, f))
        if self.modo == 'corrida' and self.frame % 20 == 0 and self.pos_voltas:
            out.append(self._posicoes_voltas(t, f))
        fim = self.modo == 'corrida' and all(c.terminou for c in self.carros if c.ativo)
        if self.modo != 'corrida' and self.t >= self.duracao and not self.fim_enviado:
            self.eventos.append(b'SEND'.ljust(16, b'\x00'))
            self.fim_enviado = 1
        if fim and self.fim_enviado < 5 and self.frame % 20 == 0:
            out.append(self._classificacao(t, f))          # o jogo manda a classificação final várias vezes
            if not self.fim_enviado:
                self.eventos.append(b'SEND'.ljust(16, b'\x00'))
            self.fim_enviado += 1
        for e in self.eventos:
            out.append(cab(3, t, f) + e)
        self.eventos = []
        return out

    PONTOS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]

    def _posicoes_voltas(self, t, f):
        voltas = sorted(self.pos_voltas)[:50]
        b = bytearray(cab(15, t, f)) + bytes([len(voltas), 0])
        for k in range(50):
            b += bytes(self.pos_voltas[voltas[k]]) if k < len(voltas) else bytes(N)
        return bytes(b)

    def _classificacao(self, t, f):
        ordem = self._ordem()
        b = bytearray(cab(8, t, f)) + bytes([len(ordem)])
        for c in self.carros:
            if not c.ativo:
                b += P.CLASSIFICACAO.pack(*([0] * 7), 0, 0.0, 0, 0, 0, *([0] * 24))
                continue
            pos = ordem.index(c) + 1
            stints = c.stints + [(c.volta, c.composto)]
            melhor = min((h[0] for h in c.historico if h[4]), default=0)
            reais = [{16: 17, 17: 18, 18: 19}.get(comp, 18) for _, comp in stints][:8]
            visuais = [comp for _, comp in stints][:8]
            fins = [fim for fim, _ in stints][:8]
            completa = lambda xs: xs + [0] * (8 - len(xs))
            b += P.CLASSIFICACAO.pack(pos, c.volta, c.grelha, self.PONTOS[pos - 1] if pos <= 10 else 0, c.paragens, 3, 0,
                                      melhor, float(c.t_fim or self.t), c.penal, 1 if c.penal else 0, len(stints),
                                      *completa(reais), *completa(visuais), *completa(fins))
        return bytes(b)

    def _historico(self, c, t, f):
        b = bytearray(cab(11, t, f))
        hist = c.historico[-99:]
        voltas = hist + ([(0, 0, 0, 0, True)] if c.ativo else [])
        validas = [(h[0], k) for k, h in enumerate(hist) if h[4] and h[0]]
        melhor = min(validas)[1] + 1 if validas else 0
        stints = c.stints + [(255, c.composto)]
        b += struct.pack('<7B', c.i, len(voltas), len(stints), melhor, melhor, melhor, melhor)
        for k in range(100):
            if k < len(voltas):
                tt, s1, s2, s3, ok = voltas[k]
                b += P.HIST_VOLTA.pack(tt, s1 % 60000, s1 // 60000, s2 % 60000, s2 // 60000, s3 % 60000, s3 // 60000,
                                       0x0F if ok else 0)
            else:
                b += P.HIST_VOLTA.pack(0, 0, 0, 0, 0, 0, 0, 0)
        for k in range(8):
            if k < len(stints):
                fim, comp = stints[k]
                b += P.HIST_STINT.pack(fim, {16: 17, 17: 18, 18: 19}.get(comp, 18), comp)
            else:
                b += P.HIST_STINT.pack(0, 0, 0)
        return bytes(b)

    def _sessao(self, t, f):
        b = bytearray(cab(1, t, f))
        resta = max(0, int(self.duracao - self.t)) if self.modo != 'corrida' else 5400
        b += P.SESSAO_A.pack(0, 27, 18, VOLTAS_CORRIDA, int(L), self.tipo, PISTA_ID, 0, resta, self.duracao,
                             80, 0, 0, 0, 0, 3)
        for k in range(21):
            b += P.ZONA_COMISSARIOS.pack(k / 3 if k < 3 else 0.0, 1 if k < 3 else 0)
        b += P.SESSAO_B.pack(0, 0, 3)
        prev = [(0, 0, 18), (10, 1, 20), (20, 3, 30)]
        for k in range(64):
            if k < 3:
                m, w, ch = prev[k]
                b += P.PREVISAO.pack(self.tipo, m, w, 27, 2, 18, 2, ch)
            else:
                b += P.PREVISAO.pack(0, 0, 0, 0, 0, 0, 0, 0)
        # campos finais (janela de box e posição de reentrada do jogador)
        eu = self.carros[JOGADOR]
        ordem = self._ordem()
        reent = 0
        if self.modo == 'corrida':
            meu_gap = self._gap(eu, ordem[0]) / 1000 + 21.4
            reent = 1 + sum(1 for c in ordem if c is not eu and self._gap(c, ordem[0]) / 1000 < meu_gap)
        # duração "completa" (7) e fim de semana normal: TL1, TL2, TL3, Q1, Q2, Q3, corrida
        fds = [1, 2, 3, 5, 6, 7, 15]
        campos = [0, 90, 1, 2, 3, 29, 32, reent] + [0] * 11 + [840] + [7] + [0] * 31 + [len(fds)] \
            + fds + [0] * (12 - len(fds)) + [S2, S3]
        b += P.SESSAO_C.pack(*campos)
        b += P.SESSAO_2026.pack(0, 2, struct.pack('<16f', 0.05, 0.12, 0.6, 0.7, *([0.0] * 12)), 0, b'\x00' * 64,
                                0, b'\x00' * 32, 0.0, 0, 0, 0, 0, 0)
        return bytes(b)

    def _participantes(self, t, f):
        b = bytearray(cab(4, t, f))
        b.append(sum(1 for c in self.carros if c.ativo))
        for c in self.carros:
            cores = list(c.cor) + [20, 20, 20] * 3
            b += P.PARTICIPANTE[FMT].pack(0 if c.i == JOGADOR else 1, c.i, 255, c.equipa, 0, c.i + 1, 0,
                                          c.nome.encode('utf-8'), 1, 1, 0, 0, 2, *cores)
        return bytes(b)

    # vida útil por composto (voltas) e ritmo: diferença base e perda por volta de idade (ms), como em _nova_volta_alvo
    VIDA = {16: 18, 17: 26, 18: 34}
    RITMO = {16: (-450, 55), 17: (-200, 35), 18: (0, 22)}

    def _conjuntos(self, t, f):
        """Conjuntos de pneus do jogador, com a vida que resta e a diferença de ritmo para o montado (como o jogo)."""
        b = bytearray(cab(12, t, f))
        b.append(JOGADOR)
        eu = self.carros[JOGADOR]
        conj = [(17, 16, 0), (17, 16, 18), (17, 16, 18), (18, 17, 0), (18, 17, 0), (19, 18, 0), (19, 18, 0)]
        montado = next(k for k, c in enumerate(conj) if c[1] == eu.composto)

        def idade(k):
            return eu.idade if k == montado else round(self.VIDA[conj[k][1]] * conj[k][2] / 70)

        def ritmo(k):
            base, por_volta = self.RITMO[conj[k][1]]
            return base + por_volta * idade(k)
        for k in range(20):
            if k < len(conj):
                r, v, w = conj[k]
                vida_util = self.VIDA[v]
                vida = max(0, vida_util - idade(k))
                desg = round(sum(self.desgaste) / 4) if k == montado else w
                b += P.CONJ_PNEUS.pack(r, v, desg, 1, 0, vida, vida_util, ritmo(k) - ritmo(montado), int(k == montado))
            else:
                b += P.CONJ_PNEUS.pack(0, 0, 0, 0, 0, 0, 0, 0, 0)
        b.append(montado)
        return bytes(b)

    def avancar_rapido(self, segundos, dt=0.05):
        alvo = self.t + segundos
        while self.t < alvo:
            self.passo(dt)


def criar(modo):
    sim = Simulador(modo)
    if modo == 'corrida':
        while sim.carros[JOGADOR].volta < 23:
            sim.passo(0.05)
    elif modo == 'qualificacao':
        sim.avancar_rapido(500)
    else:
        sim.avancar_rapido(1300)
    sim.eventos = sim.eventos[-3:]
    return sim


def correr(modo, porta=20777, hz=20):
    sim = criar(modo)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dt = 1 / hz
    proximo = time.time()
    while True:
        sim.passo(dt)
        for p in sim.pacotes():
            sock.sendto(p, ('127.0.0.1', porta))
        proximo += dt
        time.sleep(max(0, proximo - time.time()))
