"""
Testes dos algoritmos que FUNCIONAM: DFS (lista), DFS (recursivo) e BFS.

Para cada um verificamos que:
  * termina (não entra em laço infinito);
  * visita todas as células alcançáveis a partir de (0,0);
  * nunca atravessa paredes (checado a cada ação pelo observador);
  * volta para o ladrilho inicial (0,0).
E algumas propriedades específicas de cada busca.
"""

import pytest

from simulacao import (
    ALGORITMOS, alcancaveis, arena_aberta, arena_de_caminhos,
    arena_fechada, distancias, executar, fechar, labirinto_aleatorio,
    labirinto_com_ciclos, sim,
)

EXPLORADORES = ["DFS (Busca em Lista)", "DFS (Recursivo)", "BFS"]


def _cenarios():
    """Arenas variadas: perfeitas, com ciclos, abertas, corredores e casos-limite."""
    cenarios = []
    for s in range(8):
        cenarios.append((f"perfeito-6x6-s{s}", lambda s=s: labirinto_aleatorio(6, 6, s)))
        cenarios.append((f"ciclos-7x5-s{s}", lambda s=s: labirinto_com_ciclos(5, 7, s, 6)))
    cenarios += [
        ("perfeito-15x15", lambda: labirinto_aleatorio(15, 15, 123)),
        ("aberta-5x5", lambda: arena_aberta(5, 5)),
        ("aberta-3x8", lambda: arena_aberta(3, 8)),
        ("corredor-1x6", lambda: arena_aberta(1, 6)),
        ("coluna-6x1", lambda: arena_aberta(6, 1)),
        ("inicio-isolado", lambda: arena_fechada(4, 4)),
    ]
    return cenarios


CENARIOS = _cenarios()


@pytest.mark.parametrize("algoritmo", EXPLORADORES)
@pytest.mark.parametrize("nome,fabrica", CENARIOS, ids=[c[0] for c in CENARIOS])
def test_explora_tudo_e_volta_ao_inicio(algoritmo, nome, fabrica):
    arena = fabrica()
    res = executar(algoritmo, arena, max_passos=200_000)

    assert res.terminou, f"{algoritmo} não terminou em {nome}"
    assert res.cobertas == alcancaveis(arena)
    assert set(sim.visitados) == alcancaveis(arena)
    assert (res.robo.x, res.robo.y) == (0, 0)
    assert res.paradas == 0  # toda ação mudou posição ou direção


def test_celulas_inalcancaveis_sao_ignoradas():
    """No modo Manual é possível isolar regiões: os algoritmos não as visitam."""
    arena = arena_aberta(4, 4)
    for y in range(4):
        fechar(arena, (1, y), (2, y))  # parede vertical dividindo a arena
    for algoritmo in EXPLORADORES:
        res = executar(algoritmo, arena)
        assert res.terminou
        assert res.cobertas == {(x, y) for x in range(2) for y in range(4)}


# --------------------------------------------------------------------------
# DFS
# --------------------------------------------------------------------------

@pytest.mark.parametrize("semente", range(15))
@pytest.mark.parametrize("algoritmo", ["DFS (Busca em Lista)", "DFS (Recursivo)"])
def test_dfs_percorre_cada_passagem_exatamente_duas_vezes(algoritmo, semente):
    """
    Em um labirinto perfeito com N células existem N-1 passagens. A DFS passa
    por cada uma duas vezes (ida e volta): 2*(N-1) deslocamentos, que é o
    MÍNIMO possível para visitar tudo e voltar ao início.
    """
    arena = labirinto_aleatorio(8, 8, semente)
    res = executar(algoritmo, arena)
    assert res.deslocamentos == 2 * (64 - 1)


@pytest.mark.parametrize("semente", range(15))
def test_dfs_com_ciclos_usa_apenas_uma_arvore_geradora(semente):
    """Com ciclos, a DFS não repete células: continua 2*(N-1) deslocamentos."""
    arena = labirinto_com_ciclos(6, 6, semente, 8)
    res = executar("DFS (Busca em Lista)", arena)
    assert res.deslocamentos == 2 * (36 - 1)


@pytest.mark.parametrize("semente", range(15))
def test_dfs_lista_e_recursiva_fazem_o_mesmo_trajeto(semente):
    """As duas versões têm a mesma prioridade (frente, direita, esquerda)."""
    arena = labirinto_com_ciclos(6, 7, semente, semente % 5)
    lista = executar("DFS (Busca em Lista)", arena)
    recursiva = executar("DFS (Recursivo)", arena)
    assert lista.ordem_visita == recursiva.ordem_visita
    assert lista.trajeto == recursiva.trajeto[: len(lista.trajeto)]
    # A recursiva desfaz o último giro no início; a de lista para antes.
    assert recursiva.movimentos - lista.movimentos in (0, 1)


def test_dfs_prioridade_frente_direita_esquerda():
    """
    Cruzamento em (1,1) com saídas para frente, direita e esquerda.
    O robô chega vindo do Oeste (virado para Leste) e deve explorar
    Leste (frente) -> Sul (direita) -> Norte (esquerda).
    """
    arena = arena_de_caminhos(3, 3, [
        [(0, 0), (0, 1), (1, 1)],  # chega em (1,1) vindo de (0,1)
        [(1, 1), (2, 1)],          # frente
        [(1, 1), (1, 2)],          # direita
        [(1, 1), (1, 0)],          # esquerda
    ])
    res = executar("DFS (Recursivo)", arena)
    assert res.ordem_visita[:6] == [(0, 0), (0, 1), (1, 1), (2, 1), (1, 2), (1, 0)]


def test_dfs_lista_guarda_movimentos_na_pilha():
    """A pilha guarda F/D/E e é desfeita na volta; termina vazia (ou só com o 1º giro)."""
    arena = labirinto_aleatorio(5, 5, 3)
    executar("DFS (Busca em Lista)", arena)
    assert sim.movimentos_atuais in ([], ["D"])


def test_dfs_recursivo_suporta_maior_arena_do_menu():
    """15x15 = 225 níveis de recursão no pior caso, abaixo do limite do Python (1000)."""
    corredor = [(x if y % 2 == 0 else 14 - x, y) for y in range(15) for x in range(15)]
    arena = arena_de_caminhos(15, 15, [corredor])  # serpentina: profundidade máxima
    res = executar("DFS (Recursivo)", arena, max_passos=200_000)
    assert res.terminou and len(res.cobertas) == 225


# --------------------------------------------------------------------------
# BFS
# --------------------------------------------------------------------------

@pytest.mark.parametrize("semente", range(15))
@pytest.mark.parametrize("ciclos", [0, 8])
def test_bfs_visita_em_ordem_de_distancia(semente, ciclos):
    """Propriedade que define a BFS: as células são visitadas em 'camadas'."""
    arena = labirinto_com_ciclos(7, 7, semente, ciclos)
    res = executar("BFS", arena, max_passos=200_000)
    dist = distancias(arena)
    camadas = [dist[c] for c in res.ordem_visita]
    assert camadas == sorted(camadas)


@pytest.mark.parametrize("semente", range(15))
def test_bfs_anda_pelo_menos_tanto_quanto_a_dfs(semente):
    """
    Num labirinto perfeito, 2*(N-1) é o mínimo para cobrir tudo e voltar;
    a DFS atinge esse mínimo, então a BFS nunca pode andar menos.
    """
    arena = labirinto_aleatorio(8, 8, semente)
    dfs = executar("DFS (Busca em Lista)", arena)
    bfs = executar("BFS", arena, max_passos=200_000)
    assert bfs.deslocamentos >= dfs.deslocamentos


def test_bfs_fica_muito_mais_cara_em_arenas_grandes():
    """Em 15x15 a BFS física anda várias vezes mais que a DFS (ver benchmark.py)."""
    total_dfs = total_bfs = 0
    for s in range(5):
        arena = labirinto_aleatorio(15, 15, s)
        total_dfs += executar("DFS (Busca em Lista)", arena).deslocamentos
        total_bfs += executar("BFS", arena, max_passos=500_000).deslocamentos
    assert total_bfs > 3 * total_dfs


def test_bfs_em_corredor_reto_empata_com_dfs():
    """Sem bifurcações não há 'idas e vindas' entre ramos: BFS = DFS."""
    arena = arena_aberta(1, 8)
    dfs = executar("DFS (Busca em Lista)", arena)
    bfs = executar("BFS", arena)
    assert bfs.deslocamentos == dfs.deslocamentos == 14


def test_todos_os_algoritmos_estao_no_menu():
    assert set(ALGORITMOS.values()) == {
        sim.seguidor_parede_burro, sim.seguidor_parede,
        sim.dfs_lista, sim.dfs_recursivo, sim.bfs,
    }
