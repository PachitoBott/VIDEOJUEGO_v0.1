# CODIGO/Game.py
import math
import random
import sys
from collections.abc import Callable
from time import perf_counter
from pathlib import Path

import pygame

from Config import Config
from StartMenu import StartMenu
from Cinamatic import Cinamatic
from Tileset import Tileset
from Player import Player
from Dungeon import Dungeon
from Minimap import Minimap
from Projectile import ProjectileGroup
from Shop import Shop
from Shopkeeper import Shopkeeper
from HudPanels import HudPanels
from LootNotifications import LootNotificationManager
from PauseMenu import PauseMenu, PauseMenuButton
from GameOverScreen import GameOverScreen
from Statistics import StatisticsManager
from Pickup import MicrochipPickup, LootPickup
from VFX import VFXManager
from asset_paths import WEAPON_SPRITE_FILENAMES, assets_dir, weapon_sprite_path
from loot_tables import ENEMY_LOOT_TABLE
from rewards import apply_reward_entry
from Bosses import BossEnemy, DEBUG_BOSS_HP
from Weapons import WeaponFactory


class Game:
    MICROCHIP_SPRITE_NAME = "chip_moneda.png"
    MICROCHIP_ICON_DEFAULT_SCALE = 1.5
    MICROCHIP_PICKUP_SIZE = (12, 12)
    MICROCHIP_VALUE_SCALE = 0.65
    
    # =============================================================================
    # CONFIGURACIÓN DE ARMAS EN EL HUD
    # =============================================================================
    # Aquí puedes ajustar la posición y escala de cada arma cuando aparece en el HUD
    # - offset_x: Desplazamiento horizontal (+ derecha, - izquierda)
    # - offset_y: Desplazamiento vertical (+ abajo, - arriba)
    # - scale: Escala del sprite (1.0 = tamaño normal, >1.0 más grande, <1.0 más pequeño)
    WEAPON_HUD_CONFIG = {
        "short_rifle": {
            "offset_x": -15,
            "offset_y": 35,
            "scale": 1.0,
        },
        "dual_pistols": {
            "offset_x": 10,
            "offset_y": 57,
            "scale": 1.0,
        },
        "light_rifle": {
            "offset_x": -20,
            "offset_y": 20,
            "scale": 1.0,
        },
        "arcane_salvo": {
            "offset_x": -20,
            "offset_y": 9,
            "scale": 1.0,
        },
        "pulse_rifle": {
            "offset_x": -20,
            "offset_y": 15,
            "scale": 1.0,
        },
        "tesla_gloves": {
            "offset_x": 14,
            "offset_y": 60,
            "scale": 0.65,
        },
        "ember_carbine": {
            "offset_x": -20,
            "offset_y": 5,
            "scale": 1.0,
        },
    }
    # =============================================================================
    
    UPGRADE_NAMES = {
        "spd_up": "Mejora de velocidad (+5%)",
        "sprint_core": "Sprint infinito",
        "cdr_charm": "Reducción de cooldowns (menor)",
        "cdr_core": "Reducción de cooldowns (mayor)",
        "dash_core": "Dash desbloqueado",
        "dash_drive": "Dash mejorado (menor cooldown)",
    }
    WEAPON_NAMES = {
        "short_rifle": "Rifle corto",
        "dual_pistols": "Pistolas duales",
        "light_rifle": "Rifle ligero",
        "arcane_salvo": "Salva arcana",
        "pulse_rifle": "Rifle de pulsos",
        "tesla_gloves": "Guantes Tesla",
        "ember_carbine": "Carabina de ascuas",
    }
    CONSUMABLE_NAMES = {
        "heal_small": "Curación pequeña",
        "heal_battery_full": "Batería completa",
    }

    def __init__(self, cfg: Config) -> None:
        pygame.init()
        self.cfg = cfg

        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_W * cfg.SCREEN_SCALE, cfg.SCREEN_H * cfg.SCREEN_SCALE)
        )
        pygame.display.set_caption("Roguelike — Dungeon + Minimap")
        self.clock = pygame.time.Clock()
        self.world = pygame.Surface((cfg.SCREEN_W, cfg.SCREEN_H))
        pygame.mouse.set_visible(False)
        self._cursor_surface = self._create_cursor_surface()
        self._elapsed_time = 0.0

        # Indicadores globales
        self.camera_shake = 0.0
        self._camera_recoil = pygame.Vector2(0.0, 0.0)
        self._fade_surface = pygame.Surface(self.screen.get_size())
        self._fade_surface.fill((0, 0, 0))
        self._fade_alpha = 255.0
        self._fade_direction = -1
        self._fade_bounce = False
        self._fade_speed = 255.0 / 0.2
        self._low_hp_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        self._low_hp_surface.fill((255, 0, 0))
        self._low_hp_base_alpha = 28
        self._low_hp_pulse = 7

        # ---------- UI ----------
        loot_font_path = Path(__file__).resolve().parent / "assets" / "ui" / "VT323-Regular.ttf"
        if loot_font_path.exists():
            self.loot_font = pygame.font.Font(str(loot_font_path), 22)
        else:
            self.loot_font = pygame.font.SysFont("VT323", 22)
        self.ui_font = pygame.font.SysFont(None, 18)
        self.hud_font_large = pygame.font.SysFont("VT323", 32)
        
        # --- Configuración de texto de munición (AJUSTABLE MANUALMENTE) ---
        self.ammo_text_font_size = 48  # Tamaño de la fuente (cambia este número para ajustar el tamaño)
        self.ammo_text_offset_x = 700    # Desplazamiento horizontal desde el centro (positivo = derecha, negativo = izquierda)
        self.ammo_text_offset_y = 410   # Desplazamiento vertical desde el centro (positivo = abajo, negativo = arriba)
        # Cargar fuente VT323 para el texto de munición
        if loot_font_path.exists():
            self.ammo_font = pygame.font.Font(str(loot_font_path), self.ammo_text_font_size)
        else:
            self.ammo_font = pygame.font.SysFont("VT323", self.ammo_text_font_size)
        
        # Panel de vida (fondo para las baterías)
        panel_vidas_path = Path(__file__).resolve().parent.parent / "assets" / "ui" / "panel_vidas.png"
        try:
            panel_original = pygame.image.load(panel_vidas_path.as_posix()).convert_alpha()
            # Escalar el panel a un tamaño razonable (ajusta estos valores si necesitas que sea más grande/pequeño)
            panel_scale_width = 1000
            panel_scale_height= 1000
            self._life_panel_sprite = pygame.transform.smoothscale(panel_original, (panel_scale_width, panel_scale_height))
        except (pygame.error, FileNotFoundError) as e:
            self._life_panel_sprite = None
        
        # --- Configuración de posición de baterías y panel (AJUSTABLE MANUALMENTE) ---
        self.batteries_base_x = 40   # Posición X base de las baterías desde el borde
        self.batteries_base_y = 265   # Posición Y base de las baterías desde el borde
        self.life_panel_offset_x = -500  # Offset del panel desde las baterías (negativo = izquierda)
        self.life_panel_offset_y = -370  # Offset del panel desde las baterías (negativo = arriba)
        icon_source, pickup_sprite = self._create_microchip_sprites()
        self._microchip_icon_source = icon_source
        self._chip_pickup_sprite = pickup_sprite
        self._heal_pickup_sprite = self._create_heal_pickup_sprite()
        self._consumable_pickup_sprite = self._create_consumable_pickup_sprite()
        self._upgrade_pickup_sprite = self._create_upgrade_pickup_sprite()
        self._weapon_pickup_sprite = self._create_weapon_pickup_sprite()
        self._bundle_pickup_sprite = self._create_bundle_pickup_sprite()
        self.microchip_icon_scale = self.MICROCHIP_ICON_DEFAULT_SCALE * 0.42

        self.loot_notifications = LootNotificationManager(self.loot_font)
        self.loot_notifications.set_surface_size(self.screen.get_size())

        # Usa los métodos set_microchip_icon_scale/offset/value_offset para ajustar
        # manualmente la presentación del icono dentro del HUD.
        self._coin_icon = self._scale_microchip_icon(self.microchip_icon_scale)
        self._battery_states = self._load_battery_states()
        self._life_battery_highlight = pygame.Color(110, 200, 255)
        # Ajusta este offset para reposicionar las vidas en el HUD.
        # Incrementa la componente X para mover las barras hacia la derecha
        # (disminúyela para moverlas a la izquierda) y modifica Y para
        # desplazarlas verticalmente.
        self._life_battery_offset = pygame.Vector2(-380, 50)
        # --- Configuración del HUD de armas ---
        self.weapon_icon_offset = pygame.Vector2(60, -30)
        self.weapon_icon_scale = 1.9
        self.weapon_text_margin = 18
        self.weapon_ammo_offset = pygame.Vector2(-35, -110)
        self.weapon_ammo_color = pygame.Color(235, 235, 235)
        self.weapon_ammo_align_center = True
        self._weapon_icons = self._load_weapon_icons()
        self._weapon_icon_cache: dict[tuple[str, float], pygame.Surface] = {}
        self._pickup_icon_cache: dict[str, pygame.Surface] = {}
        
        self.microchip_icon_offset = pygame.Vector2(102, 108)
        self.microchip_value_offset = pygame.Vector2(0, -110)                                                                                           
        self.microchip_value_color = pygame.Color(255, 240, 180)

        # --- Tienda ---
        self.shop = Shop(
            font=self.ui_font, 
            on_gold_spent=self._register_gold_spent,
            on_weapon_purchased=self._handle_shop_weapon_purchase
        )
        self._enemy_loot_table = ENEMY_LOOT_TABLE
        self._enemy_drop_rates = ENEMY_LOOT_TABLE.get("global_drop_rates", {})

        self.hud_panels = HudPanels()
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
        self.projectiles.set_impact_callback(self._handle_projectile_impact)
        self.enemy_projectiles.set_impact_callback(self._handle_projectile_impact)
        self.door_cooldown = 0.0
        self.running = True
        self.debug_draw_doors = cfg.DEBUG_DRAW_DOOR_TRIGGERS
        self.debug_start_in_boss_room = getattr(cfg, "DEBUG_START_IN_BOSS_ROOM", False)
        self._skip_frame = False
        self.vfx = VFXManager()


        # --- Menú de pausa ---
        self.pause_menu_buttons: list[PauseMenuButton] = [
            PauseMenuButton("Reanudar", "resume"),
            PauseMenuButton("Ayuda", "help"),
            PauseMenuButton("Menú principal", "main_menu"),
            PauseMenuButton("Salir del juego", "quit"),
        ]
        self.pause_menu_handlers: dict[str, Callable[[], bool | None]] = {}

        # ---------- Sonidos de pickup ----------
        self._load_pickup_sounds()

        # ---------- Sistema de música de gameplay ----------
        self.gameplay_music_pool: list[Path] = []
        self.current_music_volume = 0.03  # Volumen muy bajo no invasivo (3%)
        self._load_gameplay_music_pool()
        pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)  # Evento cuando termina la música

        # ---------- Estadísticas ----------
        self.stats_manager = StatisticsManager()
        self._run_start_time: float | None = None
        self._stats_pending_reason: str | None = None
        self._run_gold_spent: int = 0
        self._run_kills: int = 0
        self.selected_skin_path: str | None = getattr(cfg, "PLAYER_SPRITES_PATH", None)

        # ---------- Sistema de Runs ----------
        self.completed_runs: int = 0
        self._preserved_player_state: dict | None = None
        self._persistent_upgrades_state: dict | None = None

        # --- Interacción de armas ---
        self.hovered_weapon_pickup = None
        self.prompt_font = pygame.font.Font(Path(__file__).resolve().parent / "assets" / "ui" / "VT323-Regular.ttf", 20)
        self.weapon_factory = WeaponFactory()

    def _bind_room_notifications(self) -> None:
        if not hasattr(self, "dungeon") or not getattr(self, "dungeon", None):
            return
        for room in getattr(self.dungeon, "rooms", {}).values():
            if hasattr(room, "set_notification_callback"):
                room.set_notification_callback(self._push_notification)

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

        # Guardar mejoras obtenidas antes de reiniciar
        self._capture_persistent_upgrades()

        params = self.cfg.dungeon_params()
        if dungeon_params:
            params = {**params, **dungeon_params}

        self.dungeon = Dungeon(**params, seed=seed)
        self.current_seed = self.dungeon.seed
        pygame.display.set_caption(f"Roguelike — Seed {self.current_seed}")
        self._bind_room_notifications()

        self.loot_notifications.clear()

        # preparar inventario de la tienda para esta seed
        if hasattr(self, "shop"):
            self.shop.close()
            self.shop.configure_for_seed(self.current_seed, reset_purchases=True)

        # marcar room inicial como explorado
        self.dungeon.explored = set()
        self.dungeon.explored.add((self.dungeon.i, self.dungeon.j))

        # Jugador (crear o reubicar al centro del cuarto actual)
        room = self.dungeon.current_room
        px, py = room.center_px()
        spawn_x = px - Player.HITBOX_SIZE[0] / 2
        spawn_y = py - Player.HITBOX_SIZE[1] / 2
        if not hasattr(self, "player"):
            self.player = Player(spawn_x, spawn_y, sprite_dir=self.selected_skin_path)
        else:
            self.player.set_skin(self.selected_skin_path)
            self.player.x, self.player.y = spawn_x, spawn_y
        self._bind_player_events()
        if hasattr(self.player, "reset_loadout"):
            self.player.reset_loadout()

        # Restaurar estado preservado si existe (para continuar runs)
        if self._preserved_player_state:
            self._restore_player_state(self._preserved_player_state)
            self._preserved_player_state = None  # Limpiar después de restaurar
        else:
            # Inicialización normal (primera run)
            setattr(self.player, "gold", 100)
            try:
                self.player.shop_purchases = set()
            except Exception:
                pass

        # Aplicar mejoras permanentes acumuladas
        self._apply_persistent_upgrades(self.player)

        # Reset de runtime
        self._reset_runtime_state()

        # ✅ Entrar “formalmente” a la sala inicial (dispara on_enter/Shop si aplica)
        if hasattr(self.dungeon, "enter_initial_room"):
            self.dungeon.enter_initial_room(self.player, self.cfg, ShopkeeperCls=Shopkeeper)

        self._run_start_time = perf_counter()

        if self.debug_start_in_boss_room:
            self._warp_to_boss_room()
        
        # Iniciar música de gameplay
        self._start_gameplay_music()

    def _reset_runtime_state(self) -> None:
        self.projectiles.clear()
        self.enemy_projectiles.clear()
        self.door_cooldown = 0.0
        self.locked = False
        self.cleared = False
        self._run_gold_spent = 0
        self._run_kills = 0
        self.vfx.reset()
        self.camera_shake = 0.0
        self._start_fade_in()

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
            gold = int(getattr(player, "gold", 100000000))
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

    def _preserve_player_state(self) -> dict:
        """
        Captura el estado completo del jugador para preservarlo entre runs.
        Incluye: oro, vida, armas, mejoras, items clave, y todo el progreso.
        """
        if not hasattr(self, "player"):
            return {}

        player = self.player
        state = {
            # Recursos
            "gold": int(getattr(player, "gold", 0)),
            
            # Vida y supervivencia
            "hp": int(getattr(player, "hp", 1)),
            "max_hp": int(getattr(player, "max_hp", 3)),
            "lives": int(getattr(player, "lives", 3)),
            "max_lives": int(getattr(player, "max_lives", 3)),
            "life_charge_buffer": int(getattr(player, "life_charge_buffer", 0)),
            
            # Armas (preservar todas las armas que posee y la equipada)
            "weapon_id": getattr(player, "weapon_id", None),
            "owned_weapons": set(getattr(player, "_owned_weapons", set())),
            
            # Mejoras y modificadores
            "upgrade_flags": set(getattr(player, "_upgrade_flags", set())),
            "cooldown_modifiers": dict(getattr(player, "_cooldown_modifiers", {})),
            "cooldown_scale_base": float(getattr(player, "cooldown_scale_base", 1.0)),
            
            # Items clave
            "key_items": set(getattr(player, "key_items", set())),
            
            # Stats base mejorados
            "base_speed": float(getattr(player, "base_speed", 120.0)),
            "base_sprint_multiplier": float(getattr(player, "base_sprint_multiplier", 1.35)),
            "base_dash_duration": float(getattr(player, "base_dash_duration", 0.18)),
            "base_dash_cooldown": float(getattr(player, "base_dash_cooldown", 0.75)),
            "sprint_control_bonus": float(getattr(player, "sprint_control_bonus", 0.0)),
            "phase_during_dash": bool(getattr(player, "phase_during_dash", False)),
            "dash_core_bonus_window": float(getattr(player, "dash_core_bonus_window", 0.0)),
            "dash_core_bonus_iframe": float(getattr(player, "dash_core_bonus_iframe", 0.0)),
            
            # Compras de la tienda (para preservar entre runs)
            "shop_purchases": set(getattr(player, "shop_purchases", set())),
        }
        return state

    def _capture_persistent_upgrades(self) -> None:
        """Guarda las mejoras acumuladas para aplicarlas al iniciar nuevas runs."""
        player = getattr(self, "player", None)
        if player is None:
            return

        current_state = {
            "upgrade_flags": set(getattr(player, "_upgrade_flags", set())),
            "cooldown_modifiers": dict(getattr(player, "_cooldown_modifiers", {})),
            "cooldown_scale_base": float(getattr(player, "cooldown_scale_base", 1.0)),
            "base_speed": float(getattr(player, "base_speed", 120.0)),
            "base_sprint_multiplier": float(getattr(player, "base_sprint_multiplier", 1.35)),
            "base_dash_duration": float(getattr(player, "base_dash_duration", 0.18)),
            "base_dash_cooldown": float(getattr(player, "base_dash_cooldown", 0.75)),
            "sprint_control_bonus": float(getattr(player, "sprint_control_bonus", 0.0)),
            "phase_during_dash": bool(getattr(player, "phase_during_dash", False)),
            "dash_core_bonus_window": float(getattr(player, "dash_core_bonus_window", 0.0)),
            "dash_core_bonus_iframe": float(getattr(player, "dash_core_bonus_iframe", 0.0)),
        }

        if not self._persistent_upgrades_state:
            self._persistent_upgrades_state = current_state
            return

        merged_state = dict(self._persistent_upgrades_state)
        merged_state["upgrade_flags"] = set(self._persistent_upgrades_state.get("upgrade_flags", set())) | current_state.get(
            "upgrade_flags", set()
        )
        merged_state["cooldown_modifiers"] = {
            **self._persistent_upgrades_state.get("cooldown_modifiers", {}),
            **current_state.get("cooldown_modifiers", {}),
        }

        def _max_merge(key: str) -> None:
            merged_state[key] = max(
                float(self._persistent_upgrades_state.get(key, current_state[key])), float(current_state[key])
            )

        def _min_merge(key: str) -> None:
            merged_state[key] = min(
                float(self._persistent_upgrades_state.get(key, current_state[key])), float(current_state[key])
            )

        for key in ("cooldown_scale_base", "base_speed", "base_sprint_multiplier", "base_dash_duration"):
            _max_merge(key)

        # Cooldown menor es mejor
        _min_merge("base_dash_cooldown")

        for key in ("sprint_control_bonus", "dash_core_bonus_window", "dash_core_bonus_iframe"):
            _max_merge(key)

        merged_state["phase_during_dash"] = bool(
            self._persistent_upgrades_state.get("phase_during_dash", False) or current_state.get("phase_during_dash", False)
        )

        self._persistent_upgrades_state = merged_state

    def _apply_persistent_upgrades(self, player) -> None:
        """Reaplica las mejoras acumuladas al jugador recién creado."""
        state = self._persistent_upgrades_state
        if not state or player is None:
            return

        player._upgrade_flags = set(state.get("upgrade_flags", set()))
        player._cooldown_modifiers = dict(state.get("cooldown_modifiers", {}))

        if "cooldown_scale_base" in state:
            player.cooldown_scale_base = float(state["cooldown_scale_base"])
        total = 1.0
        for mod_value in player._cooldown_modifiers.values():
            total *= mod_value
        player.cooldown_scale = player.cooldown_scale_base * total
        if hasattr(player, "refresh_weapon_modifiers"):
            try:
                player.refresh_weapon_modifiers()
            except Exception:
                pass

        for key in ("base_speed", "base_sprint_multiplier", "base_dash_duration", "base_dash_cooldown"):
            if key in state:
                setattr(player, key, float(state[key]))

        if "sprint_control_bonus" in state:
            player.sprint_control_bonus = float(state["sprint_control_bonus"])
        if "phase_during_dash" in state:
            player.phase_during_dash = bool(state["phase_during_dash"])
        if "dash_core_bonus_window" in state:
            player.dash_core_bonus_window = float(state["dash_core_bonus_window"])
        if "dash_core_bonus_iframe" in state:
            player.dash_core_bonus_iframe = float(state["dash_core_bonus_iframe"])

        player.speed = player.base_speed
        player.sprint_multiplier = player.base_sprint_multiplier
        player.dash_duration = player.base_dash_duration
        player.dash_cooldown = player.base_dash_cooldown

    def _restore_player_state(self, state: dict) -> None:
        """
        Restaura el estado completo del jugador desde un diccionario guardado.
        Se llama después de crear un nuevo jugador en start_new_run.
        """
        if not state or not hasattr(self, "player"):
            return

        player = self.player
        
        # Recursos
        if "gold" in state:
            player.gold = int(state["gold"])
        
        # Vida y supervivencia
        if "hp" in state:
            player.hp = int(state["hp"])
        if "max_hp" in state:
            player.max_hp = int(state["max_hp"])
        if "lives" in state:
            player.lives = int(state["lives"])
        if "max_lives" in state:
            player.max_lives = int(state["max_lives"])
        if "life_charge_buffer" in state:
            player.life_charge_buffer = int(state["life_charge_buffer"])
        
        # Restaurar armas
        if "owned_weapons" in state:
            player._owned_weapons = set(state["owned_weapons"])
        
        if "weapon_id" in state and state["weapon_id"]:
            # Restaurar el arma equipada
            weapon_id = state["weapon_id"]
            if hasattr(player, "_weapon_factory"):
                try:
                    player.weapon = player._weapon_factory.create(weapon_id)
                    player.weapon_id = weapon_id
                except Exception as e:
                    print(f"[WARN] No se pudo restaurar arma {weapon_id}: {e}")
        
        # Mejoras y modificadores
        if "upgrade_flags" in state:
            player._upgrade_flags = set(state["upgrade_flags"])
        if "cooldown_modifiers" in state:
            player._cooldown_modifiers = dict(state["cooldown_modifiers"])
        if "cooldown_scale_base" in state:
            player.cooldown_scale_base = float(state["cooldown_scale_base"])
            # Recalcular cooldown_scale
            if hasattr(player, "_cooldown_modifiers"):
                total = 1.0
                for mod_value in player._cooldown_modifiers.values():
                    total *= mod_value
                player.cooldown_scale = player.cooldown_scale_base * total
        
        # Items clave
        if "key_items" in state:
            player.key_items = set(state["key_items"])
        
        # Stats base mejorados
        if "base_speed" in state:
            player.base_speed = float(state["base_speed"])
            player.speed = player.base_speed
        if "base_sprint_multiplier" in state:
            player.base_sprint_multiplier = float(state["base_sprint_multiplier"])
            player.sprint_multiplier = player.base_sprint_multiplier
        if "base_dash_duration" in state:
            player.base_dash_duration = float(state["base_dash_duration"])
            player.dash_duration = player.base_dash_duration
        if "base_dash_cooldown" in state:
            player.base_dash_cooldown = float(state["base_dash_cooldown"])
            player.dash_cooldown = player.base_dash_cooldown
        if "sprint_control_bonus" in state:
            player.sprint_control_bonus = float(state["sprint_control_bonus"])
        if "phase_during_dash" in state:
            player.phase_during_dash = bool(state["phase_during_dash"])
        if "dash_core_bonus_window" in state:
            player.dash_core_bonus_window = float(state["dash_core_bonus_window"])
        if "dash_core_bonus_iframe" in state:
            player.dash_core_bonus_iframe = float(state["dash_core_bonus_iframe"])
        
        # Compras de la tienda
        if "shop_purchases" in state:
            player.shop_purchases = set(state["shop_purchases"])

    def _start_new_run_after_boss(self) -> None:
        """
        Inicia una nueva run después de derrotar a un boss.
        Preserva el estado completo del jugador y genera una nueva seed.
        """
        # Incrementar contador de runs
        self.completed_runs += 1
        
        # Preservar estado del jugador
        self._preserved_player_state = self._preserve_player_state()
        
        # Mostrar notificación
        notification_text = f"RUN {self.completed_runs} COMPLETADA - NUEVA SEED"
        if hasattr(self, "loot_notifications"):
            self.loot_notifications.push(notification_text, icon=None)
        
        # Generar nueva seed preservando el estado
        self.start_new_run(seed=None)

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
            self._elapsed_time += dt
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
            elif e.type == pygame.USEREVENT + 1:  # Música terminó
                self._play_next_random_music()
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
                elif e.key == pygame.K_b and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    self._warp_to_boss_room()
                elif e.key == pygame.K_f:
                    if self.hovered_weapon_pickup:
                        self._swap_weapon(self.hovered_weapon_pickup)
                elif e.key == pygame.K_e:
                    # Interacción con portal para siguiente run
                    room = getattr(self, "dungeon", None)
                    if room:
                        current_room = getattr(room, "current_room", None)
                        if current_room and hasattr(current_room, "check_portal_interaction"):
                            if current_room.check_portal_interaction(self.player):
                                if current_room.activate_portal():
                                    # Iniciar nueva run
                                    self._start_new_run_after_boss()
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
        cinamatic = Cinamatic(self.screen, self.cfg)
        if not cinamatic.run():
            self.running = False
            return False
        self.selected_skin_path = menu_result.skin_path or self.cfg.PLAYER_SPRITES_PATH
        self.start_new_run(seed=menu_result.seed)
        self._skip_frame = True
        return True

    def _warp_to_boss_room(self) -> bool:
        dungeon = getattr(self, "dungeon", None)
        player = getattr(self, "player", None)
        if dungeon is None or player is None:
            return False

        boss_pos = getattr(dungeon, "boss_pos", None)
        if boss_pos is None or boss_pos not in getattr(dungeon, "rooms", {}):
            print("[DEBUG] No hay sala de boss disponible para teletransporte.")
            return False

        current_room = dungeon.current_room
        if hasattr(current_room, "on_exit"):
            current_room.on_exit()

        dungeon.i, dungeon.j = boss_pos
        dungeon.explored.add(boss_pos)
        target_room = dungeon.current_room

        if hasattr(target_room, "locked"):
            target_room.locked = False

        cx, cy = target_room.center_px()
        player.x = cx - player.w / 2
        player.y = cy - player.h / 2
        player.xprec = player.x
        player.yprec = player.y

        self.projectiles.clear()
        self.enemy_projectiles.clear()
        self.door_cooldown = 0.25

        if hasattr(target_room, "on_enter"):
            target_room.on_enter(player, self.cfg, ShopkeeperCls=Shopkeeper)

        print("[DEBUG] Teletransportado a la sala del boss para pruebas.")
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
        
        # Sincronizar volumen de música con el pause menu
        self.current_music_volume = pause_menu.volume
        
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
        self.vfx.update(dt)
        room = self.dungeon.current_room
        if hasattr(room, "update"):
            room.update(dt)
        self._update_player(dt, room)
        self._spawn_room_enemies(room)
        self._update_enemies(dt, room)
        self._update_projectiles(dt, room)
        player_died = self._handle_collisions(room)
        if player_died:
            return
        self._update_pickups(dt, room)
        self._handle_room_transition(room)
        self._update_shop(events)
        self.loot_notifications.update(dt, self.screen)
        self._update_screen_effects(dt)
        
        # Actualizar portal si existe
        if hasattr(room, "update_portal"):
            room.update_portal(dt)

    def _update_screen_effects(self, dt: float) -> None:
        if self.camera_shake > 0.0:
            self.camera_shake *= 0.8
            if self.camera_shake < 0.1:
                self.camera_shake = 0.0

        if self._camera_recoil.length_squared() > 0.0:
            self._camera_recoil *= 0.85
            if self._camera_recoil.length_squared() < 0.01:
                self._camera_recoil.update(0.0, 0.0)

        if self._fade_direction != 0:
            self._fade_alpha += self._fade_speed * self._fade_direction * dt
            if self._fade_direction > 0 and self._fade_alpha >= 255.0:
                self._fade_alpha = 255.0
                if self._fade_bounce:
                    self._fade_direction = -1
                    self._fade_bounce = False
                else:
                    self._fade_direction = 0
            elif self._fade_direction < 0 and self._fade_alpha <= 0.0:
                self._fade_alpha = 0.0
                self._fade_direction = 0

    def _start_camera_shake(self, strength: float = 4.0) -> None:
        self.camera_shake = max(self.camera_shake, float(strength))

    def _apply_camera_recoil(self, direction: tuple[float, float], strength: float = 3.0) -> None:
        dir_vec = pygame.Vector2(direction)
        if dir_vec.length_squared() > 0.0:
            dir_vec = dir_vec.normalize()
        else:
            dir_vec = pygame.Vector2(1, 0)

        recoil = dir_vec * -float(strength)
        self._camera_recoil += recoil
        if self._camera_recoil.length() > strength * 3:
            self._camera_recoil.scale_to_length(strength * 3)

    def _start_room_fade(self) -> None:
        duration = random.uniform(0.15, 0.25)
        self._fade_speed = 255.0 / max(0.01, duration)
        self._fade_direction = -1
        self._fade_bounce = False
        self._fade_alpha = 255.0

    def _start_fade_in(self) -> None:
        duration = random.uniform(0.15, 0.25)
        self._fade_speed = 255.0 / max(0.01, duration)
        self._fade_direction = -1
        self._fade_bounce = False
        self._fade_alpha = 255.0

    def _update_player(self, dt: float, room) -> None:
        self.player.update(dt, room)
        mx, my = pygame.mouse.get_pos()
        mx //= self.cfg.SCREEN_SCALE
        my //= self.cfg.SCREEN_SCALE
        self.player.try_shoot((mx, my), self.projectiles)

    def _bind_player_events(self) -> None:
        player = getattr(self, "player", None)
        if player is None:
            return
        if hasattr(player, "on_shoot"):
            player.on_shoot = self._handle_player_shoot_vfx

    def _handle_player_shoot_vfx(
        self,
        position: tuple[float, float],
        direction: tuple[float, float],
    ) -> None:
        self.vfx.spawn_muzzle_flash(position, direction)
        self._apply_camera_recoil(direction)

    def _handle_projectile_impact(
        self,
        projectile,
        position: tuple[float, float],
        direction: tuple[float, float],
    ) -> None:
        self.vfx.spawn_bullet_impact(position, direction)

    def _spawn_room_enemies(self, room) -> None:
        if getattr(room, "no_spawn", False):
            return
        if getattr(room, "type", "") == "boss":
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
        initial_enemy_count = len(getattr(room, "enemies", ()))
        was_cleared = getattr(room, "cleared", False)
        for projectile in self.projectiles:
            if not projectile.alive:
                continue
            r_proj = projectile.rect()
            for enemy in room.enemies:
                if r_proj.colliderect(enemy.rect()):
                    damage = getattr(projectile, "damage", 1)
                    if hasattr(enemy, "take_damage"):
                        enemy.take_damage(damage, (projectile.dx, projectile.dy))
                    else:
                        enemy.hp -= damage
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
            if hasattr(enemy, "trigger_attack_animation"):
                ex = enemy.x + enemy.w/2
                px = self.player.x + self.player.w/2
                enemy.trigger_attack_animation(px - ex)
            contact_damage = getattr(enemy, "contact_damage", 0)
            if contact_damage <= 0:
                continue
            if player_invulnerable:
                continue
            took_hit = False
            if hasattr(self.player, "take_damage"):
                took_hit = bool(self.player.take_damage(contact_damage))
            if took_hit:
                self.vfx.trigger_damage_flash()
                self._start_camera_shake()
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
            damage = getattr(projectile, "damage", 1)
            if hasattr(self.player, "take_damage"):
                took_hit = bool(self.player.take_damage(damage))
            if took_hit:
                projectile.alive = False
                self.vfx.trigger_damage_flash()
                self._start_camera_shake()
                player_invulnerable = getattr(self.player, "is_invulnerable", lambda: False)()
            else:
                projectile.alive = False

        survivors = []
        for enemy in room.enemies:
            hp = getattr(enemy, "hp", 1)
            # Permitir que los enemigos (y especialmente los bosses) reproduzcan
            # su animación de muerte completa antes de ser eliminados.
            ready_to_remove = hp <= 0

            ready_fn = getattr(enemy, "is_ready_to_remove", None)
            if callable(ready_fn):
                ready_to_remove = bool(ready_fn())

            if getattr(enemy, "is_boss", False) and hp <= 0:
                handler = getattr(room, "on_boss_defeated", None)
                already_notified = getattr(enemy, "_boss_defeat_notified", False)
                if callable(handler) and not already_notified:
                    handler(enemy)
                    enemy._boss_defeat_notified = True

            if not ready_to_remove:
                survivors.append(enemy)
                continue

            self._drop_enemy_microchips(enemy, room)
            self._maybe_spawn_enemy_loot(enemy, room)
        defeated_enemies = max(0, initial_enemy_count - len(survivors))
        if defeated_enemies:
            # Reproducir sonido de eliminación de enemigo
            if self.enemy_elimination_sound:
                self.enemy_elimination_sound.play()
                
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
        if getattr(room, "cleared", False) and not was_cleared:
            self._handle_room_cleared(room)
        if getattr(self.player, "hp", 1) <= 0:
            self._handle_player_death(room)
            return True
        return False

    def _handle_room_cleared(self, room) -> None:
        # Reproducir sonido de puerta abierta cuando se eliminan todos los enemigos
        if hasattr(room, 'play_door_open_sound'):
            room.play_door_open_sound()
        
        if getattr(room, "is_corrupted", False):
            self._handle_corrupted_room_cleared(room)

    def _handle_corrupted_room_cleared(self, room) -> None:
        center = room.center_px() if hasattr(room, "center_px") else (self.cfg.SCREEN_W // 2, self.cfg.SCREEN_H // 2)
        drop_center = center
        if hasattr(room, "find_clear_drop_center"):
            try:
                drop_center = room.find_clear_drop_center()
            except Exception:
                drop_center = center

        if hasattr(self.vfx, "spawn_corruption_burst"):
            self.vfx.spawn_corruption_burst(drop_center)

        mode = str(getattr(room, "corrupted_loot_mode", "upgrade")).lower()
        if mode == "chips":
            total_value = int(getattr(room, "_microchips_dropped_total", 0))
            bonus_multiplier = max(0.0, float(getattr(room, "corrupted_chip_bonus", 0.5)))
            bonus_value = int(max(1, total_value * bonus_multiplier)) or 10
            self._spawn_microchip_bonus(drop_center, bonus_value, room)
            self._notify_microchips(bonus_value)
            return

        reward = self._pick_corrupted_upgrade_reward()
        if reward:
            self._spawn_reward_pickup_at(drop_center, reward, room)
            self._notify_reward(reward)
            return

        total_value = int(getattr(room, "_microchips_dropped_total", 0))
        bonus_value = int(total_value * max(0.0, float(getattr(room, "corrupted_chip_bonus", 0.5)))) or 10
        self._spawn_microchip_bonus(drop_center, bonus_value, room)
        self._notify_microchips(bonus_value)

    def _pick_corrupted_upgrade_reward(self) -> dict | None:
        loot_table = getattr(self.dungeon, "_treasure_loot_table", [])
        upgrades = [entry for entry in loot_table if str(entry.get("type", "")).lower() == "upgrade"]
        if not upgrades:
            return None
        weights = [float(entry.get("weight", 1.0)) for entry in upgrades]
        return random.choices(upgrades, weights=weights, k=1)[0]

    def _drop_enemy_microchips(self, enemy, room) -> None:
        gold_chance = float(self._enemy_drop_rates.get("enemy_gold_chance", 1.0))
        if random.random() > max(0.0, min(1.0, gold_chance)):
            return
        raw_value = int(getattr(enemy, "gold_reward", 0))
        total_value = int(math.ceil(raw_value * self.MICROCHIP_VALUE_SCALE)) if raw_value > 0 else 0
        if raw_value > 0 and total_value <= 0:
            total_value = 1
        if total_value <= 0:
            return
        room._microchips_dropped_total = getattr(room, "_microchips_dropped_total", 0) + total_value
        if not hasattr(room, "pickups"):
            room.pickups = []

        min_count, max_count = self._chip_count_for_reward(total_value)
        max_count = max(1, min(total_value, max_count))
        min_count = max(1, min(min_count, max_count))
        count = random.randint(min_count, max_count)
        count = max(1, min(count, total_value))

        base_value, remainder = divmod(total_value, count)
        values = [base_value] * count
        if remainder:
            for idx in random.sample(range(count), remainder):
                values[idx] += 1

        sprite_w = self._chip_pickup_sprite.get_width()
        sprite_h = self._chip_pickup_sprite.get_height()
        center_x = enemy.x + enemy.w / 2.0
        center_y = enemy.y + enemy.h / 2.0

        for value in values:
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(70.0, 130.0)
            jitter_x = math.cos(angle) * 4.0
            jitter_y = math.sin(angle) * 4.0
            pickup = MicrochipPickup(
                center_x - sprite_w / 2.0 + jitter_x,
                center_y - sprite_h / 2.0 + jitter_y,
                value,
                self._chip_pickup_sprite,
                angle=angle,
                speed=speed,
            )
            room.pickups.append(pickup)

    def _spawn_microchip_bonus(self, center: tuple[float, float], total_value: int, room) -> None:
        if total_value <= 0:
            return
        sprite_w = self._chip_pickup_sprite.get_width()
        sprite_h = self._chip_pickup_sprite.get_height()
        if not hasattr(room, "pickups"):
            room.pickups = []

        min_count, max_count = self._chip_count_for_reward(total_value)
        max_count = max(1, min(total_value, max_count))
        min_count = max(1, min(min_count, max_count))
        count = random.randint(min_count, max_count)
        base_value, remainder = divmod(total_value, count)
        values = [base_value] * count
        for idx in random.sample(range(count), remainder):
            values[idx] += 1

        cx, cy = center
        for value in values:
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(55.0, 110.0)
            jitter_x = math.cos(angle) * 6.0
            jitter_y = math.sin(angle) * 6.0
            pickup = MicrochipPickup(
                cx - sprite_w / 2.0 + jitter_x,
                cy - sprite_h / 2.0 + jitter_y,
                value,
                self._chip_pickup_sprite,
                angle=angle,
                speed=speed,
            )
            room.pickups.append(pickup)

    def _chip_count_for_reward(self, total_value: int) -> tuple[int, int]:
        if total_value <= 5:
            return (1, 2)
        if total_value <= 9:
            return (2, 3)
        return (3, 4)

    def _maybe_spawn_enemy_loot(self, enemy, room) -> None:
        reward = self._pick_enemy_reward(room)
        if not reward:
            return
        self._spawn_loot_pickup(enemy, room, reward)

    def _spawn_loot_pickup(self, enemy, room, reward: dict, sprite: pygame.Surface | None = None) -> None:
        sprite = sprite or self._sprite_for_reward(reward)
        if sprite is None:
            apply_reward_entry(self.player, reward)
            return
        if not hasattr(room, "pickups"):
            room.pickups = []

        sprite_w = sprite.get_width()
        sprite_h = sprite.get_height()
        ex = getattr(enemy, "x", None)
        ey = getattr(enemy, "y", None)
        ew = getattr(enemy, "w", sprite_w)
        eh = getattr(enemy, "h", sprite_h)
        if ex is None or ey is None:
            rect = getattr(enemy, "rect", None)
            if callable(rect):
                er = rect()
                ex = er.x
                ey = er.y
                ew = er.width
                eh = er.height
            else:
                ex = 0
                ey = 0
        center_x = ex + ew / 2.0
        center_y = ey + eh / 2.0

        angle = random.uniform(0.0, math.tau)
        speed = random.uniform(65.0, 115.0)
        jitter_x = math.cos(angle) * 5.0
        jitter_y = math.sin(angle) * 5.0
        pickup = LootPickup(
            center_x - sprite_w / 2.0 + jitter_x,
            center_y - sprite_h / 2.0 + jitter_y,
            sprite,
            reward,
            angle=angle,
            speed=speed,
        )
        room.pickups.append(pickup)

    def _spawn_reward_pickup_at(self, center: tuple[float, float], reward: dict, room) -> None:
        sprite = self._sprite_for_reward(reward)
        if sprite is None:
            apply_reward_entry(self.player, reward)
            return
        if not hasattr(room, "pickups"):
            room.pickups = []

        sprite_w = sprite.get_width()
        sprite_h = sprite.get_height()
        cx, cy = center
        angle = random.uniform(0.0, math.tau)
        speed = random.uniform(45.0, 85.0)
        pickup = LootPickup(
            cx - sprite_w / 2.0,
            cy - sprite_h / 2.0,
            sprite,
            reward,
            angle=angle,
            speed=speed,
        )
        room.pickups.append(pickup)

    def _get_scaled_pickup_icon(self, weapon_id: str) -> pygame.Surface | None:
        if weapon_id in self._pickup_icon_cache:
            return self._pickup_icon_cache[weapon_id]
        
        original = self._weapon_icons.get(weapon_id)
        if not original:
            return None
            
        # Escalar para que encaje en aprox 24x24 manteniendo aspecto
        # El sprite original suele ser grande (ej 64x32 o similar)
        max_dim = 24
        w, h = original.get_size()
        scale = min(max_dim / w, max_dim / h)
        new_size = (int(w * scale), int(h * scale))
        
        scaled = pygame.transform.smoothscale(original, new_size)
        self._pickup_icon_cache[weapon_id] = scaled
        return scaled

    def _sprite_for_reward(self, reward: dict | None) -> pygame.Surface | None:
        if not isinstance(reward, dict):
            return None
        rtype = str(reward.get("type", "")).lower()
        if rtype == "heal" or self._is_heal_reward(reward):
            return self._heal_pickup_sprite
        if rtype == "weapon":
            wid = reward.get("id")
            if wid:
                icon = self._get_scaled_pickup_icon(wid)
                if icon:
                    return icon
            return self._weapon_pickup_sprite
        if rtype == "upgrade":
            return self._upgrade_pickup_sprite
        if rtype == "bundle":
            return self._bundle_pickup_sprite
        return self._consumable_pickup_sprite

    def _is_heal_reward(self, reward: dict | None) -> bool:
        if not isinstance(reward, dict):
            return False
        rtype = str(reward.get("type", "")).lower()
        if rtype == "heal":
            return True
        if rtype != "consumable":
            return False
        rid = str(reward.get("id", "")).lower()
        return rid.startswith("heal") or "life" in rid

    def _pick_enemy_reward(self, room) -> dict | None:
        tiers = self._enemy_loot_table.get("tiers", {})
        tier_key = str(self._enemy_loot_tier(room))
        tier_data = tiers.get(tier_key)
        if not tier_data:
            return None
        category = self._roll_enemy_loot_category()
        entries = self._entries_for_category(tier_data, category)
        if not entries:
            return None
        weighted = [entry for entry in entries if float(entry.get("weight", 1.0)) > 0.0]
        if not weighted:
            return None
        weights = [float(entry.get("weight", 1.0)) for entry in weighted]
        return random.choices(weighted, weights=weights, k=1)[0]

    def _enemy_loot_tier(self, room) -> int:
        depth = 0
        if hasattr(self.dungeon, "room_depth"):
            pos = None
            if hasattr(self.dungeon, "rooms"):
                for coords, candidate in getattr(self.dungeon, "rooms", {}).items():
                    if candidate is room:
                        pos = coords
                        break
            if pos is None:
                pos = (self.dungeon.i, self.dungeon.j)
            depth = int(self.dungeon.room_depth(pos))
        if depth >= 8:
            return 3
        if depth >= 4:
            return 2
        return 1

    def _roll_enemy_loot_category(self) -> str | None:
        rates = self._enemy_drop_rates
        weapon_rate = max(0.0, float(rates.get("enemy_weapon_rare_chance", 0.0)))
        bundle_rate = max(0.0, float(rates.get("enemy_bundle_chance", 0.0)))
        upgrade_rate = max(0.0, float(rates.get("enemy_upgrade_chance", 0.0)))
        heal_big_rate = max(0.0, float(rates.get("enemy_heal_big_chance", rates.get("enemy_heal_chance", 0.0))))
        heal_small_rate = max(0.0, float(rates.get("enemy_heal_small_chance", rates.get("enemy_consumable_chance", 0.0))))
        roll = random.random()
        if roll < weapon_rate:
            return "weapon"
        if roll < weapon_rate + bundle_rate:
            return "bundle"
        if roll < weapon_rate + bundle_rate + upgrade_rate:
            return "upgrade"
        if roll < weapon_rate + bundle_rate + upgrade_rate + heal_big_rate:
            return "heal_big"
        if roll < weapon_rate + bundle_rate + upgrade_rate + heal_big_rate + heal_small_rate:
            return "heal_small"
        return None

    def _entries_for_category(self, tier_data: dict, category: str | None) -> list[dict]:
        if category == "weapon":
            return list(tier_data.get("weapons", ()))
        if category == "bundle":
            return list(tier_data.get("bundles", ()))
        if category == "upgrade":
            return list(tier_data.get("upgrades", ()))
        consumables = tier_data.get("consumables", ())
        if category == "heal_big":
            return [entry for entry in consumables if str(entry.get("id", "")).startswith("heal_battery")]
        if category == "heal_small":
            return [
                entry
                for entry in consumables
                if str(entry.get("id", "")).startswith("heal")
                and not str(entry.get("id", "")).startswith("heal_battery")
            ]
        return []

    def _update_pickups(self, dt: float, room) -> None:
        pickups = getattr(room, "pickups", None)
        if pickups is None or not pickups:
            if pickups is None:
                room.pickups = []
            return

        player_rect = self.player.rect()
        collected_total = 0
        survivors: list[object] = []
        reward_pickups: list[LootPickup] = []
        self.hovered_weapon_pickup = None
        for pickup in pickups:
            pickup.update(dt, room)
            if pickup.collected:
                continue
            
            if player_rect.colliderect(pickup.rect()):
                # Verificar si es un arma para lógica de intercambio
                is_weapon = False
                if isinstance(pickup, LootPickup):
                    rtype = pickup.reward_data.get("type", "")
                    if rtype == "weapon":
                        is_weapon = True
                
                if is_weapon:
                    self.hovered_weapon_pickup = pickup
                    survivors.append(pickup)
                else:
                    pickup.collect()
                    if isinstance(pickup, MicrochipPickup):
                        collected_total += getattr(pickup, "value", 0)
                    elif hasattr(pickup, "apply"):
                        reward_pickups.append(pickup)
            else:
                survivors.append(pickup)
        room.pickups = survivors
        if collected_total:
            self._add_player_gold(collected_total)
            self._notify_microchips(collected_total)
            # Reproducir sonido de microchip
            if self.microchip_pickup_sound:
                self.microchip_pickup_sound.play()
        for reward_pickup in reward_pickups:
            try:
                applied = reward_pickup.apply(self.player)
            except Exception:
                continue
            if applied:
                self._notify_reward(
                    reward_pickup.reward_data, getattr(reward_pickup, "sprite", None)
                )
                # Reproducir sonido de objeto
                if self.object_pickup_sound:
                    self.object_pickup_sound.play()

    def _swap_weapon(self, new_pickup: LootPickup) -> None:
        if not new_pickup or new_pickup.collected:
            return

        # 1. Obtener arma actual
        old_weapon_id = getattr(self.player, "weapon_id", None)
        
        # 2. Aplicar nueva arma
        # Nota: unlock_weapon devuelve False si ya la tenías, pero igual la equipa si auto_equip=True.
        # Por tanto, ignoramos el valor de retorno 'applied' para la lógica de soltar la anterior,
        # siempre y cuando sea un arma válida.
        new_id = new_pickup.reward_data.get("id")
        if not new_id:
             return

        # Forzamos el desbloqueo/equipado
        self.player.unlock_weapon(new_id, auto_equip=True)
        
        new_pickup.collect()
        
        # 3. Soltar arma vieja (si existe y no es la default/inicial si aplica)
        # Asumimos que siempre se suelta la anterior si es válida.
        if old_weapon_id:
            # Crear pickup para el arma vieja
            old_reward = {"type": "weapon", "id": old_weapon_id}
            sprite = self._sprite_for_reward(old_reward)
            
            if sprite:
                # Posición del jugador con un pequeño offset aleatorio
                cx, cy = self.player.rect().center
                angle = random.uniform(0.0, math.tau)
                speed = random.uniform(30.0, 60.0)
                
                old_pickup = LootPickup(
                    cx - sprite.get_width() / 2,
                    cy - sprite.get_height() / 2,
                    sprite,
                    old_reward,
                    angle=angle,
                    speed=speed
                )
                
                # Añadir a la sala actual
                room = self.dungeon.current_room
                if not hasattr(room, "pickups"):
                    room.pickups = []
                room.pickups.append(old_pickup)

        # 4. Feedback
        self._notify_reward(new_pickup.reward_data, getattr(new_pickup, "sprite", None))
        if self.gun_pickup_sound:
            self.gun_pickup_sound.play()
        self.hovered_weapon_pickup = None

    def _handle_shop_weapon_purchase(self, reward_data: dict) -> None:
        """Callback para cuando se compra un arma en la tienda."""
        if not hasattr(self, "player"):
            return
            
        # 1. Obtener arma actual
        old_weapon_id = getattr(self.player, "weapon_id", None)
        
        # 2. Equipar nueva arma
        new_id = reward_data.get("id")
        if not new_id:
            return
            
        self.player.unlock_weapon(new_id, auto_equip=True)
        
        # 3. Soltar arma vieja (si existe)
        if old_weapon_id:
            old_reward = {"type": "weapon", "id": old_weapon_id}
            sprite = self._sprite_for_reward(old_reward)
            
            if sprite:
                # Posición del jugador con un pequeño offset aleatorio
                cx, cy = self.player.rect().center
                angle = random.uniform(0.0, math.tau)
                speed = random.uniform(30.0, 60.0)
                
                old_pickup = LootPickup(
                    cx - sprite.get_width() / 2,
                    cy - sprite.get_height() / 2,
                    sprite,
                    old_reward,
                    angle=angle,
                    speed=speed
                )
                
                # Añadir a la sala actual
                room = self.dungeon.current_room
                if not hasattr(room, "pickups"):
                    room.pickups = []
                room.pickups.append(old_pickup)
        
        # Feedback
        self._notify_reward(reward_data, self._sprite_for_reward(reward_data))
        if self.gun_pickup_sound:
            self.gun_pickup_sound.play()

    def _add_player_gold(self, amount: int) -> None:
        amount = int(amount)
        if amount <= 0:
            return
        current_gold = getattr(self.player, "gold", 0)
        setattr(self.player, "gold", current_gold + amount)

    def _notify_microchips(self, amount: int) -> None:
        if amount <= 0:
            return
        self.loot_notifications.push(f"+{amount} microchips", self._microchip_icon_source)

    def _push_notification(self, message: str, icon: pygame.Surface | None = None) -> None:
        if not message:
            return
        self.loot_notifications.push(message, icon)

    def _notify_reward(self, reward: dict | None, icon: pygame.Surface | None = None) -> None:
        if not isinstance(reward, dict):
            return
        rtype = str(reward.get("type", "")).lower()
        if rtype == "bundle":
            contents = reward.get("contents", ())
            for entry in contents:
                self._notify_reward(entry)
            return
        message = self._format_reward_message(reward)
        if message:
            icon = icon or self._sprite_for_reward(reward)
            self.loot_notifications.push(message, icon)

    def _friendly_reward_name(self, category: str, identifier: str) -> str:
        category = category.lower()
        mapping = {
            "upgrade": self.UPGRADE_NAMES,
            "weapon": self.WEAPON_NAMES,
            "consumable": self.CONSUMABLE_NAMES,
        }
        return mapping.get(category, {}).get(identifier, identifier)

    def _format_reward_message(self, reward: dict) -> str | None:
        rtype = str(reward.get("type", "")).lower()
        if rtype == "gold":
            amount = int(reward.get("amount", 0))
            if amount <= 0:
                return None
            return f"+{amount} microchips"
        if rtype == "heal":
            amount = int(reward.get("amount", 0))
            if amount <= 0:
                return None
            return f"+{amount} vida"
        if rtype == "weapon":
            weapon_id = reward.get("id", "arma")
            weapon_name = self._friendly_reward_name(rtype, weapon_id)
            return f"Nueva arma: {weapon_name}"
        if rtype == "upgrade":
            upgrade_id = reward.get("id", "mejora")
            upgrade_name = self._friendly_reward_name(rtype, upgrade_id)
            return f"Mejora obtenida: {upgrade_name}"
        if rtype == "consumable":
            consumable_id = reward.get("id", "objeto")
            consumable_name = self._friendly_reward_name(rtype, consumable_id)
            return f"Objeto: {consumable_name}"
        return None

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

        target_room = None
        peek = getattr(self.dungeon, "room_in_direction", None)
        if callable(peek):
            target_room = peek(direction)
        if target_room and getattr(target_room, "type", "") == "boss":
            has_key = False
            checker = getattr(self.player, "has_key_item", None)
            if callable(checker):
                has_key = checker("motherboard_boss")
            if not has_key:
                if hasattr(self, "loot_notifications"):
                    self.loot_notifications.push("La puerta está sellada. Falta la MotherBoard Boss.")
                self.door_cooldown = 0.45
                return

        # Verificar si la room de destino ya fue explorada ANTES de moverse
        # (dungeon.move() añade automáticamente a explored)
        di, dj = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}[direction]
        target_pos = (self.dungeon.i + di, self.dungeon.j + dj)
        was_explored = target_pos in self.dungeon.explored

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
        
        self.door_cooldown = 0.25
        self.projectiles.clear()
        self.enemy_projectiles.clear()

        new_room = self.dungeon.current_room
        
        # Reproducir sonido de puerta cerrada para rooms no exploradas
        if not was_explored and hasattr(new_room, 'play_door_closed_sound'):
            new_room.play_door_closed_sound()
        
        self._spawn_room_enemies(new_room)
        self._update_room_lock(new_room)
        self._start_room_fade()

    def _update_room_lock(self, room) -> None:
        if not hasattr(room, "enemies") or not hasattr(room, "cleared"):
            return
        if getattr(room, "type", "") == "boss":
            room.locked = not getattr(room, "boss_defeated", False)
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
        self._draw_boss_floor_effects(room)

        if hasattr(room, "enemies"):
            for enemy in room.enemies:
                self._draw_corrupted_enemy_aura(self.world, enemy)
                enemy.draw(self.world)

        for pickup in getattr(room, "pickups", ()): 
            pickup.draw(self.world)

        self.player.draw(self.world)
        self.projectiles.draw(self.world)
        self.enemy_projectiles.draw(self.world)
        self.vfx.draw_world(self.world)
        self._draw_debug_door_triggers(room)

        if hasattr(room, "draw_overlay"):
            room.draw_overlay(self.world, self.ui_font, self.player, self.shop)
        self.shop.draw(self.world)

    def _draw_corrupted_enemy_aura(self, surface: pygame.Surface, enemy) -> None:
        if not getattr(enemy, "corrupted_visual", False):
            return
        if not hasattr(enemy, "rect"):
            return
        rect = enemy.rect()
        center = rect.center
        radius = 24
        aura_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        time_phase = getattr(self, "_elapsed_time", 0.0)
        alpha = int(130 + 30 * math.sin(time_phase * 8.0))
        color = (150, 60, 220, max(100, min(160, alpha)))
        pygame.draw.ellipse(aura_surf, color, pygame.Rect(0, 6, radius * 2, radius * 2 - 8))
        surface.blit(aura_surf, (center[0] - radius, center[1] - radius))

    def _draw_debug_door_triggers(self, room) -> None:
        if not self.debug_draw_doors:
            return

        for rect in room._door_trigger_rects().values():
            pygame.draw.rect(self.world, (0, 255, 0), rect, 1)

    def _draw_boss_floor_effects(self, room) -> None:
        boss = getattr(room, "boss_instance", None)
        if boss is None:
            for enemy in getattr(room, "enemies", []):
                if getattr(enemy, "is_boss", False):
                    boss = enemy
                    break
        if boss and hasattr(boss, "draw_floor_effects"):
            boss.draw_floor_effects(self.world)

    def _active_boss(self, room):
        if getattr(room, "type", "") != "boss":
            return None
        has_active_flag = getattr(room, "has_active_boss", None)
        if callable(has_active_flag) and not has_active_flag():
            return None

        if not getattr(room, "_boss_spawned", False) and hasattr(room, "_spawn_boss"):
            try:
                room._spawn_boss()
            except Exception:
                return None

        boss = getattr(room, "boss_instance", None)
        if boss is None:
            for enemy in getattr(room, "enemies", []):
                if getattr(enemy, "is_boss", False):
                    boss = enemy
                    break

        if boss is None:
            return None

        try:
            if float(getattr(boss, "hp", 0)) <= 0:
                return None
        except (TypeError, ValueError):
            return None
        return boss

    def _draw_weapon_tooltip(self, pickup: LootPickup) -> None:
        """Dibuja un tooltip con información del arma sobre el pickup."""
        weapon_id = pickup.reward_data.get("id")
        if not weapon_id or weapon_id not in self.weapon_factory:
            return

        spec = self.weapon_factory._registry[weapon_id]
        name = self.WEAPON_NAMES.get(weapon_id, weapon_id.replace("_", " ").title())
        
        # Stats
        damage = "N/A" # El daño depende del proyectil, no está directo en spec fácilmente sin instanciar
        # Pero podemos estimar o mostrar otras cosas.
        # Mostraremos: Cadencia (RPS), Cargador, Recarga
        rps = 1.0 / max(0.01, spec.cooldown)
        mag = spec.magazine_size
        reload_t = spec.reload_time
        
        # Configuración visual
        padding = 10
        line_height = 18
        bg_color = (20, 20, 30, 230)
        border_color = (100, 100, 150)
        text_color = (220, 220, 220)
        accent_color = (255, 200, 50)

        # Textos
        title_surf = self.loot_font.render(name, True, accent_color)
        stats_lines = [
            f"Cadencia: {rps:.1f}/s",
            f"Cargador: {mag}",
            f"Recarga: {reload_t}s"
        ]
        
        # Calcular tamaño
        width = max(title_surf.get_width(), 140) + padding * 2
        height = padding * 2 + title_surf.get_height() + 5 + len(stats_lines) * line_height + 25 # +25 para prompt
        
        # Posición (arriba del pickup)
        px = (pickup.x + pickup.width / 2) * self.cfg.SCREEN_SCALE
        py = pickup.y * self.cfg.SCREEN_SCALE
        
        rect = pygame.Rect(0, 0, width, height)
        rect.midbottom = (int(px), int(py - 15))
        
        # Dibujar fondo
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, bg_color, surf.get_rect(), border_radius=8)
        pygame.draw.rect(surf, border_color, surf.get_rect(), 2, border_radius=8)
        
        # Dibujar contenido
        y_off = padding
        surf.blit(title_surf, (padding, y_off))
        y_off += title_surf.get_height() + 5
        
        for line in stats_lines:
            txt = self.ui_font.render(line, True, text_color)
            surf.blit(txt, (padding, y_off))
            y_off += line_height
            
        # Prompt
        prompt_txt = self.prompt_font.render("[F] Equipar", True, (255, 255, 255))
        prompt_rect = prompt_txt.get_rect(centerx=width//2, top=y_off + 5)
        surf.blit(prompt_txt, prompt_rect)
        
        self.screen.blit(surf, rect)

    def _render_ui(self) -> None:
        room = self.dungeon.current_room
        scaled = pygame.transform.scale(
            self.world,
            (self.cfg.SCREEN_W * self.cfg.SCREEN_SCALE,
             self.cfg.SCREEN_H * self.cfg.SCREEN_SCALE)
        )
        self.screen.blit(scaled, (0, 0))

        # --- Prompt de intercambio de arma ---
        if self.hovered_weapon_pickup and not self.hovered_weapon_pickup.collected:
            self._draw_weapon_tooltip(self.hovered_weapon_pickup)

        inventory_rect = self.hud_panels.blit_inventory_panel(self.screen)
        weapon_rect = self._draw_weapon_hud(inventory_rect)

        gold_amount = getattr(self.player, "gold", 0)
        microchip_rect = self._draw_microchip_counter(inventory_rect, weapon_rect, gold_amount)

        seed_text = self.ui_font.render(f"Seed: {self.current_seed}", True, (230, 230, 230))

        text_x, text_y = self.hud_panels.inventory_content_anchor()
        # Usamos una posición fija para el texto, independiente del tamaño del arma
        fixed_weapon_width = 140  # Ancho estimado del slot de arma
        text_x = max(text_x, inventory_rect.left + int(self.weapon_icon_offset.x) + fixed_weapon_width + int(self.weapon_text_margin))
        
        # Restauramos la dependencia del microchip para que el texto (y las baterías) se desplacen correctamente
        if microchip_rect.width:
            text_x = max(text_x, microchip_rect.right + int(self.weapon_text_margin))
        line_gap = 6

        header_rect = pygame.Rect(0, 0, 0, 0)
        if weapon_rect.width and weapon_rect.height:
            header_rect = weapon_rect.copy()
        if microchip_rect.width and microchip_rect.height:
            header_rect = (
                header_rect.union(microchip_rect)
                if header_rect.width or header_rect.height
                else microchip_rect
            )
        if header_rect.height:
            text_y = max(text_y, header_rect.bottom + line_gap)


        # Usar posición fija para las baterías (independiente del arma)
        battery_origin = (
            inventory_rect.left + int(self.batteries_base_x),
            inventory_rect.top + int(self.batteries_base_y),
        )
        
        # Dibujar panel de vida (fondo)
        if self._life_panel_sprite is not None:
            # Usar offsets configurables para posicionar el panel
            panel_x = battery_origin[0] + int(self.life_panel_offset_x)
            panel_y = battery_origin[1] + int(self.life_panel_offset_y)
            self.screen.blit(self._life_panel_sprite, (panel_x, panel_y))
        
        batteries_rect = self._blit_life_batteries(self.screen, battery_origin)
        if batteries_rect.height:
            text_y = batteries_rect.bottom + line_gap

        seed_position = (20, 100)
        self.screen.blit(seed_text, seed_position)

        minimap_surface = self.minimap.render(self.dungeon)
        minimap_position = self.hud_panels.compute_minimap_position(self.screen, minimap_surface)
        self.hud_panels.blit_minimap_panel(self.screen, minimap_surface, minimap_position)

        self.hud_panels.blit_corner_panel(self.screen)
        self.hud_panels.blit_corner_inverse_panel(self.screen)

        self.loot_notifications.draw(self.screen)

        self.vfx.draw_screen(self.screen)

        # Recolectar bosses visibles/activos (ajusta según tu estructura)
        bosses = []
        # ejemplo si guardas enemigos en current room:
        try:
            room_enemies = getattr(self.dungeon.current_room, "enemies", []) or []
        except Exception:
            room_enemies = getattr(self, "enemies", [])
        for e in room_enemies:
            if isinstance(e, BossEnemy):
                bosses.append(e)

        # Dibujar barras HUD para cada boss, en orden (0..n) en la parte superior de la pantalla
        for i, boss in enumerate(bosses):
            # dibujamos con índice para que se apilen en la parte superior
            self._draw_boss_health_bar(self.screen, boss, index=i, top_padding=8)

        mx, my = pygame.mouse.get_pos()
        cursor_rect = self._cursor_surface.get_rect(center=(mx, my))
        self.screen.blit(self._cursor_surface, cursor_rect.topleft)

        self._apply_screen_overlays()

        pygame.display.flip()

    def _draw_boss_health_bar(self, surface: pygame.Surface, boss, index: int = 0, top_padding: int = 8) -> None:
        """
        Dibuja la barra del boss en la parte superior de la pantalla.
        Si hay varios bosses, se apilan hacia abajo usando 'index' y 'top_padding'.
        """
        max_hp = max(1, int(getattr(boss, "max_hp", 1)))
        try:
            hp_value = max(0, min(max_hp, int(getattr(boss, "hp", 0))))
        except (TypeError, ValueError):
            return
        if hp_value <= 0:
            return

        width, _ = surface.get_size()
        bar_width = max(260, width - 220)
        bar_height = 28
        spacing = 8  # espacio entre barras si hay varias
        x = (width - bar_width) // 2
        y = top_padding + index * (bar_height + spacing)  # posición en la parte superior según índice
        frame_radius = 10

        background = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
        background.fill((6, 8, 8, 180))
        surface.blit(background, (x, y))

        outline_color = pygame.Color(40, 255, 170)
        inner_margin = 4
        inner_rect = pygame.Rect(
            x + inner_margin,
            y + inner_margin,
            bar_width - inner_margin * 2,
            bar_height - inner_margin * 2,
        )

        ratio = hp_value / max_hp
        fill_width = max(0, int(inner_rect.width * ratio))
        fill_rect = pygame.Rect(inner_rect.left, inner_rect.top, fill_width, inner_rect.height)

        base_color = pygame.Color(20, 200, 120)
        glitch_color = pygame.Color(140, 255, 190)
        pygame.draw.rect(surface, base_color, fill_rect, border_radius=frame_radius)

        stripe_step = 16
        stripe_width = 7
        for offset in range(0, fill_width, stripe_step):
            height_variation = random.randint(-2, 4)
            stripe_height = max(6, inner_rect.height + height_variation)
            stripe_y = inner_rect.bottom - stripe_height
            stripe_rect = pygame.Rect(
                fill_rect.left + offset,
                stripe_y,
                min(stripe_width, fill_rect.width - offset),
                stripe_height,
            )
            pygame.draw.rect(surface, glitch_color, stripe_rect, border_radius=3)

        top_glow = pygame.Surface((fill_rect.width, 6), pygame.SRCALPHA)
        top_glow.fill((90, 255, 170, 130))
        surface.blit(top_glow, (fill_rect.left, inner_rect.top))

        pygame.draw.rect(surface, outline_color, pygame.Rect(x, y, bar_width, bar_height), 2, border_radius=frame_radius)
        pygame.draw.rect(surface, outline_color, inner_rect, 1, border_radius=frame_radius)

        boss_name = getattr(boss, "name", None) or boss.__class__.__name__
        boss_name = str(boss_name).replace("_", " ")
        label = f"{boss_name} — {hp_value}/{max_hp}"
        label_surface = self.ui_font.render(label, True, pygame.Color(210, 255, 230))
        label_rect = label_surface.get_rect(center=(x + bar_width // 2, y + bar_height // 2))
        surface.blit(label_surface, label_rect)
    def _apply_screen_overlays(self) -> None:
        offset_x = offset_y = 0
        if self.camera_shake > 0.0:
            offset_x += int(round(random.uniform(-self.camera_shake, self.camera_shake)))
            offset_y += int(round(random.uniform(-self.camera_shake, self.camera_shake)))

        if self._camera_recoil.length_squared() > 0.0:
            offset_x += int(round(self._camera_recoil.x))
            offset_y += int(round(self._camera_recoil.y))

        if offset_x or offset_y:
            frame = self.screen.copy()
            self.screen.fill(self.cfg.COLOR_BG)
            self.screen.blit(frame, (offset_x, offset_y))

        if self._should_draw_low_hp_overlay():
            pulse = math.sin(self._elapsed_time * 6.0)
            alpha = self._low_hp_base_alpha + self._low_hp_pulse * pulse
            alpha = max(20, min(35, int(alpha)))
            self._low_hp_surface.set_alpha(alpha)
            self.screen.blit(self._low_hp_surface, (0, 0))

        if self._fade_alpha > 0.0:
            self._fade_surface.set_alpha(int(self._fade_alpha))
            self.screen.blit(self._fade_surface, (0, 0))

    def _should_draw_low_hp_overlay(self) -> bool:
        player = getattr(self, "player", None)
        return player is not None and getattr(player, "hp", 0) == 1

    def set_microchip_icon_scale(self, scale: float) -> None:
        scale = max(0.1, float(scale))
        if math.isclose(scale, self.microchip_icon_scale, rel_tol=1e-4, abs_tol=1e-4):
            return
        self.microchip_icon_scale = scale
        self._coin_icon = self._scale_microchip_icon(scale)

    def set_microchip_icon_offset(
        self, offset: tuple[float, float] | pygame.Vector2
    ) -> None:
        if isinstance(offset, pygame.Vector2):
            self.microchip_icon_offset.update(offset)
        else:
            ox, oy = offset
            self.microchip_icon_offset.update(ox, oy)

    def set_microchip_value_offset(
        self, offset: tuple[float, float] | pygame.Vector2
    ) -> None:
        if isinstance(offset, pygame.Vector2):
            self.microchip_value_offset.update(offset)
        else:
            ox, oy = offset
            self.microchip_value_offset.update(ox, oy)

    def _draw_microchip_counter(
        self,
        inventory_rect: pygame.Rect,
        weapon_rect: pygame.Rect,
        amount: int,
    ) -> pygame.Rect:
        icon_surface = getattr(self, "_coin_icon", None)
        if icon_surface is None:
            return pygame.Rect(0, 0, 0, 0)

        # Desacoplamos la posición del microchip del tamaño del arma.
        # Usamos una posición fija relativa al inicio del slot del arma.
        anchor_x = inventory_rect.left + int(self.weapon_icon_offset.x) + 130  # +130 de margen fijo
        anchor_y = inventory_rect.top + int(self.weapon_icon_offset.y)

        icon_position = (
            int(anchor_x + self.microchip_icon_offset.x),
            int(anchor_y + self.microchip_icon_offset.y),
        )
        icon_rect = icon_surface.get_rect(topleft=icon_position)
        self.screen.blit(icon_surface, icon_rect.topleft)

        # Texto de cantidad (40px a la derecha, fuente grande VT323)
        value_surface = self.hud_font_large.render(str(int(amount)), True, self.microchip_value_color)
        value_rect = value_surface.get_rect()
        value_rect.midleft = (icon_rect.right + 40, icon_rect.centery)
        self.screen.blit(value_surface, value_rect)


        return icon_rect.union(value_rect)

    def _scale_microchip_icon(self, scale: float) -> pygame.Surface:
        source = getattr(self, "_microchip_icon_source", None)
        if source is None:
            source, _ = self._create_procedural_microchip()
            self._microchip_icon_source = source

        width = max(1, int(source.get_width() * scale))
        height = max(1, int(source.get_height() * scale))
        return pygame.transform.smoothscale(source, (width, height))
    
    def _load_pickup_sounds(self) -> None:
        """Carga los sonidos para recoger objetos."""
        # Sonido de microchips
        self.microchip_pickup_sound = None
        try:
            audio_path = Path("assets/audio/microchip_pickup_sfx.mp3")
            if not audio_path.exists():
                audio_path = Path(__file__).parent / "assets" / "audio" / "microchip_pickup_sfx.mp3"
            if audio_path.exists():
                self.microchip_pickup_sound = pygame.mixer.Sound(audio_path.as_posix())
                self.microchip_pickup_sound.set_volume(0.15)  # 15% del volumen
        except (pygame.error, FileNotFoundError):
            pass
        
        # Sonido de otros objetos
        self.object_pickup_sound = None
        try:
            audio_path = Path("assets/audio/object_pickup_sfx.mp3")
            if not audio_path.exists():
                audio_path = Path(__file__).parent / "assets" / "audio" / "object_pickup_sfx.mp3"
            if audio_path.exists():
                self.object_pickup_sound = pygame.mixer.Sound(audio_path.as_posix())
                self.object_pickup_sound.set_volume(0.15)  # 15% del volumen
        except (pygame.error, FileNotFoundError):
            pass
        
        # Sonido de recoger armas
        self.gun_pickup_sound = None
        try:
            audio_path = Path("assets/audio/gun_pickup_sfx.mp3")
            if not audio_path.exists():
                audio_path = Path(__file__).parent / "assets" / "audio" / "gun_pickup_sfx.mp3"
            if audio_path.exists():
                self.gun_pickup_sound = pygame.mixer.Sound(audio_path.as_posix())
                self.gun_pickup_sound.set_volume(0.2)  # 20% del volumen
        except (pygame.error, FileNotFoundError):
            pass

        # Sonido de eliminación de enemigos
        self.enemy_elimination_sound = None
        try:
            audio_path = Path("assets/audio/enemy_elimination_sfx.mp3")
            if not audio_path.exists():
                audio_path = Path(__file__).parent / "assets" / "audio" / "enemy_elimination_sfx.mp3"
            if audio_path.exists():
                self.enemy_elimination_sound = pygame.mixer.Sound(audio_path.as_posix())
                self.enemy_elimination_sound.set_volume(0.15)  # 15% del volumen
        except (pygame.error, FileNotFoundError):
            pass

    def _load_gameplay_music_pool(self) -> None:
        """Carga todos los archivos de música de gameplay en el pool."""
        audio_dir = Path(__file__).parent / "assets" / "audio"
        
        # Buscar todos los archivos que coincidan con el patrón musica_gameplay_*
        if audio_dir.exists():
            for music_file in audio_dir.glob("musica_gameplay_*.mp3"):
                self.gameplay_music_pool.append(music_file)
        
        # Shuffle del pool para orden aleatorio inicial
        if self.gameplay_music_pool:
            random.shuffle(self.gameplay_music_pool)
            print(f"[Music] Cargadas {len(self.gameplay_music_pool)} canciones de gameplay")
        else:
            print("[Music] No se encontraron canciones de gameplay")

    def _play_next_random_music(self) -> None:
        """Reproduce la siguiente canción del pool de manera aleatoria."""
        if not self.gameplay_music_pool:
            return
        
        # Seleccionar una canción aleatoria
        music_file = random.choice(self.gameplay_music_pool)
        
        try:
            pygame.mixer.music.load(str(music_file))
            pygame.mixer.music.set_volume(self.current_music_volume)
            pygame.mixer.music.play()
            print(f"[Music] Reproduciendo: {music_file.name}")
        except pygame.error as e:
            print(f"[Music] Error al reproducir {music_file.name}: {e}")

    def _start_gameplay_music(self) -> None:
        """Inicia la reproducción de música al comenzar el juego."""
        if self.gameplay_music_pool:
            self._play_next_random_music()

    def _update_music_volume(self, volume: float) -> None:
        """Actualiza el volumen de la música actual."""
        self.current_music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.current_music_volume)


    def _create_microchip_sprites(self) -> tuple[pygame.Surface, pygame.Surface]:
        procedural_icon, pickup_sprite = self._create_procedural_microchip()
        sprite_path = assets_dir("ui", self.MICROCHIP_SPRITE_NAME)
        sprite = self._load_surface(sprite_path)
        icon_source = sprite if sprite is not None else procedural_icon
        return icon_source, pickup_sprite

    def _create_heal_pickup_sprite(self) -> pygame.Surface:
        width, height = 12, 14
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        body_rect = pygame.Rect(1, 3, width - 2, height - 4)
        pygame.draw.rect(surface, pygame.Color(170, 48, 48), body_rect, border_radius=3)
        pygame.draw.rect(surface, pygame.Color(220, 96, 96), body_rect.inflate(-3, -4), border_radius=2)
        highlight = pygame.Rect(body_rect.left + 2, body_rect.top + 2, 3, body_rect.height - 4)
        pygame.draw.rect(surface, pygame.Color(255, 184, 184), highlight, border_radius=2)
        cross_h = pygame.Rect(0, 0, width - 8, 2)
        cross_h.center = (width // 2, height // 2 + 1)
        cross_v = pygame.Rect(0, 0, 2, height - 8)
        cross_v.center = (width // 2, height // 2 + 1)
        pygame.draw.rect(surface, pygame.Color(255, 240, 220), cross_h, border_radius=1)
        pygame.draw.rect(surface, pygame.Color(255, 240, 220), cross_v, border_radius=1)
        cap_rect = pygame.Rect(width // 2 - 3, 0, 6, 3)
        pygame.draw.rect(surface, pygame.Color(110, 24, 32), cap_rect, border_radius=2)
        rim = pygame.Rect(cap_rect.left, cap_rect.bottom - 1, cap_rect.width, 2)
        pygame.draw.rect(surface, pygame.Color(255, 214, 140), rim, border_radius=2)
        return surface

    def _create_consumable_pickup_sprite(self) -> pygame.Surface:
        width, height = 15, 15
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        box_rect = pygame.Rect(1, 2, width - 2, height - 4)
        pygame.draw.rect(surface, pygame.Color(60, 110, 185), box_rect, border_radius=3)
        stripe_rect = pygame.Rect(2, height // 2 - 2, width - 4, 4)
        pygame.draw.rect(surface, pygame.Color(240, 210, 120), stripe_rect, border_radius=2)
        latch_rect = pygame.Rect(width // 2 - 1, 3, 3, height - 6)
        pygame.draw.rect(surface, pygame.Color(255, 255, 255), latch_rect, border_radius=1)
        return surface

    def _create_upgrade_pickup_sprite(self) -> pygame.Surface:
        width, height = 16, 16
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        center = pygame.Vector2(width / 2, height / 2)
        radius = 6
        points = []
        for i in range(6):
            angle = math.tau * (i / 6.0)
            x = center.x + math.cos(angle) * radius
            y = center.y + math.sin(angle) * radius
            points.append((x, y))
        pygame.draw.polygon(surface, pygame.Color(198, 142, 255), points)
        pygame.draw.polygon(surface, pygame.Color(110, 60, 180), points, width=2)
        spark_rect = pygame.Rect(0, 0, 4, 8)
        spark_rect.center = center
        pygame.draw.rect(surface, pygame.Color(255, 255, 255), spark_rect)
        return surface

    def _create_weapon_pickup_sprite(self) -> pygame.Surface:
        width, height = 20, 8
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        barrel = pygame.Rect(0, height // 2 - 1, width - 4, 3)
        pygame.draw.rect(surface, pygame.Color(160, 180, 210), barrel, border_radius=2)
        grip = pygame.Rect(width - 6, height // 2 - 1, 6, 5)
        pygame.draw.rect(surface, pygame.Color(70, 70, 90), grip, border_radius=2)
        accent = pygame.Rect(width // 3, height // 2 - 2, 4, 4)
        pygame.draw.rect(surface, pygame.Color(255, 220, 110), accent)
        return surface

    def _create_bundle_pickup_sprite(self) -> pygame.Surface:
        width, height = 16, 16
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        crate_rect = pygame.Rect(1, 2, width - 2, height - 3)
        pygame.draw.rect(surface, pygame.Color(168, 118, 72), crate_rect, border_radius=2)
        grain_lines = [
            pygame.Rect(crate_rect.left + 2, crate_rect.top + 2, crate_rect.width - 4, 2),
            pygame.Rect(crate_rect.left + 3, crate_rect.centery - 1, crate_rect.width - 6, 2),
        ]
        for line in grain_lines:
            pygame.draw.rect(surface, pygame.Color(136, 90, 52), line, border_radius=2)
        pygame.draw.rect(surface, pygame.Color(96, 60, 32), crate_rect, width=2, border_radius=2)
        band_h = pygame.Rect(2, height // 2 - 2, width - 4, 4)
        band_v = pygame.Rect(width // 2 - 2, 3, 4, height - 6)
        pygame.draw.rect(surface, pygame.Color(238, 206, 104), band_h, border_radius=2)
        pygame.draw.rect(surface, pygame.Color(244, 214, 128), band_v, border_radius=2)
        knot_rect = pygame.Rect(width // 2 - 3, band_h.top - 3, 6, 6)
        pygame.draw.rect(surface, pygame.Color(196, 68, 68), knot_rect, border_radius=3)
        knot_highlight = knot_rect.inflate(-2, -2)
        pygame.draw.rect(surface, pygame.Color(236, 112, 112), knot_highlight, border_radius=2)
        return surface

    def _load_surface(self, path: Path) -> pygame.Surface | None:
        try:
            return pygame.image.load(path.as_posix()).convert_alpha()
        except FileNotFoundError:
            print(f"[HUD] Advertencia: no se encontró la imagen '{path}'. Se usará un marcador.")
        except pygame.error as exc:  # pragma: no cover - depende de SDL
            print(f"[HUD] Error al cargar '{path}': {exc}. Se usará un marcador.")
        return None

    def _create_procedural_microchip(self) -> tuple[pygame.Surface, pygame.Surface]:
        base_size = 32
        chip = pygame.Surface((base_size, base_size), pygame.SRCALPHA)
        chip.fill((0, 0, 0, 0))

        body_rect = chip.get_rect().inflate(-8, -8)
        frame_color = pygame.Color(120, 20, 80)
        frame_shadow = pygame.Color(70, 10, 48)
        pygame.draw.rect(chip, frame_shadow, body_rect, border_radius=6)
        pygame.draw.rect(chip, frame_color, body_rect.inflate(-2, -2), border_radius=6)

        core_rect = body_rect.inflate(-8, -8)
        core_color = pygame.Color(28, 94, 116)
        core_dark = pygame.Color(12, 48, 64)
        pygame.draw.rect(chip, core_color, core_rect, border_radius=5)
        pygame.draw.rect(chip, core_dark, core_rect, width=2, border_radius=5)

        highlight = pygame.Surface(core_rect.size, pygame.SRCALPHA)
        light_a = pygame.Color(136, 236, 238, 190)
        light_b = pygame.Color(94, 204, 220, 140)
        start_y = core_rect.height // 3
        pygame.draw.line(highlight, light_a, (3, start_y), (core_rect.width - 4, start_y - 3), 3)
        pygame.draw.line(highlight, light_b, (3, start_y + 4), (core_rect.width - 6, start_y + 1), 2)
        chip.blit(highlight, core_rect.topleft)

        pin_color = pygame.Color(230, 176, 70)
        pin_shadow = pygame.Color(156, 116, 46)
        pin_w, pin_h = 5, 6
        slots = 4
        slot_spacing = (body_rect.height - 12) / max(1, slots - 1)
        for i in range(slots):
            offset = int(body_rect.top + 6 + i * slot_spacing)
            left_pin = pygame.Rect(0, 0, pin_w, pin_h)
            left_pin.midright = (body_rect.left - 1, offset)
            right_pin = pygame.Rect(0, 0, pin_w, pin_h)
            right_pin.midleft = (body_rect.right + 1, offset)
            pygame.draw.rect(chip, pin_color, left_pin)
            pygame.draw.rect(chip, pin_shadow, left_pin, 1)
            pygame.draw.rect(chip, pin_color, right_pin)
            pygame.draw.rect(chip, pin_shadow, right_pin, 1)

        slot_spacing = (body_rect.width - 12) / max(1, slots - 1)
        for i in range(slots):
            offset = int(body_rect.left + 6 + i * slot_spacing)
            top_pin = pygame.Rect(0, 0, pin_h, pin_w)
            top_pin.midbottom = (offset, body_rect.top - 1)
            bottom_pin = pygame.Rect(0, 0, pin_h, pin_w)
            bottom_pin.midtop = (offset, body_rect.bottom + 1)
            pygame.draw.rect(chip, pin_color, top_pin)
            pygame.draw.rect(chip, pin_shadow, top_pin, 1)
            pygame.draw.rect(chip, pin_color, bottom_pin)
            pygame.draw.rect(chip, pin_shadow, bottom_pin, 1)

        pickup = pygame.transform.smoothscale(chip, self.MICROCHIP_PICKUP_SIZE)
        return chip, pickup

    def _load_weapon_icons(self) -> dict[str, pygame.Surface]:
        icons: dict[str, pygame.Surface] = {}
        for weapon_id in WEAPON_SPRITE_FILENAMES:
            path = weapon_sprite_path(weapon_id)
            try:
                surface = pygame.image.load(path.as_posix()).convert_alpha()
            except FileNotFoundError:
                print(
                    f"[HUD] Advertencia: sprite de arma '{path}' no encontrado. Se usará un marcador.")
                surface = self._create_weapon_placeholder_icon(weapon_id)
            except pygame.error as exc:  # pragma: no cover - depende de SDL
                print(
                    f"[HUD] Error al cargar '{path}': {exc}. Se usará un marcador.")
                surface = self._create_weapon_placeholder_icon(weapon_id)
            icons[weapon_id] = surface

        if "__missing__" not in icons:
            icons["__missing__"] = self._create_weapon_placeholder_icon(None)
        return icons

    def _create_weapon_placeholder_icon(self, weapon_id: str | None) -> pygame.Surface:
        size = 128
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))
        rect = surface.get_rect()
        base_color = pygame.Color(40, 44, 52, 200)
        frame_color = pygame.Color(120, 130, 150)
        pygame.draw.rect(surface, base_color, rect.inflate(-8, -8), border_radius=16)
        pygame.draw.rect(surface, frame_color, rect.inflate(-10, -10), width=3, border_radius=16)

        label = "???" if not weapon_id else weapon_id.replace("_", " ")
        label_surface = self.ui_font.render(label.upper(), True, (220, 220, 220))
        label_rect = label_surface.get_rect(center=rect.center)
        surface.blit(label_surface, label_rect.topleft)
        return surface

    def _get_scaled_weapon_icon(self, weapon_id: str, scale: float) -> pygame.Surface | None:
        base_id = weapon_id if weapon_id in self._weapon_icons else "__missing__"
        base_surface = self._weapon_icons.get(base_id)
        if base_surface is None:
            return None

        # Ajuste específico para short_rifle
        if weapon_id == "short_rifle":
            scale *= 0.25
        elif weapon_id == "dual_pistols":
            scale *= 0.18

        scale = max(0.05, float(scale))
        cache_key = (base_id, round(scale, 4))
        cached = self._weapon_icon_cache.get(cache_key)
        if cached is not None:
            return cached

        width = max(1, int(base_surface.get_width() * scale))
        height = max(1, int(base_surface.get_height() * scale))
        scaled = pygame.transform.smoothscale(base_surface, (width, height))
        self._weapon_icon_cache[cache_key] = scaled
        return scaled

    def _draw_weapon_hud(self, inventory_rect: pygame.Rect) -> pygame.Rect:
        player = getattr(self, "player", None)
        weapon = getattr(player, "weapon", None) if player is not None else None
        weapon_id = getattr(player, "weapon_id", None) if player is not None else None
        if weapon is None or weapon_id is None:
            return pygame.Rect(0, 0, 0, 0)

        # Obtener configuración de esta arma (o usar valores por defecto)
        weapon_config = self.WEAPON_HUD_CONFIG.get(weapon_id, {
            "offset_x": 0,
            "offset_y": 0,
            "scale": 1.0
        })
        
        # Aplicar escala personalizada del arma además de la escala global
        weapon_scale = weapon_config.get("scale", 1.0)
        combined_scale = self.weapon_icon_scale * weapon_scale
        
        icon_surface = self._get_scaled_weapon_icon(weapon_id, combined_scale)
        if icon_surface is None:
            return pygame.Rect(0, 0, 0, 0)

        # Aplicar offset específico del arma desde la configuración
        extra_x = weapon_config.get("offset_x", 0)
        extra_y = weapon_config.get("offset_y", 0)

        base_x = inventory_rect.left + int(self.weapon_icon_offset.x) + extra_x
        base_y = inventory_rect.top + int(self.weapon_icon_offset.y) + extra_y
        icon_rect = icon_surface.get_rect(topleft=(base_x, base_y))
        self.screen.blit(icon_surface, icon_rect.topleft)
        
        shots_remaining = getattr(weapon, "shots_in_mag", 0)
        magazine_size = getattr(weapon, "magazine_size", 0)
        ammo_text = f"Balas: {shots_remaining}/{magazine_size}"
        if hasattr(weapon, "is_reloading") and weapon.is_reloading():
            ammo_text = f"Recargando ({shots_remaining}/{magazine_size})"

        # Dibujar texto de munición en el centro de la pantalla
        ammo_surface = self.ammo_font.render(ammo_text, True, (255, 255, 255))
        ammo_rect = ammo_surface.get_rect()
        screen_w, screen_h = self.screen.get_size()
        # Posicionar en el centro con offsets configurables
        ammo_rect.center = (
            screen_w // 2 + int(self.ammo_text_offset_x),
            screen_h // 2 + int(self.ammo_text_offset_y)
        )
        
        # Dibujar sombra negra para mejor visibilidad
        shadow_surface = self.ammo_font.render(ammo_text, True, (0, 0, 0))
        shadow_rect = shadow_surface.get_rect()
        shadow_rect.center = (ammo_rect.centerx + 2, ammo_rect.centery + 2)
        self.screen.blit(shadow_surface, shadow_rect)
        self.screen.blit(ammo_surface, ammo_rect)
        return icon_rect

    def _create_cursor_surface(self) -> pygame.Surface:
        cursor_path = Path(__file__).resolve().parent.parent / "assets/ui/cursor2.png"
        try:
            surface = pygame.image.load(cursor_path.as_posix()).convert_alpha()
        except pygame.error as exc:  # pragma: no cover - carga de recursos
            raise FileNotFoundError(
                f"No se pudo cargar la imagen del cursor en {cursor_path}"
            ) from exc
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
        buffer_hp = max(0, int(getattr(self.player, "life_charge_buffer", 0)))

        lost_lives = max(0, min(max_lives, max_lives - lives_remaining))
        buffer_distribution = [0] * lost_lives
        remaining_buffer = buffer_hp
        for slot in range(lost_lives - 1, -1, -1):
            if remaining_buffer <= 0:
                break
            fill = min(max_hp, remaining_buffer)
            buffer_distribution[slot] = fill
            remaining_buffer -= fill

        icons: list[pygame.Surface] = []
        for index in range(max_lives):
            if lives_remaining <= 0:
                hp_value = 0
            elif index < lost_lives:
                hp_value = buffer_distribution[index]
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
    
    def _draw_frame_end(self) -> None:
        """(Inserta este bloque donde termines de dibujar el frame, antes del flip)"""
        # ...existing drawing code for world, VFX, HUD panels, etc. ...

        # Dibujar barra(es) HUD de boss(es) en la superficie final (arriba, sin cámara)
        screen_surf = getattr(self, "screen", None) or getattr(self, "screen_surf", None)
        if screen_surf is None:
            return

        # Intentar obtener boss activo; fallback: buscar BossEnemy en la sala actual
        boss = None
        try:
            room = getattr(self.dungeon, "current_room", None)
            if room:
                boss = getattr(self, "_active_boss", lambda r: None)(room)
                if boss is None:
                    for e in getattr(room, "enemies", []) or []:
                        if isinstance(e, BossEnemy):
                            boss = e
                            break
        except Exception:
            boss = None

        if boss is not None:
            try:
                boss.draw_health_bar_hud(screen_surf, index=0, top_padding=8)
            except Exception as e:
                if DEBUG_BOSS_HP:
                    print("Error dibujando HUD boss bar:", e)

        # ...añadir aquí display.flip() / pygame.display.update() ...
