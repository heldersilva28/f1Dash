"""Leitura dos pacotes UDP do EA SPORTS F1 25 (formatos 2025 e 2026 / 2026 Season Pack).

Cada pacote começa com um cabeçalho de 29 bytes. O tamanho de cada pacote é verificado
contra os tamanhos oficiais da especificação (ver TAMANHOS_OFICIAIS) no arranque.
"""
import struct

CABECALHO = struct.Struct('<HBBBBBQfIIBB')  # 29 bytes

# ---------------------------------------------------------------- estruturas por carro
LAP = struct.Struct('<IIHBHBHBHBfff' + 'B' * 15 + 'HHBfB')          # 57
TELEMETRIA = {
    2025: struct.Struct('<HfffBbHBBH4H4B4BH4f4B'),                  # 60 (temp. motor uint16)
    2026: struct.Struct('<HfffBbHBBH4H4B4BB4f4B'),                  # 59 (temp. motor uint8)
}
TELEMETRIA2 = struct.Struct('<BBHBBHBB')                            # 10 (só 2026)
ESTADO = {
    2025: struct.Struct('<BBBBBfffHHBBHBBBbfffBfffB'),              # 55
    2026: struct.Struct('<BBBBBfffHHBBHBBBbfffBffffB'),             # 59 (+ limite de recuperação ERS)
}
DANOS = struct.Struct('<4f4B4B4B18B')                               # 46
PARTICIPANTE = {
    2025: struct.Struct('<BBBBBBB32sBBHBB12B'),                     # 57
    2026: struct.Struct('<BHHHBBB32sBBHBB12B'),                     # 60 (ids de 16 bits)
}
HIST_VOLTA = struct.Struct('<IHBHBHBB')                             # 14
HIST_STINT = struct.Struct('<BBB')                                  # 3
CONJ_PNEUS = struct.Struct('<BBBBBBBhB')                            # 10

SESSAO_A = struct.Struct('<BbbBHBbBHHBBBBBB')                       # 19
ZONA_COMISSARIOS = struct.Struct('<fb')                             # 5
SESSAO_B = struct.Struct('<BBB')
PREVISAO = struct.Struct('<BBBbbbbB')                               # 8
SESSAO_C = struct.Struct('<BBIII' + 'B' * 14 + 'I' + 'B' * 33 + '12Bff')  # 85
SESSAO_2026 = struct.Struct('<BB64sB64sB32sfBBBBB')                 # zonas de aero ativa / DRS + assistências
CLASSIFICACAO = struct.Struct('<7BIdBBB8B8B8B')                     # 46 (classificação final, por carro)

TAMANHOS_OFICIAIS = {
    2025: {1: 753, 2: 1285, 3: 45, 4: 1284, 6: 1352, 7: 1239, 8: 1042, 10: 1041, 11: 1460, 12: 231},
    2026: {1: 926, 2: 1399, 3: 45, 4: 1470, 6: 1448, 7: 1445, 10: 1133, 11: 1460, 12: 231, 16: 269},
}
MAX_CARROS = {2025: 22, 2026: 24}


def tamanho_esperado(fmt, pid):
    n = MAX_CARROS[fmt]
    h = CABECALHO.size
    if pid == 1:
        t = h + SESSAO_A.size + 21 * ZONA_COMISSARIOS.size + SESSAO_B.size + 64 * PREVISAO.size + SESSAO_C.size
        return t + (SESSAO_2026.size if fmt == 2026 else 0)
    if pid == 2:
        return h + n * LAP.size + 2
    if pid == 3:
        return 45
    if pid == 4:
        return h + 1 + n * PARTICIPANTE[fmt].size
    if pid == 6:
        return h + n * TELEMETRIA[fmt].size + 3
    if pid == 7:
        return h + n * ESTADO[fmt].size
    if pid == 8:
        # no formato 2026 o tamanho não está confirmado: se o jogo mandar outro, o pacote é ignorado
        return h + 1 + n * CLASSIFICACAO.size
    if pid == 10:
        return h + n * DANOS.size
    if pid == 11:
        return h + 7 + 100 * HIST_VOLTA.size + 8 * HIST_STINT.size
    if pid == 12:
        return h + 1 + 20 * CONJ_PNEUS.size + 1
    if pid == 15:
        # posição de cada carro no início de cada volta (até 50 voltas por pacote); no formato 2026 não confirmado
        return h + 2 + 50 * n
    if pid == 16:
        return h + n * TELEMETRIA2.size
    return None


def verificar_tamanhos():
    """Confirma que as estruturas batem certo com os tamanhos oficiais da EA."""
    erros = []
    for fmt, tabela in TAMANHOS_OFICIAIS.items():
        for pid, oficial in tabela.items():
            t = tamanho_esperado(fmt, pid)
            if t != oficial:
                erros.append(f'formato {fmt} pacote {pid}: {t} != {oficial}')
    return erros


def _ms(ms_part, min_part):
    return min_part * 60000 + ms_part


def _nome(b):
    return b.split(b'\x00', 1)[0].decode('utf-8', 'replace')


# ---------------------------------------------------------------- descodificadores
def ler_cabecalho(dados):
    (fmt, ano, vmaj, vmin, vpac, pid, uid, t_sessao, frame, frame_total,
     jogador, jogador2) = CABECALHO.unpack_from(dados, 0)
    return {'formato': fmt, 'id': pid, 'uid': uid, 'tempo': t_sessao, 'frame': frame,
            'jogador': jogador}


def ler_sessao(dados, fmt):
    o = CABECALHO.size
    a = SESSAO_A.unpack_from(dados, o); o += SESSAO_A.size
    s = {
        'tempo_meteo': a[0], 'temp_pista': a[1], 'temp_ar': a[2], 'voltas_total': a[3],
        'comprimento': a[4], 'tipo': a[5], 'pista': a[6], 'formula': a[7],
        'tempo_restante': a[8], 'duracao': a[9], 'pausa': a[11],
        'espectador': a[12], 'carro_espectador': a[13],
    }
    nz = a[15]
    zonas = []
    for i in range(21):
        inicio, bandeira = ZONA_COMISSARIOS.unpack_from(dados, o); o += ZONA_COMISSARIOS.size
        if i < nz:
            zonas.append({'inicio': inicio, 'bandeira': bandeira})
    s['zonas'] = zonas
    b = SESSAO_B.unpack_from(dados, o); o += SESSAO_B.size
    s['safety_car'] = b[0]
    s['online'] = b[1]
    nprev = b[2]
    prev = []
    for i in range(64):
        p = PREVISAO.unpack_from(dados, o); o += PREVISAO.size
        if i < nprev:
            prev.append({'tipo': p[0], 'minutos': p[1], 'tempo_meteo': p[2], 'temp_pista': p[3],
                         'temp_ar': p[5], 'chuva': p[7]})
    s['previsao'] = prev
    c = SESSAO_C.unpack_from(dados, o); o += SESSAO_C.size
    s['fim_de_semana_id'] = c[3]
    s['box_ideal'] = c[5]
    s['box_ultima'] = c[6]
    s['box_reentrada'] = c[7]
    s['duracao_sessao'] = c[20]          # 0 nenhuma, 2 muito curta, 3 curta, 4 média, 5 média-longa, 6 longa, 7 completa
    n_sessoes = c[52]
    s['fim_de_semana'] = [t for t in c[53:53 + min(n_sessoes, 12)] if t]   # tipos de sessão, por ordem
    s['setor2_inicio'] = c[-2]
    s['setor3_inicio'] = c[-1]
    s['aero_zonas'] = []
    if fmt == 2026:
        d = SESSAO_2026.unpack_from(dados, o)
        n_full = d[1]
        full = d[2]
        s['aero_zonas'] = [struct.unpack_from('<ff', full, 8 * i) for i in range(min(n_full, 8))]
    return s


def ler_voltas(dados, fmt):
    o = CABECALHO.size
    carros = []
    for _ in range(MAX_CARROS[fmt]):
        v = LAP.unpack_from(dados, o); o += LAP.size
        carros.append({
            'ultima': v[0], 'atual': v[1],
            's1': _ms(v[2], v[3]), 's2': _ms(v[4], v[5]),
            'para_frente': _ms(v[6], v[7]), 'para_lider': _ms(v[8], v[9]),
            'dist_volta': v[10], 'dist_total': v[11],
            'posicao': v[13], 'volta': v[14], 'box_estado': v[15], 'paragens': v[16],
            'delta_sc': v[12],
            'setor': v[17], 'invalida': v[18], 'penalizacoes': v[19], 'avisos': v[20], 'avisos_limites': v[21],
            'drive_through': v[22], 'stop_go': v[23],
            'grelha': v[24], 'estado_piloto': v[25], 'resultado': v[26],
            'box_tempo_via': v[28], 'cumpre_penalizacao': v[30], 'speed_trap': v[31],
        })
    return carros


def ler_evento(dados):
    o = CABECALHO.size
    codigo = dados[o:o + 4].decode('ascii', 'replace')
    p = dados[o + 4:]
    ev = {'codigo': codigo}
    if codigo == 'FTLP':
        ev['carro'], ev['tempo'] = struct.unpack_from('<Bf', p)
    elif codigo == 'RTMT':
        ev['carro'], ev['motivo'] = struct.unpack_from('<BB', p)
    elif codigo == 'PENA':
        (ev['tipo'], ev['infracao'], ev['carro'], ev['outro'], ev['tempo'],
         ev['volta'], ev['lugares']) = struct.unpack_from('<7B', p)
    elif codigo == 'SCAR':
        ev['tipo'], ev['evento'] = struct.unpack_from('<BB', p)
    elif codigo == 'RCWN':
        ev['carro'] = p[0]
    elif codigo in ('DTSV', 'SGSV'):
        ev['carro'] = p[0]
    return ev   # SEND (fim da sessão), RDFL (bandeira vermelha), LGOT (luzes apagadas) não trazem dados


def ler_posicoes_voltas(dados, fmt):
    o = CABECALHO.size
    n_voltas, inicio = dados[o], dados[o + 1]
    o += 2
    n = MAX_CARROS[fmt]
    return {'inicio': inicio, 'voltas': [list(dados[o + k * n:o + (k + 1) * n]) for k in range(min(n_voltas, 50))]}


def ler_classificacao(dados, fmt):
    o = CABECALHO.size
    o += 1   # número de carros classificados (os lugares vazios vêm com a posição a 0)
    carros = []
    for _ in range(MAX_CARROS[fmt]):
        v = CLASSIFICACAO.unpack_from(dados, o); o += CLASSIFICACAO.size
        ns = v[11]
        carros.append({'posicao': v[0], 'voltas': v[1], 'grelha': v[2], 'pontos': v[3], 'paragens': v[4],
                       'resultado': v[5], 'motivo': v[6], 'melhor_ms': v[7], 'tempo_total': v[8],
                       'penalizacoes_s': v[9], 'n_penalizacoes': v[10],
                       'stints': [{'visual': v[20 + k], 'fim': v[28 + k]} for k in range(min(ns, 8))]})
    return carros   # a lista é indexada pelo número do carro: n diz quantos estão classificados, não onde


def ler_participantes(dados, fmt):
    o = CABECALHO.size
    ativos = dados[o]; o += 1
    est = PARTICIPANTE[fmt]
    lista = []
    for _ in range(MAX_CARROS[fmt]):
        v = est.unpack_from(dados, o); o += est.size
        ncores = v[12]
        cores = [tuple(v[13 + 3 * i:16 + 3 * i]) for i in range(4)]
        lista.append({
            'ia': v[0], 'piloto_id': v[1], 'equipa_id': v[3], 'minha_equipa': v[4],
            'numero': v[5], 'nome': _nome(v[7]), 'telemetria_publica': v[8],
            'cores': cores[:ncores] if ncores else [],
        })
    return ativos, lista


def ler_telemetria(dados, fmt):
    o = CABECALHO.size
    est = TELEMETRIA[fmt]
    carros = []
    for _ in range(MAX_CARROS[fmt]):
        v = est.unpack_from(dados, o); o += est.size
        carros.append({
            'velocidade': v[0], 'acelerador': v[1], 'travao': v[3], 'mudanca': v[5], 'rpm': v[6],
            'drs': v[7], 'luzes_rpm': v[8],
            'travoes_temp': list(v[10:14]), 'pneus_sup': list(v[14:18]), 'pneus_int': list(v[18:22]),
            'motor_temp': v[22], 'pressao': [round(x, 1) for x in v[23:27]],
        })
    return carros


def ler_telemetria2(dados, fmt):
    o = CABECALHO.size
    carros = []
    for _ in range(MAX_CARROS[fmt]):
        v = TELEMETRIA2.unpack_from(dados, o); o += TELEMETRIA2.size
        carros.append({'aero_modo': v[0], 'aero_disp': v[1], 'aero_dist': v[2],
                       'ovtk_disp': v[3], 'ovtk_ativo': v[4], 'ovtk_dist': v[5], 'regras_2026': v[6]})
    return carros


def ler_estado(dados, fmt):
    o = CABECALHO.size
    est = ESTADO[fmt]
    carros = []
    for _ in range(MAX_CARROS[fmt]):
        v = est.unpack_from(dados, o); o += est.size
        c = {
            'travao_bias': v[3], 'rpm_max': v[8],
            'combustivel': v[5], 'capacidade': v[6], 'combustivel_voltas': v[7],
            'drs_permitido': v[11], 'drs_dist': v[12], 'composto_real': v[13], 'composto': v[14], 'idade_pneus': v[15],
            'bandeira': v[16], 'ers': v[19], 'ers_modo': v[20],
            'ers_mguk': v[21], 'ers_mguh': v[22],
        }
        if fmt == 2026:
            c['ers_limite'] = v[23]; c['ers_usado'] = v[24]
        else:
            c['ers_limite'] = 0.0; c['ers_usado'] = v[23]
        carros.append(c)
    return carros


def ler_danos(dados, fmt):
    o = CABECALHO.size
    carros = []
    for _ in range(MAX_CARROS[fmt]):
        v = DANOS.unpack_from(dados, o); o += DANOS.size
        d = v[16:]
        carros.append({
            'desgaste': [round(x, 1) for x in v[0:4]], 'pneus_dano': list(v[4:8]),
            'travoes_dano': list(v[8:12]), 'bolhas': list(v[12:16]),
            'asa_fe': d[0], 'asa_fd': d[1], 'asa_tras': d[2], 'fundo': d[3], 'difusor': d[4],
            'pontoes': d[5], 'falha_drs': d[6], 'falha_ers': d[7], 'caixa': d[8], 'motor': d[9],
            'mguh': d[10], 'es': d[11], 'ce': d[12], 'ice': d[13], 'mguk': d[14], 'tc': d[15],
            'motor_partido': d[16], 'motor_gripado': d[17],
        })
    return carros


def ler_historico(dados):
    o = CABECALHO.size
    carro, nvoltas, nstints, melhor_v, m1, m2, m3 = struct.unpack_from('<7B', dados, o); o += 7
    voltas = []
    for i in range(100):
        v = HIST_VOLTA.unpack_from(dados, o); o += HIST_VOLTA.size
        if i < nvoltas:
            voltas.append({'tempo': v[0], 's1': _ms(v[1], v[2]), 's2': _ms(v[3], v[4]),
                           's3': _ms(v[5], v[6]), 'valida': bool(v[7] & 1)})
    stints = []
    for i in range(8):
        v = HIST_STINT.unpack_from(dados, o); o += HIST_STINT.size
        if i < nstints:
            stints.append({'fim': v[0], 'real': v[1], 'visual': v[2]})
    return {'carro': carro, 'voltas': voltas, 'stints': stints,
            'melhor_volta': melhor_v, 'melhor_s': (m1, m2, m3)}


def ler_conjuntos(dados):
    o = CABECALHO.size
    carro = dados[o]; o += 1
    conj = []
    for _ in range(20):
        v = CONJ_PNEUS.unpack_from(dados, o); o += CONJ_PNEUS.size
        conj.append({'real': v[0], 'visual': v[1], 'desgaste': v[2], 'disponivel': v[3],
                     'sessao_recomendada': v[4], 'vida': v[5], 'vida_util': v[6],
                     'delta': v[7], 'montado': v[8]})
    return carro, conj, dados[o]


LEITORES = {1: 'sessao', 2: 'voltas', 3: 'evento', 4: 'participantes', 6: 'telemetria',
            7: 'estado', 8: 'classificacao', 10: 'danos', 11: 'historico', 12: 'conjuntos',
            15: 'posicoes_voltas', 16: 'telemetria2'}


def descodificar(dados):
    """Devolve (cabeçalho, nome_do_pacote, conteúdo) ou None se o pacote não interessa/for inválido."""
    if len(dados) < CABECALHO.size:
        return None
    cab = ler_cabecalho(dados)
    fmt, pid = cab['formato'], cab['id']
    if fmt not in MAX_CARROS or pid not in LEITORES:
        return None
    esperado = tamanho_esperado(fmt, pid)
    if esperado and len(dados) != esperado:
        return None
    nome = LEITORES[pid]
    if nome == 'sessao':
        c = ler_sessao(dados, fmt)
    elif nome == 'voltas':
        c = ler_voltas(dados, fmt)
    elif nome == 'evento':
        c = ler_evento(dados)
    elif nome == 'participantes':
        c = ler_participantes(dados, fmt)
    elif nome == 'telemetria':
        c = ler_telemetria(dados, fmt)
    elif nome == 'telemetria2':
        c = ler_telemetria2(dados, fmt)
    elif nome == 'estado':
        c = ler_estado(dados, fmt)
    elif nome == 'danos':
        c = ler_danos(dados, fmt)
    elif nome == 'historico':
        c = ler_historico(dados)
    elif nome == 'classificacao':
        c = ler_classificacao(dados, fmt)
    elif nome == 'posicoes_voltas':
        c = ler_posicoes_voltas(dados, fmt)
    else:
        c = ler_conjuntos(dados)
    return cab, nome, c
