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
        trim_x, trim_y = self._trim_for_tile(logical)
        

        if self.surface and tile_id in self.rects:
            area = self.rects[tile_id].copy()
            dest_x, dest_y = px, py

            if trim_x:
                area.x += 1
                area.width = max(0, area.width - 2)
                dest_x += 1
            if trim_y:
                area.y += 1
                area.height = max(0, area.height - 2)
                dest_y += 1

            surf.blit(self.surface, (dest_x, dest_y), area)
            return

        color = CFG.COLOR_FLOOR if logical == CFG.FLOOR else CFG.COLOR_WALL
        rect = pygame.Rect(px, py, CFG.TILE_SIZE, CFG.TILE_SIZE)
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
                rect = pygame.Rect(px, py, ts, ts)
                trim_x, trim_y = self._trim_for_tile(tile_id)
                if trim_x:
                    rect.x += 1
                    rect.width = max(0, rect.width - 2)
                if trim_y:
                    rect.y += 1
                    rect.height = max(0, rect.height - 2)
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

        if down_right and not (down or right):
            return CFG.WALL_CORNER_NW
        if down_left and not (down or left):
            return CFG.WALL_CORNER_NE
        if up_right and not (up or right):
            return CFG.WALL_CORNER_SW
        if up_left and not (up or left):
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

        for ny in range(ty - 1, ty + 2):
            if not (0 <= ny < height):
                continue
            row = tiles[ny]
            for nx in range(tx - 1, tx + 2):
                if nx == tx and ny == ty:
                    continue
                if 0 <= nx < len(row) and row[nx] == CFG.FLOOR:
                    return True
        return False

    def _trim_for_tile(self, tile_id: int) -> tuple[bool, bool]:
        if tile_id in {
            CFG.WALL_CORNER_NW,
            CFG.WALL_CORNER_NE,
            CFG.WALL_CORNER_SW,
            CFG.WALL_CORNER_SE,
        }:
            return False, False

        if tile_id == CFG.WALL:
            return True, True

        if tile_id in {CFG.WALL_LEFT, CFG.WALL_RIGHT}:
            return True, False

        if tile_id in {CFG.WALL_TOP, CFG.WALL_BOTTOM}:
            return False, True

        return False, False
