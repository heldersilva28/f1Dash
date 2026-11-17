"""Testes do servidor: o estado é calculado uma vez e um erro de cálculo nunca cala o painel."""
import contextlib
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import f1dash                                  # noqa: E402


class Fonte:
    def __init__(self):
        self.falhar = False
        self.chamadas = 0

    def fotografia(self):
        self.chamadas += 1
        if self.falhar:
            raise IndexError('list index out of range')
        return {'pronto': True, 'n': self.chamadas}


class TesteDifusor(unittest.TestCase):
    def test_partilha_o_ultimo_estado(self):
        d, f = f1dash.Difusor(), Fonte()
        d.atualizar(f)
        versao, corpo = d.esperar(-1)
        self.assertEqual(json.loads(corpo)['n'], 1)
        self.assertEqual(f.chamadas, 1)

    def test_erro_mantem_o_ultimo_estado_e_avisa_uma_vez(self):
        d, f = f1dash.Difusor(), Fonte()
        d.atualizar(f)
        f.falhar = True
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(io.StringIO()):
            d.atualizar(f)
            d.atualizar(f)
        self.assertEqual(json.loads(d.corpo)['n'], 1)
        self.assertEqual(saida.getvalue().count('[erro]'), 1)
        f.falhar = False
        d.atualizar(f)
        self.assertEqual(json.loads(d.corpo)['n'], 4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
