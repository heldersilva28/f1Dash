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


class FonteRapida:
    def __init__(self):
        self.versao_rapida = 0
        self.g = 1

    def rapido(self):
        return {'g': self.g, 'v': 100 + self.g}


class TesteCanalRapido(unittest.TestCase):
    def test_publica_uma_vez_por_pacote_de_telemetria(self):
        fonte = FonteRapida()
        r = f1dash.Rapido(fonte)
        fonte.versao_rapida = 1
        self.assertTrue(r.talvez_publicar('telemetria', agora=10.0))
        fonte.versao_rapida = 2
        self.assertFalse(r.talvez_publicar('voltas', agora=10.0001))     # o pacote de voltas do mesmo frame não repete
        fonte.versao_rapida, fonte.g = 3, 2
        self.assertTrue(r.talvez_publicar('telemetria', agora=10.0167))  # frame seguinte a 60 Hz
        fonte.versao_rapida = 4
        self.assertFalse(r.talvez_publicar('telemetria', agora=10.0170))  # rajada: menos de 1/120 s
        self.assertTrue(r.talvez_publicar('telemetria', agora=10.0500))   # o valor que ficou por enviar sai agora
        self.assertFalse(r.talvez_publicar('telemetria', agora=10.0700))  # sem dados novos: não repete
        versao, corpo = r.esperar(-1)
        self.assertEqual(json.loads(corpo), {'g': 2, 'v': 102})

    def test_sem_telemetria_usa_os_pacotes_de_voltas(self):
        fonte = FonteRapida()
        r = f1dash.Rapido(fonte)
        fonte.versao_rapida = 1
        self.assertTrue(r.talvez_publicar('voltas', agora=5.0))

    def test_ritmo_do_jogo_a_60_hz(self):
        fonte = FonteRapida()
        r = f1dash.Rapido(fonte)
        publicados, t = 0, 0.0
        for frame in range(600):                       # 10 s a 60 Hz, com variação de ±3 ms na chegada
            t = frame / 60 + (0.003 if frame % 2 else -0.003)
            for nome in ('voltas', 'telemetria'):
                fonte.versao_rapida += 1
                publicados += r.talvez_publicar(nome, agora=t)
        self.assertEqual(publicados, 600)

    def test_canal_rapido_pelo_http(self):
        import http.client
        fonte = FonteRapida()
        antigo, f1dash.rapido = f1dash.rapido, f1dash.Rapido(fonte)
        srv, _ = f1dash.abrir_servidor(0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            ligacao = http.client.HTTPConnection('127.0.0.1', srv.server_address[1], timeout=5)
            ligacao.request('GET', '/rapido')
            resposta = ligacao.getresponse()
            self.assertEqual(resposta.getheader('Content-Type'), 'text/event-stream')
            fonte.versao_rapida, fonte.g = 1, 6
            f1dash.rapido.talvez_publicar('telemetria', agora=100.0)
            linha = b''
            while not linha.startswith(b'data:'):
                linha = resposta.fp.readline()
            self.assertEqual(json.loads(linha[5:]), {'g': 6, 'v': 106})
            ligacao.close()
        finally:
            f1dash.rapido = antigo
            srv.shutdown()
            srv.server_close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
