from typing import Iterator, List

import pygame
from Config import CFG

class Projectile:
    def __init__(
        self,
        x,
        y,
        dx,
        dy,
        speed=320.0,
        radius=4,
        color=(255,230,140),
        effects: list[dict] | tuple[dict, ...] | None = None,
        damage: float = 1.0,
        is_boss_projectile: bool = False,
    ):
        self.x, self.y = x, y
        self.dx, self.dy = dx, dy
        self.speed = speed
        self.radius = radius
        self.alive = True
        self.ttl = 3.5
        self.color = color if color is not None else (255, 230, 140)
        # Temporizador para ignorar colisiones con el jugador tras un dash.
        self.ignore_player_timer = 0.0
        self.effects: tuple[dict, ...] = tuple(effects) if effects else ()
        self.damage: float = damage
        self.is_boss_projectile = is_boss_projectile

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
        cx, cy = int(self.x), int(self.y)
        core_r = max(1, int(self.radius))
        outline_r = core_r + 1
        glow_r = outline_r + 1 + (1 if self.is_boss_projectile else 0)

        base_color = self.color
        shadow_color = tuple(max(0, int(c * 0.35)) for c in base_color)
        outline_color = tuple(min(255, int(c * 0.9) + 40) for c in base_color)
        highlight_color = tuple(min(255, int(c * 0.8) + 70) for c in base_color)

        # Halo suave (sombra)
        pygame.draw.circle(surf, shadow_color, (cx + 1, cy + 1), glow_r)
        # Núcleo principal
        pygame.draw.circle(surf, base_color, (cx, cy), core_r)
        # Borde brillante
        pygame.draw.circle(surf, outline_color, (cx, cy), outline_r, width=1)
        # Brillo desplazado para simular luz
        pygame.draw.circle(
            surf,
            highlight_color,
            (cx - core_r // 3, cy - core_r // 3),
            max(1, core_r // 2),
        )


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
