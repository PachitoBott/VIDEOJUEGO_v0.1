"""Definiciones y factoría de armas del jugador."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Tuple

from Projectile import Projectile


@dataclass(frozen=True)
class WeaponSpec:
    weapon_id: str
    cooldown: float
    spread_deg: float
    bullet_speed: float
    projectile_radius: int = 3
    offsets: Sequence[float] = field(default_factory=lambda: (0.0,))
    forward_spawn: float = 8.0


class Weapon:
    """Instancia runtime de un arma concreta."""

    def __init__(self, spec: WeaponSpec) -> None:
        self.spec = spec
        self._cooldown = 0.0

    # ------------------------- Temporización -------------------------
    def tick(self, dt: float) -> None:
        self._cooldown = max(0.0, self._cooldown - dt)

    def can_fire(self) -> bool:
        return self._cooldown <= 0.0

    # ------------------------ Generación balas -----------------------
    def fire(self, origin: Tuple[float, float], target: Tuple[float, float]) -> List[Projectile]:
        if not self.can_fire():
            return []

        ox, oy = origin
        tx, ty = target
        dir_x = tx - ox
        dir_y = ty - oy
        mag = math.hypot(dir_x, dir_y)
        if mag <= 0.0001:
            return []
        dir_x /= mag
        dir_y /= mag

        angle = math.atan2(dir_y, dir_x)
        bullets: List[Projectile] = []
        for offset in self.spec.offsets:
            # desplazamiento perpendicular para soportar múltiples cañones
            perp_x, perp_y = -dir_y, dir_x
            spawn_x = ox + dir_x * self.spec.forward_spawn + perp_x * offset
            spawn_y = oy + dir_y * self.spec.forward_spawn + perp_y * offset

            spread_rad = math.radians(random.uniform(-self.spec.spread_deg, self.spec.spread_deg))
            shot_angle = angle + spread_rad
            vx = math.cos(shot_angle)
            vy = math.sin(shot_angle)

            bullets.append(
                Projectile(
                    spawn_x,
                    spawn_y,
                    vx,
                    vy,
                    speed=self.spec.bullet_speed,
                    radius=self.spec.projectile_radius,
                )
            )

        self._cooldown = self.spec.cooldown
        return bullets


class WeaponFactory:
    """Gestiona los distintos tipos de armas disponibles."""

    def __init__(self) -> None:
        self._registry: Dict[str, WeaponSpec] = {
            "short_rifle": WeaponSpec(
                weapon_id="short_rifle",
                cooldown=0.25,
                spread_deg=10.0,
                bullet_speed=340.0,
            ),
            "dual_pistols": WeaponSpec(
                weapon_id="dual_pistols",
                cooldown=0.30,
                spread_deg=15.0,
                bullet_speed=340.0,
                offsets=(-6.0, 6.0),
            ),
            "light_rifle": WeaponSpec(
                weapon_id="light_rifle",
                cooldown=0.11,
                spread_deg=3.0,
                bullet_speed=380.0,
            ),
        }

    def __contains__(self, weapon_id: str) -> bool:
        return weapon_id in self._registry

    def create(self, weapon_id: str) -> Weapon:
        spec = self._registry[weapon_id]
        return Weapon(spec)

    def ids(self) -> Iterable[str]:
        return self._registry.keys()
