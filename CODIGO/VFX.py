import math
import random

import math
import random

import pygame


class _ScreenFlash:
    def __init__(self, color: tuple[int, int, int], duration: float, max_alpha: int = 140) -> None:
        self._color = color
        self._duration = max(0.01, duration)
        self._timer = 0.0
        self._max_alpha = max(0, min(255, int(max_alpha)))

    def trigger(self, duration: float | None = None) -> None:
        flash_duration = max(0.01, duration if duration is not None else self._duration)
        self._timer = max(self._timer, flash_duration)

    def update(self, dt: float) -> None:
        self._timer = max(0.0, self._timer - dt)

    def reset(self) -> None:
        self._timer = 0.0

    def draw(self, surface: pygame.Surface) -> None:
        if self._timer <= 0.0:
            return
        ratio = min(1.0, self._timer / self._duration)
        alpha = int(self._max_alpha * ratio)
        if alpha <= 0:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*self._color, alpha))
        surface.blit(overlay, (0, 0))


class _WorldEffect:
    def update(self, dt: float) -> None:  # pragma: no cover - base
        raise NotImplementedError

    def draw(self, surface: pygame.Surface) -> None:  # pragma: no cover - base
        raise NotImplementedError

    def is_alive(self) -> bool:  # pragma: no cover - base
        raise NotImplementedError


class _MuzzleFlash(_WorldEffect):
    def __init__(self, position: tuple[float, float], direction: tuple[float, float], duration: float = 0.08) -> None:
        self._pos = pygame.Vector2(position)
        dir_vec = pygame.Vector2(direction)
        if dir_vec.length_squared() <= 0.0001:
            dir_vec = pygame.Vector2(1, 0)
        else:
            dir_vec = dir_vec.normalize()
        self._dir = dir_vec
        self._duration = max(0.02, duration)
        self._timer = self._duration

    def update(self, dt: float) -> None:
        self._timer = max(0.0, self._timer - dt)

    def draw(self, surface: pygame.Surface) -> None:
        if self._timer <= 0.0:
            return
        ratio = self._timer / self._duration
        length = 12 + 10 * ratio
        start = self._pos - self._dir * 2
        end = self._pos + self._dir * length
        start_pos = (int(start.x), int(start.y))
        end_pos = (int(end.x), int(end.y))
        outer_width = max(2, int(4 * ratio) + 1)
        inner_width = max(1, outer_width - 1)
        pygame.draw.line(surface, (255, 200, 90), start_pos, end_pos, outer_width)
        pygame.draw.line(surface, (255, 255, 255), start_pos, end_pos, inner_width)

    def is_alive(self) -> bool:
        return self._timer > 0.0


class _EnemyDeathFlash(_WorldEffect):
    def __init__(self, position: tuple[float, float]) -> None:
        self._center = pygame.Vector2(position)
        self._flash_timer = 0.08
        self._particles: list[dict[str, object]] = []
        for _ in range(random.randint(3, 4)):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(70.0, 150.0)
            velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
            life = random.uniform(0.18, 0.28)
            size = random.randint(2, 4)
            self._particles.append(
                {
                    "pos": self._center.copy(),
                    "vel": velocity,
                    "life": life,
                    "timer": life,
                    "size": size,
                }
            )

    def update(self, dt: float) -> None:
        self._flash_timer = max(0.0, self._flash_timer - dt)
        remaining: list[dict[str, object]] = []
        for particle in self._particles:
            timer = float(particle["timer"]) - dt
            if timer <= 0.0:
                continue
            particle["timer"] = timer
            pos: pygame.Vector2 = particle["pos"]  # type: ignore[assignment]
            vel: pygame.Vector2 = particle["vel"]  # type: ignore[assignment]
            pos.x += vel.x * dt
            pos.y += vel.y * dt
            remaining.append(particle)
        self._particles = remaining

    def draw(self, surface: pygame.Surface) -> None:
        if self._flash_timer > 0.0:
            ratio = self._flash_timer / 0.08
            size = int(8 + 10 * ratio)
            rect = pygame.Rect(0, 0, size, size)
            rect.center = (int(self._center.x), int(self._center.y))
            pygame.draw.rect(surface, (255, 255, 255), rect)
        for particle in self._particles:
            timer = float(particle["timer"])
            life = float(particle["life"])
            ratio = timer / life if life > 0 else 0
            size = max(1, int(int(particle["size"]) * ratio) + 1)
            rect = pygame.Rect(0, 0, size, size)
            pos: pygame.Vector2 = particle["pos"]  # type: ignore[assignment]
            rect.center = (int(pos.x), int(pos.y))
            color_value = 200 + int(55 * ratio)
            pygame.draw.rect(surface, (255, color_value, 220), rect)

    def is_alive(self) -> bool:
        return self._flash_timer > 0.0 or bool(self._particles)


class _CorruptionBurst(_WorldEffect):
    def __init__(self, position: tuple[float, float]) -> None:
        self._center = pygame.Vector2(position)
        self._particles: list[dict[str, object]] = []
        for _ in range(random.randint(10, 15)):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(70.0, 150.0)
            velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
            life = random.uniform(0.2, 0.35)
            size = random.randint(3, 5)
            self._particles.append(
                {
                    "pos": self._center.copy(),
                    "vel": velocity,
                    "life": life,
                    "timer": life,
                    "size": size,
                }
            )

    def update(self, dt: float) -> None:
        remaining: list[dict[str, object]] = []
        for particle in self._particles:
            timer = float(particle["timer"]) - dt
            if timer <= 0.0:
                continue
            particle["timer"] = timer
            pos: pygame.Vector2 = particle["pos"]  # type: ignore[assignment]
            vel: pygame.Vector2 = particle["vel"]  # type: ignore[assignment]
            pos.x += vel.x * dt
            pos.y += vel.y * dt
            remaining.append(particle)
        self._particles = remaining

    def draw(self, surface: pygame.Surface) -> None:
        for particle in self._particles:
            timer = float(particle["timer"])
            life = float(particle["life"])
            ratio = timer / life if life > 0 else 0
            size = max(2, int(int(particle["size"]) * (0.6 + 0.4 * ratio)))
            rect = pygame.Rect(0, 0, size, size)
            pos: pygame.Vector2 = particle["pos"]  # type: ignore[assignment]
            rect.center = (int(pos.x), int(pos.y))
            alpha = int(160 * ratio)
            color = (170, 80, 255, max(80, alpha))
            pygame.draw.rect(surface, color, rect)

    def is_alive(self) -> bool:
        return bool(self._particles)


class VFXManager:
    def __init__(self) -> None:
        self._damage_flash = _ScreenFlash((255, 40, 40), duration=0.18, max_alpha=120)
        self._world_effects: list[_WorldEffect] = []

    def reset(self) -> None:
        self._damage_flash.reset()
        self._world_effects.clear()

    def update(self, dt: float) -> None:
        self._damage_flash.update(dt)
        for effect in self._world_effects:
            effect.update(dt)
        self._world_effects = [effect for effect in self._world_effects if effect.is_alive()]

    def draw_world(self, surface: pygame.Surface) -> None:
        for effect in self._world_effects:
            effect.draw(surface)

    def draw_screen(self, surface: pygame.Surface) -> None:
        self._damage_flash.draw(surface)

    def trigger_damage_flash(self) -> None:
        self._damage_flash.trigger()

    def spawn_enemy_flash(self, position: tuple[int, int] | tuple[float, float] | None) -> None:
        if position is None:
            return
        self._world_effects.append(_EnemyDeathFlash(position))

    def spawn_muzzle_flash(self, position: tuple[float, float], direction: tuple[float, float]) -> None:
        self._world_effects.append(_MuzzleFlash(position, direction))

    def spawn_corruption_burst(self, position: tuple[float, float] | tuple[int, int]) -> None:
        self._world_effects.append(_CorruptionBurst(position))
