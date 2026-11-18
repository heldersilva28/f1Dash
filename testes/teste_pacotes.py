"""Testes da leitura dos pacotes: tamanhos oficiais, formatos 2025 e 2026, e a simulação completa.

    python -m unittest discover -s testes        (todos os testes)
    python testes/teste_pacotes.py               (só estes)
"""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from telemetria import pacotes as P          # noqa: E402
from telemetria.estado import Sessao         # noqa: E402
import demo                                   # noqa: E402


def pacote_vazio(fmt, pid):
    cab = P.CABECALHO.pack(fmt, 25, 1, 0, 1, pid, 123, 1.0, 1, 1, 0, 255)
    return cab + bytes(P.tamanho_esperado(fmt, pid) - P.CABECALHO.size)


class TestePacotes(unittest.TestCase):
    def test_tamanhos_batem_com_a_especificacao(self):
        self.assertEqual(P.verificar_tamanhos(), [])

    def test_todos_os_pacotes_descodificam(self):
        for fmt in (2025, 2026):
            for pid in P.TAMANHOS_OFICIAIS[fmt]:
                with self.subTest(formato=fmt, pacote=pid):
                    dados = pacote_vazio(fmt, pid)
                    if pid == 3:
                        dados = dados[:P.CABECALHO.size] + b'FTLP' + struct.pack('<Bf', 0, 100.0).ljust(12, b'\0')
                    self.assertIsNotNone(P.descodificar(dados))

    def test_pacote_com_tamanho_errado_e_ignorado(self):
        dados = pacote_vazio(2026, 2)
        self.assertIsNone(P.descodificar(dados + b'\0'))
        self.assertIsNone(P.descodificar(dados[:10]))

    def test_sessao_le_modo_espectador(self):
        dados = bytearray(pacote_vazio(2026, 1))
        dados[P.CABECALHO.size + 15] = 1     # isSpectating
        dados[P.CABECALHO.size + 16] = 7     # spectatorCarIndex
        _, nome, s = P.descodificar(bytes(dados))
        self.assertEqual(nome, 'sessao')
        self.assertEqual((s['espectador'], s['carro_espectador']), (1, 7))

    def test_sessao_le_duracao_e_fim_de_semana(self):
        dados = bytearray(pacote_vazio(2026, 1))
        o = P.CABECALHO.size + P.SESSAO_A.size + 21 * P.ZONA_COMISSARIOS.size + P.SESSAO_B.size + 64 * P.PREVISAO.size
        c = list(P.SESSAO_C.unpack_from(dados, o))
        c[20], c[52], c[53:56] = 4, 3, [1, 5, 15]
        P.SESSAO_C.pack_into(dados, o, *c)
        _, _, s = P.descodificar(bytes(dados))
        self.assertEqual((s['duracao_sessao'], s['fim_de_semana']), (4, [1, 5, 15]))

    def test_classificacao_final(self):
        dados = bytearray(pacote_vazio(2025, 8))
        o = P.CABECALHO.size
        dados[o] = 22
        P.CLASSIFICACAO.pack_into(dados, o + 1, 3, 44, 5, 15, 1, 3, 0, 106100, 4712.5, 5, 1, 2,
                                  *([0] * 8), 16, 17, *([0] * 6), 18, 44, *([0] * 6))
        _, nome, fc = P.descodificar(bytes(dados))
        self.assertEqual(nome, 'classificacao')
        self.assertEqual((fc[0]['posicao'], fc[0]['pontos'], fc[0]['tempo_total']), (3, 15, 4712.5))
        self.assertEqual(fc[0]['stints'], [{'visual': 16, 'fim': 18}, {'visual': 17, 'fim': 44}])

    def test_posicoes_volta_a_volta(self):
        dados = bytearray(pacote_vazio(2025, 15))
        o = P.CABECALHO.size
        dados[o], dados[o + 1] = 2, 0                     # 2 voltas, a começar na volta 1
        dados[o + 2 + 3] = 5                              # volta 1: carro 3 em P5
        dados[o + 2 + 22 + 3] = 4                         # volta 2: carro 3 em P4
        _, nome, c = P.descodificar(bytes(dados))
        self.assertEqual(nome, 'posicoes_voltas')
        self.assertEqual((c['inicio'], c['voltas'][0][3], c['voltas'][1][3]), (0, 5, 4))

    def test_classificacao_nao_perde_carros_com_indice_alto(self):
        dados = bytearray(pacote_vazio(2025, 8))
        o = P.CABECALHO.size
        dados[o] = 20                                     # só 20 classificados, mas o teu carro é o 21
        P.CLASSIFICACAO.pack_into(dados, o + 1 + 21 * P.CLASSIFICACAO.size, 5, 44, 6, 10, 1, 3, 0, 106000, 4700.0,
                                  0, 0, 1, *([0] * 24))
        _, _, fc = P.descodificar(bytes(dados))
        self.assertEqual(len(fc), 22)
        self.assertEqual(fc[21]['posicao'], 5)

    def test_simulacao_completa(self):
        for modo in ('corrida', 'qualificacao', 'treinos'):
            with self.subTest(modo=modo):
                sim = demo.criar(modo)
                s = Sessao(guardar=False)
                for _ in range(200):
                    sim.passo(0.05)
                    for p in sim.pacotes():
                        r = P.descodificar(p)
                        self.assertIsNotNone(r)
                        s.receber(*r)
                f = s.fotografia()
                self.assertTrue(f['pronto'])
                self.assertEqual(f['ecra'], modo)
                self.assertEqual((f['eu']['codigo'], f['eu']['cor']), ('NOR', '#FF8000'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
