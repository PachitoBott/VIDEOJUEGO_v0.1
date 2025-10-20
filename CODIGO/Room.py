import pygame
from typing import Optional, Tuple
from Config import CFG

class Room:
    def __init__(self) -> None:
        self.w, self.h = CFG.MAP_W, CFG.MAP_H
        self.grid = [[CFG.WALL for _ in range(self.w)] for _ in range(self.h)]
        self.bounds: Optional[Tuple[int,int,int,int]] = None

    def build_centered(self, rw: int, rh: int) -> None:
        rx, ry = (self.w - rw)//2, (self.h - rh)//2
        for y in range(ry, ry+rh):
            for x in range(rx, rx+rw):
                self.grid[y][x] = CFG.FLOOR
        self.bounds = (rx, ry, rw, rh)

    def is_blocked(self, tx: int, ty: int) -> bool:
        return not (0 <= tx < self.w and 0 <= ty < self.h) or self.grid[ty][tx] == CFG.WALL

    def center_px(self) -> Tuple[int,int]:
        if not self.bounds: return (CFG.SCREEN_W//2, CFG.SCREEN_H//2)
        rx, ry, rw, rh = self.bounds
        return ((rx+rw//2)*CFG.TILE_SIZE, (ry+rh//2)*CFG.TILE_SIZE)

    def draw(self, surf: pygame.Surface, tileset) -> None:
        surf.fill(CFG.COLOR_BG)
        for y in range(self.h):
            for x in range(self.w):
                tileset.draw_tile(surf, self.grid[y][x], x*CFG.TILE_SIZE, y*CFG.TILE_SIZE)
