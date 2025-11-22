from __future__ import annotations

import math
import random
from typing import Callable

import pygame

from Config import CFG
from Enemy import CHASE, WANDER, Enemy, FastChaserEnemy
from Projectile import Projectile
from enemy_sprites import LayeredBossAnimator, load_boss_animation_layers

# Ajustes rápidos de hitbox por tipo de boss. Cambia estos números para mover el
# collider sin tener que buscar en el código: reduce en píxeles los lados o
# porcentajes del sprite y aplica un desplazamiento vertical opcional.
#
# side_trim_pct / top_trim_pct / bottom_trim_pct recortan el ancho/alto usando
# porcentajes del tamaño del sprite. También se respeta un mínimo en píxeles
# para evitar hitbox de tamaño 0.
#
# y_offset añade un desplazamiento final (positivo = baja el collider). Es el
# valor más directo para subir/bajar el hitbox completo.
BOSS_COLLIDER_PRESETS: dict[str, dict[str, float | int]] = {
    "default": {
        "min_width": 12,
        "min_height": 12,
        "side_trim_pct": 0.08,
        "top_trim_pct": 0.22,
        "bottom_trim_pct": 0.10,
        "min_side_trim": 4,
        "min_top_trim": 10,
        "min_bottom_trim": 4,
        "y_offset": 0.0,
    },
    # Boss de las moscas y seguridad comparten la misma forma. Ajusta aquí los
    # recortes laterales/superiores y el sesgo hacia abajo.
    "boss_core": {
        "min_width": 12,
        "min_height": 12,
        "side_trim_pct": 0.10,
        "top_trim_pct": 0.36,
        "bottom_trim_pct": 0.12,
        "min_side_trim": 6,
        "min_top_trim": 18,
        "min_bottom_trim": 5,
        "downward_bias_pct": 0.12,
        "downward_bias_min": 6.0,
        "y_offset": 0.0,
    },
    "boss_security": {
        "min_width": 12,
        "min_height": 12,
        "side_trim_pct": 0.10,
        "top_trim_pct": 0.36,
        "bottom_trim_pct": 0.12,
        "min_side_trim": 6,
        "min_top_trim": 18,
        "min_bottom_trim": 5,
        "downward_bias_pct": 0.12,
        "downward_bias_min": 6.0,
        "y_offset": 0.0,
    },
}


class BossEnemy(Enemy):
    """Base genérica para bosses con fases y efectos de suelo."""

    SPRITE_VARIANT = "boss_core"
    _CANONICAL_COLLIDER: tuple[float, float, float] | None = None

    def __init__(self, x: float, y: float, *, max_hp: int = 50, gold_reward: int = 60) -> None:
        super().__init__(x, y, hp=max_hp, gold_reward=gold_reward)
        self.max_hp = max_hp
        self.hp = self.max_hp
        self.phase = 1
        self.enraged = False
        self.is_boss = True
        self.contact_damage = 2
        self.detect_radius = 9999.0
        self.lose_radius = 9999.0
        self.reaction_delay = 0.0
        self.telegraphs: list[dict] = []
        self.puddles: list[dict] = []
        self._player_rect_cache: pygame.Rect | None = None
        self._phase_thresholds = (0.6, 0.3)
        self._tracked_room = None
        # Animación en capas (piernas/torso + muerte completa)
        self.animations = load_boss_animation_layers(self.sprite_variant)
        self.animator = LayeredBossAnimator(
            self.animations,
            leg_fps={"idle": 5.0, "run": 10.0},
            torso_fps={
                "idle": 5.0,
                "shoot1": 10.0,
                "shoot2": 12.0,
                "shoot3": 10.0,
            },
            default_fps=8.0,
            death_fps=12.0,
        )
        # Ajustar el collider al tamaño real del sprite y mantenerlo centrado
        fallback_w, fallback_h = self.animations.fallback.get_size()
        if fallback_w > 0 and fallback_h > 0:
            self._fit_collider_to_sprite(fallback_w, fallback_h)

    def _fit_collider_to_sprite(self, sprite_w: int, sprite_h: int) -> None:
        """Redimensiona el hitbox según el sprite actual.

        El boss de las moscas tiene mucha decoración en la parte superior; se
        recorta más por arriba y ligeramente por los lados para que el collider
        se sienta justo.
        """

        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        profile_key = self.sprite_variant if self.sprite_variant in BOSS_COLLIDER_PRESETS else "default"
        profile = BOSS_COLLIDER_PRESETS.get(profile_key, BOSS_COLLIDER_PRESETS["default"])

        width = sprite_w
        height = sprite_h
        y_offset = float(profile.get("y_offset", 0.0))

        side_trim_pct = float(profile.get("side_trim_pct", 0.0))
        top_trim_pct = float(profile.get("top_trim_pct", 0.0))
        bottom_trim_pct = float(profile.get("bottom_trim_pct", 0.0))
        side_trim = max(int(width * side_trim_pct), int(profile.get("min_side_trim", 0)))
        top_trim = max(int(height * top_trim_pct), int(profile.get("min_top_trim", 0)))
        bottom_trim = max(int(height * bottom_trim_pct), int(profile.get("min_bottom_trim", 0)))

        width = max(int(profile.get("min_width", 1)), width - side_trim * 2)
        height = max(int(profile.get("min_height", 1)), height - (top_trim + bottom_trim))

        downward_bias_pct = float(profile.get("downward_bias_pct", 0.0))
        downward_bias_min = float(profile.get("downward_bias_min", 0.0))
        downward_bias = max(downward_bias_min, height * downward_bias_pct)
        y_offset += (top_trim - bottom_trim) / 2 + downward_bias

        shared_hitbox_variants = {"boss_core", "boss_security"}
        if profile_key in shared_hitbox_variants:
            if BossEnemy._CANONICAL_COLLIDER is None:
                BossEnemy._CANONICAL_COLLIDER = (width, height, y_offset)
            else:
                width, height, y_offset = BossEnemy._CANONICAL_COLLIDER

        self.w = width
        self.h = height
        self.x = cx - self.w / 2
        self.y = cy - self.h / 2 + y_offset

    def on_spawn(self, room) -> None:
        self._tracked_room = room

    def update(self, dt: float, player, room) -> None:
        self._tracked_room = room
        self._player_rect_cache = self._player_rect(player)
        self._update_phase_state()
        super().update(dt, player, room)
        self._update_telegraphs(dt, player)
        self._update_puddles(dt, player)

    def on_phase_changed(self, new_phase: int) -> None:  # pragma: no cover - gancho opcional
        self.enraged = new_phase >= 3

    def draw_floor_effects(self, surface: pygame.Surface) -> None:
        for entry in self.telegraphs:
            rect: pygame.Rect = entry["rect"]
            duration = max(0.01, entry.get("duration", 0.8))
            alpha = int(60 + 160 * (entry["timer"] / duration))
            color = entry.get("color", (255, 80, 80, 140))
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((*color[:3], min(255, max(0, alpha))))
            surface.blit(overlay, rect.topleft)
            pygame.draw.rect(surface, (255, 200, 200), rect, 2)
        for puddle in self.puddles:
            rect: pygame.Rect = puddle["rect"]
            color = puddle.get("color", (120, 40, 40, 140))
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((*color[:3], color[3] if len(color) > 3 else 150))
            surface.blit(overlay, rect.topleft)
            pygame.draw.rect(surface, (255, 180, 120), rect, 1)

    def draw(self, surf: pygame.Surface) -> None:
        legs, torso = self.animator.current_surfaces()
        if not self._facing_right:
            legs = pygame.transform.flip(legs, True, False)
            if torso:
                torso = pygame.transform.flip(torso, True, False)

        center = self.rect().center
        leg_dest = legs.get_rect(center=center)
        surf.blit(legs, leg_dest)

        if torso is not None:
            torso_dest = torso.get_rect(center=center)
            surf.blit(torso, torso_dest)

        if CFG.DEBUG_DRAW_BOSS_HITBOX:
            collider_rect = self.rect()
            overlay = pygame.Surface(collider_rect.size, pygame.SRCALPHA)
            overlay.fill((255, 70, 70, 90))
            surf.blit(overlay, collider_rect.topleft)
            pygame.draw.rect(surf, (255, 50, 50), collider_rect, 2)

        if CFG.DEBUG_DRAW_BOSS_HITBOX_LAYOUT:
            self._draw_hitbox_layout(surf, leg_dest, torso_dest)

    def _draw_hitbox_layout(
        self,
        surf: pygame.Surface,
        leg_dest: pygame.Rect,
        torso_dest: pygame.Rect | None,
    ) -> None:
        collider_rect = self.rect()
        sprite_rect = leg_dest.union(torso_dest) if torso_dest is not None else leg_dest

        # Overlay directo en la escena
        pygame.draw.rect(surf, (0, 200, 255), sprite_rect, 1)
        pygame.draw.rect(surf, (255, 90, 90), collider_rect, 2)
        cx, cy = collider_rect.center
        pygame.draw.line(surf, (255, 90, 90), (cx - 6, cy), (cx + 6, cy))
        pygame.draw.line(surf, (255, 90, 90), (cx, cy - 6), (cx, cy + 6))

        # Diagrama miniatura para ver proporciones de hitbox vs sprite
        diagram_size = 104
        padding = 8
        base_max = max(1, max(sprite_rect.w, sprite_rect.h))
        scale = (diagram_size - padding * 2) / base_max

        def _scaled_rect(rect: pygame.Rect) -> pygame.Rect:
            return pygame.Rect(
                int(padding + (rect.x - sprite_rect.x) * scale),
                int(padding + (rect.y - sprite_rect.y) * scale),
                max(1, int(rect.w * scale)),
                max(1, int(rect.h * scale)),
            )

        diagram = pygame.Surface((diagram_size, diagram_size), pygame.SRCALPHA)
        diagram.fill((10, 10, 10, 180))
        mini_sprite = _scaled_rect(sprite_rect)
        mini_collider = _scaled_rect(collider_rect)
        pygame.draw.rect(diagram, (0, 200, 255, 180), mini_sprite, 1)
        pygame.draw.rect(diagram, (255, 90, 90, 220), mini_collider, 2)

        font = pygame.font.Font(None, 16)
        label_texts = [
            "Layout hitbox",
            f"Sprite: {sprite_rect.w}x{sprite_rect.h}",
            f"Collider: {self.w}x{self.h}",
        ]
        text_y = diagram_size - padding - len(label_texts) * 14
        for text in label_texts:
            rendered = font.render(text, True, (240, 240, 240))
            diagram.blit(rendered, (padding, text_y))
            text_y += 14

        diagram_dest = diagram.get_rect()
        diagram_dest.topleft = (sprite_rect.right + 10, sprite_rect.top - 6)

        # Evitar que salga completamente de pantalla
        surf_w, surf_h = surf.get_size()
        if diagram_dest.right > surf_w:
            diagram_dest.right = surf_w - 4
        if diagram_dest.top < 0:
            diagram_dest.top = 4
        if diagram_dest.bottom > surf_h:
            diagram_dest.bottom = surf_h - 4

        surf.blit(diagram, diagram_dest.topleft)

    def add_telegraph(
        self,
        rect: pygame.Rect,
        delay: float = 0.8,
        damage: int = 1,
        color: tuple[int, int, int, int] = (255, 80, 80, 150),
    ) -> None:
        self.telegraphs.append(
            {
                "rect": rect,
                "timer": delay,
                "duration": delay,
                "damage": max(1, damage),
                "color": color,
            }
        )

    def add_puddle(
        self,
        rect: pygame.Rect,
        duration: float = 4.0,
        damage: int = 1,
        tick_interval: float = 0.55,
        color: tuple[int, int, int, int] = (120, 0, 0, 180),
    ) -> None:
        self.puddles.append(
            {
                "rect": rect,
                "timer": duration,
                "damage": max(1, damage),
                "tick": tick_interval,
                "tick_timer": 0.0,
                "color": color,
            }
        )

    def _update_phase_state(self) -> None:
        ratio = 1.0 if self.max_hp <= 0 else max(0.0, self.hp / self.max_hp)
        new_phase = 1
        if ratio <= self._phase_thresholds[1]:
            new_phase = 3
        elif ratio <= self._phase_thresholds[0]:
            new_phase = 2
        if new_phase != self.phase:
            self.phase = new_phase
            self.on_phase_changed(new_phase)

    def _player_rect(self, player) -> pygame.Rect:
        if hasattr(player, "rect"):
            rect_callable = player.rect
            if isinstance(rect_callable, pygame.Rect):
                return rect_callable.copy()
            if callable(rect_callable):
                return rect_callable()
        width = int(getattr(player, "w", 16))
        height = int(getattr(player, "h", 16))
        return pygame.Rect(int(getattr(player, "x", 0)), int(getattr(player, "y", 0)), width, height)

    def _update_telegraphs(self, dt: float, player) -> None:
        if not self.telegraphs:
            return
        remaining: list[dict] = []
        for entry in self.telegraphs:
            entry["timer"] -= dt
            if entry["timer"] <= 0.0:
                self._trigger_telegraph(entry, player)
            else:
                remaining.append(entry)
        self.telegraphs = remaining

    def _trigger_telegraph(self, entry: dict, player) -> None:
        rect: pygame.Rect = entry["rect"]
        damage = entry.get("damage", 1)
        player_rect = self._player_rect_cache or self._player_rect(player)
        if player_rect.colliderect(rect):
            self._apply_damage_to_player(player, damage)

    def _update_puddles(self, dt: float, player) -> None:
        if not self.puddles:
            return
        player_rect = self._player_rect_cache or self._player_rect(player)
        survivors: list[dict] = []
        for puddle in self.puddles:
            puddle["timer"] -= dt
            puddle["tick_timer"] -= dt
            if puddle["timer"] <= 0:
                continue
            if player_rect.colliderect(puddle["rect"]) and puddle["tick_timer"] <= 0:
                self._apply_damage_to_player(player, puddle.get("damage", 1))
                puddle["tick_timer"] = puddle.get("tick", 0.5)
            survivors.append(puddle)
        self.puddles = survivors

    def _apply_damage_to_player(self, player, amount: int) -> None:
        taker: Callable[[int], bool] | None = getattr(player, "take_damage", None)
        if callable(taker):
            taker(amount)

    def _update_animation(self, dt: float) -> None:
        base_state = "idle"
        if not self._movement_locked and self.state in (WANDER, CHASE):
            base_state = "run"
        self.animator.set_leg_state(base_state)
        self.animator.set_torso_base_state("idle")
        self.animator.update(dt)

    def trigger_shoot_animation(self, variant: str = "shoot1") -> None:
        if self._is_dying:
            return
        self.animator.trigger_shoot(variant)


class CorruptedServerBoss(BossEnemy):
    SPRITE_VARIANT = "boss_core"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, max_hp=50, gold_reward=90)
        self.chase_speed = 35.0
        self.wander_speed = 0.0
        self.contact_damage = 2
        self.radial_cooldown = 1.8
        self.line_cooldown = 2.6
        self.minion_cooldown = 8.2
        self.telegraph_cooldown = 5.0
        self.laser_cooldown = 4.5
        self._radial_timer = 1.4
        self._line_timer = 1.8
        self._minion_timer = 6.0
        self._telegraph_timer = 3.5
        self._laser_timer = 2.5

    def on_phase_changed(self, new_phase: int) -> None:
        super().on_phase_changed(new_phase)
        if new_phase >= 3:
            self.chase_speed = 0.0

    def maybe_shoot(self, dt, player, room, out_bullets) -> bool:
        fired = False
        self._radial_timer -= dt
        self._line_timer -= dt
        self._minion_timer -= dt
        self._telegraph_timer -= dt
        self._laser_timer -= dt
        if self.phase == 1:
            if self._radial_timer <= 0.0:
                self._fire_radial(out_bullets, speed=140.0, bullets=18)
                self._radial_timer = self.radial_cooldown
                self.trigger_shoot_animation("shoot1")
                fired = True
            if self._line_timer <= 0.0:
                self._fire_line(player, out_bullets, speed=200.0, bullets=7)
                self._line_timer = self.line_cooldown
                self.trigger_shoot_animation("shoot2")
                fired = True
        elif self.phase == 2:
            if self._radial_timer <= 0.0:
                self._fire_radial(out_bullets, speed=200.0, bullets=12)
                self._radial_timer = max(0.9, self.radial_cooldown * 0.75)
                self.trigger_shoot_animation("shoot1")
                fired = True
            if self._line_timer <= 0.0:
                self._fire_line(player, out_bullets, speed=260.0, bullets=5)
                self._line_timer = max(1.2, self.line_cooldown * 0.7)
                self.trigger_shoot_animation("shoot2")
                fired = True
            if self._minion_timer <= 0.0:
                self._spawn_minions(room)
                self._minion_timer = self.minion_cooldown
                self.trigger_shoot_animation("shoot1")
                fired = True
        else:
            if self._telegraph_timer <= 0.0:
                self._spawn_telegraphs(player)
                self._telegraph_timer = max(2.5, self.telegraph_cooldown * 0.6)
                self.trigger_shoot_animation("shoot3")
                fired = True
            if self._laser_timer <= 0.0:
                self._fire_laser(player, out_bullets)
                self._laser_timer = max(2.8, self.laser_cooldown * 0.75)
                self.trigger_shoot_animation("shoot2")
                fired = True
        return fired

    def _fire_radial(self, out_bullets, *, bullets: int, speed: float) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        for i in range(bullets):
            angle = math.tau * (i / bullets)
            dx = math.cos(angle)
            dy = math.sin(angle)
            proj = Projectile(
                cx + dx * 12,
                cy + dy * 12,
                dx,
                dy,
                speed=speed,
                radius=4,
                color=(180, 220, 255),
            )
            out_bullets.add(proj)

    def _fire_line(self, player, out_bullets, *, speed: float, bullets: int) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        target = self._player_rect_cache or self._player_rect(player)
        tx, ty = target.center
        dx = tx - cx
        dy = ty - cy
        dist = math.hypot(dx, dy) or 1.0
        dx /= dist
        dy /= dist
        for i in range(bullets):
            offset = 14 + i * 12
            proj = Projectile(
                cx + dx * offset,
                cy + dy * offset,
                dx,
                dy,
                speed=speed,
                radius=4,
                color=(255, 160, 80),
            )
            out_bullets.add(proj)

    def _spawn_minions(self, room) -> None:
        if not hasattr(room, "enemies"):
            return
        count = random.randint(1, 3)
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            distance = random.randint(38, 72)
            px = cx + math.cos(angle) * distance
            py = cy + math.sin(angle) * distance
            minion = FastChaserEnemy(px - 6, py - 6)
            room.enemies.append(minion)

    def _spawn_telegraphs(self, player) -> None:
        target = self._player_rect_cache or self._player_rect(player)
        base_x, base_y = target.center
        for _ in range(3):
            offset_x = random.randint(-30, 30)
            offset_y = random.randint(-30, 30)
            size = CFG.TILE_SIZE + random.randint(-6, 12)
            rect = pygame.Rect(
                int(base_x + offset_x - size // 2),
                int(base_y + offset_y - size // 2),
                size,
                size,
            )
            self.add_telegraph(rect, delay=0.8, damage=2)

    def _fire_laser(self, player, out_bullets) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        target = self._player_rect_cache or self._player_rect(player)
        tx, ty = target.center
        dx = tx - cx
        dy = ty - cy
        dist = math.hypot(dx, dy) or 1.0
        dx /= dist
        dy /= dist
        for i in range(6):
            offset = 12 + i * 18
            proj = Projectile(
                cx + dx * offset,
                cy + dy * offset,
                dx,
                dy,
                speed=320.0,
                radius=3,
                color=(255, 255, 120),
            )
            out_bullets.add(proj)


class SecurityManagerBoss(BossEnemy):
    SPRITE_VARIANT = "boss_security"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, max_hp=65, gold_reward=110)
        self.chase_speed = 55.0
        self.contact_damage = 2
        self._dash_cooldown = 4.2
        self._dash_timer = 1.5
        self._dash_active = False
        self._dash_dir = pygame.Vector2(0, 0)
        self._dash_remaining = 0.0
        self._dash_windup = 0.0
        self._cone_timer = 1.0
        self._cone_cooldown = 2.6
        self._dash_origin: pygame.Vector2 | None = None

    def on_phase_changed(self, new_phase: int) -> None:
        super().on_phase_changed(new_phase)
        if new_phase >= 2:
            self.chase_speed = 70.0
            self._dash_cooldown = 3.5
            self._cone_cooldown = 2.0

    def update(self, dt: float, player, room) -> None:
        super().update(dt, player, room)
        self._update_dash(dt, room)

    def maybe_shoot(self, dt, player, room, out_bullets) -> bool:
        fired = False
        self._dash_timer = max(0.0, self._dash_timer - dt)
        self._cone_timer = max(0.0, self._cone_timer - dt)
        if not self._dash_active and self._dash_windup <= 0 and self._dash_timer <= 0:
            self._queue_dash(player)
            self._dash_timer = self._dash_cooldown
            fired = True
        elif self._cone_timer <= 0 and not self._dash_active:
            self._fire_cone(player, out_bullets)
            self._cone_timer = self._cone_cooldown
            fired = True
        return fired

    def _queue_dash(self, player) -> None:
        target = self._player_rect_cache or self._player_rect(player)
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        dx = target.centerx - cx
        dy = target.centery - cy
        dist = math.hypot(dx, dy) or 1.0
        dx /= dist
        dy /= dist
        self._dash_dir.update(dx, dy)
        self._dash_windup = 0.45 if self.phase == 1 else 0.28
        self._dash_remaining = 0.45 if self.phase == 1 else 0.55
        self.lock_movement(self._dash_windup + self._dash_remaining)
        self._dash_origin = pygame.Vector2(cx, cy)

    def _update_dash(self, dt: float, room) -> None:
        if self._dash_windup > 0:
            self._dash_windup = max(0.0, self._dash_windup - dt)
            if self._dash_windup == 0:
                self._dash_active = True
        if not self._dash_active:
            return
        dash_speed = 210.0 if self.phase == 1 else 250.0
        self.move(
            self._dash_dir.x,
            self._dash_dir.y,
            dt * (dash_speed / max(1e-6, self.speed)),
            room,
        )
        self._dash_remaining -= dt
        if self._dash_remaining <= 0:
            self._dash_active = False
            if self.phase >= 2:
                self._leave_puddle()

    def _leave_puddle(self) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        size = int(CFG.TILE_SIZE * 1.4)
        rect = pygame.Rect(int(cx - size // 2), int(cy - size // 2), size, size)
        self.add_puddle(rect, duration=4.5, damage=2, tick_interval=0.4)

    def _fire_cone(self, player, out_bullets) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        target = self._player_rect_cache or self._player_rect(player)
        tx, ty = target.center
        base_dx = tx - cx
        base_dy = ty - cy
        base_angle = math.atan2(base_dy, base_dx)
        spread = math.radians(55)
        pellets = 9
        speed = 210.0 if self.phase == 1 else 260.0
        for i in range(pellets):
            if pellets == 1:
                angle = base_angle
            else:
                t = i / (pellets - 1)
                angle = base_angle - spread / 2 + spread * t
            dx = math.cos(angle)
            dy = math.sin(angle)
            proj = Projectile(
                cx + dx * 14,
                cy + dy * 14,
                dx,
                dy,
                speed=speed,
                radius=4,
                color=(255, 120, 90),
            )
            out_bullets.add(proj)


BOSS_BLUEPRINTS = [CorruptedServerBoss, SecurityManagerBoss]

__all__ = [
    "BossEnemy",
    "CorruptedServerBoss",
    "SecurityManagerBoss",
    "BOSS_BLUEPRINTS",
]
