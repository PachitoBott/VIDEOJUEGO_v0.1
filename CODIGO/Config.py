from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple


@dataclass(frozen=True)
class StartMenuButton:
    """Representa un botón configurable dentro del menú de inicio."""

    action: str
    label: str


@dataclass(frozen=True)
class StartMenuConfig:
    """Opciones editables para personalizar el menú de inicio."""

    title: str = "Roguelike"
    subtitle: Optional[str] = "Genera tu aventura"
    background_image: Optional[str] = None
    logo_image: Optional[str] = None
    buttons: Tuple[StartMenuButton, ...] = (
        StartMenuButton("play", "Jugar"),
        StartMenuButton("credits", "Créditos"),
        StartMenuButton("controls", "Controles"),
    )
    sections: Mapping[str, Tuple[str, ...]] = field(
        default_factory=lambda: {
            "credits": (
                "Créditos",
                "",
                "Programación: Tu Nombre",
                "Arte: Tu Equipo",
                "Sonido: Recursos libres / CC",
            ),
            "controls": (
                "Controles",
                "",
                "WASD o Flechas — Moverse",
                "Mouse — Apuntar y disparar",
                "Espacio — Rodar / Acción",
                "M — Reiniciar con la misma seed",
                "N — Generar una nueva seed aleatoria",
            ),
        }
    )
    seed_placeholder: str = "Seed aleatoria"


@dataclass(frozen=True)
class Config:
    TILE_SIZE: int = 32
    SPRITE_SIZE: int = 32
    MAP_W: int = 30
    MAP_H: int = 20
    SCREEN_SCALE: int = 2
    FPS: int = 120

    PLAYER_START_LIVES: int = 10
    
    ROOM_W_MIN: int = 12
    ROOM_W_MAX: int = 18
    ROOM_H_MIN: int = 9
    ROOM_H_MAX: int = 13

    TILESET_PATH: Optional[str] = "assets/tileset.png"
    PLAYER_SPRITES_PATH: Optional[str] = "assets/player"
    PLAYER_SPRITE_PREFIX: str = "player"
    COLOR_BG: Tuple[int,int,int] = (8, 12, 28)
    COLOR_FLOOR: Tuple[int,int,int] = (20, 26, 46)
    COLOR_WALL: Tuple[int,int,int] = (118, 121, 146)
    COLOR_PLAYER: Tuple[int,int,int] = (240, 220, 120)

    DEBUG_DRAW_DOOR_TRIGGERS: bool = False

    START_MENU: StartMenuConfig = StartMenuConfig()

    FLOOR: int = 0
    WALL: int = 1  # pared genérica (fallback)
    WALL_TOP: int = 2
    WALL_BOTTOM: int = 3
    WALL_LEFT: int = 4
    WALL_RIGHT: int = 5
    WALL_CORNER_NW: int = 6
    WALL_CORNER_NE: int = 7
    WALL_CORNER_SW: int = 8
    WALL_CORNER_SE: int = 9

    @property
    def SCREEN_W(self) -> int: return self.MAP_W * self.TILE_SIZE
    @property
    def SCREEN_H(self) -> int: return self.MAP_H * self.TILE_SIZE

    def dungeon_params(self) -> dict:
        """Parámetros por defecto para generar una dungeon."""
        return {
            "grid_w": 10,
            "grid_h": 10,
            "main_len": 12,
            "branch_chance": 0.45,
            "branch_min": 2,
            "branch_max": 4,
        }

CFG = Config()
