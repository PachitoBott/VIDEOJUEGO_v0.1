from typing import Callable, Iterator, List

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
        on_impact: Callable[["Projectile", tuple[float, float], tuple[float, float]], None] | None = None,
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
        self.on_impact = on_impact

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
            self._trigger_impact()
            return

        self.y += step_y
        if self._collides(room):
            self.y -= step_y
            self.alive = False
            self._trigger_impact()

    def _trigger_impact(self) -> None:
        if not callable(self.on_impact):
            return

        direction = pygame.Vector2(self.dx, self.dy)
        if direction.length_squared() > 0.0:
            direction = direction.normalize()
        else:
            direction = pygame.Vector2(1, 0)

        self.on_impact(self, (self.x, self.y), (direction.x, direction.y))

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
        core_r = max(2, int(self.radius))
        boss_bonus = 1 if self.is_boss_projectile else 0
        rim_r = core_r + 1 + boss_bonus
        glow_r = rim_r + 1 + boss_bonus

        # Colours tuned for a luminous white core with a coloured rim and halo
        rim_color = self.color
        glow_color = (*rim_color, 55)
        bright_rim_color = (*rim_color, 155)
        core_color = (255, 255, 255, 245)
        highlight_color = (255, 255, 255, 180)

        size = glow_r * 2 + 2
        temp_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        center = (glow_r + 1, glow_r + 1)

        pygame.draw.circle(temp_surf, glow_color, center, glow_r)
        pygame.draw.circle(temp_surf, bright_rim_color, center, rim_r)
        pygame.draw.circle(temp_surf, core_color, center, core_r)
        pygame.draw.circle(
            temp_surf,
            highlight_color,
            (center[0] - core_r // 3, center[1] - core_r // 3),
            max(1, core_r // 2),
        )

        surf.blit(temp_surf, (cx - glow_r - 1, cy - glow_r - 1))


class ProjectileGroup:
    """Contenedor liviano para actualizar/dibujar proyectiles."""

    def __init__(self) -> None:
        self._items: List[Projectile] = []
        self.on_impact: Callable[[Projectile, tuple[float, float], tuple[float, float]], None] | None = None

    def set_impact_callback(
        self, callback: Callable[[Projectile, tuple[float, float], tuple[float, float]], None] | None
    ) -> None:
        self.on_impact = callback

    def add(self, projectile: Projectile) -> None:
        if getattr(projectile, "on_impact", None) is None and callable(self.on_impact):
            projectile.on_impact = self.on_impact
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
