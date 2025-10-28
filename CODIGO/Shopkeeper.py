import pygame
from typing import Optional, TYPE_CHECKING

from Config import CFG

if TYPE_CHECKING:  # pragma: no cover
    from AssetPack import AssetPack


class Shopkeeper(pygame.sprite.Sprite):
    def __init__(self, pos, asset_pack: Optional["AssetPack"] = None, sprite_id: Optional[str] = None):
        super().__init__()  # ← SIN argumentos (no pasamos pos aquí)

        self.assets = asset_pack
        self.sprite_id = sprite_id or CFG.shopkeeper_sprite_id()

        # Sprite básico (reemplaza por tu imagen si la tienes)
        self.image = pygame.Surface((16, 16), pygame.SRCALPHA)
        self.image.fill((255, 215, 0))  # dorado placeholder
        if self.assets:
            sprite = self.assets.sprite(self.sprite_id)
            if sprite:
                self.image = sprite.copy()
        self.rect = self.image.get_rect(center=pos)

        self.interact_radius = 22  # px para permitir interacción

    def can_interact(self, player_rect):
        # acepta rect o callable que devuelve rect
        if callable(player_rect):
            player_rect = player_rect()
        if not isinstance(player_rect, pygame.Rect):
            try:
                player_rect = pygame.Rect(*player_rect)
            except Exception:
                return False

        area = self.rect.inflate(self.interact_radius*2, self.interact_radius*2)
        return area.colliderect(player_rect)

    def draw(self, surface):
        if self.assets:
            sprite = self.assets.sprite(self.sprite_id)
            if sprite:
                rect = sprite.get_rect(center=self.rect.center)
                surface.blit(sprite, rect)
                return
        surface.blit(self.image, self.rect)
