"""
Benchmark sem interface: compara os 5 algoritmos em muitos labirintos.

Uso:
    python tests/benchmark.py                 # tamanhos padrão, 50 labirintos cada
    python tests/benchmark.py --amostras 200  # mais labirintos por tamanho
    python tests/benchmark.py --ciclos 10     # remove 10 paredes extras (cria ciclos)

Colunas:
    terminou   % de execuções que chegaram ao fim sozinhas
    cobertura  % média das células alcançáveis por onde o robô passou
    mov        média do contador "Mov" da tela (giros + deslocamentos)
    desloc     média de deslocamentos (trocas de célula)
    x DFS      desloc / desloc da DFS no mesmo labirinto

Para os seguidores de parede, que nunca terminam, a execução é interrompida
após um limite de ações; por isso "mov" e "desloc" não fazem sentido para eles.
"""

import argparse
import statistics

from simulacao import ALGORITMOS, executar, labirinto_aleatorio, labirinto_com_ciclos


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tamanhos", type=int, nargs="+", default=[3, 5, 8, 10, 15])
    p.add_argument("--amostras", type=int, default=50)
    p.add_argument("--ciclos", type=int, default=0, help="paredes internas extras a remover")
    args = p.parse_args()

    for n in args.tamanhos:
        titulo = f"Arena {n}x{n} ({n*n} células), {args.amostras} labirintos"
        titulo += f", {args.ciclos} passagens extras" if args.ciclos else ", perfeitos"
        print(f"\n{titulo}")
        print(f"{'algoritmo':22s} {'terminou':>9s} {'cobertura':>10s} {'mov':>8s} {'desloc':>8s} {'x DFS':>6s}")

        resultados = {nome: [] for nome in ALGORITMOS}
        for s in range(args.amostras):
            if args.ciclos:
                arena = labirinto_com_ciclos(n, n, s, args.ciclos)
            else:
                arena = labirinto_aleatorio(n, n, s)
            for nome in ALGORITMOS:
                limite = 2_000_000 if nome in ("BFS",) else 20 * n * n + 2_000
                resultados[nome].append(executar(nome, arena, max_passos=limite))

        base = [r.deslocamentos for r in resultados["DFS (Busca em Lista)"]]
        for nome, rs in resultados.items():
            terminou = sum(r.terminou for r in rs) / len(rs)
            cobertura = statistics.mean(r.cobertura for r in rs)
            if terminou == 1:
                mov = f"{statistics.mean(r.movimentos for r in rs):8.1f}"
                desl = f"{statistics.mean(r.deslocamentos for r in rs):8.1f}"
                razao = statistics.mean(r.deslocamentos / b if b else 1 for r, b in zip(rs, base))
                razao = f"{razao:6.2f}"
            else:
                mov = desl = f"{'-':>8s}"
                razao = f"{'-':>6s}"
            print(f"{nome:22s} {terminou:9.0%} {cobertura:10.0%} {mov} {desl} {razao}")


if __name__ == "__main__":
    main()
