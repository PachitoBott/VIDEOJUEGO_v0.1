"""Definiciones y factoría de armas del jugador."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence

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
    magazine_size: int = 10
    reload_time: float = 1.0


class Weapon:
    """Instancia runtime de un arma concreta."""

    def __init__(self, spec: WeaponSpec, cooldown_scale: float = 1.0) -> None:
        self.spec = spec
        self._cooldown = 0.0
        self._cooldown_scale = max(0.05, cooldown_scale)
        self._shots_in_mag = max(1, spec.magazine_size)
        self._reload_timer = 0.0

    # ------------------------- Temporización -------------------------
    def tick(self, dt: float) -> None:
        self._cooldown = max(0.0, self._cooldown - dt)
        if self._reload_timer > 0.0:
            self._reload_timer = max(0.0, self._reload_timer - dt)
            if self._reload_timer <= 0.0:
                self._shots_in_mag = max(1, self.spec.magazine_size)

    def can_fire(self) -> bool:
        if self._cooldown > 0.0:
            return False
        if self._reload_timer > 0.0:
            return False
        return self._shots_in_mag > 0

    # ----------------------------- Estado -----------------------------
    def is_reloading(self) -> bool:
        return self._reload_timer > 0.0

    @property
    def reload_time(self) -> float:
        return self.spec.reload_time

    def reload_progress(self) -> float:
        if self.spec.reload_time <= 0.0:
            return 1.0
        remaining = max(0.0, min(self.spec.reload_time, self._reload_timer))
        return 1.0 - remaining / self.spec.reload_time

    def start_reload(self) -> bool:
        """Inicia una recarga manual si es posible."""
        if self.spec.reload_time <= 0.0:
            return False
        if self._reload_timer > 0.0:
            return False
        if self._shots_in_mag >= self.spec.magazine_size:
            return False
        self._reload_timer = self.spec.reload_time
        self._shots_in_mag = 0
        return True

    # ------------------------ Generación balas -----------------------
    def fire(self, origin: tuple[float, float], target: tuple[float, float]) -> List[Projectile]:
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

        self._cooldown = self.spec.cooldown * self._cooldown_scale
        self._shots_in_mag -= 1
        if self._shots_in_mag <= 0:
            self._shots_in_mag = 0
            self._reload_timer = self.spec.reload_time
        return bullets

    # ----------------------- Ajustes dinámicos -----------------------
    def set_cooldown_scale(self, cooldown_scale: float) -> None:
        """Permite modificar el multiplicador de recarga en runtime."""
        self._cooldown_scale = max(0.05, cooldown_scale)


class WeaponFactory:
    """Gestiona los distintos tipos de armas disponibles."""

    def __init__(self) -> None:
        self._registry: Dict[str, WeaponSpec] = {
            "short_rifle": WeaponSpec(
                weapon_id="short_rifle",
                cooldown=0.25,
                spread_deg=10.0,
                bullet_speed=340.0,
                magazine_size=10,
                reload_time=1.1,
            ),
            "dual_pistols": WeaponSpec(
                weapon_id="dual_pistols",
                cooldown=0.36,
                spread_deg=18.0,
                bullet_speed=320.0,
                offsets=(-6.0, 6.0),
                magazine_size=12,
                reload_time=1.25,
            ),
            "light_rifle": WeaponSpec(
                weapon_id="light_rifle",
                cooldown=0.16,
                spread_deg=4.0,
                bullet_speed=360.0,
                magazine_size=14,
                reload_time=1.4,
            ),
            "arcane_salvo": WeaponSpec(
                weapon_id="arcane_salvo",
                cooldown=0.68,
                spread_deg=36.0,
                bullet_speed=280.0,
                offsets=(-12.0, -6.0, 0.0, 6.0, 12.0),
                projectile_radius=4,
                magazine_size=8,
                reload_time=1.85,
            ),
            "pulse_rifle": WeaponSpec(
                weapon_id="pulse_rifle",
                cooldown=0.12,
                spread_deg=2.5,
                bullet_speed=390.0,
                magazine_size=16,
                reload_time=1.6,
            ),
            "tesla_gloves": WeaponSpec(
                weapon_id="tesla_gloves",
                cooldown=0.24,
                spread_deg=28.0,
                bullet_speed=240.0,
                projectile_radius=5,
                offsets=(-4.0, 4.0),
                forward_spawn=4.0,
                magazine_size=9,
                reload_time=2.0,
            ),
            "ember_carbine": WeaponSpec(
                weapon_id="ember_carbine",
                cooldown=0.22,
                spread_deg=8.0,
                bullet_speed=325.0,
                offsets=(0.0,),
                forward_spawn=9.0,
                magazine_size=18,
                reload_time=2.1,
            ),
        }

    def __contains__(self, weapon_id: str) -> bool:
        return weapon_id in self._registry

    def create(self, weapon_id: str, *, cooldown_scale: float = 1.0) -> Weapon:
        spec = self._registry[weapon_id]
        return Weapon(spec, cooldown_scale=cooldown_scale)

    def ids(self) -> Iterable[str]:
        return self._registry.keys()
