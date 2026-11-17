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
