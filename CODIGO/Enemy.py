# CODIGO/Enemy.py
import math, random, pygame
from Entity import Entity
from Config import CFG
from Projectile import Projectile

IDLE, WANDER, CHASE = 0, 1, 2

class Enemy(Entity):
    """Base con FSM + LoS. Subclases cambian stats/comportamientos."""
    def __init__(self, x: float, y: float, hp: int = 3) -> None:
        super().__init__(x, y, w=12, h=12, speed=40.0)
        self.hp = hp

        # Estados y radios
        self.state = IDLE
        self.detect_radius = 110.0
        self.lose_radius   = 130.0
        self._los_grace    = 0.35   # “gracia” sin LoS antes de soltar persecución

        # Velocidades
        self.chase_speed  = 70.0
        self.wander_speed = 50.0

        # Wander
        self.wander_time = 0.0
        self.wander_dir  = (0.0, 0.0)

        # timers internos
        self._los_timer = 0.0

    def _center(self):
        return (self.x + self.w/2, self.y + self.h/2)

    # ---------- loop ----------
    def update(self, dt: float, player, room) -> None:
        ex, ey = self._center()
        px, py = (player.x + player.w/2, player.y + player.h/2)

        dx, dy = (px - ex), (py - ey)
        dist   = math.hypot(dx, dy)
        has_los = room.has_line_of_sight(ex, ey, px, py)

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

        # Ejecutar estado
        if self.state == IDLE:
            self._update_idle(dt)
        elif self.state == WANDER:
            self._update_wander(dt, room)
        elif self.state == CHASE:
            self._update_chase(dt, room, dx, dy)

    def maybe_shoot(self, dt: float, player, room, out_bullets) -> None:
        """Por defecto, los enemigos base NO disparan."""
        return

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
        self.move(vx, vy, dt * (self.wander_speed / max(1e-6, self.speed)), room)
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
        self.move(dx, dy, dt * (self.chase_speed / max(1e-6, self.speed)), room)

    def draw(self, surf: pygame.Surface) -> None:
        # NO llames a super().draw con color si Entity.draw no acepta color
        color = (255, 255, 255) if self.state == IDLE else \
                (255, 255, 255)  if self.state == WANDER else \
                (255, 255, 255)
        pygame.draw.rect(surf, color, self.rect())


# ===== Tipos de enemigo =====

class FastChaserEnemy(Enemy):
    """Rápido, poca vida."""
    def __init__(self, x, y):
        super().__init__(x, y, hp=2)
        self.chase_speed  = 100.0
        self.wander_speed = 80.0
        self.detect_radius = 130.0
        self.lose_radius   = 150.0

    def draw(self, surf):
        color = (0, 255, 0) if self.state == CHASE else (0, 255, 0)
        pygame.draw.rect(surf, color, self.rect())


class TankEnemy(Enemy):
    """Lento, mucha vida."""
    def __init__(self, x, y):
        super().__init__(x, y, hp=9)
        self.chase_speed  = 30.0
        self.wander_speed = 18.0
        self.detect_radius = 240.0
        self.lose_radius   = 260.0

    def draw(self, surf):
        color = (255, 0, 0) if self.state == CHASE else (255, 0, 0)
        pygame.draw.rect(surf, color, self.rect())


class ShooterEnemy(Enemy):
    """Dispara si te ve (LoS) y estás en rango."""
    def __init__(self, x, y):
        super().__init__(x, y, hp=3)
        self.chase_speed  = 5
        self.wander_speed = 5
        self.detect_radius = 220.0
        self.lose_radius   = 260.0

        self.fire_cooldown = 0.9
        self._fire_timer   = 0.0
        self.fire_range    = 260.0
        self.bullet_speed  = 200.0

    def update(self, dt, player, room):
        super().update(dt, player, room)
        self._fire_timer = max(0.0, self._fire_timer - dt)

    def maybe_shoot(self, dt, player, room, out_bullets) -> None:
        if self._fire_timer > 0.0:
            return
        # Solo dispara si está en CHASE, hay LoS y dentro de rango
        ex, ey = self._center()
        px, py = (player.x + player.w/2, player.y + player.h/2)
        dx, dy = (px - ex), (py - ey)
        dist = math.hypot(dx, dy)
        if self.state != CHASE or dist > self.fire_range:
            return
        if not room.has_line_of_sight(ex, ey, px, py):
            return

        # Normaliza y dispara
        if dist > 0:
            dx, dy = dx/dist, dy/dist
        spawn_x = ex + dx * 8
        spawn_y = ey + dy * 8
        bullet = Projectile(
            spawn_x, spawn_y, dx, dy,
            speed=self.bullet_speed, radius=3, color=(255, 90, 90)
        )
        if hasattr(out_bullets, "add"):
            out_bullets.add(bullet)
        else:
            out_bullets.append(bullet)
        self._fire_timer = self.fire_cooldown

    def draw(self, surf):
        color = (0, 0, 255) if self.state == CHASE else (0, 0, 255)
        pygame.draw.rect(surf, color, self.rect())
