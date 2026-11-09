"""
Testes que DOCUMENTAM onde os seguidores de parede falham.

Estes testes passam justamente porque a falha acontece: eles servem como
exemplos mínimos e reproduzíveis para usar em aula. Os marcados com
`xfail` mostram o comportamento que "gostaríamos" de ter e que esses
algoritmos não conseguem entregar.

Lembrete da lógica (veja simuladorv2.py):
  * Seguidor burro: prioridade frente -> direita -> esquerda -> RÉ,
    sem nenhuma memória.
  * Seguidor de parede: mesma prioridade, mas marca cada célula de onde sai
    como "completa" e evita entrar em células completas. A ré continua
    sendo permitida (e é feita sem girar o robô).
  * Nenhum dos dois tem condição de parada (`while True` sem `break`).
"""

import pytest

from simulacao import (
    alcancaveis, arena_aberta, arena_de_caminhos, arena_fechada, executar,
    labirinto_aleatorio, labirinto_com_ciclos,
)

BURRO = "Seg. Parede (Burro)"
SEGUIDOR = "Seguidor de Parede"


def _ciclo_final(res, janela=200):
    """Conjunto de células visitadas nas últimas `janela` ações."""
    return set(res.trajeto[-janela:])


# --------------------------------------------------------------------------
# Seguidor de parede "burro"
# --------------------------------------------------------------------------

def test_burro_fica_preso_num_beco_sem_saida():
    """
        (0,0) ── (1,0) ── (2,0)   <- beco sem saída
                   │
                 (1,1)            <- nunca é visitada

    Em (1,0) o robô prefere a frente e entra no beco. No beco ele dá ré,
    mas a ré não gira o robô: ele volta para (1,0) ainda olhando para o beco,
    e a regra "frente primeiro" o manda de volta. Vai-e-vem eterno.
    """
    arena = arena_de_caminhos(2, 3, [[(0, 0), (1, 0), (2, 0)], [(1, 0), (1, 1)]])
    res = executar(BURRO, arena, max_passos=1_000)

    assert not res.terminou
    assert (1, 1) not in res.cobertas
    assert _ciclo_final(res) == {(1, 0), (2, 0)}


def test_burro_gira_para_sempre_em_um_ciclo():
    """
        (0,0) ── (1,0)
          │        │
        (0,1) ── (1,1)
          │
        (0,2)              <- nunca é visitada

    Sem becos, o robô dá voltas no quadrado: em (0,1) a direita (Norte)
    tem prioridade sobre a esquerda (Sul), então (0,2) nunca é escolhida.
    """
    arena = arena_de_caminhos(3, 2, [
        [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)],
        [(0, 1), (0, 2)],
    ])
    res = executar(BURRO, arena, max_passos=1_000)

    assert not res.terminou
    assert (0, 2) not in res.cobertas
    assert _ciclo_final(res) == {(0, 0), (1, 0), (1, 1), (0, 1)}


@pytest.mark.parametrize("semente", range(20))
def test_burro_sempre_termina_em_vai_e_vem_no_labirinto_aleatorio(semente):
    """Labirintos aleatórios são perfeitos: sempre há becos, então sempre trava."""
    res = executar(BURRO, labirinto_aleatorio(8, 8, semente), max_passos=3_000)
    assert not res.terminou
    assert len(_ciclo_final(res)) == 2


def test_burro_com_inicio_isolado_fica_parado_para_sempre():
    res = executar(BURRO, arena_fechada(3, 3), max_passos=300)
    assert not res.terminou
    assert res.deslocamentos == 0 and res.paradas == 300


@pytest.mark.xfail(strict=True, reason="sem memória, o seguidor burro não explora o labirinto")
@pytest.mark.parametrize("semente", range(3))
def test_burro_deveria_explorar_labirinto_perfeito(semente):
    arena = labirinto_aleatorio(6, 6, semente)
    res = executar(BURRO, arena, max_passos=5_000)
    assert res.terminou and res.cobertas == alcancaveis(arena)


# --------------------------------------------------------------------------
# Seguidor de parede (com marcação de "completos")
# --------------------------------------------------------------------------

def test_seguidor_resolve_o_vai_e_vem_do_burro():
    """A memória de células completas evita voltar para o beco."""
    arena = arena_de_caminhos(2, 3, [[(0, 0), (1, 0), (2, 0)], [(1, 0), (1, 1)]])
    res = executar(SEGUIDOR, arena, max_passos=1_000)
    assert res.cobertas == alcancaveis(arena)


def test_seguidor_trava_quando_precisa_voltar_fazendo_curva():
    """
        (0,0) ── (1,0)
          │        │
        (0,1)    (1,1)     (sem passagem entre (0,1) e (1,1))

    Caminho: (0,0) -> (1,0) -> vira à direita -> (1,1), que é beco.
    A ré leva o robô de volta a (1,0), mas ele continua olhando para o Sul.
    Em (1,0): frente = (1,1) completa, direita = (0,0) completa,
    esquerda = borda, e atrás (Norte) também é borda -> a ré não sai do lugar.
    O robô fica parado para sempre e (0,1) nunca é visitada.
    """
    arena = arena_de_caminhos(2, 2, [[(0, 1), (0, 0), (1, 0), (1, 1)]])
    res = executar(SEGUIDOR, arena, max_passos=500)

    assert not res.terminou
    assert (0, 1) not in res.cobertas
    assert res.trajeto[-1] == (1, 0)
    assert set(res.trajeto[-100:]) == {(1, 0)}  # parado


def test_seguidor_cobre_arena_aberta_mas_nunca_termina():
    """Mesmo quando já passou por tudo, não há condição de parada."""
    arena = arena_aberta(5, 5)
    res = executar(SEGUIDOR, arena, max_passos=2_000)

    assert res.cobertas == alcancaveis(arena)
    assert not res.terminou
    assert res.paradas > 1_900  # passa quase todo o tempo parado
    assert res.trajeto[-1] != (0, 0)  # e não volta para o início


@pytest.mark.parametrize("semente", range(20))
def test_seguidor_sempre_acaba_parado_no_labirinto_aleatorio(semente):
    res = executar(SEGUIDOR, labirinto_aleatorio(8, 8, semente), max_passos=3_000)
    assert not res.terminou
    assert len(_ciclo_final(res)) == 1


@pytest.mark.parametrize("semente", range(10))
def test_seguidor_tambem_trava_com_ciclos(semente):
    res = executar(SEGUIDOR, labirinto_com_ciclos(8, 8, semente, 10), max_passos=3_000)
    assert not res.terminou
    assert len(_ciclo_final(res)) == 1


@pytest.mark.xfail(strict=True, reason="a ré sem giro não desfaz curvas: o robô trava antes de cobrir tudo")
@pytest.mark.parametrize("semente", range(3))
def test_seguidor_deveria_explorar_labirinto_perfeito(semente):
    arena = labirinto_aleatorio(6, 6, semente)
    res = executar(SEGUIDOR, arena, max_passos=5_000)
    assert res.cobertas == alcancaveis(arena)
