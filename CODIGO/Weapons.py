"""Definiciones y factoría de armas del jugador."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import pygame

from Projectile import Projectile


@dataclass(frozen=True)
class WeaponSpec:
    weapon_id: str
    cooldown: float
    spread_deg: float
    bullet_speed: float
    projectile_radius: int = 4
    offsets: Sequence[float] = field(default_factory=lambda: (0.0,))
    forward_spawn: float = 8.0
    magazine_size: int = 10
    reload_time: float = 1.0
    projectile_color: tuple[int, int, int] | None = None
    on_hit_effects: Sequence[dict[str, Any]] = field(default_factory=tuple)
    special: dict[str, Any] = field(default_factory=dict)


class Weapon:
    """Instancia runtime de un arma concreta."""

    def __init__(self, spec: WeaponSpec, cooldown_scale: float = 1.0) -> None:
        self.spec = spec
        self._cooldown = 0.0
        self._cooldown_scale = max(0.05, cooldown_scale)
        self._shots_in_mag = max(1, spec.magazine_size)
        self._reload_timer = 0.0
        self._shots_since_reload = 0
        self._time_since_last_shot = 999.0
        self._continuous_fire_time = 0.0
        
        # Cargar sonidos para el arma
        self._gun_sound = None
        self._reload_sound = None
        self._load_gun_sound()
        self._load_reload_sound()

    # ------------------------- Temporización -------------------------
    def tick(self, dt: float) -> None:
        self._cooldown = max(0.0, self._cooldown - dt)
        self._time_since_last_shot = min(10.0, self._time_since_last_shot + dt)
        if self._reload_timer > 0.0:
            self._reload_timer = max(0.0, self._reload_timer - dt)
            if self._reload_timer <= 0.0:
                self._shots_in_mag = max(1, self.spec.magazine_size)
                self._shots_since_reload = 0
        self._update_heat(dt)

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

    @property
    def shots_in_mag(self) -> int:
        """Número de balas restantes en el cargador actual."""

        return max(0, int(self._shots_in_mag))

    @property
    def magazine_size(self) -> int:
        """Capacidad máxima del cargador del arma."""

        return max(1, int(self.spec.magazine_size))

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
        self._shots_since_reload = 0
        
        # Reproducir sonido de recarga
        if self._reload_sound:
            self._reload_sound.play()
        
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
        effective_spread = self._effective_spread_deg()
        for offset in self.spec.offsets:
            # desplazamiento perpendicular para soportar múltiples cañones
            perp_x, perp_y = -dir_y, dir_x
            spawn_x = ox + dir_x * self.spec.forward_spawn + perp_x * offset
            spawn_y = oy + dir_y * self.spec.forward_spawn + perp_y * offset

            spread_rad = math.radians(random.uniform(-effective_spread, effective_spread))
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
                    color=self.spec.projectile_color,
                    effects=[dict(effect) for effect in self.spec.on_hit_effects],
                )
            )

        self._apply_special_on_fire()
        heat_multiplier = self._heat_penalty_multiplier()
        self._cooldown = self.spec.cooldown * self._cooldown_scale * heat_multiplier
        self._shots_in_mag -= 1
        if self._shots_in_mag <= 0:
            self._shots_in_mag = 0
            self._reload_timer = self.spec.reload_time
            # Reproducir sonido de recarga automática
            if self._reload_sound:
                self._reload_sound.play()
        self._shots_since_reload += 1
        self._time_since_last_shot = 0.0
        
        # Reproducir sonido de disparo
        if self._gun_sound:
            self._gun_sound.play()
        
        return bullets

    # ----------------------- Ajustes dinámicos -----------------------
    def set_cooldown_scale(self, cooldown_scale: float) -> None:
        """Permite modificar el multiplicador de recarga en runtime."""
        self._cooldown_scale = max(0.05, cooldown_scale)

    # -------------------------- Especiales --------------------------
    def _load_gun_sound(self) -> None:
        """Carga el sonido de disparo del arma basado en su weapon_id."""
        try:
            # Mapeo de armas a archivos de sonido específicos
            sound_file_mapping = {
                "arcane_salvo": "shotgun_sfx.mp3",
            }
            
            # Volúmenes personalizados por arma (default: 0.20)
            volume_settings = {
                "light_rifle": 0.10,
                "short_rifle": 0.40,
            }
            
            # Determinar archivo de sonido a usar
            sound_filename = sound_file_mapping.get(
                self.spec.weapon_id,
                f"{self.spec.weapon_id}_sfx.mp3"
            )
            
            audio_path = Path("assets/audio") / sound_filename
            
            if not audio_path.exists():
                # Intentar ruta relativa desde CODIGO
                audio_path = Path(__file__).parent / "assets" / "audio" / sound_filename
            
            if audio_path.exists():
                self._gun_sound = pygame.mixer.Sound(audio_path.as_posix())
                # Aplicar volumen personalizado o default (20%)
                volume = volume_settings.get(self.spec.weapon_id, 0.2)
                self._gun_sound.set_volume(volume)
            else:
                # Fallback a sonido por defecto si no existe sonido específico
                fallback_path = Path(__file__).parent / "assets" / "audio" / "default_gun_sfx.mp3"
                if fallback_path.exists():
                    self._gun_sound = pygame.mixer.Sound(fallback_path.as_posix())
                    volume = volume_settings.get(self.spec.weapon_id, 0.2)
                    self._gun_sound.set_volume(volume)
                else:
                    self._gun_sound = None
        except (pygame.error, FileNotFoundError):
            self._gun_sound = None
    
    def _load_reload_sound(self) -> None:
        """Carga el sonido de recarga universal para todas las armas."""
        try:
            audio_path = Path("assets/audio/reload_sfx.mp3")
            
            if not audio_path.exists():
                # Intentar ruta relativa desde CODIGO
                audio_path = Path(__file__).parent / "assets" / "audio" / "reload_sfx.mp3"
            
            if audio_path.exists():
                self._reload_sound = pygame.mixer.Sound(audio_path.as_posix())
                self._reload_sound.set_volume(0.15)  # 15% del volumen
            else:
                self._reload_sound = None
        except (pygame.error, FileNotFoundError):
            self._reload_sound = None
    
    def _effective_spread_deg(self) -> float:
        base = self.spec.spread_deg
        recoil_cfg = self.spec.special.get("recoil_ramp")
        if recoil_cfg:
            threshold = int(recoil_cfg.get("shots", 6))
            extra = float(recoil_cfg.get("extra", 0.0))
            if self._shots_since_reload + 1 >= threshold:
                base += extra
        return base

    def _update_heat(self, dt: float) -> None:
        heat_cfg = self.spec.special.get("heat")
        if not heat_cfg:
            return
        grace = float(heat_cfg.get("grace", 0.28))
        if self._time_since_last_shot > grace:
            decay = float(heat_cfg.get("decay", 3.5))
            self._continuous_fire_time = max(0.0, self._continuous_fire_time - decay * dt)

    def _apply_special_on_fire(self) -> None:
        heat_cfg = self.spec.special.get("heat")
        if heat_cfg:
            threshold = max(0.05, float(heat_cfg.get("threshold", 2.0)))
            if self._time_since_last_shot <= float(heat_cfg.get("grace", 0.28)):
                self._continuous_fire_time = min(
                    threshold + 2.0,
                    self._continuous_fire_time + self._time_since_last_shot,
                )
            else:
                self._continuous_fire_time = max(
                    0.0, self._continuous_fire_time - float(heat_cfg.get("decay", 3.5))
                )

    def _heat_penalty_multiplier(self) -> float:
        heat_cfg = self.spec.special.get("heat")
        if not heat_cfg:
            return 1.0
        threshold = max(0.05, float(heat_cfg.get("threshold", 2.0)))
        penalty = max(0.0, float(heat_cfg.get("penalty", 0.1)))
        if self._continuous_fire_time >= threshold:
            return 1.0 + penalty
        return 1.0


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
                cooldown=0.18,
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
                projectile_radius=5,
                magazine_size=8,
                reload_time=1.85,
            ),
            "pulse_rifle": WeaponSpec(
                weapon_id="pulse_rifle",
                cooldown=0.13,
                spread_deg=2.5,
                bullet_speed=390.0,
                magazine_size=16,
                reload_time=1.6,
                special={
                    "heat": {
                        "threshold": 2.0,
                        "penalty": 0.12,
                        "grace": 0.25,
                        "decay": 3.5,
                    }
                },
            ),
            "tesla_gloves": WeaponSpec(
                weapon_id="tesla_gloves",
                cooldown=0.24,
                spread_deg=28.0,
                bullet_speed=240.0,
                projectile_radius=6,
                offsets=(-4.0, 4.0),
                forward_spawn=4.0,
                magazine_size=9,
                reload_time=2.0,
                projectile_color=(140, 220, 255),
                on_hit_effects=(
                    {
                        "type": "shock",
                        "slow": 0.2,
                        "duration": 0.8,
                    },
                ),
            ),
            "ember_carbine": WeaponSpec(
                weapon_id="ember_carbine",
                cooldown=0.24,
                spread_deg=8.0,
                bullet_speed=325.0,
                offsets=(0.0,),
                forward_spawn=9.0,
                magazine_size=16,
                reload_time=2.1,
                special={
                    "recoil_ramp": {
                        "shots": 6,
                        "extra": 3.0,
                    }
                },
            ),
        }

    def __contains__(self, weapon_id: str) -> bool:
        return weapon_id in self._registry

    def create(self, weapon_id: str, *, cooldown_scale: float = 1.0) -> Weapon:
        spec = self._registry[weapon_id]
        return Weapon(spec, cooldown_scale=cooldown_scale)

    def ids(self) -> Iterable[str]:
        return self._registry.keys()
