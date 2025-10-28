import math
import pygame

from Entity import Entity
from Config import CFG
from Weapons import WeaponFactory


class Player(Entity):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, w=12, h=12, speed=120.0)
        self.gold = 0
        self.cooldown_scale = 1.0
        self._weapon_factory = WeaponFactory()
        self._owned_weapons: set[str] = set()
        self.weapon_id: str | None = None
        self.weapon = None
        self.reset_loadout()

    def update(self, dt: float, room) -> None:
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        mag = math.hypot(dx, dy)
        if mag > 0: dx, dy = dx / mag, dy / mag
        self.move(dx, dy, dt, room)

        if self.weapon:
            self.weapon.tick(dt)

    def try_shoot(self, mouse_world_pos, out_projectiles) -> None:
        """Dispara hacia mouse si se pulsa y cooldown listo."""
        if not self.weapon or not self.weapon.can_fire():
            return
        mouse_pressed = pygame.mouse.get_pressed(3)[0]  # botón izquierdo
        if not mouse_pressed:
            return

        mx, my = mouse_world_pos
        # origen: centro del jugador
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        created = self.weapon.fire((cx, cy), (mx, my))
        if not created:
            return
        adder = getattr(out_projectiles, "add", None)
        for bullet in created:
            if callable(adder):
                adder(bullet)
            else:
                out_projectiles.append(bullet)

    def draw(self, surf):
        pygame.draw.rect(surf, CFG.COLOR_PLAYER, self.rect())

    # ------------------------------------------------------------------
    # Armas
    # ------------------------------------------------------------------
    def reset_loadout(self) -> None:
        """Restablece el arma inicial al comenzar una nueva partida."""
        self._owned_weapons.clear()
        self.cooldown_scale = 1.0
        self._grant_weapon("short_rifle")
        self.equip_weapon("short_rifle")

    def has_weapon(self, weapon_id: str) -> bool:
        return weapon_id in self._owned_weapons

    def unlock_weapon(self, weapon_id: str, auto_equip: bool = True) -> bool:
        """Añade el arma al inventario. Devuelve True si era nueva."""
        if weapon_id not in self._weapon_factory:
            return False
        is_new = weapon_id not in self._owned_weapons
        self._grant_weapon(weapon_id)
        if auto_equip:
            self.equip_weapon(weapon_id)
        return is_new

    def equip_weapon(self, weapon_id: str) -> None:
        if weapon_id not in self._owned_weapons:
            return
        self.weapon = self._weapon_factory.create(weapon_id, cooldown_scale=self.cooldown_scale)
        self.weapon_id = weapon_id

    def _grant_weapon(self, weapon_id: str) -> None:
        if weapon_id in self._weapon_factory:
            self._owned_weapons.add(weapon_id)

    # -------------------- Modificadores persistentes -------------------
    def refresh_weapon_modifiers(self) -> None:
        """Reaplica mejoras acumuladas al arma equipada."""
        if not self.weapon:
            return
        setter = getattr(self.weapon, "set_cooldown_scale", None)
        if callable(setter):
            setter(self.cooldown_scale)
