import pygame
from typing import Optional, Sequence
from Config import CFG

class Tileset:
    def __init__(self) -> None:
        self.surface: Optional[pygame.Surface] = None
        self.rects = {}
        if CFG.TILESET_PATH:
            try:
                img = pygame.image.load(CFG.TILESET_PATH).convert_alpha()
                tile_defs: dict[int, tuple[int, int]] = {
                    CFG.FLOOR: (0, 0),
                    CFG.WALL: (1, 0),
                    CFG.WALL_TOP: (1, 0),
                    CFG.WALL_BOTTOM: (2, 0),
                    CFG.WALL_LEFT: (3, 0),
                    CFG.WALL_RIGHT: (4, 0),
                    CFG.WALL_CORNER_NW: (5, 0),
                    CFG.WALL_CORNER_NE: (6, 0),
                    CFG.WALL_CORNER_SW: (7, 0),
                    CFG.WALL_CORNER_SE: (8, 0),
                }

                tile_size = CFG.TILE_SIZE
                width, height = img.get_width(), img.get_height()
                for tile_id, (col, row) in tile_defs.items():
                    x = col * tile_size
                    y = row * tile_size
                    if x + tile_size <= width and y + tile_size <= height:
                        self.rects[tile_id] = pygame.Rect(x, y, tile_size, tile_size)
                if self.rects:
                    self.surface = img
            except Exception:
                self.surface = None

    def draw_tile(
        self,
        surf: pygame.Surface,
        tile_id: int,
        px: int,
        py: int,
        logical_id: Optional[int] = None,
    ) -> None:
        logical = tile_id if logical_id is None else logical_id
        left_trim, top_trim, right_trim, bottom_trim = self._trim_for_tile(logical)

        if self.surface and tile_id in self.rects:
            area = self.rects[tile_id].copy()
            dest_x = px + left_trim
            dest_y = py + top_trim

            if left_trim:
                area.x += left_trim
                area.width = max(0, area.width - left_trim)
            if right_trim:
                area.width = max(0, area.width - right_trim)
            if top_trim:
                area.y += top_trim
                area.height = max(0, area.height - top_trim)
            if bottom_trim:
                area.height = max(0, area.height - bottom_trim)

            surf.blit(self.surface, (dest_x, dest_y), area)
            return

        color = CFG.COLOR_FLOOR if logical == CFG.FLOOR else CFG.COLOR_WALL
        rect = pygame.Rect(
            px + left_trim,
            py + top_trim,
            CFG.TILE_SIZE - left_trim - right_trim,
            CFG.TILE_SIZE - top_trim - bottom_trim,
        )
        pygame.draw.rect(surf, color, rect)

    # -----------------------------------------------------------
    # Dibujo de mapas completos
    # -----------------------------------------------------------
    def draw_map(self, surf: pygame.Surface, tiles: Sequence[Sequence[int]]) -> bool:
        """Dibuja el mapa completo usando los sprites disponibles.

        Devuelve True si se usaron sprites; False si cayó en el fallback.
        """
        if not self.surface:
            self._draw_map_fallback(surf, tiles)
            return False

        used_sprite = False
        ts = CFG.TILE_SIZE

        if CFG.FLOOR in self.rects:
            used_sprite = True
            for ty, row in enumerate(tiles):
                for tx, tile_id in enumerate(row):
                    if tile_id == CFG.FLOOR:
                        px = tx * ts
                        py = ty * ts
                        self.draw_tile(surf, CFG.FLOOR, px, py)
        else:
            self._draw_floor_fallback(surf, tiles)

        for ty, row in enumerate(tiles):
            for tx, tile_id in enumerate(row):
                if not self._should_draw_wall(tiles, tx, ty):
                    continue

                px = tx * ts
                py = ty * ts
                variant = self._wall_variant(tiles, tx, ty)
                sprite_id = variant

                if sprite_id in self.rects:
                    used_sprite = True
                elif CFG.WALL in self.rects:
                    sprite_id = CFG.WALL
                    used_sprite = True

                self.draw_tile(surf, sprite_id, px, py, logical_id=variant)

        return used_sprite

    def _draw_map_fallback(self, surf: pygame.Surface, tiles: Sequence[Sequence[int]]) -> None:
        self._draw_floor_fallback(surf, tiles)
        ts = CFG.TILE_SIZE
        for ty, row in enumerate(tiles):
            for tx, tile_id in enumerate(row):
                if not self._should_draw_wall(tiles, tx, ty):
                    continue
                px = tx * ts
                py = ty * ts
                left_trim, top_trim, right_trim, bottom_trim = self._trim_for_tile(tile_id)
                rect = pygame.Rect(
                    px + left_trim,
                    py + top_trim,
                    ts - left_trim - right_trim,
                    ts - top_trim - bottom_trim,
                )
                pygame.draw.rect(surf, CFG.COLOR_WALL, rect)

    def _draw_floor_fallback(self, surf: pygame.Surface, tiles: Sequence[Sequence[int]]) -> None:
        ts = CFG.TILE_SIZE
        for ty, row in enumerate(tiles):
            for tx, tile_id in enumerate(row):
                if tile_id == CFG.FLOOR:
                    px = tx * ts
                    py = ty * ts
                    pygame.draw.rect(surf, CFG.COLOR_FLOOR, (px, py, ts, ts))

    def _wall_variant(self, tiles: Sequence[Sequence[int]], tx: int, ty: int) -> int:
        def is_floor(x: int, y: int) -> bool:
            if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]):
                return tiles[y][x] == CFG.FLOOR
            return False

        up = is_floor(tx, ty - 1)
        down = is_floor(tx, ty + 1)
        left = is_floor(tx - 1, ty)
        right = is_floor(tx + 1, ty)

        up_left = is_floor(tx - 1, ty - 1)
        up_right = is_floor(tx + 1, ty - 1)
        down_left = is_floor(tx - 1, ty + 1)
        down_right = is_floor(tx + 1, ty + 1)

        if down and not up and not left and down_right and not down_left:
            return CFG.WALL_CORNER_NW
        if down and not up and not right and down_left and not down_right:
            return CFG.WALL_CORNER_NE
        if up and not down and not left and up_right and not up_left:
            return CFG.WALL_CORNER_SW
        if up and not down and not right and up_left and not up_right:
            return CFG.WALL_CORNER_SE

        if down and not up:
            return CFG.WALL_TOP
        if up and not down:
            return CFG.WALL_BOTTOM
        if right and not left:
            return CFG.WALL_LEFT
        if left and not right:
            return CFG.WALL_RIGHT

        return CFG.WALL

    def _should_draw_wall(self, tiles: Sequence[Sequence[int]], tx: int, ty: int) -> bool:
        if tiles[ty][tx] == CFG.FLOOR:
            return False

        height = len(tiles)

        neighbours = ((tx - 1, ty), (tx + 1, ty), (tx, ty - 1), (tx, ty + 1))
        for nx, ny in neighbours:
            if 0 <= ny < height and 0 <= nx < len(tiles[ny]):
                if tiles[ny][nx] == CFG.FLOOR:
                    return True
        return False

    def _trim_for_tile(self, tile_id: int) -> tuple[int, int, int, int]:
        """Devuelve el recorte (izq, arriba, der, abajo) para un tile."""
        return 0, 0, 0, 0

