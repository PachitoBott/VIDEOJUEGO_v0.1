# CODIGO/Shopkeeper.py
import pygame

class Shopkeeper(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        # Placeholder si no tienes sprite
        self.image = pygame.Surface((16, 16), pygame.SRCALPHA)
        self.image.fill((255, 215, 0))  # dorado
        self.rect = self.image.get_rect(center=pos)
        self.interact_radius = 22  # px para permitir interacción

    def can_interact(self, player_rect):
        return self.rect.inflate(self.interact_radius*2, self.interact_radius*2).colliderect(player_rect)

    def draw(self, surface):
        surface.blit(self.image, self.rect)
