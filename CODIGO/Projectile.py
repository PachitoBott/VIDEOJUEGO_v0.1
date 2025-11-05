from typing import Iterator, List

import pygame
from Config import CFG

class Projectile:
    def __init__(self, x, y, dx, dy, speed=320.0, radius=3, color=(255,230,140)):
        self.x, self.y = x, y
        self.dx, self.dy = dx, dy
        self.speed = speed
        self.radius = radius
        self.alive = True
        self.ttl = 3.5
        self.color = color
        # Temporizador para ignorar colisiones con el jugador tras un dash.
        self.ignore_player_timer = 0.0

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

        if self.ignore_player_timer > 0.0:
            self.ignore_player_timer = max(0.0, self.ignore_player_timer - dt)

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

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)


class ProjectileGroup:
    """Contenedor liviano para actualizar/dibujar proyectiles."""

    def __init__(self) -> None:
        self._items: List[Projectile] = []

    def add(self, projectile: Projectile) -> None:
        self._items.append(projectile)

    def clear(self) -> None:
        self._items.clear()

    def update(self, dt: float, room) -> None:
        for projectile in self._items:
            projectile.update(dt, room)
        self.prune()

    def prune(self) -> None:
        self._items = [p for p in self._items if p.alive]

    def draw(self, surf) -> None:
        for projectile in self._items:
            projectile.draw(surf)

    def __iter__(self) -> Iterator[Projectile]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)
