# CODIGO/Shop.py
import random
import pygame

class Shop:
    WIDTH, HEIGHT = 320, 240
    MAX_ITEMS = 6

    def __init__(self, font=None):
        self.catalog = [
            {"name": "Pistolas dobles", "price": 65, "type": "weapon", "id": "dual_pistols", "weight": 0.8},
            {"name": "Rifle ligero", "price": 82, "type": "weapon", "id": "light_rifle", "weight": 0.8},
            {"name": "Escopeta salva arcana", "price": 105, "type": "weapon", "id": "arcane_salvo", "weight": 0.6},
            {"name": "Rifle de pulsos", "price": 98, "type": "weapon", "id": "pulse_rifle", "weight": 0.6},
            {"name": "Guantes tesla", "price": 86, "type": "weapon", "id": "tesla_gloves", "weight": 0.6},
            {"name": "Carabina incandescente", "price": 110, "type": "weapon", "id": "ember_carbine", "weight": 0.5},
            {"name": "Vida extra (+1)", "price": 38, "type": "upgrade", "id": "hp_up", "weight": 4},
            {"name": "Aumento de velocidad (+5%)", "price": 32, "type": "upgrade", "id": "spd_up", "weight": 3},
            {"name": "Blindaje reforzado (+1 golpe)", "price": 64, "type": "upgrade", "id": "armor_up", "weight": 2},
            {"name": "Talismán de recarga (-10%)", "price": 56, "type": "upgrade", "id": "cdr_charm", "weight": 3},
            {"name": "Manual de puntería (-12% cd)", "price": 68, "type": "upgrade", "id": "cdr_core", "weight": 2},
            {"name": "Botas relámpago (+10% sprint)", "price": 52, "type": "upgrade", "id": "sprint_core", "weight": 3},
            {"name": "Condensador de fase (-15% dash)", "price": 70, "type": "upgrade", "id": "dash_core", "weight": 2},
            {"name": "Impulso cinético (+duración dash)", "price": 64, "type": "upgrade", "id": "dash_drive", "weight": 2},
            {"name": "Botiquín de campaña (+2 HP)", "price": 34, "type": "consumable", "id": "heal_medium", "amount": 2, "weight": 4},
            {"name": "Botiquín de nanobots (curación total)", "price": 85, "type": "consumable", "id": "heal_full", "weight": 1},
            {
                "name": "Kit de incursión",
                "price": 58,
                "type": "bundle",
                "contents": [
                    {"type": "gold", "amount": 45},
                    {"type": "heal", "amount": 1},
                    {"type": "upgrade", "id": "spd_up"},
                ],
                "weight": 2,
            },
            {
                "name": "Paquete de reconocimiento",
                "price": 62,
                "type": "bundle",
                "contents": [
                    {"type": "gold", "amount": 35},
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

        # ventana
        self.rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        self._item_hitboxes: list[pygame.Rect] = []

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
        gold = getattr(player, "gold", 0)
        if gold < item["price"]:
            return False, "No tienes suficiente oro."

        if item["type"] == "weapon" and hasattr(player, "has_weapon"):
            if player.has_weapon(item["id"]):
                return False, "Ya tienes esta arma."

        # Cobro
        setattr(player, "gold", gold - item["price"])

        # Aplicación del efecto
        applied = False
        if item["type"] == "weapon":
            applied = self._apply_weapon(player, item["id"])
        elif item["type"] == "upgrade":
            applied = self._apply_upgrade(player, item["id"])
        elif item["type"] == "consumable":
            applied = self._apply_consumable(player, item.get("id"), item)
        elif item["type"] == "bundle":
            applied = self._apply_bundle(player, item)
        elif item["type"] == "gold":
            applied = self._apply_gold(player, item.get("amount", 0))
        elif item["type"] == "heal":
            applied = self._heal_player(player, int(item.get("amount", 0)))
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

    def _apply_weapon(self, player, wid):
        # Si tienes un sistema de armas, llama tu método real:
        # player.equip_weapon(wid)
        unlock = getattr(player, "unlock_weapon", None)
        if callable(unlock):
            return bool(unlock(wid, auto_equip=True))
        equip = getattr(player, "equip_weapon", None)
        if callable(equip):
            equip(wid)
            return True
        setattr(player, "current_weapon", wid)
        return True

    def _apply_upgrade(self, player, uid):
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

    def _apply_consumable(self, player, cid, item) -> bool:
        if not cid:
            return False
        if cid == "heal_full":
            max_hp = getattr(player, "max_hp", getattr(player, "hp", 1))
            setattr(player, "hp", max_hp)
            if hasattr(player, "_hits_taken_current_life"):
                setattr(player, "_hits_taken_current_life", 0)
            return True
        if cid == "heal_medium":
            amount = int(item.get("amount", 2) or 2)
            return self._heal_player(player, amount)
        if cid == "heal_small":
            amount = int(item.get("amount", 1) or 1)
            return self._heal_player(player, amount)
        if cid == "life_refill":
            max_lives = getattr(player, "max_lives", getattr(player, "lives", 1))
            setattr(player, "lives", max_lives)
            return True
        return False

    def _apply_bundle(self, player, bundle: dict) -> bool:
        contents = bundle.get("contents") or []
        applied_any = False
        for entry in contents:
            if not isinstance(entry, dict):
                continue
            applied_any = self._apply_reward_entry(player, entry) or applied_any
        return applied_any

    def _apply_reward_entry(self, player, entry: dict) -> bool:
        rtype = entry.get("type")
        if rtype == "gold":
            return self._apply_gold(player, entry.get("amount", 0))
        if rtype == "heal":
            return self._heal_player(player, int(entry.get("amount", 0)))
        if rtype == "upgrade":
            return self._apply_upgrade(player, entry.get("id"))
        if rtype == "weapon":
            wid = entry.get("id")
            if not wid:
                return False
            return self._apply_weapon(player, wid)
        if rtype == "consumable":
            return self._apply_consumable(player, entry.get("id"), entry)
        if rtype == "bundle":
            return self._apply_bundle(player, entry)
        return False

    def _apply_gold(self, player, amount) -> bool:
        amount = int(amount)
        if amount <= 0:
            return False
        current = getattr(player, "gold", 0)
        setattr(player, "gold", current + amount)
        return True

    def _heal_player(self, player, amount: int) -> bool:
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
