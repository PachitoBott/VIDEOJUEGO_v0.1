"""Utilities for loading and animating enemy sprites.

This module centralizes the expected directory structure for enemy
animations.  Each enemy variant is expected to live under
``assets/enemigos/<variant>/`` and provide the following frame sets::

    idle_0.png  .. idle_3.png      (4 frames)
    run_0.png   .. run_3.png       (4 frames)
    shoot_0.png .. shoot_3.png     (4 frames)
    attack_0.png .. attack_3.png   (4 frames, opcional)
    death_0.png .. death_N.png     (los detecta automáticamente)

For bosses the assets are grouped under ``assets/enemigos/boss/<variant>/``
and use prefixed filenames to separate layers::

    legs_idle_0.png  .. legs_idle_3.png
    legs_run_0.png   .. legs_run_7.png
    torso_idle_0.png .. torso_idle_3.png
    torso_shoot1_0.png .. torso_shoot1_4.png
    torso_shoot2_0.png .. torso_shoot2_7.png
    torso_shoot3_0.png .. torso_shoot3_3.png
    death_0.png .. death_8.png

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
_BOSS_ASSET_DIR = _ENEMY_ASSET_DIR / "boss"
_BOSS_ASSET_DIR.mkdir(parents=True, exist_ok=True)

_STATE_FRAME_COUNTS: dict[str, int] = {
    "idle": 4,
    "run": 4,
    "shoot": 4,
    "attack": 4,
    "death": 8,
}

_BOSS_LEG_COUNTS: dict[str, int] = {
    "idle": 4,
    "run": 8,
}

_BOSS_TORSO_COUNTS: dict[str, int] = {
    "idle": 4,
    "shoot1": 5,
    "shoot2": 8,
    "shoot3": 4,
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


@dataclass(slots=True)
class BossAnimationLayers:
    """Layered frames for bosses (legs, torso, and full-body death)."""

    legs: Dict[str, List[pygame.Surface]]
    torso: Dict[str, List[pygame.Surface]]
    death: List[pygame.Surface]
    fallback: pygame.Surface

    def leg_frames(self, state: str) -> List[pygame.Surface]:
        return self.legs.get(state) or [self.fallback]

    def torso_frames(self, state: str) -> List[pygame.Surface]:
        return self.torso.get(state) or [self.fallback]

    def death_frames(self) -> List[pygame.Surface]:
        return self.death or [self.fallback]


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


class LayeredBossAnimator:
    """Animator that combines independent leg/torso layers plus a death strip."""

    def __init__(
        self,
        animations: BossAnimationLayers,
        *,
        leg_fps: dict[str, float] | None = None,
        torso_fps: dict[str, float] | None = None,
        default_fps: float = 8.0,
        death_fps: float = 12.0,
    ) -> None:
        self.animations = animations
        self.default_fps = max(0.1, float(default_fps))
        self.death_fps = max(0.1, float(death_fps))
        self.leg_fps = dict(leg_fps or {})
        self.torso_fps = dict(torso_fps or {})

        self.leg_state = "idle"
        self.torso_state = "idle"
        self.torso_oneshot: str | None = None
        self.death_active = False
        self.death_finished = False

        self._leg_index = 0
        self._torso_index = 0
        self._death_index = 0

        self._leg_timer = 0.0
        self._torso_timer = 0.0
        self._death_timer = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_base_state(self, state: str) -> None:
        """Compatibility shim for Enemy.update death handling."""

        if state == "death":
            self.trigger_death()
            return
        if state in _BOSS_LEG_COUNTS:
            self.set_leg_state(state)

    def set_leg_state(self, state: str) -> None:
        if self.death_active:
            return
        if state != self.leg_state:
            self.leg_state = state
            self._leg_index = 0
            self._leg_timer = 0.0

    def set_torso_base_state(self, state: str) -> None:
        if self.death_active:
            return
        if self.torso_oneshot:
            return
        if state != self.torso_state:
            self.torso_state = state
            self._torso_index = 0
            self._torso_timer = 0.0

    def trigger_shoot(self, variant: str = "shoot1") -> None:
        if self.death_active:
            return
        variant = (variant or "shoot1").lower()
        if variant not in self.animations.torso:
            variant = "shoot1"
        self.torso_oneshot = variant
        self._torso_index = 0
        self._torso_timer = 0.0

    def trigger_death(self) -> None:
        if self.death_active:
            return
        self.death_active = True
        self.death_finished = False
        self._death_index = 0
        self._death_timer = 0.0

    def update(self, dt: float) -> None:
        if self.death_active:
            self._advance_death(dt)
            return
        self._advance_leg(dt)
        self._advance_torso(dt)

    def current_surfaces(self) -> tuple[pygame.Surface, pygame.Surface | None]:
        if self.death_active:
            frames = self.animations.death_frames()
            index = min(self._death_index, len(frames) - 1)
            return frames[index], None

        leg_frames = self.animations.leg_frames(self.leg_state)
        torso_state = self.torso_oneshot or self.torso_state
        torso_frames = self.animations.torso_frames(torso_state)

        leg_frame = leg_frames[min(self._leg_index, len(leg_frames) - 1)]
        torso_frame = torso_frames[min(self._torso_index, len(torso_frames) - 1)]
        return leg_frame, torso_frame

    def is_death_finished(self) -> bool:
        return self.death_active and self.death_finished

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _advance_leg(self, dt: float) -> None:
        frames = self.animations.leg_frames(self.leg_state)
        fps = self.leg_fps.get(self.leg_state, self.default_fps)
        self._advance_timer(dt, fps, frames, "leg")

    def _advance_torso(self, dt: float) -> None:
        state = self.torso_oneshot or self.torso_state
        frames = self.animations.torso_frames(state)
        fps = self.torso_fps.get(state, self.default_fps)
        if self.torso_oneshot and len(frames) <= 1:
            self.torso_oneshot = None
            self._torso_index = 0
            self._torso_timer = 0.0
            return
        finished = self._advance_timer(dt, fps, frames, "torso")
        if finished and self.torso_oneshot:
            self.torso_oneshot = None
            self._torso_index = 0
            self._torso_timer = 0.0

    def _advance_death(self, dt: float) -> None:
        frames = self.animations.death_frames()
        if len(frames) <= 1:
            self.death_finished = True
            return
        self._death_timer += dt * self.death_fps
        while self._death_timer >= 1.0 and not self.death_finished:
            self._death_timer -= 1.0
            self._death_index += 1
            if self._death_index >= len(frames) - 1:
                self._death_index = len(frames) - 1
                self.death_finished = True

    def _advance_timer(
        self,
        dt: float,
        fps: float,
        frames: list[pygame.Surface],
        layer: str,
    ) -> bool:
        if fps <= 0 or len(frames) <= 1:
            return False
        timer_attr = "_leg_timer" if layer == "leg" else "_torso_timer"
        index_attr = "_leg_index" if layer == "leg" else "_torso_index"
        timer = getattr(self, timer_attr)
        index = getattr(self, index_attr)
        timer += dt * fps
        finished_cycle = False
        while timer >= 1.0:
            timer -= 1.0
            index = (index + 1) % len(frames)
            finished_cycle = index == 0
        setattr(self, timer_attr, timer)
        setattr(self, index_attr, index)
        return finished_cycle


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


def load_boss_animation_layers(variant: str) -> BossAnimationLayers:
    """Load layered animations (legs, torso, death) for bosses.

    If no variant folder exists, this loader will fall back to sprites placed
    directly under ``assets/enemigos/boss`` so you can simply drop your PNGs in
    that folder without an extra subdirectory.
    """

    variant_slug = (variant or "default").strip().lower() or "default"
    base_dir = _resolve_boss_dir(variant_slug)
    color = _VARIANT_COLORS.get(variant_slug, _VARIANT_COLORS["default"])

    leg_frames: dict[str, list[pygame.Surface]] = {}
    torso_frames: dict[str, list[pygame.Surface]] = {}

    for state, count in _BOSS_LEG_COUNTS.items():
        leg_frames[state] = _load_layer_frames(base_dir, "legs", state, count, color)

    for state, count in _BOSS_TORSO_COUNTS.items():
        torso_frames[state] = _load_layer_frames(base_dir, "torso", state, count, color)

    # Las imágenes originales de torso incluyen las piernas completas, lo que
    # provoca que se superpongan con la capa de piernas animadas y se vea un
    # par de piernas estáticas debajo. Eliminamos la región ocupada por las
    # piernas en todos los fotogramas de torso para que sólo se vea la capa
    # inferior animada.
    torso_frames = _strip_leg_region_from_torso(leg_frames, torso_frames)

    death_frames = _load_layer_frames(base_dir, "death", "", 9, color, allow_suffix=False)

    fallback = leg_frames.get("idle") or torso_frames.get("idle")
    fallback_surface = fallback[0] if fallback else _placeholder_surface(color)

    return BossAnimationLayers(
        legs=leg_frames,
        torso=torso_frames,
        death=death_frames,
        fallback=fallback_surface,
    )


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


def expected_boss_filenames(variant: str) -> dict[str, dict[str, list[str]] | list[str]]:
    """List expected filenames for boss variants under assets/enemigos/boss."""

    variant_slug = (variant or "default").strip().lower() or "default"
    base_dir = _resolve_boss_dir(variant_slug)

    legs: dict[str, list[str]] = {}
    for state, count in _BOSS_LEG_COUNTS.items():
        indices = _existing_layer_indices(base_dir, "legs", state)
        legs[state] = [f"legs_{state}_{i}.png" for i in (indices or range(count))]

    torso: dict[str, list[str]] = {}
    for state, count in _BOSS_TORSO_COUNTS.items():
        indices = _existing_layer_indices(base_dir, "torso", state)
        torso[state] = [f"torso_{state}_{i}.png" for i in (indices or range(count))]

    death_indices = _existing_layer_indices(base_dir, "death", "")
    death = [f"death_{i}.png" for i in (death_indices or range(9))]

    return {"legs": legs, "torso": torso, "death": death}


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


def _load_layer_frames(
    base_dir: Path,
    layer: str,
    state: str,
    expected_count: int,
    color: tuple[int, int, int],
    *,
    allow_suffix: bool = True,
) -> list[pygame.Surface]:
    frames: list[pygame.Surface] = []
    pattern = f"{layer}_{state}_*.png" if allow_suffix and state else f"{layer}_{state}*.png"
    for path in sorted(base_dir.glob(pattern)):
        try:
            frame = pygame.image.load(path.as_posix()).convert_alpha()
        except pygame.error:
            frame = _placeholder_surface(color)
        frames.append(frame)

    if frames:
        return frames

    count = max(1, expected_count)
    return [_placeholder_surface(color) for _ in range(count)]


def _strip_leg_region_from_torso(
    leg_frames: dict[str, list[pygame.Surface]],
    torso_frames: dict[str, list[pygame.Surface]],
) -> dict[str, list[pygame.Surface]]:
    """Recorta la zona de las piernas de los sprites de torso.

    Esto evita que el boss muestre dos pares de piernas (unas animadas y otras
    estáticas) cuando se usan las mismas imágenes de torso/legs para ambos
    bosses.
    """

    # Calcular la unión de los rects ocupados por todas las piernas para saber
    # qué zona borrar del torso.
    leg_union: pygame.Rect | None = None
    for frames in leg_frames.values():
        for frame in frames:
            mask = pygame.mask.from_surface(frame)
            rect: pygame.Rect
            # Compatibilidad con distintas versiones de pygame: algunas
            # versiones no exponen ``get_bounding_rects`` y otras devuelven una
            # lista. Normalizamos para obtener siempre un único rectángulo.
            if hasattr(mask, "get_bounding_rect"):
                rect = mask.get_bounding_rect()
            elif hasattr(mask, "get_bounding_rects"):
                rects = mask.get_bounding_rects()
                rect = rects[0] if rects else pygame.Rect(0, 0, 0, 0)
            else:
                rect = frame.get_rect()
            leg_union = rect if leg_union is None else leg_union.union(rect)

    if leg_union is None:
        return torso_frames

    # Añadimos un pequeño margen para asegurarnos de borrar las rodillas incluso
    # si la máscara tiene huecos.
    leg_union = leg_union.inflate(4, 4)

    cropped: dict[str, list[pygame.Surface]] = {}
    for state, frames in torso_frames.items():
        cropped_frames: list[pygame.Surface] = []
        for frame in frames:
            surface = frame.copy()
            mask_rect = leg_union.clip(surface.get_rect())
            if mask_rect.width > 0 and mask_rect.height > 0:
                surface.fill((0, 0, 0, 0), mask_rect)
            cropped_frames.append(surface)
        cropped[state] = cropped_frames

    return cropped


def _existing_state_indices(base_dir: Path, state: str) -> list[int]:
    indices: list[int] = []
    for path in sorted(base_dir.glob(f"{state}_*.png")):
        suffix = path.stem[len(state) + 1 :]
        if suffix.isdigit():
            indices.append(int(suffix))
    return sorted(indices)


def _existing_layer_indices(base_dir: Path, layer: str, state: str) -> list[int]:
    prefix = f"{layer}_{state}_" if state else f"{layer}_"
    pattern = f"{prefix}*.png"
    indices: list[int] = []
    for path in sorted(base_dir.glob(pattern)):
        suffix = path.stem[len(prefix) :]
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


def _resolve_boss_dir(variant_slug: str) -> Path:
    """Return the directory that actually contains boss sprites.

    Preferred order:
    1) ``assets/enemigos/boss/<variant_slug>/`` if it has any PNG files.
    2) ``assets/enemigos/boss/`` (root) if sprites were placed there directly.
    This avoids silent placeholder usage when the user creates ``boss/`` but
    skips the extra variant subfolder.
    """

    variant_dir = _BOSS_ASSET_DIR / variant_slug
    if any(variant_dir.glob("*.png")):
        return variant_dir
    if any(_BOSS_ASSET_DIR.glob("*.png")):
        return _BOSS_ASSET_DIR
    return variant_dir
