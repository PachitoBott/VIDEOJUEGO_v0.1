import pygame
from typing import Tuple, Dict, Set
from Config import CFG
from Room import Room

class Dungeon:
    """
    Grid de rooms (3x3 por defecto). Maneja room actual, transiciones y rooms exploradas.
    """
    def __init__(self, grid_w: int = 3, grid_h: int = 3) -> None:
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.rooms: Dict[Tuple[int, int], Room] = {}
        self.explored = set()
        self.i = grid_w // 2
        self.j = grid_h // 2
        self._ensure_room(self.i, self.j)
        self.explored.add((self.i, self.j))

    @property
    def current_room(self) -> Room:
        return self.rooms[(self.i, self.j)]

    def can_move(self, direction: str) -> bool:
        di, dj = self._dir_to_delta(direction)
        ni, nj = self.i + di, self.j + dj
        return 0 <= ni < self.grid_w and 0 <= nj < self.grid_h

    def move(self, direction: str) -> None:
        di, dj = self._dir_to_delta(direction)
        self.i += di
        self.j += dj
        self._ensure_room(self.i, self.j)
        self.explored.add((self.i, self.j))

    def entry_position(self, came_from: str, pw: int, ph: int) -> Tuple[float, float]:
        room = self.current_room
        rx, ry, rw, rh = room.bounds
        ts = CFG.TILE_SIZE
        cx_px = (rx + rw // 2) * ts
        cy_px = (ry + rh // 2) * ts

        margin = 6  # píxeles hacia adentro

        if came_from == "N":  # Venías desde el sur hacia el norte
            x = cx_px - pw // 2
            y = (ry + rh) * ts - ph - 2 - margin
        elif came_from == "S":
            x = cx_px - pw // 2
            y = ry * ts + 2 + margin
        elif came_from == "E":
            x = rx * ts + 2 + margin
            y = cy_px - ph // 2
        else:  # "W"
            x = (rx + rw) * ts - pw - 2 - margin
            y = cy_px - ph // 2
        return float(x), float(y)


    def _ensure_room(self, i: int, j: int) -> None:
        if (i, j) in self.rooms:
            return
        room = Room()
        room.build_centered(CFG.ROOM_W, CFG.ROOM_H)
        # Puertas según vecinos válidos
        room.doors["N"] = (j - 1) >= 0
        room.doors["S"] = (j + 1) < self.grid_h
        room.doors["W"] = (i - 1) >= 0
        room.doors["E"] = (i + 1) < self.grid_w
        # Corredores cortos visuales
        room.carve_corridors(width_tiles=2, length_tiles=3)
        self.rooms[(i, j)] = room

    def _dir_to_delta(self, d: str) -> Tuple[int, int]:
        if d == "N": return (0, -1)
        if d == "S": return (0, 1)
        if d == "E": return (1, 0)
        if d == "W": return (-1, 0)
        return (0, 0)
