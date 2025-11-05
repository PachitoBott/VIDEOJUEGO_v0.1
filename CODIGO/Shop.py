# CODIGO/Shop.py
import random
import pygame

class Shop:
    WIDTH, HEIGHT = 320, 240
    MAX_ITEMS = 6

    def __init__(self, font=None):
        self.catalog = [
            {"name": "Pistolas dobles", "price": 65, "type": "weapon", "id": "dual_pistols", "weight": 1},
            {"name": "Rifle ligero", "price": 80, "type": "weapon", "id": "light_rifle", "weight": 1},
            {"name": "Escopeta salva arcana", "price": 95, "type": "weapon", "id": "arcane_salvo", "weight": 1},
            {"name": "Rifle de pulsos", "price": 90, "type": "weapon", "id": "pulse_rifle", "weight": 1},
            {"name": "Guantes tesla", "price": 78, "type": "weapon", "id": "tesla_gloves", "weight": 1},
            {"name": "Vida extra (+1)", "price": 35, "type": "upgrade", "id": "hp_up", "weight": 4},
            {"name": "Aumento de velocidad (+5%)", "price": 30, "type": "upgrade", "id": "spd_up", "weight": 3},
            {"name": "Blindaje reforzado (+1 golpe)", "price": 60, "type": "upgrade", "id": "armor_up", "weight": 2},
            {"name": "Talismán de recarga (-10%)", "price": 52, "type": "upgrade", "id": "cdr_charm", "weight": 3},
        ]
        self.items: list[dict] = []
        self.active = False
        self.selected = 0
        self.hover_index = None
        self.font = font or pygame.font.SysFont(None, 18)

        # ventana
        self.rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        self._item_hitboxes: list[pygame.Rect] = []
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

    def open(self, cx, cy):
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
        if not self.active: return
        self.selected = (self.selected + dy) % len(self.items)
        self.hover_index = self.selected

    def try_buy(self, player):
        """Aplica compra si hay oro suficiente y devuelve (comprado: bool, msg: str)."""
        if not self.active: 
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
        if item["type"] == "weapon":
            self._apply_weapon(player, item["id"])
        elif item["type"] == "upgrade":
            self._apply_upgrade(player, item["id"])
        return True, f"Compraste: {item['name']}"

    # --- Efectos concretos ---
    def _apply_weapon(self, player, wid):
        # Si tienes un sistema de armas, llama tu método real:
        # player.equip_weapon(wid)
        unlock = getattr(player, "unlock_weapon", None)
        if callable(unlock):
            unlock(wid, auto_equip=True)
        else:
            equip = getattr(player, "equip_weapon", None)
            if callable(equip):
                equip(wid)
            else:
                setattr(player, "current_weapon", wid)

    def _apply_upgrade(self, player, uid):
        if uid == "hp_up":
            max_lives = getattr(player, "max_lives", getattr(player, "lives", 1))
            lives = getattr(player, "lives", max_lives)
            max_lives += 1
            lives = min(lives + 1, max_lives)
            setattr(player, "max_lives", max_lives)
            setattr(player, "lives", lives)
        elif uid == "spd_up":
            speed = getattr(player, "speed", 1.0)
            setattr(player, "speed", speed * 1.05)
        elif uid == "armor_up":
            max_hp = getattr(player, "max_hp", getattr(player, "hp", 3))
            hp = getattr(player, "hp", max_hp)
            max_hp += 1
            hp = min(hp + 1, max_hp)
            setattr(player, "max_hp", max_hp)
            setattr(player, "hp", hp)
            if hasattr(player, "_hits_taken_current_life"):
                hits_taken = max(0, max_hp - hp)
                setattr(player, "_hits_taken_current_life", hits_taken)
        elif uid == "cdr_charm":
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
