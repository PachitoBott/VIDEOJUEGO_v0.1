"""Utilities for loading and animating enemy sprites.

This module centralizes the expected directory structure for enemy
animations.  Each enemy variant is expected to live under
``assets/enemigos/<variant>/`` and provide the following frame sets::

    idle_0.png  .. idle_3.png      (4 frames)
    run_0.png   .. run_3.png       (4 frames)
    shoot_0.png .. shoot_3.png     (4 frames)
    death_0.png .. death_7.png     (8 frames)

Sprites can be safely added later; missing files are replaced by a
placeholder surface tinted according to the enemy variant.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pygame

from asset_paths import assets_dir

# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

_ENEMY_ASSET_DIR = assets_dir("enemigos")
_ENEMY_ASSET_DIR.mkdir(parents=True, exist_ok=True)

_STATE_FRAME_COUNTS: dict[str, int] = {
    "idle": 4,
    "run": 4,
    "shoot": 4,
    "death": 8,
}

_VARIANT_COLORS: dict[str, tuple[int, int, int]] = {
    "yellow_shooter": (255, 214, 120),
    "green_chaser": (126, 232, 170),
    "tank": (200, 116, 116),
    "default": (210, 210, 210),
}


@dataclass(slots=True)
class EnemyAnimationSet:
    """Container with the loaded frames for every animation state."""

    frames: Dict[str, List[pygame.Surface]]
    fallback: pygame.Surface

    def get(self, state: str) -> List[pygame.Surface]:
        return self.frames.get(state) or [self.fallback]


class EnemyAnimator:
    """Stateful helper that advances animation frames over time."""

    def __init__(
        self,
        animations: EnemyAnimationSet,
        *,
        default_state: str = "idle",
        default_fps: float = 8.0,
        fps_overrides: dict[str, float] | None = None,
    ) -> None:
        self.animations = animations
        self.default_state = default_state
        self.base_state = default_state
        self.state = default_state
        self.frame_index = 0
        self.timer = 0.0
        self.default_fps = max(0.1, float(default_fps))
        self.fps_overrides = dict(fps_overrides or {})
        self.oneshot_state: str | None = None
        self.death_finished = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_base_state(self, state: str) -> None:
        self.base_state = state
        if self.state not in ("death", self.oneshot_state):
            self._change_state(state)

    def trigger_shoot(self) -> None:
        if self.state == "death":
            return
        self.oneshot_state = "shoot"
        self._change_state("shoot")

    def trigger_death(self) -> None:
        if self.state == "death":
            return
        self.oneshot_state = None
        self.death_finished = False
        self._change_state("death")

    def update(self, dt: float) -> pygame.Surface:
        frames = self.animations.get(self.state)
        if not frames:
            return self.animations.fallback

        fps = self.fps_overrides.get(self.state, self.default_fps)
        if fps <= 0 or len(frames) == 1:
            return frames[min(self.frame_index, len(frames) - 1)]

        self.timer += dt * fps
        while self.timer >= 1.0:
            self.timer -= 1.0
            self.frame_index += 1
            if self.frame_index >= len(frames):
                if self.state == "death":
                    self.frame_index = len(frames) - 1
                    self.death_finished = True
                    break
                if self.state == self.oneshot_state and self.oneshot_state is not None:
                    self.oneshot_state = None
                    self._change_state(self.base_state)
                    frames = self.animations.get(self.state)
                    fps = self.fps_overrides.get(self.state, self.default_fps)
                    if fps <= 0 or len(frames) == 1:
                        break
                    continue
                self.frame_index %= len(frames)

        return frames[min(self.frame_index, len(frames) - 1)]

    def current_surface(self) -> pygame.Surface:
        frames = self.animations.get(self.state)
        if not frames:
            return self.animations.fallback
        index = min(self.frame_index, len(frames) - 1)
        return frames[index]

    def is_death_finished(self) -> bool:
        return self.state == "death" and self.death_finished

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _change_state(self, state: str) -> None:
        self.state = state
        self.frame_index = 0
        self.timer = 0.0
        if state != "death":
            self.death_finished = False


def load_enemy_animation_set(variant: str) -> EnemyAnimationSet:
    """Load (or synthesize) the animation frames for a given variant."""

    variant_slug = (variant or "default").strip().lower() or "default"
    base_dir = _ENEMY_ASSET_DIR / variant_slug
    color = _VARIANT_COLORS.get(variant_slug, _VARIANT_COLORS["default"])
    frames: dict[str, list[pygame.Surface]] = {}

    for state, expected_count in _STATE_FRAME_COUNTS.items():
        frames[state] = _load_state_frames(base_dir, state, expected_count, color)

    fallback = frames.get("idle")
    if fallback:
        fallback_surface = fallback[0]
    else:
        fallback_surface = _placeholder_surface(color)

    return EnemyAnimationSet(frames=frames, fallback=fallback_surface)


def expected_enemy_filenames(variant: str) -> dict[str, list[str]]:
    """Expose the expected filenames for a variant (useful for docs/UI)."""

    filenames: dict[str, list[str]] = {}
    for state, count in _STATE_FRAME_COUNTS.items():
        filenames[state] = [f"{state}_{i}.png" for i in range(count)]
    return filenames


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_state_frames(
    base_dir: Path,
    state: str,
    expected_count: int,
    color: tuple[int, int, int],
) -> list[pygame.Surface]:
    frames: list[pygame.Surface] = []
    for index in range(expected_count):
        filename = f"{state}_{index}.png"
        path = base_dir / filename
        if path.exists():
            try:
                frame = pygame.image.load(path.as_posix()).convert_alpha()
            except pygame.error:
                frame = _placeholder_surface(color)
        else:
            frame = _placeholder_surface(color)
        frames.append(frame)
    return frames


def _placeholder_surface(color: tuple[int, int, int]) -> pygame.Surface:
    surface = pygame.Surface((32, 32), pygame.SRCALPHA)
    surface.fill((*color, 255))
    pygame.draw.rect(surface, (0, 0, 0, 255), surface.get_rect(), 2, border_radius=6)
    return surface
