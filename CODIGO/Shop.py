# CODIGO/Shop.py
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable

import pygame

from asset_paths import assets_dir, weapon_sprite_path
from rewards import apply_reward_entry


@dataclass
class ShopItem:
    name: str
    price: int
    description: str
    effect: str
    payload: dict
    sprite: pygame.Surface
    sprite_name: str = ""


class Shop:
    UI_SCALE = 0.84
    BASE_WIDTH, BASE_HEIGHT = 720, 420
    WIDTH, HEIGHT = int(BASE_WIDTH * UI_SCALE), int(BASE_HEIGHT * UI_SCALE)
    MAX_ITEMS = 6

    TITLE_COLOR = (255, 240, 180)
    BG_COLOR = (16, 16, 22)
    PANEL_COLOR = (28, 28, 36)
    BORDER_COLOR = (120, 200, 255)
    TEXT_COLOR = (235, 235, 235)
    TEXT_MUTED = (185, 185, 200)
    ACCENT_COLOR = (110, 220, 180)
    ERROR_COLOR = (255, 120, 120)

    def __init__(self, font=None, on_gold_spent: Callable[[int], None] | None = None):
        self.catalog = self._build_catalog()
        self.items: list[ShopItem] = []
        self.active = False
        self.selected = 0
        self.hover_index: int | None = None
        self._font_path = self._resolve_font_path()
        self.font = self._load_font(18)
        self.title_font = self._load_font(28)
        self._on_gold_spent = on_gold_spent

        self.rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        self._arrow_left_rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_rect = pygame.Rect(0, 0, 0, 0)
        self._buy_button_rect = pygame.Rect(0, 0, 0, 0)
        self._center_sprite_rect = pygame.Rect(0, 0, 0, 0)
        self._side_hitboxes: list[tuple[int, pygame.Rect]] = []

        self._message_text: str = ""
        self._message_color = self.TEXT_COLOR
        self._message_timer = 0.0

        self._slide_offset = 0.0
        self._last_ticks = pygame.time.get_ticks()
        self._player_ref = None

        self._microchip_icon, self._microchip_icon_small = self._load_microchip_icons()

        self._seed: int | None = None
        self._rng = random.Random()
        self._inventory_generated = False
        self._restock_random()

    def _scaled(self, value: float) -> int:
        return int(value * self.UI_SCALE)

    def _hover_tint(self, color, amount: int = 50):
        return tuple(min(255, c + amount) for c in color)

    def _hover_fill(self, color, amount: int = 16):
        return tuple(min(255, max(0, c + amount)) for c in color)

    def _resolve_font_path(self) -> Path | None:
        candidates = [
            Path(__file__).resolve().parent / "assets" / "ui" / "VT323-Regular.ttf",
            assets_dir("ui", "VT323-Regular.ttf"),
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _load_font(self, size: int) -> pygame.font.Font:
        if self._font_path:
            try:
                return pygame.font.Font(self._font_path, size)
            except Exception:
                pass
        return pygame.font.SysFont("VT323", size) or pygame.font.SysFont(None, size)

    # ------------------------------------------------------------------
    # Inventario y datos de catálogo
    # ------------------------------------------------------------------
    def _build_catalog(self) -> list[dict]:
        return [
            {
                "name": "Pistolas dobles",
                "price": 58,
                "type": "weapon",
                "id": "dual_pistols",
                "weight": 0.8,
                "description": "Dos pistolas sincronizadas con excelente cadencia de fuego.",
                "effect": "Incrementa la cobertura y permite disparar ráfagas dobles.",
            },
            {
                "name": "Rifle ligero",
                "price": 82,
                "type": "weapon",
                "id": "light_rifle",
                "weight": 0.8,
                "description": "Rifle de precisión con retroceso contenido.",
                "effect": "Mayor daño a distancia manteniendo la movilidad.",
            },
            {
                "name": "Escopeta salva arcana",
                "price": 95,
                "type": "weapon",
                "id": "arcane_salvo",
                "weight": 0.6,
                "description": "Escopeta pesada que libera una salva de proyectiles arcanos.",
                "effect": "Excelente a corta distancia y con amplio cono de impacto.",
            },
            {
                "name": "Rifle de pulsos",
                "price": 108,
                "type": "weapon",
                "id": "pulse_rifle",
                "weight": 0.6,
                "description": "Prototipo que dispara ráfagas energéticas estables.",
                "effect": "Perfecto para mantener daño sostenido sobre jefes.",
            },
            {
                "name": "Guantes tesla",
                "price": 78,
                "type": "weapon",
                "id": "tesla_gloves",
                "weight": 0.6,
                "description": "Canaliza descargas eléctricas a corta distancia.",
                "effect": "Aturde y limpia grupos pequeños rápidamente.",
            },
            {
                "name": "Carabina incandescente",
                "price": 104,
                "type": "weapon",
                "id": "ember_carbine",
                "weight": 0.5,
                "description": "Carabina que dispara ráfagas de plasma incandescente.",
                "effect": "Aplica daño continuo y ligero retroceso sobre enemigos.",
            },
            {
                "name": "Aumento de velocidad (+5%)",
                "price": 30,
                "type": "upgrade",
                "id": "spd_up",
                "weight": 3,
                "description": "Botas afinadas para correr con mayor fluidez.",
                "effect": "Mejora el movimiento del jugador un 5% permanente.",
            },
            {
                "name": "Talismán de recarga (-10%)",
                "price": 54,
                "type": "upgrade",
                "id": "cdr_charm",
                "weight": 3,
                "description": "Cristal que acelera los mecanismos del arma.",
                "effect": "Reduce los tiempos de recarga y enfriamiento en un 10%.",
            },
            {
                "name": "Manual de puntería (-12% cd)",
                "price": 72,
                "type": "upgrade",
                "id": "cdr_core",
                "weight": 2,
                "description": "Rutinas de disparo mejoradas y lubricación óptima.",
                "effect": "Disminuye el cooldown de disparo un 12% adicional.",
            },
            {
                "name": "Botas relámpago (+10% sprint)",
                "price": 48,
                "type": "upgrade",
                "id": "sprint_core",
                "weight": 3,
                "description": "Botas electrizantes que responden al instante.",
                "effect": "Aumentan la velocidad de sprint en un 10% y algo el movimiento.",
            },
            {
                "name": "Condensador de fase (-15% dash)",
                "price": 66,
                "type": "upgrade",
                "id": "dash_core",
                "weight": 2,
                "description": "Concentrador que mejora la disipación de calor del dash.",
                "effect": "Reduce el enfriamiento del dash en un 15% y da micro iframes.",
            },
            {
                "name": "Impulso cinético (+duración dash)",
                "price": 56,
                "type": "upgrade",
                "id": "dash_drive",
                "weight": 2,
                "description": "Mecanismo que extiende el impulso del dash.",
                "effect": "Alarga la duración del dash y permite fasear durante más tiempo.",
            },
            {
                "name": "Pack de cápsulas (+2 golpes)",
                "price": 28,
                "type": "consumable",
                "id": "heal_small",
                "amount": 2,
                "weight": 4,
                "description": "Mini cápsulas reparadoras de emergencia.",
                "effect": "Recupera dos golpes de tu batería de vida actual.",
            },
            {
                "name": "Batería verde (vida completa)",
                "price": 90,
                "type": "consumable",
                "id": "heal_battery_full",
                "weight": 1,
                "description": "Batería de reserva con carga completa.",
                "effect": "Recupera la vida completa de la batería en uso.",
            },
            {
                "name": "Kit de incursión",
                "price": 62,
                "type": "bundle",
                "contents": [
                    {"type": "gold", "amount": 45},
                    {"type": "consumable", "id": "heal_small", "amount": 1},
                    {"type": "upgrade", "id": "spd_up"},
                ],
                "weight": 2,
                "description": "Pack de inicio con recursos para seguir explorando.",
                "effect": "Suma microchips, curación ligera y un impulso de velocidad.",
            },
            {
                "name": "Paquete de reconocimiento",
                "price": 64,
                "type": "bundle",
                "contents": [
                    {"type": "gold", "amount": 40},
                    {"type": "consumable", "id": "heal_small", "amount": 1},
                    {"type": "upgrade", "id": "cdr_charm"},
                ],
                "weight": 2,
                "description": "Equipo para mantenerte con vida en las primeras salas.",
                "effect": "Microchips, curación y menor recarga para tus armas.",
            },
        ]

    def _restock_random(self) -> None:
        self.items = self._select_items(random.Random())
        self._inventory_generated = True
        self.selected = 0
        self.hover_index = None

    def configure_for_seed(self, seed: int | None) -> None:
        self._seed = seed
        base_seed = random.randrange(1 << 30) if seed is None else int(seed)
        self._rng = random.Random(base_seed ^ 0xBADC0FFE)
        self.items = self._select_items(self._rng)
        self.selected = 0
        self.hover_index = None
        self._inventory_generated = True

    def rotate_inventory(self) -> None:
        if self._seed is None:
            self._restock_random()
        else:
            self.configure_for_seed(self._seed)

    def ensure_inventory(self) -> None:
        if self.items:
            return
        if self._inventory_generated and self._seed is not None:
            self.configure_for_seed(self._seed)
        else:
            self._restock_random()

    def _select_items(self, rng: random.Random) -> list[ShopItem]:
        available = list(self.catalog)
        weights = [float(entry.get("weight", 1.0)) for entry in available]
        chosen: list[dict] = []
        while available and len(chosen) < self.MAX_ITEMS:
            choice = rng.choices(available, weights=weights, k=1)[0]
            idx = available.index(choice)
            chosen.append(choice)
            available.pop(idx)
            weights.pop(idx)
        if not chosen:
            chosen = list(self.catalog)
        return [self._build_shop_item(entry) for entry in chosen]

    def _build_shop_item(self, entry: dict) -> ShopItem:
        payload = {k: v for k, v in entry.items() if k not in {"description", "effect", "weight", "sprite"}}
        price = max(0, int(entry.get("price", 0)))
        description = entry.get("description", "")
        effect = entry.get("effect", "")
        sprite_surface, sprite_name = self._load_item_sprite(entry)
        return ShopItem(
            name=entry.get("name", "Artículo misterioso"),
            price=price,
            description=description,
            effect=effect,
            payload=payload,
            sprite=sprite_surface,
            sprite_name=sprite_name,
        )

    # ------------------------------------------------------------------
    # Control de visibilidad y selección
    # ------------------------------------------------------------------
    def open(self, cx: int, cy: int, player=None) -> None:
        self.ensure_inventory()
        self.active = True
        self.rect.center = (cx, cy + self._scaled(20))
        self.hover_index = None
        self._player_ref = player
        self._message_timer = 0.0
        self._message_text = ""
        if hasattr(player, "set_controls_enabled"):
            try:
                player.set_controls_enabled(False)
            except Exception:
                pass

    def close(self) -> None:
        self.active = False
        self.hover_index = None
        if hasattr(self._player_ref, "set_controls_enabled"):
            try:
                self._player_ref.set_controls_enabled(True)
            except Exception:
                pass
        self._player_ref = None

    def move_selection(self, delta: int) -> None:
        if not self.active or not self.items:
            return
        self.selected = (self.selected + delta) % len(self.items)
        self.hover_index = self.selected
        self._start_slide(-delta)

    def _start_slide(self, direction: int) -> None:
        # direction: +1 significa moverse hacia la derecha visualmente
        self._slide_offset += direction * 140

    # ------------------------------------------------------------------
    # Manejo de eventos
    # ------------------------------------------------------------------
    def update_hover(self, mouse_pos) -> None:
        if not self.active:
            self.hover_index = None
            return
        self._ensure_hitboxes()
        self.hover_index = None

    def handle_click(self, mouse_pos, player):
        """Procesa un click izquierdo dentro de la tienda."""
        if not self.active:
            return False, ""

        if not self.rect.collidepoint(mouse_pos):
            self.close()
            return False, ""

        self._ensure_hitboxes()

        if self._arrow_left_rect.collidepoint(mouse_pos):
            self.move_selection(-1)
            return False, ""
        if self._arrow_right_rect.collidepoint(mouse_pos):
            self.move_selection(+1)
            return False, ""

        for idx, rect in self._side_hitboxes:
            if rect.collidepoint(mouse_pos):
                delta = (idx - self.selected)
                # Ajustar delta para navegación circular mínima
                if delta > 0 and abs(delta - len(self.items)) < abs(delta):
                    delta = delta - len(self.items)
                elif delta < 0 and abs(delta + len(self.items)) < abs(delta):
                    delta = delta + len(self.items)
                self.move_selection(delta)
                return False, ""

        if self._buy_button_rect.collidepoint(mouse_pos) or self._center_sprite_rect.collidepoint(mouse_pos):
            return self.try_buy(player)

        return False, ""

    def try_buy(self, player):
        """Aplica compra si hay microchips suficientes y devuelve (comprado: bool, msg: str)."""
        if not self.active or not self.items:
            return False, ""
        item = self.items[self.selected]
        price = max(0, int(item.price))
        gold = getattr(player, "gold", 0)
        if gold < price:
            self._set_message("No tienes suficientes microchips.", self.ERROR_COLOR)
            return False, "No tienes suficiente oro."

        if item.payload.get("type") == "weapon" and hasattr(player, "has_weapon"):
            if player.has_weapon(item.payload.get("id", "")):
                self._set_message("Ya posees esta arma.", self.ERROR_COLOR)
                return False, "Ya tienes esta arma."

        setattr(player, "gold", gold - price)
        if price > 0 and callable(self._on_gold_spent):
            try:
                self._on_gold_spent(price)
            except Exception:
                pass

        applied = apply_reward_entry(player, item.payload)
        name = item.name
        self.items.pop(self.selected)
        if self.items:
            self.selected %= len(self.items)
            self.hover_index = self.selected
        else:
            self.selected = 0
            self.hover_index = None
        if applied:
            self._set_message(f"Compraste: {name}", self.ACCENT_COLOR)
        else:
            self._set_message("No se pudo aplicar el artículo.", self.ERROR_COLOR)
        return applied, f"Compraste: {name}"

    # ------------------------------------------------------------------
    # Renderizado
    # ------------------------------------------------------------------
    def draw(self, surface):
        if not self.active:
            return
        self._update_time()
        self._ensure_hitboxes()

        pygame.draw.rect(surface, self.BG_COLOR, self.rect, border_radius=12)
        pygame.draw.rect(surface, self.BORDER_COLOR, self.rect, 2, border_radius=12)

        title = self.title_font.render("TIENDA", True, self.TITLE_COLOR)
        surface.blit(title, (self.rect.x + self._scaled(20), self.rect.y + self._scaled(16)))

        mouse_pos = pygame.mouse.get_pos()

        self._draw_player_wallet(surface)
        if not self.items:
            empty = self.font.render("Inventario agotado", True, self.TEXT_COLOR)
            surface.blit(empty, (self.rect.centerx - empty.get_width() // 2, self.rect.centery))
            return

        prev_idx = (self.selected - 1) % len(self.items)
        next_idx = (self.selected + 1) % len(self.items)

        self._draw_side_item(
            surface,
            self.items[prev_idx],
            self._side_hitboxes[0][1],
            faded=True,
            hovered=False,
        )
        self._draw_side_item(
            surface,
            self.items[next_idx],
            self._side_hitboxes[1][1],
            faded=True,
            hovered=False,
        )
        self._draw_center_panel(surface, self.items[self.selected], hovered=False)

        self._draw_arrows(surface, mouse_pos)
        self._draw_buy_button(surface, mouse_pos)
        self._draw_message(surface)

    def _draw_center_panel(self, surface, item: ShopItem, *, hovered: bool = False) -> None:
        panel_rect = self._center_sprite_rect.copy()
        panel_rect.inflate_ip(self._scaled(32), self._scaled(32))
        panel_color = self.PANEL_COLOR
        border_color = self.BORDER_COLOR
        if hovered:
            panel_color = self._hover_fill(panel_color)
            border_color = self._hover_tint(border_color)
        pygame.draw.rect(surface, panel_color, panel_rect, border_radius=8)
        pygame.draw.rect(surface, border_color, panel_rect, 2, border_radius=8)

        max_w, max_h = 200, 200
        sprite = self._scaled_sprite(item.sprite, max_w, max_h)
        sprite_pos = sprite.get_rect(center=self._center_sprite_rect.center)
        surface.blit(sprite, sprite_pos)

        text_y = panel_rect.bottom + self._scaled(10)
        name = self.title_font.render(item.name, True, self.TEXT_COLOR)
        surface.blit(name, (self.rect.x + self._scaled(24), text_y))

        price_text = self._price_surface(item.price)
        surface.blit(price_text, (self.rect.right - price_text.get_width() - self._scaled(24), text_y))

        desc_lines = self._wrap_text(item.description, self.rect.width - self._scaled(48))
        effect_lines = self._wrap_text(f"Efecto: {item.effect}", self.rect.width - self._scaled(48))

        y = text_y + name.get_height() + 6
        for line in desc_lines:
            txt = self.font.render(line, True, self.TEXT_COLOR)
            surface.blit(txt, (self.rect.x + self._scaled(24), y))
            y += txt.get_height() + 2
        for line in effect_lines:
            txt = self.font.render(line, True, self.ACCENT_COLOR)
            surface.blit(txt, (self.rect.x + self._scaled(24), y))
            y += txt.get_height() + 2

    def _draw_side_item(self, surface, item: ShopItem, rect: pygame.Rect, faded: bool = False, *, hovered: bool = False) -> None:
        scale = 0.6
        max_w, max_h = int(160 * scale), int(160 * scale)
        sprite = self._scaled_sprite(item.sprite, max_w, max_h)
        sprite_pos = sprite.get_rect(center=rect.center)
        shaded = sprite.copy()
        if faded:
            shaded.fill((120, 120, 120, 180), None, pygame.BLEND_RGBA_MULT)
        surface.blit(shaded, sprite_pos)

        if hovered:
            glow_rect = rect.inflate(self._scaled(10), self._scaled(10))
            pygame.draw.rect(surface, self._hover_tint(self.ACCENT_COLOR), glow_rect, 2, border_radius=10)

    def _draw_arrows(self, surface, mouse_pos) -> None:
        arrow_color = self.BORDER_COLOR
        for rect, direction in ((self._arrow_left_rect, -1), (self._arrow_right_rect, 1)):
            hovered = rect.collidepoint(mouse_pos)
            color = self._hover_tint(arrow_color) if hovered else arrow_color
            fill = self._hover_fill(self.PANEL_COLOR) if hovered else self.PANEL_COLOR
            pygame.draw.rect(surface, fill, rect, border_radius=6)
            pygame.draw.rect(surface, color, rect, 2, border_radius=6)
            cx, cy = rect.center
            size = rect.height // 3
            if direction < 0:
                points = [(cx + size // 2, cy - size), (cx + size // 2, cy + size), (cx - size, cy)]
            else:
                points = [(cx - size // 2, cy - size), (cx - size // 2, cy + size), (cx + size, cy)]
            pygame.draw.polygon(surface, color, points)

    def _draw_buy_button(self, surface, mouse_pos) -> None:
        player_gold = getattr(self._player_ref, "gold", None)
        affordable = player_gold is None or not self.items or player_gold >= self.items[self.selected].price
        color = self.ACCENT_COLOR if affordable else self.TEXT_MUTED
        hovered = self._buy_button_rect.collidepoint(mouse_pos)
        fill = self._hover_fill(self.PANEL_COLOR) if hovered else self.PANEL_COLOR
        border_color = self._hover_tint(color) if hovered else color
        shadow_rect = self._buy_button_rect.inflate(self._scaled(6), self._scaled(6))
        pygame.draw.rect(surface, (0, 0, 0, 60), shadow_rect, border_radius=12)
        pygame.draw.rect(surface, fill, self._buy_button_rect, border_radius=10)
        pygame.draw.rect(surface, border_color, self._buy_button_rect, 3, border_radius=10)
        label = self.title_font.render("Comprar", True, border_color)
        surface.blit(label, label.get_rect(center=self._buy_button_rect.center))

    def _draw_message(self, surface) -> None:
        if self._message_timer <= 0.0 or not self._message_text:
            return
        txt = self.font.render(self._message_text, True, self._message_color)
        pos = txt.get_rect()
        pos.centerx = self.rect.centerx
        pos.y = self.rect.bottom - pos.height - self._scaled(12)
        surface.blit(txt, pos)

    def _draw_player_wallet(self, surface) -> None:
        if self._player_ref is None:
            return
        microchips = getattr(self._player_ref, "gold", 0)
        icon = self._microchip_icon_small
        label = self.font.render(f"Monedas: {microchips}", True, self.TITLE_COLOR)
        x = self.rect.right - icon.get_width() - label.get_width() - self._scaled(18)
        y = self.rect.y + self._scaled(14)
        surface.blit(icon, (x, y))
        surface.blit(label, (x + icon.get_width() + 8, y + (icon.get_height() - label.get_height()) // 2))

    # ------------------------------------------------------------------
    # Utilidades de render
    # ------------------------------------------------------------------
    def _price_surface(self, price: int) -> pygame.Surface:
        label = self.font.render(f"Costo: {price}", True, self.TITLE_COLOR)
        icon = self._microchip_icon_small
        if icon.get_width():
            height = max(label.get_height(), icon.get_height())
            surf = pygame.Surface((label.get_width() + icon.get_width() + 8, height), pygame.SRCALPHA)
            surf.blit(icon, (0, (height - icon.get_height()) // 2))
            surf.blit(label, (icon.get_width() + 8, (height - label.get_height()) // 2))
            return surf
        return label

    def _scaled_sprite(self, sprite: pygame.Surface, max_w: int, max_h: int) -> pygame.Surface:
        if sprite.get_width() <= max_w and sprite.get_height() <= max_h:
            return sprite
        return pygame.transform.smoothscale(sprite, self._fit_size(sprite.get_size(), (max_w, max_h)))

    def _fit_size(self, size: tuple[int, int], max_size: tuple[int, int]) -> tuple[int, int]:
        w, h = size
        max_w, max_h = max_size
        scale = min(max_w / w, max_h / h)
        return int(w * scale), int(h * scale)

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            if self.font.size(trial)[0] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [text]

    def _set_message(self, text: str, color) -> None:
        self._message_text = text
        self._message_color = color
        self._message_timer = 2.5

    def _update_time(self) -> None:
        now = pygame.time.get_ticks()
        dt = (now - self._last_ticks) / 1000.0
        self._last_ticks = now
        self._slide_offset *= 0.85
        if abs(self._slide_offset) < 0.5:
            self._slide_offset = 0.0
        if self._message_timer > 0.0:
            self._message_timer -= dt

    def _ensure_hitboxes(self) -> None:
        cx, cy = self.rect.center
        cy -= self._scaled(12)
        offset = self._slide_offset
        side_gap = self._scaled(190)
        side_size = self._scaled(140)
        center_size = self._scaled(180)

        left_rect = pygame.Rect(0, 0, side_size, side_size)
        left_rect.center = (cx - side_gap + offset, cy)
        right_rect = pygame.Rect(0, 0, side_size, side_size)
        right_rect.center = (cx + side_gap + offset, cy)
        center_rect = pygame.Rect(0, 0, center_size, center_size)
        center_rect.center = (cx + offset, cy)

        self._center_sprite_rect = center_rect
        self._side_hitboxes = [
            ((self.selected - 1) % len(self.items) if self.items else 0, left_rect),
            ((self.selected + 1) % len(self.items) if self.items else 0, right_rect),
        ]

        arrow_w, arrow_h = self._scaled(44), self._scaled(64)
        self._arrow_left_rect = pygame.Rect(0, 0, arrow_w, arrow_h)
        self._arrow_left_rect.center = (self.rect.x + self._scaled(60), cy)
        self._arrow_right_rect = pygame.Rect(0, 0, arrow_w, arrow_h)
        self._arrow_right_rect.center = (self.rect.right - self._scaled(60), cy)

        buy_w, buy_h = self._scaled(200), self._scaled(52)
        self._buy_button_rect = pygame.Rect(0, 0, buy_w, buy_h)
        padding_y = self._scaled(32)
        self._buy_button_rect.midtop = (self.rect.centerx, self.rect.y + padding_y)

    def _load_microchip_icons(self) -> tuple[pygame.Surface, pygame.Surface]:
        base_icon, pickup_icon = self._create_procedural_microchip()
        source_icon = pickup_icon or base_icon
        try:
            sprite = pygame.image.load(assets_dir("ui", "chip_moneda.png")).convert_alpha()
            if sprite.get_width() and sprite.get_height():
                source_icon = sprite
        except Exception:
            pass

        main_icon = self._scale_icon(source_icon, 0.72)
        small_icon = self._scale_icon(source_icon, 0.48)
        return main_icon, small_icon

    def _scale_icon(self, icon: pygame.Surface, scale: float) -> pygame.Surface:
        if icon.get_width() == 0 or icon.get_height() == 0:
            return pygame.Surface((0, 0), pygame.SRCALPHA)
        width = max(1, int(icon.get_width() * scale))
        height = max(1, int(icon.get_height() * scale))
        return pygame.transform.smoothscale(icon, (width, height))

    def _create_procedural_microchip(self) -> tuple[pygame.Surface, pygame.Surface]:
        base_size = 32
        chip = pygame.Surface((base_size, base_size), pygame.SRCALPHA)
        chip.fill((0, 0, 0, 0))

        body_rect = chip.get_rect().inflate(-8, -8)
        frame_color = pygame.Color(120, 20, 80)
        frame_shadow = pygame.Color(70, 10, 48)
        pygame.draw.rect(chip, frame_shadow, body_rect, border_radius=6)
        pygame.draw.rect(chip, frame_color, body_rect.inflate(-2, -2), border_radius=6)

        core_rect = body_rect.inflate(-8, -8)
        core_color = pygame.Color(28, 94, 116)
        core_dark = pygame.Color(12, 48, 64)
        pygame.draw.rect(chip, core_color, core_rect, border_radius=5)
        pygame.draw.rect(chip, core_dark, core_rect, width=2, border_radius=5)

        highlight = pygame.Surface(core_rect.size, pygame.SRCALPHA)
        light_a = pygame.Color(136, 236, 238, 190)
        light_b = pygame.Color(94, 204, 220, 140)
        start_y = core_rect.height // 3
        pygame.draw.line(highlight, light_a, (3, start_y), (core_rect.width - 4, start_y - 3), 3)
        pygame.draw.line(highlight, light_b, (3, start_y + 4), (core_rect.width - 6, start_y + 1), 2)
        chip.blit(highlight, core_rect.topleft)

        pin_color = pygame.Color(230, 176, 70)
        pin_shadow = pygame.Color(156, 116, 46)
        pin_w, pin_h = 5, 6
        slots = 4
        slot_spacing = (body_rect.height - 12) / max(1, slots - 1)
        for i in range(slots):
            offset = int(body_rect.top + 6 + i * slot_spacing)
            left_pin = pygame.Rect(0, 0, pin_w, pin_h)
            left_pin.midright = (body_rect.left - 1, offset)
            right_pin = pygame.Rect(0, 0, pin_w, pin_h)
            right_pin.midleft = (body_rect.right + 1, offset)
            pygame.draw.rect(chip, pin_color, left_pin)
            pygame.draw.rect(chip, pin_shadow, left_pin, 1)
            pygame.draw.rect(chip, pin_color, right_pin)
            pygame.draw.rect(chip, pin_shadow, right_pin, 1)

        slot_spacing = (body_rect.width - 12) / max(1, slots - 1)
        for i in range(slots):
            offset = int(body_rect.left + 6 + i * slot_spacing)
            top_pin = pygame.Rect(0, 0, pin_h, pin_w)
            top_pin.midbottom = (offset, body_rect.top - 1)
            bottom_pin = pygame.Rect(0, 0, pin_h, pin_w)
            bottom_pin.midtop = (offset, body_rect.bottom + 1)
            pygame.draw.rect(chip, pin_color, top_pin)
            pygame.draw.rect(chip, pin_shadow, top_pin, 1)
            pygame.draw.rect(chip, pin_color, bottom_pin)
            pygame.draw.rect(chip, pin_shadow, bottom_pin, 1)

        pickup = pygame.transform.smoothscale(chip, (12, 12))
        return chip, pickup

    def _load_item_sprite(self, entry: dict) -> tuple[pygame.Surface, str]:
        sprite_path: Path | None = None
        sprite_name = ""
        if entry.get("sprite"):
            sprite_path = assets_dir(entry.get("sprite")) if isinstance(entry.get("sprite"), str) else Path(entry.get("sprite"))
        elif entry.get("type") == "weapon":
            sprite_path = weapon_sprite_path(entry.get("id", ""))
        elif entry.get("type") == "consumable":
            sprite_path = assets_dir("ui", "Baterias_Vida.png")
        elif entry.get("type") == "bundle":
            sprite_path = assets_dir("ui", "panel_inventario.png")
        elif entry.get("type") == "upgrade":
            sprite_path = assets_dir("ui", "panel_minimapa.png")

        sprite = None
        if sprite_path:
            try:
                sprite = pygame.image.load(sprite_path).convert_alpha()
                sprite_name = sprite_path.name
            except Exception:
                sprite = None
        if sprite is None:
            sprite = self._placeholder_sprite(entry.get("name", "?"))
        return sprite, sprite_name

    def _placeholder_sprite(self, label: str) -> pygame.Surface:
        surf = pygame.Surface((128, 128), pygame.SRCALPHA)
        surf.fill((70, 80, 110))
        pygame.draw.rect(surf, self.BORDER_COLOR, surf.get_rect(), 3)
        txt = self.font.render(label[:10], True, self.TITLE_COLOR)
        surf.blit(txt, txt.get_rect(center=surf.get_rect().center))
        return surf

