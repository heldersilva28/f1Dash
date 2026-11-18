"""Testes do servidor: o estado é calculado uma vez e um erro de cálculo nunca cala o painel."""
import contextlib
import io
import json
import os
import sys
import threading
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


class TesteServidor(unittest.TestCase):
    def test_porta_ocupada_passa_para_a_seguinte(self):
        srv1, p1 = f1dash.abrir_servidor(0)               # 0: o sistema escolhe uma porta livre
        porta = srv1.server_address[1]
        try:
            srv2, p2 = f1dash.abrir_servidor(porta)
            self.assertIsNotNone(srv2)
            self.assertNotEqual(srv2.server_address[1], porta)
            srv2.server_close()
        finally:
            srv1.server_close()

    def test_porta_udp_nao_abre_duas_vezes(self):
        a = f1dash.abrir_udp(0)
        try:
            with self.assertRaises(OSError):
                f1dash.abrir_udp(a.getsockname()[1])
        finally:
            a.close()

    def test_definir_voltas_pelo_ecra(self):
        import urllib.request
        import urllib.error
        sessao = f1dash.sessao
        sessao.guardar, sessao.memoria = False, {}
        srv, _ = f1dash.abrir_servidor(0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{srv.server_address[1]}/definicoes'

        def enviar(corpo):
            pedido = urllib.request.Request(url, data=corpo, headers={'Content-Type': 'application/json'})
            try:
                return urllib.request.urlopen(pedido, timeout=5).status
            except urllib.error.HTTPError as e:
                return e.code
        try:
            sessao.sessao = None
            self.assertEqual(enviar(b'{"voltas": 22}'), 409)                 # ainda sem sessão do jogo
            sessao.sessao = {'pista': 10, 'tipo': 2, 'voltas_total': 0, 'comprimento': 7004}
            self.assertEqual(enviar(b'{"voltas": 22}'), 200)
            self.assertEqual(sessao.voltas_corrida(), (22, 'definido por ti'))
            for mau in (b'{"voltas": 0}', b'{"voltas": "22"}', b'{"voltas": true}', b'nada', b'{"voltas": 999}'):
                self.assertEqual(enviar(mau), 400, mau)
            self.assertEqual(enviar(b'{"voltas": null}'), 200)
        finally:
            srv.shutdown()
            srv.server_close()
            sessao.sessao = None


if __name__ == '__main__':
    unittest.main(verbosity=2)
