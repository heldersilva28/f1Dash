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
            'setor': 0}


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
        self.assertEqual(guardado['corridas'][str(PISTA)], 22)
        self.assertEqual(guardado['percentagem'], 0.5)


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


if __name__ == '__main__':
    unittest.main(verbosity=2)
