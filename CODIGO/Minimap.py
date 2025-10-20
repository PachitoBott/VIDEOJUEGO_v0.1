import pygame
from typing import Tuple
from Config import CFG
from Dungeon import Dungeon

class Minimap:
    def __init__(self, cell: int = 10, padding: int = 6) -> None:
        self.cell = cell
        self.padding = padding
        self.bg = (20, 20, 26)
        self.grid = (60, 60, 80)
        self.explored = (140, 140, 160)
        self.current = (240, 220, 120)

    def render(self, dungeon: Dungeon) -> pygame.Surface:
        w = dungeon.grid_w * self.cell + self.padding * 2
        h = dungeon.grid_h * self.cell + self.padding * 2
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        # Fondo
        pygame.draw.rect(surf, self.bg, (0, 0, w, h), border_radius=6)
        # Celdas
        for j in range(dungeon.grid_h):
            for i in range(dungeon.grid_w):
                x = self.padding + i * self.cell
                y = self.padding + j * self.cell
                rect = pygame.Rect(x, y, self.cell - 1, self.cell - 1)
                color = self.grid
                if (i, j) in dungeon.explored:
                    color = self.explored
                if (i, j) == (dungeon.i, dungeon.j):
                    color = self.current
                pygame.draw.rect(surf, color, rect, border_radius=2)
        return surf
