"""Utilities for loading and animating enemy sprites.

This module centralizes the expected directory structure for enemy
animations.  Each enemy variant is expected to live under
``assets/enemigos/<variant>/`` and provide the following frame sets::

    idle_0.png  .. idle_3.png      (4 frames)
    run_0.png   .. run_3.png       (4 frames)
    shoot_0.png .. shoot_3.png     (4 frames)
    attack_0.png .. attack_3.png   (4 frames, opcional)
    death_0.png .. death_N.png     (los detecta automáticamente)

Sprites can be safely added later; missing files are replaced by a
placeholder surface tinted according to the enemy variant.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

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
    "attack": 4,
    "death": 8,
}

_VARIANT_COLORS: dict[str, tuple[int, int, int]] = {
    "yellow_shooter": (255, 214, 120),
    "green_chaser": (126, 232, 170),
    "blue_shooter": (120, 188, 255),
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
        if self.state == "death" or self.state == self.oneshot_state:
            return
        if self.state != state:
            self._change_state(state)

    def trigger_shoot(self) -> None:
        self._trigger_oneshot("shoot")

    def trigger_attack(self) -> None:
        self._trigger_oneshot("attack")

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

    def _trigger_oneshot(self, state: str) -> None:
        if self.state == "death":
            return
        if self.state == state and self.oneshot_state == state:
            return
        self.oneshot_state = state
        self._change_state(state)


def resolve_enemy_variant(preferred: Iterable[str]) -> str:
    """Pick the best available sprite variant from a list of preferences."""

    preferred = list(preferred) or ["default"]
    for variant in preferred:
        slug = (variant or "default").strip().lower() or "default"
        base_dir = _ENEMY_ASSET_DIR / slug
        if any(base_dir.glob("*.png")):
            return slug
    slug = (preferred[0] or "default").strip().lower() or "default"
    return slug


def load_enemy_animation_set(variant: str) -> EnemyAnimationSet:
    """Load (or synthesize) the animation frames for a given variant."""

    variant_slug = (variant or "default").strip().lower() or "default"
    base_dir = _ENEMY_ASSET_DIR / variant_slug
    color = _VARIANT_COLORS.get(variant_slug, _VARIANT_COLORS["default"])
    frames: dict[str, list[pygame.Surface]] = {}

    for state, expected_count in _STATE_FRAME_COUNTS.items():
        frames[state] = _load_state_frames(base_dir, state, expected_count, color)

    # Detect extra states that may exist on disk (e.g., alternative actions).
    for path in sorted(base_dir.glob("*_*.png")):
        state, _, suffix = path.stem.partition("_")
        if not suffix.isdigit() or state in frames:
            continue
        frames[state] = _load_state_frames(base_dir, state, 1, color)

    fallback = frames.get("idle")
    if fallback:
        fallback_surface = fallback[0]
    else:
        fallback_surface = _placeholder_surface(color)

    return EnemyAnimationSet(frames=frames, fallback=fallback_surface)


def expected_enemy_filenames(variant: str) -> dict[str, list[str]]:
    """Expose the filenames present (or expected) for a variant."""

    variant_slug = (variant or "default").strip().lower() or "default"
    base_dir = _ENEMY_ASSET_DIR / variant_slug

    filenames: dict[str, list[str]] = {}
    discovered_states: set[str] = set()

    for state, count in _STATE_FRAME_COUNTS.items():
        indices = _existing_state_indices(base_dir, state)
        if indices:
            filenames[state] = [f"{state}_{i}.png" for i in indices]
        else:
            filenames[state] = [f"{state}_{i}.png" for i in range(count)]
        discovered_states.add(state)

    for extra_state in sorted(_discover_extra_states(base_dir) - discovered_states):
        indices = _existing_state_indices(base_dir, extra_state)
        filenames[extra_state] = [f"{extra_state}_{i}.png" for i in indices]

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
    indices = _existing_state_indices(base_dir, state)
    for index in indices:
        filename = f"{state}_{index}.png"
        path = base_dir / filename
        try:
            frame = pygame.image.load(path.as_posix()).convert_alpha()
        except pygame.error:
            frame = _placeholder_surface(color)
        frames.append(frame)

    if frames:
        return frames

    count = max(1, expected_count)
    return [_placeholder_surface(color) for _ in range(count)]


def _existing_state_indices(base_dir: Path, state: str) -> list[int]:
    indices: list[int] = []
    for path in sorted(base_dir.glob(f"{state}_*.png")):
        suffix = path.stem[len(state) + 1 :]
        if suffix.isdigit():
            indices.append(int(suffix))
    return sorted(indices)


def _discover_extra_states(base_dir: Path) -> set[str]:
    states: set[str] = set()
    for path in base_dir.glob("*_*.png"):
        state, _, suffix = path.stem.partition("_")
        if suffix.isdigit():
            states.add(state)
    return states


def _placeholder_surface(color: tuple[int, int, int]) -> pygame.Surface:
    surface = pygame.Surface((32, 32), pygame.SRCALPHA)
    surface.fill((*color, 255))
    pygame.draw.rect(surface, (0, 0, 0, 255), surface.get_rect(), 2, border_radius=6)
    return surface
