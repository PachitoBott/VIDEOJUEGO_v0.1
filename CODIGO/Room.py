import pygame
import random
from typing import Dict, Tuple, Optional, List
from Config import CFG
from Enemy import Enemy

class Room:
    """
    Un cuarto sobre una grilla MAP_W x MAP_H (en tiles).
    - `tiles` = 1 (pared), 0 (suelo)
    - `bounds` = (rx, ry, rw, rh) en tiles: rectángulo de la habitación dentro del mapa
    - `doors` = dict con direcciones "N","S","E","W" -> bool (existe puerta hacia ese vecino)
    - Enemigos se generan 1 sola vez con `ensure_spawn(...)`
    """

    def __init__(self) -> None:
        # mapa lleno de paredes por defecto
        self.tiles: List[List[int]] = [[CFG.WALL for _ in range(CFG.MAP_W)] for _ in range(CFG.MAP_H)]
        self.bounds: Optional[Tuple[int, int, int, int]] = None  # (rx, ry, rw, rh) en tiles
        self.doors: Dict[str, bool] = {"N": False, "S": False, "E": False, "W": False}

        # contenido dinámico
        self.enemies: List[Enemy] = []
        self._spawn_done: bool = False

    # ------------------------------------------------------------------ #
    # Construcción de la habitación
    # ------------------------------------------------------------------ #
    def build_centered(self, rw: int, rh: int) -> None:
        """
        Talla un rectángulo de suelo centrado en el mapa (en tiles).
        rw/rh son el tamaño de la habitación en tiles.
        """
        rx = CFG.MAP_W // 2 - rw // 2
        ry = CFG.MAP_H // 2 - rh // 2
        self.bounds = (rx, ry, rw, rh)

        # Suelo dentro de la habitación
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                if 0 <= x < CFG.MAP_W and 0 <= y < CFG.MAP_H:
                    self.tiles[y][x] = 0

    # ------------------------------------------------------------------ #
    # Corredores cortos (visuales) hacia las puertas
    # ------------------------------------------------------------------ #
    def carve_corridors(self, width_tiles: int = 2, length_tiles: int = 3) -> None:
        """
        Abre pasillos cortos desde los bordes de la sala hacia la dirección de cada puerta.
        Usa el bounding box de la sala: (rx, ry, rw, rh) en tiles.
        """
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds

        def carve_rect(x: int, y: int, w: int, h: int) -> None:
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    if 0 <= xx < CFG.MAP_W and 0 <= yy < CFG.MAP_H:
                        self.tiles[yy][xx] = 0

        half_w = max(1, width_tiles // 2)

        # Norte
        if self.doors.get("N"):
            cx = rx + rw // 2
            carve_rect(cx - half_w, ry - length_tiles, width_tiles, length_tiles)

        # Sur
        if self.doors.get("S"):
            cx = rx + rw // 2
            carve_rect(cx - half_w, ry + rh, width_tiles, length_tiles)

        # Este
        if self.doors.get("E"):
            cy = ry + rh // 2
            carve_rect(rx + rw, cy - half_w, length_tiles, width_tiles)

        # Oeste
        if self.doors.get("W"):
            cy = ry + rh // 2
            carve_rect(rx - length_tiles, cy - half_w, length_tiles, width_tiles)

    # ------------------------------------------------------------------ #
    # Spawning de enemigos (una sola vez por cuarto)
    # ------------------------------------------------------------------ #
    def ensure_spawn(self, difficulty: int = 1) -> None:
        if self._spawn_done or self.bounds is None:
            return
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE

        n = max(1, min(6, 1 + difficulty))  # cantidad según dificultad (cap 6)
        for _ in range(n):
            tx = random.randint(rx + 1, rx + rw - 2)
            ty = random.randint(ry + 1, ry + rh - 2)
            px = tx * ts + ts // 2 - 6
            py = ty * ts + ts // 2 - 6
            self.enemies.append(Enemy(px, py))

        self._spawn_done = True

    # ------------------------------------------------------------------ #
    # Colisiones y triggers de puertas
    # ------------------------------------------------------------------ #
    def is_blocked(self, tx: int, ty: int) -> bool:
        """¿El tile (tx,ty) es sólido (pared)?"""
        if not (0 <= tx < CFG.MAP_W and 0 <= ty < CFG.MAP_H):
            return True
        return self.tiles[ty][tx] == CFG.WALL

    def _door_trigger_rects(self) -> Dict[str, pygame.Rect]:
        """
        Rectángulos en píxeles que detectan cuando el jugador pisa una puerta.
        """
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE

        left   = rx * ts
        right  = (rx + rw) * ts
        top    = ry * ts
        bottom = (ry + rh) * ts
        band   = max(6, ts // 3)  # banda más finita para evitar ping-pong

        rects: Dict[str, pygame.Rect] = {}
        if self.doors.get("N"):
            rects["N"] = pygame.Rect(left + rw*ts//2 - band//2, top - band, band, band)
        if self.doors.get("S"):
            rects["S"] = pygame.Rect(left + rw*ts//2 - band//2, bottom, band, band)
        if self.doors.get("E"):
            rects["E"] = pygame.Rect(right, top + rh*ts//2 - band//2, band, band)
        if self.doors.get("W"):
            rects["W"] = pygame.Rect(left - band, top + rh*ts//2 - band//2, band, band)
        return rects

    def check_exit(self, player_rect: pygame.Rect) -> Optional[str]:
        """Devuelve 'N','S','E','W' si el jugador toca una puerta; en caso contrario None."""
        for d, r in self._door_trigger_rects().items():
            if player_rect.colliderect(r):
                return d
        return None

    # ------------------------------------------------------------------ #
    # Utilidades
    # ------------------------------------------------------------------ #
    def center_px(self) -> Tuple[int, int]:
        """Centro de la sala (en píxeles), útil para ubicar al jugador."""
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        cx = (rx + rw // 2) * ts
        cy = (ry + rh // 2) * ts
        return cx, cy

    # ------------------------------------------------------------------ #
    # Dibujo
    # ------------------------------------------------------------------ #
    def draw(self, surf: pygame.Surface, tileset) -> None:
        """
        Dibuja el room en `surf`. Si tu `Tileset` tiene un método específico,
        úsalo; si no, renderizo con rectángulos de colores.
        """
        ts = CFG.TILE_SIZE
        # Si tu tileset expone un método de dibujado por mapa, úsalo:
        if hasattr(tileset, "draw_map"):
            tileset.draw_map(surf, self.tiles)  # <- adapta si tu Tileset usa otra firma
            return

        # Fallback: pintar a color
        wall = (60, 60, 70)
        floor = (110, 85, 70)
        for ty in range(CFG.MAP_H):
            for tx in range(CFG.MAP_W):
                color = floor if self.tiles[ty][tx] == 0 else wall
                pygame.draw.rect(surf, color, pygame.Rect(tx*ts, ty*ts, ts, ts))
