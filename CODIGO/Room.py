from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Type

import pygame

from Config import CFG
from Enemy import Enemy, FastChaserEnemy, TankEnemy, ShooterEnemy, BasicEnemy
import Enemy as enemy_mod  # <- para usar enemy_mod.WANDER
from Bosses import CorruptedServerBoss
from asset_paths import assets_dir
from rewards import apply_reward_entry

# Plantillas de encuentros por umbral de dificultad.
ENCOUNTER_TABLE: list[tuple[int, list[list[Type[Enemy]]]]] = [
    (
        2,
        [
            [BasicEnemy],
            [BasicEnemy, BasicEnemy],
            [FastChaserEnemy],
            [BasicEnemy, FastChaserEnemy],
            [BasicEnemy, BasicEnemy, FastChaserEnemy],
        ],
    ),
    (
        4,
        [
            [BasicEnemy, BasicEnemy, FastChaserEnemy],
            [FastChaserEnemy, FastChaserEnemy],
            [BasicEnemy, FastChaserEnemy, FastChaserEnemy],
            [BasicEnemy, BasicEnemy, BasicEnemy],
        ],
    ),
    (
        6,
        [
            [TankEnemy],
            [TankEnemy, BasicEnemy],
            [TankEnemy, FastChaserEnemy],
            [BasicEnemy, BasicEnemy, TankEnemy],
        ],
    ),
    (
        8,
        [
            [TankEnemy, TankEnemy],
            [TankEnemy, FastChaserEnemy, FastChaserEnemy],
            [TankEnemy, BasicEnemy, FastChaserEnemy],
            [TankEnemy, TankEnemy, BasicEnemy],
        ],
    ),
    (
        10,
        [
            [ShooterEnemy, ShooterEnemy, FastChaserEnemy],
            [ShooterEnemy, TankEnemy, FastChaserEnemy],
            [ShooterEnemy, ShooterEnemy, TankEnemy],
            [ShooterEnemy, BasicEnemy, TankEnemy, FastChaserEnemy],
            [ShooterEnemy, ShooterEnemy, FastChaserEnemy, FastChaserEnemy],
        ],
    ),
]


_OBSTACLE_ASSET_DIR = assets_dir("obstacles")

_DOOR_RAW_CACHE: dict[str, pygame.Surface | None] = {}
_DOOR_SPRITE_CACHE: dict[tuple[str, tuple[int, int], str], pygame.Surface | None] = {}

# Sprite opcional para cofres personalizados (``assets/cofre.png`` o
# ``assets/obstacles/cofre.png``). Se escala al tamaño del rectángulo del cofre
# y se oscurece ligeramente cuando el cofre está abierto.
_TREASURE_SPRITE_CACHE: dict[tuple[int, int], pygame.Surface | None] = {}
_TREASURE_SPRITE_OPEN_CACHE: dict[tuple[int, int], pygame.Surface | None] = {}
_TREASURE_RAW_SPRITE: pygame.Surface | None = None
_TREASURE_SPRITE_TRIED: bool = False

# Sprite opcional para el Cofre Rúnico (``assets/cofre_runico.png`` o
# ``assets/obstacles/cofre_runico.png``). Se escala al tamaño del rectángulo
# del cofre y se oscurece ligeramente cuando está abierto.
_RUNE_SPRITE_CACHE: dict[tuple[int, int], pygame.Surface | None] = {}
_RUNE_SPRITE_OPEN_CACHE: dict[tuple[int, int], pygame.Surface | None] = {}
_RUNE_RAW_SPRITE: pygame.Surface | None = None
_RUNE_SPRITE_TRIED: bool = False

_START_GRAFFITI_SPRITE: pygame.Surface | None = None
_START_GRAFFITI_TRIED: bool = False


def _load_raw_treasure_sprite() -> pygame.Surface | None:
    global _TREASURE_SPRITE_TRIED
    global _TREASURE_RAW_SPRITE

    if _TREASURE_SPRITE_TRIED:
        return _TREASURE_RAW_SPRITE

    _TREASURE_SPRITE_TRIED = True
    candidates = [assets_dir("cofre.png"), assets_dir("obstacles", "cofre.png")]

    for path in candidates:
        if not path.exists():
            continue
        try:
            _TREASURE_RAW_SPRITE = pygame.image.load(path.as_posix()).convert_alpha()
            break
        except pygame.error:
            _TREASURE_RAW_SPRITE = None
    return _TREASURE_RAW_SPRITE


def _load_treasure_sprite(size: tuple[int, int], opened: bool) -> pygame.Surface | None:
    cached = (
        _TREASURE_SPRITE_OPEN_CACHE if opened else _TREASURE_SPRITE_CACHE
    ).get(size)
    if cached is not None or size in _TREASURE_SPRITE_CACHE:
        return cached

    raw = _load_raw_treasure_sprite()
    sprite = raw.copy() if raw is not None else None

    if sprite is not None and sprite.get_size() != size:
        sprite = pygame.transform.smoothscale(sprite, size)

    _TREASURE_SPRITE_CACHE[size] = sprite
    if sprite is not None:
        opened_variant = sprite.copy()
        opened_variant.fill((180, 180, 180, 255), special_flags=pygame.BLEND_RGBA_MULT)
        _TREASURE_SPRITE_OPEN_CACHE[size] = opened_variant
    else:
        _TREASURE_SPRITE_OPEN_CACHE[size] = None

    return _TREASURE_SPRITE_OPEN_CACHE[size] if opened else sprite


def _load_raw_rune_chest_sprite() -> pygame.Surface | None:
    global _RUNE_SPRITE_TRIED
    global _RUNE_RAW_SPRITE

    if _RUNE_SPRITE_TRIED:
        return _RUNE_RAW_SPRITE

    _RUNE_SPRITE_TRIED = True
    candidates = [
        assets_dir("cofre_runico.png"),
        assets_dir("obstacles", "cofre_runico.png"),
    ]

    for path in candidates:
        if not path.exists():
            continue
        try:
            _RUNE_RAW_SPRITE = pygame.image.load(path.as_posix()).convert_alpha()
            break
        except pygame.error:
            _RUNE_RAW_SPRITE = None
    return _RUNE_RAW_SPRITE


def _load_rune_chest_sprite(size: tuple[int, int], opened: bool) -> pygame.Surface | None:
    cached = (_RUNE_SPRITE_OPEN_CACHE if opened else _RUNE_SPRITE_CACHE).get(size)
    if cached is not None or size in _RUNE_SPRITE_CACHE:
        return cached

    raw = _load_raw_rune_chest_sprite()
    sprite = raw.copy() if raw is not None else None

    if sprite is not None and sprite.get_size() != size:
        sprite = pygame.transform.smoothscale(sprite, size)

    _RUNE_SPRITE_CACHE[size] = sprite
    if sprite is not None:
        opened_variant = sprite.copy()
        opened_variant.fill((180, 180, 180, 255), special_flags=pygame.BLEND_RGBA_MULT)
        _RUNE_SPRITE_OPEN_CACHE[size] = opened_variant
    else:
        _RUNE_SPRITE_OPEN_CACHE[size] = None

    return _RUNE_SPRITE_OPEN_CACHE[size] if opened else sprite


def _load_start_graffiti_sprite() -> pygame.Surface | None:
    global _START_GRAFFITI_TRIED
    global _START_GRAFFITI_SPRITE

    if _START_GRAFFITI_TRIED:
        return _START_GRAFFITI_SPRITE

    _START_GRAFFITI_TRIED = True
    path = assets_dir("obstacles", "grafiti.png")
    if not path.exists():
        return None

    try:
        _START_GRAFFITI_SPRITE = pygame.image.load(path.as_posix()).convert_alpha()
    except pygame.error:
        _START_GRAFFITI_SPRITE = None
    return _START_GRAFFITI_SPRITE
_OBSTACLE_ASSET_DIR.mkdir(parents=True, exist_ok=True)


def _treasure_box_from_sprite_rect(
    sprite_rect: pygame.Rect, size: tuple[int, int] | None
) -> pygame.Rect:
    """Crea un rectángulo centrado en el sprite usando el tamaño dado."""

    try:
        box_w, box_h = size if size is not None else CFG.TREASURE_SIZE  # type: ignore[attr-defined]
        box_w, box_h = int(box_w), int(box_h)
    except Exception:
        box_w = box_h = 32

    box_w = box_w if box_w > 0 else 32
    box_h = box_h if box_h > 0 else 32

    return pygame.Rect(
        sprite_rect.centerx - box_w // 2,
        sprite_rect.centery - box_h // 2,
        box_w,
        box_h,
    )


def _treasure_hitbox_from_sprite_rect(sprite_rect: pygame.Rect) -> pygame.Rect:
    """Área de interacción del cofre (para detectar cercanía/interacción)."""

    size = getattr(CFG, "TREASURE_HITBOX_SIZE", None)
    return _treasure_box_from_sprite_rect(sprite_rect, size)


def _treasure_collision_from_sprite_rect(
    sprite_rect: pygame.Rect,
) -> pygame.Rect | None:
    """Área sólida que bloquea al jugador (más pequeña que el sprite)."""

    size = getattr(CFG, "TREASURE_COLLISION_SIZE", None)
    if size is None:
        return None

    return _treasure_box_from_sprite_rect(sprite_rect, size)


@dataclass(frozen=True)
class ObstacleSpriteInfo:
    filename: str | Path | None = None
    scale: tuple[float, float] = (1.0, 1.0)
    offset: tuple[int, int] = (0, 0)
    frame_count: int = 1
    fps: float = 0.0


_OBSTACLE_FRAME_CACHE: dict[tuple[tuple[int, int], str], list[pygame.Surface]] = {}
_OBSTACLE_SPRITE_OFFSETS: dict[tuple[tuple[int, int], str], tuple[int, int]] = {}

_GLOBAL_OBSTACLE_SCALE: tuple[float, float] = (1.0, 1.0)
_OBSTACLE_SCALE_OVERRIDES: dict[str, tuple[float, float]] = {}

_DEFAULT_OBSTACLE_ANIMATION_FPS = 6.0

_OBSTACLE_LIBRARY: dict[tuple[int, int], dict[str, ObstacleSpriteInfo]] = {
    (1, 1): {
        "silla": ObstacleSpriteInfo("silla.png", scale=(2, 2)),
        "hoyo": ObstacleSpriteInfo("hoyo.png", scale=(2, 2)),
        "caneca": ObstacleSpriteInfo("caneca.png", scale=(2, 2)),
    },
    (1, 2): {
        "tubo_verde": ObstacleSpriteInfo(
            "tubo_verde_1x2.png", scale=(1, 1), frame_count=4, fps=_DEFAULT_OBSTACLE_ANIMATION_FPS
        ),
        "tubo_verde_vacio": ObstacleSpriteInfo("tubo_verde_vacio_1x2.png", scale=(1, 1)),
        "tubo_verde_singular": ObstacleSpriteInfo(
            "tubo_verde_singular_1x2.png", scale=(1, 1), frame_count=4, fps=_DEFAULT_OBSTACLE_ANIMATION_FPS
        ),
    },
    (2, 1): {
        "pantalla": ObstacleSpriteInfo(
            "pantalla_2x1.png", frame_count=5, fps=_DEFAULT_OBSTACLE_ANIMATION_FPS
        ),
        "impresora": ObstacleSpriteInfo(
            "impresora_2x1.png", frame_count=2, fps=_DEFAULT_OBSTACLE_ANIMATION_FPS
        ),
    },
    (2, 2): {
        "pantallas": ObstacleSpriteInfo("pantallas_2x2.png"),
    },
    (4, 2): {
        "pantallas_azules": ObstacleSpriteInfo(
            "pantallas_azules_4x2.png", scale=(1, 1), frame_count=5, fps=_DEFAULT_OBSTACLE_ANIMATION_FPS
        ),
    },
}

_OBSTACLE_VARIANTS: dict[tuple[int, int], list[str]] = {
    size: list(variants.keys()) for size, variants in _OBSTACLE_LIBRARY.items()
}

_OBSTACLE_SIZE_WEIGHTS: list[tuple[tuple[int, int], float]] = [
    ((1, 1), 0.38),
    ((2, 1), 0.24),
    ((1, 2), 0.14),
    ((2, 2), 0.14),
    ((4, 2), 0.10),
]

_OBSTACLE_FALLBACK_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "silla": ((148, 108, 74), (96, 68, 44)),
    "hoyo": ((28, 28, 32), (10, 10, 12)),
    "caneca": ((54, 102, 176), (32, 62, 118)),
    "tubo_verde": ((56, 142, 60), (32, 82, 36)),
    "tubo_verde_vacio": ((56, 142, 60), (32, 82, 36)),
    "tubo_verde_singular": ((56, 142, 60), (32, 82, 36)),
    "pantalla": ((82, 188, 242), (36, 90, 126)),
    "impresora": ((210, 210, 210), (128, 128, 128)),
    "pantallas": ((120, 160, 196), (70, 100, 132)),
    "pantallas_azules": ((74, 142, 212), (28, 68, 128)),
}


def _normalize_scale_value(scale: float | tuple[float, float] | list[float]) -> tuple[float, float]:
    if isinstance(scale, (int, float)):
        value = float(scale)
        if value <= 0:
            raise ValueError("scale debe ser un número positivo")
        return (value, value)
    if isinstance(scale, (list, tuple)) and len(scale) == 2:
        try:
            sx = float(scale[0])
            sy = float(scale[1])
        except (TypeError, ValueError) as exc:
            raise ValueError("scale debe contener números válidos") from exc
        if sx <= 0 or sy <= 0:
            raise ValueError("scale debe contener números positivos")
        return (sx, sy)
    raise ValueError("scale debe ser un número o una tupla/lista de dos números")


def set_obstacle_sprite_scale(
    variant: str | None, scale: float | tuple[float, float] | list[float] | None
) -> None:
    """Configura (o elimina) la escala aplicada a un sprite de obstáculo."""

    slug = (variant or "").lower().strip() or "default"
    if scale is None:
        _OBSTACLE_SCALE_OVERRIDES.pop(slug, None)
    else:
        _OBSTACLE_SCALE_OVERRIDES[slug] = _normalize_scale_value(scale)
    clear_obstacle_sprite_cache()


def set_global_obstacle_scale(scale: float | tuple[float, float] | list[float] | None) -> None:
    """Aplica un factor de escala uniforme a todos los sprites de obstáculos."""

    global _GLOBAL_OBSTACLE_SCALE
    if scale is None:
        _GLOBAL_OBSTACLE_SCALE = (1.0, 1.0)
    else:
        _GLOBAL_OBSTACLE_SCALE = _normalize_scale_value(scale)
    clear_obstacle_sprite_cache()


def clear_obstacle_sprite_cache() -> None:
    """Vacia el caché interno para volver a cargar sprites personalizados."""

    _OBSTACLE_FRAME_CACHE.clear()
    _OBSTACLE_SPRITE_OFFSETS.clear()


def _resolve_sprite_info(size_tiles: tuple[int, int], variant_slug: str) -> ObstacleSpriteInfo:
    variants = _OBSTACLE_LIBRARY.get(size_tiles)
    if variants:
        info = variants.get(variant_slug) or variants.get("default")
        if info is not None:
            return info
    generic = _OBSTACLE_LIBRARY.get((0, 0), {})
    return generic.get(variant_slug) or generic.get("default") or ObstacleSpriteInfo()


def _resolve_scale(variant_slug: str, base_scale: tuple[float, float]) -> tuple[float, float]:
    override = _OBSTACLE_SCALE_OVERRIDES.get(variant_slug)
    scale_x, scale_y = override if override else base_scale
    global_x, global_y = _GLOBAL_OBSTACLE_SCALE
    return (max(0.01, scale_x * global_x), max(0.01, scale_y * global_y))


def _resolve_offset(
    size_tiles: tuple[int, int], sprite: pygame.Surface, extra_offset: tuple[int, int]
) -> tuple[int, int]:
    ts = CFG.TILE_SIZE
    width_tiles, height_tiles = size_tiles
    width_px = width_tiles * ts
    height_px = height_tiles * ts
    offset_x = (width_px - sprite.get_width()) // 2 + extra_offset[0]
    offset_y = (height_px - sprite.get_height()) // 2 + extra_offset[1]
    return (offset_x, offset_y)


def _candidate_stems(
    size_tiles: tuple[int, int], variant_slug: str, info: ObstacleSpriteInfo
) -> list[tuple[Path, str]]:
    width_tiles, height_tiles = size_tiles
    stems: list[tuple[Path, str]] = []

    if info.filename:
        path = Path(info.filename)
        if not path.is_absolute():
            path = _OBSTACLE_ASSET_DIR / path
        stems.append((path.parent, path.stem))

    if variant_slug and variant_slug != "default":
        stems.extend(
            [
                (_OBSTACLE_ASSET_DIR, f"{variant_slug}_{width_tiles}x{height_tiles}"),
                (
                    _OBSTACLE_ASSET_DIR,
                    f"obstacle_{variant_slug}_{width_tiles}x{height_tiles}",
                ),
                (_OBSTACLE_ASSET_DIR, f"obstacle_{variant_slug}"),
                (_OBSTACLE_ASSET_DIR, variant_slug),
            ]
        )

    stems.extend(
        [
            (_OBSTACLE_ASSET_DIR, f"crate_{width_tiles}x{height_tiles}"),
            (_OBSTACLE_ASSET_DIR, "crate"),
        ]
    )

    unique: list[tuple[Path, str]] = []
    seen: set[tuple[Path, str]] = set()
    for stem in stems:
        if stem not in seen:
            unique.append(stem)
            seen.add(stem)
    return unique


def _build_placeholder_sprite(
    size_tiles: tuple[int, int], target_size: tuple[int, int], variant_slug: str
) -> pygame.Surface:
    width_tiles, height_tiles = size_tiles
    ts = CFG.TILE_SIZE
    base_color, border_color = _OBSTACLE_FALLBACK_COLORS.get(
        variant_slug,
        ((124, 92, 64), (90, 60, 38)),
    )
    surface = pygame.Surface(target_size, pygame.SRCALPHA)
    surface.fill(base_color)
    pygame.draw.rect(surface, border_color, surface.get_rect(), 3)
    if width_tiles >= 2 or height_tiles >= 2:
        inner = surface.get_rect().inflate(-ts // 2, -ts // 2)
        if inner.width > 0 and inner.height > 0:
            pygame.draw.rect(surface, border_color, inner, 1)
    return surface


def _load_obstacle_frames(
    size_tiles: tuple[int, int], variant: str | None = None
) -> list[pygame.Surface]:
    width_tiles, height_tiles = size_tiles
    variant_slug = (variant or "").lower().strip() or "default"
    key = (size_tiles, variant_slug)
    cached = _OBSTACLE_FRAME_CACHE.get(key)
    if cached is not None:
        return cached

    ts = CFG.TILE_SIZE
    info = _resolve_sprite_info(size_tiles, variant_slug)
    expected_frames = max(1, int(info.frame_count))
    scale_x, scale_y = _resolve_scale(variant_slug, info.scale)
    width_px = width_tiles * ts
    height_px = height_tiles * ts
    target_size = (
        max(1, int(round(width_px * scale_x))),
        max(1, int(round(height_px * scale_y))),
    )

    def _load_scaled_surface(path: Path) -> pygame.Surface | None:
        try:
            surface = pygame.image.load(path.as_posix()).convert_alpha()
        except pygame.error:
            return None
        if surface.get_size() != target_size:
            surface = pygame.transform.smoothscale(surface, target_size)
        return surface

    frames: list[pygame.Surface] = []
    stems = _candidate_stems(size_tiles, variant_slug, info)
    for directory, stem in stems:
        frame_paths: list[Path] = []
        if expected_frames > 1:
            frame_paths = [directory / f"{stem}_{i}.png" for i in range(expected_frames)]
            frame_paths = [path for path in frame_paths if path.exists()]
        if frame_paths:
            for path in frame_paths:
                surface = _load_scaled_surface(path)
                if surface is not None:
                    frames.append(surface)
            break

        candidate = directory / f"{stem}.png"
        if candidate.exists():
            surface = _load_scaled_surface(candidate)
            if surface is not None:
                frames.append(surface)
                break

    if not frames:
        frames.append(_build_placeholder_sprite(size_tiles, target_size, variant_slug))

    if len(frames) < expected_frames and frames:
        repeats = (expected_frames + len(frames) - 1) // len(frames)
        frames = (frames * repeats)[:expected_frames]

    offset = _resolve_offset(size_tiles, frames[0], info.offset)
    _OBSTACLE_SPRITE_OFFSETS[key] = offset
    _OBSTACLE_FRAME_CACHE[key] = frames
    return frames


def _load_obstacle_sprite(size_tiles: tuple[int, int], variant: str | None = None) -> pygame.Surface:
    return _load_obstacle_frames(size_tiles, variant)[0]


def _load_door_sprite(
    opened: bool, vertical: bool, size: tuple[int, int], direction: str | None = None
) -> pygame.Surface | None:
    """Carga y escala el sprite de la puerta según su orientación, estado y dirección."""

    variant = ("opened" if opened else "closed") + ("_vertical" if vertical else "_side")
    direction_key = (direction or "").upper()
    cache_key = (variant, size, direction_key)
    if cache_key in _DOOR_SPRITE_CACHE:
        return _DOOR_SPRITE_CACHE[cache_key]

    filename = "DoorOpened.png" if opened else "DoorClosed.png"
    if not vertical:
        filename = "DoorOpenedSide.png" if opened else "DoorClosedSide.png"

    raw_sprite = _DOOR_RAW_CACHE.get(filename)
    if filename not in _DOOR_RAW_CACHE:
        path = assets_dir("obstacles", filename)
        if path.exists():
            try:
                raw_sprite = pygame.image.load(path.as_posix()).convert_alpha()
            except pygame.error:
                raw_sprite = None
        else:
            raw_sprite = None
        _DOOR_RAW_CACHE[filename] = raw_sprite

    sprite = raw_sprite
    if sprite is not None and sprite.get_size() != size:
        sprite = pygame.transform.smoothscale(sprite, size)
    if sprite is not None and direction_key == "W" and not vertical:
        sprite = pygame.transform.rotate(sprite, 180)

    _DOOR_SPRITE_CACHE[cache_key] = sprite
    return sprite

class Room:
    """
    Un cuarto sobre una grilla MAP_W x MAP_H (en tiles).
    - `tiles` = 1 (pared), 0 (suelo)
    - `bounds` = (rx, ry, rw, rh) en tiles: rectángulo de la habitación dentro del mapa
    - `doors` = dict con direcciones "N","S","E","W" -> bool (existe puerta hacia ese vecino)
    - Enemigos se generan 1 sola vez con `ensure_spawn(...)`
    """

    def __init__(self) -> None:
        # mapa lleno de paredes por defecto
        self.tiles: List[List[int]] = [[CFG.WALL for _ in range(CFG.MAP_W)] for _ in range(CFG.MAP_H)]
        self.bounds: Optional[Tuple[int, int, int, int]] = None
        self.doors: Dict[str, bool] = {"N": False, "S": False, "E": False, "W": False}

        # contenido dinámico
        self.enemies: List[Enemy] = []
        self.pickups: list = []
        self._spawn_done: bool = False
        self._door_width_tiles = 2
        self._door_side_height_tiles = 3
        self._door_corridor_length_tiles = 3
        self._door_block_tiles: set[tuple[int, int]] = set()
        self._locked: bool = False

        # 🔒 estado de puertas
        self.locked = getattr(self, "locked", False)
        self.cleared: bool = False

        # Salas corruptas (glitch)
        self.is_corrupted: bool = getattr(self, "is_corrupted", False)
        self.corrupted_loot_mode: str = getattr(self, "corrupted_loot_mode", "upgrade")
        self.corrupted_chip_bonus: float = getattr(self, "corrupted_chip_bonus", 0.5)
        self._glitch_timer: float = 0.0
        self._next_glitch_burst: float = random.uniform(0.08, 0.18)
        self._glitch_lines: list[tuple[pygame.Rect, tuple[int, int, int, int]]] = []
        self._glitch_offset: tuple[int, int] = (0, 0)
        self._microchips_dropped_total: int = 0

        self.type = getattr(self, "type", "normal")  # "normal" / "shop"
        self.bounds = getattr(self, "bounds", (0, 0, 9, 9))  # (rx,ry,rw,rh) tiles
        self.doors = getattr(self, "doors", {"N":False,"S":False,"E":False,"W":False})

        # --- NUEVO ---
        self.safe = False
        self.no_spawn = False
        self.no_combat = False
        self._populated_once = False
        self.shopkeeper = None
        self.treasure: dict | None = None
        self.is_start_room: bool = getattr(self, "is_start_room", False)
        self.treasure_message: str = ""
        self.treasure_message_until: int = 0
        self._treasure_tiles: set[tuple[int, int]] = set()
        self.rune_chest: dict | None = None
        self.rune_message: str = ""
        self.rune_message_until: int = 0
        self._rune_chest_tiles: set[tuple[int, int]] = set()
        self._rune_wave_triggered: bool = False
        self._rune_wave_cleared: bool = False
        self._notification_callback: Callable[[str, pygame.Surface | None], None] | None = None

        self.obstacles: list[dict] = []
        self._obstacle_tiles: set[tuple[int, int]] = set()
        self._shop_decorated: bool = False
        self._shop_decor_seed: int | None = None

        # Bosses
        self.boss_blueprint = getattr(self, "boss_blueprint", None)
        self.boss_loot_table = getattr(self, "boss_loot_table", None)
        self.boss_instance = None
        self.boss_defeated = False
        self._boss_spawned = False
        self._boss_corner_obstacles_placed = False
        
        # Sonido de cofre
        self._chest_sound = None
        self._load_chest_sound()
        
        # Sonidos de puerta
        self._door_closed_sound = None
        self._door_open_sound = None
        self._load_door_sounds()


    # ------------------------------------------------------------------ #
    # API estática para sprites de obstáculos
    # ------------------------------------------------------------------ #
    
    def _load_chest_sound(self) -> None:
        """Carga el sonido de cofre."""
        try:
            audio_path = Path("assets/audio/chest_sfx.mp3")
            if not audio_path.exists():
                audio_path = Path(__file__).parent / "assets" / "audio" / "chest_sfx.mp3"
            if audio_path.exists():
                self._chest_sound = pygame.mixer.Sound(audio_path.as_posix())
                self._chest_sound.set_volume(0.15)  # 15% del volumen
            else:
                self._chest_sound = None
        except (pygame.error, FileNotFoundError):
            self._chest_sound = None
    
    def _load_door_sounds(self) -> None:
        """Carga los sonidos de puerta (cerrada y abierta)."""
        # Cargar sonido de puerta cerrada
        try:
            audio_path = Path("assets/audio/door_closed_sfx.mp3")
            if not audio_path.exists():
                audio_path = Path(__file__).parent / "assets" / "audio" / "door_closed_sfx.mp3"
            if audio_path.exists():
                self._door_closed_sound = pygame.mixer.Sound(audio_path.as_posix())
                self._door_closed_sound.set_volume(0.2)  # 20% del volumen
            else:
                self._door_closed_sound = None
        except (pygame.error, FileNotFoundError):
            self._door_closed_sound = None
        
        # Cargar sonido de puerta abierta
        try:
            audio_path = Path("assets/audio/door_open_sfx.mp3")
            if not audio_path.exists():
                audio_path = Path(__file__).parent / "assets" / "audio" / "door_open_sfx.mp3"
            if audio_path.exists():
                self._door_open_sound = pygame.mixer.Sound(audio_path.as_posix())
                self._door_open_sound.set_volume(0.2)  # 20% del volumen
            else:
                self._door_open_sound = None
        except (pygame.error, FileNotFoundError):
            self._door_open_sound = None
    
    def play_door_closed_sound(self) -> None:
        """Reproduce el sonido de puerta cerrada al entrar a una room no explorada."""
        if self._door_closed_sound:
            self._door_closed_sound.play()
    
    def play_door_open_sound(self) -> None:
        """Reproduce el sonido de puerta abierta cuando se eliminan todos los enemigos."""
        if self._door_open_sound:
            self._door_open_sound.play()

    def set_notification_callback(
        self, callback: Callable[[str, pygame.Surface | None], None] | None
    ) -> None:
        """Define un callback para mostrar mensajes en el HUD en lugar de sobre el cofre."""

        self._notification_callback = callback

    @staticmethod
    def set_obstacle_sprite_scale(
        variant: str | None, scale: float | tuple[float, float] | list[float] | None
    ) -> None:
        """Envuelve :func:`set_obstacle_sprite_scale` para uso externo."""

        set_obstacle_sprite_scale(variant, scale)

    @staticmethod
    def set_global_obstacle_scale(
        scale: float | tuple[float, float] | list[float] | None
    ) -> None:
        """Permite ajustar la escala común para todos los sprites desde ``Room``."""

        set_global_obstacle_scale(scale)

    @staticmethod
    def clear_obstacle_sprite_cache() -> None:
        """Reexpone el limpiador del caché de sprites de obstáculos."""

        clear_obstacle_sprite_cache()


    # ------------------------------------------------------------------ #
    # Construcción de la habitación
    # ------------------------------------------------------------------ #
    def build_centered(self, rw: int, rh: int) -> None:
        """
        Talla un rectángulo de suelo centrado en el mapa (en tiles).
        rw/rh son el tamaño de la habitación en tiles.
        """
        rx = CFG.MAP_W // 2 - rw // 2
        ry = CFG.MAP_H // 2 - rh // 2
        self.bounds = (rx, ry, rw, rh)
        
        

        # Suelo dentro de la habitación
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                if 0 <= x < CFG.MAP_W and 0 <= y < CFG.MAP_H:
                    self.tiles[y][x] = 0

    # ------------------------------------------------------------------ #
    # Obstáculos
    # ------------------------------------------------------------------ #
    def clear_obstacles(self) -> None:
        self.obstacles.clear()
        self._obstacle_tiles.clear()
        self._boss_corner_obstacles_placed = False

    def _can_place_obstacle(
        self,
        tx: int,
        ty: int,
        w_tiles: int,
        h_tiles: int,
        forbidden_tiles: set[tuple[int, int]] | None = None,
    ) -> bool:
        if self.bounds is None:
            return False
        rx, ry, rw, rh = self.bounds
        min_tx = rx + 1
        min_ty = ry + 1
        max_tx = rx + rw - w_tiles - 1
        max_ty = ry + rh - h_tiles - 1
        if tx < min_tx or ty < min_ty or tx > max_tx or ty > max_ty:
            return False
        forbidden_tiles = forbidden_tiles or set()
        for dy in range(h_tiles):
            for dx in range(w_tiles):
                cx = tx + dx
                cy = ty + dy
                if not (0 <= cx < CFG.MAP_W and 0 <= cy < CFG.MAP_H):
                    return False
                if self.tiles[cy][cx] != CFG.FLOOR:
                    return False
                if (cx, cy) in self._obstacle_tiles or (cx, cy) in self._treasure_tiles or (cx, cy) in self._rune_chest_tiles:
                    return False
                if (cx, cy) in forbidden_tiles:
                    return False
        return True

    def _register_obstacle(
        self,
        tx: int,
        ty: int,
        w_tiles: int,
        h_tiles: int,
        variant: str | None = None,
    ) -> None:
        ts = CFG.TILE_SIZE
        rect = pygame.Rect(tx * ts, ty * ts, w_tiles * ts, h_tiles * ts)
        variant_slug = (variant or "").lower().strip() or "default"
        info = _resolve_sprite_info((w_tiles, h_tiles), variant_slug)
        frame_count_hint = max(1, int(info.frame_count))
        start_phase = random.random()
        start_frame = int(start_phase * frame_count_hint) % frame_count_hint
        speed_jitter = random.uniform(0.85, 1.15)
        tiles = {(tx + dx, ty + dy) for dy in range(h_tiles) for dx in range(w_tiles)}
        self.obstacles.append({
            "rect": rect,
            "tiles": tiles,
            "size": (w_tiles, h_tiles),
            "variant": variant_slug,
            "frame_index": start_frame,
            "frame_timer": start_phase % 1.0,
            "animation_fps": max(0.0, float(info.fps)),
            "animation_speed": speed_jitter,
            "expected_frames": frame_count_hint,
        })
        self._obstacle_tiles.update(tiles)

    def generate_obstacles(
        self,
        rng: random.Random | None = None,
        max_density: float = 0.08,
        forbidden_tiles: set[tuple[int, int]] | None = None,
        max_obstacles_override: int | None = None,
    ) -> None:
        if self.bounds is None:
            return
        self.clear_obstacles()
        rng = rng or random
        forbidden_tiles = forbidden_tiles or set()

        rx, ry, rw, rh = self.bounds
        interior_w = max(0, rw - 2)
        interior_h = max(0, rh - 2)
        if interior_w <= 0 or interior_h <= 0:
            return

        interior_area = interior_w * interior_h
        max_obstacles = max(0, int(interior_area * max_density))
        if max_obstacles_override is not None:
            max_obstacles = max(0, int(max_obstacles_override))
        if max_obstacles <= 0:
            max_obstacles = 1 if interior_area >= 6 else 0
        if max_obstacles <= 0:
            return

        available_sizes = [
            (size, weight)
            for size, weight in _OBSTACLE_SIZE_WEIGHTS
            if interior_w >= size[0] and interior_h >= size[1]
        ]
        if not available_sizes:
            available_sizes = [((1, 1), 1.0)]

        attempts = max_obstacles * 6
        placed = 0
        while placed < max_obstacles and attempts > 0:
            attempts -= 1
            sizes, weights = zip(*available_sizes)
            w_tiles, h_tiles = rng.choices(sizes, weights=weights, k=1)[0]
            min_tx = rx + 1
            max_tx = rx + rw - w_tiles - 1
            min_ty = ry + 1
            max_ty = ry + rh - h_tiles - 1
            if max_tx < min_tx or max_ty < min_ty:
                continue
            tx = rng.randint(min_tx, max_tx)
            ty = rng.randint(min_ty, max_ty)
            if not self._can_place_obstacle(
                tx, ty, w_tiles, h_tiles, forbidden_tiles=forbidden_tiles
            ):
                continue
            variant_choices = _OBSTACLE_VARIANTS.get((w_tiles, h_tiles), ["default"])
            variant = rng.choice(variant_choices)
            self._register_obstacle(tx, ty, w_tiles, h_tiles, variant=variant)
            placed += 1

    def _spawn_boss_corner_obstacles(self, rng: random.Random | None = None) -> None:
        """Coloca 0-2 obstáculos pequeños en cada esquina de la sala del boss."""

        if self.bounds is None or self._boss_corner_obstacles_placed:
            return
        if self.type != "boss":
            return

        rng = rng or random
        rx, ry, rw, rh = self.bounds
        corners = [
            (rx + 1, ry + 1),
            (rx + rw - 2, ry + 1),
            (rx + 1, ry + rh - 2),
            (rx + rw - 2, ry + rh - 2),
        ]

        candidate_sizes = [
            size
            for size in [(1, 1), (1, 2), (2, 1), (2, 2)]
            if rx + rw - size[0] - 1 >= rx + 1 and ry + rh - size[1] - 1 >= ry + 1
        ]
        candidate_sizes = candidate_sizes or [(1, 1)]

        for base_tx, base_ty in corners:
            spots = [
                (base_tx, base_ty),
                (min(base_tx + 1, rx + rw - 2), base_ty),
                (base_tx, min(base_ty + 1, ry + rh - 2)),
            ]
            rng.shuffle(spots)
            desired = rng.randint(0, 2)
            placed = 0
            for tx, ty in spots:
                if placed >= desired:
                    break
                for w_tiles, h_tiles in rng.sample(candidate_sizes, k=len(candidate_sizes)):
                    if placed >= desired:
                        break
                    if self._can_place_obstacle(tx, ty, w_tiles, h_tiles):
                        variant_pool = _OBSTACLE_VARIANTS.get((w_tiles, h_tiles), ["default"])
                        variant = rng.choice(variant_pool)
                        self._register_obstacle(tx, ty, w_tiles, h_tiles, variant=variant)
                        placed += 1
                        break

        self._boss_corner_obstacles_placed = True

    # ------------------------------------------------------------------ #
    # Corredores cortos (visuales) hacia las puertas
    # ------------------------------------------------------------------ #
    def carve_corridors(
        self, width_tiles: int = 2, length_tiles: int = 3, side_height_tiles: int | None = None
    ) -> None:
        """
        Talla la abertura/“corredor” exactamente centrado en tiles.
        Guarda el ancho para que _door_trigger_rects use el mismo valor.
        """
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        self._door_width_tiles = max(1, int(width_tiles))
        # Mantén la altura lateral igual al ancho del pasillo para no cambiar el corredor.
        self._door_side_height_tiles = self._door_width_tiles
        base_length = max(1, int(length_tiles))
        self._door_corridor_length_tiles = base_length

        def carve_rect(x: int, y: int, w: int, h: int) -> None:
            for yy in range(y, y + h):
                if 0 <= yy < CFG.MAP_H:
                    for xx in range(x, x + w):
                        if 0 <= xx < CFG.MAP_W:
                            self.tiles[yy][xx] = 0

        W = self._door_width_tiles
        side_height = self._door_side_height_tiles
        # centro “en medios tiles” (evita perder la mitad cuando rw es par)
        center_tx2 = rx * 2 + rw   # = 2*(rx + rw/2)
        center_ty2 = ry * 2 + rh

        # izquierda superior del hueco (en tiles), usando la misma aritmética para N/S y E/W
        left_tile   = (center_tx2 - W) // 2  # N y S
        top_tile    = (center_ty2 - side_height) // 2  # E y W

        # Longitudes dinámicas hasta el borde del mapa.
        north_length = ry
        south_length = CFG.MAP_H - (ry + rh)
        east_length = CFG.MAP_W - (rx + rw)
        west_length = rx

        # Norte (arriba)
        if self.doors.get("N"):
            length = max(base_length, north_length)
            carve_rect(left_tile, ry - length, W, length)
        # Sur (abajo)
        if self.doors.get("S"):
            length = max(base_length, south_length)
            carve_rect(left_tile, ry + rh, W, length)
        # Este (derecha)
        if self.doors.get("E"):
            length = max(base_length, east_length)
            carve_rect(rx + rw, top_tile, length, side_height)
        # Oeste (izquierda)
        if self.doors.get("W"):
            length = max(base_length, west_length)
            carve_rect(rx - length, top_tile, length, side_height)

        self._refresh_door_block_tiles()

    def _door_opening_rects(self) -> dict[str, pygame.Rect]:
        """Rectángulos EXACTOS de la abertura de cada puerta (en px)."""
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE

        left_px   = rx * ts
        right_px  = (rx + rw) * ts
        top_px    = ry * ts
        bottom_px = (ry + rh) * ts

        W = max(1, getattr(self, "_door_width_tiles", 2))
        side_height = max(1, getattr(self, "_door_side_height_tiles", W))
        opening_px = W * ts
        side_opening_px = side_height * ts

        # mismos centros que usaste para tallar
        center_tx2 = rx * 2 + rw
        center_ty2 = ry * 2 + rh
        left_tile  = (center_tx2 - W) // 2
        top_tile   = (center_ty2 - side_height) // 2

        left_open_px = left_tile * ts
        top_open_px  = top_tile * ts
        side_top_open_px = top_tile * ts

        rects: dict[str, pygame.Rect] = {}
        if self.doors.get("N"):
            rects["N"] = pygame.Rect(left_open_px, top_px - ts, opening_px, ts)
        if self.doors.get("S"):
            rects["S"] = pygame.Rect(left_open_px, bottom_px, opening_px, ts)
        if self.doors.get("E"):
            rects["E"] = pygame.Rect(right_px, side_top_open_px, ts, side_opening_px)
        if self.doors.get("W"):
            rects["W"] = pygame.Rect(left_px - ts, side_top_open_px, ts, side_opening_px)
        return rects


    @property
    def locked(self) -> bool:
        return getattr(self, "_locked", False)

    @locked.setter
    def locked(self, value: bool) -> None:
        self._locked = bool(value)
        self._refresh_door_block_tiles()

    def _refresh_door_block_tiles(self) -> None:
        self._door_block_tiles.clear()
        if not getattr(self, "_locked", False):
            return
        if self.bounds is None:
            return

        rx, ry, rw, rh = self.bounds
        W = max(1, getattr(self, "_door_width_tiles", 2))
        side_height = max(1, getattr(self, "_door_side_height_tiles", W))

        center_tx2 = rx * 2 + rw
        center_ty2 = ry * 2 + rh
        left_tile = (center_tx2 - W) // 2
        top_tile = (center_ty2 - side_height) // 2

        max_x = CFG.MAP_W - 1
        max_y = CFG.MAP_H - 1

        if self.doors.get("N"):
            for dx in range(W):
                tx = left_tile + dx
                ty = ry - 1
                if 0 <= tx <= max_x and 0 <= ty <= max_y:
                    self._door_block_tiles.add((tx, ty))
        if self.doors.get("S"):
            for dx in range(W):
                tx = left_tile + dx
                ty = ry + rh
                if 0 <= tx <= max_x and 0 <= ty <= max_y:
                    self._door_block_tiles.add((tx, ty))
        if self.doors.get("E"):
            for dy in range(side_height):
                ty = top_tile + dy
                tx = rx + rw
                if 0 <= tx <= max_x and 0 <= ty <= max_y:
                    self._door_block_tiles.add((tx, ty))
        if self.doors.get("W"):
            for dy in range(side_height):
                ty = top_tile + dy
                tx = rx - 1
                if 0 <= tx <= max_x and 0 <= ty <= max_y:
                    self._door_block_tiles.add((tx, ty))

    
    # ---------- TIENDA ----------
    def _ensure_shopkeeper(self, cfg, ShopkeeperCls):
        if self.shopkeeper is not None:
            return
        rx, ry, rw, rh = self.bounds
        ts = cfg.TILE_SIZE
        cx = (rx + rw // 2) * ts + ts // 2 - ts
        cy = (ry + rh // 2) * ts + ts // 2 - ts
        self.shopkeeper = ShopkeeperCls((cx, cy))

    def _decorate_shop(self) -> None:
        if self._shop_decorated or self.bounds is None or self.shopkeeper is None:
            return

        if self._shop_decor_seed is None:
            rx, ry, rw, rh = self.bounds
            self._shop_decor_seed = (
                (rx * 73856093) ^ (ry * 19349663) ^ (rw * 83492791) ^ (rh * 2971215073)
            ) & 0xFFFFFFFF

        ts = CFG.TILE_SIZE
        sk_center = (
            self.shopkeeper.rect.centerx // ts,
            self.shopkeeper.rect.centery // ts,
        )
        forbidden_tiles: set[tuple[int, int]] = set()
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                forbidden_tiles.add((sk_center[0] + dx, sk_center[1] + dy))

        rng = random.Random(self._shop_decor_seed)
        self.generate_obstacles(
            rng=rng,
            max_density=0.03,
            forbidden_tiles=forbidden_tiles,
            max_obstacles_override=3,
        )
        self._shop_decorated = True

    def on_enter(self, player, cfg, ShopkeeperCls=None):
        """
        Llamado cuando entras a la sala.
        - Marca flags si es 'shop'
        - Evita spawn de enemigos
        - Crea Shopkeeper si aplica
        """
        self._microchips_dropped_total = 0
        if self.type == "shop":
            self.safe = True
            self.no_spawn = True
            self.no_combat = True
            self.locked = False
            if ShopkeeperCls:
                self._ensure_shopkeeper(cfg, ShopkeeperCls)
            self._decorate_shop()
        elif self.type == "boss":
            self.safe = False
            self.no_spawn = True
            self.no_combat = False
            self.locked = True
            if not self._boss_spawned:
                self._spawn_boss()
            self._spawn_boss_corner_obstacles()
            self._populated_once = True
            self._spawn_done = True
        else:
            # Salas normales/tesoro: poblar enemigos una vez si aplica
            self.safe = False
            self.no_combat = False
            if not self._populated_once and not self.no_spawn:
                # TODO: aquí tu lógica real de spawn por sala
                # e.g., self.enemies = spawn_enemies_for(self)
                pass
            self._populated_once = True

        if self.is_corrupted:
            for enemy in self.enemies:
                self._apply_corruption_to_enemy(enemy)

    def on_exit(self):
        """Llamado cuando sales de la sala."""
        # Nada especial por defecto. Podrías pausar IA/ambiente si quieres.
        pass

    def _spawn_boss(self) -> None:
        if self._boss_spawned:
            return
        blueprint = self.boss_blueprint or CorruptedServerBoss
        try:
            cx, cy = self.center_px()
        except AssertionError:
            self.build_centered(CFG.BOSS_ROOM_W, CFG.BOSS_ROOM_H)
            cx, cy = self.center_px()
        boss = blueprint(cx - 24, cy - 24)
        boss.x = cx - boss.w / 2
        boss.y = cy - boss.h / 2
        if hasattr(boss, "on_spawn"):
            boss.on_spawn(self)
        self.enemies.clear()
        self.enemies.append(boss)
        self.boss_instance = boss
        self._boss_spawned = True
        self._spawn_done = True
        self.locked = True

    def has_active_boss(self) -> bool:
        return self.type == "boss" and not self.boss_defeated

    def on_boss_defeated(self, boss) -> None:
        if self.boss_defeated or self.type != "boss":
            return
        self.boss_defeated = True
        self.locked = False
        self.cleared = True
        if hasattr(boss, "telegraphs"):
            boss.telegraphs.clear()
        if hasattr(boss, "puddles"):
            boss.puddles.clear()
        self.boss_instance = None
        if not self.treasure:
            self.spawn_boss_reward()

    def handle_events(self, events, player, shop_ui, world_surface, ui_font, screen_scale=1):
        """
        Maneja interacción con la tienda dentro de la sala (si es shop).
        No lee pygame.event.get() aquí; recibe la lista de events desde Game.
        """
        if self.rune_chest:
            self._handle_rune_chest_events(events, player)

        if self.treasure:
            self._handle_treasure_events(events, player)

        if self.type != "shop" or self.shopkeeper is None:
            return

        # ¿Jugador cerca? (usa .rect del jugador)
        can_interact = False
        if hasattr(player, "rect"):
            can_interact = self.shopkeeper.can_interact(player.rect())
        else:
            can_interact = True  # fallback

        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_e and can_interact:
                    if not shop_ui.active:
                        self.shopkeeper.play_interaction_sound()
                        shop_ui.open(
                            world_surface.get_width() // 2,
                            world_surface.get_height() // 2,
                            player=player,
                        )
                    else:
                        shop_ui.close()
                    continue

                if not shop_ui.active:
                    continue

                if ev.key in (pygame.K_LEFT, pygame.K_a):
                    shop_ui.move_selection(-1)
                    continue
                if ev.key in (pygame.K_RIGHT, pygame.K_d):
                    shop_ui.move_selection(+1)
                    continue
                if ev.key in (pygame.K_UP, pygame.K_DOWN):
                    # Compatibilidad con la navegación previa
                    delta = -1 if ev.key == pygame.K_UP else 1
                    shop_ui.move_selection(delta)
                    continue
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    bought, msg = shop_ui.try_buy(player)
                    # TODO: pintar msg en tu HUD si quieres
                    continue
                if ev.key == pygame.K_ESCAPE:
                    shop_ui.close()
                    continue

            if not shop_ui.active:
                continue

            if ev.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                if not hasattr(ev, "pos"):
                    continue
                mx = ev.pos[0] // max(1, screen_scale)
                my = ev.pos[1] // max(1, screen_scale)
                if ev.type == pygame.MOUSEMOTION:
                    shop_ui.update_hover((mx, my))
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    shop_ui.update_hover((mx, my))
                    bought, msg = shop_ui.handle_click((mx, my), player)
                    # TODO: usar msg en HUD si se desea

    def draw_overlay(self, surface, ui_font, player, shop_ui):
        """
        Dibuja elementos propios de la sala por encima del piso (p.ej. el mercader y tooltip).
        """
        if self.rune_chest:
            self._draw_rune_chest_overlay(surface, ui_font, player)

        if self.treasure:
            self._draw_treasure_overlay(surface, ui_font, player)

        if self.type == "shop" and self.shopkeeper is not None:
            player_rect = player.rect() if hasattr(player, "rect") else None
            self.shopkeeper.draw(surface, talk_active=shop_ui.active, player_rect=player_rect)
            if player_rect is not None and self.shopkeeper.can_interact(player_rect) and not shop_ui.active:
                tip = ui_font.render("E - Abrir tienda", True, (255, 255, 255))
                surface.blit(tip, (self.shopkeeper.rect.x - 12, self.shopkeeper.rect.y - 22))

    def _apply_corruption_to_enemy(self, enemy: Enemy) -> None:
        if getattr(enemy, "_corruption_buffed", False):
            return
        enemy.corrupted_visual = True
        enemy._corruption_buffed = True

        speed_multiplier = 1.35
        if hasattr(enemy, "chase_speed"):
            enemy.chase_speed *= speed_multiplier
        if hasattr(enemy, "wander_speed"):
            enemy.wander_speed *= speed_multiplier

        if hasattr(enemy, "detect_radius"):
            enemy.detect_radius *= 1.2
        if hasattr(enemy, "lose_radius"):
            enemy.lose_radius *= 1.2
        if hasattr(enemy, "reaction_delay"):
            enemy.reaction_delay *= 0.65

        try:
            enemy.hp = max(1, int(enemy.hp * 1.6))
        except Exception:
            pass

        if hasattr(enemy, "bullet_speed"):
            try:
                enemy.bullet_speed *= 1.2
            except Exception:
                pass

        cooldown_attrs = ("fire_cooldown", "attack_cooldown", "shoot_windup")
        for attr in cooldown_attrs:
            if hasattr(enemy, attr):
                value = getattr(enemy, attr)
                try:
                    setattr(enemy, attr, float(value) * 0.7)
                except Exception:
                    continue

        contact_damage = getattr(enemy, "contact_damage", 0)
        if contact_damage > 0:
            enemy.contact_damage = max(contact_damage + 1, int(round(contact_damage * 1.75)))
        else:
            enemy.contact_damage = max(1, contact_damage + 1)

        projectile_damage = getattr(enemy, "projectile_damage", 1.0)
        try:
            enemy.projectile_damage = max(1.0, projectile_damage * 1.75)
        except Exception:
            enemy.projectile_damage = 2.0

            
            


    # ------------------------------------------------------------------ #
    # Spawning de enemigos (una sola vez por cuarto)
    # ------------------------------------------------------------------ #
    def ensure_spawn(self, difficulty: int = 1) -> None:
        if self._spawn_done or self.bounds is None or self.no_spawn:
            return
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE

        encounter_factories = self._pick_encounter(difficulty)
        if not encounter_factories:
            self._spawn_done = True
            return
        used_tiles: set[tuple[int, int]] = set(self._obstacle_tiles)
        for factory in encounter_factories:
            # Intentar encontrar una baldosa libre para ubicar al enemigo
            for _ in range(12):
                tx = random.randint(rx + 1, rx + rw - 2)
                ty = random.randint(ry + 1, ry + rh - 2)
                if (tx, ty) in used_tiles:
                    continue
                used_tiles.add((tx, ty))
                px = tx * ts + ts // 2 - 6
                py = ty * ts + ts // 2 - 6
                enemy = factory(px, py)

                # Variar encuentros: algunos enemigos comienzan patrullando
                if random.random() < 0.35:
                    enemy._pick_wander()
                    enemy.state = enemy_mod.WANDER

                if self.is_corrupted:
                    self._apply_corruption_to_enemy(enemy)

                self.enemies.append(enemy)
                break

        # Escalado adicional: probabilidad de sumar un perseguidor extra
        extra_chance = min(0.1 * max(0, difficulty - 1), 0.5)
        if random.random() < extra_chance:
            for _ in range(12):
                tx = random.randint(rx + 1, rx + rw - 2)
                ty = random.randint(ry + 1, ry + rh - 2)
                if (tx, ty) in used_tiles:
                    continue
                used_tiles.add((tx, ty))
                px = tx * ts + ts // 2 - 6
                py = ty * ts + ts // 2 - 6
                bonus = FastChaserEnemy(px, py)
                bonus._pick_wander()
                bonus.state = enemy_mod.WANDER
                if self.is_corrupted:
                    self._apply_corruption_to_enemy(bonus)
                self.enemies.append(bonus)
                break

        if self.enemies and self.type != "boss":
            self.locked = True
            self.cleared = False
         
        self._spawn_done = True

    def _pick_encounter(self, difficulty: int) -> list[Type[Enemy]]:
        """Selecciona una combinación de enemigos según la dificultad."""
        tier = max(1, min(10, difficulty))
        for threshold, templates in ENCOUNTER_TABLE:
            if tier <= threshold:
                return random.choice(templates)
        return random.choice(ENCOUNTER_TABLE[-1][1]) if ENCOUNTER_TABLE else []


    # ------------------------------------------------------------------ #
    # Colisiones y triggers de puertas
    # ------------------------------------------------------------------ #
    def is_blocked(self, tx: int, ty: int) -> bool:
        """¿El tile (tx,ty) es sólido (pared)?"""
        if not (0 <= tx < CFG.MAP_W and 0 <= ty < CFG.MAP_H):
            return True
        if self.tiles[ty][tx] == CFG.WALL:
            return True
        if (tx, ty) in self._door_block_tiles:
            return True
        return (tx, ty) in self._obstacle_tiles or (tx, ty) in self._treasure_tiles or (tx, ty) in self._rune_chest_tiles
    
    def has_line_of_sight(self, x0_px: float, y0_px: float, x1_px: float, y1_px: float) -> bool:
        """
        Línea de visión en tiles usando DDA (Amanatides & Woo).
        Devuelve True si NO hay paredes (room.is_blocked) entre origen y destino.
        x*, y* están en píxeles del mundo.
        """
        ts = CFG.TILE_SIZE

        # Convertir a coords de tile
        x0 = int(x0_px // ts); y0 = int(y0_px // ts)
        x1 = int(x1_px // ts); y1 = int(y1_px // ts)

        # Si el destino está fuera del mapa, no hay LoS
        if not (0 <= x1 < CFG.MAP_W and 0 <= y1 < CFG.MAP_H):
            return False

        # Vector dirección en píxeles
        dx = x1_px - x0_px
        dy = y1_px - y0_px

        # Si origen y destino están en el mismo tile, hay LoS
        if x0 == x1 and y0 == y1:
            return True

        # Direcciones de paso en la grilla
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1

        # Evitar divisiones por cero
        inv_dx = 1.0 / dx if dx != 0 else float('inf')
        inv_dy = 1.0 / dy if dy != 0 else float('inf')

        # Fronteras del tile actual en píxeles
        tile_boundary_x = (x0 + (1 if step_x > 0 else 0)) * ts
        tile_boundary_y = (y0 + (1 if step_y > 0 else 0)) * ts

        # tMax = distancia paramétrica hasta la próxima pared vertical/horizontal
        t_max_x = (tile_boundary_x - x0_px) * inv_dx
        t_max_y = (tile_boundary_y - y0_px) * inv_dy

        # tDelta = distancia paramétrica entre paredes consecutivas
        t_delta_x = abs(ts * inv_dx)
        t_delta_y = abs(ts * inv_dy)

        tx, ty = x0, y0

        # Seguridad para evitar loops infinitos
        for _ in range(CFG.MAP_W + CFG.MAP_H + 4):
            # Si llegamos al tile destino, LoS limpio
            if tx == x1 and ty == y1:
                return True

            # Avanza hacia el siguiente cruce de grid
            if t_max_x < t_max_y:
                tx += step_x
                t_max_x += t_delta_x
            else:
                ty += step_y
                t_max_y += t_delta_y

            # Límites
            if not (0 <= tx < CFG.MAP_W and 0 <= ty < CFG.MAP_H):
                return False

            # Si el tile atravesado es sólido, se bloquea LoS
            if self.is_blocked(tx, ty):
                return False

        # Si por alguna razón salimos del bucle, considera bloqueado
        return False


    def _door_trigger_rects(self) -> dict[str, pygame.Rect]:
        """
        Triggers centrados con EXACTAMENTE el mismo ancho que la abertura tallada.
        """
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE

        left_px   = rx * ts
        right_px  = (rx + rw) * ts
        top_px    = ry * ts
        bottom_px = (ry + rh) * ts

        W = max(1, getattr(self, "_door_width_tiles", 2))
        side_height = max(1, getattr(self, "_door_side_height_tiles", W))
        opening_px = W * ts
        side_opening_px = side_height * ts
        thickness  = max(10, ts // 2)  # profundidad del trigger (hacia fuera/dentro del room)
        length_tiles = max(1, getattr(self, "_door_corridor_length_tiles", 3))
        corridor_px = length_tiles * ts

        offset_px = min(ts, max(0, corridor_px - thickness))

        # mismos centros en “medios tiles” que en carve_corridors
        center_tx2 = rx * 2 + rw
        center_ty2 = ry * 2 + rh
        left_tile  = (center_tx2 - W) // 2
        top_tile   = (center_ty2 - side_height) // 2

        # convertir a píxeles esas posiciones de tile
        left_open_px = left_tile * ts
        top_open_px  = top_tile * ts
        side_top_open_px = top_tile * ts
        cx_px = (left_px + right_px) // 2
        cy_px = (top_px + bottom_px) // 2

        rects: dict[str, pygame.Rect] = {}
        # Norte y Sur: horizontal, centrado
        if self.doors.get("N"):
            rects["N"] = pygame.Rect(
                left_open_px,
                top_px - ts - thickness - offset_px,
                opening_px,
                thickness,
            )
        if self.doors.get("S"):
            rects["S"] = pygame.Rect(
                left_open_px,
                bottom_px + ts + offset_px,
                opening_px,
                thickness,
            )
        # Este y Oeste: vertical, centrado
        if self.doors.get("E"):
            rects["E"] = pygame.Rect(
                right_px + ts + offset_px,
                side_top_open_px,
                thickness,
                side_opening_px,
            )
        if self.doors.get("W"):
            rects["W"] = pygame.Rect(
                left_px - ts - thickness - offset_px,
                side_top_open_px,
                thickness,
                side_opening_px,
            )
        return rects

    # Room.py — reemplaza check_exit por esta versión
    def check_exit(self, player):
        """Devuelve 'N'/'S'/'E'/'W' si el jugador toca el trigger de salida.
        Si la sala está bloqueada, no permite salir.
        Acepta player.rect() como método o player.rect como pygame.Rect.
        """
        # 1) si está bloqueada, nada que hacer
        if getattr(self, "locked", False):
            return None

        # 2) obtener rect del jugador de forma segura
        prect = None
        if hasattr(player, "rect"):
            r = player.rect
            prect = r() if callable(r) else r
        if not isinstance(prect, pygame.Rect):
            # Fallback: construir desde atributos x,y,w,h
            prect = pygame.Rect(int(getattr(player, "x", 0)),
                                int(getattr(player, "y", 0)),
                                int(getattr(player, "w", 12)),
                                int(getattr(player, "h", 12)))

        pr = prect.inflate(4, 4)  # pequeña tolerancia

        # 3) comprobar triggers
        triggers = self._door_trigger_rects()
        for direction, r in triggers.items():
            if pr.colliderect(r) and self.doors.get(direction, False):
                return direction
        return None

    
    def refresh_lock_state(self) -> None:
        """Si no hay enemigos, se marca cleared y se desbloquea."""
        if self._rune_wave_triggered and not self._rune_wave_cleared:
            if len(self.enemies) == 0:
                self._rune_wave_cleared = True
            else:
                self.locked = True
                return
        if self.type == "boss":
            if self.boss_defeated:
                self.locked = False
                if len(self.enemies) == 0:
                    self.cleared = True
            else:
                self.locked = True
            return
        if not self.cleared and len(self.enemies) == 0:
            self.cleared = True
            self.locked = False

    def _update_obstacle_animations(self, dt: float) -> None:
        if not self.obstacles:
            return
        for obstacle in self.obstacles:
            fps = float(obstacle.get("animation_fps", 0.0))
            speed_mult = float(obstacle.get("animation_speed", 1.0))
            fps *= speed_mult
            frames = _load_obstacle_frames(obstacle["size"], obstacle.get("variant"))
            frame_count = max(1, len(frames), int(obstacle.get("expected_frames", 1)))
            obstacle["expected_frames"] = frame_count

            frame_index = int(obstacle.get("frame_index", 0)) % frame_count
            if fps <= 0 or frame_count <= 1:
                obstacle["frame_index"] = frame_index
                obstacle["frame_timer"] = 0.0
                continue

            obstacle["frame_timer"] = float(obstacle.get("frame_timer", 0.0)) + dt * fps
            while obstacle["frame_timer"] >= 1.0:
                obstacle["frame_timer"] -= 1.0
                frame_index = (frame_index + 1) % frame_count
            obstacle["frame_index"] = frame_index

    def update(self, dt: float) -> None:
        self._update_obstacle_animations(dt)
        if not self.is_corrupted:
            return
        self._glitch_timer += dt
        if self._glitch_timer >= self._next_glitch_burst:
            self._glitch_timer = 0.0
            self._next_glitch_burst = random.uniform(0.08, 0.18)
            self._glitch_lines.clear()
            if self.bounds:
                rx, ry, rw, rh = self.bounds
                ts = CFG.TILE_SIZE
                base_rect = pygame.Rect(rx * ts, ry * ts, rw * ts, rh * ts)
                for _ in range(random.randint(6, 12)):
                    horizontal = random.random() < 0.5
                    length = random.randint(ts // 2, ts * 2)
                    thickness = random.randint(2, 4)
                    if horizontal:
                        x = random.randint(base_rect.left, base_rect.right - length)
                        y = random.randint(base_rect.top, base_rect.bottom - thickness)
                        rect = pygame.Rect(x, y, length, thickness)
                    else:
                        x = random.randint(base_rect.left, base_rect.right - thickness)
                        y = random.randint(base_rect.top, base_rect.bottom - length)
                        rect = pygame.Rect(x, y, thickness, length)
                    color = (180, 60, 255, 130)
                    self._glitch_lines.append((rect, color))
                self._glitch_offset = (random.randint(-2, 2), random.randint(-2, 2))




    # ------------------------------------------------------------------ #
    # Utilidades
    # ------------------------------------------------------------------ #
    def center_px(self) -> Tuple[int, int]:
        """Centro de la sala (en píxeles), útil para ubicar al jugador."""
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        cx = (rx + rw // 2) * ts + ts // 2
        cy = (ry + rh // 2) * ts + ts // 2
        return cx, cy

    def find_clear_drop_center(self) -> Tuple[int, int]:
        """Devuelve un punto céntrico libre de obstáculos para botines."""
        if not self.bounds:
            return self.center_px()

        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        cx_tile = rx + rw // 2
        cy_tile = ry + rh // 2

        candidates: list[tuple[float, float, int, int]] = []
        for ty in range(ry + 1, ry + rh - 1):
            for tx in range(rx + 1, rx + rw - 1):
                dx = tx - cx_tile
                dy = ty - cy_tile
                dist2 = dx * dx + dy * dy
                candidates.append((dist2, random.random(), tx, ty))

        candidates.sort(key=lambda entry: (entry[0], entry[1]))
        for _, _, tx, ty in candidates:
            if not self.is_blocked(tx, ty):
                drop_x = tx * ts + ts // 2
                drop_y = ty * ts + ts // 2
                return drop_x, drop_y

        return self.center_px()

    def _draw_doors(self, surf: pygame.Surface) -> None:
        openings = self._door_opening_rects()
        for direction, rect in openings.items():
            opened = not self.locked
            ts = CFG.TILE_SIZE
            sprite_size = rect.size
            if direction in ("E", "W"):
                sprite_size = (ts, ts * 3)

            sprite = _load_door_sprite(opened, direction in ("N", "S"), sprite_size, direction)
            if sprite is None:
                color = (90, 200, 120) if opened else (180, 40, 40)
                pygame.draw.rect(surf, color, rect)
                if not opened:
                    pygame.draw.rect(surf, (255, 90, 90), rect, 1)
                continue

            target_rect = sprite.get_rect(center=rect.center)
            if direction in ("E", "W"):
                target_rect.move_ip(0, -CFG.TILE_SIZE // 2)
            surf.blit(sprite, target_rect)

    # ------------------------------------------------------------------ #
    # Dibujo
    # ------------------------------------------------------------------ #
    def draw(self, surf: pygame.Surface, tileset) -> None:
        """
        Dibuja el room en `surf`. Si tu `Tileset` tiene un método específico,
        úsalo; si no, renderizo con rectángulos de colores.
        """
        ts = CFG.TILE_SIZE

        # Rellenar el suelo con un color plano para evitar repetir sprites.
        floor = CFG.COLOR_FLOOR
        for ty in range(CFG.MAP_H):
            row = self.tiles[ty]
            for tx in range(CFG.MAP_W):
                if row[tx] == CFG.FLOOR:
                    pygame.draw.rect(surf, floor, pygame.Rect(tx * ts, ty * ts, ts, ts))

        # Si tu tileset expone un método de dibujado por mapa, úsalo para las paredes.
        drew_with_tileset = False
        if hasattr(tileset, "draw_map"):
            drew_with_tileset = tileset.draw_map(surf, self.tiles)

        if not drew_with_tileset:
            # Fallback: colorear las paredes a mano, evitando el exterior.
            wall = CFG.COLOR_WALL
            for ty in range(CFG.MAP_H):
                row = self.tiles[ty]
                for tx in range(CFG.MAP_W):
                    if row[tx] != CFG.FLOOR and self._wall_adjacent_to_floor(tx, ty):
                        pygame.draw.rect(surf, wall, pygame.Rect(tx * ts, ty * ts, ts, ts))

        if self.is_corrupted and self.bounds is not None:
            rx, ry, rw, rh = self.bounds
            overlay_rect = pygame.Rect(rx * ts, ry * ts, rw * ts, rh * ts)
            overlay = pygame.Surface(overlay_rect.size, pygame.SRCALPHA)
            overlay.fill((90, 0, 120, 100))
            surf.blit(overlay, overlay_rect.topleft)

            if self._glitch_offset != (0, 0):
                ghost = pygame.Surface(overlay_rect.size, pygame.SRCALPHA)
                ghost.fill((70, 20, 110, 55))
                surf.blit(ghost, (overlay_rect.x + self._glitch_offset[0], overlay_rect.y + self._glitch_offset[1]))

            if self._glitch_lines:
                lines_surf = pygame.Surface(overlay_rect.size, pygame.SRCALPHA)
                for rect, color in self._glitch_lines:
                    local_rect = rect.move(-overlay_rect.x, -overlay_rect.y)
                    pygame.draw.rect(lines_surf, color, local_rect)
                surf.blit(lines_surf, overlay_rect.topleft)
                self._glitch_lines.clear()

        if self.is_start_room:
            graffiti = _load_start_graffiti_sprite()
            if graffiti is not None and self.bounds is not None:
                cx, cy = self.center_px()
                surf.blit(graffiti, graffiti.get_rect(center=(cx, cy)))

        if self.obstacles:
            for obstacle in self.obstacles:
                frames = _load_obstacle_frames(obstacle["size"], obstacle.get("variant"))
                frame_index = obstacle.get("frame_index", 0)
                if len(frames) == 0:
                    continue
                sprite = frames[min(frame_index % len(frames), len(frames) - 1)]
                variant_slug = (obstacle.get("variant") or "").lower().strip() or "default"
                offset = _OBSTACLE_SPRITE_OFFSETS.get((obstacle["size"], variant_slug), (0, 0))
                surf.blit(
                    sprite,
                    (
                        obstacle["rect"].x + offset[0],
                        obstacle["rect"].y + offset[1],
                    ),
                )

        if self.rune_chest:
            self._draw_rune_chest(surf)
        if self.treasure:
            self._draw_treasure(surf)

        self._draw_doors(surf)

    # ------------------------------------------------------------------ #
    # Cofre rúnico especial
    # ------------------------------------------------------------------ #
    def setup_rune_chest(self, loot_table: list[dict], prefer_bottom: bool = True) -> None:
        self.rune_chest = None
        self._rune_chest_tiles.clear()
        self._rune_wave_triggered = False
        self._rune_wave_cleared = False
        self.rune_message = ""
        self.rune_message_until = 0

        if not self.bounds:
            self.build_centered(9, 9)
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        cx = (rx + rw // 2) * ts + ts // 2
        if prefer_bottom:
            cy = (ry + rh - 2) * ts + ts // 2
        else:
            cy = (ry + rh // 2) * ts + ts // 2

        width, height = self._treasure_dimensions((30, 22))
        sprite_rect = pygame.Rect(cx - width // 2, cy - height // 2, width, height)
        self.rune_chest = {
            "rect": sprite_rect,
            "hitbox": _treasure_hitbox_from_sprite_rect(sprite_rect),
            "collision": _treasure_collision_from_sprite_rect(sprite_rect),
            "opened": False,
            "loot_table": loot_table,
        }
        self._refresh_rune_chest_tiles()

    def _refresh_rune_chest_tiles(self) -> None:
        self._rune_chest_tiles.clear()
        if not self.rune_chest:
            return
        rect: pygame.Rect | None = self.rune_chest.get("collision")
        if rect is None:
            return
        ts = CFG.TILE_SIZE
        x0 = rect.left // ts
        y0 = rect.top // ts
        x1 = (rect.right - 1) // ts
        y1 = (rect.bottom - 1) // ts
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if 0 <= tx < CFG.MAP_W and 0 <= ty < CFG.MAP_H:
                    self._rune_chest_tiles.add((tx, ty))

    def _handle_rune_chest_events(self, events, player) -> None:
        if not self.rune_chest:
            return

        hitbox: pygame.Rect = self.rune_chest.get("hitbox", self.rune_chest["rect"])
        player_rect = self._player_rect(player)
        interact_rect = hitbox.inflate(30, 30)
        can_interact = interact_rect.colliderect(player_rect)

        if self.rune_chest.get("opened", False):
            return

        for ev in events:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                if not can_interact:
                    continue
                if not self._rune_wave_triggered:
                    self._trigger_rune_wave()
                    break
                if self._can_open_rune_chest():
                    self._open_rune_chest(player)
                else:
                    self._show_rune_message("Derrota a los guardianes", duration=2200)
                break

    def _trigger_rune_wave(self) -> None:
        if self._rune_wave_triggered:
            return
        self._rune_wave_triggered = True
        self._rune_wave_cleared = False
        self.locked = True
        self._spawn_rune_guardian_wave()
        self._show_rune_message("¡Los guardianes rúnicos atacan!", duration=2400)

    def _spawn_rune_guardian_wave(self) -> None:
        if self.bounds is None:
            self.build_centered(9, 9)
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        used_tiles: set[tuple[int, int]] = set(self._obstacle_tiles)
        used_tiles.update(self._treasure_tiles)
        used_tiles.update(self._rune_chest_tiles)

        guardian_pool: list[Type[Enemy]] = [TankEnemy, ShooterEnemy, FastChaserEnemy, TankEnemy, ShooterEnemy]
        wave_size = max(4, min(8, (rw + rh) // 2))

        for _ in range(wave_size):
            random.shuffle(guardian_pool)
            factory = guardian_pool[0]
            for _ in range(14):
                tx = random.randint(rx + 1, rx + rw - 2)
                ty = random.randint(ry + 1, ry + rh - 2)
                if (tx, ty) in used_tiles:
                    continue
                used_tiles.add((tx, ty))
                px = tx * ts + ts // 2 - 6
                py = ty * ts + ts // 2 - 6
                enemy = factory(px, py)
                if random.random() < 0.35 and hasattr(enemy, "_pick_wander"):
                    enemy._pick_wander()
                    enemy.state = getattr(enemy_mod, "WANDER", enemy.state)
                if self.is_corrupted:
                    self._apply_corruption_to_enemy(enemy)
                self.enemies.append(enemy)
                break

    def _can_open_rune_chest(self) -> bool:
        if not self._rune_wave_triggered:
            return False
        if not self._rune_wave_cleared:
            if len(self.enemies) == 0:
                self._rune_wave_cleared = True
            else:
                return False
        return len(self.enemies) == 0

    def _open_rune_chest(self, player) -> None:
        if not self.rune_chest or self.rune_chest.get("opened", False):
            return
        reward = self._pick_rune_reward(player)
        message = "El cofre está vacío..."
        if reward:
            applied = self._apply_treasure_reward(player, reward)
            name = reward.get("name", "Recompensa misteriosa")
            message = f"Obtuviste: {name}" if applied else f"Encontraste: {name}"
        self.rune_chest["opened"] = True
        self._show_rune_message(message, duration=4400)
        # Reproducir sonido de cofre
        if self._chest_sound:
            self._chest_sound.play()

    def _pick_rune_reward(self, player) -> dict | None:
        if not self.rune_chest:
            return None
        loot_table: list[dict] = self.rune_chest.get("loot_table", [])
        weighted: list[tuple[dict, float]] = []
        for entry in loot_table:
            weight = float(entry.get("weight", 1.0))
            if weight <= 0:
                continue
            weighted.append((entry, weight))
        if not weighted:
            return None
        population = [entry for entry, _ in weighted]
        weights = [weight for _, weight in weighted]
        return random.choices(population, weights=weights, k=1)[0]

    def _show_rune_message(self, message: str, *, duration: int = 3200) -> None:
        if self._notification_callback:
            self._notification_callback(message)
            self.rune_message = ""
            self.rune_message_until = 0
            return

        self.rune_message = message
        self.rune_message_until = pygame.time.get_ticks() + max(500, duration)

    def _draw_rune_chest(self, surface: pygame.Surface) -> None:
        if not self.rune_chest:
            return
        rect: pygame.Rect = self.rune_chest["rect"]
        hitbox: pygame.Rect = self.rune_chest.get("hitbox", rect)
        opened = self.rune_chest.get("opened", False)

        sprite = _load_rune_chest_sprite(rect.size, opened)

        if sprite is not None:
            surface.blit(sprite, rect)
        else:
            body_color = (90, 62, 140) if not opened else (58, 48, 92)
            lid_color = (130, 92, 186) if not opened else (92, 74, 134)
            band_color = (196, 176, 240) if not opened else (150, 138, 196)

            pygame.draw.rect(surface, body_color, rect)
            lid_height = max(6, rect.height // 3)
            lid_rect = pygame.Rect(rect.x, rect.y, rect.width, lid_height)
            pygame.draw.rect(surface, lid_color, lid_rect)
            pygame.draw.rect(surface, band_color, pygame.Rect(rect.centerx - 3, rect.y, 6, rect.height))
            pygame.draw.rect(surface, (22, 14, 44), rect, 2)

        if getattr(CFG, "DEBUG_DRAW_DOOR_TRIGGERS", False):
            pygame.draw.rect(surface, (255, 0, 255), hitbox, 1)

    def _draw_rune_chest_overlay(self, surface, ui_font, player) -> None:
        rect = self.rune_chest["rect"]
        hitbox = self.rune_chest.get("hitbox", rect)
        player_rect = self._player_rect(player)
        near = hitbox.inflate(36, 36).colliderect(player_rect)

        if not self.rune_chest.get("opened", False) and near:
            if not self._rune_wave_triggered:
                tip_text = "E - Examinar cofre rúnico"
            elif self._can_open_rune_chest():
                tip_text = "E - Abrir cofre rúnico"
            else:
                tip_text = "Guardianes activos"
            tip = ui_font.render(tip_text, True, (235, 220, 255))
            surface.blit(tip, (rect.centerx - tip.get_width() // 2, rect.y - 24))

        now = pygame.time.get_ticks()
        if self.rune_message and now <= self.rune_message_until:
            msg = ui_font.render(self.rune_message, True, (210, 190, 255))
            surface.blit(msg, (rect.centerx - msg.get_width() // 2, rect.bottom + 8))
        elif now > self.rune_message_until:
            self.rune_message = ""

    # ------------------------------------------------------------------ #
    # Tesoro
    # ------------------------------------------------------------------ #
    def setup_treasure_room(self, loot_table: list[dict]) -> None:
        self.type = "treasure"
        self.is_corrupted = False
        self.safe = False
        self.no_spawn = False
        self.no_combat = False
        self.locked = False
        self.treasure_message = ""
        self.treasure_message_until = 0
        self.clear_obstacles()
        self._treasure_tiles.clear()

        if not self.bounds:
            self.build_centered(9, 9)
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        cx = (rx + rw // 2) * ts + ts // 2
        cy = (ry + rh // 2) * ts + ts // 2

        width, height = self._treasure_dimensions((28, 20))
        sprite_rect = pygame.Rect(cx - width // 2, cy - height // 2, width, height)
        self.treasure = {
            "rect": sprite_rect,
            "hitbox": _treasure_hitbox_from_sprite_rect(sprite_rect),
            "collision": _treasure_collision_from_sprite_rect(sprite_rect),
            "opened": False,
            "loot_table": loot_table,
        }
        self._refresh_treasure_tiles()

    def spawn_boss_reward(self) -> None:
        loot_table = list(self.boss_loot_table or [
            {"name": "Reserva de emergencia (+80)", "type": "gold", "amount": 80, "weight": 1}
        ])
        if not self.bounds:
            self.build_centered(9, 9)
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        cx = (rx + rw // 2) * ts + ts // 2
        cy = (ry + rh // 2) * ts + ts // 2
        width, height = self._treasure_dimensions((32, 24))
        sprite_rect = pygame.Rect(cx - width // 2, cy - height // 2, width, height)
        self.treasure = {
            "rect": sprite_rect,
            "hitbox": _treasure_hitbox_from_sprite_rect(sprite_rect),
            "collision": _treasure_collision_from_sprite_rect(sprite_rect),
            "opened": False,
            "loot_table": loot_table,
        }
        self.treasure_message = ""
        self.treasure_message_until = 0
        self._refresh_treasure_tiles()

    def _treasure_dimensions(self, base_size: tuple[int, int]) -> tuple[int, int]:
        """Calcula el tamaño del cofre aplicando la escala configurada."""

        scale = max(0.1, float(getattr(CFG, "TREASURE_SPRITE_SCALE", 1.0)))

        cfg_size = getattr(CFG, "TREASURE_SIZE", base_size)
        sprite_size: tuple[int, int] | None = None
        raw_sprite = _load_raw_treasure_sprite()
        if raw_sprite is not None:
            sprite_size = raw_sprite.get_size()

        try:
            bw, bh = int(cfg_size[0]), int(cfg_size[1])
        except (TypeError, ValueError, IndexError):
            if sprite_size:
                bw, bh = sprite_size
            else:
                bw, bh = base_size

        if bw <= 0 or bh <= 0:
            if sprite_size:
                bw, bh = sprite_size
            else:
                bw, bh = base_size

        width = max(4, int(round(bw * scale)))
        height = max(4, int(round(bh * scale)))
        return width, height

    def _refresh_treasure_tiles(self) -> None:
        """Actualiza los tiles sólidos ocupados por el cofre."""

        self._treasure_tiles.clear()
        if not self.treasure:
            return

        rect: pygame.Rect | None = self.treasure.get("collision")
        if rect is None:
            return
        ts = CFG.TILE_SIZE
        x0 = rect.left // ts
        y0 = rect.top // ts
        x1 = (rect.right - 1) // ts
        y1 = (rect.bottom - 1) // ts

        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if 0 <= tx < CFG.MAP_W and 0 <= ty < CFG.MAP_H:
                    self._treasure_tiles.add((tx, ty))

    def _handle_treasure_events(self, events, player) -> None:
        if not self.treasure:
            return

        hitbox: pygame.Rect = self.treasure.get("hitbox", self.treasure["rect"])
        player_rect = self._player_rect(player)
        interact_rect = hitbox.inflate(30, 30)
        can_interact = interact_rect.colliderect(player_rect)

        if self.treasure.get("opened", False):
            return

        for ev in events:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                if can_interact:
                    self._open_treasure_chest(player)
                    break

    def _open_treasure_chest(self, player) -> None:
        if not self.treasure or self.treasure.get("opened", False):
            return

        reward = self._pick_treasure_reward(player)
        message = "El cofre está vacío..."
        if reward:
            applied = self._apply_treasure_reward(player, reward)
            name = reward.get("name", "Recompensa misteriosa")
            message = f"Obtuviste: {name}" if applied else f"Encontraste: {name}"

        self.treasure["opened"] = True
        # Reproducir sonido de cofre
        if self._chest_sound:
            self._chest_sound.play()
        
        if self._notification_callback:
            self._notification_callback(message)
            self.treasure_message = ""
            self.treasure_message_until = 0
        else:
            self.treasure_message = message
            self.treasure_message_until = pygame.time.get_ticks() + 4200

    def _pick_treasure_reward(self, player) -> dict | None:
        if not self.treasure:
            return None
        loot_table: list[dict] = self.treasure.get("loot_table", [])
        weighted: list[tuple[dict, float]] = []
        for entry in loot_table:
            weight = float(entry.get("weight", 1.0))
            if weight <= 0:
                continue
            weighted.append((entry, weight))
        if not weighted:
            return None

        attempts = max(1, len(weighted) * 2)
        has_weapon = getattr(player, "has_weapon", None)
        population = [entry for entry, _ in weighted]
        weights = [weight for _, weight in weighted]
        for _ in range(attempts):
            candidate = random.choices(population, weights=weights, k=1)[0]
            if candidate.get("type") == "weapon" and callable(has_weapon):
                if has_weapon(candidate.get("id", "")):
                    continue
            return candidate

        for entry in population:
            if entry.get("type") == "gold":
                return entry
        return population[0]

    def _apply_treasure_reward(self, player, reward: dict) -> bool:
        return apply_reward_entry(player, reward)


    def _draw_treasure(self, surface: pygame.Surface) -> None:
        if not self.treasure:
            return
        rect: pygame.Rect = self.treasure["rect"]
        hitbox: pygame.Rect = self.treasure.get("hitbox", rect)
        opened = self.treasure.get("opened", False)

        sprite = _load_treasure_sprite(rect.size, opened)
        if sprite is not None:
            surface.blit(sprite, rect.topleft)
            return

        body_color = (176, 124, 56) if not opened else (110, 96, 96)
        lid_color = (214, 168, 96) if not opened else (140, 128, 128)
        band_color = (235, 208, 128) if not opened else (180, 172, 172)

        pygame.draw.rect(surface, body_color, rect)
        lid_height = max(6, rect.height // 3)
        lid_rect = pygame.Rect(rect.x, rect.y, rect.width, lid_height)
        pygame.draw.rect(surface, lid_color, lid_rect)
        pygame.draw.rect(surface, band_color, pygame.Rect(rect.centerx - 3, rect.y, 6, rect.height))
        pygame.draw.rect(surface, (20, 12, 8), rect, 2)

        # Hitbox visible para depuración: se dibuja sólo si las banderas debug lo permiten.
        if getattr(CFG, "DEBUG_DRAW_DOOR_TRIGGERS", False):
            pygame.draw.rect(surface, (255, 0, 0), hitbox, 1)

    def _draw_treasure_overlay(self, surface, ui_font, player) -> None:
        rect = self.treasure["rect"]
        hitbox = self.treasure.get("hitbox", rect)
        player_rect = self._player_rect(player)
        near = hitbox.inflate(36, 36).colliderect(player_rect)

        if not self.treasure.get("opened", False) and near:
            tip = ui_font.render("E - Abrir cofre", True, (255, 255, 255))
            surface.blit(tip, (rect.centerx - tip.get_width() // 2, rect.y - 22))

        now = pygame.time.get_ticks()
        if self.treasure_message and now <= self.treasure_message_until:
            msg = ui_font.render(self.treasure_message, True, (255, 230, 140))
            surface.blit(msg, (rect.centerx - msg.get_width() // 2, rect.bottom + 8))
        elif now > self.treasure_message_until:
            self.treasure_message = ""

    def _player_rect(self, player) -> pygame.Rect:
        if hasattr(player, "rect"):
            prect = player.rect
            if callable(prect):
                prect = prect()
            if isinstance(prect, pygame.Rect):
                return prect
        return pygame.Rect(int(getattr(player, "x", 0)),
                            int(getattr(player, "y", 0)),
                            int(getattr(player, "w", 12)),
                            int(getattr(player, "h", 12)))

    def _wall_adjacent_to_floor(self, tx: int, ty: int) -> bool:
        if self.tiles[ty][tx] == CFG.FLOOR:
            return False

        height = len(self.tiles)
        for ny in range(ty - 1, ty + 2):
            if not (0 <= ny < height):
                continue
            row = self.tiles[ny]
            for nx in range(tx - 1, tx + 2):
                if nx == tx and ny == ty:
                    continue
                if 0 <= nx < len(row) and row[nx] == CFG.FLOOR:
                    return True
        return False
        
