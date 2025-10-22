import pygame, sys
from Config import CFG, Config
from Tileset import Tileset
from Player import Player
from Dungeon import Dungeon
from Minimap import Minimap

class Game:
    def __init__(self, cfg: Config) -> None:
        pygame.init()
        self.cfg = cfg

        # ---------- Ventana ----------
        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_W * cfg.SCREEN_SCALE, cfg.SCREEN_H * cfg.SCREEN_SCALE)
        )
        pygame.display.set_caption("Roguelike — Dungeon + Minimap")
        self.clock = pygame.time.Clock()
        self.world = pygame.Surface((cfg.SCREEN_W, cfg.SCREEN_H))

        # ---------- Mundo ----------
        self.dungeon = Dungeon(
            grid_w=7, grid_h=7,   # tamaño máximo del “mundo”
            main_len=8,           # largo del camino principal (siempre conectado)
            branch_chance=0.45,   # prob. de generar ramas
            branch_min=2, branch_max=4,
            seed=None             # pon un int para repetir la misma dungeon
        )
        self.dungeon.explored.add((self.dungeon.i, self.dungeon.j))  # marca room inicial
        self.tileset = Tileset()

        # ---------- Jugador ----------
        room = self.dungeon.current_room
        px, py = room.center_px()
        self.player = Player(px - 6, py - 6)

        # ---------- Minimapa ----------
        self.minimap = Minimap(cell=16, padding=8)

        # ---------- Control ----------
        self.door_cooldown = 0.0
        self.running = True
        
        #----------- Proyectiles -------
        self.projectiles = []
        self.enemy_projectiles = []

    # ============================================================
    def run(self) -> None:
        frame = 0
        while self.running:
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            self.door_cooldown = max(0.0, self.door_cooldown - dt)

            # -------- Eventos --------
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False

            # (opcional) debug FPS
            frame += 1
            if frame % 60 == 0:
                print("[RUN] frames:", frame, "cooldown:", self.door_cooldown)
            pygame.display.set_caption(f"Roguelike — FPS {self.clock.get_fps():.1f}")

            # -------- UPDATE: jugador --------
            room = self.dungeon.current_room
            self.player.update(dt, room)

            # Disparo hacia el mouse (coordenadas de mundo)
            mx, my = pygame.mouse.get_pos()
            mx //= self.cfg.SCREEN_SCALE
            my //= self.cfg.SCREEN_SCALE
            self.player.try_shoot((mx, my), self.projectiles)

            # -------- SPAWN + UPDATE: enemigos --------
            # Dificultad por distancia al centro de la grilla
            cx, cy = self.dungeon.grid_w // 2, self.dungeon.grid_h // 2
            dist = abs(self.dungeon.i - cx) + abs(self.dungeon.j - cy)

            # 🚫 No spawnear en el cuarto inicial
            if (self.dungeon.i, self.dungeon.j) != getattr(self.dungeon, "start", (cx, cy)):
                room.ensure_spawn(difficulty=1 + dist)

            # Persecución
            for en in room.enemies:
                en.update(dt, self.player, room)
            # Enemigos con disparo
            for en in room.enemies:
                en.maybe_shoot(dt, self.player, room, self.enemy_projectiles)    

            # -------- UPDATE: proyectiles --------
            for p in self.projectiles:
                p.update(dt, room)
            # Update balas del enemigo
            for b in self.enemy_projectiles:
                b.update(dt, room)
            # Limpia inactivas
            self.enemy_projectiles = [b for b in self.enemy_projectiles if b.alive]

            # -------- Transición por puertas --------
            d = None
            if self.door_cooldown <= 0.0:
                d = room.check_exit(self.player.rect())
            if d and self.dungeon.can_move(d):
                self.dungeon.move(d)
                self.player.x, self.player.y = self.dungeon.entry_position(
                    d, self.player.w, self.player.h
                )
                self.dungeon.explored.add((self.dungeon.i, self.dungeon.j))
                self.door_cooldown = 0.25
                # opcional: limpiar balas al cambiar de cuarto
                self.projectiles.clear()

                # actualizar referencias y spawner del nuevo cuarto
                room = self.dungeon.current_room
                if (self.dungeon.i, self.dungeon.j) != getattr(self.dungeon, "start", (cx, cy)):
                    room.ensure_spawn(difficulty=1 + dist)

            # -------- COLISIONES: balas ↔ enemigos --------
            for p in self.projectiles:
                if not p.alive:
                    continue
                r_p = p.rect()
                for en in room.enemies:
                    if r_p.colliderect(en.rect()):
                        en.hp -= 1
                        p.alive = False
                        break  # una bala = un impacto

            # Limpieza de listas
            room.enemies = [en for en in room.enemies if en.hp > 0]
            self.projectiles = [p for p in self.projectiles if p.alive]

            # -------- RENDER al world --------
            room = self.dungeon.current_room
            room.draw(self.world, self.tileset)

            # enemigos (puedes dibujarlos antes o después del player)
            for en in room.enemies:
                en.draw(self.world)

            self.player.draw(self.world)

            for p in self.projectiles:
                p.draw(self.world)
            for b in self.enemy_projectiles:
                b.draw(self.world)
    
                
                # DEBUG: dibuja triggers de puertas en verde
            for r in room._door_trigger_rects().values():
                pygame.draw.rect(self.world, (0, 255, 0), r, 1)

            # -------- ESCALADO a screen + minimapa --------
            scaled = pygame.transform.scale(
                self.world,
                (self.cfg.SCREEN_W * self.cfg.SCREEN_SCALE,
                self.cfg.SCREEN_H * self.cfg.SCREEN_SCALE)
            )
            self.screen.blit(scaled, (0, 0))

            mm = self.minimap.render(self.dungeon)
            margin = 16
            self.screen.blit(mm, (self.screen.get_width() - mm.get_width() - margin, 105))

            pygame.display.flip()

        pygame.quit()
        sys.exit(0)
