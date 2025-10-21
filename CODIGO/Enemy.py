import math, pygame
from Entity import Entity
from Config import CFG

class Enemy(Entity):
    def __init__(self, x, y, hp=3, speed=70.0):
        super().__init__(x, y, w=12, h=12, speed=speed)
        self.hp = hp

    def update(self, dt, player, room):
        vx, vy = player.x - self.x, player.y - self.y
        m = math.hypot(vx, vy)
        if m: vx, vy = vx/m, vy/m
        self.move(vx, vy, dt, room)

    def draw(self, surf):  # ← si no lo tienes, agrégalo
        super().draw(surf, (200, 60, 60))
