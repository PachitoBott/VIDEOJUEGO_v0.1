from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass(frozen=True)
class Config:
    TILE_SIZE: int = 16
    MAP_W: int = 60
    MAP_H: int = 40
    SCREEN_SCALE: int = 2
    FPS: int = 120
    
    ROOM_W_MIN: int = 24
    ROOM_W_MAX: int = 36
    ROOM_H_MIN: int = 18
    ROOM_H_MAX: int = 26

    TILESET_PATH: Optional[str] = None  # ej: "assets/tileset.png"

    COLOR_BG: Tuple[int,int,int] = (10, 10, 14)
    COLOR_FLOOR: Tuple[int,int,int] = (36, 36, 46)
    COLOR_WALL: Tuple[int,int,int] = (110, 113, 128)
    COLOR_PLAYER: Tuple[int,int,int] = (240, 220, 120)

    DEBUG_DRAW_DOOR_TRIGGERS: bool = False

    FLOOR: int = 0
    WALL: int = 1

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
