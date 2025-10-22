# CODIGO/Enemy.py
import math, random, pygame
from Entity import Entity
from Config import CFG

IDLE, WANDER, CHASE = 0, 1, 2

class Enemy(Entity):
    def __init__(self, x: float, y: float, hp: int = 3, speed: float = 55.0) -> None:
        super().__init__(x, y, w=12, h=12, speed=speed)
        self.hp = hp

        # --- comportamiento ---
        self.state = IDLE
        self.detect_radius = 80.0   # px: se activa persecución
        self.lose_radius    = 120.0   # px: suelta la persecución (histéresis)
        self.wander_speed   = 35.0
        self.wander_time    = 0.0
        self.wander_dir     = (0.0, 0.0)

        # jitters visuales cuando idle (opcional)
        self._idle_timer = 0.0
        self._idle_offset = (0, 0)

    # --------- lógica principal ---------
    def update(self, dt: float, player, room) -> None:
        # Distancia al jugador
        dx = (player.x - self.x)
        dy = (player.y - self.y)
        dist = math.hypot(dx, dy)

        # Cambios de estado (con histéresis)
        if self.state != CHASE and dist <= self.detect_radius:
            self.state = CHASE
        elif self.state == CHASE and dist >= self.lose_radius:
            # al perderte: vuelve a deambular (o idle)
            self._pick_wander()
            self.state = WANDER

        # Ejecutar estado
        if self.state == IDLE:
            self._update_idle(dt, room)
        elif self.state == WANDER:
            self._update_wander(dt, room)
        elif self.state == CHASE:
            self._update_chase(dt, room, dx, dy)

    # --------- estados ---------
    def _update_idle(self, dt: float, room) -> None:
        # pequeño “temblor” visual opcional (no mueve la colisión)
        self._idle_timer += dt
        if self._idle_timer > 0.2:
            self._idle_timer = 0.0
            self._idle_offset = (random.randint(-1, 1), random.randint(-1, 1))
        # chance de pasar a wander cada cierto tiempo
        if random.random() < 0.005:
            self._pick_wander()
            self.state = WANDER

    def _pick_wander(self) -> None:
        # elige una dirección aleatoria y un tiempo corto
        ang = random.uniform(0, math.tau)
        self.wander_dir = (math.cos(ang), math.sin(ang))
        self.wander_time = random.uniform(0.6, 1.2)

    def _update_wander(self, dt: float, room) -> None:
        vx, vy = self.wander_dir
        self.move(vx, vy, dt * (self.wander_speed / max(1e-6, self.speed)), room)
        self.wander_time -= dt
        if self.wander_time <= 0.0 or random.random() < 0.01:
            # parar o elegir otro paseíto
            if random.random() < 0.5:
                self.state = IDLE
            else:
                self._pick_wander()

    def _update_chase(self, dt: float, room, dx: float, dy: float) -> None:
        mag = math.hypot(dx, dy)
        if mag > 0:
            dx, dy = dx / mag, dy / mag
        self.move(dx, dy, dt, room)

    # --------- dibujo ---------
    def draw(self, surf: pygame.Surface) -> None:
        # color por estado
        color = (200, 60, 60)   # rojo base
        if self.state == IDLE:
            color = (170, 75, 75)
        elif self.state == WANDER:
            color = (200, 90, 60)
        elif self.state == CHASE:
            color = (255, 80, 80)

        # “blink” mínimo si quieres indicar daño (opcional: manejar en Game al impacto)
        super().draw(surf, color)

        # DEBUG opcional: radios
        pygame.draw.circle(surf, (60,200,60), (int(self.x+self.w/2), int(self.y+self.h/2)), int(self.detect_radius), 1)
        pygame.draw.circle(surf, (60,120,200), (int(self.x+self.w/2), int(self.y+self.h/2)), int(self.lose_radius), 1)
