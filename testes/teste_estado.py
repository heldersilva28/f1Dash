"""Testes da lógica do painel (telemetria/estado.py): voltas da corrida, flashbacks, espectador,
referência entre sessões, medições guardadas, alertas e memória.

    python -m unittest discover -s testes
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from telemetria import estado as E            # noqa: E402
from telemetria import pacotes as P           # noqa: E402
import demo                                   # noqa: E402

PISTA = 10           # Spa: 44 voltas, 7004 m
COMPRIMENTO = 7004


class ComMemoriaTemporaria(unittest.TestCase):
    """Cada teste usa um memoria.json próprio, para nunca tocar no do jogador."""

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.original = E.FICHEIRO_MEMORIA
        E.FICHEIRO_MEMORIA = os.path.join(self.pasta.name, 'memoria.json')

    def tearDown(self):
        E.FICHEIRO_MEMORIA = self.original
        self.pasta.cleanup()


# ---------------------------------------------------------------- dados sintéticos
def cab(uid=1, jogador=0):
    return {'formato': 2026, 'uid': uid, 'jogador': jogador}


def sessao(tipo=15, voltas=44, espectador=0, carro_espectador=255, previsao=(), meteo=0):
    return {'tipo': tipo, 'voltas_total': voltas, 'pista': PISTA, 'comprimento': COMPRIMENTO,
            'setor2_inicio': 2120.0, 'setor3_inicio': 5290.0, 'espectador': espectador,
            'carro_espectador': carro_espectador, 'previsao': list(previsao), 'tempo_meteo': meteo,
            'temp_ar': 18, 'temp_pista': 27, 'tempo_restante': 600, 'duracao': 900, 'safety_car': 0,
            'box_ideal': 0, 'box_ultima': 0, 'box_reentrada': 0, 'zonas': [], 'aero_zonas': []}


def volta(n, dist, atual, ultima=0, estado=1):
    return {'resultado': 2, 'paragens': 0, 'volta': n, 'dist_volta': dist, 'atual': atual, 'ultima': ultima,
            'estado_piloto': estado, 'invalida': 0, 'posicao': 1, 'dist_total': dist, 'para_frente': 0,
            'para_lider': 0, 'penalizacoes': 0, 'box_estado': 0, 'grelha': 1, 'speed_trap': 300, 's1': 0, 's2': 0,
            'setor': 0, 'delta_sc': 0.0, 'avisos': 0, 'avisos_limites': 0, 'drive_through': 0, 'stop_go': 0,
            'cumpre_penalizacao': 0}


def conduzir(s, n, de, ate, t0=0, passo=50, ms_por_metro=15.0, uid=1):
    """Leva o carro 0 da distância `de` à `ate` na volta `n`; devolve o tempo de volta no fim."""
    d = de
    while d <= ate:
        s.receber(cab(uid), 'voltas', [volta(n, d, int(t0 + (d - de) * ms_por_metro))])
        d += passo
    return int(t0 + (ate - de) * ms_por_metro)


def alimentar_demo(s, modo, passos=200, jogador=None, mexer_sessao=None):
    sim = demo.criar(modo)
    for _ in range(passos):
        sim.passo(0.05)
        for p in sim.pacotes():
            r = P.descodificar(p)
            if not r:
                continue
            c, nome, conteudo = r
            if jogador is not None:
                c = dict(c, jogador=jogador)
            if nome == 'sessao' and mexer_sessao:
                mexer_sessao(conteudo)
            s.receber(c, nome, conteudo)
    return s


# ---------------------------------------------------------------- funções simples
class TesteAjudas(unittest.TestCase):
    def test_ecra_da_sessao(self):
        self.assertEqual(E.ecra_da_sessao(1), 'treinos')
        self.assertEqual(E.ecra_da_sessao(4), 'treinos')
        self.assertEqual(E.ecra_da_sessao(5), 'qualificacao')
        self.assertEqual(E.ecra_da_sessao(18), 'qualificacao')
        self.assertEqual(E.ecra_da_sessao(15), 'corrida')

    def test_codigo_piloto(self):
        self.assertEqual(E.codigo_piloto('Lando NORRIS'), 'NOR')
        self.assertEqual(E.codigo_piloto('Nico HÜLKENBERG'), 'HUL')
        self.assertEqual(E.codigo_piloto(''), '???')

    def test_voltas_completas(self):
        self.assertEqual(E.voltas_completas(PISTA, COMPRIMENTO), 44)
        self.assertEqual(E.voltas_completas(999, 5000), 61)   # sem tabela: 305 km / comprimento

    def test_tarefa(self):
        self.assertEqual(E._tarefa('X', 2, 8, 'voltas')['detalhe'], '2 de 8 voltas')
        self.assertTrue(E._tarefa('X', 9, 8, 'voltas')['feito'])


# ---------------------------------------------------------------- voltas da corrida
class TesteVoltasCorrida(ComMemoriaTemporaria):
    def nova(self, tipo, voltas, memoria=None):
        s = E.Sessao()
        s.memoria = memoria or {}
        s.sessao = sessao(tipo=tipo, voltas=voltas)
        return s

    def test_na_corrida_usa_o_numero_do_jogo(self):
        self.assertEqual(self.nova(15, 22).voltas_corrida(), (22, 'da corrida'))

    def test_nos_treinos_usa_a_ultima_corrida_neste_circuito(self):
        s = self.nova(2, 0, {'corridas': {str(PISTA): 22}})
        self.assertEqual(s.voltas_corrida(), (22, 'da última corrida aqui'))

    def test_aprende_a_percentagem_das_tuas_corridas(self):
        s = self.nova(2, 0, {'percentagem': 0.5})
        self.assertEqual(s.voltas_corrida()[0], 22)

    def test_sem_nada_usa_a_distancia_completa(self):
        self.assertEqual(self.nova(2, 0).voltas_corrida(), (44, 'distância completa'))

    def test_corrida_guarda_voltas_e_percentagem(self):
        s = E.Sessao()
        s.receber(cab(), 'sessao', sessao(tipo=15, voltas=22))
        with open(E.FICHEIRO_MEMORIA, encoding='utf-8') as f:
            guardado = json.load(f)
        self.assertEqual(guardado['corridas'][f'{PISTA}:0'], 22)
        self.assertEqual(guardado['percentagem_por_duracao']['0'], 0.5)


# ---------------------------------------------------------------- memória
class TesteMemoria(ComMemoriaTemporaria):
    def test_guardar_e_ler(self):
        E.guardar_memoria({'a': 1})
        self.assertEqual(E.ler_memoria(), {'a': 1})
        self.assertFalse(os.path.exists(E.FICHEIRO_MEMORIA + '.tmp'))

    def test_falha_a_meio_nao_estraga_o_ficheiro(self):
        E.guardar_memoria({'a': 1})
        E.guardar_memoria({'b': object()})        # não dá para escrever em JSON
        self.assertEqual(E.ler_memoria(), {'a': 1})
        self.assertFalse(os.path.exists(E.FICHEIRO_MEMORIA + '.tmp'))

    def test_modo_demo_nao_grava(self):
        s = E.Sessao(guardar=False)
        s.receber(cab(), 'sessao', sessao(tipo=15, voltas=44))
        self.assertFalse(os.path.exists(E.FICHEIRO_MEMORIA))


# ---------------------------------------------------------------- flashbacks
class TesteFlashback(ComMemoriaTemporaria):
    def preparar(self):
        s = E.Sessao(guardar=False)
        s.receber(cab(), 'sessao', sessao(tipo=5))
        conduzir(s, 1, 0, 0)          # primeira leitura: marca a volta atual
        return s

    def test_flashback_a_meio_da_volta_refaz_o_traco(self):
        s = self.preparar()
        conduzir(s, 1, 50, 3000, t0=750)                 # 1.ª passagem: 15 ms por metro
        antes = s.traco_atual[250]                         # aos 2500 m
        # flashback para os 1000 m e repete o troço mais depressa (10 ms por metro)
        t = s.traco_atual[100]
        conduzir(s, 1, 1000, 3000, t0=t, ms_por_metro=10)
        self.assertLess(s.traco_atual[250], antes)
        self.assertEqual(s.traco_atual[250], t + 15000)

    def test_flashback_limpa_os_mini_setores_a_frente(self):
        s = self.preparar()
        conduzir(s, 1, 50, 3000, t0=750)
        lim = s._limites_mini()
        self.assertTrue(any(lim[k] > 1500 for k in s.mini_atual[0]))
        s.receber(cab(), 'voltas', [volta(1, 1500, 22000)])
        self.assertFalse(any(lim[k] > 1500 for k in s.mini_atual[0]))

    def test_flashback_para_a_volta_anterior_nao_cria_referencia_errada(self):
        s = self.preparar()
        fim = conduzir(s, 1, 10, COMPRIMENTO - 40, t0=150)
        s.receber(cab(), 'voltas', [volta(2, 20, 300, ultima=fim)])      # cruza a meta: volta 1 fica como referência
        self.assertEqual(s.tempo_melhor_traco, fim)
        s.receber(cab(), 'voltas', [volta(1, COMPRIMENTO - 400, fim - 6000, ultima=0)])   # flashback para trás da meta
        self.assertEqual(s.minha_volta, 1)
        self.assertEqual(s.traco_atual, {})
        # a volta recomeça a meio: ao cruzar a meta outra vez não pode substituir a referência por uma volta incompleta
        s.receber(cab(), 'voltas', [volta(2, 20, 300, ultima=fim - 5000)])
        self.assertEqual(s.tempo_melhor_traco, fim)


# ---------------------------------------------------------------- espectador
class TesteEspectador(ComMemoriaTemporaria):
    def test_sem_carro_nao_rebenta(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'corrida', passos=40, jogador=255)
        f = s.fotografia()
        self.assertFalse(f['pronto'])
        self.assertTrue(f['espectador'])

    def test_segue_o_carro_que_o_jogo_mostra(self):
        def espectar(c):
            c['espectador'], c['carro_espectador'] = 1, 0
        s = alimentar_demo(E.Sessao(guardar=False), 'corrida', passos=60, jogador=255, mexer_sessao=espectar)
        f = s.fotografia()
        self.assertTrue(f['pronto'])
        self.assertTrue(f['espectador'])
        self.assertEqual(f['eu']['codigo'], 'VER')     # carro 0 da grelha da demo


# ---------------------------------------------------------------- referência entre sessões
class TesteReferenciaQualificacao(ComMemoriaTemporaria):
    def com_volta_rapida(self, uid, tipo):
        s = E.Sessao(guardar=False)
        s.receber(cab(uid), 'sessao', sessao(tipo=tipo))
        conduzir(s, 1, 0, 0, uid=uid)
        fim = conduzir(s, 1, 10, COMPRIMENTO - 40, t0=150, uid=uid)
        s.receber(cab(uid), 'voltas', [volta(2, 20, 300, ultima=fim)])
        return s, fim

    def test_q1_passa_para_q2(self):
        s, fim = self.com_volta_rapida(1, 5)
        s.receber(cab(2), 'sessao', sessao(tipo=6))
        self.assertEqual(s.tempo_melhor_traco, fim)
        self.assertEqual(s.referencia_origem, 'Q1')

    def test_nao_passa_para_a_corrida(self):
        s, _ = self.com_volta_rapida(1, 5)
        s.receber(cab(2), 'sessao', sessao(tipo=15))
        self.assertIsNone(s.tempo_melhor_traco)

    def test_nao_passa_para_outro_circuito(self):
        s, _ = self.com_volta_rapida(1, 5)
        outra = sessao(tipo=6)
        outra['pista'] = 11
        s.receber(cab(2), 'sessao', outra)
        self.assertIsNone(s.tempo_melhor_traco)


# ---------------------------------------------------------------- medições dos treinos na corrida
class TesteMedicoesGuardadas(ComMemoriaTemporaria):
    def test_corrida_usa_o_desgaste_e_consumo_dos_treinos(self):
        s = E.Sessao(guardar=False)
        s.memoria = {'pistas': {str(PISTA): {'consumo': 1.6, 'sessao': 'Treinos livres 2',
                                            'desgaste': {'M': [1.0, 1.2, 1.5, 1.8]}}}}
        alimentar_demo(s, 'corrida', passos=40)
        eu = s.fotografia()['eu']
        self.assertEqual(eu['composto'], 'M')
        self.assertEqual(eu['desgaste_volta'], [1.0, 1.2, 1.5, 1.8])
        self.assertEqual(eu['desgaste_fonte'], 'medido em Treinos livres 2')
        self.assertEqual(eu['consumo_volta'], 1.6)
        self.assertIsNotNone(eu['vida_restante_voltas'])

    def test_sem_medicoes_nao_inventa(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'corrida', passos=40)
        eu = s.fotografia()['eu']
        self.assertIsNone(eu['consumo_volta'])
        self.assertIsNone(eu.get('desgaste_volta'))

    def test_treinos_guardam_por_circuito_e_composto(self):
        s = E.Sessao()
        alimentar_demo(s, 'treinos', passos=20 * 60 * 4)       # 4 minutos: duas voltas completas
        guardado = E.ler_memoria()['pistas'][str(PISTA)]
        self.assertGreater(guardado['consumo'], 0)
        self.assertIn('S', guardado['desgaste'])
        self.assertEqual(guardado['sessao'], 'Treinos livres 2')


# ---------------------------------------------------------------- alertas
class TesteAlertas(ComMemoriaTemporaria):
    def alertas(self, eu=None, sessao_extra=None, meteo=0, ecra='corrida'):
        s = E.Sessao(guardar=False)
        s.sessao = sessao(meteo=meteo)
        base = {'safety_car': 0, 'chuva': None, 'box_ideal': 0, 'box_ultima': 0, 'voltas_total': 44}
        base.update(sessao_extra or {})
        meu = {'estado_piloto': 4, 'box': False, 'composto': 'M', 'volta': 10}
        meu.update(eu or {})
        return s._alertas({'sessao': base, 'eu': meu, 'ecra': ecra})

    def test_sem_nada_nao_ha_alertas(self):
        self.assertEqual(self.alertas(), [])

    def test_chuva_com_pneus_de_seco_e_o_mais_grave(self):
        res = self.alertas(meteo=4, sessao_extra={'safety_car': 1})
        self.assertEqual([a['id'] for a in res], ['chuva', 'sc'])
        self.assertEqual(res[0]['nivel'], 'perigo')

    def test_chuva_prevista(self):
        res = self.alertas(sessao_extra={'chuva': {'min': 10, 'chuva': 60}})
        self.assertEqual(res[0]['texto'], 'Chuva 60% daqui a 10 min — prepara os intermédios')

    def test_chuva_prevista_com_intermedios_nao_avisa(self):
        self.assertEqual(self.alertas(eu={'composto': 'I'}, sessao_extra={'chuva': {'min': 10, 'chuva': 60}}), [])

    def test_pneus_no_limite(self):
        res = self.alertas(eu={'vida_restante_voltas': 1})
        self.assertEqual(res[0]['id'], 'box')
        self.assertEqual(res[0]['nivel'], 'perigo')

    def test_janela_de_box(self):
        res = self.alertas(sessao_extra={'box_ideal': 9, 'box_ultima': 12})
        self.assertEqual(res[0]['texto'], 'Janela de box aberta até à volta 12')

    def test_asa_e_combustivel(self):
        res = self.alertas(eu={'danos': {'asa_fe': 40, 'asa_fd': 0}, 'margem_voltas': -0.6})
        self.assertEqual({a['id'] for a in res}, {'asa', 'fuel'})

    def test_previsao_de_chuva(self):
        s = E.Sessao(guardar=False)
        s.sessao = sessao(tipo=15, previsao=[
            {'tipo': 15, 'minutos': 0, 'chuva': 80}, {'tipo': 15, 'minutos': 5, 'chuva': 10},
            {'tipo': 15, 'minutos': 15, 'chuva': 55}, {'tipo': 15, 'minutos': 10, 'chuva': 45},
            {'tipo': 13, 'minutos': 5, 'chuva': 90}])
        self.assertEqual(s._chuva_prevista(), {'min': 10, 'chuva': 45})


# ---------------------------------------------------------------- qualificação
class TesteQualificacao(ComMemoriaTemporaria):
    def test_linha_de_corte_na_q2(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'qualificacao', passos=60)
        q = s.fotografia()['quali']
        self.assertEqual(q['corte'], 10)
        self.assertEqual(len(q['ordem']), 16)


# ---------------------------------------------------------------- duração da corrida e fim de semana (dados do jogo)
class TesteFimDeSemana(ComMemoriaTemporaria):
    def test_sprint_nao_estraga_a_duracao_aprendida(self):
        s = E.Sessao()
        fds = [1, 10, 11, 12, 15, 5, 6, 7, 16]          # TL1, shootout, sprint, qualificação, corrida
        sprint = dict(sessao(tipo=15, voltas=15), fim_de_semana=fds, duracao_sessao=7)
        s.receber(cab(1), 'sessao', sprint)
        self.assertFalse(os.path.exists(E.FICHEIRO_MEMORIA))
        s.receber(cab(2), 'sessao', dict(sessao(tipo=16, voltas=44), fim_de_semana=fds, duracao_sessao=7))
        self.assertEqual(E.ler_memoria()['corridas'][f'{PISTA}:7'], 44)

    def test_voltas_pela_duracao_escolhida_no_jogo(self):
        s = E.Sessao()
        s.memoria = {'percentagem_por_duracao': {'3': 0.25, '7': 1.0}}
        s.sessao = dict(sessao(tipo=2, voltas=0), duracao_sessao=3)
        self.assertEqual(s.voltas_corrida()[0], 11)
        s.sessao['duracao_sessao'] = 7
        self.assertEqual(s.voltas_corrida()[0], 44)

    def test_proxima_sessao(self):
        s = E.Sessao(guardar=False)
        s.sessao = dict(sessao(tipo=2), fim_de_semana=[1, 2, 3, 5, 6, 7, 15])
        self.assertEqual(s._proxima_sessao(), 'Treinos livres 3')
        s.sessao['tipo'] = 15
        self.assertIsNone(s._proxima_sessao())

    def test_programa_com_um_so_treino(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'treinos', passos=40,
                           mexer_sessao=lambda c: c.update(fim_de_semana=[2, 10, 11, 12, 15, 5, 6, 7, 16]))
        nomes = [t['nome'] for t in s.fotografia()['treinos']['programa']]
        self.assertEqual(nomes, ['Reconhecimento da pista', 'Simulação de qualificação', 'Simulação de corrida',
                                 'Medir o consumo de combustível'])


# ---------------------------------------------------------------- plano de corrida
def conj(comp, vida, delta, desgaste=0):
    return {'composto': comp, 'vida': vida, 'vida_util': vida, 'delta': delta, 'desgaste': desgaste}


class TestePlano(unittest.TestCase):
    def test_sem_paragem_se_os_pneus_chegam_e_ja_usaste_dois_compostos(self):
        planos = E.planear(10, [conj('H', 30, 300)], conj('M', 12, 0), usados={'S', 'M'}, volta_atual=35)
        self.assertEqual(planos[0]['paragens'], 0)

    def test_regra_dos_dois_compostos(self):
        planos = E.planear(10, [conj('H', 30, 300)], conj('M', 12, 0), usados={'M'}, volta_atual=35)
        self.assertEqual(planos[0]['paragens'], 1)
        self.assertEqual(planos[0]['stints'][1]['composto'], 'H')

    def test_respeita_a_vida_de_cada_conjunto(self):
        planos = E.planear(30, [conj('S', 15, -500), conj('H', 34, 200)], conj('M', 10, 0), usados={'M'})
        p = planos[0]
        vidas = {'M': 10, 'S': 15, 'H': 34}
        for st in p['stints']:
            self.assertLessEqual(st['voltas'], vidas[st['composto']])
        self.assertEqual(sum(st['voltas'] for st in p['stints']), 30)

    def test_mais_paragens_so_quando_compensa(self):
        rapido = [conj('S', 10, -1000), conj('S', 10, -1000)]
        com_perda_grande = E.planear(20, rapido + [conj('H', 30, 0)], conj('M', 10, 0), perda_box_ms=30000, usados={'M'})
        self.assertEqual(com_perda_grande[0]['paragens'], 1)
        com_perda_pequena = E.planear(20, rapido + [conj('H', 30, 0)], conj('M', 10, 0), perda_box_ms=1000, usados={'M'})
        self.assertEqual(com_perda_pequena[0]['paragens'], 2)

    def test_voltas_da_paragem(self):
        p = E.planear(20, [conj('H', 30, 0)], conj('M', 8, 0), usados={'M'}, volta_atual=25)[0]
        self.assertEqual(p['box'], [p['stints'][0]['ate_volta']])
        self.assertEqual(p['stints'][-1]['ate_volta'], 44)

    def test_janela_do_jogo_quando_custa_pouco(self):
        p = E.planear(20, [conj('H', 30, 50)], conj('M', 15, 0), usados={'M'}, volta_atual=25, janela=(30, 33))[0]
        self.assertEqual(p['box'], [30])

    def test_sem_pneus_que_cheguem(self):
        self.assertEqual(E.planear(40, [conj('H', 10, 0)], conj('M', 5, 0), usados={'M'}), [])


class TestePneusDoJogo(ComMemoriaTemporaria):
    def test_vida_vem_do_conjunto_montado(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'corrida', passos=60)
        eu = s.fotografia()['eu']
        self.assertEqual(eu['vida_fonte'], 'do jogo')
        self.assertEqual(eu['vida_total_voltas'], 26)                # médios na demo
        self.assertEqual(eu['vida_restante_voltas'], 26 - eu['idade'])

    def test_plano_e_perda_de_box_medida_nas_paragens(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'corrida', passos=600)
        plano = s.fotografia()['corrida']['plano']
        self.assertIn('medida', plano['perda_box_fonte'])
        self.assertAlmostEqual(plano['perda_box_s'], 21.4, delta=1.5)
        self.assertEqual(plano['stints'][-1]['ate_volta'], 44)

    def test_saida_e_entrada_do_historico_na_qualificacao(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'qualificacao', passos=200)
        q = s.fotografia()['quali']
        self.assertEqual(q['tempos_box_fonte'], 'do jogo')
        self.assertGreater(q['saida_ms'], 100000)


# ---------------------------------------------------------------- bandeiras e penalizações (dados do jogo)
class TesteBandeiras(ComMemoriaTemporaria):
    def test_vermelha_vem_do_evento(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'corrida', passos=20)
        s.receber(cab(s.uid, demo.JOGADOR), 'evento', {'codigo': 'RDFL'})
        f = s.fotografia()
        self.assertTrue(f['sessao']['bandeira_vermelha'])
        self.assertEqual(f['alertas'][0]['id'], 'vermelha')
        s.receber(cab(s.uid, demo.JOGADOR), 'evento', {'codigo': 'LGOT'})
        self.assertFalse(s.fotografia()['sessao']['bandeira_vermelha'])

    def test_amarela_a_frente_pelas_zonas(self):
        s = E.Sessao(guardar=False)
        s.sessao = dict(sessao(), zonas=[{'inicio': 0.0, 'bandeira': 0}, {'inicio': 0.5, 'bandeira': 3},
                                         {'inicio': 0.7, 'bandeira': 0}])
        s.voltas = [volta(3, 0.4 * COMPRIMENTO, 0)]
        self.assertEqual(s._amarela_a_frente(), round(0.1 * COMPRIMENTO))
        s.voltas = [volta(3, 0.6 * COMPRIMENTO, 0)]
        self.assertEqual(s._amarela_a_frente(), 0)
        s.voltas = [volta(3, 0.8 * COMPRIMENTO, 0)]
        self.assertEqual(s._amarela_a_frente(), round(0.7 * COMPRIMENTO))

    def alertas(self, **eu):
        s = E.Sessao(guardar=False)
        s.sessao = sessao()
        base = {'safety_car': 0, 'chuva': None, 'box_ideal': 0, 'box_ultima': 0, 'voltas_total': 44,
                'bandeira_vermelha': False, 'zona_amarela_m': None}
        sc = eu.pop('sc', 0)
        base['safety_car'] = sc
        meu = dict({'estado_piloto': 4, 'box': False, 'composto': 'M', 'volta': 10}, **eu)
        return s, s._alertas({'sessao': base, 'eu': meu, 'ecra': 'corrida'})

    def test_delta_do_safety_car(self):
        _, res = self.alertas(sc=2, delta_sc=-0.4)
        self.assertEqual((res[0]['id'], res[0]['nivel']), ('sc', 'perigo'))
        _, res = self.alertas(sc=2, delta_sc=1.2)
        self.assertEqual(res[0]['texto'], 'Virtual Safety Car · delta +1.2 s')

    def test_penalizacao_por_cumprir(self):
        _, res = self.alertas(drive_through=1, cumpre_penalizacao=True)
        self.assertEqual(res[0]['texto'], 'Drive-through por cumprir — cumpres nesta paragem')

    def test_aviso_de_limites_de_pista_dura_uns_segundos(self):
        s = E.Sessao(guardar=False)
        s.receber(cab(), 'sessao', sessao(tipo=15))
        v = volta(3, 100, 1000)
        v['avisos_limites'] = 2
        s.receber(cab(), 'voltas', [v])
        self.assertEqual(s.avisos_limites[0], 2)
        res = s._alertas({'sessao': {'safety_car': 0, 'chuva': None, 'box_ideal': 0, 'box_ultima': 0, 'voltas_total': 44},
                          'eu': {'estado_piloto': 4, 'composto': 'M'}, 'ecra': 'corrida'})
        self.assertEqual(res[0]['texto'], '2 avisos de limites de pista')
        s.avisos_limites = (2, 0.0)
        res = s._alertas({'sessao': {'safety_car': 0, 'chuva': None, 'box_ideal': 0, 'box_ultima': 0, 'voltas_total': 44},
                          'eu': {'estado_piloto': 4, 'composto': 'M'}, 'ecra': 'corrida'})
        self.assertEqual(res, [])


# ---------------------------------------------------------------- resumo no fim da sessão
class TesteResumo(ComMemoriaTemporaria):
    def test_corrida_usa_a_classificacao_final_do_jogo(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'corrida', passos=60)
        self.assertNotIn('resumo', s.fotografia())
        fc = [{'posicao': 0, 'voltas': 0, 'grelha': 0, 'pontos': 0, 'paragens': 0, 'resultado': 0, 'motivo': 0,
               'melhor_ms': 0, 'tempo_total': 0.0, 'penalizacoes_s': 0, 'n_penalizacoes': 0, 'stints': []}
              for _ in range(22)]
        fc[0].update(posicao=1, voltas=44, tempo_total=4700.0, resultado=3)
        fc[demo.JOGADOR].update(posicao=3, voltas=44, grelha=5, pontos=15, paragens=1, resultado=3, melhor_ms=106100,
                                tempo_total=4712.5, stints=[{'visual': 16, 'fim': 18}, {'visual': 17, 'fim': 44}])
        s.receber(cab(s.uid, demo.JOGADOR), 'classificacao', fc)
        r = s.fotografia()['resumo']
        self.assertEqual((r['posicao'], r['grelha'], r['pontos'], r['resultado']), (3, 5, 15, 'Terminou'))
        self.assertEqual([(st['composto'], st['voltas']) for st in r['stints']], [('S', 18), ('M', 26)])
        self.assertEqual(r['box_voltas'], [18])
        eu = next(x for x in r['tabela'] if x['eu'])
        self.assertEqual((eu['pos'], eu['pontos'], eu['dif'], eu['compostos']), (3, 15, '+12.500', ['S', 'M']))
        self.assertEqual(r['tabela'][0]['dif'], '1:18:20.000')          # o vencedor mostra o tempo total
        self.assertEqual(r['posicoes'][-1]['pos'], 3)
        self.assertEqual(r['para_vencedor_s'], 12.5)
        self.assertEqual(s.fotografia()['alertas'], [])        # corrida acabada: sem alertas

    def test_treinos_no_fim_da_sessao(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'treinos', passos=60)
        s.receber(cab(s.uid, demo.JOGADOR), 'evento', {'codigo': 'SEND'})
        r = s.fotografia()['resumo']
        self.assertEqual(r['proxima'], 'Treinos livres 3')
        self.assertEqual(r['programa']['total'], 3)
        self.assertIn('plano_corrida', r)
        self.assertEqual(r['proxima_programa'], ['Simulação de qualificação', 'Confirmar ritmo de corrida (5 voltas)',
                                                 'Medir o desgaste dos pneus'])
        # a simulação de corrida é o stint com mais voltas limpas, não o último
        runs = []
        fim_ant = 0
        for st in r['stints']:
            runs.append(sum(1 for v in r['voltas_lista'] if fim_ant < v['n'] <= st['ate_volta'] and v['valida'] and not v['box']))
            fim_ant = st['ate_volta']
        self.assertEqual(len(r['ritmo']['voltas']), max(runs))

    def test_nova_sessao_apaga_o_resumo(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'treinos', passos=20)
        s.receber(cab(s.uid, demo.JOGADOR), 'evento', {'codigo': 'SEND'})
        s.receber(cab(999), 'sessao', sessao(tipo=3))
        self.assertFalse(s.fim_sessao)


# ---------------------------------------------------------------- resumos mais completos
class TesteResumoCompleto(ComMemoriaTemporaria):
    def test_corrida_da_demo_ate_ao_fim(self):
        """A demo termina a corrida como o jogo: resultado final, posições por volta e classificação."""
        sim = demo.Simulador('corrida')
        s = E.Sessao(guardar=False)
        k = 0
        while not (s.fim_sessao and s.classificacao) and k < 20 * 60 * 100:
            sim.passo(0.05)
            k += 1
            if k % 4 and not s.fim_sessao:
                continue
            for p in sim.pacotes():
                r = P.descodificar(p)
                if r:
                    s.receber(*r)
        f = s.fotografia()
        r = f['resumo']
        self.assertEqual(r['fonte'], 'classificação final do jogo')
        self.assertEqual(len(r['tabela']), 22)
        self.assertEqual(r['voltas'], 44)
        self.assertEqual(sum(st['voltas'] for st in r['stints']), 44)
        self.assertEqual(r['posicoes'][-1]['pos'], r['posicao'])
        self.assertGreater(len(r['posicoes']), 40)               # vem do pacote de posições do jogo
        self.assertEqual(sum(x['pontos'] for x in r['tabela']), 101)
        self.assertEqual(sum(1 for x in r['tabela'] if x['volta_rapida']), 1)
        self.assertTrue(any(x['eu'] for x in r['ritmos']))
        self.assertEqual([x['rank'] for x in r['ritmos'][:3]], [1, 2, 3])
        self.assertEqual(f['alertas'], [])

    def test_qualificacao_compara_setores_com_a_pole(self):
        sim = demo.Simulador('qualificacao')
        sim.carros[demo.JOGADOR].na_garagem_ate = 5
        s = E.Sessao(guardar=False)
        while not s.fim_sessao:
            sim.passo(0.05)
            for p in sim.pacotes():
                r = P.descodificar(p)
                if r:
                    s.receber(*r)
        r = s.fotografia()['resumo']
        self.assertTrue(r['voltas_lista'])
        self.assertIn(r['voltas_lista'][0]['box'], ('saida', None))
        if r['posicao'] > 1:
            pole = r['comparacao'][0]
            self.assertEqual(pole['pos'], 1)
            self.assertEqual(pole['total_ms'], sum(pole['setores_ms']))
            self.assertEqual(pole['total_ms'], r['para_pole_ms'])


# ---------------------------------------------------------------- correções da revisão
class TesteRevisao(ComMemoriaTemporaria):
    def test_plano_com_pneus_no_fim_para_nesta_volta(self):
        p = E.planear(10, [conj('H', 30, 0)], dict(conj('M', 0, 0), vida_util=26), usados={'M'}, volta_atual=35)[0]
        self.assertEqual(p['box'], [35])                      # box nesta volta, não numa que já passou
        self.assertEqual(p['stints'][0]['voltas'], 1)

    def test_stints_planeados_tem_pelo_menos_5_voltas(self):
        # antes: "Macios 1 volta -> Médios 21" só para cumprir a regra dos dois compostos
        p = E.planear(22, [conj('S', 13, 100), conj('M', 26, -300)], None)[0]
        self.assertTrue(all(st['voltas'] >= 5 for st in p['stints']), p['stints'])
        # o stint em curso pode acabar já, se for preciso
        p = E.planear(20, [conj('H', 30, 0)], conj('M', 1, 0), usados={'M'})[0]
        self.assertEqual(p['stints'][0]['voltas'], 1)

    def test_conjuntos_sem_vida_nao_entram_no_plano(self):
        planos = E.planear(10, [conj('S', 0, -900), conj('H', 30, 0)], conj('M', 5, 0), usados={'M'})
        self.assertTrue(all(st['composto'] != 'S' for p in planos for st in p['stints']))

    def test_voltas_escolhidas_a_mao_servem_para_tudo(self):
        s = E.Sessao()
        self.assertFalse(s.definir_voltas(22))                # ainda sem sessão: não há circuito
        s.sessao = sessao(tipo=2, voltas=0)
        self.assertTrue(s.definir_voltas(22))
        self.assertEqual(s.voltas_corrida(), (22, 'definido por ti'))
        self.assertEqual(E.ler_memoria()['voltas_manuais'][str(PISTA)], 22)
        s.sessao = sessao(tipo=15, voltas=44)                 # na corrida manda o jogo
        self.assertEqual(s.voltas_corrida(), (44, 'da corrida'))
        s.sessao = sessao(tipo=2, voltas=0)
        s.definir_voltas(None)
        self.assertNotEqual(s.voltas_corrida()[1], 'definido por ti')

    def test_plano_dos_treinos_usa_as_voltas_escolhidas(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'treinos', passos=60)
        s.definir_voltas(10)
        plano = s.fotografia()['treinos']['plano_corrida']
        self.assertEqual(sum(st['voltas'] for st in plano['stints']), 10)


# ---------------------------------------------------------------- vista do volante (tablet)
class TesteVolante(ComMemoriaTemporaria):
    def test_dados_do_volante_vem_do_jogo(self):
        s = alimentar_demo(E.Sessao(guardar=False), 'corrida', passos=60)
        f = s.fotografia()
        eu = f['eu']
        self.assertEqual(eu['travao_bias'], 56)                  # repartição de travagem (estado do carro)
        self.assertTrue(0 <= eu['luzes_rpm'] <= 100)             # luzes de rotações (telemetria)
        self.assertTrue(1 <= eu['mudanca'] <= 8)
        self.assertGreater(eu['rpm'], 9000)
        self.assertEqual(f['sessao']['setores_m'], [2120, 5290, 7004])
        self.assertEqual(len(eu['setores_sessao']), 3)
        self.assertGreaterEqual(eu['dist_volta'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
