"""F1 Dash — painel para o segundo monitor (EA SPORTS F1 25 / 2026 Season Pack).

Uso:
    python f1dash.py                 # escuta o jogo na porta UDP 20777 e abre o painel em http://localhost:8080
    python f1dash.py --demo corrida  # sem jogo: simula uma corrida (ou qualificacao / treinos)
"""
import argparse
import json
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telemetria import pacotes
from telemetria.estado import Sessao

PASTA_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
TIPOS = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
         '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml'}

sessao = Sessao()
estatisticas = {'pacotes': 0, 'ignorados': 0, 'formatos': set()}


class Difusor:
    """Calcula o estado uma vez a cada 0,2 s e partilha-o com todos os ecrãs ligados (PC, tablet, telemóvel)."""
    INTERVALO = 0.2

    def __init__(self):
        self.cond = threading.Condition()
        self.versao = 0
        self.corpo = b'{}'
        self.ultimo_erro = None

    def atualizar(self, fonte=None):
        fonte = fonte or sessao
        try:
            foto = fonte.fotografia()
            foto['estatisticas'] = {'pacotes': estatisticas['pacotes'], 'ignorados': estatisticas['ignorados']}
            corpo = json.dumps(foto, ensure_ascii=False).encode()
            self.ultimo_erro = None
        except Exception as e:  # nunca deixa um erro de cálculo calar o painel: avisa e mantém o último estado
            texto = f'{type(e).__name__}: {e}'
            if texto != self.ultimo_erro:
                print('[erro] não consegui preparar os dados do painel:')
                traceback.print_exc()
                self.ultimo_erro = texto
            corpo = None
        with self.cond:
            if corpo is not None:
                self.corpo = corpo
            self.versao += 1
            self.cond.notify_all()

    def correr(self):
        while True:
            self.atualizar()
            time.sleep(self.INTERVALO)

    def esperar(self, versao):
        with self.cond:
            self.cond.wait_for(lambda: self.versao != versao, timeout=5)
            return self.versao, self.corpo


difusor = Difusor()


def ip_da_rede():
    """IP deste PC na rede local, para abrir o painel num tablet ou telemóvel. Não envia nada pela rede."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def escutar_udp(porta):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(('0.0.0.0', porta))
    except OSError as e:
        print(f'[ERRO] Não consegui abrir a porta UDP {porta}: {e}')
        print('       Fecha outros programas de telemetria ou escolhe outra porta com --porta-udp.')
        os._exit(1)
    print(f'[OK] À escuta do jogo na porta UDP {porta}')
    while True:
        dados, _ = sock.recvfrom(4096)
        try:
            r = pacotes.descodificar(dados)
        except Exception:
            r = None
        if r is None:
            estatisticas['ignorados'] += 1
            continue
        estatisticas['pacotes'] += 1
        estatisticas['formatos'].add(r[0]['formato'])
        try:
            sessao.receber(*r)
        except Exception as e:  # um pacote estranho nunca deve parar o painel
            print('[aviso] pacote ignorado:', e)


class Pedido(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith('/stream'):
            return self._stream()
        if self.path.startswith('/dados'):
            return self._enviar_json(difusor.corpo)
        caminho = self.path.split('?')[0]
        if caminho == '/':
            caminho = '/index.html'
        f = os.path.normpath(os.path.join(PASTA_WEB, caminho.lstrip('/')))
        if not f.startswith(PASTA_WEB + os.sep) or not os.path.isfile(f):
            self.send_error(404)
            return
        with open(f, 'rb') as fh:
            corpo = fh.read()
        self.send_response(200)
        self.send_header('Content-Type', TIPOS.get(os.path.splitext(f)[1], 'application/octet-stream'))
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Content-Length', str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _enviar_json(self, corpo):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        versao = -1
        try:
            while True:
                versao, corpo = difusor.esperar(versao)
                self.wfile.write(b'data: ' + corpo + b'\n\n')
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


class Servidor(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return   # um browser fechou ou recarregou a página: normal, não é um erro
        super().handle_error(request, client_address)


def main():
    ap = argparse.ArgumentParser(description='Painel F1 para o segundo monitor')
    ap.add_argument('--porta-udp', type=int, default=20777)
    ap.add_argument('--porta-web', type=int, default=8080)
    ap.add_argument('--demo', choices=['corrida', 'qualificacao', 'treinos'],
                    help='simula uma sessão sem o jogo (para experimentar o painel)')
    ap.add_argument('--sem-browser', action='store_true', help='não abrir o browser automaticamente')
    a = ap.parse_args()

    erros = pacotes.verificar_tamanhos()
    if erros:
        print('[ERRO] Estruturas UDP não batem com a especificação:', erros)
        sys.exit(1)

    threading.Thread(target=escutar_udp, args=(a.porta_udp,), daemon=True).start()
    threading.Thread(target=difusor.correr, daemon=True).start()
    if a.demo:
        sessao.guardar = False      # a simulação não pode estragar o que o painel aprendeu das tuas corridas
        sessao.memoria = {}
        import demo
        threading.Thread(target=demo.correr, args=(a.demo, a.porta_udp), daemon=True).start()
        print(f'[OK] Modo demonstração: {a.demo}')

    srv = Servidor(('0.0.0.0', a.porta_web), Pedido)
    url = f'http://localhost:{a.porta_web}'
    print(f'[OK] Painel em {url}  (no segundo monitor carrega F11 para ecrã inteiro)')
    ip = ip_da_rede()
    if ip and not ip.startswith('127.'):
        print(f'[OK] No tablet ou telemóvel (mesma rede Wi-Fi): http://{ip}:{a.porta_web}')
    if not a.sem_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nAté à próxima!')


if __name__ == '__main__':
    main()
