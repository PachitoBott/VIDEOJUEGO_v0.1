# CODIGO/Game.py
import math
import sys
from collections.abc import Callable
from time import perf_counter
from pathlib import Path

import pygame

from Config import Config
from StartMenu import StartMenu
from Tileset import Tileset
from Player import Player
from Dungeon import Dungeon
from Minimap import Minimap
from Projectile import ProjectileGroup
from Shop import Shop
from Shopkeeper import Shopkeeper
from HudPanels import HudPanels
from PauseMenu import PauseMenu, PauseMenuButton
from GameOverScreen import GameOverScreen
from Statistics import StatisticsManager


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
        self._battery_states = self._load_battery_states()
        self._life_battery_highlight = pygame.Color(110, 200, 255)
        # Ajusta este offset para reposicionar las vidas en el HUD.
        self._life_battery_offset = pygame.Vector2(0, 300)
        self.current_seed: int | None = None

        # --- Tienda ---
        self.shop = Shop(font=self.ui_font, on_gold_spent=self._register_gold_spent)

        # --- HUD ---
        self.hud_panels = HudPanels()
        # Ajusta posiciones/escala desde fuera, por ejemplo:
        # self.hud_panels.inventory_panel_position.update(nuevo_x, nuevo_y)
        if hasattr(self.hud_panels, "set_minimap_anchor"):
            # Centra el minimapa dentro del panel de esquina para que quede cubierto.
            self.hud_panels.set_minimap_anchor("top-right",  margin=(80, 140))

        # ---------- Recursos ----------
        self.tileset = Tileset()
        self.minimap = Minimap(cell=16, padding=8)

        # ---------- Estado runtime ----------
        self.projectiles = ProjectileGroup()          # balas del jugador
        self.enemy_projectiles = ProjectileGroup()    # balas de enemigos
        self.door_cooldown = 0.0
        self.running = True
        self.debug_draw_doors = cfg.DEBUG_DRAW_DOOR_TRIGGERS
        self._skip_frame = False


        # --- Menú de pausa ---
        self.pause_menu_buttons: list[PauseMenuButton] = [
            PauseMenuButton("Reanudar", "resume"),
            PauseMenuButton("Menú principal", "main_menu"),
            PauseMenuButton("Salir del juego", "quit"),
        ]
        self.pause_menu_handlers: dict[str, Callable[[], bool | None]] = {}

        # ---------- Estadísticas ----------
        self.stats_manager = StatisticsManager()
        self._run_start_time: float | None = None
        self._stats_pending_reason: str | None = None
        self._run_gold_spent: int = 0
        self._run_kills: int = 0

    # ------------------------------------------------------------------ #
    # Nueva partida / regenerar dungeon (misma o nueva seed)
    # ------------------------------------------------------------------ #
    def start_new_run(self, seed: int | None = None, dungeon_params: dict | None = None) -> None:
        """
        Crea una nueva dungeon con la seed dada (o aleatoria si None),
        reubica al jugador y resetea estado de runtime.
        """
        finalize_reason = self._stats_pending_reason or "restart"
        self._finalize_run_statistics(finalize_reason)
        self._stats_pending_reason = None

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

        self._run_start_time = perf_counter()

    def _reset_runtime_state(self) -> None:
        self.projectiles.clear()
        self.enemy_projectiles.clear()
        self.door_cooldown = 0.0
        self.locked = False
        self.cleared = False
        self._run_gold_spent = 0
        self._run_kills = 0

    def _register_gold_spent(self, amount: int) -> None:
        if amount <= 0:
            return
        self._run_gold_spent = max(0, self._run_gold_spent) + int(amount)

    def _finalize_run_statistics(self, reason: str | None = None) -> None:
        if self._run_start_time is None:
            return

        duration = max(0.0, perf_counter() - self._run_start_time)
        rooms_explored = 0
        dungeon = getattr(self, "dungeon", None)
        if dungeon is not None and hasattr(dungeon, "explored"):
            try:
                rooms_explored = len(dungeon.explored)
            except TypeError:
                rooms_explored = 0
        gold = 0
        player = getattr(self, "player", None)
        if player is not None:
            gold = int(getattr(player, "gold", 0))
        gold_spent = max(0, int(self._run_gold_spent))
        gold_obtained = max(0, gold) + gold_spent

        try:
            self.stats_manager.record_run(
                duration_seconds=duration,
                rooms_explored=rooms_explored,
                gold_obtained=gold_obtained,
                gold_spent=gold_spent,
            )
        except Exception as exc:  # pragma: no cover - logging best effort
            print(f"[WARN] No se pudo guardar la estadística: {exc}", file=sys.stderr)

        self._run_start_time = None
        self._stats_pending_reason = None
        self._run_gold_spent = 0

    # ------------------------------------------------------------------ #
    # Bucle principal
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        if not self._open_start_menu():
            pygame.mouse.set_visible(True)
            pygame.quit()
            sys.exit(0)

        self._frame_counter = 0
        while self.running:
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            self.door_cooldown = max(0.0, self.door_cooldown - dt)

            events = self._handle_events()
            if self._skip_frame:
                self._skip_frame = False
                continue
            self._update_fps_counter()
            self._update(dt, events)
            self._render()

        pygame.mouse.set_visible(True)
        self._finalize_run_statistics("shutdown")
        pygame.quit()
        sys.exit(0)

    def _handle_events(self) -> list:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                self._finalize_run_statistics("quit")
                self.running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self._show_pause_menu()
                    return []
                elif e.key == pygame.K_m:
                    self._stats_pending_reason = "manual_same_seed"
                    self.start_new_run(seed=self.current_seed)
                elif e.key == pygame.K_n:
                    self._stats_pending_reason = "manual_new_seed"
                    self.start_new_run(seed=None)
        return events

    def _open_start_menu(self) -> bool:
        pygame.mouse.set_visible(True)
        start_menu = StartMenu(self.screen, self.cfg, stats_manager=self.stats_manager)
        menu_result = start_menu.run()
        if not menu_result.start_game:
            if self._run_start_time is not None:
                reason = self._stats_pending_reason or "menu_exit"
                self._finalize_run_statistics(reason)
                self._stats_pending_reason = None
            self.running = False
            return False
        pygame.mouse.set_visible(False)
        self.start_new_run(seed=menu_result.seed)
        self._skip_frame = True
        return True

    def add_pause_menu_button(
        self,
        button: PauseMenuButton,
        *,
        handler: Callable[[], bool | None] | None = None,
    ) -> None:
        """Permite añadir botones adicionales al menú de pausa."""

        self.pause_menu_buttons.append(button)
        if handler is not None:
            self.pause_menu_handlers[button.action] = handler

    def _show_pause_menu(self) -> None:
        pygame.mouse.set_visible(True)
        background = self.screen.copy()
        pause_menu = PauseMenu(self.screen, buttons=self.pause_menu_buttons)
        action = pause_menu.run(background=background)
        keep_playing = self._handle_pause_action(action)
        if keep_playing and self.running:
            pygame.mouse.set_visible(False)
        self.clock.tick(self.cfg.FPS)
        self._skip_frame = True

    def _handle_pause_action(self, action: str) -> bool:
        if action == "resume":
            return True
        if action == "main_menu":
            self._stats_pending_reason = "menu_restart"
            return self._open_start_menu()
        if action == "quit":
            self._finalize_run_statistics("quit")
            self.running = False
            return False

        handler = self.pause_menu_handlers.get(action)
        if handler is not None:
            result = handler()
            if result is False:
                self._finalize_run_statistics(f"handler:{action}")
                self.running = False
                return False
            return True

        return True

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
        notify = getattr(self.player, "notify_enemy_shot", None)
        for enemy in room.enemies:
            fired = enemy.maybe_shoot(dt, self.player, room, self.enemy_projectiles)
            if fired and callable(notify):
                notify()

    def _update_projectiles(self, dt: float, room) -> None:
        self.projectiles.update(dt, room)
        self.enemy_projectiles.update(dt, room)

    def _handle_collisions(self, room) -> bool:
        if not hasattr(room, "enemies"):
            return False
        gold_earned = 0
        initial_enemy_count = len(getattr(room, "enemies", ()))
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
                    self._apply_projectile_effects(projectile, enemy)
                    projectile.alive = False
                    break
        player_rect = self.player.rect()
        player_invulnerable = getattr(self.player, "is_invulnerable", lambda: False)()
        phase_active = getattr(self.player, "is_phase_active", None)
        phase_through = phase_active() if callable(phase_active) else False
        for enemy in room.enemies:
            if not player_rect.colliderect(enemy.rect()):
                continue
            if phase_through:
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
        defeated_enemies = max(0, initial_enemy_count - len(survivors))
        if defeated_enemies:
            self._run_kills = max(0, self._run_kills) + defeated_enemies
            try:
                self.stats_manager.record_kill(defeated_enemies)
            except Exception as exc:  # pragma: no cover - registro best effort
                print(f"[WARN] No se pudo guardar kills: {exc}", file=sys.stderr)
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

    def _apply_projectile_effects(self, projectile, enemy) -> None:
        effects = getattr(projectile, "effects", ())
        if not effects:
            return
        for effect in effects:
            if not isinstance(effect, dict):
                continue
            etype = effect.get("type")
            if etype == "shock":
                slow = float(effect.get("slow", 0.2))
                duration = float(effect.get("duration", 0.6))
                applier = getattr(enemy, "apply_slow", None)
                if callable(applier):
                    applier(slow, duration)

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
        can_continue = False
        if hasattr(self.player, "lose_life"):
            try:
                can_continue = bool(self.player.lose_life())
            except TypeError:
                can_continue = False

        if can_continue:
            if hasattr(self.player, "respawn"):
                self.player.respawn()
            else:
                max_hp = getattr(self.player, "max_hp", 1)
                self.player.hp = max_hp
                invuln = getattr(self.player, "post_hit_invulnerability", 0.0)
                self.player.invulnerable_timer = max(
                    getattr(self.player, "invulnerable_timer", 0.0), invuln
                )

            if hasattr(room, "center_px"):
                px, py = room.center_px()
                self.player.x = px - self.player.w / 2
                self.player.y = py - self.player.h / 2

            self.projectiles.clear()
            self.enemy_projectiles.clear()
            self.door_cooldown = 0.25
            return

        summary = self._collect_run_summary()
        self._record_stats_death()
        self._finalize_run_statistics("player_death")

        action = self._show_game_over_screen(summary)

        if action == "quit":
            self.running = False
            return

        if action == "main_menu":
            if not self._open_start_menu():
                self.running = False
            return

        # Cualquier otra acción reinicia la partida con nueva seed.
        self.start_new_run(seed=None)

    def _record_stats_death(self) -> None:
        try:
            self.stats_manager.record_death()
        except Exception as exc:  # pragma: no cover - registro best effort
            print(f"[WARN] No se pudo guardar muerte: {exc}", file=sys.stderr)

    def _collect_run_summary(self) -> dict[str, int]:
        rooms_explored = 0
        dungeon = getattr(self, "dungeon", None)
        if dungeon is not None and hasattr(dungeon, "explored"):
            try:
                rooms_explored = len(dungeon.explored)
            except TypeError:
                rooms_explored = 0

        gold = 0
        player = getattr(self, "player", None)
        if player is not None:
            try:
                gold = int(getattr(player, "gold", 0))
            except (TypeError, ValueError):
                gold = 0

        gold_spent = max(0, int(self._run_gold_spent))
        coins_obtained = max(0, gold) + gold_spent

        return {
            "coins": coins_obtained,
            "kills": max(0, int(self._run_kills)),
            "rooms": max(0, rooms_explored),
        }

    def _show_game_over_screen(self, summary: dict[str, int]) -> str:
        pygame.mouse.set_visible(True)
        background = self.screen.copy()
        game_over = GameOverScreen(self.screen)
        action = game_over.run(summary, background=background)

        if action not in ("main_menu", "quit"):
            pygame.mouse.set_visible(False)

        self.clock.tick(self.cfg.FPS)
        self._skip_frame = True
        return action

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
        gold_amount = getattr(self.player, "gold", 0)
        gold_text = self.ui_font.render(f"Monedas: {gold_amount}", True, (255, 240, 180))
        seed_text = self.ui_font.render(f"Seed: {self.current_seed}", True, (230, 230, 230))
        help_text = self.ui_font.render("R: rejugar seed  |  N: nueva seed", True, (200, 200, 200))

        text_x, text_y = self.hud_panels.inventory_content_anchor()
        line_gap = 6

        battery_origin = (
        text_x + int(self._life_battery_offset.x),
         text_y + int(self._life_battery_offset.y),
        )
        batteries_rect = self._blit_life_batteries(self.screen, battery_origin)
        if batteries_rect.height:
         text_y = batteries_rect.bottom + line_gap
        
        self.screen.blit(lives_text, (text_x, text_y))
        text_y += lives_text.get_height() + line_gap

        coin_x = text_x
        coin_y = text_y
        self.screen.blit(self._coin_icon, (coin_x, coin_y))
        self.screen.blit(gold_text, (coin_x + self._coin_icon.get_width() + 6, coin_y))
        text_y += max(self._coin_icon.get_height(), gold_text.get_height()) + line_gap

        self.screen.blit(seed_text, (text_x, text_y))
        text_y += seed_text.get_height() + line_gap

        self.screen.blit(help_text, (text_x, text_y))

        minimap_surface = self.minimap.render(self.dungeon)
        minimap_position = self.hud_panels.compute_minimap_position(self.screen, minimap_surface)
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

    def _load_battery_states(self) -> list[pygame.Surface]:
        sprite_path = Path(__file__).resolve().parent.parent / "assets/ui/Baterias_Vida.png"
        try:
            sheet = pygame.image.load(sprite_path.as_posix()).convert_alpha()
        except pygame.error as exc:  # pragma: no cover - carga de recursos
            raise FileNotFoundError(f"No se pudo cargar el sprite de baterías en {sprite_path}") from exc

        columns = 4
        frame_width = sheet.get_width() // columns
        frame_height = sheet.get_height()
        frames: list[pygame.Surface] = []
        for index in range(columns):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), pygame.Rect(index * frame_width, 0, frame_width, frame_height))
            frames.append(frame)

        if not frames:
            raise ValueError("El sprite de baterías no contiene frames válidos")

        if len(frames) >= 4:
            empty_frame = frames[-1]
            filled_frames = frames[:-1]
        else:
            empty_frame = frames[0].copy()
            darken = pygame.Surface(empty_frame.get_size(), pygame.SRCALPHA)
            darken.fill((60, 60, 60, 255))
            empty_frame.blit(darken, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            filled_frames = frames

        return [empty_frame] + filled_frames

    def _player_hits_remaining(self) -> int:
        hits_remaining_life_fn = getattr(self.player, "hits_remaining_this_life", None)
        if callable(hits_remaining_life_fn):
            try:
                return int(hits_remaining_life_fn())
            except (TypeError, ValueError):
                pass
        return max(0, int(getattr(self.player, "hp", 0)))

    def _battery_surface(self, max_hp: int, hp: int) -> pygame.Surface:
        if not self._battery_states:
            return pygame.Surface((0, 0), pygame.SRCALPHA)

        if max_hp <= 0:
            return self._battery_states[0]

        hp_clamped = max(0, min(max_hp, hp))
        if hp_clamped <= 0:
            return self._battery_states[0]

        tiers = len(self._battery_states) - 1
        ratio = hp_clamped / max_hp
        frame_index = max(1, min(tiers, math.ceil(ratio * tiers)))
        return self._battery_states[frame_index]

    def _blit_life_batteries(self, surface: pygame.Surface, origin: tuple[int, int]) -> pygame.Rect:
        if not hasattr(self, "player"):
            return pygame.Rect(origin, (0, 0))

        max_lives = max(0, int(getattr(self.player, "max_lives", 0)))
        if max_lives <= 0:
            return pygame.Rect(origin, (0, 0))

        lives_remaining = max(0, int(getattr(self.player, "lives", 0)))
        max_hp = max(1, int(getattr(self.player, "max_hp", 1)))
        hits_remaining = max(0, min(max_hp, self._player_hits_remaining()))

        lost_lives = max(0, min(max_lives, max_lives - lives_remaining))
        icons: list[pygame.Surface] = []
        for index in range(max_lives):
            if index < lost_lives or lives_remaining <= 0:
                hp_value = 0
            elif index == lost_lives:
                hp_value = hits_remaining
            else:
                hp_value = max_hp

            icon = self._battery_surface(max_hp, hp_value).copy()
            if index == lost_lives and lives_remaining > 0:
                pygame.draw.rect(
                    icon,
                    self._life_battery_highlight,
                    icon.get_rect(),
                    3,
                    border_radius=6,
                )
            icons.append(icon)

        if not icons:
            return pygame.Rect(origin, (0, 0))

        icon_w, icon_h = icons[0].get_size()
        columns = 2
        max_rows = 5
        spacing_x = 6
        spacing_y = 6
        rows = min(max_rows, math.ceil(len(icons) / columns))

        ox, oy = origin
        max_icons = min(len(icons), columns * rows)
        for idx, icon_surface in enumerate(icons[:max_icons]):
            col = idx % columns
            row = idx // columns
            x = ox + col * (icon_w + spacing_x)
            y = oy + row * (icon_h + spacing_y)
            surface.blit(icon_surface, (x, y))

        used_columns = columns if max_icons >= columns else max_icons
        width = used_columns * icon_w + max(0, used_columns - 1) * spacing_x
        height = rows * icon_h + max(0, rows - 1) * spacing_y

        last_row_count = max_icons % columns or min(max_icons, columns)
        if max_icons >= columns:
            width_columns = columns
        else:
            width_columns = last_row_count
        width = width_columns * icon_w + max(0, width_columns - 1) * spacing_x
        height = rows * icon_h + max(0, rows - 1) * spacing_y

        return pygame.Rect(ox, oy, width, height)
