import pygame
from typing import Dict, Optional, Sequence

from Config import CFG
from AssetPack import AssetPack


class Tileset:
    def __init__(self, assets: Optional[AssetPack] = None) -> None:
        self.assets = assets
        self.surface: Optional[pygame.Surface] = None
        self.rects: Dict[int, pygame.Rect] = {}
        self.tile_surfaces: Dict[int, pygame.Surface] = {}

        self._init_from_asset_pack()
        if CFG.TILESET_PATH and not self.tile_surfaces:
            self._init_from_tileset_path()

    # ------------------------------------------------------------------ #
    def draw_tile(self, surf: pygame.Surface, tile_id: int, px: int, py: int) -> None:
        if tile_id in self.tile_surfaces:
            surf.blit(self.tile_surfaces[tile_id], (px, py))
            return
        if self.surface and tile_id in self.rects:
            surf.blit(self.surface, (px, py), self.rects[tile_id])
            return
        color = CFG.COLOR_FLOOR if tile_id == CFG.FLOOR else CFG.COLOR_WALL
        pygame.draw.rect(surf, color, (px, py, CFG.TILE_SIZE, CFG.TILE_SIZE))

    def draw_map(self, surf: pygame.Surface, tiles: Sequence[Sequence[int]]) -> None:
        ts = CFG.TILE_SIZE
        for ty, row in enumerate(tiles):
            for tx, tile_id in enumerate(row):
                self.draw_tile(surf, tile_id, tx * ts, ty * ts)

    # ------------------------------------------------------------------ #
    def _init_from_tileset_path(self) -> None:
        try:
            img = pygame.image.load(CFG.TILESET_PATH).convert_alpha()
        except Exception:
            self.surface = None
            return
        self.surface = img
        self.rects[CFG.FLOOR] = pygame.Rect(0, 0, CFG.TILE_SIZE, CFG.TILE_SIZE)
        self.rects[CFG.WALL] = pygame.Rect(CFG.TILE_SIZE, 0, CFG.TILE_SIZE, CFG.TILE_SIZE)

    def _init_from_asset_pack(self) -> None:
        if not self.assets:
            return
        mapping = CFG.tile_sprite_ids()
        for tile_id, sprite_id in mapping.items():
            sprite = self.assets.sprite(sprite_id)
            if sprite is None:
                continue
            if sprite.get_width() != CFG.TILE_SIZE or sprite.get_height() != CFG.TILE_SIZE:
                sprite = pygame.transform.smoothscale(sprite, (CFG.TILE_SIZE, CFG.TILE_SIZE))
            self.tile_surfaces[tile_id] = sprite
