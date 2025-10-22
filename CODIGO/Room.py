import pygame
from typing import Dict, Tuple, Optional, List
from Config import CFG
from Enemy import Enemy
# arriba de Room.py
import random
from Enemy import Enemy, FastChaserEnemy, TankEnemy, ShooterEnemy
import Enemy as enemy_mod  # <- para usar enemy_mod.WANDER


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
        self.bounds: Optional[Tuple[int, int, int, int]] = None  # (rx, ry, rw, rh) en tiles
        self.doors: Dict[str, bool] = {"N": False, "S": False, "E": False, "W": False}

        # contenido dinámico
        self.enemies: List[Enemy] = []
        self._spawn_done: bool = False
        self._door_width_tiles = 2

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
    # Corredores cortos (visuales) hacia las puertas
    # ------------------------------------------------------------------ #
    def carve_corridors(self, width_tiles: int = 2, length_tiles: int = 3) -> None:
        """
        Talla la abertura/“corredor” exactamente centrado en tiles.
        Guarda el ancho para que _door_trigger_rects use el mismo valor.
        """
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        self._door_width_tiles = max(1, int(width_tiles))

        def carve_rect(x: int, y: int, w: int, h: int) -> None:
            for yy in range(y, y + h):
                if 0 <= yy < CFG.MAP_H:
                    for xx in range(x, x + w):
                        if 0 <= xx < CFG.MAP_W:
                            self.tiles[yy][xx] = 0

        W = self._door_width_tiles
        # centro “en medios tiles” (evita perder la mitad cuando rw es par)
        center_tx2 = rx * 2 + rw   # = 2*(rx + rw/2)
        center_ty2 = ry * 2 + rh

        # izquierda superior del hueco (en tiles), usando la misma aritmética para N/S y E/W
        left_tile   = (center_tx2 - W) // 2  # N y S
        top_tile    = (center_ty2 - W) // 2  # E y W

        # Norte (arriba)
        if self.doors.get("N"):
            carve_rect(left_tile, ry - length_tiles, W, length_tiles)
        # Sur (abajo)
        if self.doors.get("S"):
            carve_rect(left_tile, ry + rh, W, length_tiles)
        # Este (derecha)
        if self.doors.get("E"):
            carve_rect(rx + rw, top_tile, length_tiles, W)
        # Oeste (izquierda)
        if self.doors.get("W"):
            carve_rect(rx - length_tiles, top_tile, length_tiles, W)


    # ------------------------------------------------------------------ #
    # Spawning de enemigos (una sola vez por cuarto)
    # ------------------------------------------------------------------ #
    def ensure_spawn(self, difficulty: int = 1) -> None:
        if self._spawn_done or self.bounds is None:
            return
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE

        n = max(1, min(6, 1 + difficulty))
        for _ in range(n):
            tx = random.randint(rx + 1, rx + rw - 2)
            ty = random.randint(ry + 1, ry + rh - 2)
            px = tx * ts + ts // 2 - 6
            py = ty * ts + ts // 2 - 6

            # ---- elige tipo según dificultad/azar ----
            r = random.random()
            if r < 0.5:
                e = Enemy(px, py)                 # estándar
            elif r < 0.75:
                e = FastChaserEnemy(px, py)       # rápido
            elif r < 0.9:
                e = TankEnemy(px, py)             # tanque
            else:
               e = Enemy(px, py)  # o FastChaserEnemy / TankEnemy / ShooterEnemy según prob.
            # algunos empiezan deambulando
            if random.random() < 0.4:
                e._pick_wander()
                e.state = enemy_mod.WANDER    # <<< evita NameError
            self.enemies.append(e)

            self.enemies.append(e)

        self._spawn_done = True

    # ------------------------------------------------------------------ #
    # Colisiones y triggers de puertas
    # ------------------------------------------------------------------ #
    def is_blocked(self, tx: int, ty: int) -> bool:
        """¿El tile (tx,ty) es sólido (pared)?"""
        if not (0 <= tx < CFG.MAP_W and 0 <= ty < CFG.MAP_H):
            return True
        return self.tiles[ty][tx] == CFG.WALL
    
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
        opening_px = W * ts
        thickness  = max(10, ts // 2)  # profundidad del trigger (hacia fuera/dentro del room)

        # mismos centros en “medios tiles” que en carve_corridors
        center_tx2 = rx * 2 + rw
        center_ty2 = ry * 2 + rh
        left_tile  = (center_tx2 - W) // 2
        top_tile   = (center_ty2 - W) // 2

        # convertir a píxeles esas posiciones de tile
        left_open_px = left_tile * ts
        top_open_px  = top_tile * ts
        cx_px = (left_px + right_px) // 2
        cy_px = (top_px + bottom_px) // 2

        rects: dict[str, pygame.Rect] = {}
        # Norte y Sur: horizontal, centrado
        if self.doors.get("N"):
            rects["N"] = pygame.Rect(left_open_px, top_px - thickness // 2, opening_px, thickness)
        if self.doors.get("S"):
            rects["S"] = pygame.Rect(left_open_px, bottom_px - thickness // 2, opening_px, thickness)
        # Este y Oeste: vertical, centrado
        if self.doors.get("E"):
            rects["E"] = pygame.Rect(right_px - thickness // 2, top_open_px, thickness, opening_px)
        if self.doors.get("W"):
            rects["W"] = pygame.Rect(left_px - thickness // 2, top_open_px, thickness, opening_px)
        return rects

    def check_exit(self, player_rect: pygame.Rect) -> Optional[str]:
        """
        Devuelve 'N','S','E','W' si el jugador toca una puerta; en caso contrario None.
        """
        # Inflamos un poco el rect del jugador para evitar errores por 1px
        pr = player_rect.inflate(4, 4)
        for d, r in self._door_trigger_rects().items():
            if pr.colliderect(r):
                return d
        return None



    # ------------------------------------------------------------------ #
    # Utilidades
    # ------------------------------------------------------------------ #
    def center_px(self) -> Tuple[int, int]:
        """Centro de la sala (en píxeles), útil para ubicar al jugador."""
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        cx = (rx + rw // 2) * ts
        cy = (ry + rh // 2) * ts
        return cx, cy

    # ------------------------------------------------------------------ #
    # Dibujo
    # ------------------------------------------------------------------ #
    def draw(self, surf: pygame.Surface, tileset) -> None:
        """
        Dibuja el room en `surf`. Si tu `Tileset` tiene un método específico,
        úsalo; si no, renderizo con rectángulos de colores.
        """
        ts = CFG.TILE_SIZE
        # Si tu tileset expone un método de dibujado por mapa, úsalo:
        if hasattr(tileset, "draw_map"):
            tileset.draw_map(surf, self.tiles)  # <- adapta si tu Tileset usa otra firma
            return

        # Fallback: pintar a color
        wall = (60, 60, 70)
        floor = (110, 85, 70)
        for ty in range(CFG.MAP_H):
            for tx in range(CFG.MAP_W):
                color = floor if self.tiles[ty][tx] == 0 else wall
                pygame.draw.rect(surf, color, pygame.Rect(tx*ts, ty*ts, ts, ts))
