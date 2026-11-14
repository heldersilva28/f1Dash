"""Testes rápidos: tamanhos oficiais, formato 2025 e 2026, e a simulação completa.  python testes/teste_pacotes.py"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from telemetria import pacotes as P          # noqa: E402
from telemetria.estado import Sessao         # noqa: E402
import demo                                   # noqa: E402


def pacote_vazio(fmt, pid):
    cab = P.CABECALHO.pack(fmt, 25, 1, 0, 1, pid, 123, 1.0, 1, 1, 0, 255)
    return cab + bytes(P.tamanho_esperado(fmt, pid) - P.CABECALHO.size)


def main():
    assert P.verificar_tamanhos() == [], P.verificar_tamanhos()
    for fmt in (2025, 2026):
        for pid in P.TAMANHOS_OFICIAIS[fmt]:
            dados = pacote_vazio(fmt, pid)
            if pid == 3:
                dados = dados[:P.CABECALHO.size] + b'FTLP' + struct.pack('<Bf', 0, 100.0).ljust(12, b'\0')
            r = P.descodificar(dados)
            assert r is not None, (fmt, pid)
    print('[ok] todos os pacotes 2025 e 2026 descodificam com os tamanhos oficiais')
    for modo in ('corrida', 'qualificacao', 'treinos'):
        sim = demo.criar(modo)
        s = Sessao()
        for _ in range(200):
            sim.passo(0.05)
            for p in sim.pacotes():
                r = P.descodificar(p)
                assert r is not None
                s.receber(*r)
        f = s.fotografia()
        assert f['pronto'] and f['ecra'] == modo, f.get('ecra')
        assert f['eu']['codigo'] == 'NOR' and f['eu']['cor'] == '#FF8000'
        print(f'[ok] {modo}: {len(f["carros"])} carros, tu és {f["eu"]["codigo"]} P{f["eu"]["pos"]} com a cor {f["eu"]["cor"]}')


if __name__ == '__main__':
    main()
