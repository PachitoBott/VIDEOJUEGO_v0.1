# CODIGO/Game.py
import sys
import pygame
from typing import Optional

from Config import Config
from Tileset import Tileset
from Player import Player
from Dungeon import Dungeon
from Minimap import Minimap
from Projectile import ProjectileGroup
from Shop import Shop
from Shopkeeper import Shopkeeper
from AssetPack import AssetPack


class Game:
    def __init__(self, cfg: Config) -> None:
        pygame.init()
        self.cfg = cfg
        self.assets = AssetPack(cfg.ASSET_PACK_DIR, cfg.ASSET_PACK_MANIFEST, tile_size=cfg.TILE_SIZE)

        # ---------- Ventana ----------
        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_W * cfg.SCREEN_SCALE, cfg.SCREEN_H * cfg.SCREEN_SCALE)
        )
        pygame.display.set_caption("Roguelike — Dungeon + Minimap")
        self.clock = pygame.time.Clock()
        self.world = pygame.Surface((cfg.SCREEN_W, cfg.SCREEN_H))

        # ---------- UI ----------
        self.ui_font = pygame.font.SysFont(None, 18)
        self._coin_icon = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(self._coin_icon, (255, 215, 0), (8, 8), 6)
        pygame.draw.circle(self._coin_icon, (160, 120, 0), (8, 8), 6, 1)
        pygame.draw.line(self._coin_icon, (160, 120, 0), (6, 8), (10, 8), 1)
        self.current_seed: Optional[int] = None
        
        # --- Tienda ---
        self.shop = Shop(font=self.ui_font)

        # ---------- Recursos ----------
        self.tileset = Tileset(assets=self.assets)
        self.minimap = Minimap(cell=16, padding=8)

        # ---------- Estado runtime ----------
        default_proj_sprite = cfg.projectile_sprite_id()
        self.projectiles = ProjectileGroup(assets=self.assets, default_sprite_id=default_proj_sprite)          # balas del jugador
        self.enemy_projectiles = ProjectileGroup(assets=self.assets, default_sprite_id=default_proj_sprite)    # balas de enemigos
        self.door_cooldown = 0.0
        self.running = True
        self.debug_draw_doors = cfg.DEBUG_DRAW_DOOR_TRIGGERS

        # ---------- Arranque de run ----------
        self.start_new_run()  # crea dungeon, posiciona player, limpia estado

    # ------------------------------------------------------------------ #
    # Nueva partida / regenerar dungeon (misma o nueva seed)
    # ------------------------------------------------------------------ #
    def start_new_run(self, seed: Optional[int] = None, dungeon_params: Optional[dict] = None) -> None:
        """
        Crea una nueva dungeon con la seed dada (o aleatoria si None),
        reubica al jugador y resetea estado de runtime.
        """
        params = self.cfg.dungeon_params()
        if dungeon_params:
            params = {**params, **dungeon_params}

        self.dungeon = Dungeon(**params, seed=seed, asset_pack=self.assets)
        self.current_seed = self.dungeon.seed
        pygame.display.set_caption(f"Roguelike — Seed {self.current_seed}")

        # marcar room inicial como explorado
        self.dungeon.explored = set()
        self.dungeon.explored.add((self.dungeon.i, self.dungeon.j))

        # Jugador (crear o reubicar al centro del cuarto actual)
        room = self.dungeon.current_room
        px, py = room.center_px()
        if not hasattr(self, "player"):
            self.player = Player(px - 6, py - 6, asset_pack=self.assets)
        else:
            self.player.x, self.player.y = px - 6, py - 6
            if hasattr(self.player, "set_assets"):
                self.player.set_assets(self.assets)
        if hasattr(self.player, "reset_loadout"):
            self.player.reset_loadout()
        setattr(self.player, "gold", 0)

        # Reset de runtime
        self._reset_runtime_state()

        # ✅ Entrar “formalmente” a la sala inicial (dispara on_enter/Shop si aplica)
        if hasattr(self.dungeon, "enter_initial_room"):
            self.dungeon.enter_initial_room(self.player, self.cfg, ShopkeeperCls=Shopkeeper)

    def _reset_runtime_state(self) -> None:
        self.projectiles.clear()
        self.enemy_projectiles.clear()
        self.door_cooldown = 0.0
        self.locked = False
        self.cleared = False

    # ------------------------------------------------------------------ #
    # Bucle principal
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        self._frame_counter = 0
        while self.running:
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            self.door_cooldown = max(0.0, self.door_cooldown - dt)

            events = self._handle_events()
            self._update_fps_counter()
            self._update(dt, events)
            self._render()

        pygame.quit()
        sys.exit(0)

    def _handle_events(self) -> list:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.running = False
                elif e.key == pygame.K_r:
                    self.start_new_run(seed=self.current_seed)
                elif e.key == pygame.K_n:
                    self.start_new_run(seed=None)
        return events

    def _update_fps_counter(self) -> None:
        self._frame_counter += 1
        if self._frame_counter % 90 == 0:
            pygame.display.set_caption(
                f"Roguelike — Seed {self.current_seed} — FPS {self.clock.get_fps():.1f}"
            )

    def _update(self, dt: float, events: list) -> None:
        room = self.dungeon.current_room
        self._update_player(dt, room)
        self._spawn_room_enemies(room)
        self._update_enemies(dt, room)
        self._update_projectiles(dt, room)
        self._handle_collisions(room)
        self._handle_room_transition(room)
        self._update_shop(events)

    def _update_player(self, dt: float, room) -> None:
        self.player.update(dt, room)
        mx, my = pygame.mouse.get_pos()
        mx //= self.cfg.SCREEN_SCALE
        my //= self.cfg.SCREEN_SCALE
        self.player.try_shoot((mx, my), self.projectiles)

    def _spawn_room_enemies(self, room) -> None:
        if getattr(room, "no_spawn", False):
            return
        cx, cy = self.dungeon.grid_w // 2, self.dungeon.grid_h // 2
        is_start = (self.dungeon.i, self.dungeon.j) == getattr(self.dungeon, "start", (cx, cy))
        if is_start:
            return
        if hasattr(room, "ensure_spawn"):
            pos = (self.dungeon.i, self.dungeon.j)
            depth = 0
            if hasattr(self.dungeon, "room_depth"):
                depth = self.dungeon.room_depth(pos)
            branch_factor = max(0, sum(1 for open_ in getattr(room, "doors", {}).values() if open_) - 2)
            on_main_path = 0
            if hasattr(self.dungeon, "main_path"):
                on_main_path = 1 if pos in self.dungeon.main_path else 0
            difficulty = 1 + depth + branch_factor + (depth // 3) + on_main_path
            room.ensure_spawn(difficulty=difficulty)

    def _update_enemies(self, dt: float, room) -> None:
        if not hasattr(room, "enemies"):
            return
        for enemy in room.enemies:
            enemy.update(dt, self.player, room)
        for enemy in room.enemies:
            enemy.maybe_shoot(dt, self.player, room, self.enemy_projectiles)

    def _update_projectiles(self, dt: float, room) -> None:
        self.projectiles.update(dt, room)
        self.enemy_projectiles.update(dt, room)

    def _handle_collisions(self, room) -> None:
        if not hasattr(room, "enemies"):
            return
        gold_earned = 0
        for projectile in self.projectiles:
            if not projectile.alive:
                continue
            r_proj = projectile.rect()
            for enemy in room.enemies:
                if r_proj.colliderect(enemy.rect()):
                    enemy.hp -= 1
                    projectile.alive = False
                    break
        survivors = []
        for enemy in room.enemies:
            if getattr(enemy, "hp", 1) > 0:
                survivors.append(enemy)
            else:
                gold_earned += getattr(enemy, "gold_reward", 0)
        if gold_earned:
            current_gold = getattr(self.player, "gold", 0)
            setattr(self.player, "gold", current_gold + gold_earned)
        room.enemies = survivors
        self.projectiles.prune()
        if hasattr(room, "refresh_lock_state"):
            room.refresh_lock_state()
        self._update_room_lock(room)

    def _handle_room_transition(self, room) -> None:
        if not hasattr(room, "check_exit"):
            return
        if getattr(room, "locked", False):
            return
        if self.door_cooldown > 0.0:
            return

        direction = room.check_exit(self.player)
        if not direction or not self.dungeon.can_move(direction):
            return

        if hasattr(self.dungeon, "move_and_enter"):
            moved = self.dungeon.move_and_enter(direction, self.player, self.cfg, ShopkeeperCls=Shopkeeper)
        else:
            self.dungeon.move(direction)
            moved = True
        if not moved:
            return

        self.player.x, self.player.y = self.dungeon.entry_position(
            direction, self.player.w, self.player.h
        )
        self.dungeon.explored.add((self.dungeon.i, self.dungeon.j))
        self.door_cooldown = 0.25
        self.projectiles.clear()
        self.enemy_projectiles.clear()

        new_room = self.dungeon.current_room
        self._spawn_room_enemies(new_room)
        self._update_room_lock(new_room)

    def _update_room_lock(self, room) -> None:
        if not hasattr(room, "enemies") or not hasattr(room, "cleared"):
            return
        cx, cy = self.dungeon.grid_w // 2, self.dungeon.grid_h // 2
        is_start = (self.dungeon.i, self.dungeon.j) == getattr(self.dungeon, "start", (cx, cy))
        room.locked = (not is_start) and (len(room.enemies) > 0) and (not room.cleared)

    def _update_shop(self, events: list) -> None:
        current_room = self.dungeon.current_room
        if hasattr(current_room, "handle_events"):
            current_room.handle_events(
                events,
                self.player,
                self.shop,
                self.world,
                self.ui_font,
                self.cfg.SCREEN_SCALE,
            )

    def _render(self) -> None:
        self._render_world()
        self._render_ui()

    def _render_world(self) -> None:
        self.world.fill((0, 0, 0))
        room = self.dungeon.current_room
        room.draw(self.world, self.tileset)

        if hasattr(room, "enemies"):
            for enemy in room.enemies:
                enemy.draw(self.world)

        self.player.draw(self.world)
        self.projectiles.draw(self.world)
        self.enemy_projectiles.draw(self.world)

        if self.debug_draw_doors and hasattr(room, "_door_trigger_rects"):
            self._draw_debug_door_triggers(room)

        if hasattr(room, "draw_overlay"):
            room.draw_overlay(self.world, self.ui_font, self.player, self.shop)
        self.shop.draw(self.world)

    def _draw_debug_door_triggers(self, room) -> None:
        for rect in room._door_trigger_rects().values():
            pygame.draw.rect(self.world, (0, 255, 0), rect, 1)

    def _render_ui(self) -> None:
        scaled = pygame.transform.scale(
            self.world,
            (self.cfg.SCREEN_W * self.cfg.SCREEN_SCALE,
             self.cfg.SCREEN_H * self.cfg.SCREEN_SCALE)
        )
        self.screen.blit(scaled, (0, 0))

        gold_amount = getattr(self.player, "gold", 0)
        gold_text = self.ui_font.render(f"Monedas: {gold_amount}", True, (255, 240, 180))
        self.screen.blit(self._coin_icon, (305, 100))
        self.screen.blit(gold_text, (320, 100))
        seed_text = self.ui_font.render(f"Seed: {self.current_seed}", True, (230, 230, 230))
        help_text = self.ui_font.render("R: rejugar seed  |  N: nueva seed", True, (200, 200, 200))
        self.screen.blit(seed_text, (200, 100))
        self.screen.blit(help_text, (0, 100))

        minimap_surface = self.minimap.render(self.dungeon)
        margin = 16
        self.screen.blit(
            minimap_surface,
            (self.screen.get_width() - minimap_surface.get_width() - margin, 100)
        )

        pygame.display.flip()
