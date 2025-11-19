from __future__ import annotations

import math
import random

import pygame

from Config import CFG
from rewards import apply_reward_entry


class MicrochipPickup:
    """Moneda física que puede recoger el jugador."""

    def __init__(
        self,
        x: float,
        y: float,
        value: int,
        sprite: pygame.Surface,
        *,
        angle: float | None = None,
        speed: float | None = None,
    ) -> None:
        self.x = float(x)
        self.y = float(y)
        self.value = max(1, int(value))
        self.sprite = sprite
        self.width = sprite.get_width()
        self.height = sprite.get_height()
        if angle is None:
            angle = random.uniform(0.0, math.tau)
        if speed is None:
            speed = random.uniform(60.0, 110.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.drag = 7.5
        self.bob_phase = random.uniform(0.0, math.tau)
        self.bob_speed = random.uniform(4.0, 6.5)
        self.bob_amplitude = 2.4
        self._collected = False

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    @property
    def collected(self) -> bool:
        return self._collected

    def collect(self) -> None:
        self._collected = True

    def update(self, dt: float, room) -> None:
        if self._collected:
            return
        self._move_axis(dt, room, "x")
        self._move_axis(dt, room, "y")
        damping = max(0.0, 1.0 - self.drag * dt)
        self.vx *= damping
        self.vy *= damping
        if abs(self.vx) < 3.0:
            self.vx = 0.0
        if abs(self.vy) < 3.0:
            self.vy = 0.0
        self.bob_phase = (self.bob_phase + self.bob_speed * dt) % math.tau

    def draw(self, surface: pygame.Surface) -> None:
        if self._collected:
            return
        offset_y = math.sin(self.bob_phase) * self.bob_amplitude
        surface.blit(self.sprite, (int(self.x), int(self.y + offset_y)))

    def _move_axis(self, dt: float, room, axis: str) -> None:
        velocity = self.vx if axis == "x" else self.vy
        if velocity == 0.0:
            return
        step = velocity * dt
        if axis == "x":
            self.x += step
        else:
            self.y += step
        if room is None:
            return
        if self._collides(room):
            if axis == "x":
                self.x -= step
                self.vx = -self.vx * 0.35
            else:
                self.y -= step
                self.vy = -self.vy * 0.35
    def _collides(self, room) -> bool:
        rect = self.rect()
        tile = CFG.TILE_SIZE
        left = rect.left // tile
        top = rect.top // tile
        right = (rect.right - 1) // tile
        bottom = (rect.bottom - 1) // tile
        for ty in range(top, bottom + 1):
            for tx in range(left, right + 1):
                if room.is_blocked(tx, ty):
                    return True
        return False


class LootPickup:
    """Objeto físico que aplica una recompensa al recogerse."""

    def __init__(
        self,
        x: float,
        y: float,
        sprite: pygame.Surface,
        reward: dict,
        *,
        angle: float | None = None,
        speed: float | None = None,
    ) -> None:
        self.x = float(x)
        self.y = float(y)
        self.sprite = sprite
        self.width = sprite.get_width()
        self.height = sprite.get_height()
        self.reward_data = dict(reward) if isinstance(reward, dict) else {}
        if angle is None:
            angle = random.uniform(0.0, math.tau)
        if speed is None:
            speed = random.uniform(60.0, 110.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.drag = 7.5
        self.bob_phase = random.uniform(0.0, math.tau)
        self.bob_speed = random.uniform(3.5, 6.0)
        self.bob_amplitude = 2.0
        self._collected = False
        self._reward_applied = False

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    @property
    def collected(self) -> bool:
        return self._collected

    def collect(self) -> None:
        self._collected = True

    def apply(self, player) -> bool:
        if self._reward_applied:
            return False
        applied = apply_reward_entry(player, dict(self.reward_data))
        if applied:
            self._reward_applied = True
        return applied

    def update(self, dt: float, room) -> None:
        if self._collected:
            return
        self._move_axis(dt, room, "x")
        self._move_axis(dt, room, "y")
        damping = max(0.0, 1.0 - self.drag * dt)
        self.vx *= damping
        self.vy *= damping
        if abs(self.vx) < 3.0:
            self.vx = 0.0
        if abs(self.vy) < 3.0:
            self.vy = 0.0
        self.bob_phase = (self.bob_phase + self.bob_speed * dt) % math.tau

    def draw(self, surface: pygame.Surface) -> None:
        if self._collected:
            return
        offset_y = math.sin(self.bob_phase) * self.bob_amplitude
        surface.blit(self.sprite, (int(self.x), int(self.y + offset_y)))

    def _move_axis(self, dt: float, room, axis: str) -> None:
        velocity = self.vx if axis == "x" else self.vy
        if velocity == 0.0:
            return
        step = velocity * dt
        if axis == "x":
            self.x += step
        else:
            self.y += step
        if room is None:
            return
        if self._collides(room):
            if axis == "x":
                self.x -= step
                self.vx = -self.vx * 0.35
            else:
                self.y -= step
                self.vy = -self.vy * 0.35

def _collides(self, room) -> bool:
        rect = self.rect()
        tile = CFG.TILE_SIZE
        left = rect.left // tile
        top = rect.top // tile
        right = (rect.right - 1) // tile
        bottom = (rect.bottom - 1) // tile
        for ty in range(top, bottom + 1):
            for tx in range(left, right + 1):
                if room.is_blocked(tx, ty):
                    return True
        return False


class LootPickup:
    """Objeto físico que aplica una recompensa al recogerse."""

    def __init__(
        self,
        x: float,
        y: float,
        sprite: pygame.Surface,
        reward: dict,
        *,
        angle: float | None = None,
        speed: float | None = None,
    ) -> None:
        self.x = float(x)
        self.y = float(y)
        self.sprite = sprite
        self.width = sprite.get_width()
        self.height = sprite.get_height()
        self.reward_data = dict(reward) if isinstance(reward, dict) else {}
        if angle is None:
            angle = random.uniform(0.0, math.tau)
        if speed is None:
            speed = random.uniform(60.0, 110.0)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.drag = 7.5
        self.bob_phase = random.uniform(0.0, math.tau)
        self.bob_speed = random.uniform(3.5, 6.0)
        self.bob_amplitude = 2.0
        self._collected = False
        self._reward_applied = False

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    @property
    def collected(self) -> bool:
        return self._collected

    def collect(self) -> None:
        self._collected = True

    def apply(self, player) -> bool:
        if self._reward_applied:
            return False
        applied = apply_reward_entry(player, dict(self.reward_data))
        if applied:
            self._reward_applied = True
        return applied

    def update(self, dt: float, room) -> None:
        if self._collected:
            return
        self._move_axis(dt, room, "x")
        self._move_axis(dt, room, "y")
        damping = max(0.0, 1.0 - self.drag * dt)
        self.vx *= damping
        self.vy *= damping
        if abs(self.vx) < 3.0:
            self.vx = 0.0
        if abs(self.vy) < 3.0:
            self.vy = 0.0
        self.bob_phase = (self.bob_phase + self.bob_speed * dt) % math.tau

    def draw(self, surface: pygame.Surface) -> None:
        if self._collected:
            return
        offset_y = math.sin(self.bob_phase) * self.bob_amplitude
        surface.blit(self.sprite, (int(self.x), int(self.y + offset_y)))

    def _move_axis(self, dt: float, room, axis: str) -> None:
        velocity = self.vx if axis == "x" else self.vy
        if velocity == 0.0:
            return
        step = velocity * dt
        if axis == "x":
            self.x += step
        else:
            self.y += step
        if room is None:
            return
        if self._collides(room):
            if axis == "x":
                self.x -= step
                self.vx = -self.vx * 0.35
            else:
                self.y -= step
                self.vy = -self.vy * 0.35

    def _collides(self, room) -> bool:
        rect = self.rect()
        tile = CFG.TILE_SIZE
        left = rect.left // tile
        top = rect.top // tile
        right = (rect.right - 1) // tile
        bottom = (rect.bottom - 1) // tile
        for ty in range(top, bottom + 1):
            for tx in range(left, right + 1):
                if room.is_blocked(tx, ty):
                    return True
        return False
