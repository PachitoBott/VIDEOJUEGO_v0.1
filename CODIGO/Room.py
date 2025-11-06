import json
import os
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


_OBSTACLE_ASSET_DIR = os.path.join("assets", "obstacles")
os.makedirs(_OBSTACLE_ASSET_DIR, exist_ok=True)


_OBSTACLE_SPRITE_CACHE: dict[tuple[tuple[int, int], str], pygame.Surface] = {}
_OBSTACLE_SPRITE_PATHS: dict[tuple[tuple[int, int], str], str] = {}


_OBSTACLE_VARIANTS: dict[tuple[int, int], list[str]] = {
    (1, 1): ["silla", "hoyo", "caneca"],
    (1, 2): ["tubo_verde"],
    (2, 1): ["pantalla", "impresora"],
    (2, 2): ["pantallas"],
    (4, 2): ["pantallas_azules"],
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
    "pantalla": ((82, 188, 242), (36, 90, 126)),
    "impresora": ((210, 210, 210), (128, 128, 128)),
    "pantallas": ((120, 160, 196), (70, 100, 132)),
    "pantallas_azules": ((74, 142, 212), (28, 68, 128)),
}


def _register_obstacle_sprite_path(size_tiles: tuple[int, int], variant: str, path: str) -> None:
    key = (tuple(size_tiles), variant.lower().strip())
    if not key[1]:
        key = (key[0], "default")
    _OBSTACLE_SPRITE_PATHS[key] = path
    _OBSTACLE_SPRITE_CACHE.pop(key, None)


def register_obstacle_sprite(
    size_tiles: tuple[int, int],
    variant: str,
    filename: str,
) -> None:
    """Registra explícitamente un sprite personalizado para un obstáculo.

    Parameters
    ----------
    size_tiles:
        Tamaño (ancho, alto) en tiles del obstáculo al que aplica el sprite.
    variant:
        Nombre de la variante (por ejemplo "silla" o "tubo_verde").
    filename:
        Ruta al archivo PNG. Si es relativa se toma desde ``assets/obstacles``.
    """

    if not variant:
        raise ValueError("variant no puede ser vacío al registrar un sprite")

    norm_variant = variant.lower().strip()
    if os.path.isabs(filename):
        path = filename
    else:
        path = os.path.join(_OBSTACLE_ASSET_DIR, filename)
    _register_obstacle_sprite_path(tuple(size_tiles), norm_variant, path)


def clear_obstacle_sprite_cache() -> None:
    """Vacia el caché interno para volver a cargar sprites personalizados."""

    _OBSTACLE_SPRITE_CACHE.clear()


def _load_obstacle_manifest() -> None:
    manifest_path = os.path.join(_OBSTACLE_ASSET_DIR, "manifest.json")
    if not os.path.exists(manifest_path):
        return
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return

    if not isinstance(manifest, dict):
        return

    for variant, entries in manifest.items():
        if not isinstance(entries, dict):
            continue
        norm_variant = str(variant).lower().strip()
        for size_key, path in entries.items():
            if not isinstance(path, str):
                continue
            size_key = str(size_key).lower().strip()
            if size_key == "default":
                size_tuple = (0, 0)
            else:
                try:
                    w_str, h_str = size_key.split("x", 1)
                    size_tuple = (int(w_str), int(h_str))
                except (ValueError, TypeError):
                    continue
            if os.path.isabs(path):
                resolved = path
            else:
                resolved = os.path.join(_OBSTACLE_ASSET_DIR, path)
            _register_obstacle_sprite_path(size_tuple, norm_variant, resolved)


_load_obstacle_manifest()


def _resolve_registered_path(size_tiles: tuple[int, int], variant_slug: str) -> Optional[str]:
    specific_key = (size_tiles, variant_slug)
    path = _OBSTACLE_SPRITE_PATHS.get(specific_key)
    if path and os.path.exists(path):
        return path
    default_key = ((0, 0), variant_slug)
    path = _OBSTACLE_SPRITE_PATHS.get(default_key)
    if path and os.path.exists(path):
        return path
    return None


def _load_obstacle_sprite(size_tiles: tuple[int, int], variant: str | None = None) -> pygame.Surface:
    width_tiles, height_tiles = size_tiles
    variant_slug = (variant or "").lower().strip() or "default"
    key = (size_tiles, variant_slug)
    if key in _OBSTACLE_SPRITE_CACHE:
        return _OBSTACLE_SPRITE_CACHE[key]

    ts = CFG.TILE_SIZE
    width_px = width_tiles * ts
    height_px = height_tiles * ts

    asset_dir = _OBSTACLE_ASSET_DIR
    os.makedirs(asset_dir, exist_ok=True)

    filenames: list[str] = []
    registered_path = _resolve_registered_path(size_tiles, variant_slug)
    if registered_path:
        filenames.append(registered_path)
    if variant_slug and variant_slug != "default":
        filenames.extend([
            f"obstacle_{variant_slug}_{width_tiles}x{height_tiles}.png",
            f"{variant_slug}_{width_tiles}x{height_tiles}.png",
            f"obstacle_{variant_slug}.png",
            f"{variant_slug}.png",
        ])
    filenames.extend([
        f"crate_{width_tiles}x{height_tiles}.png",
        "crate.png",
    ])

    surface: pygame.Surface | None = None
    for filename in filenames:
        if os.path.isabs(filename):
            candidate = filename
        else:
            candidate = os.path.join(asset_dir, filename)
        if not os.path.exists(candidate):
            continue
        try:
            loaded = pygame.image.load(candidate).convert_alpha()
        except pygame.error:
            continue
        if loaded.get_size() != (width_px, height_px):
            loaded = pygame.transform.smoothscale(loaded, (width_px, height_px))
        surface = loaded
        break

    if surface is None:
        base_color, border_color = _OBSTACLE_FALLBACK_COLORS.get(
            variant_slug,
            ((124, 92, 64), (90, 60, 38)),
        )
        surface = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
        surface.fill(base_color)
        pygame.draw.rect(surface, border_color, surface.get_rect(), 3)
        if width_tiles >= 2 or height_tiles >= 2:
            inner = surface.get_rect().inflate(-ts // 2, -ts // 2)
            if inner.width > 0 and inner.height > 0:
                pygame.draw.rect(surface, border_color, inner, 1)

    _OBSTACLE_SPRITE_CACHE[key] = surface
    return surface


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
        self.treasure: dict | None = None
        self.treasure_message: str = ""
        self.treasure_message_until: int = 0

        self.obstacles: list[dict] = []
        self._obstacle_tiles: set[tuple[int, int]] = set()


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

    def _can_place_obstacle(self, tx: int, ty: int, w_tiles: int, h_tiles: int) -> bool:
        if self.bounds is None:
            return False
        rx, ry, rw, rh = self.bounds
        min_tx = rx + 1
        min_ty = ry + 1
        max_tx = rx + rw - w_tiles - 1
        max_ty = ry + rh - h_tiles - 1
        if tx < min_tx or ty < min_ty or tx > max_tx or ty > max_ty:
            return False
        for dy in range(h_tiles):
            for dx in range(w_tiles):
                cx = tx + dx
                cy = ty + dy
                if not (0 <= cx < CFG.MAP_W and 0 <= cy < CFG.MAP_H):
                    return False
                if self.tiles[cy][cx] != CFG.FLOOR:
                    return False
                if (cx, cy) in self._obstacle_tiles:
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
        tiles = {(tx + dx, ty + dy) for dy in range(h_tiles) for dx in range(w_tiles)}
        self.obstacles.append({
            "rect": rect,
            "tiles": tiles,
            "size": (w_tiles, h_tiles),
            "variant": (variant or "").lower().strip() or "default",
        })
        self._obstacle_tiles.update(tiles)

    def generate_obstacles(self, rng: random.Random | None = None, max_density: float = 0.08) -> None:
        if self.bounds is None:
            return
        self.clear_obstacles()
        rng = rng or random

        rx, ry, rw, rh = self.bounds
        interior_w = max(0, rw - 2)
        interior_h = max(0, rh - 2)
        if interior_w <= 0 or interior_h <= 0:
            return

        interior_area = interior_w * interior_h
        max_obstacles = max(0, int(interior_area * max_density))
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
            if not self._can_place_obstacle(tx, ty, w_tiles, h_tiles):
                continue
            variant_choices = _OBSTACLE_VARIANTS.get((w_tiles, h_tiles), ["default"])
            variant = rng.choice(variant_choices)
            self._register_obstacle(tx, ty, w_tiles, h_tiles, variant=variant)
            placed += 1

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
        elif self.type == "treasure":
            self.safe = True
            self.no_spawn = True
            self.no_combat = True
            self.locked = False
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
        if self.type == "treasure":
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
                        rotater = getattr(shop_ui, "rotate_inventory", None)
                        if callable(rotater):
                            rotater()
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
        if self.type == "treasure" and self.treasure:
            self._draw_treasure_overlay(surface, ui_font, player)

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
        if self.tiles[ty][tx] == CFG.WALL:
            return True
        return (tx, ty) in self._obstacle_tiles
    
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
            # Fallback: colorear las paredes a mano, evitando el exterior.
            wall = CFG.COLOR_WALL
            for ty in range(CFG.MAP_H):
                row = self.tiles[ty]
                for tx in range(CFG.MAP_W):
                    if row[tx] != CFG.FLOOR and self._wall_adjacent_to_floor(tx, ty):
                        pygame.draw.rect(surf, wall, pygame.Rect(tx * ts, ty * ts, ts, ts))

        if self.obstacles:
            for obstacle in self.obstacles:
                sprite = _load_obstacle_sprite(obstacle["size"], obstacle.get("variant"))
                surf.blit(sprite, obstacle["rect"].topleft)

        if self.type == "treasure" and self.treasure:
            self._draw_treasure(surf)
        # Puertas bloqueadas: dibuja “rejas” rojas en las aberturas
        if self.locked:
            bars = self._door_opening_rects()
            for d, r in bars.items():
                pygame.draw.rect(surf, (180, 40, 40), r)         # relleno rojo
                pygame.draw.rect(surf, (255, 90, 90), r, 1)      # borde claro

    # ------------------------------------------------------------------ #
    # Tesoro
    # ------------------------------------------------------------------ #
    def setup_treasure_room(self, loot_table: list[dict]) -> None:
        self.type = "treasure"
        self.safe = True
        self.no_spawn = True
        self.no_combat = True
        self.locked = False
        self.treasure_message = ""
        self.treasure_message_until = 0
        self.clear_obstacles()

        if not self.bounds:
            self.build_centered(9, 9)
        assert self.bounds is not None
        rx, ry, rw, rh = self.bounds
        ts = CFG.TILE_SIZE
        cx = (rx + rw // 2) * ts
        cy = (ry + rh // 2) * ts

        width = 28
        height = 20
        self.treasure = {
            "rect": pygame.Rect(cx - width // 2, cy - height // 2, width, height),
            "opened": False,
            "loot_table": loot_table,
        }

    def _handle_treasure_events(self, events, player) -> None:
        if not self.treasure:
            return

        chest_rect: pygame.Rect = self.treasure["rect"]
        player_rect = self._player_rect(player)
        interact_rect = chest_rect.inflate(30, 30)
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
        return self._apply_reward_entry(player, reward)

    def _apply_reward_entry(self, player, reward: dict) -> bool:
        rtype = reward.get("type")
        if rtype == "gold":
            return self._apply_gold_reward(player, reward.get("amount", 0))
        if rtype == "heal":
            return self._apply_heal_reward(player, reward.get("amount", 0))
        if rtype == "weapon":
            return self._apply_weapon_reward(player, reward.get("id"))
        if rtype == "upgrade":
            return self._apply_upgrade_reward(player, reward.get("id"))
        if rtype == "consumable":
            return self._apply_consumable_reward(player, reward)
        if rtype == "bundle":
            return self._apply_bundle_reward(player, reward)
        return False

    def _apply_gold_reward(self, player, amount) -> bool:
        amount = int(amount)
        if amount <= 0:
            return False
        current = getattr(player, "gold", 0)
        setattr(player, "gold", current + amount)
        return True

    def _apply_heal_reward(self, player, amount) -> bool:
        amount = int(amount)
        if amount <= 0:
            return False
        max_hp = getattr(player, "max_hp", getattr(player, "hp", 1))
        hp = getattr(player, "hp", max_hp)
        new_hp = min(max_hp, hp + amount)
        setattr(player, "hp", new_hp)
        if hasattr(player, "_hits_taken_current_life"):
            setattr(player, "_hits_taken_current_life", max(0, max_hp - new_hp))
        return new_hp != hp

    def _apply_weapon_reward(self, player, wid: str | None) -> bool:
        if not wid:
            return False
        unlock = getattr(player, "unlock_weapon", None)
        if callable(unlock):
            return bool(unlock(wid, auto_equip=True))
        equip = getattr(player, "equip_weapon", None)
        if callable(equip):
            equip(wid)
            return True
        setattr(player, "current_weapon", wid)
        return True

    def _apply_upgrade_reward(self, player, uid: str) -> bool:
        if uid == "hp_up":
            max_lives = getattr(player, "max_lives", getattr(player, "lives", 1))
            lives = getattr(player, "lives", max_lives)
            max_lives += 1
            lives = min(lives + 1, max_lives)
            setattr(player, "max_lives", max_lives)
            setattr(player, "lives", lives)
            return True
        if uid == "spd_up":
            speed = getattr(player, "speed", 1.0)
            setattr(player, "speed", speed * 1.05)
            return True
        if uid == "armor_up":
            max_hp = getattr(player, "max_hp", getattr(player, "hp", 3))
            hp = getattr(player, "hp", max_hp)
            max_hp += 1
            hp = min(hp + 1, max_hp)
            setattr(player, "max_hp", max_hp)
            setattr(player, "hp", hp)
            if hasattr(player, "_hits_taken_current_life"):
                hits_taken = max(0, max_hp - hp)
                setattr(player, "_hits_taken_current_life", hits_taken)
            return True
        if uid == "cdr_charm":
            current = getattr(player, "cooldown_scale", 1.0)
            new_scale = max(0.4, current * 0.9)
            setattr(player, "cooldown_scale", new_scale)
            refresher = getattr(player, "refresh_weapon_modifiers", None)
            if callable(refresher):
                refresher()
            elif hasattr(player, "weapon") and player.weapon:
                setter = getattr(player.weapon, "set_cooldown_scale", None)
                if callable(setter):
                    setter(new_scale)
            return True
        if uid == "cdr_core":
            current = getattr(player, "cooldown_scale", 1.0)
            new_scale = max(0.35, current * 0.88)
            setattr(player, "cooldown_scale", new_scale)
            refresher = getattr(player, "refresh_weapon_modifiers", None)
            if callable(refresher):
                refresher()
            elif hasattr(player, "weapon") and player.weapon:
                setter = getattr(player.weapon, "set_cooldown_scale", None)
                if callable(setter):
                    setter(new_scale)
            return True
        if uid == "sprint_core":
            sprint = getattr(player, "sprint_multiplier", 1.0)
            setattr(player, "sprint_multiplier", sprint * 1.1)
            speed = getattr(player, "speed", 1.0)
            setattr(player, "speed", speed * 1.03)
            return True
        if uid == "dash_core":
            cooldown = getattr(player, "dash_cooldown", 0.75)
            new_cd = max(0.25, cooldown * 0.85)
            setattr(player, "dash_cooldown", new_cd)
            return True
        if uid == "dash_drive":
            duration = getattr(player, "dash_duration", 0.18)
            new_duration = min(0.45, duration + 0.05)
            setattr(player, "dash_duration", new_duration)
            setattr(player, "dash_iframe_duration", new_duration + 0.08)
            return True
        return False

    def _apply_consumable_reward(self, player, reward: dict) -> bool:
        cid = reward.get("id")
        if not cid:
            return False
        if cid == "heal_full":
            max_hp = getattr(player, "max_hp", getattr(player, "hp", 1))
            setattr(player, "hp", max_hp)
            if hasattr(player, "_hits_taken_current_life"):
                setattr(player, "_hits_taken_current_life", 0)
            return True
        if cid == "heal_medium":
            amount = int(reward.get("amount", 2) or 2)
            return self._apply_heal_reward(player, amount)
        if cid == "heal_small":
            amount = int(reward.get("amount", 1) or 1)
            return self._apply_heal_reward(player, amount)
        if cid == "life_refill":
            max_lives = getattr(player, "max_lives", getattr(player, "lives", 1))
            setattr(player, "lives", max_lives)
            return True
        return False

    def _apply_bundle_reward(self, player, reward: dict) -> bool:
        contents = reward.get("contents") or []
        applied_any = False
        for entry in contents:
            if not isinstance(entry, dict):
                continue
            applied_any = self._apply_reward_entry(player, entry) or applied_any
        return applied_any

    def _draw_treasure(self, surface: pygame.Surface) -> None:
        if not self.treasure:
            return
        rect: pygame.Rect = self.treasure["rect"]
        opened = self.treasure.get("opened", False)
        body_color = (176, 124, 56) if not opened else (110, 96, 96)
        lid_color = (214, 168, 96) if not opened else (140, 128, 128)
        band_color = (235, 208, 128) if not opened else (180, 172, 172)

        pygame.draw.rect(surface, body_color, rect)
        lid_height = max(6, rect.height // 3)
        lid_rect = pygame.Rect(rect.x, rect.y, rect.width, lid_height)
        pygame.draw.rect(surface, lid_color, lid_rect)
        pygame.draw.rect(surface, band_color, pygame.Rect(rect.centerx - 3, rect.y, 6, rect.height))
        pygame.draw.rect(surface, (20, 12, 8), rect, 2)

    def _draw_treasure_overlay(self, surface, ui_font, player) -> None:
        rect = self.treasure["rect"]
        player_rect = self._player_rect(player)
        near = rect.inflate(36, 36).colliderect(player_rect)

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
        
