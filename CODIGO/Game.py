import pygame, sys
from Config import CFG, Config
from Tileset import Tileset
from Player import Player
from Dungeon import Dungeon
from Minimap import Minimap

class Game:
    def __init__(self, cfg: Config) -> None:
        pygame.init()
        self.door_cooldown = 0.0  # segundos para ignorar triggers tras cambiar de room
        self.cfg = cfg
        self.screen = pygame.display.set_mode((cfg.SCREEN_W*cfg.SCREEN_SCALE, cfg.SCREEN_H*cfg.SCREEN_SCALE))
        pygame.display.set_caption("Roguelike — Dungeon Rooms + Minimap")
        self.clock = pygame.time.Clock()
        self.world = pygame.Surface((cfg.SCREEN_W, cfg.SCREEN_H))

        self.dungeon = Dungeon(grid_w=3, grid_h=3)
        self.tileset = Tileset()
        self.minimap = Minimap(cell=10, padding=6)

        room = self.dungeon.current_room
        px, py = room.center_px()
        self.player = Player(px-6, py-6)
        self.running = True

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            self.door_cooldown = max(0.0, self.door_cooldown - dt)

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False

            room = self.dungeon.current_room

            # 🔹 Movimiento normal del jugador
            self.player.update(dt, room)

            # 🔹 👉 AQUÍ VA EL PASO C (detección y transición de puertas)
            d = None
            if self.door_cooldown <= 0.0:
                d = room.check_exit(self.player.rect())

            if d and self.dungeon.can_move(d):
                self.dungeon.move(d)
                self.player.x, self.player.y = self.dungeon.entry_position(
                    d, self.player.w, self.player.h
                )
                self.door_cooldown = 0.25  # evita rebote

            # 🔹 A partir de aquí sigue todo lo de renderizado
            room = self.dungeon.current_room
            room.draw(self.world, self.tileset)
            self.player.draw(self.world)

            scaled = pygame.transform.scale(
                self.world,
                (self.cfg.SCREEN_W * self.cfg.SCREEN_SCALE,
                self.cfg.SCREEN_H * self.cfg.SCREEN_SCALE)
            )
            self.screen.blit(scaled, (0, 0))

            mm = self.minimap.render(self.dungeon)
            margin = 10
            self.screen.blit(mm, (self.screen.get_width() - mm.get_width() - margin, margin))

            pygame.display.flip()

        pygame.quit()
        sys.exit(0)


   
