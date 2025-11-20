# CODIGO/Shop.py
import random
from collections.abc import Callable
import pygame

from rewards import apply_reward_entry

class Shop:
    WIDTH, HEIGHT = 320, 240
    MAX_ITEMS = 6

    def __init__(self, font=None, on_gold_spent: Callable[[int], None] | None = None):
        self.catalog = [
            {"name": "Pistolas dobles", "price": 58, "type": "weapon", "id": "dual_pistols", "weight": 0.8},
            {"name": "Rifle ligero", "price": 82, "type": "weapon", "id": "light_rifle", "weight": 0.8},
            {"name": "Escopeta salva arcana", "price": 95, "type": "weapon", "id": "arcane_salvo", "weight": 0.6},
            {"name": "Rifle de pulsos", "price": 108, "type": "weapon", "id": "pulse_rifle", "weight": 0.6},
            {"name": "Guantes tesla", "price": 78, "type": "weapon", "id": "tesla_gloves", "weight": 0.6},
            {"name": "Carabina incandescente", "price": 104, "type": "weapon", "id": "ember_carbine", "weight": 0.5},
            {"name": "Vida extra (+1)", "price": 45, "type": "upgrade", "id": "hp_up", "weight": 4},
            {"name": "Aumento de velocidad (+5%)", "price": 30, "type": "upgrade", "id": "spd_up", "weight": 3},
            {"name": "Talismán de recarga (-10%)", "price": 54, "type": "upgrade", "id": "cdr_charm", "weight": 3},
            {"name": "Manual de puntería (-12% cd)", "price": 72, "type": "upgrade", "id": "cdr_core", "weight": 2},
            {"name": "Botas relámpago (+10% sprint)", "price": 48, "type": "upgrade", "id": "sprint_core", "weight": 3},
            {"name": "Condensador de fase (-15% dash)", "price": 66, "type": "upgrade", "id": "dash_core", "weight": 2},
            {"name": "Impulso cinético (+duración dash)", "price": 56, "type": "upgrade", "id": "dash_drive", "weight": 2},
            {"name": "Pack de cápsulas (+2 golpes)", "price": 28, "type": "consumable", "id": "heal_small", "amount": 2, "weight": 4},
            {"name": "Batería verde (vida completa)", "price": 90, "type": "consumable", "id": "heal_battery_full", "weight": 1},
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
            },
        ]
        self.items: list[dict] = []
        self.active = False
        self.selected = 0
        self.hover_index = None
        self.font = font or pygame.font.SysFont(None, 18)
        self._on_gold_spent = on_gold_spent

        # ventana
        self.rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        self._item_hitboxes: list[pygame.Rect] = []
        self._restock()

    def rotate_inventory(self) -> None:
        """Genera un nuevo lote de artículos disponibles."""
        self._restock()

    def _restock(self) -> None:
        available = list(self.catalog)
        weights = [float(entry.get("weight", 1.0)) for entry in available]
        self.items = []
        while available and len(self.items) < self.MAX_ITEMS:
            choice = random.choices(available, weights=weights, k=1)[0]
            idx = available.index(choice)
            entry = {k: v for k, v in choice.items() if k != "weight"}
            self.items.append(entry)
            available.pop(idx)
            weights.pop(idx)
        if not self.items:
            # fallback por si las ponderaciones eran cero
            self.items = [{k: v for k, v in entry.items() if k != "weight"} for entry in self.catalog]
        self.selected = 0
        self.hover_index = None

        # rng propio para fijar inventario por seed
        self._seed: int | None = None
        self._rng = random.Random()
        self._inventory_generated = False

    def configure_for_seed(self, seed: int | None) -> None:
        """Genera el inventario inicial usando una seed concreta."""
        self._seed = seed
        if seed is None:
            base_seed = random.randrange(1 << 30)
        else:
            base_seed = int(seed)
        self._rng = random.Random(base_seed ^ 0xBADC0FFE)
        self.items = self._build_inventory()
        self.selected = 0
        self.hover_index = None
        self._inventory_generated = True

    def rotate_inventory(self) -> None:
        """Compatibilidad: asegura que exista inventario pero no lo rerolla."""
        self.ensure_inventory()

    def ensure_inventory(self) -> None:
        if self.items or self._inventory_generated:
            return
        if self._seed is None:
            self.configure_for_seed(None)
        else:
            self.configure_for_seed(self._seed)

    def _build_inventory(self) -> list[dict]:
        available = list(self.catalog)
        weights = [float(entry.get("weight", 1.0)) for entry in available]
        items: list[dict] = []
        while available and len(items) < self.MAX_ITEMS:
            choice = self._rng.choices(available, weights=weights, k=1)[0]
            idx = available.index(choice)
            entry = {k: v for k, v in choice.items() if k != "weight"}
            items.append(entry)
            available.pop(idx)
            weights.pop(idx)
        if not items:
            items = [{k: v for k, v in entry.items() if k != "weight"} for entry in self.catalog]
        return items

        # rng propio para fijar inventario por seed
        self._seed: int | None = None
        self._rng = random.Random()
        self._inventory_generated = False

    def configure_for_seed(self, seed: int | None) -> None:
        """Genera el inventario inicial usando una seed concreta."""
        self._seed = seed
        if seed is None:
            base_seed = random.randrange(1 << 30)
        else:
            base_seed = int(seed)
        self._rng = random.Random(base_seed ^ 0xBADC0FFE)
        self.items = self._build_inventory()
        self.selected = 0
        self.hover_index = None
        self._inventory_generated = True

    def rotate_inventory(self) -> None:
        """Compatibilidad: asegura que exista inventario pero no lo rerolla."""
        self.ensure_inventory()

    def ensure_inventory(self) -> None:
        if self.items or self._inventory_generated:
            return
        if self._seed is None:
            self.configure_for_seed(None)
        else:
            self.configure_for_seed(self._seed)

    def _build_inventory(self) -> list[dict]:
        available = list(self.catalog)
        weights = [float(entry.get("weight", 1.0)) for entry in available]
        items: list[dict] = []
        while available and len(items) < self.MAX_ITEMS:
            choice = self._rng.choices(available, weights=weights, k=1)[0]
            idx = available.index(choice)
            entry = {k: v for k, v in choice.items() if k != "weight"}
            items.append(entry)
            available.pop(idx)
            weights.pop(idx)
        if not items:
            items = [{k: v for k, v in entry.items() if k != "weight"} for entry in self.catalog]
        return items

    def open(self, cx, cy):
        self.ensure_inventory()
        self.active = True
        # centrar sobre el mundo
        self.rect.center = (cx, cy)
        self.hover_index = None
        if self.items:
            self.selected = min(self.selected, len(self.items) - 1)
        else:
            self.selected = 0

    def close(self):
        self.active = False
        self.hover_index = None

    def update_hover(self, mouse_pos):
        if not self.active:
            self.hover_index = None
            return
        self.hover_index = None
        for idx, rect in enumerate(self._item_hitboxes):
            if rect.collidepoint(mouse_pos):
                self.hover_index = idx
                self.selected = idx
                break

    def handle_click(self, mouse_pos, player):
        """Procesa un click izquierdo dentro de la tienda."""
        if not self.active:
            return False, ""

        # Click fuera de la ventana = cerrar
        if not self.rect.collidepoint(mouse_pos):
            self.close()
            return False, ""

        for idx, rect in enumerate(self._item_hitboxes):
            if rect.collidepoint(mouse_pos):
                if self.selected != idx:
                    self.selected = idx
                    self.hover_index = idx
                    return False, ""
                return self.try_buy(player)

        return False, ""

    def move_selection(self, dy):
        if not self.active or not self.items:
            return
        self.selected = (self.selected + dy) % len(self.items)
        self.hover_index = self.selected

    def try_buy(self, player):
        """Aplica compra si hay oro suficiente y devuelve (comprado: bool, msg: str)."""
        if not self.active or not self.items:
            return False, ""
        item = self.items[self.selected]
        price = max(0, int(item.get("price", 0)))
        gold = getattr(player, "gold", 0)
        if gold < price:
            return False, "No tienes suficiente oro."

        if item["type"] == "weapon" and hasattr(player, "has_weapon"):
            if player.has_weapon(item["id"]):
                return False, "Ya tienes esta arma."

        # Cobro
        setattr(player, "gold", gold - price)
        if price > 0 and callable(self._on_gold_spent):
            try:
                self._on_gold_spent(price)
            except Exception:
                pass

        # Aplicación del efecto
        applied = apply_reward_entry(player, item)
        name = item.get("name", "Artículo")
        self.items.pop(self.selected)
        if self.items:
            self.selected %= len(self.items)
            self.hover_index = self.selected
        else:
            self.selected = 0
            self.hover_index = None
        return True, f"Compraste: {name}"

    # --- Efectos concretos ---

    def draw(self, surface):
        if not self.active:
            return
        # marco
        pygame.draw.rect(surface, (20, 20, 24), self.rect)
        pygame.draw.rect(surface, (240, 220, 120), self.rect, 2)

        # título
        title = self.font.render("TIENDA", True, (255, 240, 180))
        surface.blit(title, (self.rect.x + 12, self.rect.y + 8))

        # lista
        y = self.rect.y + 36
        self._item_hitboxes = []
        for idx, it in enumerate(self.items):
            item_rect = pygame.Rect(self.rect.x + 12, y - 4, self.rect.width - 24, 22)
            self._item_hitboxes.append(item_rect)

            is_selected = idx == self.selected
            is_hover = idx == self.hover_index

            if is_selected:
                pygame.draw.rect(surface, (65, 60, 100), item_rect)
            elif is_hover:
                pygame.draw.rect(surface, (50, 45, 75), item_rect)

            line = f"{it['name']}  -  {it['price']} oro"
            color = (255, 240, 180) if is_selected else (235, 235, 235)
            if is_hover and not is_selected:
                color = (255, 255, 255)
            txt = self.font.render(line, True, color)
            surface.blit(txt, (self.rect.x + 18, y))
            y += 24
