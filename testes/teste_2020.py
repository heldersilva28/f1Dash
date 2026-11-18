"""Testes do formato UDP do F1 2020: leitura dos pacotes e o que o painel calcula por o jogo não o enviar.

    python -m unittest discover -s testes
"""
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from telemetria import estado as E            # noqa: E402
from telemetria import f1_2020 as F           # noqa: E402
from telemetria import pacotes as P           # noqa: E402
import demo                                   # noqa: E402


def cab(pid, tempo=1.0):
    return F.CABECALHO.pack(2020, 1, 18, 1, pid, 99, tempo, 1, 3, 255)


def vazio(pid):
    return cab(pid) + bytes(F.tamanho_esperado(pid) - F.CABECALHO.size)


def sessao_2020(passos, modo='corrida', parar=None):
    sim = demo.criar(modo)
    sim.formato = 2020
    s = E.Sessao(guardar=False)
    for _ in range(passos):
        sim.passo(1 / 60)
        for p in sim.pacotes():
            r = P.descodificar(p)
            if r:
                s.receber(*r)
        if parar and parar(s):
            break
    return sim, s


class TestePacotes2020(unittest.TestCase):
    def test_tamanhos_oficiais(self):
        self.assertEqual(F.verificar_tamanhos(), [])
        self.assertEqual(P.verificar_tamanhos(), [])

    def test_todos_os_pacotes_descodificam(self):
        for pid, nome in ((1, 'sessao'), (2, 'voltas'), (4, 'participantes'), (6, 'telemetria'),
                          (7, 'estado_e_danos'), (8, 'classificacao')):
            with self.subTest(pacote=pid):
                r = P.descodificar(vazio(pid))
                self.assertIsNotNone(r)
                self.assertEqual(r[1], nome)

    def test_tamanho_errado_e_ignorado(self):
        self.assertIsNone(P.descodificar(vazio(2) + b'\0'))

    def test_pacotes_que_o_2020_nao_tem_sao_ignorados(self):
        self.assertIsNone(P.descodificar(cab(0) + bytes(1440)))      # movimento
        self.assertIsNone(P.descodificar(cab(5) + bytes(1078)))      # afinação

    def test_sessao_converte_os_codigos(self):
        dados = bytearray(vazio(1))
        o = F.CABECALHO.size
        dados[o + 6] = 10                               # tipo de sessão (depois do comprimento, 2 bytes): 10 = corrida
        _, _, s = P.descodificar(bytes(dados))
        self.assertEqual(s['tipo'], 15)                 # 15 = corrida na numeração atual
        self.assertEqual(s['fim_de_semana'], [])

    def test_voltas_em_segundos_passam_a_milissegundos(self):
        dados = bytearray(vazio(2))
        F.VOLTA.pack_into(dados, F.CABECALHO.size, 106.25, 30.5, 30100, 48200, 105.95, 3, *([0] * 9),
                          1234.5, 50000.0, 0.0, 5, 12, 0, 1, 0, 0, 4, 4, 6)
        _, _, v = P.descodificar(bytes(dados))
        c = v[0]
        self.assertEqual((c['ultima'], c['atual'], c['melhor_ms']), (106250, 30500, 105950))
        self.assertEqual((c['s1'], c['s2'], c['posicao'], c['volta']), (30100, 48200, 5, 12))
        self.assertEqual(c['resultado'], 7)             # 6 "desistiu" no 2020 = 7 na numeração atual
        self.assertIsNone(c['para_frente'])             # o 2020 não envia: o painel calcula

    def test_estado_traz_desgaste_e_danos(self):
        dados = bytearray(vazio(7))
        F.ESTADO.pack_into(dados, F.CABECALHO.size, 0, 0, 1, 57, 0, 30.0, 110.0, 1.5, 13000, 4000, 8, 1, 0,
                           20, 22, 30, 33, 17, 17, 9, 0, 0, 0, 0, 12, 0, 0, 0, 5, 0, 4, 3.0e6, 1, 0.0, 0.0, 0.0)
        _, nome, (estado, danos) = P.descodificar(bytes(dados))
        self.assertEqual(nome, 'estado_e_danos')
        self.assertEqual((estado[0]['travao_bias'], estado[0]['composto'], estado[0]['bandeira']), (57, 17, 4))
        self.assertEqual((danos[0]['desgaste'], danos[0]['asa_fe'], danos[0]['motor']), ([20.0, 22.0, 30.0, 33.0], 12, 5))

    def test_speed_trap_vem_em_eventos(self):
        r = P.descodificar(cab(3) + b'SPTP' + struct.pack('<Bf', 4, 331.5).ljust(7, b'\0'))
        self.assertEqual(r[2], {'codigo': 'SPTP', 'carro': 4, 'velocidade': 331.5})

    def test_formatos_atuais_continuam_iguais(self):
        cab26 = P.CABECALHO.pack(2026, 25, 1, 0, 1, 2, 123, 1.0, 1, 1, 0, 255)
        r = P.descodificar(cab26 + bytes(P.tamanho_esperado(2026, 2) - P.CABECALHO.size))
        self.assertEqual(r[1], 'voltas')
        self.assertEqual(len(r[2]), 24)


class TestePainelCom2020(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.original = E.FICHEIRO_MEMORIA
        E.FICHEIRO_MEMORIA = os.path.join(self.pasta.name, 'memoria.json')

    def tearDown(self):
        E.FICHEIRO_MEMORIA = self.original
        self.pasta.cleanup()

    def test_corrida(self):
        sim, s = sessao_2020(60 * 120)
        f = s.fotografia()
        eu = f['eu']
        self.assertEqual((f['ecra'], f['sessao']['nome']), ('corrida', 'Corrida'))
        self.assertEqual(eu['cor'], '#FF8700')                    # McLaren 2020
        self.assertEqual(eu['travao_bias'], 56)
        self.assertEqual(len(eu['danos']['desgaste']), 4)
        self.assertGreater(eu['speed_trap'], 300)                 # do evento SPTP
        self.assertEqual(f['sessao']['setores_m'][:2], [2121, 5290])   # aprendidos onde o jogo muda de setor
        # diferenças calculadas pelo painel, contra as reais da simulação (que mede em blocos de 10 m)
        ordem = sim._ordem()
        for k, c in enumerate(ordem[1:10], start=1):
            self.assertLess(abs(s.voltas[c.i]['para_frente'] - sim._gap(c, ordem[k - 1])), 250, c.nome)
        # histórico construído com as voltas vistas
        h = s.historico[demo.JOGADOR]
        self.assertTrue(any(v['tempo'] for v in h['voltas']))
        self.assertEqual(h['stints'][-1]['fim'], 255)

    def test_setores_de_referencia_logo_ao_abrir(self):
        _, s = sessao_2020(60 * 5)                                 # 5 s: ainda não viu nenhuma volta completa
        eu = s.fotografia()['eu']
        self.assertTrue(eu['melhor_setores'] and all(eu['melhor_setores']))   # vêm nos dados das voltas do 2020
        self.assertTrue(all(eu['setores_sessao']))

    def test_diferencas_desconhecidas_logo_ao_abrir(self):
        _, s = sessao_2020(30)                                     # meio segundo
        f = s.fotografia()
        self.assertTrue(any(c['lider_ms'] is None for c in f['carros']))     # "—" no ecrã, em vez de um número errado
        self.assertEqual(f['carros'][0]['lider_ms'], 0)

    def test_paragens_contadas_pelas_boxes(self):
        sim = demo.criar('corrida')
        sim.formato = 2020
        antes = {c.i: c.paragens for c in sim.carros if c.ativo}
        s = E.Sessao(guardar=False)
        for _ in range(60 * 60 * 8):                               # 8 minutos: há carros a parar
            sim.passo(1 / 60)
            for p in sim.pacotes():
                r = P.descodificar(p)
                if r:
                    s.receber(*r)
        reais = {i: c.paragens - antes[i] for i, c in enumerate(sim.carros) if c.ativo}
        contadas = {i: s.voltas[i]['paragens'] for i in reais}
        self.assertTrue(any(reais.values()))
        self.assertEqual(contadas, reais)

    def test_qualificacao_e_treinos(self):
        for modo, ecra in (('qualificacao', 'qualificacao'), ('treinos', 'treinos')):
            with self.subTest(modo=modo):
                _, s = sessao_2020(60 * 30, modo)
                f = s.fotografia()
                self.assertEqual(f['ecra'], ecra)
                self.assertGreater(f['eu']['melhor_ms'], 0)        # a melhor volta que o 2020 envia nas voltas
                self.assertTrue(all(c['frente_ms'] == 0 for c in f['carros']))   # fora da corrida não há diferenças

    def test_chuva_prevista_sem_percentagem(self):
        _, s = sessao_2020(60 * 5)
        f = s.fotografia()
        self.assertEqual(f['sessao']['chuva'], {'min': 20, 'chuva': None})
        self.assertIn('Chuva prevista daqui a 20 min — prepara os intermédios', [a['texto'] for a in f['alertas']])

    def test_bandeira_vermelha_vem_do_carro(self):
        _, s = sessao_2020(60 * 2)
        s.estado[s.jogador]['bandeira'] = 4
        f = s.fotografia()
        self.assertTrue(f['sessao']['bandeira_vermelha'])
        self.assertEqual(f['alertas'][0]['id'], 'vermelha')

    def test_fim_da_corrida_com_a_classificacao_do_2020(self):
        sim = demo.criar('corrida')
        sim.formato = 2020
        while sim.carros[demo.JOGADOR].volta < 41:                # avança sem o painel até perto do fim
            sim.passo(0.05)
        s = E.Sessao(guardar=False)
        k = 0
        while not s.classificacao and k < 60 * 60 * 20:
            sim.passo(1 / 60)
            k += 1
            for p in sim.pacotes():
                r = P.descodificar(p)
                if r:
                    s.receber(*r)
        r = s.fotografia()['resumo']
        self.assertEqual(r['fonte'], 'classificação final do jogo')
        self.assertEqual(len(r['tabela']), 22)
        self.assertEqual(sum(x['pontos'] for x in r['tabela']), 101)
        self.assertEqual(r['voltas'], 44)
        self.assertTrue(r['stints'])                               # o 2020 não diz onde acabou cada stint: vêm do histórico


if __name__ == '__main__':
    unittest.main(verbosity=2)
