# CODIGO/Game.py
import sys
import pygame
from Config import Config
from Tileset import Tileset
from Player import Player
from Dungeon import Dungeon
from Minimap import Minimap
from Projectile import ProjectileGroup
from Shop import Shop
from Shopkeeper import Shopkeeper
from HudPanels import HudPanels


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
        pygame.mouse.set_visible(False)
        self._cursor_surface = self._create_cursor_surface()

        # ---------- UI ----------
        self.ui_font = pygame.font.SysFont(None, 18)
        self._coin_icon = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(self._coin_icon, (255, 215, 0), (8, 8), 6)
        pygame.draw.circle(self._coin_icon, (160, 120, 0), (8, 8), 6, 1)
        pygame.draw.line(self._coin_icon, (160, 120, 0), (6, 8), (10, 8), 1)
        self.current_seed: int | None = None

        # --- Tienda ---
        self.shop = Shop(font=self.ui_font)

        # --- HUD ---
        self.hud_panels = HudPanels()
        # Ajusta posiciones/escala desde fuera, por ejemplo:
        # self.hud_panels.inventory_panel_position.update(nuevo_x, nuevo_y)

        # ---------- Recursos ----------
        self.tileset = Tileset()
        self.minimap = Minimap(cell=16, padding=8)

        # ---------- Estado runtime ----------
        self.projectiles = ProjectileGroup()          # balas del jugador
        self.enemy_projectiles = ProjectileGroup()    # balas de enemigos
        self.door_cooldown = 0.0
        self.running = True
        self.debug_draw_doors = cfg.DEBUG_DRAW_DOOR_TRIGGERS

        # ---------- Arranque de run ----------
        self.start_new_run()  # crea dungeon, posiciona player, limpia estado

    # ------------------------------------------------------------------ #
    # Nueva partida / regenerar dungeon (misma o nueva seed)
    # ------------------------------------------------------------------ #
    def start_new_run(self, seed: int | None = None, dungeon_params: dict | None = None) -> None:
        """
        Crea una nueva dungeon con la seed dada (o aleatoria si None),
        reubica al jugador y resetea estado de runtime.
        """
        params = self.cfg.dungeon_params()
        if dungeon_params:
            params = {**params, **dungeon_params}

        self.dungeon = Dungeon(**params, seed=seed)
        self.current_seed = self.dungeon.seed
        pygame.display.set_caption(f"Roguelike — Seed {self.current_seed}")

        # preparar inventario de la tienda para esta seed
        if hasattr(self, "shop"):
            self.shop.close()
            self.shop.configure_for_seed(self.current_seed)

        # marcar room inicial como explorado
        self.dungeon.explored = set()
        self.dungeon.explored.add((self.dungeon.i, self.dungeon.j))

        # Jugador (crear o reubicar al centro del cuarto actual)
        room = self.dungeon.current_room
        px, py = room.center_px()
        spawn_x = px - Player.HITBOX_SIZE[0] / 2
        spawn_y = py - Player.HITBOX_SIZE[1] / 2
        if not hasattr(self, "player"):
            self.player = Player(spawn_x, spawn_y)
        else:
            self.player.x, self.player.y = spawn_x, spawn_y
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

        pygame.mouse.set_visible(True)
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
                elif e.key == pygame.K_m:
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
        player_died = self._handle_collisions(room)
        if player_died:
            return
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

    def _handle_collisions(self, room) -> bool:
        if not hasattr(room, "enemies"):
            return False
        gold_earned = 0
        for projectile in self.projectiles:
            if not projectile.alive:
                continue
            r_proj = projectile.rect()
            for enemy in room.enemies:
                if r_proj.colliderect(enemy.rect()):
                    if hasattr(enemy, "take_damage"):
                        enemy.take_damage(1, (projectile.dx, projectile.dy))
                    else:
                        enemy.hp -= 1
                    projectile.alive = False
                    break
        player_rect = self.player.rect()
        player_invulnerable = getattr(self.player, "is_invulnerable", lambda: False)()
        for enemy in room.enemies:
            if not player_rect.colliderect(enemy.rect()):
                continue
            self._separate_player_enemy(enemy, room)
            contact_damage = getattr(enemy, "contact_damage", 0)
            if contact_damage <= 0:
                continue
            if player_invulnerable:
                continue
            took_hit = False
            if hasattr(self.player, "take_damage"):
                took_hit = bool(self.player.take_damage(contact_damage))
            if took_hit:
                player_invulnerable = getattr(self.player, "is_invulnerable", lambda: False)()
        for projectile in self.enemy_projectiles:
            if not projectile.alive:
                continue
            if projectile.ignore_player_timer > 0.0:
                continue
            if not projectile.rect().colliderect(player_rect):
                continue
            if player_invulnerable:
                remaining_iframes = getattr(self.player, "invulnerable_timer", 0.0)
                projectile.ignore_player_timer = max(
                    projectile.ignore_player_timer,
                    remaining_iframes + 0.05,
                )
                continue
            took_hit = False
            if hasattr(self.player, "take_damage"):
                took_hit = bool(self.player.take_damage(1))
            if took_hit:
                projectile.alive = False
                player_invulnerable = getattr(self.player, "is_invulnerable", lambda: False)()
            else:
                projectile.alive = False

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
        self.enemy_projectiles.prune()
        if hasattr(room, "refresh_lock_state"):
            room.refresh_lock_state()
        self._update_room_lock(room)
        if getattr(self.player, "hp", 1) <= 0:
            self._handle_player_death(room)
            return True
        return False

    def _separate_player_enemy(self, enemy, room) -> None:
        player_rect = self.player.rect()
        if not player_rect.colliderect(enemy.rect()):
            return

        enemy_rect = enemy.rect()
        px, py = player_rect.center
        ex, ey = enemy_rect.center
        primary_axis = 'x' if abs(ex - px) >= abs(ey - py) else 'y'

        for axis in (primary_axis, 'y' if primary_axis == 'x' else 'x'):
            original_pos = enemy.x if axis == 'x' else enemy.y
            direction = 1 if ((ex - px) if axis == 'x' else (ey - py)) >= 0 else -1
            moved = False
            limit = max(enemy.w, enemy.h) + 2
            for _ in range(limit):
                if axis == 'x':
                    enemy.x += direction
                else:
                    enemy.y += direction
                if enemy._collides(room):
                    if axis == 'x':
                        enemy.x -= direction
                    else:
                        enemy.y -= direction
                    break
                if not player_rect.colliderect(enemy.rect()):
                    moved = True
                    break
            if moved:
                push_dir = (
                    enemy.rect().centerx - player_rect.centerx,
                    enemy.rect().centery - player_rect.centery,
                )
                if hasattr(enemy, "take_damage"):
                    enemy.take_damage(0, push_dir, stun_duration=0.0, knockback_strength=120.0)
                return
            if axis == 'x':
                enemy.x = original_pos
            else:
                enemy.y = original_pos

        # Último recurso: reposicionar a borde del jugador
        enemy_rect = enemy.rect()
        ex, ey = enemy_rect.center
        if abs(ex - px) >= abs(ey - py):
            if ex >= px:
                enemy.x = player_rect.right
            else:
                enemy.x = player_rect.left - enemy.w
        else:
            if ey >= py:
                enemy.y = player_rect.bottom
            else:
                enemy.y = player_rect.top - enemy.h

    def _handle_player_death(self, room) -> None:
        if not hasattr(self.player, "lose_life"):
            seed = self.current_seed
            self.start_new_run(seed=seed)
            return
        can_continue = bool(self.player.lose_life())
        if not can_continue:
            seed = self.current_seed
            self.start_new_run(seed=seed)
            return

        if hasattr(self.player, "respawn"):
            self.player.respawn()
        else:
            max_hp = getattr(self.player, "max_hp", 1)
            self.player.hp = max_hp
            invuln = getattr(self.player, "post_hit_invulnerability", 0.0)
            self.player.invulnerable_timer = max(getattr(self.player, "invulnerable_timer", 0.0), invuln)

        if hasattr(room, "center_px"):
            px, py = room.center_px()
            self.player.x = px - self.player.w / 2
            self.player.y = py - self.player.h / 2

        self.projectiles.clear()
        self.enemy_projectiles.clear()
        self.door_cooldown = 0.25

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
        self.world.fill(self.cfg.COLOR_BG)
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

        self.hud_panels.blit_inventory_panel(self.screen)

        lives_remaining = getattr(self.player, "lives", 0)
        max_lives = getattr(self.player, "max_lives", self.cfg.PLAYER_START_LIVES)
        lives_text = self.ui_font.render(
            f"Vidas: {lives_remaining}/{max_lives}", True, (255, 120, 120)
        )
        hits_remaining_life_fn = getattr(self.player, "hits_remaining_this_life", None)
        if callable(hits_remaining_life_fn):
            hits_remaining = hits_remaining_life_fn()
        else:
            hits_remaining = max(0, getattr(self.player, "hp", 0))
        hits_text = self.ui_font.render(
            f"Golpes restantes vida: {hits_remaining}", True, (255, 180, 120)
        )
        gold_amount = getattr(self.player, "gold", 0)
        gold_text = self.ui_font.render(f"Monedas: {gold_amount}", True, (255, 240, 180))
        seed_text = self.ui_font.render(f"Seed: {self.current_seed}", True, (230, 230, 230))
        help_text = self.ui_font.render("R: rejugar seed  |  N: nueva seed", True, (200, 200, 200))

        text_x, text_y = self.hud_panels.inventory_content_anchor()
        line_gap = 6

        self.screen.blit(lives_text, (text_x, text_y))
        text_y += lives_text.get_height() + line_gap

        self.screen.blit(hits_text, (text_x, text_y))
        text_y += hits_text.get_height() + line_gap

        coin_x = text_x
        coin_y = text_y
        self.screen.blit(self._coin_icon, (coin_x, coin_y))
        self.screen.blit(gold_text, (coin_x + self._coin_icon.get_width() + 6, coin_y))
        text_y += max(self._coin_icon.get_height(), gold_text.get_height()) + line_gap

        self.screen.blit(seed_text, (text_x, text_y))
        text_y += seed_text.get_height() + line_gap

        self.screen.blit(help_text, (text_x, text_y))

        minimap_surface = self.minimap.render(self.dungeon)
        margin = 16
        minimap_position = (
            self.screen.get_width() - minimap_surface.get_width() - margin,
            100,
        )
        self.hud_panels.blit_minimap_panel(self.screen, minimap_surface, minimap_position)

        self.hud_panels.blit_corner_panel(self.screen)

        mx, my = pygame.mouse.get_pos()
        cursor_rect = self._cursor_surface.get_rect(center=(mx, my))
        self.screen.blit(self._cursor_surface, cursor_rect.topleft)

        pygame.display.flip()

    def _create_cursor_surface(self) -> pygame.Surface:
        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        center = (16, 16)
        outer_radius = 12
        inner_radius = 4
        color = (60, 170, 255)
        pygame.draw.circle(surface, color, center, outer_radius, 2)
        pygame.draw.circle(surface, color, center, inner_radius, 0)
        pygame.draw.line(surface, color, (center[0] - outer_radius, center[1]), (center[0] - inner_radius - 1, center[1]), 2)
        pygame.draw.line(surface, color, (center[0] + outer_radius, center[1]), (center[0] + inner_radius + 1, center[1]), 2)
        pygame.draw.line(surface, color, (center[0], center[1] - outer_radius), (center[0], center[1] - inner_radius - 1), 2)
        pygame.draw.line(surface, color, (center[0], center[1] + outer_radius), (center[0], center[1] + inner_radius + 1), 2)
        return surface
