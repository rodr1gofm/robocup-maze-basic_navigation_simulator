import pygame
import sys
import random
from collections import deque

# --- Paleta de Cores Moderna (Dark Theme) ---
BG_COLOR = (30, 30, 46)          
TILE_VAZIO = (49, 50, 68)        
TILE_VISITADO = (249, 226, 175)  
TILE_COMPLETO = (166, 227, 161)  
PAREDE_COLOR = (203, 166, 247)   
ROBO_CORPO = (55, 65, 90)        
ROBO_SENSOR = (243, 139, 168)    
TEXTO_PRINCIPAL = (205, 214, 244)
TEXTO_DESTAQUE = (137, 180, 250) 
CARD_BG = (49, 50, 68)           
VERMELHO_ALERTA = (231, 130, 132) 

# --- Configurações Fixas de Tela ---
LARGURA_TELA = 600
ALTURA_UI = 60 
ALTURA_TELA = 600 + ALTURA_UI

FPS = 30
completos = []
visitados = set() 
movimentos_atuais = [] 
proximos_bfs = [] 
algoritmo_atual = ""

class VoltarMenu(Exception):
    pass

modo_automatico = False
busca_concluida = False

indice_velocidade = 1
VELOCIDADES_DELAY = [300, 120, 30, 0] 
VELOCIDADES_TEXTO = ["1x Lento", "2x Normal", "3x Rápido", "MAX Turbo"]

def fonte_padrao(tamanho, negrito=False):
    return pygame.font.SysFont("Segoe UI, Arial", tamanho, bold=negrito)

class Arena:
    def __init__(self, linhas, colunas, tamanho_tile, offset_x=0, offset_y=0):
        self.linhas = linhas
        self.colunas = colunas
        self.tamanho_tile = tamanho_tile
        self.offset_x = offset_x
        self.offset_y = offset_y
        
        self.fonte_coord = fonte_padrao(12, negrito=True) 
        
        self.grid = []
        for y in range(linhas):
            linha = []
            for x in range(colunas):
                celula = {'N': 0, 'E': 0, 'S': 0, 'W': 0}
                if y == 0: celula['N'] = 1
                if y == linhas - 1: celula['S'] = 1
                if x == 0: celula['W'] = 1
                if x == colunas - 1: celula['E'] = 1
                linha.append(celula)
            self.grid.append(linha)

    def gerar_labirinto_aleatorio(self):
        for y in range(self.linhas):
            for x in range(self.colunas):
                self.grid[y][x] = {'N': 1, 'E': 1, 'S': 1, 'W': 1}
                
        visitados_gen = set()
        
        def carve(cx, cy):
            visitados_gen.add((cx, cy))
            direcoes = [('N', 0, -1, 'S'), ('E', 1, 0, 'W'), ('S', 0, 1, 'N'), ('W', -1, 0, 'E')]
            random.shuffle(direcoes)
            
            for dir_nome, dx, dy, dir_oposta in direcoes:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.colunas and 0 <= ny < self.linhas and (nx, ny) not in visitados_gen:
                    self.grid[cy][cx][dir_nome] = 0
                    self.grid[ny][nx][dir_oposta] = 0
                    carve(nx, ny)
                    
        carve(0, 0)

    def desenhar(self, tela):
        tela.fill(BG_COLOR)
        padding = 4 
        
        for y in range(self.linhas):
            for x in range(self.colunas):
                celula = self.grid[y][x]
                
                px = x * self.tamanho_tile + self.offset_x
                py = y * self.tamanho_tile + self.offset_y
                
                tile_rect = (px + padding, py + padding, self.tamanho_tile - padding*2, self.tamanho_tile - padding*2)
                
                if (x, y) in completos:
                    pygame.draw.rect(tela, TILE_COMPLETO, tile_rect, border_radius=8)
                elif (x, y) in visitados:
                    cor = TILE_COMPLETO if algoritmo_atual == 'bfs' else TILE_VISITADO
                    pygame.draw.rect(tela, cor, tile_rect, border_radius=8)
                elif (x, y) in proximos_bfs:
                    pygame.draw.rect(tela, TILE_VISITADO, tile_rect, border_radius=8)
                else:
                    pygame.draw.rect(tela, TILE_VAZIO, tile_rect, border_radius=8)

                esp = 6
                if celula['N']: pygame.draw.rect(tela, PAREDE_COLOR, (px, py - esp//2, self.tamanho_tile, esp), border_radius=4)
                if celula['S']: pygame.draw.rect(tela, PAREDE_COLOR, (px, py + self.tamanho_tile - esp//2, self.tamanho_tile, esp), border_radius=4)
                if celula['W']: pygame.draw.rect(tela, PAREDE_COLOR, (px - esp//2, py, esp, self.tamanho_tile), border_radius=4)
                if celula['E']: pygame.draw.rect(tela, PAREDE_COLOR, (px + self.tamanho_tile - esp//2, py, esp, self.tamanho_tile), border_radius=4)

                surf_coord = self.fonte_coord.render(f"{x},{y}", True, (10, 10, 15)) 
                surf_coord.set_alpha(80) 
                tela.blit(surf_coord, (px + padding + 4, py + padding + 2))

class Robo:
    def __init__(self, arena, x_inicial, y_inicial):
        self.arena = arena
        self.x = x_inicial
        self.y = y_inicial
        self.direcao = 1
        self.movimentos = 0 
        self.mapa_dir = {0: 'N', 1: 'E', 2: 'S', 3: 'W'}

    def virar_direita(self): 
        self.direcao = (self.direcao + 1) % 4
        self.movimentos += 1

    def virar_esquerda(self): 
        self.direcao = (self.direcao - 1) % 4
        self.movimentos += 1

    def andar_frente(self):
        if not self.verificar_parede_frente():
            movimentos_dir = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
            dx, dy = movimentos_dir[self.direcao]
            self.x += dx
            self.y += dy
            self.movimentos += 1
            
    def andar_tras(self):
        if not self.verificar_parede_tras():
            movimentos_dir = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
            dx, dy = movimentos_dir[self.direcao]
            self.x -= dx
            self.y -= dy
            self.movimentos += 1

    def verificar_parede_frente(self): return self.arena.grid[self.y][self.x][self.mapa_dir[self.direcao]] == 1
    def verificar_parede_tras(self): return self.arena.grid[self.y][self.x][self.mapa_dir[(self.direcao + 2) % 4]] == 1
    def verificar_parede_direita(self): return self.arena.grid[self.y][self.x][self.mapa_dir[(self.direcao + 1) % 4]] == 1
    def verificar_parede_esquerda(self): return self.arena.grid[self.y][self.x][self.mapa_dir[(self.direcao - 1) % 4]] == 1
    
    def desenhar(self, tela):
        tam = self.arena.tamanho_tile
        
        centro_x = self.x * tam + tam // 2 + self.arena.offset_x
        centro_y = self.y * tam + tam // 2 + self.arena.offset_y
        
        tamanho_corpo = tam // 1.5
        raio_sensor = tam // 8 
        
        corpo_rect = (centro_x - tamanho_corpo // 2, centro_y - tamanho_corpo // 2, tamanho_corpo, tamanho_corpo)

        pygame.draw.rect(tela, ROBO_CORPO, corpo_rect, border_radius=int(tam//10))
        pygame.draw.rect(tela, PAREDE_COLOR, corpo_rect, width=2, border_radius=int(tam//10))
        
        corpo_rect_inner = (corpo_rect[0] + 3, corpo_rect[1] + 3, corpo_rect[2] - 6, corpo_rect[3] - 6)
        pygame.draw.rect(tela, BG_COLOR, corpo_rect_inner, width=2, border_radius=int(tam//12))

        ponta_x, ponta_y = centro_x, centro_y
        offset = (tamanho_corpo // 2) - raio_sensor - 2
        
        if self.direcao == 0: ponta_y -= offset
        elif self.direcao == 1: ponta_x += offset
        elif self.direcao == 2: ponta_y += offset
        elif self.direcao == 3: ponta_x -= offset
        
        pygame.draw.circle(tela, ROBO_SENSOR, (ponta_x, ponta_y), int(raio_sensor))


# --- FUNÇÕES DE RENDERIZAÇÃO E UI DO JOGO ---

def get_rect_botao_auto(tela):
    largura = 220
    altura = 40
    x = tela.get_width() // 2 - 185
    y = tela.get_height() - ALTURA_UI + 10 
    return pygame.Rect(x, y, largura, altura)

def get_rect_botao_vel(tela):
    largura = 140
    altura = 40
    x = tela.get_width() // 2 + 45
    y = tela.get_height() - ALTURA_UI + 10 
    return pygame.Rect(x, y, largura, altura)

def get_rect_botao_sair(tela):
    tamanho = 40
    x = tela.get_width() - tamanho - 10
    y = tela.get_height() - ALTURA_UI + 10
    return pygame.Rect(x, y, tamanho, tamanho)

def renderizar_tela_jogo(tela, arena, robo):
    global modo_automatico, busca_concluida, indice_velocidade, movimentos_atuais
    arena.desenhar(tela)
    robo.desenhar(tela)
    
    if len(movimentos_atuais) > 0 and algoritmo_atual == 'dfs_lista':
        rect_lista = pygame.Rect(10, 10, tela.get_width() - 20, 36)
        surf_fundo = pygame.Surface((rect_lista.width, rect_lista.height), pygame.SRCALPHA)
        pygame.draw.rect(surf_fundo, (*CARD_BG, 220), surf_fundo.get_rect(), border_radius=8)
        tela.blit(surf_fundo, (rect_lista.x, rect_lista.y))
        pygame.draw.rect(tela, TEXTO_DESTAQUE, rect_lista, width=2, border_radius=8)
        
        max_items = 20 
        exibir = movimentos_atuais[-max_items:]
        texto_lista = "Pilha DFS: [ " + ", ".join(exibir) + " ]"
        if len(movimentos_atuais) > max_items:
            texto_lista = "Pilha DFS: [ ..., " + ", ".join(exibir) + " ]"
            
        f_lista = fonte_padrao(16, negrito=True)
        surf_lista = f_lista.render(texto_lista, True, TEXTO_PRINCIPAL)
        tela.blit(surf_lista, (rect_lista.x + 15, rect_lista.centery - surf_lista.get_height()//2))

    elif algoritmo_atual == 'bfs' and len(proximos_bfs) > 0:
        rect_lista = pygame.Rect(10, 10, tela.get_width() - 20, 36)
        surf_fundo = pygame.Surface((rect_lista.width, rect_lista.height), pygame.SRCALPHA)
        pygame.draw.rect(surf_fundo, (*CARD_BG, 220), surf_fundo.get_rect(), border_radius=8)
        tela.blit(surf_fundo, (rect_lista.x, rect_lista.y))
        pygame.draw.rect(tela, TILE_VISITADO, rect_lista, width=2, border_radius=8) 
        
        max_items = 10 
        lista_str = [f"({x},{y})" for x, y in proximos_bfs]
        exibir = lista_str[-max_items:]
        
        texto_lista = "Fila BFS: [ " + ", ".join(exibir) + " ]"
        if len(lista_str) > max_items:
            texto_lista = "Fila BFS: [ ..., " + ", ".join(exibir) + " ]"
            
        f_lista = fonte_padrao(16, negrito=True)
        surf_lista = f_lista.render(texto_lista, True, TEXTO_PRINCIPAL)
        tela.blit(surf_lista, (rect_lista.x + 15, rect_lista.centery - surf_lista.get_height()//2))

    pygame.draw.rect(tela, BG_COLOR, (0, tela.get_height() - ALTURA_UI, tela.get_width(), ALTURA_UI))
    
    f_contador = fonte_padrao(16, negrito=True)
    surf_mov = f_contador.render(f"Mov: {robo.movimentos}", True, TEXTO_DESTAQUE)
    tela.blit(surf_mov, (15, tela.get_height() - ALTURA_UI + 20))

    rect_botao = get_rect_botao_auto(tela)
    if busca_concluida:
        cor_fundo = TILE_COMPLETO 
        cor_texto = BG_COLOR
        texto = "↻  Novo Labirinto"
    elif modo_automatico:
        cor_fundo = PAREDE_COLOR
        cor_texto = BG_COLOR
        texto = "||  Pausar Automático"
    else:
        cor_fundo = CARD_BG
        cor_texto = TEXTO_PRINCIPAL
        texto = "▶  Rodar Automático"
        
    pygame.draw.rect(tela, cor_fundo, rect_botao, border_radius=8)
    if not busca_concluida:
        pygame.draw.rect(tela, PAREDE_COLOR, rect_botao, width=2, border_radius=8)
    
    f_botao = fonte_padrao(18, negrito=True)
    surf_texto = f_botao.render(texto, True, cor_texto)
    tela.blit(surf_texto, (rect_botao.centerx - surf_texto.get_width()//2, rect_botao.centery - surf_texto.get_height()//2))

    rect_vel = get_rect_botao_vel(tela)
    pygame.draw.rect(tela, CARD_BG, rect_vel, border_radius=8)
    pygame.draw.rect(tela, TEXTO_DESTAQUE, rect_vel, width=2, border_radius=8)
    
    if busca_concluida:
        texto_vel = "Trocar Alg."
    else:
        texto_vel = VELOCIDADES_TEXTO[indice_velocidade]
        
    surf_vel = f_botao.render(texto_vel, True, TEXTO_PRINCIPAL)
    tela.blit(surf_vel, (rect_vel.centerx - surf_vel.get_width()//2, rect_vel.centery - surf_vel.get_height()//2))

    rect_sair = get_rect_botao_sair(tela)
    pygame.draw.rect(tela, VERMELHO_ALERTA, rect_sair, border_radius=8)
    f_x = fonte_padrao(22, negrito=True)
    surf_x = f_x.render("X", True, BG_COLOR)
    tela.blit(surf_x, (rect_sair.centerx - surf_x.get_width()//2, rect_sair.centery - surf_x.get_height()//2 + 1))

    pygame.display.flip()

def esperar_tecla(robo, arena, tela):
    global modo_automatico, indice_velocidade
    
    if modo_automatico:
        renderizar_tela_jogo(tela, arena, robo)
        pygame.time.delay(VELOCIDADES_DELAY[indice_velocidade]) 
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if get_rect_botao_auto(tela).collidepoint(evento.pos):
                    modo_automatico = False 
                elif get_rect_botao_vel(tela).collidepoint(evento.pos):
                    indice_velocidade = (indice_velocidade + 1) % 4
                elif get_rect_botao_sair(tela).collidepoint(evento.pos):
                    raise VoltarMenu() 
        return 

    while True:
        renderizar_tela_jogo(tela, arena, robo)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if evento.type == pygame.KEYDOWN: return
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if get_rect_botao_auto(tela).collidepoint(evento.pos):
                    modo_automatico = True 
                    return
                elif get_rect_botao_vel(tela).collidepoint(evento.pos):
                    indice_velocidade = (indice_velocidade + 1) % 4
                elif get_rect_botao_sair(tela).collidepoint(evento.pos):
                    raise VoltarMenu() 

# --- ALGORITMOS DE BUSCA ---

def proximo_tile_visitado(robo, alvo):
    rotacao = {0: 0, 1: 1, 2: 3}
    dir_alvo = (robo.direcao + rotacao[alvo]) % 4
    deslocamentos = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
    dx, dy = deslocamentos[dir_alvo]
    return (robo.x + dx, robo.y + dy) in visitados

def proximo_tile_completo(robo, alvo):
    rotacao = {0: 0, 1: 1, 2: 3}
    dir_alvo = (robo.direcao + rotacao[alvo]) % 4
    deslocamentos = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
    dx, dy = deslocamentos[dir_alvo]
    return (robo.x + dx, robo.y + dy) in completos

def coordenadas_vizinho(robo, alvo):
    rotacao = {0: 0, 1: 1, 2: 3}
    dir_alvo = (robo.direcao + rotacao[alvo]) % 4
    deslocamentos = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
    dx, dy = deslocamentos[dir_alvo]
    return (robo.x + dx, robo.y + dy)

def mover_para_vizinho(robo, coord_atual, coord_alvo, arena, tela):
    x_atual, y_atual = coord_atual
    x_alvo, y_alvo = coord_alvo
    
    if coord_atual == coord_alvo:
        return
    
    if x_alvo > x_atual:
        dir_alvo = 1  # Leste
    elif x_alvo < x_atual:
        dir_alvo = 3  # Oeste
    elif y_alvo > y_atual:
        dir_alvo = 2  # Sul
    else:
        dir_alvo = 0  # Norte
        
    diff = (dir_alvo - robo.direcao) % 4
    
    if diff == 1:
        robo.virar_direita()
        esperar_tecla(robo, arena, tela)
    elif diff == 2:
        robo.virar_direita()
        esperar_tecla(robo, arena, tela)
        robo.virar_direita()
        esperar_tecla(robo, arena, tela)
    elif diff == 3:
        robo.virar_esquerda()
        esperar_tecla(robo, arena, tela)
        
    robo.andar_frente()
    esperar_tecla(robo, arena, tela)

def proximo_tile_conhecido(robo, proximos, alvo):
    rotacao = {0: 0, 1: 1, 2: 3}
    dir_alvo = (robo.direcao + rotacao[alvo]) % 4
    deslocamentos = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
    dx, dy = deslocamentos[dir_alvo]
    
    tile_vizinho = (robo.x + dx, robo.y + dy)
    
    return (tile_vizinho in visitados) or (tile_vizinho in proximos)


def bfs(robo, arena, tela):
    global proximos_bfs
    proximos_bfs.clear()
    
    origem = {(robo.x, robo.y): (robo.x, robo.y)} 
    proximos = deque() 
    finalizado = 0
    while True:
        coord_atual = (robo.x, robo.y)
        visitados.add(coord_atual)
        if not robo.verificar_parede_frente() and not proximo_tile_conhecido(robo, proximos, 0):
            proximos.append(coordenadas_vizinho(robo, 0))
            origem[coordenadas_vizinho(robo, 0)] = (coord_atual)
        if not robo.verificar_parede_direita() and not proximo_tile_conhecido(robo, proximos, 1):
            proximos.append(coordenadas_vizinho(robo, 1))
            origem[coordenadas_vizinho(robo, 1)] = (coord_atual)
        if not robo.verificar_parede_esquerda() and not proximo_tile_conhecido(robo, proximos, 2):
            proximos.append(coordenadas_vizinho(robo, 2))
            origem[coordenadas_vizinho(robo, 2)] = (coord_atual)
            
        proximos_bfs.clear()
        proximos_bfs.extend(proximos)
            
        if not proximos:
            if finalizado == 1:
                break
            else:
                proximos.append((0, 0))
                finalizado = 1
        
        coord_proximo = proximos[0]
        proximo_origem = coord_proximo
        atual_origem = coord_atual
        k1 = 1
        while k1 == 1:
            while True:
                proximo_origem = origem[proximo_origem]
                if atual_origem == proximo_origem:
                    comum = atual_origem
                    k1 = 0
                    break
                if proximo_origem == origem[proximo_origem]:
                    break
            atual_origem = origem[atual_origem]
            proximo_origem = coord_proximo
        
        while comum != coord_atual:
            coord_alvo = origem[coord_atual]
            mover_para_vizinho(robo, coord_atual, coord_alvo, arena, tela)
            coord_atual = coord_alvo
        
        while coord_atual!=coord_proximo:
            coord_alvo = coord_proximo
            while coord_alvo!=coord_atual:
                coord_anterior = coord_alvo
                coord_alvo = origem[coord_alvo]
            mover_para_vizinho(robo, coord_atual, coord_anterior, arena, tela)
            coord_atual = coord_anterior
            
        proximos.popleft()
        
        proximos_bfs.clear()
        proximos_bfs.extend(proximos)

def dfs_recursivo(robo, arena, tela):
    visitados.add((robo.x, robo.y))
    
    if not robo.verificar_parede_frente() and not proximo_tile_visitado(robo, 0):
        robo.andar_frente(); esperar_tecla(robo, arena, tela)
        dfs_recursivo(robo, arena, tela)
        robo.andar_tras(); esperar_tecla(robo, arena, tela)
        
    if not robo.verificar_parede_direita() and not proximo_tile_visitado(robo, 1):
        robo.virar_direita(); esperar_tecla(robo, arena, tela)
        robo.andar_frente(); esperar_tecla(robo, arena, tela)
        dfs_recursivo(robo, arena, tela)
        robo.andar_tras(); esperar_tecla(robo, arena, tela)
        robo.virar_esquerda(); esperar_tecla(robo, arena, tela)
    
    if not robo.verificar_parede_esquerda() and not proximo_tile_visitado(robo, 2):
        robo.virar_esquerda(); esperar_tecla(robo, arena, tela)
        robo.andar_frente(); esperar_tecla(robo, arena, tela)
        dfs_recursivo(robo, arena, tela)
        robo.andar_tras(); esperar_tecla(robo, arena, tela)
        robo.virar_direita(); esperar_tecla(robo, arena, tela)
         
    completos.append((robo.x, robo.y))
    return

def dfs_lista(robo, arena, tela):
    global movimentos_atuais
    movimentos_atuais.clear()
    
    visitados.add((robo.x, robo.y))
    x_inicial = robo.x
    y_inicial = robo.y
    
    while True:
        if not robo.verificar_parede_frente() and not proximo_tile_visitado(robo, 0):
            movimentos_atuais.append("F")
            robo.andar_frente()
            esperar_tecla(robo, arena, tela)
            visitados.add((robo.x, robo.y))
            
        elif not robo.verificar_parede_direita() and not proximo_tile_visitado(robo, 1):
            movimentos_atuais.append("D")
            robo.virar_direita()
            esperar_tecla(robo, arena, tela)
            
            movimentos_atuais.append("F")
            robo.andar_frente()
            esperar_tecla(robo, arena, tela)
            visitados.add((robo.x, robo.y))
            
        elif not robo.verificar_parede_esquerda() and not proximo_tile_visitado(robo, 2):
            movimentos_atuais.append("E")
            robo.virar_esquerda()
            esperar_tecla(robo, arena, tela)
            
            movimentos_atuais.append("F")
            robo.andar_frente()
            esperar_tecla(robo, arena, tela)
            visitados.add((robo.x, robo.y))
            
        else:
            completos.append((robo.x, robo.y))
            if robo.x == x_inicial and robo.y == y_inicial:
                break
                
            ultimo_movimento = movimentos_atuais.pop()
            
            if ultimo_movimento == "F":
                robo.andar_tras()
                esperar_tecla(robo, arena, tela)
            elif ultimo_movimento == "D":
                robo.virar_esquerda()
                esperar_tecla(robo, arena, tela)
            elif ultimo_movimento == "E":
                robo.virar_direita()
                esperar_tecla(robo, arena, tela)

def seguidor_parede_burro(robo, arena, tela):
    while True:
        if not robo.verificar_parede_frente():
            completos.append((robo.x, robo.y))
            robo.andar_frente(); esperar_tecla(robo, arena, tela)
        elif not robo.verificar_parede_direita():
            completos.append((robo.x, robo.y))
            robo.virar_direita(); esperar_tecla(robo, arena, tela)
            robo.andar_frente(); esperar_tecla(robo, arena, tela)
        elif not robo.verificar_parede_esquerda():
            completos.append((robo.x, robo.y))
            robo.virar_esquerda(); esperar_tecla(robo, arena, tela)
            robo.andar_frente(); esperar_tecla(robo, arena, tela)
        else:
            completos.append((robo.x, robo.y))
            robo.andar_tras(); esperar_tecla(robo, arena, tela)
    return

def seguidor_parede(robo, arena, tela):
    while True:
        if not robo.verificar_parede_frente() and not proximo_tile_completo(robo, 0):
            completos.append((robo.x, robo.y))
            robo.andar_frente(); esperar_tecla(robo, arena, tela)
        elif not robo.verificar_parede_direita() and not proximo_tile_completo(robo, 1):
            completos.append((robo.x, robo.y))
            robo.virar_direita(); esperar_tecla(robo, arena, tela)
            robo.andar_frente(); esperar_tecla(robo, arena, tela)
        elif not robo.verificar_parede_esquerda() and not proximo_tile_completo(robo, 2):
            completos.append((robo.x, robo.y))
            robo.virar_esquerda(); esperar_tecla(robo, arena, tela)
            robo.andar_frente(); esperar_tecla(robo, arena, tela)
        else:
            completos.append((robo.x, robo.y))
            robo.andar_tras(); esperar_tecla(robo, arena, tela)
    return


# --- FUNÇÕES DE MENU E CONSTRUÇÃO ---

def desenhar_texto_centralizado(tela, texto, fonte, cor, y, shadow=True):
    surf_texto = fonte.render(texto, True, cor)
    x = tela.get_width() // 2 - surf_texto.get_width() // 2
    if shadow:
        surf_sombra = fonte.render(texto, True, (10, 10, 15))
        tela.blit(surf_sombra, (x + 2, y + 2))
    tela.blit(surf_texto, (x, y))

def desenhar_seta(tela, rect, direcao, cor, hover=False):
    pygame.draw.rect(tela, TILE_VAZIO if hover else BG_COLOR, rect, border_radius=8)
    pygame.draw.rect(tela, cor, rect, width=2, border_radius=8)
    x, y, w, h = rect
    cx, cy = x + w//2, y + h//2
    pts = []
    if direcao == 'esq': pts = [(cx+4, cy-6), (cx-4, cy), (cx+4, cy+6)]
    elif direcao == 'dir': pts = [(cx-4, cy-6), (cx+4, cy), (cx-4, cy+6)]
    pygame.draw.polygon(tela, cor, pts)

def tela_inicio(tela):
    f_titulo = fonte_padrao(36, negrito=True)
    f_sub = fonte_padrao(18)
    f_media = fonte_padrao(24, negrito=True)
    f_pequena = fonte_padrao(18)
    f_dropdown = fonte_padrao(20, negrito=True) # NOVO: Fonte Menor para o dropdown
    
    linhas = 5
    colunas = 5
    modo = None

    algoritmos = [
        ("Seg. Parede (Burro)", seguidor_parede_burro), # Encurtado para caber perfeitamente
        ("Seguidor de Parede", seguidor_parede),
        ("DFS (Busca em Lista)", dfs_lista),
        ("DFS (Recursivo)", dfs_recursivo),
        ("BFS", bfs) 
    ]
    algo_idx = 0

    dropdown_aberto = False
    esperando = True
    
    while esperando:
        mx, my = pygame.mouse.get_pos()
        tela.fill(BG_COLOR)
        
        desenhar_texto_centralizado(tela, "Rescue Maze", f_titulo, PAREDE_COLOR, 20)
        desenhar_texto_centralizado(tela, "Simulador de Algoritmos", f_sub, TEXTO_PRINCIPAL, 55, shadow=False)
        
        x_card = (tela.get_width() - 400) // 2

        pygame.draw.rect(tela, CARD_BG, (x_card, 95, 400, 140), border_radius=15)
        desenhar_texto_centralizado(tela, "Tamanho da Arena", f_pequena, TEXTO_PRINCIPAL, 110, shadow=False)
        
        rect_col_esq = pygame.Rect(x_card + 80, 140, 30, 30)
        rect_col_dir = pygame.Rect(x_card + 290, 140, 30, 30)
        desenhar_seta(tela, rect_col_esq, 'esq', TEXTO_DESTAQUE, rect_col_esq.collidepoint(mx, my))
        desenhar_seta(tela, rect_col_dir, 'dir', TEXTO_DESTAQUE, rect_col_dir.collidepoint(mx, my))
        surf_col = f_media.render(f"Colunas: {colunas:02d}", True, TILE_VISITADO)
        tela.blit(surf_col, (tela.get_width()//2 - surf_col.get_width()//2, 142))

        rect_lin_esq = pygame.Rect(x_card + 80, 185, 30, 30)
        rect_lin_dir = pygame.Rect(x_card + 290, 185, 30, 30)
        desenhar_seta(tela, rect_lin_esq, 'esq', TEXTO_DESTAQUE, rect_lin_esq.collidepoint(mx, my))
        desenhar_seta(tela, rect_lin_dir, 'dir', TEXTO_DESTAQUE, rect_lin_dir.collidepoint(mx, my))
        surf_lin = f_media.render(f"Linhas:  {linhas:02d}", True, TILE_VISITADO)
        tela.blit(surf_lin, (tela.get_width()//2 - surf_lin.get_width()//2, 187))

        pygame.draw.rect(tela, CARD_BG, (x_card, 400, 400, 140), border_radius=15)
        desenhar_texto_centralizado(tela, "Selecione o Modo:", f_pequena, TEXTO_PRINCIPAL, 420, shadow=False)
        
        rect_btn_m = pygame.Rect(x_card + 20, 460, 160, 50)
        hover_m = rect_btn_m.collidepoint(mx, my)
        pygame.draw.rect(tela, TILE_COMPLETO if not hover_m else (186, 247, 181), rect_btn_m, border_radius=8)
        surf_m = f_pequena.render("[ M ] Manual", True, BG_COLOR)
        tela.blit(surf_m, (rect_btn_m.centerx - surf_m.get_width()//2, rect_btn_m.centery - surf_m.get_height()//2))

        rect_btn_a = pygame.Rect(x_card + 220, 460, 160, 50)
        hover_a = rect_btn_a.collidepoint(mx, my)
        pygame.draw.rect(tela, PAREDE_COLOR if not hover_a else (223, 186, 255), rect_btn_a, border_radius=8)
        surf_a = f_pequena.render("[ A ] Aleatório", True, BG_COLOR)
        tela.blit(surf_a, (rect_btn_a.centerx - surf_a.get_width()//2, rect_btn_a.centery - surf_a.get_height()//2))

        pygame.draw.rect(tela, CARD_BG, (x_card, 250, 400, 130), border_radius=15)
        desenhar_texto_centralizado(tela, "Algoritmo de Busca", f_pequena, TEXTO_PRINCIPAL, 265, shadow=False)
        
        rect_dd_main = pygame.Rect(x_card + 40, 305, 320, 45)
        hover_dd = rect_dd_main.collidepoint(mx, my)
        pygame.draw.rect(tela, TILE_VAZIO if not hover_dd else (69, 70, 88), rect_dd_main, border_radius=8)
        pygame.draw.rect(tela, VERMELHO_ALERTA, rect_dd_main, width=2, border_radius=8)
        
        texto_algo = f"[{algo_idx+1}] {algoritmos[algo_idx][0]}"
        surf_algo = f_dropdown.render(texto_algo, True, TEXTO_PRINCIPAL)
        tela.blit(surf_algo, (rect_dd_main.x + 15, rect_dd_main.centery - surf_algo.get_height()//2))
        
        seta_dd = "v" if not dropdown_aberto else "^"
        surf_seta = f_dropdown.render(seta_dd, True, VERMELHO_ALERTA)
        tela.blit(surf_seta, (rect_dd_main.right - 30, rect_dd_main.centery - surf_seta.get_height()//2))

        rects_opcoes = []
        if dropdown_aberto:
            rect_dd_list = pygame.Rect(x_card + 40, 355, 320, len(algoritmos) * 40 + 10)
            pygame.draw.rect(tela, (40, 40, 56), rect_dd_list, border_radius=8)
            pygame.draw.rect(tela, VERMELHO_ALERTA, rect_dd_list, width=2, border_radius=8)
            
            for i, algo in enumerate(algoritmos):
                rect_op = pygame.Rect(rect_dd_list.x + 5, rect_dd_list.y + 5 + i*40, 310, 35)
                rects_opcoes.append(rect_op)
                hover_op = rect_op.collidepoint(mx, my)
                
                if hover_op or i == algo_idx:
                    pygame.draw.rect(tela, TILE_VAZIO, rect_op, border_radius=5)
                    
                cor_texto = VERMELHO_ALERTA if i == algo_idx else TEXTO_PRINCIPAL
                surf_op = f_pequena.render(f"{i+1}. {algo[0]}", True, cor_texto)
                tela.blit(surf_op, (rect_op.x + 10, rect_op.centery - surf_op.get_height()//2))

        pygame.display.flip()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
                
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1: 
                    if dropdown_aberto:
                        clicou_opcao = False
                        for i, rect_op in enumerate(rects_opcoes):
                            if rect_op.collidepoint(evento.pos):
                                algo_idx = i
                                dropdown_aberto = False
                                clicou_opcao = True
                                break
                        if not clicou_opcao:
                            dropdown_aberto = False 
                    else:
                        if rect_dd_main.collidepoint(evento.pos):
                            dropdown_aberto = True
                        elif rect_col_esq.collidepoint(evento.pos) and colunas > 3: colunas -= 1
                        elif rect_col_dir.collidepoint(evento.pos) and colunas < 15: colunas += 1
                        elif rect_lin_esq.collidepoint(evento.pos) and linhas > 3: linhas -= 1
                        elif rect_lin_dir.collidepoint(evento.pos) and linhas < 15: linhas += 1
                        elif rect_btn_m.collidepoint(evento.pos):
                            modo = 'M'
                            esperando = False
                        elif rect_btn_a.collidepoint(evento.pos):
                            modo = 'A'
                            esperando = False

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_UP and linhas < 15: linhas += 1
                elif evento.key == pygame.K_DOWN and linhas > 3: linhas -= 1
                elif evento.key == pygame.K_RIGHT and colunas < 15: colunas += 1
                elif evento.key == pygame.K_LEFT and colunas > 3: colunas -= 1
                
                elif evento.key == pygame.K_1: algo_idx = 0; dropdown_aberto = False
                elif evento.key == pygame.K_2: algo_idx = 1; dropdown_aberto = False
                elif evento.key == pygame.K_3: algo_idx = 2; dropdown_aberto = False
                elif evento.key == pygame.K_4: algo_idx = 3; dropdown_aberto = False
                elif evento.key == pygame.K_5: algo_idx = 4; dropdown_aberto = False
                
                elif evento.key == pygame.K_m: 
                    modo = 'M'
                    esperando = False
                elif evento.key == pygame.K_a:
                    modo = 'A'
                    esperando = False
                    
    return linhas, colunas, modo, algoritmos[algo_idx][1]

def tela_construcao(tela, arena):
    f_instrucao = fonte_padrao(22, negrito=True)
    
    construindo = True
    while construindo:
        arena.desenhar(tela)
        
        pygame.draw.rect(tela, (20, 20, 30, 200), (0, 0, tela.get_width(), 40))
        surf_inst = f_instrucao.render("Construa: Clique nas bordas | Pronto: Aperte ESPAÇO", True, TILE_VISITADO)
        tela.blit(surf_inst, (tela.get_width()//2 - surf_inst.get_width()//2, 10))
        
        pygame.display.flip()
        
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
                
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_SPACE:
                    construindo = False 
                    
            if evento.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                
                mx -= arena.offset_x
                my -= arena.offset_y
                
                tx = mx // arena.tamanho_tile
                ty = my // arena.tamanho_tile
                
                if 0 <= tx < arena.colunas and 0 <= ty < arena.linhas:
                    ox = mx % arena.tamanho_tile
                    oy = my % arena.tamanho_tile
                    margem = 15
                    
                    if oy < margem and ty > 0: 
                        arena.grid[ty][tx]['N'] = 1 - arena.grid[ty][tx]['N']
                        arena.grid[ty-1][tx]['S'] = arena.grid[ty][tx]['N']
                    elif oy > arena.tamanho_tile - margem and ty < arena.linhas - 1: 
                        arena.grid[ty][tx]['S'] = 1 - arena.grid[ty][tx]['S']
                        arena.grid[ty+1][tx]['N'] = arena.grid[ty][tx]['S']
                    elif ox < margem and tx > 0: 
                        arena.grid[ty][tx]['W'] = 1 - arena.grid[ty][tx]['W']
                        arena.grid[ty][tx-1]['E'] = arena.grid[ty][tx]['W']
                    elif ox > arena.tamanho_tile - margem and tx < arena.colunas - 1: 
                        arena.grid[ty][tx]['E'] = 1 - arena.grid[ty][tx]['E']
                        arena.grid[ty][tx+1]['W'] = arena.grid[ty][tx]['E']

# NOVO: Recebe 'arena' e 'robo' para renderizar o fundo desfocado e re-usa a lógica de dropdown
def tela_escolher_algoritmo(tela, arena, robo):
    f_titulo = fonte_padrao(24, negrito=True)
    f_dropdown = fonte_padrao(20, negrito=True)
    f_pequena = fonte_padrao(18)
    
    algoritmos = [
        ("Seg. Parede (Burro)", seguidor_parede_burro),
        ("Seguidor de Parede", seguidor_parede),
        ("DFS (Busca em Lista)", dfs_lista),
        ("DFS (Recursivo)", dfs_recursivo),
        ("BFS", bfs) 
    ]
    algo_idx = 0
    dropdown_aberto = False
    esperando = True
    
    while esperando:
        mx, my = pygame.mouse.get_pos()
        
        # Renderiza o labirinto concluído como cenário de fundo
        arena.desenhar(tela)
        robo.desenhar(tela)
        
        surf_overlay = pygame.Surface((tela.get_width(), tela.get_height()), pygame.SRCALPHA)
        surf_overlay.fill((30, 30, 46, 200)) 
        tela.blit(surf_overlay, (0, 0))

        rect_card = pygame.Rect(0, 0, 400, 250)
        rect_card.center = (tela.get_width()//2, tela.get_height()//2)
        pygame.draw.rect(tela, CARD_BG, rect_card, border_radius=15)
        pygame.draw.rect(tela, TEXTO_DESTAQUE, rect_card, width=2, border_radius=15)

        desenhar_texto_centralizado(tela, "Escolha o Novo Algoritmo", f_titulo, TEXTO_PRINCIPAL, rect_card.y + 20, shadow=False)
        
        # Caixa de Seleção do Algoritmo
        rect_dd_main = pygame.Rect(rect_card.x + 40, rect_card.y + 70, 320, 45)
        hover_dd = rect_dd_main.collidepoint(mx, my)
        pygame.draw.rect(tela, TILE_VAZIO if not hover_dd else (69, 70, 88), rect_dd_main, border_radius=8)
        pygame.draw.rect(tela, VERMELHO_ALERTA, rect_dd_main, width=2, border_radius=8)
        
        texto_algo = f"[{algo_idx+1}] {algoritmos[algo_idx][0]}"
        surf_algo = f_dropdown.render(texto_algo, True, TEXTO_PRINCIPAL)
        tela.blit(surf_algo, (rect_dd_main.x + 15, rect_dd_main.centery - surf_algo.get_height()//2))
        
        seta_dd = "v" if not dropdown_aberto else "^"
        surf_seta = f_dropdown.render(seta_dd, True, VERMELHO_ALERTA)
        tela.blit(surf_seta, (rect_dd_main.right - 30, rect_dd_main.centery - surf_seta.get_height()//2))

        # Botão de Confirmar
        rect_btn_conf = pygame.Rect(rect_card.x + 100, rect_card.y + 160, 200, 45)
        hover_conf = rect_btn_conf.collidepoint(mx, my)
        pygame.draw.rect(tela, TILE_COMPLETO if not hover_conf else (186, 247, 181), rect_btn_conf, border_radius=8)
        surf_conf = f_pequena.render("Confirmar (ENTER)", True, BG_COLOR)
        tela.blit(surf_conf, (rect_btn_conf.centerx - surf_conf.get_width()//2, rect_btn_conf.centery - surf_conf.get_height()//2))

        # Lista do Dropdown expandida
        rects_opcoes = []
        if dropdown_aberto:
            rect_dd_list = pygame.Rect(rect_dd_main.x, rect_dd_main.bottom + 5, 320, len(algoritmos) * 40 + 10)
            pygame.draw.rect(tela, (40, 40, 56), rect_dd_list, border_radius=8)
            pygame.draw.rect(tela, VERMELHO_ALERTA, rect_dd_list, width=2, border_radius=8)
            
            for i, algo in enumerate(algoritmos):
                rect_op = pygame.Rect(rect_dd_list.x + 5, rect_dd_list.y + 5 + i*40, 310, 35)
                rects_opcoes.append(rect_op)
                hover_op = rect_op.collidepoint(mx, my)
                
                if hover_op or i == algo_idx:
                    pygame.draw.rect(tela, TILE_VAZIO, rect_op, border_radius=5)
                    
                cor_texto = VERMELHO_ALERTA if i == algo_idx else TEXTO_PRINCIPAL
                surf_op = f_pequena.render(f"{i+1}. {algo[0]}", True, cor_texto)
                tela.blit(surf_op, (rect_op.x + 10, rect_op.centery - surf_op.get_height()//2))

        pygame.display.flip()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
                
            if evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    if dropdown_aberto:
                        clicou_opcao = False
                        for i, rect_op in enumerate(rects_opcoes):
                            if rect_op.collidepoint(evento.pos):
                                algo_idx = i
                                dropdown_aberto = False
                                clicou_opcao = True
                                break
                        if not clicou_opcao:
                            dropdown_aberto = False
                    else:
                        if rect_dd_main.collidepoint(evento.pos):
                            dropdown_aberto = True
                        elif rect_btn_conf.collidepoint(evento.pos):
                            esperando = False

            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RIGHT: algo_idx = (algo_idx + 1) % 5
                elif evento.key == pygame.K_LEFT: algo_idx = (algo_idx - 1) % 5
                elif evento.key == pygame.K_1: algo_idx = 0; dropdown_aberto = False
                elif evento.key == pygame.K_2: algo_idx = 1; dropdown_aberto = False
                elif evento.key == pygame.K_3: algo_idx = 2; dropdown_aberto = False
                elif evento.key == pygame.K_4: algo_idx = 3; dropdown_aberto = False
                elif evento.key == pygame.K_5: algo_idx = 4; dropdown_aberto = False
                elif evento.key == pygame.K_RETURN:
                    esperando = False
                    
    return algoritmos[algo_idx][1]

def main():
    global modo_automatico, busca_concluida, indice_velocidade, movimentos_atuais
    global algoritmo_atual, proximos_bfs
    
    pygame.init()
    pygame.display.set_caption("Rescue Maze Simulator")
    relogio = pygame.time.Clock()

    while True: 
        tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
        
        linhas, colunas, modo, funcao_algoritmo = tela_inicio(tela)
        
        area_util_altura = ALTURA_TELA - ALTURA_UI
        tamanho_tile = min(LARGURA_TELA // colunas, area_util_altura // linhas)
        
        offset_x = (LARGURA_TELA - (colunas * tamanho_tile)) // 2
        offset_y = (area_util_altura - (linhas * tamanho_tile)) // 2

        arena = Arena(linhas, colunas, tamanho_tile, offset_x, offset_y)
        
        if modo == 'A':
            arena.gerar_labirinto_aleatorio()
        elif modo == 'M':
            visitados.clear()
            completos.clear()
            tela_construcao(tela, arena)

        robo = Robo(arena, 0, 0)
        
        visitados.clear()
        completos.clear()
        movimentos_atuais.clear() 
        proximos_bfs.clear() 
        algoritmo_atual = funcao_algoritmo.__name__ 
        modo_automatico = False
        busca_concluida = False
        indice_velocidade = 1 

        rodando = True
        while rodando:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_SPACE and not busca_concluida:
                        try:
                            funcao_algoritmo(robo, arena, tela)
                            busca_concluida = True 
                        except VoltarMenu:
                            rodando = False 
                        
                if evento.type == pygame.MOUSEBUTTONDOWN:
                    if get_rect_botao_auto(tela).collidepoint(evento.pos):
                        if busca_concluida:
                            rodando = False 
                        else:
                            modo_automatico = True
                            try:
                                funcao_algoritmo(robo, arena, tela)
                                busca_concluida = True 
                            except VoltarMenu:
                                rodando = False 
                
                    elif get_rect_botao_vel(tela).collidepoint(evento.pos):
                        if busca_concluida:
                            funcao_algoritmo = tela_escolher_algoritmo(tela, arena, robo)
                            algoritmo_atual = funcao_algoritmo.__name__ 
                            robo = Robo(arena, 0, 0)
                            visitados.clear()
                            completos.clear()
                            movimentos_atuais.clear()
                            proximos_bfs.clear()
                            modo_automatico = False
                            busca_concluida = False
                        else:
                            indice_velocidade = (indice_velocidade + 1) % 4
                        
                    elif get_rect_botao_sair(tela).collidepoint(evento.pos):
                        rodando = False 

            if rodando:
                renderizar_tela_jogo(tela, arena, robo)
                relogio.tick(FPS)

if __name__ == "__main__":
    main()