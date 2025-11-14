# CODIGO/Enemy.py
import math
import random
import pygame

from Entity import Entity
from Config import CFG
from Projectile import Projectile
from enemy_sprites import EnemyAnimator, load_enemy_animation_set

IDLE, WANDER, CHASE = 0, 1, 2

class Enemy(Entity):
    """Base con FSM + LoS. Subclases cambian stats/comportamientos."""

    SPRITE_VARIANT = "default"

    def __init__(self, x: float, y: float, hp: int = 3, gold_reward: int = 5) -> None:
        super().__init__(x, y, w=12, h=12, speed=40.0)
        self.hp = hp
        self.gold_reward = gold_reward

        # Estados y radios
        self.state = IDLE
        self.detect_radius = 110.0
        self.lose_radius = 130.0
        self._los_grace = 0.35  # “gracia” sin LoS antes de soltar persecución

        # Velocidades
        self.chase_speed = 70.0
        self.wander_speed = 50.0

        # Wander
        self.wander_time = 0.0
        self.wander_dir = (0.0, 0.0)

        # timers internos
        self._los_timer = 0.0
        self.reaction_delay = 0.35
        self.alert_timer = 0.0

        # Control de aturdimiento/knockback
        self.stun_timer = 0.0
        self._knockback_dir = (0.0, 0.0)
        self._knockback_speed = 0.0
        self.knockback_decay = 420.0

        # Daño por contacto (override en subclases que lo requieran)
        self.contact_damage = 0

        # Control de ralentizaciones
        self._slow_timer = 0.0
        self._slow_multiplier = 1.0

        # Animación
        self.animations = load_enemy_animation_set(self.SPRITE_VARIANT)
        self.animator = EnemyAnimator(
            self.animations,
            default_state="idle",
            fps_overrides={
                "idle": 5.0,
                "run": 10.0,
                "shoot": 8.0,
                "attack": 12.0,
                "death": 12.0,
            },
        )
        self._facing_right = True
        self._is_dying = False
        self._ready_to_remove = False

    def _center(self):
        return (self.x + self.w/2, self.y + self.h/2)

    # ---------- loop ----------
    def update(self, dt: float, player, room) -> None:
        if self._is_dying:
            self.animator.set_base_state("death")
            self.animator.update(dt)
            if self.animator.is_death_finished():
                self._ready_to_remove = True
            return
        self.alert_timer = max(0.0, self.alert_timer - dt)
        if self._slow_timer > 0.0:
            self._slow_timer = max(0.0, self._slow_timer - dt)
            if self._slow_timer <= 0.0:
                self._slow_multiplier = 1.0
        ex, ey = self._center()
        px, py = (player.x + player.w/2, player.y + player.h/2)

        dx, dy = (px - ex), (py - ey)
        dist   = math.hypot(dx, dy)
        has_los = room.has_line_of_sight(ex, ey, px, py)

        stunned = self.stun_timer > 0.0
        prev_state = self.state

        # Cambios de estado (LoS + histéresis)
        if self.state != CHASE:
            if dist <= self.detect_radius and has_los:
                self.state = CHASE
                self._los_timer = self._los_grace
        else:
            if has_los:
                self._los_timer = self._los_grace
            else:
                self._los_timer = max(0.0, self._los_timer - dt)
            if dist >= self.lose_radius or self._los_timer <= 0.0:
                self._pick_wander()
                self.state = WANDER

        if prev_state != CHASE and self.state == CHASE:
            self.alert_timer = max(self.alert_timer, self.reaction_delay)

        if stunned:
            self.stun_timer = max(0.0, self.stun_timer - dt)
            self._apply_knockback(dt, room)
            self._update_animation(dt)
            return

        self.stun_timer = max(0.0, self.stun_timer - dt)
        self._apply_knockback(dt, room)

        # Ejecutar estado
        if self.state == IDLE:
            self._update_idle(dt)
        elif self.state == WANDER:
            self._update_wander(dt, room)
        elif self.state == CHASE:
            self._update_chase(dt, room, dx, dy)

        self._update_animation(dt)

    def maybe_shoot(self, dt: float, player, room, out_bullets: list) -> bool:
        """Por defecto, los enemigos base NO disparan."""
        return False

    def is_stunned(self) -> bool:
        return self.stun_timer > 0.0

    def take_damage(
        self,
        amount: int,
        knockback_dir: tuple[float, float] | None = None,
        stun_duration: float = 0.22,
        knockback_strength: float = 150.0,
    ) -> bool:
        if self._is_dying:
            return False
        if amount > 0:
            self.hp -= amount
        alive = self.hp > 0
        if alive:
            if stun_duration > 0.0:
                self.stun_timer = max(self.stun_timer, stun_duration)
            if knockback_dir is not None and knockback_strength > 0.0:
                nx, ny = knockback_dir
                mag = math.hypot(nx, ny)
                if mag > 0.0:
                    self._knockback_dir = (nx / mag, ny / mag)
                    self._knockback_speed = max(self._knockback_speed, knockback_strength)
        else:
            self._begin_death()
        return self._is_dying

    def _apply_knockback(self, dt: float, room) -> None:
        if self._knockback_speed <= 0.0:
            return
        scale = self._knockback_speed / max(1e-6, self.speed)
        self.move(self._knockback_dir[0], self._knockback_dir[1], dt * scale, room)
        self._knockback_speed = max(0.0, self._knockback_speed - self.knockback_decay * dt)
        if self._knockback_speed <= 0.0:
            self._knockback_dir = (0.0, 0.0)

    def _begin_death(self) -> None:
        if self._is_dying:
            return
        self._is_dying = True
        self.hp = 0
        self.animator.trigger_death()

    def _movement_speed_factor(self) -> float:
        return self._slow_multiplier if self._slow_timer > 0.0 else 1.0

    def apply_slow(self, slow_fraction: float, duration: float) -> None:
        slow_fraction = max(0.0, min(0.95, slow_fraction))
        target_multiplier = max(0.05, 1.0 - slow_fraction)
        self._slow_multiplier = min(self._slow_multiplier, target_multiplier)
        self._slow_timer = max(self._slow_timer, max(0.0, duration))

    # ---------- estados ----------
    def _update_idle(self, dt: float) -> None:
        if random.random() < 0.005:
            self._pick_wander()
            self.state = WANDER

    def _pick_wander(self) -> None:
        ang = random.uniform(0, math.tau)
        self.wander_dir = (math.cos(ang), math.sin(ang))
        self.wander_time = random.uniform(0.6, 1.2)

    def _update_wander(self, dt: float, room) -> None:
        vx, vy = self.wander_dir
        speed_factor = self._movement_speed_factor()
        self._update_facing(vx)
        self.move(vx, vy, dt * (self.wander_speed / max(1e-6, self.speed)) * speed_factor, room)
        self.wander_time -= dt
        if self.wander_time <= 0.0 or random.random() < 0.01:
            if random.random() < 0.5:
                self.state = IDLE
            else:
                self._pick_wander()

    def _update_chase(self, dt: float, room, dx: float, dy: float) -> None:
        mag = math.hypot(dx, dy)
        if mag > 0:
            dx, dy = dx/mag, dy/mag
        speed_factor = self._movement_speed_factor()
        self._update_facing(dx)
        self.move(dx, dy, dt * (self.chase_speed / max(1e-6, self.speed)) * speed_factor, room)

    def draw(self, surf: pygame.Surface) -> None:
        frame = self.animator.current_surface()
        if not self._facing_right:
            frame = pygame.transform.flip(frame, True, False)
        dest = frame.get_rect(center=self.rect().center)
        surf.blit(frame, dest)

    def _update_animation(self, dt: float) -> None:
        base_state = "idle"
        if self.state in (WANDER, CHASE):
            base_state = "run"
        self.animator.set_base_state(base_state)
        self.animator.update(dt)

    def _update_facing(self, dx: float) -> None:
        if dx > 0.05:
            self._facing_right = True
        elif dx < -0.05:
            self._facing_right = False

    def trigger_shoot_animation(self, dir_x: float) -> None:
        self._update_facing(dir_x)
        self.animator.trigger_shoot()

    def trigger_attack_animation(self, dir_x: float = 0.0) -> None:
        """Gancho para enemigos cuerpo a cuerpo."""
        return

    def is_ready_to_remove(self) -> bool:
        if not self._is_dying:
            return False
        return self._ready_to_remove

    def is_dying(self) -> bool:
        return self._is_dying


# ===== Tipos de enemigo =====

class FastChaserEnemy(Enemy):
    """Rápido, poca vida."""
    SPRITE_VARIANT = "green_chaser"
    def __init__(self, x, y):
        super().__init__(x, y, hp=2, gold_reward=7)
        self.chase_speed  = 100.0
        self.wander_speed = 80.0
        self.detect_radius = 100.0
        self.lose_radius   = 150.0
        self.reaction_delay = 0.0
        self.contact_damage = 1
        self.attack_range = 26.0
        self.attack_cooldown = 0.8
        self._attack_timer = 0.0

    def update(self, dt, player, room):
        self._attack_timer = max(0.0, self._attack_timer - dt)
        super().update(dt, player, room)
        if self.is_dying():
            return
        if self._attack_timer > 0.0:
            return
        ex = self.x + self.w/2
        ey = self.y + self.h/2
        px = player.x + player.w/2
        py = player.y + player.h/2
        dist = math.hypot(px - ex, py - ey)
        if dist <= self.attack_range:
            dir_x = px - ex
            self.trigger_attack_animation(dir_x)

    def trigger_attack_animation(self, dir_x: float = 0.0) -> None:
        if self.is_dying():
            return
        self._attack_timer = self.attack_cooldown
        self._update_facing(dir_x)
        self.animator.trigger_attack()


class TankEnemy(Enemy):
    """Lento, mucha vida."""

    SPRITE_VARIANT = "tank"

    def __init__(self, x, y):
        super().__init__(x, y, hp=9, gold_reward=12)
        self.chase_speed  = 30.0
        self.wander_speed = 18.0
        self.detect_radius = 240.0
        self.lose_radius   = 260.0


class ShooterEnemy(Enemy):
    """Dispara si te ve (LoS) y estás en rango."""
    SPRITE_VARIANT = "yellow_shooter"
    def __init__(self, x, y):
        super().__init__(x, y, hp=3, gold_reward=9)
        self.chase_speed  = 5
        self.wander_speed = 5
        self.detect_radius = 220.0
        self.lose_radius   = 260.0

        self.fire_cooldown = 2.75
        self._fire_timer   = 0.0
        self.fire_range    = 260.0
        self.bullet_speed  = 160.0
        self.reaction_delay = 0.55

    def update(self, dt, player, room):
        super().update(dt, player, room)
        self._fire_timer = max(0.0, self._fire_timer - dt)

    def maybe_shoot(self, dt, player, room, out_bullets: list) -> bool:
        if self.alert_timer > 0.0 or self.is_stunned() or self.is_dying():
            return False
        if self._fire_timer > 0.0:
            return False
        # Solo dispara si está en CHASE, hay LoS y dentro de rango
        ex, ey = self._center()
        px, py = (player.x + player.w/2, player.y + player.h/2)
        dx, dy = (px - ex), (py - ey)
        dist = math.hypot(dx, dy)
        if self.state != CHASE or dist > self.fire_range:
            return False
        if not room.has_line_of_sight(ex, ey, px, py):
            return False

        # Normaliza y dispara ráfagas en abanico
        if dist > 0:
            dx, dy = dx/dist, dy/dist
            self._update_facing(dx)

        base_angle = math.atan2(dy, dx)
        spread = math.radians(35)
        burst = 5
        center = (burst - 1) / 2.0
        for i in range(burst):
            offset = (i - center)
            angle = base_angle + (spread * offset / max(center, 1))
            dir_x = math.cos(angle)
            dir_y = math.sin(angle)
            spawn_x = ex + dir_x * 8
            spawn_y = ey + dir_y * 8
            bullet = Projectile(
                spawn_x, spawn_y, dir_x, dir_y,
                speed=self.bullet_speed, radius=3, color=(255, 90, 90)
            )
            if hasattr(out_bullets, "add"):
                out_bullets.add(bullet)
            else:
                out_bullets.append(bullet)

        # Anillo radial lento para saturar la sala
        radial = 8
        radial_speed = self.bullet_speed * 0.55
        for j in range(radial):
            angle = base_angle + j * (math.tau / radial)
            dir_x = math.cos(angle)
            dir_y = math.sin(angle)
            spawn_x = ex + dir_x * 10
            spawn_y = ey + dir_y * 10
            bullet = Projectile(
                spawn_x, spawn_y, dir_x, dir_y,
                speed=radial_speed, radius=3, color=(200, 70, 180)
            )
            if hasattr(out_bullets, "add"):
                out_bullets.add(bullet)
            else:
                out_bullets.append(bullet)
        self._fire_timer = self.fire_cooldown
        self.trigger_shoot_animation(dx)
        return True


class BasicEnemy(Enemy):
    """Enemigo común que dispara lentamente mientras avanza."""

    SPRITE_VARIANT = "yellow_shooter"

    def __init__(self, x, y):
        super().__init__(x, y, hp=3, gold_reward=5)
        self.fire_cooldown = 1.1
        self._fire_timer = 0.0
        self.fire_range = 210.0
        self.bullet_speed = 192.0
        self.reaction_delay = 0.45

    def update(self, dt, player, room):
        super().update(dt, player, room)
        self._fire_timer = max(0.0, getattr(self, "_fire_timer", 0.0) - dt)

    def maybe_shoot(self, dt, player, room, out_bullets) -> bool:
        if self.alert_timer > 0.0 or self.is_stunned() or self.is_dying():
            return False
        if getattr(self, "_fire_timer", 0.0) > 0.0:
            return False

        ex, ey = self._center()
        px, py = (player.x + player.w/2, player.y + player.h/2)
        dx, dy = (px - ex), (py - ey)
        dist = math.hypot(dx, dy)
        if self.state != CHASE or dist > self.fire_range:
            return False
        if not room.has_line_of_sight(ex, ey, px, py):
            return False

        if dist > 0:
            dx, dy = dx/dist, dy/dist
            self._update_facing(dx)

        base_angle = math.atan2(dy, dx)
        offsets = (-0.18, 0.0, 0.18)
        for offset in offsets:
            angle = base_angle + offset
            dir_x = math.cos(angle)
            dir_y = math.sin(angle)
            spawn_x = ex + dir_x * 6
            spawn_y = ey + dir_y * 6
            bullet = Projectile(
                spawn_x, spawn_y, dir_x, dir_y,
                speed=self.bullet_speed, radius=3, color=(240, 200, 120)
            )
            if hasattr(out_bullets, "add"):
                out_bullets.add(bullet)
            else:
                out_bullets.append(bullet)
        self._fire_timer = self.fire_cooldown
        self.trigger_shoot_animation(dx)
        return True


class TankEnemy(Enemy):
    """Lento, mucha vida y dispara ráfagas estilo escopeta."""

    SPRITE_VARIANT = "tank"

    def __init__(self, x, y):
        super().__init__(x, y, hp=9, gold_reward=12)
        self.chase_speed  = 30.0
        self.wander_speed = 18.0
        self.detect_radius = 240.0
        self.lose_radius   = 260.0

        self.fire_cooldown = 3.1
        self._fire_timer = 0.0
        self.fire_range = 260.0
        self.bullet_speed = 152.0
        self.pellets = 7
        self.spread_radians = math.radians(28)
        self.reaction_delay = 0.65

    def update(self, dt, player, room):
        super().update(dt, player, room)
        self._fire_timer = max(0.0, getattr(self, "_fire_timer", 0.0) - dt)

    def maybe_shoot(self, dt, player, room, out_bullets) -> bool:
        if self.alert_timer > 0.0 or self.is_stunned() or self.is_dying():
            return False
        if getattr(self, "_fire_timer", 0.0) > 0.0:
            return False

        ex, ey = self._center()
        px, py = (player.x + player.w/2, player.y + player.h/2)
        dx, dy = (px - ex), (py - ey)
        dist = math.hypot(dx, dy)
        if self.state != CHASE or dist > self.fire_range:
            return False
        if not room.has_line_of_sight(ex, ey, px, py):
            return False

        if dist > 0:
            dx, dy = dx/dist, dy/dist
            self._update_facing(dx)

        base_angle = math.atan2(dy, dx)
        half = (self.pellets - 1) / 2.0
        fired_any = False
        for i in range(self.pellets):
            offset = (i - half)
            angle = base_angle + offset * (self.spread_radians / max(half, 1))
            dir_x = math.cos(angle)
            dir_y = math.sin(angle)
            spawn_x = ex + dir_x * 8
            spawn_y = ey + dir_y * 8
            bullet = Projectile(
                spawn_x, spawn_y, dir_x, dir_y,
                speed=self.bullet_speed, radius=3, color=(255, 120, 90)
            )
            fired_any = True
            if hasattr(out_bullets, "add"):
                out_bullets.add(bullet)
            else:
                out_bullets.append(bullet)

        # Anillo secundario para llenar el cuarto (tiro en cruz)
        if fired_any:
            ortho_angle = base_angle + math.pi / 2
            ortho_dirs = (
                (math.cos(ortho_angle), math.sin(ortho_angle)),
                (math.cos(ortho_angle + math.pi), math.sin(ortho_angle + math.pi)),
            )
            for dir_x, dir_y in ortho_dirs:
                spawn_x = ex + dir_x * 8
                spawn_y = ey + dir_y * 8
                bullet = Projectile(
                    spawn_x, spawn_y, dir_x, dir_y,
                    speed=self.bullet_speed * 0.9, radius=3, color=(255, 160, 120)
                )
                if hasattr(out_bullets, "add"):
                    out_bullets.add(bullet)
                else:
                    out_bullets.append(bullet)

        self._fire_timer = self.fire_cooldown
        return fired_any
