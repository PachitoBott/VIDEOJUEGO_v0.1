import pygame, sys
from Config import CFG, Config
from Room import Room
from Tileset import Tileset
from Player import Player

class Game:
    def __init__(self, cfg: Config) -> None:
        pygame.init()
        self.cfg = cfg
        self.screen = pygame.display.set_mode((cfg.SCREEN_W*cfg.SCREEN_SCALE, cfg.SCREEN_H*cfg.SCREEN_SCALE))
        pygame.display.set_caption("Roguelike — OOP Base")
        self.clock = pygame.time.Clock()
        self.world = pygame.Surface((cfg.SCREEN_W, cfg.SCREEN_H))

        self.room = Room()
        self.room.build_centered(cfg.ROOM_W, cfg.ROOM_H)
        self.tileset = Tileset()

        px, py = self.room.center_px()
        self.player = Player(px-6, py-6)
        self.running = True

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.cfg.FPS)/1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: self.running = False

            self.player.update(dt, self.room)
            self.room.draw(self.world, self.tileset)
            self.player.draw(self.world)

            scaled = pygame.transform.scale(self.world, (self.cfg.SCREEN_W*self.cfg.SCREEN_SCALE,
                                                         self.cfg.SCREEN_H*self.cfg.SCREEN_SCALE))
            self.screen.blit(scaled, (0,0))
            pygame.display.flip()
        pygame.quit(); sys.exit(0)
