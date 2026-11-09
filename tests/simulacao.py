"""
Utilitários para executar os algoritmos do simulador SEM interface gráfica.

A ideia é simples: todos os algoritmos chamam `esperar_tecla(...)` depois de
cada ação do robô (é ali que a tela é desenhada e o programa espera o usuário).
Durante os testes, essa função é substituída por um "observador" que:

  * registra a posição do robô após cada ação;
  * confere que o robô nunca atravessou uma parede nem saiu da arena;
  * interrompe a execução depois de um número máximo de ações, para que
    algoritmos que nunca terminam (laços infinitos) não travem os testes.

Este módulo é usado tanto pelos testes (pytest) quanto pelo benchmark.py.
"""

import os
import random
import sys
from collections import deque

# Pygame sem janela: precisa ser definido ANTES de importar o pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import pygame  # noqa: E402

pygame.init()

import simuladorv2 as sim  # noqa: E402

# Nome exibido no menu -> função
ALGORITMOS = {
    "Seg. Parede (Burro)": sim.seguidor_parede_burro,
    "Seguidor de Parede": sim.seguidor_parede,
    "DFS (Busca em Lista)": sim.dfs_lista,
    "DFS (Recursivo)": sim.dfs_recursivo,
    "BFS": sim.bfs,
}

DESLOC = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
OPOSTA = {"N": "S", "S": "N", "E": "W", "W": "E"}


class LimiteDePassos(Exception):
    """Lançada quando o algoritmo excede o número máximo de ações."""


# ---------------------------------------------------------------------------
# Construção de arenas
# ---------------------------------------------------------------------------

def arena_fechada(linhas, colunas):
    """Arena com TODAS as paredes internas levantadas (cada célula isolada)."""
    arena = sim.Arena(linhas, colunas, 40)
    for y in range(linhas):
        for x in range(colunas):
            arena.grid[y][x] = {"N": 1, "E": 1, "S": 1, "W": 1}
    return arena


def arena_aberta(linhas, colunas):
    """Arena sem paredes internas (é o estado inicial do modo Manual)."""
    return sim.Arena(linhas, colunas, 40)


def abrir(arena, a, b):
    """Remove a parede entre duas células vizinhas a=(x,y) e b=(x,y)."""
    _definir_parede(arena, a, b, 0)


def fechar(arena, a, b):
    """Levanta a parede entre duas células vizinhas a=(x,y) e b=(x,y)."""
    _definir_parede(arena, a, b, 1)


def _definir_parede(arena, a, b, valor):
    (ax, ay), (bx, by) = a, b
    for d, (dx, dy) in DESLOC.items():
        if (ax + dx, ay + dy) == (bx, by):
            arena.grid[ay][ax][d] = valor
            arena.grid[by][bx][OPOSTA[d]] = valor
            return
    raise ValueError(f"{a} e {b} não são vizinhas")


def arena_de_caminhos(linhas, colunas, caminhos):
    """
    Cria uma arena fechada e abre passagens ao longo de cada caminho.
    Ex.: [[(0,0), (1,0), (1,1)]] abre (0,0)-(1,0) e (1,0)-(1,1).
    """
    arena = arena_fechada(linhas, colunas)
    for caminho in caminhos:
        for a, b in zip(caminho, caminho[1:]):
            abrir(arena, a, b)
    return arena


def labirinto_aleatorio(linhas, colunas, semente):
    """Labirinto perfeito gerado pelo próprio simulador (modo Aleatório)."""
    random.seed(semente)
    arena = sim.Arena(linhas, colunas, 40)
    arena.gerar_labirinto_aleatorio()
    return arena


def labirinto_com_ciclos(linhas, colunas, semente, extras):
    """Labirinto perfeito + `extras` paredes internas removidas (cria ciclos)."""
    arena = labirinto_aleatorio(linhas, colunas, semente)
    rng = random.Random(semente * 7919 + 1)
    candidatas = []
    for y in range(linhas):
        for x in range(colunas):
            if x + 1 < colunas and arena.grid[y][x]["E"]:
                candidatas.append(((x, y), (x + 1, y)))
            if y + 1 < linhas and arena.grid[y][x]["S"]:
                candidatas.append(((x, y), (x, y + 1)))
    rng.shuffle(candidatas)
    for a, b in candidatas[:extras]:
        abrir(arena, a, b)
    return arena


# ---------------------------------------------------------------------------
# Consultas sobre a arena
# ---------------------------------------------------------------------------

def vizinhos_abertos(arena, celula):
    x, y = celula
    for d, (dx, dy) in DESLOC.items():
        if not arena.grid[y][x][d]:
            yield (x + dx, y + dy)


def distancias(arena, origem=(0, 0)):
    """Distância (em células) de `origem` até cada célula alcançável."""
    dist = {origem: 0}
    fila = deque([origem])
    while fila:
        atual = fila.popleft()
        for v in vizinhos_abertos(arena, atual):
            if v not in dist:
                dist[v] = dist[atual] + 1
                fila.append(v)
    return dist


def alcancaveis(arena, origem=(0, 0)):
    return set(distancias(arena, origem))


def numero_de_passagens(arena):
    total = 0
    for y in range(arena.linhas):
        for x in range(arena.colunas):
            total += (not arena.grid[y][x]["E"]) and x + 1 < arena.colunas
            total += (not arena.grid[y][x]["S"]) and y + 1 < arena.linhas
    return total


# ---------------------------------------------------------------------------
# Execução sem interface
# ---------------------------------------------------------------------------

class ConjuntoComOrdem(set):
    """`set` que lembra a ordem em que cada elemento foi adicionado pela 1ª vez."""

    def __init__(self):
        super().__init__()
        self.ordem = []

    def add(self, item):
        if item not in self:
            self.ordem.append(item)
        super().add(item)


class Resultado:
    def __init__(self):
        self.terminou = False
        self.passos = 0          # chamadas a esperar_tecla (ações observadas)
        self.deslocamentos = 0   # ações que mudaram a célula do robô
        self.giros = 0           # ações que só mudaram a direção
        self.paradas = 0         # ações que não mudaram nada (robô "parado")
        self.trajeto = []        # posição após cada ação
        self.ordem_visita = []   # ordem de 1ª inserção em `visitados`
        self.cobertas = set()    # células por onde o robô passou
        self.robo = None
        self.arena = None
        self.movimentos = 0      # contador "Mov" exibido na tela

    @property
    def cobertura(self):
        total = len(alcancaveis(self.arena))
        return len(self.cobertas) / total if total else 1.0

    def __repr__(self):
        return (f"Resultado(terminou={self.terminou}, mov={self.movimentos}, "
                f"desloc={self.deslocamentos}, giros={self.giros}, "
                f"cobertura={self.cobertura:.0%})")


def resetar_estado_global():
    sim.visitados.clear()
    sim.completos.clear()
    sim.movimentos_atuais.clear()
    sim.proximos_bfs.clear()
    sim.modo_automatico = True
    sim.busca_concluida = False


def executar(algoritmo, arena, max_passos=20_000):
    """
    Executa `algoritmo` a partir de (0,0) virado para Leste — exatamente como
    o simulador faz — e devolve um `Resultado`.
    """
    if isinstance(algoritmo, str):
        algoritmo = ALGORITMOS[algoritmo]

    resetar_estado_global()
    sim.algoritmo_atual = algoritmo.__name__

    # Troca o set global por um que registra a ordem de visita.
    original_visitados = sim.visitados
    registro = ConjuntoComOrdem()
    sim.visitados = registro

    robo = sim.Robo(arena, 0, 0)
    res = Resultado()
    res.robo, res.arena = robo, arena
    res.cobertas.add((0, 0))
    estado = {"pos": (robo.x, robo.y), "dir": robo.direcao}

    def observador(robo_, arena_, tela_):
        res.passos += 1
        pos_ant, dir_ant = estado["pos"], estado["dir"]
        pos = (robo_.x, robo_.y)

        assert 0 <= robo_.x < arena_.colunas and 0 <= robo_.y < arena_.linhas, \
            f"robô saiu da arena: {pos}"
        if pos != pos_ant:
            assert pos in set(vizinhos_abertos(arena_, pos_ant)), \
                f"robô atravessou parede: {pos_ant} -> {pos}"
            res.deslocamentos += 1
        elif robo_.direcao != dir_ant:
            res.giros += 1
        else:
            res.paradas += 1

        estado["pos"], estado["dir"] = pos, robo_.direcao
        res.trajeto.append(pos)
        res.cobertas.add(pos)
        if res.passos >= max_passos:
            raise LimiteDePassos()

    original_esperar = sim.esperar_tecla
    sim.esperar_tecla = observador
    try:
        algoritmo(robo, arena, None)
        res.terminou = True
    except LimiteDePassos:
        res.terminou = False
    finally:
        sim.esperar_tecla = original_esperar
        sim.visitados = original_visitados
        original_visitados.clear()
        original_visitados.update(registro)

    res.ordem_visita = list(registro.ordem)
    res.movimentos = robo.movimentos
    return res
