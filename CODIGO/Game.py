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

    # ============================================================
    def run(self) -> None:
        frame = 0
        while self.running:
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            self.door_cooldown = max(0.0, self.door_cooldown - dt)

            # ---------- Eventos ----------
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False

            # DEBUG opcional
            frame += 1
            if frame % 60 == 0:
                print("[RUN] frames:", frame, "cooldown:", self.door_cooldown)
            pygame.display.set_caption(f"Roguelike — FPS {self.clock.get_fps():.1f}")

            # ---------- UPDATE ----------
            room = self.dungeon.current_room
            self.player.update(dt, room)

            # 1) Disparo hacia el mouse (en coordenadas de MUNDO)
            mx, my = pygame.mouse.get_pos()
            mx //= self.cfg.SCREEN_SCALE
            my //= self.cfg.SCREEN_SCALE
            self.player.try_shoot((mx, my), self.projectiles)

            # 2) Actualizar proyectiles y limpiar muertos
            for p in self.projectiles:
                p.update(dt, room)
            self.projectiles = [p for p in self.projectiles if p.alive]

            # 3) Transición por puertas (con cooldown)
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

            # ---------- RENDER AL WORLD ----------
            room = self.dungeon.current_room
            room.draw(self.world, self.tileset)
            self.player.draw(self.world, CFG.COLOR_PLAYER)
            for p in self.projectiles:
                p.draw(self.world)

            # ---------- ESCALADO WORLD -> SCREEN ----------
            scaled = pygame.transform.scale(
                self.world,
                (self.cfg.SCREEN_W * self.cfg.SCREEN_SCALE,
                self.cfg.SCREEN_H * self.cfg.SCREEN_SCALE)
            )
            self.screen.blit(scaled, (0, 0))

            # ---------- MINIMAPA ----------
            mm = self.minimap.render(self.dungeon)
            margin = 16
            self.screen.blit(
                mm,
                (self.screen.get_width() - mm.get_width() - margin, 100)
            )

            # ---------- FLIP ----------
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

