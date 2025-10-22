# CODIGO/Game.py
import sys
import random
import pygame
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

        # ---------- UI ----------
        self.ui_font = pygame.font.SysFont(None, 18)
        self.current_seed: int | None = None

        # ---------- Recursos ----------
        self.tileset = Tileset()
        self.minimap = Minimap(cell=16, padding=8)

        # ---------- Estado runtime ----------
        self.projectiles = []          # balas del jugador
        self.enemy_projectiles = []    # balas de enemigos
        self.door_cooldown = 0.0
        self.running = True

        # ---------- Arranque de run ----------
        self.start_new_run(seed=None)  # crea dungeon, posiciona player, limpia estado

    # ------------------------------------------------------------------ #
    # Nueva partida / regenerar dungeon (misma o nueva seed)
    # ------------------------------------------------------------------ #
    def start_new_run(self, seed: int | None) -> None:
        """
        Crea una nueva dungeon con la seed dada (o aleatoria si None),
        reubica al jugador y resetea estado de runtime.
        """
        params = dict(grid_w=7, grid_h=7, main_len=8, branch_chance=0.45, branch_min=2, branch_max=4)

        self.dungeon = Dungeon(**params, seed=seed)
        self.current_seed = self.dungeon.seed
        pygame.display.set_caption(f"Roguelike — Seed {self.current_seed}")

        # marca room inicial como explorado
        self.dungeon.explored = set()
        self.dungeon.explored.add((self.dungeon.i, self.dungeon.j))

        # Jugador (crear o reubicar al centro del cuarto actual)
        room = self.dungeon.current_room
        px, py = room.center_px()
        if not hasattr(self, "player"):
            self.player = Player(px - 6, py - 6)
        else:
            self.player.x, self.player.y = px - 6, py - 6

        # Reset de runtime
        self.projectiles.clear()
        self.enemy_projectiles.clear()
        self.door_cooldown = 0.0
        
        
        self.locked = False
        self.cleared = False


    # ------------------------------------------------------------------ #
    # Bucle principal
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        frame = 0
        while self.running:
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            self.door_cooldown = max(0.0, self.door_cooldown - dt)

            # -------- Eventos --------
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        self.running = False
                    elif e.key == pygame.K_r:
                        # Rejugar misma seed
                        self.start_new_run(seed=self.current_seed)
                    elif e.key == pygame.K_n:
                        # Nueva seed aleatoria
                        self.start_new_run(seed=None)

            # (opcional) debug FPS
            frame += 1
            if frame % 90 == 0:
                pygame.display.set_caption(f"Roguelike — Seed {self.current_seed} — FPS {self.clock.get_fps():.1f}")

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

            # No spawnear en el cuarto inicial
            if (self.dungeon.i, self.dungeon.j) != getattr(self.dungeon, "start", (cx, cy)):
                room.ensure_spawn(difficulty=1 + dist)

            # IA de enemigos
            for en in room.enemies:
                en.update(dt, self.player, room)

            # Disparo de enemigos (shooters, etc.)
            for en in room.enemies:
                # Si tu Enemy base no implementa maybe_shoot, simplemente no hará nada
                en.maybe_shoot(dt, self.player, room, self.enemy_projectiles)

            # -------- UPDATE: proyectiles --------
            for p in self.projectiles:
                p.update(dt, room)
            self.projectiles = [p for p in self.projectiles if p.alive]

            for b in self.enemy_projectiles:
                b.update(dt, room)
            self.enemy_projectiles = [b for b in self.enemy_projectiles if b.alive]

            # -------- Transición por puertas --------
            d = None
            if self.door_cooldown <= 0.0:
                d = room.check_exit(self.player.rect())

            if d and self.dungeon.can_move(d):
                # Mover de sala
                self.dungeon.move(d)
                self.player.x, self.player.y = self.dungeon.entry_position(
                    d, self.player.w, self.player.h
                )
                self.dungeon.explored.add((self.dungeon.i, self.dungeon.j))
                self.door_cooldown = 0.25

                # limpiar balas al cambiar de cuarto (opcional)
                self.projectiles.clear()
                self.enemy_projectiles.clear()

                # Actualizar referencia de room (¡muy importante!)
                room = self.dungeon.current_room

                # Spawn si no es el cuarto inicial
                cx, cy = self.dungeon.grid_w // 2, self.dungeon.grid_h // 2
                is_start = (self.dungeon.i, self.dungeon.j) == getattr(self.dungeon, "start", (cx, cy))
                if not is_start:
                    dist = abs(self.dungeon.i - cx) + abs(self.dungeon.j - cy)
                    room.ensure_spawn(difficulty=1 + dist)

                # 🔒 BLOQUEAR si hay enemigos y no ha sido limpiada (solo si no es start)
                room.locked = (not is_start) and (len(room.enemies) > 0) and (not room.cleared)

            # -------- COLISIONES: balas jugador ↔ enemigos --------
            for p in self.projectiles:
                if not p.alive:
                    continue
                r_p = p.rect()
                for en in room.enemies:
                    if r_p.colliderect(en.rect()):
                        en.hp -= 1
                        p.alive = False
                        break  # una bala = un impacto

            # Limpiar enemigos muertos
            room.enemies = [en for en in room.enemies if getattr(en, "hp", 1) > 0]

            # 🔓 DESBLOQUEAR cuando limpias
            room.refresh_lock_state()


            # -------- RENDER al world --------
            self.world.fill((0, 0, 0))  # limpia el lienzo del mundo
            room = self.dungeon.current_room
            room.draw(self.world, self.tileset)

            # enemigos
            for en in room.enemies:
                en.draw(self.world)

            # jugador
            self.player.draw(self.world)

            # proyectiles (jugador y enemigos)
            for p in self.projectiles:
                p.draw(self.world)
            for b in self.enemy_projectiles:
                b.draw(self.world)

            # (opcional) DEBUG de triggers de puertas
            # for r in room._door_trigger_rects().values():
            #     pygame.draw.rect(self.world, (0, 255, 0), r, 1)
            
            # antes de escalar al screen
            for r in room._door_trigger_rects().values():
                pygame.draw.rect(self.world, (0,255,0), r, 1)


            # -------- ESCALADO world -> screen --------
            scaled = pygame.transform.scale(
                self.world,
                (self.cfg.SCREEN_W * self.cfg.SCREEN_SCALE,
                 self.cfg.SCREEN_H * self.cfg.SCREEN_SCALE)
            )
            self.screen.blit(scaled, (0, 0))

            # -------- UI: Seed + ayuda --------
            seed_text = self.ui_font.render(f"Seed: {self.current_seed}", True, (230, 230, 230))
            help_text = self.ui_font.render("R: rejugar seed  |  N: nueva seed", True, (200, 200, 200))
            self.screen.blit(seed_text, (200, 100))
            self.screen.blit(help_text, (0, 100))

            # -------- Minimapa --------
            mm = self.minimap.render(self.dungeon)
            margin = 16
            self.screen.blit(mm, (self.screen.get_width() - mm.get_width() - margin, 100))

            # -------- Flip --------
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)
