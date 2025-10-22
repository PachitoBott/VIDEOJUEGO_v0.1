import pygame
from Config import CFG

class Projectile:
    def __init__(self, x: float, y: float, dx: float, dy: float,
                 speed: float = 320.0, radius: int = 3, color=(255, 230, 140)):
        self.x, self.y = x, y
        self.dx, self.dy = dx, dy
        self.speed = speed
        self.radius = radius
        self.alive = True
        self.ttl = 2.0
        self.color = color

    def rect(self) -> pygame.Rect:
        r = self.radius
        return pygame.Rect(int(self.x - r), int(self.y - r), r * 2, r * 2)

    def update(self, dt: float, room) -> None:
        if not self.alive:
            return
        self.ttl -= dt
        if self.ttl <= 0:
            self.alive = False
            return

        step_x = self.dx * self.speed * dt
        step_y = self.dy * self.speed * dt

        self.x += step_x
        if self._collides(room):
            self.x -= step_x
            self.alive = False
            return

        self.y += step_y
        if self._collides(room):
            self.y -= step_y
            self.alive = False

    def _collides(self, room) -> bool:
        r = self.rect()
        ts = CFG.TILE_SIZE
        x0, y0 = r.left // ts, r.top // ts
        x1, y1 = (r.right - 1) // ts, (r.bottom - 1) // ts
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if room.is_blocked(tx, ty):
                    return True
        return False

    def draw(self, surf: pygame.Surface) -> None:
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
