import pygame, math
from Entity import Entity
from Config import CFG
from Projectile import Projectile   


class Player(Entity):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, w=12, h=12, speed=120.0)
        self.fire_cooldown = 0.001  # segundos entre disparos
        self._fire_timer = 0.0

    def update(self, dt: float, room) -> None:
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        mag = math.hypot(dx, dy)
        if mag > 0: dx, dy = dx / mag, dy / mag
        self.move(dx, dy, dt, room)

        # avanza el temporizador del disparo
        self._fire_timer = max(0.0, self._fire_timer - dt)

    def try_shoot(self, mouse_world_pos, out_projectiles: list) -> None:
        """Dispara hacia mouse si se pulsa y cooldown listo."""
        if self._fire_timer > 0.0:
            return
        mouse_pressed = pygame.mouse.get_pressed(3)[0]  # botón izquierdo
        if not mouse_pressed:
            return

        mx, my = mouse_world_pos
        # origen: centro del jugador
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        vx, vy = mx - cx, my - cy
        mag = math.hypot(vx, vy)
        if mag <= 0.0001:
            return
        vx, vy = vx / mag, vy / mag  # normaliza

        # separa un poco el spawn para que no colisione con el propio jugador
        spawn_x = cx + vx * 8
        spawn_y = cy + vy * 8
        out_projectiles.append(Projectile(spawn_x, spawn_y, vx, vy, speed=360.0, radius=3))
        self._fire_timer = self.fire_cooldown
    def draw(self, surf):
     pygame.draw.rect(surf, CFG.COLOR_PLAYER, self.rect())
