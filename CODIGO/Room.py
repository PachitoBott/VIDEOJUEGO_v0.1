import pygame
from typing import Dict, Tuple, Optional, List, Type
from Config import CFG
# arriba de Room.py
import random
from Enemy import Enemy, FastChaserEnemy, TankEnemy, ShooterEnemy, BasicEnemy
import Enemy as enemy_mod  # <- para usar enemy_mod.WANDER

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
        self._spawn_done: bool = False
        self._door_width_tiles = 2

        # 🔒 estado de puertas
        self.locked: bool = False
        self.cleared: bool = False
        
        self.type = getattr(self, "type", "normal")  # "normal" / "shop"
        self.bounds = getattr(self, "bounds", (0, 0, 9, 9))  # (rx,ry,rw,rh) tiles
        self.doors = getattr(self, "doors", {"N":False,"S":False,"E":False,"W":False})

        # --- NUEVO ---
        self.safe = False
        self.no_spawn = False
        self.no_combat = False
        self._populated_once = False
        self.shopkeeper = None


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
        opening_px = W * ts

        # mismos centros que usaste para tallar
        center_tx2 = rx * 2 + rw
        center_ty2 = ry * 2 + rh
        left_tile  = (center_tx2 - W) // 2
        top_tile   = (center_ty2 - W) // 2

        left_open_px = left_tile * ts
        top_open_px  = top_tile * ts

        rects: dict[str, pygame.Rect] = {}
        if self.doors.get("N"):
            rects["N"] = pygame.Rect(left_open_px, top_px, opening_px, ts)         # una “faja” de 1 tile
        if self.doors.get("S"):
            rects["S"] = pygame.Rect(left_open_px, bottom_px - ts, opening_px, ts)
        if self.doors.get("E"):
            rects["E"] = pygame.Rect(right_px - ts, top_open_px, ts, opening_px)
        if self.doors.get("W"):
            rects["W"] = pygame.Rect(left_px, top_open_px, ts, opening_px)
        return rects
    
    
    # ---------- TIENDA ----------
    def _ensure_shopkeeper(self, cfg, ShopkeeperCls):
        if self.shopkeeper is not None:
            return
        rx, ry, rw, rh = self.bounds
        ts = cfg.TILE_SIZE
        cx = (rx + rw // 2) * ts
        cy = (ry + rh // 2) * ts
        self.shopkeeper = ShopkeeperCls((cx, cy))

    def on_enter(self, player, cfg, ShopkeeperCls=None):
        """
        Llamado cuando entras a la sala.
        - Marca flags si es 'shop'
        - Evita spawn de enemigos
        - Crea Shopkeeper si aplica
        """
        if self.type == "shop":
            self.safe = True
            self.no_spawn = True
            self.no_combat = True
            self.locked = False
            if ShopkeeperCls:
                self._ensure_shopkeeper(cfg, ShopkeeperCls)
        else:
            # Poblar enemigos SOLO una vez (si no es shop)
            if not self._populated_once and not self.no_spawn:
                # TODO: aquí tu lógica real de spawn por sala
                # e.g., self.enemies = spawn_enemies_for(self)
                pass
            self._populated_once = True

    def on_exit(self):
        """Llamado cuando sales de la sala."""
        # Nada especial por defecto. Podrías pausar IA/ambiente si quieres.
        pass

    def handle_events(self, events, player, shop_ui, world_surface, ui_font, screen_scale=1):
        """
        Maneja interacción con la tienda dentro de la sala (si es shop).
        No lee pygame.event.get() aquí; recibe la lista de events desde Game.
        """
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
                        shop_ui.open(world_surface.get_width()//2, world_surface.get_height()//2)
                    else:
                        shop_ui.close()
                    continue

                if not shop_ui.active:
                    continue

                if ev.key == pygame.K_UP:
                    shop_ui.move_selection(-1)
                    continue
                if ev.key == pygame.K_DOWN:
                    shop_ui.move_selection(+1)
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
        if self.type == "shop" and self.shopkeeper is not None:
            self.shopkeeper.draw(surface)
            if hasattr(player, "rect") and self.shopkeeper.can_interact(player.rect()) and not shop_ui.active:
                tip = ui_font.render("E - Abrir tienda", True, (255, 255, 255))
                surface.blit(tip, (self.shopkeeper.rect.x - 12, self.shopkeeper.rect.y - 22))

            
            


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
        used_tiles: set[tuple[int, int]] = set()
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
                self.enemies.append(bonus)
                break

        if self.enemies:
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
        if not self.cleared and len(self.enemies) == 0:
            self.cleared = True
            self.locked = False




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
            # Fallback: colorear las paredes a mano.
            wall = CFG.COLOR_WALL
            for ty in range(CFG.MAP_H):
                row = self.tiles[ty]
                for tx in range(CFG.MAP_W):
                    if row[tx] != CFG.FLOOR:
                        pygame.draw.rect(surf, wall, pygame.Rect(tx * ts, ty * ts, ts, ts))
        # Puertas bloqueadas: dibuja “rejas” rojas en las aberturas
        if self.locked:
            bars = self._door_opening_rects()
            for d, r in bars.items():
                pygame.draw.rect(surf, (180, 40, 40), r)         # relleno rojo
                pygame.draw.rect(surf, (255, 90, 90), r, 1)      # borde claro
        
