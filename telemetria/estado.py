"""Estado da sessão: junta os pacotes recebidos e calcula tudo o que os ecrãs mostram."""
import json
import math
import os
import threading
import time
import unicodedata
from collections import deque

# Ordem das rodas nos arrays do jogo: 0 = trás esq., 1 = trás dir., 2 = frente esq., 3 = frente dir.
TE, TD, FE, FD = 0, 1, 2, 3

PISTAS = {
    0: 'GP da Austrália · Melbourne', 2: 'GP da China · Xangai', 3: 'GP do Bahrain · Sakhir',
    4: 'GP de Espanha · Barcelona', 5: 'GP do Mónaco · Monte Carlo', 6: 'GP do Canadá · Montreal',
    7: 'GP da Grã-Bretanha · Silverstone', 9: 'GP da Hungria · Hungaroring', 10: 'GP da Bélgica · Spa-Francorchamps',
    11: 'GP de Itália · Monza', 12: 'GP de Singapura · Marina Bay', 13: 'GP do Japão · Suzuka',
    14: 'GP de Abu Dhabi · Yas Marina', 15: 'GP dos EUA · Austin', 16: 'GP de São Paulo · Interlagos',
    17: 'GP da Áustria · Red Bull Ring', 19: 'GP do México · Hermanos Rodríguez', 20: 'GP do Azerbaijão · Baku',
    26: 'GP dos Países Baixos · Zandvoort', 27: 'GP da Emília-Romanha · Imola', 29: 'GP da Arábia Saudita · Jeddah',
    30: 'GP de Miami · Miami', 31: 'GP de Las Vegas · Las Vegas', 32: 'GP do Qatar · Lusail',
    39: 'Silverstone (inverso)', 40: 'Red Bull Ring (inverso)', 41: 'Zandvoort (inverso)', 42: 'GP de Madrid · Madring',
}
SESSOES = {
    0: 'Sessão', 1: 'Treinos livres 1', 2: 'Treinos livres 2', 3: 'Treinos livres 3', 4: 'Treinos curtos',
    5: 'Q1', 6: 'Q2', 7: 'Q3', 8: 'Qualificação curta', 9: 'Qualificação de volta única',
    10: 'Sprint Shootout 1', 11: 'Sprint Shootout 2', 12: 'Sprint Shootout 3', 13: 'Sprint Shootout curto',
    14: 'Sprint Shootout volta única', 15: 'Corrida', 16: 'Corrida 2', 17: 'Corrida 3', 18: 'Contrarrelógio',
}
METEO = {0: 'Limpo', 1: 'Pouco nublado', 2: 'Nublado', 3: 'Chuva fraca', 4: 'Chuva forte', 5: 'Tempestade'}
COMPOSTOS = {16: 'S', 17: 'M', 18: 'H', 7: 'I', 8: 'W', 19: 'S', 20: 'S', 21: 'M', 22: 'H', 15: 'W'}
# cores de recurso por equipa, se o jogo não enviar as cores da pintura
CORES_EQUIPA = {
    0: '#27F4D2', 1: '#E8002D', 2: '#3671C6', 3: '#64C4FF', 4: '#229971', 5: '#0093CC', 6: '#6692FF',
    7: '#B6BABD', 8: '#FF8000', 9: '#52E252',
    476: '#27F4D2', 477: '#E8002D', 478: '#3671C6', 479: '#64C4FF', 480: '#229971', 481: '#0093CC',
    482: '#6692FF', 483: '#B6BABD', 484: '#FF8000', 485: '#BB0A30', 486: '#E5E7EB',
}
# número oficial de voltas de cada GP (distância completa)
VOLTAS_OFICIAIS = {
    0: 58, 2: 56, 3: 57, 4: 66, 5: 78, 6: 70, 7: 52, 9: 70, 10: 44, 11: 53, 12: 62, 13: 53, 14: 58,
    15: 56, 16: 71, 17: 71, 19: 71, 20: 51, 26: 72, 27: 63, 29: 50, 30: 57, 31: 50, 32: 57,
    39: 52, 40: 71, 41: 72,
}
FICHEIRO_MEMORIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'memoria.json')


def ler_memoria():
    try:
        with open(FICHEIRO_MEMORIA, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def guardar_memoria(m):
    try:
        with open(FICHEIRO_MEMORIA, 'w', encoding='utf-8') as f:
            json.dump(m, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def voltas_completas(pista, comprimento):
    if pista in VOLTAS_OFICIAIS:
        return VOLTAS_OFICIAIS[pista]
    return math.ceil(305000 / comprimento) if comprimento else None


CORTES_PENALIZACAO = {0: 'drive-through', 1: 'stop & go', 4: 'penalização +{t} s', 6: 'desqualificado'}


def ecra_da_sessao(tipo):
    if 15 <= tipo <= 17:
        return 'corrida'
    if 5 <= tipo <= 14 or tipo == 18:
        return 'qualificacao'
    return 'treinos'


def codigo_piloto(nome):
    if not nome:
        return '???'
    limpo = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode().strip()
    partes = [p for p in limpo.replace('.', ' ').split() if p]
    base = partes[-1] if partes else limpo
    return (base[:3] or '???').upper()


def cor_hex(rgb):
    return '#%02X%02X%02X' % rgb


def luminancia(rgb):
    def c(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)


def media(xs):
    return sum(xs) / len(xs) if xs else None


def regressao(ys):
    n = len(ys)
    if n < 2:
        return 0.0
    mx = (n - 1) / 2
    my = sum(ys) / n
    num = sum((i - mx) * (y - my) for i, y in enumerate(ys))
    den = sum((i - mx) ** 2 for i in range(n))
    return num / den if den else 0.0


def desvio(ys):
    if len(ys) < 2:
        return 0.0
    m = sum(ys) / len(ys)
    return math.sqrt(sum((y - m) ** 2 for y in ys) / len(ys))


class Sessao:
    N_MINI = 8   # mini-setores por setor

    def __init__(self):
        self.lock = threading.Lock()
        self.memoria = ler_memoria()
        self.reiniciar(None)
        self.ultimo_pacote = 0.0
        self.formato = None

    # ------------------------------------------------------------ gestão
    def reiniciar(self, uid):
        self.uid = uid
        self.jogador = 0
        self.sessao = None
        self.voltas = None
        self.telem = None
        self.telem2 = None
        self.estado = None
        self.danos = None
        self.ativos = 0
        self.participantes = []
        self.historico = {}
        self.conjuntos = None
        self.mensagens = deque(maxlen=12)
        self.volta_rapida = None
        self.paragens_vistas = {}
        # dados do jogador recolhidos volta a volta
        self.minha_volta = None
        self.inicio_volta = {}      # combustível e desgaste no início da volta atual
        self.consumos = deque(maxlen=10)
        self.desgaste_volta = deque(maxlen=8)
        self.tempos_saida = deque(maxlen=5)
        self.tempos_entrada = deque(maxlen=5)
        self.estado_volta_atual = None
        # traçado (tempo por cada 10 m) para o delta ao vivo
        self.traco_atual = {}
        self.traco_melhor = None
        self.tempo_melhor_traco = None
        # mini-setores de todos os carros
        self.mini_atual = {}         # carro -> {idx: tempo acumulado}
        self.mini_volta = {}         # carro -> número da volta a que mini_atual pertence
        self.mini_melhor_sessao = {}  # idx -> melhor tempo do segmento
        self.mini_meu_melhor = {}    # idx -> melhor tempo do segmento (jogador)
        self.mini_cores_atual = {}

    def receber(self, cab, nome, c):
        with self.lock:
            self.ultimo_pacote = time.time()
            self.formato = cab['formato']
            if cab['uid'] != self.uid:
                self.reiniciar(cab['uid'])
            self.jogador = cab['jogador']
            if nome == 'sessao':
                self.sessao = c
                self._aprender_corrida(c)
            elif nome == 'voltas':
                self._voltas(c)
            elif nome == 'evento':
                self._evento(c)
            elif nome == 'participantes':
                self.ativos, self.participantes = c
            elif nome == 'telemetria':
                self.telem = c
            elif nome == 'telemetria2':
                self.telem2 = c
            elif nome == 'estado':
                self.estado = c
            elif nome == 'danos':
                self.danos = c
            elif nome == 'historico':
                self.historico[c['carro']] = c
            elif nome == 'conjuntos':
                carro, conj, _ = c
                if carro == self.jogador:
                    self.conjuntos = conj

    # ------------------------------------------------------------ ajudas
    def _cod(self, i):
        if i < len(self.participantes):
            return codigo_piloto(self.participantes[i]['nome'])
        return '???'

    def _cor(self, i):
        if i < len(self.participantes):
            p = self.participantes[i]
            cores = [c for c in p['cores'] if any(c)]
            for c in cores:
                if luminancia(c) > 0.04:
                    return cor_hex(c)
            return CORES_EQUIPA.get(p['equipa_id'], '#98A2B3')
        return '#98A2B3'

    def _composto(self, i):
        if self.estado and i < len(self.estado):
            return COMPOSTOS.get(self.estado[i]['composto'], '?')
        return '?'

    def _msg(self, texto, cor='#98A2B3', volta=None, carro=None):
        """Guarda uma mensagem; '{c}' no texto é trocado pelo código do piloto quando os ecrãs pedem os dados."""
        if volta is None and self.voltas and self.jogador < len(self.voltas):
            volta = self.voltas[self.jogador]['volta']
        self.mensagens.appendleft({'volta': volta or 0, 'texto': texto, 'cor': cor, 'carro': carro})

    def _comprimento(self):
        return (self.sessao or {}).get('comprimento') or 5000

    def _limites_mini(self):
        L = self._comprimento()
        s2 = (self.sessao or {}).get('setor2_inicio') or L / 3
        s3 = (self.sessao or {}).get('setor3_inicio') or 2 * L / 3
        if not (0 < s2 < s3 < L):
            s2, s3 = L / 3, 2 * L / 3
        lim = []
        for a, b in ((0, s2), (s2, s3), (s3, L)):
            for k in range(1, self.N_MINI + 1):
                lim.append(a + (b - a) * k / self.N_MINI)
        return lim  # 24 fins de segmento

    # ------------------------------------------------------------ voltas da corrida (automático)
    def _aprender_corrida(self, s):
        """Numa corrida, guarda quantas voltas tem e a duração escolhida (percentagem da distância real)."""
        if not (15 <= s['tipo'] <= 17) or not s['voltas_total']:
            return
        completas = voltas_completas(s['pista'], s['comprimento'])
        m = self.memoria
        chave = str(s['pista'])
        if m.get('corridas', {}).get(chave) == s['voltas_total']:
            return
        m.setdefault('corridas', {})[chave] = s['voltas_total']
        if completas:
            m['percentagem'] = round(s['voltas_total'] / completas, 3)
        guardar_memoria(m)

    def voltas_corrida(self):
        """Devolve (voltas, de onde vem o número)."""
        s = self.sessao or {}
        total = s.get('voltas_total') or 0
        completas = voltas_completas(s.get('pista'), s.get('comprimento'))
        if 15 <= s.get('tipo', 0) <= 17 and total:
            return total, 'da corrida'
        guardada = self.memoria.get('corridas', {}).get(str(s.get('pista')))
        pct = self.memoria.get('percentagem')
        if completas and 3 <= total <= completas + 2 and total != guardada:
            return total, 'do jogo'
        if guardada:
            return guardada, 'da última corrida aqui'
        if pct and completas:
            return max(3, round(completas * pct)), f'{round(pct * 100)}% da distância, como nas tuas corridas'
        if completas and 3 <= total <= completas + 2:
            return total, 'do jogo'
        if completas:
            return completas, 'distância completa'
        return None, ''

    # ------------------------------------------------------------ eventos
    def _evento(self, ev):
        cod = ev['codigo']
        if cod == 'FTLP':
            self.volta_rapida = {'carro': ev['carro'], 'ms': int(ev['tempo'] * 1000),
                                 'volta': self.voltas[ev['carro']]['volta'] - 1 if self.voltas else 0}
            self._msg(f"{{c}} — volta mais rápida {fmt_volta(ev['tempo'] * 1000)}", '#B57BFF', carro=ev['carro'])
        elif cod == 'PENA':
            t = CORTES_PENALIZACAO.get(ev['tipo'])
            if t:
                self._msg('{c} — ' + t.format(t=ev['tempo']), '#FFB020', ev['volta'], carro=ev['carro'])
        elif cod == 'RTMT':
            self._msg('{c} — abandonou', '#FF4D4D', carro=ev['carro'])
        elif cod == 'SCAR':
            tipo = {1: 'Safety Car', 2: 'Virtual Safety Car', 3: 'Volta de formação'}.get(ev['tipo'], 'Safety Car')
            acao = {0: 'em pista', 1: 'vai recolher', 2: 'recolheu', 3: 'corrida retomada'}.get(ev['evento'], '')
            self._msg(f'{tipo} — {acao}', '#F5C518')
        elif cod == 'RDFL':
            self._msg('Bandeira vermelha', '#FF4D4D')
        elif cod == 'CHQF':
            self._msg('Bandeira de xadrez', '#F2F4F7')
        elif cod == 'RCWN':
            self._msg('{c} — vence a corrida', '#F2F4F7', carro=ev['carro'])
        elif cod == 'DTSV':
            self._msg('{c} — cumpriu drive-through', '#98A2B3', carro=ev['carro'])
        elif cod == 'SGSV':
            self._msg('{c} — cumpriu stop & go', '#98A2B3', carro=ev['carro'])

    # ------------------------------------------------------------ voltas (60 Hz)
    def _voltas(self, voltas):
        anterior = self.voltas
        self.voltas = voltas
        lim = self._limites_mini()
        for i, v in enumerate(voltas):
            if v['resultado'] < 2:
                continue
            # paragens nas boxes (mensagem para a direção de corrida)
            p0 = self.paragens_vistas.get(i)
            if p0 is not None and v['paragens'] > p0:
                comp = {'S': 'Macios', 'M': 'Médios', 'H': 'Duros', 'I': 'Intermédios', 'W': 'Chuva'}.get(self._composto(i), '')
                self._msg('{c} — box' + (f', {comp}' if comp else ''), '#98A2B3', v['volta'], carro=i)
            self.paragens_vistas[i] = v['paragens']
            # mini-setores
            if self.mini_volta.get(i) != v['volta']:
                self._fechar_mini(i)
                self.mini_volta[i] = v['volta']
                self.mini_atual[i] = {}
            d = v['dist_volta']
            if d > 0:
                m = self.mini_atual[i]
                for k, fim in enumerate(lim):
                    if d >= fim and k not in m:
                        m[k] = v['atual']
        self._jogador_volta(anterior)

    def _fechar_mini(self, i):
        m = self.mini_atual.get(i)
        if not m or len(m) < 3 * self.N_MINI - 1:
            return
        tempos = [m.get(k) for k in range(3 * self.N_MINI)]
        ant = 0
        for k, t in enumerate(tempos):
            if t is None:
                ant = None
                continue
            if ant is not None:
                seg = t - ant
                if seg > 0:
                    if seg < self.mini_melhor_sessao.get(k, 1e12):
                        self.mini_melhor_sessao[k] = seg
                    if i == self.jogador and seg < self.mini_meu_melhor.get(k, 1e12):
                        self.mini_meu_melhor[k] = seg
            ant = t

    def _jogador_volta(self, anterior):
        j = self.jogador
        if j >= len(self.voltas):
            return
        v = self.voltas[j]
        # traço tempo-distância desta volta (cada 10 m)
        if v['dist_volta'] > 0:
            b = int(v['dist_volta'] // 10)
            self.traco_atual.setdefault(b, v['atual'])
        if self.minha_volta is None:
            self.minha_volta = v['volta']
            self._marcar_inicio_volta()
            self.estado_volta_atual = v['estado_piloto']
            return
        if v['volta'] != self.minha_volta:
            ultima = v['ultima']
            # traço de referência = melhor volta válida
            completa = bool(self.traco_atual) and min(self.traco_atual) <= 2
            if ultima and completa and self.estado_volta_atual in (1, 4) and not self._ultima_invalida(anterior):
                if self.tempo_melhor_traco is None or ultima < self.tempo_melhor_traco:
                    self.tempo_melhor_traco = ultima
                    self.traco_melhor = dict(self.traco_atual)
            # voltas de saída / entrada (para saber se ainda dá tempo na qualificação)
            if self.estado_volta_atual == 3 and ultima:
                self.tempos_saida.append(ultima)
            if self.estado_volta_atual == 2 and ultima:
                self.tempos_entrada.append(ultima)
            # consumo e desgaste por volta
            ini = self.inicio_volta
            if self.estado and self.danos and ini.get('volta') == self.minha_volta:
                comb = self.estado[j]['combustivel']
                gasto = ini['combustivel'] - comb
                if 0.2 < gasto < 5:
                    self.consumos.append(gasto)
                des = self.danos[j]['desgaste']
                delta = [des[k] - ini['desgaste'][k] for k in range(4)]
                if all(0 <= x < 15 for x in delta) and any(x > 0 for x in delta):
                    self.desgaste_volta.append(delta)
                elif any(x < 0 for x in delta):
                    self.desgaste_volta.clear()   # pneus novos
            self.minha_volta = v['volta']
            self.traco_atual = {}
            self.estado_volta_atual = v['estado_piloto']
            self._marcar_inicio_volta()

    def _ultima_invalida(self, anterior):
        if anterior and self.jogador < len(anterior):
            return bool(anterior[self.jogador]['invalida'])
        return False

    def _marcar_inicio_volta(self):
        j = self.jogador
        if self.estado and self.danos and j < len(self.estado):
            self.inicio_volta = {'volta': self.voltas[j]['volta'], 'combustivel': self.estado[j]['combustivel'],
                                 'desgaste': list(self.danos[j]['desgaste'])}

    # ------------------------------------------------------------ histórico
    def _voltas_hist(self, i):
        h = self.historico.get(i)
        return h['voltas'] if h else []

    def _ritmo(self, i, n=5):
        """Média das últimas n voltas válidas, sem voltas de entrada/saída das boxes."""
        h = self.historico.get(i)
        if not h:
            return None
        excluir = set()
        for s in h['stints'][:-1]:
            if s['fim'] and s['fim'] != 255:
                excluir.update({s['fim'], s['fim'] + 1})
        excluir.add(1)
        atual = self.voltas[i]['volta'] if self.voltas else len(h['voltas'])
        tempos = [v['tempo'] for k, v in enumerate(h['voltas'], start=1)
                  if v['tempo'] and v['valida'] and k not in excluir and k < atual]
        return media(tempos[-n:]) if tempos else None

    def _volta_rapida_historico(self):
        """Se o painel abriu a meio da sessão (sem o evento de volta mais rápida), procura no histórico."""
        melhor = None
        for i, h in self.historico.items():
            for k, v in enumerate(h['voltas'], start=1):
                if v['tempo'] and v['valida'] and (melhor is None or v['tempo'] < melhor['ms']):
                    melhor = {'carro': i, 'ms': v['tempo'], 'volta': k}
        return melhor

    def _melhor(self, i):
        h = self.historico.get(i)
        if not h or not h['melhor_volta'] or h['melhor_volta'] > len(h['voltas']):
            return None
        t = h['voltas'][h['melhor_volta'] - 1]['tempo']
        return t or None

    # ------------------------------------------------------------ fotografia para os ecrãs
    def fotografia(self):
        with self.lock:
            return self._fotografia()

    def _fotografia(self):
        agora = time.time()
        ligado = agora - self.ultimo_pacote < 3
        if not (self.sessao and self.voltas):
            return {'ligado': ligado, 'pronto': False, 'formato': self.formato}
        s = self.sessao
        j = self.jogador
        tipo = s['tipo']
        ecra = ecra_da_sessao(tipo)
        L = self._comprimento()
        out = {
            'ligado': ligado, 'pronto': True, 'formato': self.formato, 'ecra': ecra,
            'sessao': {
                'tipo': tipo, 'nome': SESSOES.get(tipo, 'Sessão'), 'pista': PISTAS.get(s['pista'], f"Pista {s['pista']}"),
                'comprimento': L, 'voltas_total': s['voltas_total'], 'restante': s['tempo_restante'],
                'duracao': s['duracao'], 'temp_ar': s['temp_ar'], 'temp_pista': s['temp_pista'],
                'meteo': METEO.get(s['tempo_meteo'], ''), 'safety_car': s['safety_car'],
                'previsao': self._previsao(), 'box_ideal': s['box_ideal'], 'box_ultima': s['box_ultima'],
                'box_reentrada': s['box_reentrada'],
            },
        }
        vc, fonte = self.voltas_corrida()
        out['sessao']['voltas_corrida'] = vc
        out['sessao']['voltas_corrida_fonte'] = fonte
        carros = self._carros()
        out['carros'] = carros
        out['eu'] = self._eu(carros)
        out['mensagens'] = [{'volta': m['volta'], 'cor': m['cor'],
                             'texto': m['texto'].replace('{c}', self._cod(m['carro']) if m['carro'] is not None else '')}
                            for m in list(self.mensagens)[:6]]
        vr = self.volta_rapida or self._volta_rapida_historico()
        out['volta_rapida'] = {'codigo': self._cod(vr['carro']), 'ms': vr['ms'], 'volta': vr['volta']} if vr else None
        if ecra == 'corrida':
            out['corrida'] = self._corrida(carros)
        elif ecra == 'qualificacao':
            out['quali'] = self._quali(carros)
        else:
            out['treinos'] = self._treinos(carros)
        return out

    def _previsao(self):
        s = self.sessao
        tipo = s['tipo']
        res = []
        for p in s['previsao']:
            if p['tipo'] == tipo and p['minutos'] in (0, 5, 10, 15, 30) and len(res) < 3:
                res.append({'min': p['minutos'], 'meteo': METEO.get(p['tempo_meteo'], ''), 'chuva': p['chuva']})
        return res

    def _carros(self):
        v = self.voltas
        L = self._comprimento()
        lista = []
        for i, c in enumerate(v):
            if c['resultado'] < 2 or c['posicao'] == 0:
                continue
            lista.append(i)
        lista.sort(key=lambda i: v[i]['posicao'])
        lider = lista[0] if lista else 0
        res = []
        for i in lista:
            c = v[i]
            atras = 0
            if L:
                atras = int((v[lider]['dist_total'] - c['dist_total']) // L) if i != lider else 0
            est = self.estado[i] if self.estado and i < len(self.estado) else {}
            res.append({
                'idx': i, 'pos': c['posicao'], 'codigo': self._cod(i), 'cor': self._cor(i), 'eu': i == self.jogador,
                'volta': c['volta'], 'lider_ms': c['para_lider'], 'frente_ms': c['para_frente'],
                'voltas_atras': max(atras, 0), 'paragens': c['paragens'], 'composto': self._composto(i),
                'idade': est.get('idade_pneus', 0), 'penal': c['penalizacoes'], 'estado_piloto': c['estado_piloto'],
                'box': c['box_estado'] > 0, 'resultado': c['resultado'], 'grelha': c['grelha'],
                'melhor_ms': self._melhor(i), 'ultima_ms': c['ultima'], 'speed_trap': round(c['speed_trap'] or 0),
                'dist_volta': c['dist_volta'],
            })
        return res

    def _eu(self, carros):
        j = self.jogador
        v = self.voltas[j]
        est = self.estado[j] if self.estado else None
        tel = self.telem[j] if self.telem else None
        t2 = self.telem2[j] if self.telem2 else None
        dan = self.danos[j] if self.danos else None
        hist = self._voltas_hist(j)
        eu = {
            'pos': v['posicao'], 'grelha': v['grelha'], 'volta': v['volta'], 'atual_ms': v['atual'],
            'ultima_ms': v['ultima'], 'melhor_ms': self._melhor(j), 'setor': v['setor'],
            'estado_piloto': v['estado_piloto'], 'invalida': bool(v['invalida']), 'paragens': v['paragens'],
            'codigo': self._cod(j), 'cor': self._cor(j), 's1_ms': v['s1'], 's2_ms': v['s2'],
            'nome': self.participantes[j]['nome'] if j < len(self.participantes) else '',
        }
        h = self.historico.get(j)
        if h and h['melhor_volta'] and h['melhor_volta'] <= len(hist):
            eu['melhor_volta_num'] = h['melhor_volta']
            mv = hist[h['melhor_volta'] - 1]
            eu['melhor_setores'] = [mv['s1'], mv['s2'], mv['s3']]
        # setores da última volta com cores (roxo = melhor da sessão, verde = melhor pessoal, amarelo = mais lento)
        eu['setores_ultima'] = self._setores_ultima(j)
        eu['ritmo'] = [x['tempo'] for x in hist if x['tempo']][-8:] if hist else []
        # delta ao vivo e previsão
        eu['delta_ms'] = self._delta_vivo(v)
        if eu['delta_ms'] is not None and self.tempo_melhor_traco:
            eu['previsao_ms'] = self.tempo_melhor_traco + eu['delta_ms']
        eu['mini'] = self._mini_cores(j)
        if est:
            eu.update({
                'composto': COMPOSTOS.get(est['composto'], '?'), 'idade': est['idade_pneus'],
                'combustivel': round(est['combustivel'], 1), 'margem_voltas': round(est['combustivel_voltas'], 2),
                'ers_pct': round(est['ers'] / 4e6 * 100), 'ers_modo': est['ers_modo'],
                'ers_rec_mj': round((est['ers_mguk'] + est['ers_mguh']) / 1e6, 1),
                'ers_usado_mj': round(est['ers_usado'] / 1e6, 1), 'ers_limite_mj': round(est['ers_limite'] / 1e6, 1),
                'bandeira': est['bandeira'],
            })
        if tel:
            eu.update({'pneus_sup': tel['pneus_sup'], 'pneus_int': tel['pneus_int'], 'travoes': tel['travoes_temp'],
                       'pressao': tel['pressao'], 'motor_temp': tel['motor_temp'], 'velocidade': tel['velocidade']})
        if dan:
            eu['danos'] = dan
        if t2:
            eu['aero'] = {'modo': t2['aero_modo'], 'disp': t2['aero_disp'], 'dist': t2['aero_dist'],
                          'ovtk_disp': t2['ovtk_disp'], 'ovtk_ativo': t2['ovtk_ativo'], 'ovtk_dist': t2['ovtk_dist'],
                          'regras_2026': t2['regras_2026']}
        eu['consumo_volta'] = round(media(list(self.consumos)), 2) if self.consumos else None
        if self.desgaste_volta:
            taxa = [round(media([d[k] for d in self.desgaste_volta]), 2) for k in range(4)]
            eu['desgaste_volta'] = taxa
            if dan:
                restos = [(70 - dan['desgaste'][k]) / taxa[k] for k in range(4) if taxa[k] > 0.05]
                if restos:
                    pior = min(range(4), key=lambda k: (70 - dan['desgaste'][k]) / taxa[k] if taxa[k] > 0.05 else 1e9)
                    eu['vida_restante_voltas'] = max(0, int(min(restos)))
                    eu['pneu_limite'] = pior
                    eu['vida_total_voltas'] = int(max(0, min(restos)) + (est['idade_pneus'] if est else 0))
        eu['speed_trap'] = round(v['speed_trap'] or 0)
        return eu

    def _setores_ultima(self, j):
        hist = self._voltas_hist(j)
        if not hist:
            return []
        atual = self.voltas[j]['volta']
        if atual - 2 < 0 or atual - 2 >= len(hist):
            return []
        u = hist[atual - 2]
        if not u['tempo']:
            return []
        best_s = self._melhores_setores_sessao()
        meus = self._meus_melhores_setores(j)
        res = []
        for k, t in enumerate((u['s1'], u['s2'], u['s3'])):
            if best_s[k] and t <= best_s[k]:
                cor = 'roxo'
            elif meus[k] and t <= meus[k]:
                cor = 'verde'
            else:
                cor = 'amarelo'
            res.append({'ms': t, 'cor': cor})
        return res

    def _melhores_setores_sessao(self):
        best = [None, None, None]
        for h in self.historico.values():
            for v in h['voltas']:
                if not v['valida']:
                    continue
                for k, t in enumerate((v['s1'], v['s2'], v['s3'])):
                    if t and (best[k] is None or t < best[k]):
                        best[k] = t
        return best

    def _meus_melhores_setores(self, i):
        best = [None, None, None]
        for v in self._voltas_hist(i):
            if not v['valida']:
                continue
            for k, t in enumerate((v['s1'], v['s2'], v['s3'])):
                if t and (best[k] is None or t < best[k]):
                    best[k] = t
        return best

    def _delta_vivo(self, v):
        if not self.traco_melhor or v['dist_volta'] <= 0:
            return None
        b = int(v['dist_volta'] // 10)
        for k in range(b, max(b - 30, -1), -1):   # o mesmo ponto da pista (ou o mais próximo antes)
            if k in self.traco_melhor and k in self.traco_atual:
                return self.traco_atual[k] - self.traco_melhor[k] + (v['atual'] - self.traco_atual[b] if b in self.traco_atual else 0)
        return None

    def _mini_cores(self, j):
        m = self.mini_atual.get(j, {})
        cores = []
        ant = 0
        for k in range(3 * self.N_MINI):
            t = m.get(k)
            if t is None or ant is None:
                cores.append('cinza')
                ant = None if t is None else t
                continue
            seg = t - ant
            if seg <= self.mini_melhor_sessao.get(k, -1):
                cores.append('roxo')
            elif seg <= self.mini_meu_melhor.get(k, -1):
                cores.append('verde')
            elif k in self.mini_meu_melhor:
                cores.append('amarelo')
            else:
                cores.append('verde')
            ant = t
        return cores

    # ------------------------------------------------------------ corrida
    def _corrida(self, carros):
        j = self.jogador
        idx_eu = next((k for k, c in enumerate(carros) if c['eu']), None)
        res = {}
        if idx_eu is None:
            return res
        eu = carros[idx_eu]
        meu_ritmo = self._ritmo(j)

        def vizinho(k, frente):
            c = carros[k]
            gap = (eu['frente_ms'] if frente else c['frente_ms']) / 1000
            r = self._ritmo(c['idx'])
            dif = None
            if r and meu_ritmo:
                dif = (r - meu_ritmo) / 1000 if frente else (meu_ritmo - r) / 1000
            return {'codigo': c['codigo'], 'pos': c['pos'], 'composto': c['composto'], 'idade': c['idade'],
                    'gap_s': round(gap, 3), 'ritmo_ms': r, 'diferenca_volta': round(dif, 2) if dif is not None else None,
                    'voltas_atras': c['voltas_atras']}

        if idx_eu > 0:
            res['frente'] = vizinho(idx_eu - 1, True)
        if idx_eu + 1 < len(carros):
            res['atras'] = vizinho(idx_eu + 1, False)
        res['meu_ritmo_ms'] = meu_ritmo
        # ritmo do carro da frente (últimas 8 voltas) para o gráfico
        if idx_eu > 0:
            res['ritmo_frente'] = [x['tempo'] for x in self._voltas_hist(carros[idx_eu - 1]['idx']) if x['tempo']][-8:]
        # reentrada se parar agora (posição dada pelo próprio jogo)
        reent = self.sessao.get('box_reentrada') or 0
        if reent:
            outros = [c for c in carros if not c['eu']]
            if 1 < reent <= len(outros) + 1:
                f = outros[reent - 2]
                res['reentrada'] = {'pos': reent, 'atras_de': f['codigo']}
            else:
                res['reentrada'] = {'pos': reent, 'atras_de': None}
        return res

    # ------------------------------------------------------------ qualificação
    def _quali(self, carros):
        tipo = self.sessao['tipo']
        n = len(carros)
        corte = None
        if tipo in (5, 10):
            corte = 10 + math.ceil(max(n - 10, 0) / 2)
        elif tipo in (6, 11):
            corte = 10
        res = {'corte': corte}
        ordem = sorted(carros, key=lambda c: (c['melhor_ms'] is None, c['melhor_ms'] or 0, c['pos']))
        res['ordem'] = [c['idx'] for c in ordem]
        tempos = [c['melhor_ms'] for c in ordem]
        res['pole_ms'] = tempos[0] if tempos and tempos[0] else None
        res['pole_codigo'] = ordem[0]['codigo'] if ordem else ''
        eu = next((c for c in ordem if c['eu']), None)
        if corte and len(ordem) > corte:
            res['corte_ms'] = ordem[corte - 1]['melhor_ms']
            prox = ordem[corte]
            res['corte_seguinte'] = prox['codigo']
            if eu and eu['melhor_ms'] and prox['melhor_ms']:
                res['margem_ms'] = prox['melhor_ms'] - eu['melhor_ms']
        # volta ideal
        meus = self._meus_melhores_setores(self.jogador)
        if all(meus):
            res['ideal_ms'] = sum(meus)
        # previsão de posição
        ev = self._eu_rapido()
        prev = ev.get('previsao')
        if prev:
            outros = [c['melhor_ms'] for c in ordem if not c['eu'] and c['melhor_ms']]
            res['previsao_pos'] = 1 + sum(1 for t in outros if t < prev)
        # tráfego à volta do jogador
        res['trafego'] = self._trafego(carros)
        # tempo para mais uma tentativa
        saida = media(list(self.tempos_saida)) or 120000
        entrada = media(list(self.tempos_entrada)) or 125000
        res['saida_ms'] = int(saida)
        res['entrada_ms'] = int(entrada)
        rest = self.sessao['tempo_restante'] * 1000
        v = self.voltas[self.jogador]
        ref = self.tempo_melhor_traco or (eu['melhor_ms'] if eu else None) or 100000
        if v['estado_piloto'] == 0 or v['box_estado']:
            res['tentativa'] = {'ok': rest > saida, 'sair_ate_ms': int(saida + 5000)}
        else:
            falta_volta = max(ref - v['atual'], 0)
            res['tentativa'] = {'ok': rest - falta_volta - saida > 0, 'sair_ate_ms': int(saida + 5000)}
        # conjuntos de pneus
        if self.conjuntos:
            grupos = {}
            for c in self.conjuntos:
                if not c['disponivel']:
                    continue
                comp = COMPOSTOS.get(c['visual'], '?')
                novo = c['desgaste'] == 0
                chave = (comp, novo, 0 if novo else c['desgaste'])
                grupos[chave] = grupos.get(chave, 0) + 1
            ordem_c = {'S': 0, 'M': 1, 'H': 2, 'I': 3, 'W': 4}
            res['conjuntos'] = [{'composto': k[0], 'novo': k[1], 'desgaste': k[2], 'qtd': q}
                                for k, q in sorted(grupos.items(), key=lambda x: (ordem_c.get(x[0][0], 9), not x[0][1], x[0][2]))][:5]
        return res

    def _eu_rapido(self):
        v = self.voltas[self.jogador]
        d = self._delta_vivo(v)
        if d is not None and self.tempo_melhor_traco:
            return {'previsao': self.tempo_melhor_traco + d}
        return {}

    def _trafego(self, carros):
        L = self._comprimento()
        j = self.jogador
        v = self.voltas
        vel = (self.telem[j]['velocidade'] if self.telem else 200) / 3.6
        vel = max(vel, 40)
        meu = v[j]['dist_volta']
        if v[j]['estado_piloto'] == 0 or v[j]['box_estado']:
            return []   # na garagem / boxes: o tráfego não interessa
        nomes = {0: 'na garagem', 1: 'volta rápida', 2: 'volta de entrada', 3: 'volta de saída', 4: 'em pista'}
        res = []
        for c in carros:
            if c['eu'] or c['estado_piloto'] == 0 or c['box']:
                continue
            d = (c['dist_volta'] - meu) % L
            frente = d < L / 2
            dist = d if frente else L - d
            seg = dist / vel
            if seg > 15:
                continue
            nota = ''
            eu_rapido = v[j]['estado_piloto'] == 1
            if frente and eu_rapido and c['estado_piloto'] in (2, 3, 4):
                nota = 'Vais apanhá-lo nesta volta' if seg < 10 else 'Pode atrapalhar'
            elif not frente and c['estado_piloto'] == 1 and not eu_rapido:
                nota = 'Vem em volta rápida — dá passagem'
            res.append({'codigo': c['codigo'], 'frente': frente, 'estado': nomes.get(c['estado_piloto'], ''),
                        'gap_s': round(seg, 1), 'nota': nota, 'alerta': bool(nota)})
        res.sort(key=lambda r: r['gap_s'])
        return res[:3]

    # ------------------------------------------------------------ treinos
    def _programa(self, h):
        """Programa da sessão escolhido pelo tipo de treino; cada tarefa marca-se sozinha com o que fazes em pista."""
        tipo = self.sessao['tipo']
        voltas = h['voltas'] if h else []
        stints = h['stints'] if h else []
        feitas = sum(1 for v in voltas if v['tempo'])
        # voltas válidas seguidas no mesmo pneu (sem a volta de saída nem a de entrada)
        maior_run, compostos, rapida_macios = 0, set(), None
        inicio = 1
        for st in stints:
            fim = st['fim'] if st['fim'] != 255 else len(voltas)
            lista = voltas[inicio - 1:fim]
            corpo = lista[1:-1] if st['fim'] != 255 else lista[1:]
            seguidas = atual = 0
            for v in corpo:
                atual = atual + 1 if (v['tempo'] and v['valida']) else 0
                seguidas = max(seguidas, atual)
            maior_run = max(maior_run, seguidas)
            comp = COMPOSTOS.get(st['visual'], '?')
            if any(v['tempo'] and v['valida'] for v in corpo):
                compostos.add(comp)
                if comp == 'S':
                    t = min(v['tempo'] for v in corpo if v['tempo'] and v['valida'])
                    rapida_macios = t if rapida_macios is None else min(rapida_macios, t)
            inicio = fim + 1
        nomes = {'S': 'macios', 'M': 'médios', 'H': 'duros'}
        testados = ', '.join(nomes[c] for c in ('S', 'M', 'H') if c in compostos)
        consumos = len(self.consumos)
        desgastes = len(self.desgaste_volta)
        t_reco = _tarefa('Reconhecimento da pista', min(feitas, 3), 3, 'voltas')
        t_comp = _tarefa('Testar os 3 compostos', len(compostos & {'S', 'M', 'H'}), 3, 'compostos', testados)
        t_desg = _tarefa('Medir o desgaste dos pneus', min(desgastes, 3), 3, 'voltas medidas')
        t_quali = _tarefa('Simulação de qualificação', 1 if rapida_macios else 0, 1, 'volta rápida em macios',
                          fmt_volta(rapida_macios) if rapida_macios else '')
        t_corr8 = _tarefa('Simulação de corrida', min(maior_run, 8), 8, 'voltas seguidas')
        t_corr5 = _tarefa('Confirmar ritmo de corrida', min(maior_run, 5), 5, 'voltas seguidas')
        t_cons = _tarefa('Medir o consumo de combustível', min(consumos, 2), 2, 'voltas medidas')
        if tipo == 1:
            lista = [t_reco, t_comp, t_desg]
        elif tipo == 2:
            lista = [t_quali, t_corr8, t_cons]
        elif tipo == 3:
            lista = [t_quali, t_corr5, t_desg]
        else:
            lista = [t_reco, t_quali, t_corr8, t_cons]
        return lista

    def _treinos(self, carros):
        j = self.jogador
        h = self.historico.get(j)
        res = {'stints': [], 'longo': None}
        if h:
            voltas = h['voltas']
            inicio = 1
            for s in h['stints']:
                fim = s['fim'] if s['fim'] != 255 else len(voltas)
                lista = [(k, voltas[k - 1]) for k in range(inicio, min(fim, len(voltas)) + 1)]
                validas = [x['tempo'] for k, x in lista[1:-1] if x['tempo'] and x['valida']] if s['fim'] != 255 \
                    else [x['tempo'] for k, x in lista[1:] if x['tempo'] and x['valida']]
                res['stints'].append({
                    'composto': COMPOSTOS.get(s['visual'], '?'), 'voltas': len(lista),
                    'melhor_ms': min(validas) if validas else None, 'media_ms': int(media(validas)) if validas else None,
                    'atual': s['fim'] == 255,
                })
                if s['fim'] == 255 and len(validas) >= 2:
                    slope = regressao(validas)
                    res['longo'] = {
                        'composto': COMPOSTOS.get(s['visual'], '?'), 'voltas': validas,
                        'media_ms': int(media(validas)), 'degradacao_ms': round(slope),
                        'consistencia_ms': round(desvio(validas)), 'melhor_ms': min(validas),
                        'melhor_volta': validas.index(min(validas)) + 1,
                        'projecao': [int(validas[-1] + slope * (k + 1)) for k in range(3)],
                    }
                inicio = fim + 1
        res['programa'] = self._programa(h)
        best = self._melhores_setores_sessao()
        meus = self._meus_melhores_setores(j)
        res['setores'] = [{'meu': meus[k], 'melhor': best[k]} for k in range(3)]
        traps = [c['speed_trap'] for c in carros if c['speed_trap']]
        res['speed_trap_melhor'] = max(traps) if traps else None
        return res


def _tarefa(nome, feito_qtd, alvo, unidade, extra=''):
    feito = feito_qtd >= alvo
    if feito:
        det = 'Feito' + (f' · {extra}' if extra else '')
    else:
        det = f'{feito_qtd} de {alvo} {unidade}' + (f' · {extra}' if extra else '')
    return {'nome': nome, 'detalhe': det, 'progresso': min(feito_qtd / alvo, 1) if alvo else 1, 'feito': feito}


def fmt_volta(ms):
    ms = int(ms)
    return f'{ms // 60000}:{(ms % 60000) / 1000:06.3f}'
