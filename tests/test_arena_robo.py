"""Testes das peças básicas: a Arena (grid de paredes) e o Robo (movimentos)."""

import pytest

from simulacao import (
    abrir, alcancaveis, arena_aberta, arena_fechada, labirinto_aleatorio,
    numero_de_passagens, sim,
)

TAMANHOS = [(3, 3), (5, 5), (4, 9), (15, 15)]


# --------------------------------------------------------------------------
# Arena
# --------------------------------------------------------------------------

@pytest.mark.parametrize("linhas,colunas", TAMANHOS)
def test_arena_nova_tem_bordas_fechadas_e_interior_aberto(linhas, colunas):
    arena = arena_aberta(linhas, colunas)
    for y in range(linhas):
        for x in range(colunas):
            c = arena.grid[y][x]
            assert c["N"] == (y == 0)
            assert c["S"] == (y == linhas - 1)
            assert c["W"] == (x == 0)
            assert c["E"] == (x == colunas - 1)


def _paredes_consistentes(arena):
    """A parede E de uma célula é a W da vizinha; a S é a N da de baixo."""
    for y in range(arena.linhas):
        for x in range(arena.colunas):
            c = arena.grid[y][x]
            if x + 1 < arena.colunas:
                assert c["E"] == arena.grid[y][x + 1]["W"], (x, y)
            if y + 1 < arena.linhas:
                assert c["S"] == arena.grid[y + 1][x]["N"], (x, y)
            if x == 0:
                assert c["W"] == 1
            if y == 0:
                assert c["N"] == 1
            if x == arena.colunas - 1:
                assert c["E"] == 1
            if y == arena.linhas - 1:
                assert c["S"] == 1


@pytest.mark.parametrize("semente", range(10))
@pytest.mark.parametrize("linhas,colunas", TAMANHOS)
def test_labirinto_aleatorio_e_perfeito(linhas, colunas, semente):
    """
    O gerador (backtracking recursivo) cria um labirinto PERFEITO:
    todas as células alcançáveis, nenhum ciclo (passagens = células - 1)
    e paredes coerentes dos dois lados.
    """
    arena = labirinto_aleatorio(linhas, colunas, semente)
    _paredes_consistentes(arena)
    assert len(alcancaveis(arena)) == linhas * colunas
    assert numero_de_passagens(arena) == linhas * colunas - 1


# --------------------------------------------------------------------------
# Robo
# --------------------------------------------------------------------------

def test_robo_comeca_em_0_0_virado_para_leste():
    robo = sim.Robo(arena_aberta(3, 3), 0, 0)
    assert (robo.x, robo.y, robo.direcao, robo.movimentos) == (0, 0, 1, 0)
    assert robo.mapa_dir[robo.direcao] == "E"


def test_giros_mudam_direcao_e_contam_como_movimento():
    robo = sim.Robo(arena_aberta(3, 3), 0, 0)
    robo.virar_direita()
    assert robo.mapa_dir[robo.direcao] == "S"
    robo.virar_esquerda()
    robo.virar_esquerda()
    assert robo.mapa_dir[robo.direcao] == "N"
    assert robo.movimentos == 3
    assert (robo.x, robo.y) == (0, 0)


def test_sensores_sao_relativos_a_direcao_do_robo():
    # Canto (0,0): paredes ao Norte e a Oeste.
    robo = sim.Robo(arena_aberta(3, 3), 0, 0)  # virado para Leste
    assert not robo.verificar_parede_frente()   # Leste
    assert not robo.verificar_parede_direita()  # Sul
    assert robo.verificar_parede_esquerda()     # Norte
    assert robo.verificar_parede_tras()         # Oeste


def test_andar_frente_e_tras():
    robo = sim.Robo(arena_aberta(3, 3), 0, 0)
    robo.andar_frente()
    assert (robo.x, robo.y) == (1, 0)
    robo.andar_tras()
    assert (robo.x, robo.y) == (0, 0)
    assert robo.direcao == 1  # andar de ré NÃO gira o robô
    assert robo.movimentos == 2


def test_robo_nao_atravessa_parede_nem_conta_movimento():
    arena = arena_fechada(3, 3)
    robo = sim.Robo(arena, 0, 0)
    robo.andar_frente()
    robo.andar_tras()
    assert (robo.x, robo.y, robo.movimentos) == (0, 0, 0)

    abrir(arena, (0, 0), (1, 0))
    robo.andar_frente()
    assert (robo.x, robo.y, robo.movimentos) == (1, 0, 1)
