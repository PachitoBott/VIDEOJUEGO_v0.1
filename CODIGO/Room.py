import pygame
from typing import Optional, Tuple, Dict
from Config import CFG

class Room:
    def __init__(self) -> None:
        self.w, self.h = CFG.MAP_W, CFG.MAP_H
        self.grid = [[CFG.WALL for _ in range(self.w)] for _ in range(self.h)]
        self.bounds: Optional[Tuple[int,int,int,int]] = None  # (rx, ry, rw, rh) en tiles
        self.doors: Dict[str, bool] = {"N": False, "S": False, "E": False, "W": False}

    def build_centered(self, rw: int, rh: int) -> None:
        rx = (self.w - rw) // 2
        ry = (self.h - rh) // 2
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                self.grid[y][x] = CFG.FLOOR
        self.bounds = (rx, ry, rw, rh)

    def is_blocked(self, tx: int, ty: int) -> bool:
        return not (0 <= tx < self.w and 0 <= ty < self.h) or self.grid[ty][tx] == CFG.WALL

    def center_px(self) -> Tuple[int,int]:
        if not self.bounds: return (CFG.SCREEN_W//2, CFG.SCREEN_H//2)
        rx, ry, rw, rh = self.bounds
        return ((rx+rw//2)*CFG.TILE_SIZE, (ry+rh//2)*CFG.TILE_SIZE)

    # ---------- Corredores cortos ----------
    def carve_corridors(self, width_tiles: int = 2, length_tiles: int = 3) -> None:
        """Cava un pequeño corredor (piso) que sale desde cada puerta activa."""
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        cx = rx + rw // 2
        cy = ry + rh // 2

        def carve_rect(tx0, ty0, tw, th):
            for ty in range(max(0, ty0), min(self.h, ty0 + th)):
                for tx in range(max(0, tx0), min(self.w, tx0 + tw)):
                    self.grid[ty][tx] = CFG.FLOOR

        if self.doors.get("N"):
            carve_rect(cx - width_tiles//2, ry - length_tiles, width_tiles, length_tiles)
        if self.doors.get("S"):
            carve_rect(cx - width_tiles//2, ry + rh, width_tiles, length_tiles)
        if self.doors.get("W"):
            carve_rect(rx - length_tiles, cy - width_tiles//2, length_tiles, width_tiles)
        if self.doors.get("E"):
            carve_rect(rx + rw, cy - width_tiles//2, length_tiles, width_tiles)

    # ---------- Puertas / salidas ----------
    def _door_trigger_rects(self) -> Dict[str, pygame.Rect]:
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        left   = rx * ts
        right  = (rx + rw) * ts
        top    = ry * ts
        bottom = (ry + rh) * ts
        band = ts // 2
        w2 = ts * 2
        cx = (left + right) // 2 - w2 // 2
        cy = (top + bottom) // 2 - w2 // 2
        return {
            "N": pygame.Rect(cx, top + 2, w2, band),
            "S": pygame.Rect(cx, bottom - band - 2, w2, band),
            "W": pygame.Rect(left + 2, cy, band, w2),
            "E": pygame.Rect(right - band - 2, cy, band, w2),
        }

    def check_exit(self, player_rect: pygame.Rect) -> Optional[str]:
        rects = self._door_trigger_rects()
        for d, r in rects.items():
            if self.doors.get(d, False) and r.colliderect(player_rect):
                return d
        return None

    # ---------- Render ----------
    def draw(self, surf: pygame.Surface, tileset) -> None:
        surf.fill(CFG.COLOR_BG)
        for y in range(self.h):
            for x in range(self.w):
                tileset.draw_tile(surf, self.grid[y][x], x*CFG.TILE_SIZE, y*CFG.TILE_SIZE)

        # Visual de puertas
        if self.bounds:
            rects = self._door_trigger_rects()
            for d, r in rects.items():
                if self.doors.get(d, False):
                    pygame.draw.rect(surf, (80, 120, 160), r)
