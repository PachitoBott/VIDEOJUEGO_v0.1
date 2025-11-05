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

        # --- Atributos de supervivencia y movilidad ---
        self.max_hp = 3
        self.hp = self.max_hp
        self.max_lives = CFG.PLAYER_START_LIVES
        self.lives = self.max_lives
        self.invulnerable_timer = 0.0
        self.post_hit_invulnerability = 0.45

        self.sprint_multiplier = 1.35

        self.dash_speed_multiplier = 3.25
        self.dash_duration = 0.18
        self.dash_cooldown = 0.75
        self.dash_iframe_duration = self.dash_duration + 0.08

        self._dash_timer = 0.0
        self._dash_cooldown_timer = 0.0
        self._dash_key_down = False
        self._dash_dir = (0.0, -1.0)
        self._last_move_dir = (0.0, -1.0)

        self.reset_loadout()

    def update(self, dt: float, room) -> None:
        keys = pygame.key.get_pressed()
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self._dash_timer = max(0.0, self._dash_timer - dt)
        self._dash_cooldown_timer = max(0.0, self._dash_cooldown_timer - dt)

        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        input_mag = math.hypot(dx, dy)
        if input_mag > 0:
            dx, dy = dx / input_mag, dy / input_mag
            self._last_move_dir = (dx, dy)

        dash_pressed = keys[pygame.K_SPACE]
        dash_just_pressed = dash_pressed and not self._dash_key_down
        self._dash_key_down = dash_pressed

        move_dx, move_dy = dx, dy
        speed_scale = 1.0

        dash_active = self._dash_timer > 0.0
        if dash_active:
            move_dx, move_dy = self._dash_dir
            speed_scale = self.dash_speed_multiplier
        else:
            if dash_just_pressed and self._dash_cooldown_timer <= 0.0:
                dash_dir = (dx, dy) if input_mag > 0 else self._last_move_dir
                dash_mag = math.hypot(*dash_dir)
                if dash_mag > 0:
                    dash_dir = (dash_dir[0] / dash_mag, dash_dir[1] / dash_mag)
                    self._dash_dir = dash_dir
                    self._dash_timer = self.dash_duration
                    move_dx, move_dy = dash_dir
                    speed_scale = self.dash_speed_multiplier
                    self._dash_cooldown_timer = self.dash_cooldown
                    self.invulnerable_timer = max(self.invulnerable_timer, self.dash_iframe_duration)
                    dash_active = True
            if not dash_active and input_mag > 0:
                if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                    speed_scale = self.sprint_multiplier

        if move_dx != 0 or move_dy != 0:
            mag = math.hypot(move_dx, move_dy)
            if mag > 0:
                move_dx /= mag
                move_dy /= mag

        self.move(move_dx * speed_scale, move_dy * speed_scale, dt, room)

        if self.weapon:
            self.weapon.tick(dt)

    # ------------------------------------------------------------------
    # Estado defensivo
    # ------------------------------------------------------------------
    def is_invulnerable(self) -> bool:
        return self.invulnerable_timer > 0.0

    def take_damage(self, amount: int) -> bool:
        """Aplica daño al jugador si no está en iframes. Devuelve True si impactó."""
        if amount <= 0 or self.is_invulnerable():
            return False
        self.hp = max(0, self.hp - amount)
        self.invulnerable_timer = max(self.invulnerable_timer, self.post_hit_invulnerability)
        return True

    def lose_life(self) -> bool:
        """Consume una vida. Devuelve True si aún quedan vidas disponibles."""
        if self.lives <= 0:
            return False
        self.lives -= 1
        return self.lives > 0

    def reset_lives(self) -> None:
        self.lives = self.max_lives

    def respawn(self) -> None:
        """Restaura la salud y otorga invulnerabilidad breve tras revivir."""
        self.hp = self.max_hp
        self.invulnerable_timer = max(self.invulnerable_timer, self.post_hit_invulnerability)
        self._dash_timer = 0.0
        self._dash_cooldown_timer = 0.0
        self._dash_key_down = False
        self._dash_dir = (0.0, -1.0)
        self._last_move_dir = (0.0, -1.0)

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
        self.hp = self.max_hp
        self.reset_lives()
        self.invulnerable_timer = 0.0
        self._dash_timer = 0.0
        self._dash_cooldown_timer = 0.0
        self._dash_key_down = False
        self._dash_dir = (0.0, -1.0)
        self._last_move_dir = (0.0, -1.0)
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
