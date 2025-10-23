# CODIGO/Shop.py
import pygame

class Shop:
    WIDTH, HEIGHT = 320, 180

    def __init__(self, font=None):
        self.items = [
            # type: weapon|upgrade
            {"name": "Pistola Doble", "price": 50, "type": "weapon", "id": "dual_pistol"},
            {"name": "Rifle Ligero", "price": 65, "type": "weapon", "id": "light_rifle"},
            {"name": "Aumento de Vida (+1)", "price": 30, "type": "upgrade", "id": "hp_up"},
            {"name": "Aumento de Velocidad (+5%)", "price": 25, "type": "upgrade", "id": "spd_up"},
        ]
        self.active = False
        self.selected = 0
        self.font = font or pygame.font.SysFont(None, 18)

        # ventana
        self.rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)

    def open(self, cx, cy):
        self.active = True
        # centrar sobre el mundo
        self.rect.center = (cx, cy)

    def close(self):
        self.active = False

    def move_selection(self, dy):
        if not self.active: return
        self.selected = (self.selected + dy) % len(self.items)

    def try_buy(self, player):
        """Aplica compra si hay oro suficiente y devuelve (comprado: bool, msg: str)."""
        if not self.active: 
            return False, ""
        item = self.items[self.selected]
        gold = getattr(player, "gold", 0)
        if gold < item["price"]:
            return False, "No tienes suficiente oro."

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
        equip = getattr(player, "equip_weapon", None)
        if callable(equip):
            equip(wid)
        else:
            # Fallback no destructivo: setear atributo temporal
            setattr(player, "current_weapon", wid)

    def _apply_upgrade(self, player, uid):
        if uid == "hp_up":
            max_hp = getattr(player, "max_hp", getattr(player, "hp", 3))
            hp = getattr(player, "hp", max_hp)
            max_hp += 1
            hp = min(hp + 1, max_hp)
            setattr(player, "max_hp", max_hp)
            setattr(player, "hp", hp)
        elif uid == "spd_up":
            speed = getattr(player, "speed", 1.0)
            setattr(player, "speed", speed * 1.05)

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
        for idx, it in enumerate(self.items):
            line = f"{'>' if idx == self.selected else ' '} {it['name']}  -  {it['price']} oro"
            txt = self.font.render(line, True, (230, 230, 230))
            surface.blit(txt, (self.rect.x + 16, y))
            y += 24
