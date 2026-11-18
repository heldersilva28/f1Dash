"""Estado da sessão: junta os pacotes recebidos e calcula tudo o que os ecrãs mostram."""
import bisect
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
    # pistas que só existem no F1 2020
    1: 'GP de França · Paul Ricard', 8: 'GP da Alemanha · Hockenheim', 18: 'GP da Rússia · Sochi',
    21: 'GP do Bahrain · Sakhir (curto)', 22: 'GP da Grã-Bretanha · Silverstone (curto)', 23: 'GP dos EUA · Austin (curto)',
    24: 'GP do Japão · Suzuka (curto)', 25: 'GP do Vietname · Hanói',
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
# equipas do F1 2020 (o jogo não envia as cores da pintura)
CORES_2020 = {0: '#00D2BE', 1: '#DC0000', 2: '#0600EF', 3: '#0082FA', 4: '#F596C8', 5: '#FFF500', 6: '#C8C8C8',
              7: '#787878', 8: '#FF8700', 9: '#960000'}
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
    1: 53, 8: 67, 18: 53, 25: 55,     # F1 2020
}
FICHEIRO_MEMORIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'memoria.json')


def ler_memoria():
    try:
        with open(FICHEIRO_MEMORIA, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def guardar_memoria(m):
    """Escreve primeiro num ficheiro temporário e só depois troca: se o PC desligar a meio, o antigo fica intacto."""
    tmp = FICHEIRO_MEMORIA + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(m, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, FICHEIRO_MEMORIA)
    except (OSError, TypeError, ValueError):
        try:
            os.remove(tmp)
        except OSError:
            pass


def voltas_completas(pista, comprimento):
    if pista in VOLTAS_OFICIAIS:
        return VOLTAS_OFICIAIS[pista]
    return math.ceil(305000 / comprimento) if comprimento else None


CORTES_PENALIZACAO = {0: 'drive-through', 1: 'stop & go', 4: 'penalização +{t} s', 6: 'desqualificado'}


def e_qualificacao(tipo):
    return 5 <= tipo <= 14


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


SECOS = ('S', 'M', 'H')
NOMES_COMPOSTOS = {'S': 'Macios', 'M': 'Médios', 'H': 'Duros', 'I': 'Intermédios', 'W': 'Chuva'}


STINT_MINIMO = 5   # voltas: um stint planeado mais curto do que isto não é estratégia, é uma paragem desperdiçada


def _repartir(voltas, conjuntos, minimos):
    """Distribui as voltas pelos stints: cada um com pelo menos o seu mínimo e no máximo a vida que o jogo dá
    ao conjunto; as voltas que sobram vão para os conjuntos mais rápidos. Devolve None se não chegar."""
    if sum(c['vida'] for c in conjuntos) < voltas or sum(minimos) > voltas \
            or any(c['vida'] < m for c, m in zip(conjuntos, minimos)):
        return None
    rep = list(minimos)
    resto = voltas - sum(minimos)
    for k in sorted(range(len(conjuntos)), key=lambda k: conjuntos[k]['delta']):
        mais = min(resto, conjuntos[k]['vida'] - rep[k])
        rep[k] += mais
        resto -= mais
    return rep


def planear(voltas, conjuntos, atual=None, perda_box_ms=22000, usados=(), volta_atual=1, janela=None, max_paragens=2):
    """Escolhe a estratégia mais rápida com os dados que o jogo envia para cada conjunto de pneus:
    voltas que lhe restam (vida) e diferença de ritmo por volta para o conjunto montado (delta, ms).

    voltas: voltas que faltam (contando a atual); conjuntos: candidatos para os stints seguintes;
    atual: o conjunto montado (o primeiro stint) ou None antes da corrida; usados: compostos já usados.
    Devolve a lista de planos, do mais rápido para o mais lento (um por número de paragens)."""
    # um conjunto sem voltas (o jogo diz vida 0) já não serve; o montado ainda faz esta volta até às boxes
    conjuntos = [c for c in conjuntos if c['vida'] >= 1]
    if atual and atual['vida'] < 1:
        atual = dict(atual, vida=1)
    if voltas <= 0 or not conjuntos and not atual:
        return []
    # conjuntos iguais (mesmo composto e desgaste) contam como um tipo com quantidade
    tipos = {}
    for c in conjuntos:
        tipos.setdefault((c['composto'], c['desgaste']), dict(c, qtd=0))['qtd'] += 1
    tipos = list(tipos.values())
    planos = {}

    def combinacoes(n, desde=0):
        if n == 0:
            yield []
            return
        for k in range(desde, len(tipos)):
            for resto in combinacoes(n - 1, k):
                seq = [tipos[k]] + resto
                if all(seq.count(t) <= t['qtd'] for t in seq):
                    yield seq

    for paragens in range(0, max_paragens + 1):
        n_novos = paragens if atual else paragens + 1
        if n_novos == 0 and not atual:
            continue
        for seq in combinacoes(n_novos):
            seq = sorted(seq, key=lambda c: -c['delta'])           # o mais rápido fica para o fim
            stints = ([atual] if atual else []) + seq
            secos = {c['composto'] for c in stints} | set(usados)
            if secos <= set(SECOS) and len(secos) < 2:
                continue                                           # regra: dois compostos de seco na corrida
            # o stint em curso pode acabar já (box nesta volta); os outros têm de valer a paragem
            minimo = STINT_MINIMO if voltas >= 2 * STINT_MINIMO else 1
            minimos = [1 if (k == 0 and atual) else minimo for k in range(len(stints))]
            rep = _repartir(voltas, stints, minimos)
            if not rep:
                continue
            if janela and atual and paragens == 1:
                # se der, a paragem fica na janela que o jogo recomenda
                ideal, ultima = janela
                lo, hi = max(1, voltas - stints[1]['vida']), min(stints[0]['vida'], voltas - minimos[1])
                alvo = min(max(ideal - volta_atual + 1, lo), hi)
                custo = lambda k: k * stints[0]['delta'] + (voltas - k) * stints[1]['delta']
                if lo <= alvo <= hi and custo(alvo) - custo(rep[0]) < 2000:
                    rep = [alvo, voltas - alvo]
            tempo = sum(r * c['delta'] for r, c in zip(rep, stints)) + paragens * perda_box_ms
            fim, lista = volta_atual - 1, []
            for r, c in zip(rep, stints):
                fim += r
                lista.append({'composto': c['composto'], 'novo': c['desgaste'] == 0, 'desgaste': c['desgaste'],
                              'voltas': r, 'ate_volta': fim})
            plano = {'paragens': paragens, 'stints': lista, 'tempo_ms': int(tempo),
                     'box': [st['ate_volta'] for st in lista[:-1]]}
            if paragens not in planos or tempo < planos[paragens]['tempo_ms']:
                planos[paragens] = plano
    return sorted(planos.values(), key=lambda p: p['tempo_ms'])


class Sessao:
    N_MINI = 8   # mini-setores por setor

    RECUO_FLASHBACK = 30   # metros: se a distância na volta recuar mais do que isto, foi um flashback

    def __init__(self, guardar=True):
        self.lock = threading.Lock()
        self.guardar = guardar     # False no modo demo: a simulação não mexe na memória das tuas corridas
        self.memoria = ler_memoria() if guardar else {}
        self.sessao = None
        self.referencia_pendente = None
        self.reiniciar(None)
        self.ultimo_pacote = 0.0
        self.formato = None
        self.versao_rapida = 0      # sobe a cada pacote de voltas/telemetria: há valores rápidos novos

    # ------------------------------------------------------------ gestão
    def reiniciar(self, uid):
        # a melhor volta da Q1 continua a servir de referência na Q2 e na Q3
        self.referencia_pendente = self._referencia_para_guardar() or self.referencia_pendente
        self.uid = uid
        self.jogador = 0
        self.espectador = False
        self.sessao = None
        self.voltas = None
        self.telem = None
        self.telem2 = None
        self.estado = None
        self.danos = None
        self.ativos = 0
        self.participantes = []
        self.historico = {}
        self.mensagens = deque(maxlen=12)
        self.volta_rapida = None
        self.paragens_vistas = {}
        self.dist_anterior = {}      # carro -> distância na volta no último pacote (para detetar flashbacks)
        self.bandeira_vermelha = False   # o jogo avisa com eventos: RDFL (vermelha) e LGOT (nova partida)
        self.fim_sessao = False          # evento SEND, ou o teu resultado final na corrida
        self.classificacao = None        # pacote de classificação final (fim da corrida)
        self.posicoes_voltas = {}        # volta -> posição de cada carro no início dessa volta (pacote do jogo)
        # o que o F1 2020 não envia e o painel calcula com os dados que recebe
        self.historico_do_jogo = False   # True quando chegam pacotes de histórico (2025/2026)
        self.hist_volta_atual = {}       # carro -> setores e validade da volta em curso (para construir o histórico)
        self.marcas = {}                 # carro -> ([distância total], [tempo de sessão]) para calcular diferenças
        self.box_anterior = {}           # carro -> estado das boxes no último pacote (para contar paragens)
        self.paragens_contadas = {}
        self.speed_traps = {}            # carro -> velocidade máxima (eventos SPTP)
        self.setores_vistos = {1: [], 2: []}   # distâncias onde o jogo mudou de setor
        self.tempo_sessao = 0.0
        self.perda_box_guardada = None
        # mini-setores de todos os carros
        self.mini_atual = {}         # carro -> {idx: tempo acumulado}
        self.mini_volta = {}         # carro -> número da volta a que mini_atual pertence
        self.mini_melhor_sessao = {}  # idx -> melhor tempo do segmento
        self._reiniciar_jogador()

    def _reiniciar_jogador(self):
        """Dados que só fazem sentido para o carro que estamos a seguir."""
        self.conjuntos = None
        self.conjunto_montado = None
        self.avisos_limites = (0, 0.0)   # (quantos, quando mudou) — para mostrar o aviso durante uns segundos
        self.minhas_posicoes = {}        # volta -> a tua posição ao começar essa volta (se o jogo não mandar as posições)
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
        self.referencia_origem = None
        self.mini_meu_melhor = {}    # idx -> melhor tempo do segmento (jogador)

    def _referencia_para_guardar(self):
        s = self.sessao
        if not (s and e_qualificacao(s['tipo']) and self.traco_melhor and not self.espectador):
            return None
        return {'pista': s['pista'], 'traco': self.traco_melhor, 'tempo': self.tempo_melhor_traco,
                'mini_meu': dict(self.mini_meu_melhor), 'mini_sessao': dict(self.mini_melhor_sessao),
                'origem': self.referencia_origem or SESSOES.get(s['tipo'], 'Qualificação')}

    def _recuperar_referencia(self, s):
        ref, self.referencia_pendente = self.referencia_pendente, None
        if not ref or ref['pista'] != s['pista'] or not e_qualificacao(s['tipo']) or self.tempo_melhor_traco:
            return
        self.traco_melhor, self.tempo_melhor_traco = ref['traco'], ref['tempo']
        self.mini_meu_melhor = dict(ref['mini_meu'])
        self.mini_melhor_sessao = dict(ref['mini_sessao'])
        self.referencia_origem = ref['origem']

    def _carro_seguido(self, cab):
        """O teu carro; a ver como espectador, o carro que o jogo está a mostrar."""
        s = self.sessao
        if s and s.get('espectador'):
            alvo = s.get('carro_espectador', 255)
            return alvo if alvo < 255 else 255
        return cab['jogador']

    def receber(self, cab, nome, c):
        with self.lock:
            self.ultimo_pacote = time.time()
            self.tempo_sessao = cab.get('tempo', 0.0)
            self.formato = cab['formato']
            if cab['uid'] != self.uid:
                self.reiniciar(cab['uid'])
            if nome == 'sessao':
                if self.sessao is None:
                    self._recuperar_referencia(c)
                self.sessao = c
                self.espectador = bool(c.get('espectador'))
                self._aprender_corrida(c)
            j = self._carro_seguido(cab)
            if j != self.jogador:
                self._reiniciar_jogador()
                self.jogador = j
            if nome in ('voltas', 'telemetria'):
                self.versao_rapida += 1
            if nome == 'voltas':
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
            elif nome == 'estado_e_danos':      # F1 2020: o estado do carro traz também desgaste e danos
                self.estado, self.danos = c
            elif nome == 'danos':
                self.danos = c
            elif nome == 'historico':
                if not self.historico_do_jogo:
                    self.historico_do_jogo = True
                    self.historico = {}         # o do jogo substitui o que o painel ia construindo
                self.historico[c['carro']] = c
            elif nome == 'conjuntos':
                carro, conj, montado = c
                if carro == self.jogador:
                    self.conjuntos = conj
                    self.conjunto_montado = montado if montado < len(conj) else None
            elif nome == 'classificacao':
                self.classificacao = c
                self.fim_sessao = True
            elif nome == 'posicoes_voltas':
                for k, linha in enumerate(c['voltas']):
                    self.posicoes_voltas[c['inicio'] + k + 1] = linha

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
            if self.formato == 2020:
                return CORES_2020.get(p['equipa_id'], '#98A2B3')
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
        vistos = getattr(self, 'setores_vistos', {1: [], 2: []})
        aprendido = lambda k: sorted(vistos[k])[len(vistos[k]) // 2] if vistos[k] else None
        s2 = (self.sessao or {}).get('setor2_inicio') or aprendido(1) or L / 3
        s3 = (self.sessao or {}).get('setor3_inicio') or aprendido(2) or 2 * L / 3
        if not (0 < s2 < s3 < L):
            s2, s3 = L / 3, 2 * L / 3
        lim = []
        for a, b in ((0, s2), (s2, s3), (s3, L)):
            for k in range(1, self.N_MINI + 1):
                lim.append(a + (b - a) * k / self.N_MINI)
        return lim  # 24 fins de segmento

    # ------------------------------------------------------------ voltas da corrida (automático)
    def _e_corrida_principal(self, s):
        """Num fim de semana com sprint há duas corridas: a principal é a última da estrutura que o jogo envia."""
        if not (15 <= s.get('tipo', 0) <= 17):
            return False
        corridas = [t for t in s.get('fim_de_semana') or [] if 15 <= t <= 17]
        return not corridas or s['tipo'] == corridas[-1]

    def _aprender_corrida(self, s):
        """Na corrida principal, guarda quantas voltas tem, por circuito e pela duração escolhida no jogo."""
        if not self._e_corrida_principal(s) or not s['voltas_total']:
            return
        completas = voltas_completas(s['pista'], s['comprimento'])
        m = self.memoria
        dur = s.get('duracao_sessao') or 0
        chave = f"{s['pista']}:{dur}"
        if m.get('corridas', {}).get(chave) == s['voltas_total']:
            return
        m.setdefault('corridas', {})[chave] = s['voltas_total']
        if completas:
            pct = round(s['voltas_total'] / completas, 3)
            m.setdefault('percentagem_por_duracao', {})[str(dur)] = pct
            m['percentagem'] = pct
        self._persistir()

    def voltas_corrida(self):
        """Devolve (voltas, de onde vem o número)."""
        s = self.sessao or {}
        total = s.get('voltas_total') or 0
        pista = s.get('pista')
        completas = voltas_completas(pista, s.get('comprimento'))
        if 15 <= s.get('tipo', 0) <= 17 and total:
            return total, 'da corrida'
        manual = self.memoria.get('voltas_manuais', {}).get(str(pista))
        if manual:
            return manual, 'definido por ti'
        dur = s.get('duracao_sessao') or 0
        corridas = self.memoria.get('corridas', {})
        guardada = corridas.get(f'{pista}:{dur}')
        pct = self.memoria.get('percentagem_por_duracao', {}).get(str(dur))
        plausivel = completas and 3 <= total <= completas + 2
        if plausivel and total != guardada:
            return total, 'do jogo'
        if guardada:
            return guardada, 'da última corrida aqui, com esta duração'
        if pct and completas:
            return max(3, round(completas * pct)), f'{round(pct * 100)}% da distância, a duração escolhida no jogo'
        antiga = corridas.get(str(pista))              # memória de versões anteriores (sem a duração)
        if antiga:
            return antiga, 'da última corrida aqui'
        pct = self.memoria.get('percentagem')
        if pct and completas:
            return max(3, round(completas * pct)), f'{round(pct * 100)}% da distância, como nas tuas corridas'
        if plausivel:
            return total, 'do jogo'
        if completas:
            return completas, 'distância completa'
        return None, ''

    def definir_voltas(self, voltas):
        """Voltas da corrida escolhidas à mão nas definições (None volta ao automático), para este circuito."""
        with self.lock:
            pista = (self.sessao or {}).get('pista')
            if pista is None:
                return False
            m = self.memoria.setdefault('voltas_manuais', {})
            if voltas:
                m[str(pista)] = int(voltas)
            else:
                m.pop(str(pista), None)
            self._persistir()
            return True

    def _proxima_tipo(self):
        s = self.sessao or {}
        fds = s.get('fim_de_semana') or []
        if s.get('tipo') in fds:
            k = fds.index(s['tipo'])
            if k + 1 < len(fds):
                return fds[k + 1]
        return None

    def _proxima_sessao(self):
        """A sessão seguinte do fim de semana, pela estrutura que o jogo envia."""
        t = self._proxima_tipo()
        return SESSOES.get(t) if t else None

    # ------------------------------------------------------------ medições guardadas por circuito
    def _guardar_medicoes(self):
        """Guarda consumo e desgaste por composto, para a corrida já os conhecer desde a primeira volta."""
        s = self.sessao
        if not s or s['tipo'] == 18 or self.espectador or not (self.consumos or self.desgaste_volta):
            return
        p = self.memoria.setdefault('pistas', {}).setdefault(str(s['pista']), {})
        if self.consumos:
            p['consumo'] = round(media(list(self.consumos)), 3)
        comp = self._composto(self.jogador)
        if self.desgaste_volta and comp in ('S', 'M', 'H', 'I', 'W'):
            p.setdefault('desgaste', {})[comp] = [round(media([d[k] for d in self.desgaste_volta]), 3) for k in range(4)]
        p['sessao'] = SESSOES.get(s['tipo'], 'Sessão')
        p['quando'] = int(time.time())
        self._persistir()

    def _persistir(self):
        if self.guardar:
            guardar_memoria(self.memoria)

    def _medicoes_pista(self):
        return self.memoria.get('pistas', {}).get(str((self.sessao or {}).get('pista')), {})

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
            self.bandeira_vermelha = True
            self._msg('Bandeira vermelha', '#FF4D4D')
        elif cod in ('LGOT', 'SSTA'):
            self.bandeira_vermelha = False
        elif cod == 'SEND':
            self.fim_sessao = True
        elif cod == 'SPTP' and 'velocidade' in ev:
            self.speed_traps[ev['carro']] = max(self.speed_traps.get(ev['carro'], 0), ev['velocidade'])
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
        if voltas and voltas[0]['paragens'] is None:
            self._completar_2020(voltas)
        self.voltas = voltas
        lim = self._limites_mini()
        j = self.jogador
        if j < len(voltas):
            if self.sessao and 15 <= self.sessao['tipo'] <= 17 and voltas[j]['resultado'] >= 3:
                self.fim_sessao = True       # terminaste (ou abandonaste): o jogo dá o resultado final
            n = voltas[j]['avisos_limites']
            if n != self.avisos_limites[0]:
                self.avisos_limites = (n, time.time())
        for i, v in enumerate(voltas):
            if v['resultado'] < 2:
                continue
            # paragens nas boxes (mensagem para a direção de corrida)
            p0 = self.paragens_vistas.get(i)
            if p0 is not None and v['paragens'] > p0:
                comp = {'S': 'Macios', 'M': 'Médios', 'H': 'Duros', 'I': 'Intermédios', 'W': 'Chuva'}.get(self._composto(i), '')
                self._msg('{c} — box' + (f', {comp}' if comp else ''), '#98A2B3', v['volta'], carro=i)
            self.paragens_vistas[i] = max(p0 or 0, v['paragens'])   # um flashback não repete a mensagem
            # mini-setores
            d = v['dist_volta']
            if self.mini_volta.get(i) != v['volta']:
                self._fechar_mini(i)
                self.mini_volta[i] = v['volta']
                self.mini_atual[i] = {}
            elif d < self.dist_anterior.get(i, d) - self.RECUO_FLASHBACK:
                # flashback: esquece os mini-setores à frente do ponto para onde o jogo voltou
                m = self.mini_atual.get(i, {})
                for k in [k for k in m if lim[k] > d]:
                    del m[k]
            self.dist_anterior[i] = d
            if d > 0:
                m = self.mini_atual[i]
                for k, fim in enumerate(lim):
                    if d >= fim and k not in m:
                        m[k] = v['atual']
        if not self.historico_do_jogo:
            self._construir_historico(voltas)
        self._aprender_setores(anterior, voltas)
        self._jogador_volta(anterior)

    # ------------------------------------------------------------ o que o F1 2020 não envia
    PASSO_MARCAS = 20     # metros entre marcas para calcular as diferenças

    def _completar_2020(self, voltas):
        """Paragens, speed trap e diferenças para o carro da frente e para o líder, calculados com o que o jogo
        envia: o estado das boxes, os eventos SPTP e a hora da sessão a que cada carro passa em cada ponto da pista."""
        t = self.tempo_sessao
        L = self._comprimento()
        for i, v in enumerate(voltas):
            b0 = self.box_anterior.get(i, v['box_estado'])
            if b0 == 0 and v['box_estado'] != 0 and self.sessao and 15 <= self.sessao['tipo'] <= 17:
                self.paragens_contadas[i] = self.paragens_contadas.get(i, 0) + 1
            self.box_anterior[i] = v['box_estado']
            v['paragens'] = self.paragens_contadas.get(i, 0)
            v['speed_trap'] = self.speed_traps.get(i, 0.0)
            if v['resultado'] < 2:
                continue
            dists, tempos = self.marcas.setdefault(i, ([], []))
            d = v['dist_total']
            if dists and d < dists[-1] - 50:                      # flashback ou recomeço: recomeça as marcas
                dists.clear(); tempos.clear()
            if not dists or d - dists[-1] >= self.PASSO_MARCAS:
                dists.append(d); tempos.append(t)
                limite = int(1.5 * L / self.PASSO_MARCAS) + 20
                if len(dists) > 2 * limite:                       # guarda só a última volta e meia
                    del dists[:-limite]; del tempos[:-limite]
        corrida = bool(self.sessao) and 15 <= self.sessao['tipo'] <= 17     # só na corrida as diferenças fazem sentido
        ordem = sorted((i for i, v in enumerate(voltas) if v['resultado'] >= 2 and v['posicao']), key=lambda i: voltas[i]['posicao']) \
            if corrida else []
        lider = ordem[0] if ordem else None
        for k, i in enumerate(ordem):
            v = voltas[i]
            v['para_lider'] = self._diferenca(lider, v['dist_total'], t) if k else 0
            v['para_frente'] = self._diferenca(ordem[k - 1], v['dist_total'], t) if k else 0
        if not corrida:
            for v in voltas:
                v['para_lider'] = v['para_frente'] = 0

    def _diferenca(self, alvo, dist, agora):
        """Há quanto tempo (ms) o carro `alvo` passou na distância `dist`."""
        dists, tempos = self.marcas.get(alvo, ([], []))
        if not dists or dist > dists[-1]:
            return 0                      # está à frente do carro de referência (ultrapassagem a acontecer)
        if dist < dists[0]:
            return None                   # o painel ainda não viu o outro carro passar aqui: diferença desconhecida
        k = bisect.bisect_left(dists, dist)
        if k == 0:
            t = tempos[0]
        else:
            d0, d1, t0, t1 = dists[k - 1], dists[k], tempos[k - 1], tempos[k]
            t = t0 + (t1 - t0) * (dist - d0) / (d1 - d0) if d1 > d0 else t1
        return max(0, int(round((agora - t) * 1000)))

    def _construir_historico(self, voltas):
        """Sem pacotes de histórico (F1 2020): constrói as voltas e os stints de cada carro com o que vê passar."""
        for i, v in enumerate(voltas):
            if v['resultado'] < 2 or not v['volta']:
                continue
            h = self.historico.setdefault(i, {'carro': i, 'voltas': [], 'stints': [], 'melhor_volta': 0, 'melhor_s': (0, 0, 0)})
            st = self.hist_volta_atual.get(i)
            visual = self.estado[i]['composto'] if self.estado and i < len(self.estado) else 0
            if st is None or v['volta'] < st['volta']:            # início, ou flashback para a volta anterior
                del h['voltas'][max(v['volta'] - 1, 0):]
                st = self.hist_volta_atual[i] = {'volta': v['volta'], 's1': 0, 's2': 0, 'inv': False}
            if v['volta'] > st['volta']:
                n = st['volta']
                if v['ultima']:
                    while len(h['voltas']) < n - 1:
                        h['voltas'].append({'tempo': 0, 's1': 0, 's2': 0, 's3': 0, 'valida': False})
                    s1, s2 = st['s1'], st['s2']
                    volta = {'tempo': v['ultima'], 's1': s1, 's2': s2, 's3': v['ultima'] - s1 - s2 if s1 and s2 else 0,
                             'valida': not st['inv']}
                    h['voltas'][n - 1:n] = [volta]
                    validas = [(x['tempo'], k + 1) for k, x in enumerate(h['voltas']) if x['tempo'] and x['valida']]
                    h['melhor_volta'] = min(validas)[1] if validas else 0
                st = self.hist_volta_atual[i] = {'volta': v['volta'], 's1': 0, 's2': 0, 'inv': False}
            st['s1'] = v['s1'] or st['s1']
            st['s2'] = v['s2'] or st['s2']
            st['inv'] = st['inv'] or bool(v['invalida'])
            # stints: quando o composto muda, o anterior acabou na última volta completa
            if visual:
                if not h['stints']:
                    h['stints'].append({'fim': 255, 'real': 0, 'visual': visual})
                elif h['stints'][-1]['visual'] != visual:
                    h['stints'][-1]['fim'] = max(v['volta'] - 1, 1)
                    h['stints'].append({'fim': 255, 'real': 0, 'visual': visual})

    def _aprender_setores(self, anterior, voltas):
        """Sem os limites dos setores na sessão (F1 2020), aprende-os no sítio onde o jogo muda de setor."""
        if (self.sessao or {}).get('setor2_inicio') or not anterior:
            return
        for i, v in enumerate(voltas):
            if i < len(anterior) and anterior[i]['volta'] == v['volta'] and v['setor'] == anterior[i]['setor'] + 1 \
                    and v['setor'] in (1, 2):
                lista = self.setores_vistos[v['setor']]
                if len(lista) < 15:
                    lista.append(v['dist_volta'])

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
        d = v['dist_volta']
        if self.minha_volta is not None and v['volta'] < self.minha_volta:
            # flashback para antes da linha de meta: a volta recomeça a meio, por isso não serve de referência
            self.minha_volta = v['volta']
            self.traco_atual = {}
            self.inicio_volta = {}
            self.estado_volta_atual = v['estado_piloto']
            return
        if self.traco_atual and anterior and j < len(anterior) and anterior[j]['volta'] == v['volta'] \
                and d < anterior[j]['dist_volta'] - self.RECUO_FLASHBACK:
            # flashback a meio da volta: os pontos à frente vão ser percorridos outra vez
            b = int(d // 10)
            self.traco_atual = {k: t for k, t in self.traco_atual.items() if k <= b}
        if v['posicao'] and v['volta'] not in self.minhas_posicoes:
            self.minhas_posicoes[v['volta']] = v['posicao']
        if self.minha_volta is None:
            self.minha_volta = v['volta']
            self._marcar_inicio_volta()
            self.estado_volta_atual = v['estado_piloto']
        elif v['volta'] != self.minha_volta:
            ultima = v['ultima']
            # traço de referência = melhor volta válida, percorrida do início ao fim com o painel aberto
            completa = bool(self.traco_atual) and min(self.traco_atual) <= 2 \
                and max(self.traco_atual) * 10 >= self._comprimento() - 300
            if ultima and completa and self.estado_volta_atual in (1, 4) and not self._ultima_invalida(anterior):
                if self.tempo_melhor_traco is None or ultima < self.tempo_melhor_traco:
                    self.tempo_melhor_traco = ultima
                    self.traco_melhor = dict(self.traco_atual)
                    self.referencia_origem = SESSOES.get((self.sessao or {}).get('tipo'), None)
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
                self._guardar_medicoes()
            self.minha_volta = v['volta']
            self.traco_atual = {}
            self.estado_volta_atual = v['estado_piloto']
            self._marcar_inicio_volta()
        # traço tempo-distância desta volta (cada 10 m); só depois de fechar a anterior
        if d > 0:
            self.traco_atual.setdefault(int(d // 10), v['atual'])

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
        t = None
        if h and h['melhor_volta'] and h['melhor_volta'] <= len(h['voltas']):
            t = h['voltas'][h['melhor_volta'] - 1]['tempo'] or None
        if self.voltas and i < len(self.voltas) and self.voltas[i].get('melhor_ms'):
            t = min(t, self.voltas[i]['melhor_ms']) if t else self.voltas[i]['melhor_ms']   # F1 2020 dá-a nas voltas
        return t

    # ------------------------------------------------------------ fotografia para os ecrãs
    def fotografia(self):
        with self.lock:
            return self._fotografia()

    def rapido(self):
        """Os valores que mudam a cada pacote (canal rápido, até 60 por segundo): mudança, velocidade, rotações,
        luzes, tempo da volta atual, delta e previsão. Pequeno de propósito: o resto vai na fotografia (5 por segundo)."""
        with self.lock:
            j = self.jogador
            if not self.voltas or not 0 <= j < len(self.voltas):
                return None
            v = self.voltas[j]
            delta = self._delta_vivo(v)
            r = {'t': v['atual'], 'd': delta, 's': v['setor'], 'dv': round(v['dist_volta']),
                 'p': self.tempo_melhor_traco + delta if delta is not None and self.tempo_melhor_traco else None}
            tel = self.telem[j] if self.telem and j < len(self.telem) else None
            if tel:
                r.update({'g': tel['mudanca'], 'v': tel['velocidade'], 'r': tel['rpm'], 'l': tel['luzes_rpm']})
            return r

    def _fotografia(self):
        agora = time.time()
        ligado = agora - self.ultimo_pacote < 3
        if not (self.sessao and self.voltas):
            return {'ligado': ligado, 'pronto': False, 'formato': self.formato}
        if not 0 <= self.jogador < len(self.voltas):
            # a ver como espectador sem carro escolhido: não há "o teu carro" para mostrar
            return {'ligado': ligado, 'pronto': False, 'formato': self.formato, 'espectador': True}
        s = self.sessao
        tipo = s['tipo']
        ecra = ecra_da_sessao(tipo)
        L = self._comprimento()
        out = {
            'ligado': ligado, 'pronto': True, 'formato': self.formato, 'ecra': ecra, 'espectador': self.espectador,
            'sessao': {
                'tipo': tipo, 'nome': SESSOES.get(tipo, 'Sessão'), 'pista': PISTAS.get(s['pista'], f"Pista {s['pista']}"),
                'comprimento': L, 'voltas_total': s['voltas_total'], 'restante': s['tempo_restante'],
                'duracao': s['duracao'], 'temp_ar': s['temp_ar'], 'temp_pista': s['temp_pista'],
                'meteo': METEO.get(s['tempo_meteo'], ''), 'safety_car': s['safety_car'],
                'previsao': self._previsao(), 'box_ideal': s['box_ideal'], 'box_ultima': s['box_ultima'],
                'box_reentrada': s['box_reentrada'],
                'bandeira_vermelha': self.bandeira_vermelha or bool(self.estado and self.jogador < len(self.estado)
                                                                    and self.estado[self.jogador]['bandeira'] == 4),
                'proxima': self._proxima_sessao(), 'zona_amarela_m': self._amarela_a_frente(),
                'setores_m': [round(x) for x in self._limites_mini()[self.N_MINI - 1::self.N_MINI]],
            },
        }
        vc, fonte = self.voltas_corrida()
        out['sessao']['voltas_corrida'] = vc
        out['sessao']['voltas_corrida_fonte'] = fonte
        out['sessao']['voltas_manuais'] = self.memoria.get('voltas_manuais', {}).get(str(s['pista']))
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
        out['sessao']['chuva'] = self._chuva_prevista()
        out['alertas'] = [] if self.fim_sessao else self._alertas(out)   # sessão acabada: já não há nada a avisar
        if self.fim_sessao:
            out['resumo'] = self._resumo(out)
        return out

    RESULTADOS = {3: 'Terminou', 4: 'Não terminou', 5: 'Desclassificado', 6: 'Não classificado', 7: 'Desistiu'}

    def _voltas_resumo(self, j):
        """Todas as voltas do histórico do jogo, com o composto, setores e se foi de entrada/saída das boxes."""
        h = self.historico.get(j)
        if not h:
            return [], []
        voltas, lista, stints, inicio = h['voltas'], [], [], 1
        for k, st in enumerate(h['stints']):
            fim = st['fim'] if st['fim'] != 255 else len(voltas)
            fim = min(fim, len(voltas))
            comp = COMPOSTOS.get(st['visual'], '?')
            tempos = []
            for n in range(inicio, fim + 1):
                v = voltas[n - 1]
                if not v['tempo']:
                    continue
                box = 'saida' if n == inicio and (k > 0 or self.sessao['tipo'] < 15) else \
                      'entrada' if n == fim and st['fim'] != 255 else None
                lista.append({'n': n, 'ms': v['tempo'], 's': [v['s1'], v['s2'], v['s3']], 'valida': v['valida'],
                              'composto': comp, 'box': box})
                if v['valida'] and not box and n > 1:
                    tempos.append(v['tempo'])
            stints.append({'composto': comp, 'voltas': max(fim - inicio + 1, 0), 'ate_volta': fim,
                           'media_ms': int(media(tempos)) if tempos else None, 'melhor_ms': min(tempos) if tempos else None})
            inicio = fim + 1
        return lista, stints

    def _resumo(self, out):
        """Resumo da sessão que acabou, com o que o jogo enviou (classificação final, posições, histórico de voltas)."""
        j, s, eu = self.jogador, self.sessao, out['eu']
        lista, stints = self._voltas_resumo(j)
        r = {'sessao': SESSOES.get(s['tipo'], 'Sessão'), 'ecra': out['ecra'], 'proxima': self._proxima_sessao(),
             'posicao': eu['pos'], 'melhor_ms': eu.get('melhor_ms'), 'voltas': len(lista), 'stints': stints,
             'voltas_lista': lista, 'consumo_volta': eu.get('consumo_volta'), 'desgaste_volta': eu.get('desgaste_volta'),
             'cor': eu.get('cor'), 'speed_trap': eu.get('speed_trap')}
        vr = out.get('volta_rapida')
        if vr:
            r['mais_rapida'] = {'codigo': vr['codigo'], 'ms': vr['ms']}
        if out['ecra'] == 'corrida':
            self._resumo_corrida(r, out)
        elif out['ecra'] == 'qualificacao':
            self._resumo_quali(r, out)
        else:
            self._resumo_treinos(r, out)
        return r

    def _resumo_corrida(self, r, out):
        j, eu = self.jogador, out['eu']
        r.update({'grelha': eu.get('grelha'), 'paragens': eu.get('paragens'),
                  'resultado': self.RESULTADOS.get(self.voltas[j]['resultado'], ''), 'fonte': 'histórico do jogo'})
        fc = self.classificacao
        tabela = []
        if fc and j < len(fc) and fc[j]['posicao']:
            c = fc[j]
            r.update({'posicao': c['posicao'], 'grelha': c['grelha'], 'pontos': c['pontos'],
                      'paragens': c['paragens'], 'tempo_total_s': round(c['tempo_total'], 3),
                      'penalizacoes_s': c['penalizacoes_s'], 'n_penalizacoes': c['n_penalizacoes'],
                      'resultado': self.RESULTADOS.get(c['resultado'], ''),
                      'melhor_ms': c['melhor_ms'] or r['melhor_ms'], 'voltas': c['voltas'],
                      'fonte': 'classificação final do jogo'})
            ordem = sorted((k for k, x in enumerate(fc) if x['posicao']), key=lambda k: fc[k]['posicao'])
            venc = fc[ordem[0]] if ordem else None
            melhores = sorted(x['melhor_ms'] for x in fc if x['posicao'] and x['melhor_ms'])
            for k in ordem:
                x = fc[k]
                if x['resultado'] in (4, 5, 6, 7):
                    dif = {4: 'DNF', 5: 'DSQ', 6: 'NC', 7: 'Desistiu'}[x['resultado']]
                elif k == ordem[0]:
                    dif = fmt_tempo_total(x['tempo_total'])
                elif venc and x['voltas'] < venc['voltas']:
                    dif = f"+{venc['voltas'] - x['voltas']} V"
                else:
                    dif = f"+{x['tempo_total'] - venc['tempo_total']:.3f}"
                tabela.append({'pos': x['posicao'], 'codigo': self._cod(k), 'cor': self._cor(k), 'eu': k == j,
                               'pontos': x['pontos'], 'paragens': x['paragens'], 'dif': dif, 'grelha': x['grelha'],
                               'compostos': [COMPOSTOS.get(st['visual'], '?') for st in x['stints']],
                               'melhor_ms': x['melhor_ms'], 'volta_rapida': bool(melhores) and x['melhor_ms'] == melhores[0]})
            if c['stints'] and all(st['fim'] for st in c['stints']):
                # os stints da classificação final (com as voltas em que paraste) mandam sobre o histórico
                fim_ant, novos = 0, []
                for st in c['stints']:
                    tempos = [v['ms'] for v in r['voltas_lista']
                              if fim_ant < v['n'] <= st['fim'] and v['valida'] and not v['box'] and v['n'] > 1]
                    novos.append({'composto': COMPOSTOS.get(st['visual'], '?'), 'voltas': st['fim'] - fim_ant,
                                  'ate_volta': st['fim'], 'media_ms': int(media(tempos)) if tempos else None,
                                  'melhor_ms': min(tempos) if tempos else None})
                    fim_ant = st['fim']
                r['stints'] = novos
            if venc and ordem[0] != j and venc['tempo_total'] and c['tempo_total'] and c['voltas'] == venc['voltas']:
                r['para_vencedor_s'] = round(c['tempo_total'] - venc['tempo_total'], 3)
            if c['melhor_ms'] and melhores:
                r['melhor_rank'] = melhores.index(c['melhor_ms']) + 1
        else:
            for c in out['carros']:
                tabela.append({'pos': c['pos'], 'codigo': c['codigo'], 'cor': c['cor'], 'eu': c['eu'], 'pontos': None,
                               'paragens': c['paragens'], 'dif': '', 'grelha': c['grelha'], 'compostos': [c['composto']],
                               'melhor_ms': c['melhor_ms'], 'volta_rapida': False})
        r['tabela'] = tabela
        r['n_carros'] = len(tabela) or len(out['carros'])
        r['ganhos'] = (r['grelha'] or 0) - r['posicao'] if r.get('grelha') else None
        # posição volta a volta: o pacote do jogo, ou o que o painel foi vendo
        if self.posicoes_voltas:
            pos = {v: linha[j] for v, linha in self.posicoes_voltas.items() if j < len(linha) and linha[j]}
        else:
            pos = dict(self.minhas_posicoes)
        if r.get('grelha'):
            pos.setdefault(1, r['grelha'])
        if pos:
            pos[max(max(pos) + 1, r.get('voltas') or 0)] = r['posicao']     # posição final, depois da bandeira
        r['posicoes'] = [{'volta': v, 'pos': p} for v, p in sorted(pos.items())]
        r['box_voltas'] = [st['ate_volta'] for st in r['stints'][:-1]]
        r['ritmos'] = self._ritmos_corrida()

    def _ritmos_corrida(self):
        """Ritmo de corrida de cada piloto: mediana das voltas limpas (sem a 1.ª, nem entradas/saídas das boxes),
        do histórico de voltas que o jogo envia para todos os carros."""
        lista = []
        for i, h in self.historico.items():
            excluir = {1}
            for st in h['stints'][:-1]:
                if st['fim'] and st['fim'] != 255:
                    excluir |= {st['fim'], st['fim'] + 1}
            tempos = sorted(v['tempo'] for k, v in enumerate(h['voltas'], start=1)
                            if v['tempo'] and v['valida'] and k not in excluir)
            if len(tempos) >= 3:
                lista.append({'idx': i, 'codigo': self._cod(i), 'cor': self._cor(i), 'eu': i == self.jogador,
                              'ms': tempos[len(tempos) // 2]})
        lista.sort(key=lambda x: x['ms'])
        for k, x in enumerate(lista):
            x['rank'] = k + 1
        return [x for x in lista if x['rank'] <= 6 or x['eu']]

    def _resumo_quali(self, r, out):
        j = self.jogador
        q = out.get('quali') or {}
        porIdx = {c['idx']: c for c in out['carros']}
        ordem = [porIdx[i] for i in q.get('ordem') or [] if i in porIdx]
        if j in (q.get('ordem') or []):
            r['posicao'] = q['ordem'].index(j) + 1
        pole = ordem[0] if ordem else None
        if pole and pole['melhor_ms']:
            r['pole'] = {'codigo': pole['codigo'], 'ms': pole['melhor_ms']}
            if r['melhor_ms']:
                r['para_pole_ms'] = r['melhor_ms'] - pole['melhor_ms']
        if q.get('corte'):
            r['passou'] = r['posicao'] <= q['corte']
            r['corte'] = q['corte']
        r['ideal_ms'] = q.get('ideal_ms')
        meus = self._meus_melhores_setores(j)
        sessao = self._melhores_setores_sessao()
        r['setores'] = [{'meu': meus[k], 'melhor': sessao[k]} for k in range(3)]
        r['conjuntos'] = q.get('conjuntos') or []
        r['tabela'] = [{'pos': k + 1, 'codigo': c['codigo'], 'cor': c['cor'], 'eu': c['eu'], 'melhor_ms': c['melhor_ms'],
                        'dif_ms': c['melhor_ms'] - pole['melhor_ms'] if c['melhor_ms'] and pole and pole['melhor_ms'] else None,
                        'fora': bool(q.get('corte')) and k >= q['corte']} for k, c in enumerate(ordem)]
        r['tentativas'] = sum(1 for v in r['voltas_lista'] if not v['box'])
        # onde perdeste tempo: a tua melhor volta, setor a setor, contra a da pole e a do carro à tua frente
        meus = self._setores_melhor_volta(j)
        r['comparacao'] = []
        if meus and r['posicao'] > 1:
            rivais = [ordem[0]] + ([ordem[r['posicao'] - 2]] if r['posicao'] > 2 else [])
            for c in rivais:
                deles = self._setores_melhor_volta(c['idx'])
                if deles:
                    r['comparacao'].append({'codigo': c['codigo'], 'cor': c['cor'], 'pos': ordem.index(c) + 1,
                                            'total_ms': sum(meus) - sum(deles),
                                            'setores_ms': [a - b for a, b in zip(meus, deles)]})

    def _setores_melhor_volta(self, i):
        h = self.historico.get(i)
        if not h or not h['melhor_volta'] or h['melhor_volta'] > len(h['voltas']):
            return None
        v = h['voltas'][h['melhor_volta'] - 1]
        return [v['s1'], v['s2'], v['s3']] if v['tempo'] and all((v['s1'], v['s2'], v['s3'])) else None

    def _resumo_treinos(self, r, out):
        t = out.get('treinos') or {}
        prog = t.get('programa') or []
        r['programa'] = {'feitas': sum(1 for p in prog if p['feito']), 'total': len(prog),
                         'falta': [p['nome'] for p in prog if not p['feito']], 'tarefas': prog}
        # a simulação de corrida é o stint com mais voltas limpas seguidas (não necessariamente o último)
        melhor_run = []
        fim_ant = 0
        for st in r['stints']:
            run = [v for v in r['voltas_lista'] if fim_ant < v['n'] <= st['ate_volta'] and v['valida'] and not v['box']]
            if len(run) > len(melhor_run):
                melhor_run = run
            fim_ant = st['ate_volta']
        if len(melhor_run) >= 3:
            tempos = [v['ms'] for v in melhor_run]
            deg = regressao(tempos)
            r['ritmo'] = {'media_ms': int(media(tempos)), 'degradacao_ms': round(deg), 'voltas': tempos,
                          'consistencia_ms': round(desvio(tempos)), 'composto': melhor_run[0]['composto'],
                          'de_volta': melhor_run[0]['n'], 'projecao': [int(tempos[-1] + deg * (k + 1)) for k in range(3)]}
        prox = self._proxima_tipo()
        if prox and 1 <= prox <= 4:
            r['proxima_programa'] = [self.TAREFAS[k] for k in self._tarefas_do_treino(prox)]
        r['setores'] = t.get('setores') or []
        r['plano_corrida'] = t.get('plano_corrida')
        vc, fonte = self.voltas_corrida()
        if r['consumo_volta'] and vc:
            r['combustivel_corrida'] = {'kg': round(r['consumo_volta'] * (vc + 1), 1), 'voltas': vc, 'fonte': fonte}
        tabela = sorted((c for c in out['carros'] if c['melhor_ms']), key=lambda c: c['melhor_ms'])
        melhor = tabela[0]['melhor_ms'] if tabela else None
        linhas = [{'pos': k + 1, 'codigo': c['codigo'], 'cor': c['cor'], 'eu': c['eu'], 'melhor_ms': c['melhor_ms'],
                   'dif_ms': c['melhor_ms'] - melhor} for k, c in enumerate(tabela)]
        r['tabela'] = [x for x in linhas if x['pos'] <= 10 or x['eu']]

    def _amarela_a_frente(self):
        """Metros até à próxima zona com bandeira amarela (0 se já estás dentro dela), pelas zonas dos comissários."""
        s, j = self.sessao, self.jogador
        zonas = sorted(s.get('zonas') or [], key=lambda z: z['inicio'])
        if not zonas or j >= len(self.voltas):
            return None
        L = self._comprimento()
        f = (self.voltas[j]['dist_volta'] / L) % 1
        melhor = None
        for k, z in enumerate(zonas):
            if z['bandeira'] != 3:
                continue
            fim = zonas[k + 1]['inicio'] if k + 1 < len(zonas) else 1.0
            dentro = z['inicio'] <= f < fim
            m = 0 if dentro else round(((z['inicio'] - f) % 1) * L)
            melhor = m if melhor is None else min(melhor, m)
        return melhor

    def _chuva_prevista(self):
        """Primeira previsão desta sessão, nos próximos 30 min, com probabilidade de chuva de 40% ou mais."""
        s = self.sessao
        for p in sorted(s['previsao'], key=lambda p: p['minutos']):
            if p['chuva'] is None:          # F1 2020: só diz o tempo previsto
                chove = p['tempo_meteo'] >= 3
            else:
                chove = p['chuva'] >= 40
            if p['tipo'] == s['tipo'] and 0 < p['minutos'] <= 30 and chove:
                return {'min': p['minutos'], 'chuva': p['chuva']}
        return None

    def _alertas(self, out):
        """Avisos curtos para ler de relance, do mais grave para o menos grave."""
        s, eu, ecra = out['sessao'], out['eu'], out['ecra']
        res = []

        def alerta(ident, nivel, texto):
            res.append({'id': ident, 'nivel': nivel, 'texto': texto})

        em_pista = eu.get('estado_piloto', 0) != 0 and not eu.get('box')
        bandeira = eu.get('bandeira')
        if s.get('bandeira_vermelha'):
            alerta('vermelha', 'perigo', 'Bandeira vermelha — sessão suspensa')
        if eu.get('drive_through') or eu.get('stop_go'):
            qual = 'Stop & go' if eu.get('stop_go') else 'Drive-through'
            alerta('penal', 'perigo', f'{qual} por cumprir' + (' — cumpres nesta paragem' if eu.get('cumpre_penalizacao') else ''))
        if s['safety_car'] in (1, 2):
            nome = 'Safety Car' if s['safety_car'] == 1 else 'Virtual Safety Car'
            d = eu.get('delta_sc')
            if d is not None and d < 0:
                alerta('sc', 'perigo', f'{nome} · delta {d:+.1f} s — abranda')
            else:
                alerta('sc', 'aviso', nome + (f' · delta {d:+.1f} s' if d is not None else ''))
        amarela = s.get('zona_amarela_m')
        if bandeira == 3 or amarela == 0:
            alerta('amarela', 'aviso', 'Bandeira amarela — sem ultrapassagens')
        elif amarela is not None and amarela <= 1500 and em_pista:
            alerta('amarela', 'aviso', f'Bandeira amarela daqui a {amarela} m')
        if bandeira == 2:
            alerta('azul', 'aviso', 'Bandeira azul — deixa passar')
        n, quando = self.avisos_limites
        if n and time.time() - quando < 15:
            alerta('limites', 'aviso', f"{n} {'aviso' if n == 1 else 'avisos'} de limites de pista")
        # tempo
        seco = eu.get('composto') in ('S', 'M', 'H')
        a_chover = (self.sessao.get('tempo_meteo') or 0) >= 3
        if a_chover and seco and em_pista:
            alerta('chuva', 'perigo', 'Está a chover e tens pneus de seco')
        elif s['chuva'] and seco:
            c = s['chuva']
            quanto = f"Chuva {c['chuva']}%" if c['chuva'] is not None else 'Chuva prevista'
            alerta('chuva', 'aviso', f"{quanto} daqui a {c['min']} min — prepara os intermédios")
        # carro
        dan = eu.get('danos') or {}
        asa = max(dan.get('asa_fe', 0), dan.get('asa_fd', 0))
        if asa >= 25:
            alerta('asa', 'aviso', f'Asa da frente danificada ({asa}%) — pondera trocá-la')
        interior = eu.get('pneus_int') or []
        if em_pista and interior and max(interior) > 115:
            alerta('temp', 'aviso', f'Pneus a sobreaquecer ({max(interior)}° no interior)')
        if ecra == 'corrida':
            vida = eu.get('vida_restante_voltas')
            faltam = (s.get('voltas_total') or 0) - (eu.get('volta') or 0)
            if vida is not None and vida <= 2 and faltam > vida:
                alerta('box', 'perigo', 'Pneus no limite — box ' + ('nesta volta' if vida == 0 else f'nas próximas {vida} voltas'))
            elif s['box_ideal'] and s['box_ideal'] <= eu.get('volta', 0) <= (s['box_ultima'] or s['box_ideal']):
                alerta('box', 'info', f"Janela de box aberta até à volta {s['box_ultima'] or s['box_ideal']}")
            plano = (out.get('corrida') or {}).get('plano')
            if plano and plano['box'] and plano['box'][0] == eu.get('volta') and not eu.get('box') \
                    and not any(a['id'] == 'box' and a['nivel'] == 'perigo' for a in res):
                prox = plano['stints'][1]
                res[:] = [a for a in res if a['id'] != 'box']
                alerta('box', 'aviso', f"Box nesta volta — {NOMES_COMPOSTOS[prox['composto']]} {'novos' if prox['novo'] else 'usados'}")
            margem = eu.get('margem_voltas')
            if margem is not None and margem < -0.2:
                alerta('fuel', 'aviso', f'Combustível curto: faltam {abs(margem):.1f} voltas — poupa')
        ordem = {'perigo': 0, 'aviso': 1, 'info': 2}
        res.sort(key=lambda a: ordem[a['nivel']])
        return res

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
            'box': v['box_estado'] > 0, 'referencia_origem': self.referencia_origem,
            'delta_sc': round(v['delta_sc'], 1) if self.sessao['safety_car'] in (1, 2) else None,
            'drive_through': v['drive_through'], 'stop_go': v['stop_go'],
            'cumpre_penalizacao': bool(v['cumpre_penalizacao']), 'avisos_limites': v['avisos_limites'],
        }
        h = self.historico.get(j)
        if h and h['melhor_volta'] and h['melhor_volta'] <= len(hist):
            eu['melhor_volta_num'] = h['melhor_volta']
            mv = hist[h['melhor_volta'] - 1]
            eu['melhor_setores'] = [mv['s1'], mv['s2'], mv['s3']]
        ms = eu.get('melhor_setores')
        if not (ms and all(ms)) and v.get('melhor_setores') and all(v['melhor_setores']):
            eu['melhor_setores'] = v['melhor_setores']          # F1 2020: os setores da melhor volta vêm nas voltas
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
                'bandeira': est['bandeira'], 'travao_bias': est['travao_bias'], 'rpm_max': est['rpm_max'],
            })
        eu['ajuda'] = self._ajuda(j)
        if tel:
            eu.update({'pneus_sup': tel['pneus_sup'], 'pneus_int': tel['pneus_int'], 'travoes': tel['travoes_temp'],
                       'pressao': tel['pressao'], 'motor_temp': tel['motor_temp'], 'velocidade': tel['velocidade'],
                       'mudanca': tel['mudanca'], 'rpm': tel['rpm'], 'luzes_rpm': tel['luzes_rpm']})
        eu['dist_volta'] = v['dist_volta']
        eu['setores_sessao'] = self._melhores_setores_sessao()
        if dan:
            eu['danos'] = dan
        if t2:
            eu['aero'] = {'modo': t2['aero_modo'], 'disp': t2['aero_disp'], 'dist': t2['aero_dist'],
                          'ovtk_disp': t2['ovtk_disp'], 'ovtk_ativo': t2['ovtk_ativo'], 'ovtk_dist': t2['ovtk_dist'],
                          'regras_2026': t2['regras_2026']}
        # consumo e desgaste: o que mediste nesta sessão; até lá, o que ficou guardado dos treinos neste circuito
        guardado = self._medicoes_pista()
        origem = f"medido em {guardado.get('sessao', 'sessões anteriores')}"
        eu['consumo_volta'], eu['consumo_fonte'] = None, None
        if self.consumos:
            eu['consumo_volta'], eu['consumo_fonte'] = round(media(list(self.consumos)), 2), 'esta sessão'
        elif guardado.get('consumo'):
            eu['consumo_volta'], eu['consumo_fonte'] = round(guardado['consumo'], 2), origem
        taxa, eu['desgaste_fonte'] = None, None
        if self.desgaste_volta:
            taxa = [round(media([d[k] for d in self.desgaste_volta]), 2) for k in range(4)]
            eu['desgaste_fonte'] = 'esta sessão'
        elif est and guardado.get('desgaste', {}).get(eu.get('composto')):
            taxa = [round(x, 2) for x in guardado['desgaste'][eu['composto']]]
            eu['desgaste_fonte'] = origem
        if taxa:
            eu['desgaste_volta'] = taxa
            if dan:
                restos = [(70 - dan['desgaste'][k]) / taxa[k] for k in range(4) if taxa[k] > 0.05]
                if restos:
                    pior = min(range(4), key=lambda k: (70 - dan['desgaste'][k]) / taxa[k] if taxa[k] > 0.05 else 1e9)
                    eu['vida_restante_voltas'] = max(0, int(min(restos)))
                    eu['pneu_limite'] = pior
                    eu['vida_total_voltas'] = int(max(0, min(restos)) + (est['idade_pneus'] if est else 0))
                    eu['vida_fonte'] = 'pelo desgaste medido'
        # o jogo diz quantas voltas restam ao conjunto montado: é a fonte preferida
        montado = self._conjunto_atual()
        if montado:
            eu['vida_restante_voltas'] = montado['vida']
            eu['vida_total_voltas'] = montado['vida_util']
            eu['vida_fonte'] = 'do jogo'
        eu['speed_trap'] = round(v['speed_trap'] or 0)
        return eu

    def _ajuda(self, i):
        """DRS (regras 2025) ou Overtake (regras 2026), como o jogo os indica para o carro i."""
        t2 = self.telem2[i] if self.telem2 and i < len(self.telem2) else None
        if t2 and t2['regras_2026']:
            return {'nome': 'Overtake', 'disp': bool(t2['ovtk_disp']), 'ativo': bool(t2['ovtk_ativo']), 'dist': None}
        est = self.estado[i] if self.estado and i < len(self.estado) else None
        if est:
            return {'nome': 'DRS', 'disp': bool(est['drs_permitido']), 'ativo': False, 'dist': est.get('drs_dist') or None}
        return None

    # ------------------------------------------------------------ pneus (dados do jogo por conjunto)
    def _conjunto_atual(self):
        conj, k = self.conjuntos, self.conjunto_montado
        if conj and k is not None and k < len(conj) and conj[k]['vida_util']:
            return self._conjunto(conj[k])
        return None

    def _conjunto(self, c):
        return {'composto': COMPOSTOS.get(c['visual'], '?'), 'desgaste': c['desgaste'], 'vida': c['vida'],
                'vida_util': c['vida_util'], 'delta': c['delta'] if self.conjunto_montado is not None else 0}

    def _conjuntos_livres(self, molhado=False):
        """Conjuntos que ainda podes montar (sem o que já tens montado), só de seco ou só de chuva."""
        res = []
        for k, c in enumerate(self.conjuntos or []):
            comp = COMPOSTOS.get(c['visual'], '?')
            if not c['disponivel'] or k == self.conjunto_montado or c['vida'] <= 0:
                continue
            if (comp in ('I', 'W')) == molhado and comp != '?':
                res.append(self._conjunto(c))
        return res

    def _perda_box(self):
        """Tempo perdido numa paragem, medido nas paragens desta corrida (volta de entrada + volta de saída
        contra o ritmo normal de cada piloto). Sem paragens ainda, usa a da última corrida neste circuito."""
        perdas = []
        if self.sessao and 15 <= self.sessao['tipo'] <= 17:
            for h in self.historico.values():
                voltas = h['voltas']
                limpos = sorted(v['tempo'] for k, v in enumerate(voltas, start=1) if v['tempo'] and v['valida'] and k > 1)
                if len(limpos) < 3:
                    continue
                ref = limpos[len(limpos) // 2]
                for st in h['stints'][:-1]:
                    e = st['fim']
                    if not e or e == 255 or e >= len(voltas):
                        continue
                    entrada, saida = voltas[e - 1]['tempo'], voltas[e]['tempo']
                    if entrada and saida and 8000 < entrada + saida - 2 * ref < 45000:
                        perdas.append(entrada + saida - 2 * ref)
        if perdas:
            perda = sorted(perdas)[len(perdas) // 2]
            p = self.memoria.setdefault('pistas', {}).setdefault(str(self.sessao['pista']), {})
            if abs(p.get('perda_box', 0) - perda) >= 500:
                p['perda_box'] = int(perda)
                self._persistir()
            return int(perda), f'medida em {len(perdas)} paragens desta corrida'
        guardada = self._medicoes_pista().get('perda_box')
        if guardada:
            return guardada, 'medida na última corrida aqui'
        return 22000, 'estimada até haver uma paragem'

    def _plano(self, voltas_restantes, volta_atual, atual, usados, janela=None):
        molhado = (self.sessao.get('tempo_meteo') or 0) >= 3 or (atual and atual['composto'] in ('I', 'W'))
        livres = self._conjuntos_livres(molhado)
        if not livres and not atual:
            return None
        perda, fonte = self._perda_box()
        planos = planear(voltas_restantes, livres, atual, perda, () if molhado else usados, volta_atual, janela)
        if not planos:
            return None
        melhor = dict(planos[0], perda_box_s=round(perda / 1000, 1), perda_box_fonte=fonte, molhado=bool(molhado))
        if len(planos) > 1:
            alt = planos[1]
            melhor['alternativa'] = {'paragens': alt['paragens'], 'stints': alt['stints'],
                                     'mais_lento_s': round((alt['tempo_ms'] - planos[0]['tempo_ms']) / 1000, 1)}
        return melhor

    def _compostos_usados(self, j):
        h = self.historico.get(j)
        return {COMPOSTOS.get(st['visual'], '?') for st in (h['stints'] if h else [])} & set(SECOS)

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
        return self._juntar_setores_do_jogo(best, range(len(self.voltas or [])))

    def _meus_melhores_setores(self, i):
        best = [None, None, None]
        for v in self._voltas_hist(i):
            if not v['valida']:
                continue
            for k, t in enumerate((v['s1'], v['s2'], v['s3'])):
                if t and (best[k] is None or t < best[k]):
                    best[k] = t
        return self._juntar_setores_do_jogo(best, [i])

    def _juntar_setores_do_jogo(self, best, carros):
        """F1 2020: o jogo dá o melhor de cada setor de cada carro nos dados das voltas (mesmo das voltas que o
        painel não viu); junta-os aos do histórico."""
        for i in carros:
            if self.voltas and i < len(self.voltas):
                for k, t in enumerate(self.voltas[i].get('melhores_setores_carro') or []):
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
            gap_ms = eu['frente_ms'] if frente else c['frente_ms']
            gap = None if gap_ms is None else gap_ms / 1000      # None: ainda sem dados (F1 2020, logo ao abrir)
            r = self._ritmo(c['idx'])
            dif = None
            if r and meu_ritmo:
                dif = (r - meu_ritmo) / 1000 if frente else (meu_ritmo - r) / 1000
            ajuda = self._ajuda(c['idx'])
            return {'codigo': c['codigo'], 'pos': c['pos'], 'composto': c['composto'], 'idade': c['idade'],
                    'gap_s': round(gap, 3) if gap is not None else None, 'ritmo_ms': r, 'diferenca_volta': round(dif, 2) if dif is not None else None,
                    'voltas_atras': c['voltas_atras'], 'ajuda_disp': bool(ajuda and ajuda['disp'])}

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
        # plano de corrida com os conjuntos de pneus que o jogo diz que tens
        s = self.sessao
        v = self.voltas[j]
        total = s['voltas_total'] or 0
        atual = self._conjunto_atual()
        if total and atual and v['resultado'] == 2:
            janela = (s['box_ideal'], s['box_ultima'] or s['box_ideal']) if s['box_ideal'] else None
            usados = self._compostos_usados(j) | {atual['composto']}
            res['plano'] = self._plano(total - v['volta'] + 1, v['volta'], atual, usados, janela)
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
        h_saidas, h_entradas = self._tempos_box_historico()
        saida = media(list(self.tempos_saida)) or media(h_saidas)
        entrada = media(list(self.tempos_entrada)) or media(h_entradas)
        res['tempos_box_fonte'] = 'do jogo' if saida else 'estimados até fazeres uma volta de saída'
        saida = saida or 120000
        entrada = entrada or 125000
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
        tarefas = {'reco': t_reco, 'comp': t_comp, 'desg': t_desg, 'quali': t_quali, 'corr8': t_corr8,
                   'corr5': t_corr5, 'cons': t_cons}
        return [tarefas[k] for k in self._tarefas_do_treino(tipo)]

    TAREFAS = {'reco': 'Reconhecimento da pista', 'comp': 'Testar os 3 compostos', 'desg': 'Medir o desgaste dos pneus',
               'quali': 'Simulação de qualificação', 'corr8': 'Simulação de corrida (8 voltas)',
               'corr5': 'Confirmar ritmo de corrida (5 voltas)', 'cons': 'Medir o consumo de combustível'}

    def _tarefas_do_treino(self, tipo):
        """Programa de cada treino, pelo tipo e pela estrutura do fim de semana que o jogo envia."""
        treinos = [t for t in self.sessao.get('fim_de_semana') or [] if 1 <= t <= 4]
        if tipo in treinos and len(treinos) <= 2:
            # fim de semana com só 1 ou 2 treinos (por exemplo com sprint): o programa encolhe
            if len(treinos) == 1:
                return ['reco', 'quali', 'corr8', 'cons']
            return ['reco', 'comp', 'desg'] if treinos.index(tipo) == 0 else ['quali', 'corr8', 'cons']
        return {1: ['reco', 'comp', 'desg'], 2: ['quali', 'corr8', 'cons'], 3: ['quali', 'corr5', 'desg']}.get(
            tipo, ['reco', 'quali', 'corr8', 'cons'])

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
        voltas_corrida, _ = self.voltas_corrida()
        if voltas_corrida and self.conjuntos:
            # todos os conjuntos que ainda tens, incluindo o montado, porque a corrida começa do zero
            montado = self._conjunto_atual()
            res['plano_corrida'] = self._plano(voltas_corrida, 1, None, set()) if not montado else \
                self._plano_sem_montado(voltas_corrida, montado)
        return res

    def _plano_sem_montado(self, voltas, montado):
        livres = self._conjuntos_livres() + [montado]
        perda, fonte = self._perda_box()
        planos = planear(voltas, livres, None, perda)
        if not planos:
            return None
        return dict(planos[0], perda_box_s=round(perda / 1000, 1), perda_box_fonte=fonte)

    def _tempos_box_historico(self):
        """Voltas de saída (a primeira de cada stint) e de entrada (a última de um stint fechado), do histórico do jogo."""
        h = self.historico.get(self.jogador)
        if not h:
            return [], []
        voltas, saidas, entradas, inicio = h['voltas'], [], [], 1
        for st in h['stints']:
            fim = st['fim'] if st['fim'] != 255 else len(voltas)
            if inicio <= len(voltas) and voltas[inicio - 1]['tempo'] and inicio < fim:
                saidas.append(voltas[inicio - 1]['tempo'])
            if st['fim'] != 255 and 0 < fim <= len(voltas) and voltas[fim - 1]['tempo']:
                entradas.append(voltas[fim - 1]['tempo'])
            inicio = fim + 1
        return saidas[-5:], entradas[-5:]


def _tarefa(nome, feito_qtd, alvo, unidade, extra=''):
    feito = feito_qtd >= alvo
    if feito:
        det = 'Feito' + (f' · {extra}' if extra else '')
    else:
        det = f'{feito_qtd} de {alvo} {unidade}' + (f' · {extra}' if extra else '')
    return {'nome': nome, 'detalhe': det, 'progresso': min(feito_qtd / alvo, 1) if alvo else 1, 'feito': feito}


def fmt_tempo_total(seg):
    seg = float(seg)
    h, resto = divmod(seg, 3600)
    m, sg = divmod(resto, 60)
    return (f'{int(h)}:{int(m):02d}:{sg:06.3f}' if h else f'{int(m)}:{sg:06.3f}')


def fmt_volta(ms):
    ms = int(ms)
    return f'{ms // 60000}:{(ms % 60000) / 1000:06.3f}'
