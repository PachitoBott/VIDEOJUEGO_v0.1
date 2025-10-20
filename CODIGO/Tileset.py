import pygame
from typing import Optional
from Config import CFG

class Tileset:
    def __init__(self) -> None:
        self.surface: Optional[pygame.Surface] = None
        self.rects = {}
        if CFG.TILESET_PATH:
            try:
                img = pygame.image.load(CFG.TILESET_PATH).convert_alpha()
                self.surface = img
                self.rects[CFG.FLOOR] = pygame.Rect(0, 0, CFG.TILE_SIZE, CFG.TILE_SIZE)
                self.rects[CFG.WALL]  = pygame.Rect(CFG.TILE_SIZE, 0, CFG.TILE_SIZE, CFG.TILE_SIZE)
            except Exception:
                self.surface = None

    def draw_tile(self, surf: pygame.Surface, tile_id: int, px: int, py: int) -> None:
        if self.surface and tile_id in self.rects:
            surf.blit(self.surface, (px, py), self.rects[tile_id]); return
        color = CFG.COLOR_FLOOR if tile_id == CFG.FLOOR else CFG.COLOR_WALL
        pygame.draw.rect(surf, color, (px, py, CFG.TILE_SIZE, CFG.TILE_SIZE))
