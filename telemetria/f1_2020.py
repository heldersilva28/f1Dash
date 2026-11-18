"""Leitura dos pacotes UDP do F1 2020 (formato 2020).

O formato 2020 é bastante diferente do atual: cabeçalho de 24 bytes, tempos de volta em segundos, outros códigos
de sessão e de resultado, e não há pacotes de danos, histórico de voltas nem conjuntos de pneus (o desgaste e o
dano vêm no pacote de estado do carro). Aqui cada pacote é convertido para a mesma forma que o painel usa com os
formatos 2025 e 2026, para o resto do código não precisar de saber de que jogo vêm os dados.
"""
import struct

FORMATO = 2020
N = 22

CABECALHO = struct.Struct('<HBBBBQfIBB')                                    # 24
SESSAO_A = struct.Struct('<BbbBHBbBHHBBBBBB')                               # 19 (igual ao atual)
ZONA = struct.Struct('<fb')                                                 # 5
SESSAO_B = struct.Struct('<BBB')                                            # 3
PREVISAO = struct.Struct('<BBBbb')                                          # 5 (sem probabilidade de chuva)
VOLTA = struct.Struct('<ffHHfBHHHHBHBHBfffBBBBBBBBB')                       # 53
PARTICIPANTE = struct.Struct('<BBBBB48sB')                                  # 54
TELEMETRIA = struct.Struct('<HfffBbHBB4H4B4BH4f4B')                         # 58
ESTADO = struct.Struct('<BBBBBfffHHBBH4BBBB4BBBBBBBbfBfff')                 # 60 (inclui desgaste e danos)
CLASSIFICACAO = struct.Struct('<BBBBBBfdBBB8B8B')                           # 37

TAMANHOS_OFICIAIS = {1: 251, 2: 1190, 3: 35, 4: 1213, 6: 1307, 7: 1344, 8: 839}

# o F1 2020 numera as sessões e os resultados de outra forma: converte para a numeração atual
SESSOES = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 15, 11: 16, 12: 18}
RESULTADOS = {0: 0, 1: 1, 2: 2, 3: 3, 4: 5, 5: 6, 6: 7}     # 2020: 4 desclassificado, 5 não classificado, 6 desistiu


def tamanho_esperado(pid):
    h = CABECALHO.size
    return {
        1: h + SESSAO_A.size + 21 * ZONA.size + SESSAO_B.size + 20 * PREVISAO.size,
        2: h + N * VOLTA.size,
        3: h + 4 + 7,
        4: h + 1 + N * PARTICIPANTE.size,
        6: h + N * TELEMETRIA.size + 7,
        7: h + N * ESTADO.size,
        8: h + 1 + N * CLASSIFICACAO.size,
    }.get(pid)


def verificar_tamanhos():
    return [f'formato 2020 pacote {pid}: {tamanho_esperado(pid)} != {oficial}'
            for pid, oficial in TAMANHOS_OFICIAIS.items() if tamanho_esperado(pid) != oficial]


def _ms(segundos):
    return int(round(segundos * 1000)) if segundos and segundos > 0 else 0


def ler_cabecalho(dados):
    fmt, vmaj, vmin, vpac, pid, uid, t, frame, jogador, jogador2 = CABECALHO.unpack_from(dados, 0)
    return {'formato': fmt, 'id': pid, 'uid': uid, 'tempo': t, 'frame': frame, 'jogador': jogador}


def ler_sessao(dados):
    o = CABECALHO.size
    a = SESSAO_A.unpack_from(dados, o); o += SESSAO_A.size
    tipo = SESSOES.get(a[5], 0)
    s = {
        'tempo_meteo': a[0], 'temp_pista': a[1], 'temp_ar': a[2], 'voltas_total': a[3],
        'comprimento': a[4], 'tipo': tipo, 'pista': a[6], 'formula': a[7],
        'tempo_restante': a[8], 'duracao': a[9], 'pausa': a[11],
        'espectador': a[12], 'carro_espectador': a[13],
    }
    zonas = []
    for i in range(21):
        inicio, bandeira = ZONA.unpack_from(dados, o); o += ZONA.size
        if i < a[15]:
            zonas.append({'inicio': inicio, 'bandeira': bandeira})
    s['zonas'] = zonas
    b = SESSAO_B.unpack_from(dados, o); o += SESSAO_B.size
    s['safety_car'], s['online'] = b[0], b[1]
    prev = []
    for i in range(20):
        p = PREVISAO.unpack_from(dados, o); o += PREVISAO.size
        if i < b[2]:
            # o F1 2020 não dá a probabilidade de chuva, só o tempo previsto
            prev.append({'tipo': SESSOES.get(p[0], 0), 'minutos': p[1], 'tempo_meteo': p[2], 'temp_pista': p[3],
                         'temp_ar': p[4], 'chuva': None})
    s['previsao'] = prev
    # o que o F1 2020 não envia: janela de box, estrutura do fim de semana, limites dos setores
    s.update({'fim_de_semana_id': 0, 'box_ideal': 0, 'box_ultima': 0, 'box_reentrada': 0, 'duracao_sessao': 0,
              'fim_de_semana': [], 'setor2_inicio': 0, 'setor3_inicio': 0, 'aero_zonas': []})
    return s


def ler_voltas(dados):
    o = CABECALHO.size
    carros = []
    for _ in range(N):
        v = VOLTA.unpack_from(dados, o); o += VOLTA.size
        carros.append({
            'ultima': _ms(v[0]), 'atual': _ms(v[1]), 's1': v[2], 's2': v[3], 'melhor_ms': _ms(v[4]),
            'melhor_setores': [v[6], v[7], v[8]],             # setores da melhor volta deste carro
            'melhores_setores_carro': [v[9], v[11], v[13]],   # o melhor de cada setor deste carro na sessão
            'para_frente': None, 'para_lider': None,          # o F1 2020 não envia: o painel calcula
            'dist_volta': v[15], 'dist_total': v[16], 'delta_sc': v[17],
            'posicao': v[18], 'volta': v[19], 'box_estado': v[20], 'paragens': None,   # paragens: o painel conta
            'setor': v[21], 'invalida': v[22], 'penalizacoes': v[23], 'avisos': 0, 'avisos_limites': 0,
            'drive_through': 0, 'stop_go': 0, 'grelha': v[24], 'estado_piloto': v[25],
            'resultado': RESULTADOS.get(v[26], v[26]), 'box_tempo_via': 0, 'cumpre_penalizacao': 0,
            'speed_trap': None,                                # vem nos eventos SPTP
        })
    return carros


def ler_evento(dados):
    o = CABECALHO.size
    codigo = dados[o:o + 4].decode('ascii', 'replace')
    p = dados[o + 4:]
    ev = {'codigo': codigo}
    if codigo in ('FTLP', 'SPTP'):
        ev['carro'], valor = struct.unpack_from('<Bf', p)
        ev['tempo' if codigo == 'FTLP' else 'velocidade'] = valor
    elif codigo in ('RTMT', 'TMPT', 'RCWN'):
        ev['carro'], ev['motivo'] = p[0], 0
    elif codigo == 'PENA':
        (ev['tipo'], ev['infracao'], ev['carro'], ev['outro'], ev['tempo'],
         ev['volta'], ev['lugares']) = struct.unpack_from('<7B', p)
    return ev


def ler_participantes(dados):
    o = CABECALHO.size
    ativos = dados[o]; o += 1
    lista = []
    for _ in range(N):
        v = PARTICIPANTE.unpack_from(dados, o); o += PARTICIPANTE.size
        lista.append({'ia': v[0], 'piloto_id': v[1], 'equipa_id': v[2], 'minha_equipa': 0, 'numero': v[3],
                      'nome': v[5].split(b'\x00', 1)[0].decode('utf-8', 'replace'), 'telemetria_publica': v[6],
                      'cores': []})                                     # sem cores da pintura: usa as da equipa
    return ativos, lista


def ler_telemetria(dados):
    o = CABECALHO.size
    carros = []
    for _ in range(N):
        v = TELEMETRIA.unpack_from(dados, o); o += TELEMETRIA.size
        carros.append({
            'velocidade': v[0], 'acelerador': v[1], 'travao': v[3], 'mudanca': v[5], 'rpm': v[6],
            'drs': v[7], 'luzes_rpm': v[8],
            'travoes_temp': list(v[9:13]), 'pneus_sup': list(v[13:17]), 'pneus_int': list(v[17:21]),
            'motor_temp': v[21], 'pressao': [round(x, 1) for x in v[22:26]],
        })
    return carros


def ler_estado_e_danos(dados):
    """No F1 2020 o estado do carro também traz o desgaste dos pneus e os danos."""
    o = CABECALHO.size
    estado, danos = [], []
    for _ in range(N):
        v = ESTADO.unpack_from(dados, o); o += ESTADO.size
        estado.append({
            'travao_bias': v[3], 'rpm_max': v[8],
            'combustivel': v[5], 'capacidade': v[6], 'combustivel_voltas': v[7],
            'drs_permitido': v[11], 'drs_dist': v[12], 'composto_real': v[17], 'composto': v[18],
            'idade_pneus': v[19], 'bandeira': v[30], 'ers': v[31], 'ers_modo': v[32],
            'ers_mguk': v[33], 'ers_mguh': v[34], 'ers_usado': v[35], 'ers_limite': 0.0,
        })
        danos.append({
            'desgaste': [float(x) for x in v[13:17]], 'pneus_dano': list(v[20:24]),
            'travoes_dano': [0] * 4, 'bolhas': [0] * 4,
            'asa_fe': v[24], 'asa_fd': v[25], 'asa_tras': v[26], 'fundo': 0, 'difusor': 0, 'pontoes': 0,
            'falha_drs': v[27], 'falha_ers': 0, 'caixa': v[29], 'motor': v[28],
            'mguh': 0, 'es': 0, 'ce': 0, 'ice': 0, 'mguk': 0, 'tc': 0, 'motor_partido': 0, 'motor_gripado': 0,
        })
    return estado, danos


def ler_classificacao(dados):
    o = CABECALHO.size + 1
    carros = []
    for _ in range(N):
        v = CLASSIFICACAO.unpack_from(dados, o); o += CLASSIFICACAO.size
        ns = min(v[10], 8)
        carros.append({'posicao': v[0], 'voltas': v[1], 'grelha': v[2], 'pontos': v[3], 'paragens': v[4],
                       'resultado': RESULTADOS.get(v[5], v[5]), 'motivo': 0, 'melhor_ms': _ms(v[6]),
                       'tempo_total': v[7], 'penalizacoes_s': v[8], 'n_penalizacoes': v[9],
                       # o F1 2020 não diz em que volta acabou cada stint
                       'stints': [{'visual': v[19 + k], 'fim': None} for k in range(ns)]})
    return carros


LEITORES = {1: ('sessao', ler_sessao), 2: ('voltas', ler_voltas), 3: ('evento', ler_evento),
            4: ('participantes', ler_participantes), 6: ('telemetria', ler_telemetria),
            7: ('estado_e_danos', ler_estado_e_danos), 8: ('classificacao', ler_classificacao)}


def descodificar(dados):
    if len(dados) < CABECALHO.size:
        return None
    cab = ler_cabecalho(dados)
    if cab['formato'] != FORMATO or cab['id'] not in LEITORES:
        return None
    if len(dados) != tamanho_esperado(cab['id']):
        return None
    nome, ler = LEITORES[cab['id']]
    return cab, nome, ler(dados)
