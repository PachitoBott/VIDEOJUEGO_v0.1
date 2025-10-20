import pygame, math
from Entity import Entity
from Config import CFG

class Player(Entity):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, w=12, h=12, speed=120.0)

    def update(self, dt: float, room) -> None:
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        m = math.hypot(dx, dy)
        if m: dx, dy = dx/m, dy/m
        self.move(dx, dy, dt, room)

    def draw(self, surf: pygame.Surface) -> None:
        super().draw(surf, CFG.COLOR_PLAYER)
