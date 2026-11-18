"""F1 Dash — painel para o segundo monitor (EA SPORTS F1 25 / 2026 Season Pack, e também F1 2020).

Uso:
    python f1dash.py                 # escuta o jogo na porta UDP 20777 e abre o painel em http://localhost:8080
    python f1dash.py --demo corrida  # sem jogo: simula uma corrida (ou qualificacao / treinos)
"""
import sys

if sys.version_info < (3, 10):
    print('[ERRO] O F1 Dash precisa do Python 3.10 ou mais recente (tens o %d.%d).' % sys.version_info[:2])
    print('       Instala a versão mais recente em https://www.python.org/downloads/')
    sys.exit(1)

import argparse
import json
import os
import socket
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


class Rapido:
    """Canal rápido: os poucos valores que mudam a cada pacote (mudança, velocidade, rotações, luzes, delta), enviados
    logo que chegam do jogo, até 60 vezes por segundo. Publica a partir do fio que recebe os pacotes UDP, por isso
    não depende da precisão dos temporizadores do sistema."""
    MINIMO = 1 / 120       # proteção contra rajadas; o ritmo real é o do jogo (um envio por pacote de telemetria)
    SEM_TELEMETRIA = 0.25  # se a telemetria deixar de chegar, publica com os pacotes de voltas

    def __init__(self, fonte=None):
        self.fonte = fonte
        self.cond = threading.Condition()
        self.versao = 0
        self.corpo = None            # nada até chegar o primeiro pacote (um vazio apagaria o ecrã por um instante)
        self.ultimo = -1e9
        self.visto = -1
        self.ultima_telemetria = -1e9

    def talvez_publicar(self, nome='telemetria', agora=None):
        """Chamado a cada pacote de voltas ou de telemetria. Publica uma vez por frame do jogo: no pacote de
        telemetria (mudança, velocidade, rotações, luzes), que chega no mesmo frame do pacote de voltas."""
        fonte = self.fonte or sessao
        agora = time.monotonic() if agora is None else agora
        if nome == 'telemetria':
            self.ultima_telemetria = agora
        elif agora - self.ultima_telemetria < self.SEM_TELEMETRIA:
            return False
        if fonte.versao_rapida == self.visto or agora - self.ultimo < self.MINIMO:
            return False
        try:
            dados = fonte.rapido()
        except Exception:     # nunca deixa um valor estranho parar a receção dos pacotes
            return False
        self.visto = fonte.versao_rapida
        if dados is None:
            return False
        self.ultimo = agora
        corpo = json.dumps(dados, separators=(',', ':')).encode()
        with self.cond:
            self.corpo = corpo
            self.versao += 1
            self.cond.notify_all()
        return True

    def esperar(self, versao):
        with self.cond:
            self.cond.wait_for(lambda: self.versao != versao, timeout=2)
            return self.versao, self.corpo


rapido = Rapido()


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


def abrir_udp(porta):
    """Abre a porta UDP do jogo só para este programa. Sem SO_REUSEADDR: no Windows e no Linux essa opção deixava
    um segundo painel abrir a mesma porta, e os dois ficavam a dividir os pacotes sem avisar."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if sys.platform == 'win32' and hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        sock.bind(('0.0.0.0', porta))
    except OSError:
        sock.close()
        raise
    return sock


def escutar_udp(porta):
    try:
        sock = abrir_udp(porta)
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
        if r[1] in ('voltas', 'telemetria'):
            rapido.talvez_publicar(r[1])


class Pedido(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith('/stream'):
            return self._stream(difusor)
        if self.path.startswith('/rapido'):
            return self._stream(rapido)
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

    def do_POST(self):
        """Definições que o servidor tem de saber (por agora, as voltas da corrida escolhidas à mão)."""
        if self.path != '/definicoes':
            return self.send_error(404)
        try:
            n = int(self.headers.get('Content-Length') or 0)
            if not 0 < n <= 1000:
                raise ValueError
            voltas = json.loads(self.rfile.read(n)).get('voltas')
            if voltas is not None and (isinstance(voltas, bool) or not isinstance(voltas, int) or not 1 <= voltas <= 99):
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            return self.send_error(400, 'Pedido inválido')
        if not sessao.definir_voltas(voltas):
            return self.send_error(409, 'Ainda não há sessão do jogo')
        difusor.atualizar()          # os ecrãs ligados veem a mudança já
        self._enviar_json(b'{"ok": true}')

    def _enviar_json(self, corpo):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _stream(self, fonte):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        versao = -1
        try:
            while True:
                nova, corpo = fonte.esperar(versao)
                if nova == versao or corpo is None:
                    self.wfile.write(b': ainda aqui\n\n')     # sem dados novos: só para saber se o ecrã ainda está ligado
                else:
                    self.wfile.write(b'data: ' + corpo + b'\n\n')
                versao = nova
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


class Servidor(ThreadingHTTPServer):
    daemon_threads = True
    # no Windows, SO_REUSEADDR deixa abrir uma porta que outro programa já está a usar
    allow_reuse_address = sys.platform != 'win32'

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return   # um browser fechou ou recarregou a página: normal, não é um erro
        super().handle_error(request, client_address)


def abrir_servidor(porta, tentativas=10):
    """Abre o painel na porta pedida; se estiver ocupada, tenta as seguintes."""
    for p in range(porta, porta + tentativas):
        try:
            return Servidor(('0.0.0.0', p), Pedido), p
        except OSError:
            continue
    return None, None


def main():
    ap = argparse.ArgumentParser(description='Painel F1 para o segundo monitor')
    ap.add_argument('--porta-udp', type=int, default=20777)
    ap.add_argument('--porta-web', type=int, default=8080)
    ap.add_argument('--demo-formato', type=int, choices=[2020, 2026], default=2026,
                    help='formato UDP da demonstração: 2026 (F1 25) ou 2020 (F1 2020)')
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
        threading.Thread(target=demo.correr, args=(a.demo, a.porta_udp), kwargs={'formato': a.demo_formato},
                         daemon=True).start()
        print(f'[OK] Modo demonstração: {a.demo} (formato {a.demo_formato})')

    srv, porta = abrir_servidor(a.porta_web)
    if not srv:
        print(f'[ERRO] As portas {a.porta_web} a {a.porta_web + 9} estão todas ocupadas.')
        print('       Fecha a outra janela do F1 Dash ou escolhe outra porta com --porta-web.')
        sys.exit(1)
    if porta != a.porta_web:
        print(f'[aviso] A porta {a.porta_web} está ocupada (outra janela do F1 Dash?). Uso a {porta}.')
    url = f'http://localhost:{porta}'
    print(f'[OK] Painel em {url}  (no segundo monitor carrega F11 para ecrã inteiro)')
    ip = ip_da_rede()
    if ip and not ip.startswith('127.'):
        print(f'[OK] No tablet ou telemóvel (mesma rede Wi-Fi): http://{ip}:{porta}')
    if not a.sem_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nAté à próxima!')


if __name__ == '__main__':
    main()
