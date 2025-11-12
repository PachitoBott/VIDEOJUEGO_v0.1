import math
from dataclasses import dataclass
from pathlib import Path

import pygame

from Entity import Entity
from Config import CFG
from Weapons import WeaponFactory


PLAYER_SPRITE_SIZE = (64, 64)
PLAYER_HITBOX_SIZE = (18, 24)
PLAYER_HITBOX_OFFSET = (23, 40)
PLAYER_SPRITE_CENTER_OFFSET_Y = (
    PLAYER_HITBOX_OFFSET[1] + PLAYER_HITBOX_SIZE[1] // 2 - PLAYER_SPRITE_SIZE[1] // 2
)


@dataclass
class FrameAnimation:
    frames: list[pygame.Surface]
    frame_time: float
    loop: bool
    index: int = 0
    timer: float = 0.0
    finished: bool = False

    def reset(self) -> None:
        self.index = 0
        self.timer = 0.0
        self.finished = False

    def set_frame_duration(self, frame_time: float) -> None:
        self.frame_time = max(0.01, frame_time)

    def update(self, dt: float) -> None:
        if self.finished or len(self.frames) <= 1:
            return
        self.timer += dt
        while self.timer >= self.frame_time:
            self.timer -= self.frame_time
            self.index += 1
            if self.index >= len(self.frames):
                if self.loop:
                    self.index = 0
                else:
                    self.index = len(self.frames) - 1
                    self.finished = True
                    break

    def current_frame(self) -> pygame.Surface:
        return self.frames[self.index]


@dataclass
class DashTrailSegment:
    pos: tuple[float, float]
    life: float


class Player(Entity):
    HITBOX_SIZE = PLAYER_HITBOX_SIZE

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, w=PLAYER_HITBOX_SIZE[0], h=PLAYER_HITBOX_SIZE[1], speed=120.0)
        self.gold = 0
        self.cooldown_scale = 1.0
        self._weapon_factory = WeaponFactory()
        self._owned_weapons: set[str] = set()
        self.weapon_id: str | None = None
        self.weapon = None
        self.cooldown_scale_base = 1.0
        self._cooldown_modifiers: dict[str, float] = {}
        self._upgrade_flags: set[str] = set()
        self.sprint_control_bonus = 0.0
        self._sprint_control_timer = 0.0
        self._is_sprinting = False
        self.phase_during_dash = False
        self.dash_core_bonus_window = 0.0
        self.dash_core_bonus_iframe = 0.0
        self._recent_enemy_shot_timer = 0.0
        self._was_dashing = False

        # --- Atributos de supervivencia y movilidad ---
        self.base_speed = self.speed
        self.base_max_hp = 3
        self.max_hp = self.base_max_hp
        self.hp = self.max_hp
        self.base_max_lives = CFG.PLAYER_START_LIVES
        self.max_lives = self.base_max_lives
        self.lives = self.max_lives
        self.invulnerable_timer = 0.0
        self.post_hit_invulnerability = 0.45
        # Conteo de golpes por vida (cada golpe equivale a 1 punto de vida perdido)
        self._hits_taken_current_life = 0

        self.sprint_multiplier = 1.35
        self.base_sprint_multiplier = self.sprint_multiplier

        self.dash_speed_multiplier = 3.25
        self.dash_duration = 0.18
        self.base_dash_duration = self.dash_duration
        self.dash_cooldown = 0.75
        self.base_dash_cooldown = self.dash_cooldown
        self.dash_iframe_duration = self.dash_duration + 0.08

        self._dash_timer = 0.0
        self._dash_cooldown_timer = 0.0
        self._dash_key_down = False
        self._dash_dir = (0.0, -1.0)
        self._last_move_dir = (0.0, -1.0)

        # Rastro visual del dash
        self.dash_trail_lifetime = 0.22
        self.dash_trail_interval = 0.02
        self.dash_trail_size = max(8, int(self.w * 0.75))
        self.dash_trail_vertical_offset = 14
        self._dash_trail_timer = 0.0
        self._dash_trail: list[DashTrailSegment] = []

        self._animations = self._build_animations()
        self._current_animation = "idle"
        self._animation_override: str | None = None
        self._was_reloading = False
        self._facing_left = False
        self._reload_key_down = False

        self.reset_loadout()

    def update(self, dt: float, room) -> None:
        keys = pygame.key.get_pressed()
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self._dash_timer = max(0.0, self._dash_timer - dt)
        self._dash_cooldown_timer = max(0.0, self._dash_cooldown_timer - dt)
        self._recent_enemy_shot_timer = max(0.0, self._recent_enemy_shot_timer - dt)
        self._sprint_control_timer = max(0.0, self._sprint_control_timer - dt)

        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        input_mag = math.hypot(dx, dy)
        if input_mag > 0:
            dx, dy = dx / input_mag, dy / input_mag
            self._last_move_dir = (dx, dy)

        reload_pressed = keys[pygame.K_r]
        if reload_pressed and not self._reload_key_down:
            self._try_manual_reload()
        self._reload_key_down = reload_pressed

        dash_pressed = keys[pygame.K_SPACE]
        dash_just_pressed = dash_pressed and not self._dash_key_down
        self._dash_key_down = dash_pressed

        move_dx, move_dy = dx, dy
        speed_scale = 1.0

        dash_active = self._dash_timer > 0.0
        sprinting_now = False
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
                    sprinting_now = True

        if sprinting_now and not self._is_sprinting:
            self._sprint_control_timer = max(self._sprint_control_timer, 1.0)

        if sprinting_now and self.sprint_control_bonus > 0.0 and self._sprint_control_timer > 0.0:
            speed_scale *= 1.0 + self.sprint_control_bonus

        self._update_facing(move_dx, dash_active)

        if move_dx != 0 or move_dy != 0:
            mag = math.hypot(move_dx, move_dy)
            if mag > 0:
                move_dx /= mag
                move_dy /= mag

        self.move(move_dx * speed_scale, move_dy * speed_scale, dt, room)

        self._update_dash_trail(dt, dash_active)

        if self.weapon:
            self.weapon.tick(dt)

        moving = dash_active or input_mag > 0
        self._update_animation(dt, moving)
        if self._was_dashing and not dash_active and self.dash_core_bonus_iframe > 0.0:
            if self._recent_enemy_shot_timer > 0.0:
                self.invulnerable_timer = max(0.0, self.invulnerable_timer) + self.dash_core_bonus_iframe
        self._was_dashing = dash_active
        self._is_sprinting = sprinting_now

    # ------------------------------------------------------------------
    # Estado defensivo
    # ------------------------------------------------------------------
    def is_invulnerable(self) -> bool:
        return self.invulnerable_timer > 0.0

    def is_phase_active(self) -> bool:
        return self.phase_during_dash and self._dash_timer > 0.0

    def take_damage(self, amount: int) -> bool:
        """Aplica daño al jugador si no está en iframes. Devuelve True si impactó."""
        if amount <= 0 or self.is_invulnerable():
            return False
        prev_hp = self.hp
        self.hp = max(0, self.hp - amount)
        self.invulnerable_timer = max(self.invulnerable_timer, self.post_hit_invulnerability)
        if prev_hp != self.hp:
            self._hits_taken_current_life = self.max_hp - self.hp
        return True

    def lose_life(self) -> bool:
        """Consume una vida. Devuelve True si aún quedan vidas disponibles."""
        if self.lives <= 0:
            return False
        self.lives -= 1
        return self.lives > 0

    def reset_lives(self) -> None:
        self.lives = self.max_lives

    def hits_taken_this_life(self) -> int:
        """Golpes recibidos en la vida actual (se resetea al revivir)."""
        return self._hits_taken_current_life

    def hits_remaining_this_life(self) -> int:
        """Golpes que aún se pueden resistir antes de perder la vida actual."""
        return max(0, self.max_hp - self._hits_taken_current_life)

    def respawn(self) -> None:
        """Restaura la salud y otorga invulnerabilidad breve tras revivir."""
        self.hp = self.max_hp
        self._hits_taken_current_life = 0
        self.invulnerable_timer = max(self.invulnerable_timer, self.post_hit_invulnerability)
        self._dash_timer = 0.0
        self._dash_cooldown_timer = 0.0
        self._dash_key_down = False
        self._dash_dir = (0.0, -1.0)
        self._last_move_dir = (0.0, -1.0)
        self._reload_key_down = False
        self._dash_trail.clear()
        self._dash_trail_timer = 0.0

    def try_shoot(self, mouse_world_pos, out_projectiles) -> None:
        """Dispara hacia mouse si se pulsa y cooldown listo."""
        if not self.weapon or not self.weapon.can_fire():
            return
        mouse_pressed = pygame.mouse.get_pressed(3)[0]  # botón izquierdo
        if not mouse_pressed:
            return

        mx, my = mouse_world_pos
        self._face_towards_x(mx)
        # origen: centro del jugador
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        created = self.weapon.fire((cx, cy), (mx, my))
        if not created:
            return
        self._start_shoot_animation()
        adder = getattr(out_projectiles, "add", None)
        for bullet in created:
            if callable(adder):
                adder(bullet)
            else:
                out_projectiles.append(bullet)

    def draw(self, surf):
        self._draw_dash_trail(surf)
        animation = self._animations[self._current_animation]
        sprite = self._prepare_sprite(animation.current_frame())
        sprite_rect = sprite.get_rect()
        sprite_rect.centerx = int(round(self.x + self.w / 2))
        sprite_rect.centery = int(round(self.y + self.h / 2 - PLAYER_SPRITE_CENTER_OFFSET_Y))
        surf.blit(sprite, sprite_rect)

    def _prepare_sprite(self, base_sprite: pygame.Surface) -> pygame.Surface:
        sprite = base_sprite
        if self._facing_left:
            sprite = pygame.transform.flip(sprite, True, False)
        return sprite

    def _update_facing(self, move_dx: float, dash_active: bool) -> None:
        horizontal = 0.0
        if dash_active:
            horizontal = self._dash_dir[0]
        elif abs(move_dx) > 1e-3:
            horizontal = move_dx
        elif abs(self._last_move_dir[0]) > 1e-3:
            horizontal = self._last_move_dir[0]

        if abs(horizontal) > 1e-3:
            self._facing_left = horizontal < 0
        else:
            self._update_facing_from_mouse()

    def _face_towards_x(self, target_x: float) -> None:
        cx = self.x + self.w / 2
        if abs(target_x - cx) < 0.5:
            return
        self._facing_left = target_x < cx

    def _update_facing_from_mouse(self) -> None:
        try:
            mx, _ = pygame.mouse.get_pos()
        except pygame.error:
            return
        scale = getattr(CFG, "SCREEN_SCALE", 1)
        scale = scale if scale else 1
        mx = mx / scale
        self._face_towards_x(mx)

    def _try_manual_reload(self) -> None:
        if not self.weapon:
            return
        if self.weapon.start_reload():
            self._start_reload_animation()

    # ------------------------------------------------------------------
    # Animaciones
    # ------------------------------------------------------------------
    def _build_animations(self) -> dict[str, FrameAnimation]:
        sprite_dir = Path(CFG.PLAYER_SPRITES_PATH) if CFG.PLAYER_SPRITES_PATH else None
        sprite_prefix = getattr(CFG, "PLAYER_SPRITE_PREFIX", "player")

        def load_surface(path: Path) -> pygame.Surface | None:
            try:
                image = pygame.image.load(path.as_posix()).convert_alpha()
            except (FileNotFoundError, pygame.error):
                return None
            expected_w, expected_h = PLAYER_SPRITE_SIZE
            if image.get_size() != PLAYER_SPRITE_SIZE:
                width, height = image.get_size()
                raise ValueError(
                    f"El sprite '{path.as_posix()}' debe medir {expected_w}x{expected_h} píxeles (actual {width}x{height})"
                )
            return image

        def load_animation(state: str, expected_frames: int) -> list[pygame.Surface]:
            if not sprite_dir:
                raise FileNotFoundError(
                    "Config.PLAYER_SPRITES_PATH no está definido; no se pueden cargar animaciones del jugador"
                )
            frames: list[pygame.Surface] = []
            if expected_frames <= 1:
                candidates = [
                    sprite_dir / f"{sprite_prefix}_{state}.png",
                    sprite_dir / f"{sprite_prefix}_{state}_0.png",
                ]
                for candidate in candidates:
                    surface = load_surface(candidate)
                    if surface is not None:
                        frames.append(surface)
                        return frames
                missing = " o ".join(candidate.as_posix() for candidate in candidates)
                raise FileNotFoundError(
                    f"No se encontró el sprite '{missing}' para la animación '{state}'"
                )
            for i in range(expected_frames):
                candidate = sprite_dir / f"{sprite_prefix}_{state}_{i}.png"
                surface = load_surface(candidate)
                if surface is None:
                    raise FileNotFoundError(
                        f"No se encontró el sprite '{candidate.as_posix()}' para la animación '{state}'"
                    )
                frames.append(surface)
            return frames

        idle_frames = load_animation("idle", 1)
        run_frames = load_animation("run", 4)
        reload_frames = load_animation("reload", 5)
        shoot_frames = load_animation("shoot", 4)

        animations = {
            "idle": FrameAnimation(idle_frames, frame_time=0.2, loop=False),
            "run": FrameAnimation(run_frames, frame_time=0.09, loop=True),
            "reload": FrameAnimation(reload_frames, frame_time=0.12, loop=False),
            "shoot": FrameAnimation(shoot_frames, frame_time=0.06, loop=False),
        }
        return animations

    def _set_current_animation(self, name: str, *, force_reset: bool = False) -> None:
        if self._current_animation != name:
            self._current_animation = name
            self._animations[name].reset()
        elif force_reset:
            self._animations[name].reset()

    def _start_shoot_animation(self) -> None:
        if self.weapon and self.weapon.is_reloading():
            return
        self._animation_override = "shoot"
        self._set_current_animation("shoot", force_reset=True)

    def _start_reload_animation(self) -> None:
        if not self.weapon:
            return
        anim = self._animations["reload"]
        anim.set_frame_duration(self.weapon.reload_time / max(1, len(anim.frames)))
        self._animation_override = "reload"
        self._set_current_animation("reload", force_reset=True)

    def _update_animation(self, dt: float, moving: bool) -> None:
        reloading = self.weapon.is_reloading() if self.weapon else False
        if reloading and not self._was_reloading:
            self._start_reload_animation()
        self._was_reloading = reloading

        active_name = self._animation_override
        if active_name is None:
            active_name = "run" if moving else "idle"
        self._set_current_animation(active_name)

        animation = self._animations[active_name]
        animation.update(dt)

        if self._animation_override == "shoot" and animation.finished:
            self._animation_override = None
        elif self._animation_override == "reload":
            if not reloading and animation.finished:
                self._animation_override = None

    def _update_dash_trail(self, dt: float, dash_active: bool) -> None:
        # Reducir vida de los rastros existentes
        for segment in self._dash_trail:
            segment.life -= dt
        self._dash_trail = [seg for seg in self._dash_trail if seg.life > 0.0]

        # Controlar el spawn de nuevos rastros mientras dura el dash
        self._dash_trail_timer = max(0.0, self._dash_trail_timer - dt)
        if dash_active and self._dash_trail_timer <= 0.0:
            self._dash_trail_timer = self.dash_trail_interval
            cx = self.x + self.w / 2
            cy = (
                self.y
                + self.h / 2
                - PLAYER_SPRITE_CENTER_OFFSET_Y
                + self.dash_trail_vertical_offset
            )
            self._dash_trail.append(DashTrailSegment(pos=(cx, cy), life=self.dash_trail_lifetime))

    def _draw_dash_trail(self, surf) -> None:
        if not self._dash_trail:
            return

        max_life = self.dash_trail_lifetime if self.dash_trail_lifetime > 0 else 0.0001
        size = self.dash_trail_size
        for segment in self._dash_trail:
            life = segment.life
            alpha = max(0, min(255, int(255 * (life / max_life))))
            trail_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            trail_surface.fill((255, 255, 255, alpha))
            pos_x, pos_y = segment.pos
            surf.blit(trail_surface, (pos_x - size / 2, pos_y - size / 2))

    # ------------------------------------------------------------------
    # Armas
    # ------------------------------------------------------------------
    def reset_loadout(self) -> None:
        """Restablece el arma inicial al comenzar una nueva partida."""
        self._owned_weapons.clear()
        self._upgrade_flags.clear()
        self._cooldown_modifiers.clear()
        self.cooldown_scale_base = 1.0
        self.cooldown_scale = 1.0
        self.speed = self.base_speed
        self.max_hp = self.base_max_hp
        self.hp = self.max_hp
        self.max_lives = self.base_max_lives
        self.reset_lives()
        self._hits_taken_current_life = 0
        self.invulnerable_timer = 0.0
        self._dash_timer = 0.0
        self._dash_cooldown_timer = 0.0
        self._dash_key_down = False
        self._dash_dir = (0.0, -1.0)
        self._last_move_dir = (0.0, -1.0)
        self._dash_trail.clear()
        self._dash_trail_timer = 0.0
        self.sprint_control_bonus = 0.0
        self._sprint_control_timer = 0.0
        self._is_sprinting = False
        self.phase_during_dash = False
        self.dash_core_bonus_window = 0.0
        self.dash_core_bonus_iframe = 0.0
        self._recent_enemy_shot_timer = 0.0
        self._was_dashing = False

        self.sprint_multiplier = self.base_sprint_multiplier
        self.dash_duration = self.base_dash_duration
        self.dash_cooldown = self.base_dash_cooldown
        self.dash_iframe_duration = self.dash_duration + 0.08
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

    # ------------------------- Gestion de upgrades --------------------
    def register_upgrade(self, upgrade_id: str) -> None:
        self._upgrade_flags.add(upgrade_id)

    def has_upgrade(self, upgrade_id: str) -> bool:
        return upgrade_id in self._upgrade_flags

    def set_cooldown_modifier(self, upgrade_id: str, multiplier: float) -> None:
        self._cooldown_modifiers[upgrade_id] = float(multiplier)
        self._recompute_cooldown_scale()

    def _recompute_cooldown_scale(self) -> None:
        scale = self.cooldown_scale_base
        for mult in self._cooldown_modifiers.values():
            scale *= mult
        scale = max(0.35, scale)
        self.cooldown_scale = scale
        self.refresh_weapon_modifiers()

    def notify_enemy_shot(self, window: float | None = None) -> None:
        if window is None:
            window = self.dash_core_bonus_window if self.dash_core_bonus_window > 0.0 else 0.15
        if window <= 0.0:
            return
        self._recent_enemy_shot_timer = max(self._recent_enemy_shot_timer, window)
