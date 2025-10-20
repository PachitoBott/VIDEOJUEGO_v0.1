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
        self.dungeon = Dungeon(grid_w=3, grid_h=3)
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

    # ============================================================
    def run(self) -> None:
        frame = 0
        while self.running:
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            self.door_cooldown = max(0.0, self.door_cooldown - dt)

            # Eventos
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False

            # DEBUG: confirma que el bucle corre (verás frames en consola)
            frame += 1
            if frame % 60 == 0:
                print("[RUN] frames:", frame, "cooldown:", self.door_cooldown)
            pygame.display.set_caption(f"Roguelike — FPS {self.clock.get_fps():.1f}")

            # ====== UPDATE ======
            room = self.dungeon.current_room
            self.player.update(dt, room)

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

             # ====== RENDER AL WORLD ======
             # 1) renderizas TODO al world (tilemap, player, etc.)
            room.draw(self.world, self.tileset)
            self.player.draw(self.world)

            # 2) escalas world -> screen
            scaled = pygame.transform.scale(
                self.world,
                (self.cfg.SCREEN_W * self.cfg.SCREEN_SCALE,
                self.cfg.SCREEN_H * self.cfg.SCREEN_SCALE)
            )
            self.screen.blit(scaled, (0, 0))


            # 4) minimapa (también en screen)
            mm = self.minimap.render(self.dungeon)
            margin = 16
            self.screen.blit(mm, (self.screen.get_width() - mm.get_width() - margin, 200))

            # 5) flip final (¡una sola vez!)
            pygame.display.flip()


        pygame.quit()
        sys.exit(0)
