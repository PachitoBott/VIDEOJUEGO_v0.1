"""
Tests unitarios para la clase Game del roguelike.

Cubre los métodos más críticos:
- start_new_run: Inicialización de partidas
- _handle_collisions: Sistema de combate y colisiones
- _drop_enemy_microchips: Sistema de recompensas
- _handle_player_death: Lógica de game over
- _add_player_gold: Economía del jugador
- _update_room_lock: Mecánica de puertas
"""

import pytest
import pygame
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from pathlib import Path
import sys

# Añadir la carpeta CODIGO al path para poder importar
sys.path.insert(0, str(Path(__file__).parent.parent / "CODIGO"))

# Inicializar pygame para los tests
pygame.init()


def _create_mock_surface():
    """Helper para crear un surface mock completo."""
    mock_surface = Mock()
    mock_surface.convert_alpha = Mock(return_value=mock_surface)
    mock_surface.get_width = Mock(return_value=32)
    mock_surface.get_height = Mock(return_value=32)
    mock_surface.get_size = Mock(return_value=(32, 32))
    mock_surface.get_rect = Mock(return_value=pygame.Rect(0, 0, 32, 32))
    mock_surface.blit = Mock()
    mock_surface.fill = Mock()
    return mock_surface


def _mock_create_microchip_sprites(self):
    """Mock para _create_microchip_sprites que devuelve surfaces mockeados."""
    icon_surface = _create_mock_surface()
    pickup_surface = _create_mock_surface()
    return (icon_surface, pickup_surface)


class TestGameInitialization:
    """Tests para la inicialización del juego."""
    
    def setup_method(self):
        """Configuración antes de cada test."""
        # Mock de Config con TODOS los atributos necesarios
        self.mock_config = Mock()
        self.mock_config.SCREEN_W = 640
        self.mock_config.SCREEN_H = 480
        self.mock_config.SCREEN_SCALE = 2  # Debe ser int, no Mock
        self.mock_config.FPS = 60
        self.mock_config.COLOR_BG = (0, 0, 0)
        self.mock_config.DEBUG_DRAW_DOOR_TRIGGERS = False
        self.mock_config.PLAYER_START_LIVES = 3
        self.mock_config.TILE_SIZE = 32
        self.mock_config.MAP_W = 30
        self.mock_config.MAP_H = 20
        self.mock_config.dungeon_params = Mock(return_value={
            'grid_w': 7, 'grid_h': 7, 'main_len': 8
        })
        
    @patch('Game.Tileset')
    @patch('Game.Minimap')
    @patch('Game.Shop')
    @patch('Game.HudPanels')
    @patch('Game.StatisticsManager')
    @patch('Game.pygame.image.load')
    @patch('Game.pygame.Surface')
    @patch('Game.Game._create_microchip_sprites', _mock_create_microchip_sprites)
    def test_game_initialization(self, mock_pygame_surface, mock_load, 
                                  mock_stats, mock_hud, mock_shop, 
                                  mock_minimap, mock_tileset):
        """Verifica que Game se inicializa correctamente."""
        from Game import Game
        
        # Mock de surfaces
        mock_surface = _create_mock_surface()
        mock_load.return_value = mock_surface
        mock_pygame_surface.return_value = mock_surface
        
        game = Game(self.mock_config)
        
        # Verificar que se crearon los componentes esenciales
        assert game.cfg == self.mock_config
        assert game.running is True
        assert game.projectiles is not None
        assert game.enemy_projectiles is not None
        assert game.door_cooldown == 0.0
        
        # Verificar que los sistemas de UI se inicializaron
        assert game.ui_font is not None
        assert game.shop is not None
        assert game.hud_panels is not None
        
        # Verificar que se crearon los componentes esenciales
        assert game.cfg == self.mock_config
        assert game.running is True
        assert game.projectiles is not None
        assert game.enemy_projectiles is not None
        assert game.door_cooldown == 0.0
        
        # Verificar que los sistemas de UI se inicializaron
        assert game.ui_font is not None
        assert game.shop is not None
        assert game.hud_panels is not None


class TestStartNewRun:
    """Tests para el método start_new_run."""
    
    @pytest.fixture
    def game(self):
        """Fixture que crea una instancia de Game mockeada."""
        with patch('Game.pygame.image.load') as mock_img_load, \
             patch('Game.pygame.Surface') as mock_pygame_surface, \
             patch('Game.Game._create_microchip_sprites', _mock_create_microchip_sprites), \
             patch('Game.Tileset'), \
             patch('Game.Minimap'), \
             patch('Game.Shop'), \
             patch('Game.HudPanels'), \
             patch('Game.StatisticsManager'), \
             patch('Game.Dungeon') as mock_dungeon, \
             patch('Game.Player') as mock_player:
            
            # Mock de surfaces
            mock_surface = _create_mock_surface()
            mock_img_load.return_value = mock_surface
            mock_pygame_surface.return_value = mock_surface
            
            from Game import Game
            mock_config = Mock()
            mock_config.SCREEN_W = 640
            mock_config.SCREEN_H = 480
            mock_config.SCREEN_SCALE = 2
            mock_config.FPS = 60
            mock_config.COLOR_BG = (0, 0, 0)
            mock_config.DEBUG_DRAW_DOOR_TRIGGERS = False
            mock_config.TILE_SIZE = 32
            mock_config.MAP_W = 30
            mock_config.MAP_H = 20
            mock_config.dungeon_params = Mock(return_value={})
            
            game = Game(mock_config)
            game.player = Mock()
            game.player.x = 0
            game.player.y = 0
            game.player.w = 18
            game.player.h = 24
            game.player.gold = 0
            game.player.reset_loadout = Mock()
            
            # Mock de dungeon con center_px que devuelve tupla
            game.dungeon = Mock()
            game.dungeon.seed = 12345
            game.dungeon.current_room = Mock()
            game.dungeon.current_room.center_px = Mock(return_value=(320, 240))
            game.dungeon.explored = set()
            game.dungeon.i = 3
            game.dungeon.j = 3
            
            yield game
    
    def test_start_new_run_with_seed(self, game):
        """Verifica que start_new_run funciona con una seed específica."""
        test_seed = 42
        game.start_new_run(seed=test_seed)
        
        assert game.current_seed == game.dungeon.seed
        assert (game.dungeon.i, game.dungeon.j) in game.dungeon.explored
        
    def test_start_new_run_resets_runtime_state(self, game):
        """Verifica que start_new_run resetea el estado del juego."""
        # Configurar estado previo
        game.projectiles.add(Mock())
        game.enemy_projectiles.add(Mock())
        game.door_cooldown = 1.5
        
        game.start_new_run(seed=123)
        
        # Verificar reset
        assert game.door_cooldown == 0.25  # Se reinicia pero con el valor de entrada
        game.projectiles.clear.assert_called()
        game.enemy_projectiles.clear.assert_called()
        
    def test_start_new_run_finalizes_previous_stats(self, game):
        """Verifica que se finalizan las estadísticas de la partida anterior."""
        game._run_start_time = 100.0
        game._finalize_run_statistics = Mock()
        
        game.start_new_run(seed=999)
        
        game._finalize_run_statistics.assert_called_once()


class TestHandleCollisions:
    """Tests para el sistema de colisiones."""
    
    @pytest.fixture
    def game_with_room(self):
        """Fixture con un juego y sala configurados."""
        with patch('Game.pygame.image.load') as mock_img_load, \
             patch('Game.pygame.Surface') as mock_pygame_surface, \
             patch('Game.Game._create_microchip_sprites', _mock_create_microchip_sprites), \
             patch('Game.Tileset'), \
             patch('Game.Minimap'), \
             patch('Game.Shop'), \
             patch('Game.HudPanels'), \
             patch('Game.StatisticsManager'):
            
            # Mock de surfaces
            mock_surface = _create_mock_surface()
            mock_img_load.return_value = mock_surface
            mock_pygame_surface.return_value = mock_surface
            
            from Game import Game
            mock_config = Mock()
            mock_config.SCREEN_W = 640
            mock_config.SCREEN_H = 480
            mock_config.SCREEN_SCALE = 2
            mock_config.FPS = 60
            mock_config.COLOR_BG = (0, 0, 0)
            mock_config.DEBUG_DRAW_DOOR_TRIGGERS = False
            mock_config.TILE_SIZE = 32
            mock_config.MAP_W = 30
            mock_config.MAP_H = 20
            mock_config.dungeon_params = Mock(return_value={})
            
            game = Game(mock_config)
            
            # Mock player
            game.player = Mock()
            game.player.rect = Mock(return_value=pygame.Rect(100, 100, 18, 24))
            game.player.hp = 3
            game.player.is_invulnerable = Mock(return_value=False)
            game.player.is_phase_active = Mock(return_value=False)
            game.player.take_damage = Mock(return_value=True)
            
            # Mock room con enemigos
            room = Mock()
            room.enemies = []
            room.refresh_lock_state = Mock()
            
            game.dungeon = Mock()
            game.dungeon.current_room = room
            
            # Mock projectiles
            game.projectiles = Mock()
            game.projectiles.__iter__ = Mock(return_value=iter([]))
            game.projectiles.prune = Mock()
            
            game.enemy_projectiles = Mock()
            game.enemy_projectiles.__iter__ = Mock(return_value=iter([]))
            game.enemy_projectiles.prune = Mock()
            
            yield game, room
    
    def test_collision_player_hit_by_projectile(self, game_with_room):
        """Verifica que el jugador recibe daño de proyectiles enemigos."""
        game, room = game_with_room
        
        # Crear proyectil enemigo
        enemy_proj = Mock()
        enemy_proj.alive = True
        enemy_proj.ignore_player_timer = 0.0
        enemy_proj.rect = Mock(return_value=pygame.Rect(100, 100, 6, 6))
        
        game.enemy_projectiles.__iter__ = Mock(return_value=iter([enemy_proj]))
        
        player_died = game._handle_collisions(room)
        
        # El jugador debe haber tomado daño
        game.player.take_damage.assert_called_once_with(1)
        assert enemy_proj.alive is False
        assert player_died is False  # No murió (tiene 3 HP)
        
    def test_collision_enemy_hit_by_projectile(self, game_with_room):
        """Verifica que enemigos reciben daño de proyectiles del jugador."""
        game, room = game_with_room
        
        # Crear enemigo
        enemy = Mock()
        enemy.hp = 2
        enemy.rect = Mock(return_value=pygame.Rect(150, 150, 12, 12))
        enemy.take_damage = Mock()
        room.enemies = [enemy]
        
        # Crear proyectil del jugador
        proj = Mock()
        proj.alive = True
        proj.rect = Mock(return_value=pygame.Rect(150, 150, 4, 4))
        proj.dx = 1.0
        proj.dy = 0.0
        
        game.projectiles.__iter__ = Mock(return_value=iter([proj]))
        
        game._handle_collisions(room)
        
        # El enemigo debe recibir daño
        enemy.take_damage.assert_called_once()
        assert proj.alive is False
        
    def test_collision_player_invulnerable_ignores_damage(self, game_with_room):
        """Verifica que jugador invulnerable no recibe daño."""
        game, room = game_with_room
        game.player.is_invulnerable = Mock(return_value=True)
        
        enemy_proj = Mock()
        enemy_proj.alive = True
        enemy_proj.ignore_player_timer = 0.0
        enemy_proj.rect = Mock(return_value=pygame.Rect(100, 100, 6, 6))
        
        game.enemy_projectiles.__iter__ = Mock(return_value=iter([enemy_proj]))
        
        game._handle_collisions(room)
        
        # No debe tomar daño
        game.player.take_damage.assert_not_called()
        
    def test_collision_removes_dead_enemies(self, game_with_room):
        """Verifica que enemigos muertos se eliminan de la sala."""
        game, room = game_with_room
        game._drop_enemy_microchips = Mock()
        
        # Enemigo vivo
        enemy1 = Mock()
        enemy1.hp = 1
        enemy1.is_ready_to_remove = Mock(return_value=False)
        enemy1.is_dying = Mock(return_value=False)
        enemy1.rect = Mock(return_value=pygame.Rect(200, 200, 12, 12))
        
        # Enemigo muriendo
        enemy2 = Mock()
        enemy2.hp = 0
        enemy2.is_ready_to_remove = Mock(return_value=True)
        enemy2.is_dying = Mock(return_value=True)
        enemy2.rect = Mock(return_value=pygame.Rect(250, 250, 12, 12))
        
        room.enemies = [enemy1, enemy2]
        
        game._handle_collisions(room)
        
        # Solo debe quedar el enemigo vivo
        assert len(room.enemies) == 1
        assert enemy1 in room.enemies
        game._drop_enemy_microchips.assert_called_once_with(enemy2, room)


class TestDropEnemyMicrochips:
    """Tests para el sistema de drop de monedas."""
    
    @pytest.fixture
    def game_with_sprites(self):
        """Fixture con sprites de microchip."""
        with patch('Game.pygame.image.load') as mock_img_load, \
             patch('Game.pygame.Surface') as mock_pygame_surface, \
             patch('Game.Game._create_microchip_sprites', _mock_create_microchip_sprites), \
             patch('Game.Tileset'), \
             patch('Game.Minimap'), \
             patch('Game.Shop'), \
             patch('Game.HudPanels'), \
             patch('Game.StatisticsManager'), \
             patch('Game.MicrochipPickup') as mock_pickup:
            
            # Mock de surfaces
            mock_surface = _create_mock_surface()
            mock_img_load.return_value = mock_surface
            mock_pygame_surface.return_value = mock_surface
            
            from Game import Game
            mock_config = Mock()
            mock_config.SCREEN_W = 640
            mock_config.SCREEN_H = 480
            mock_config.SCREEN_SCALE = 2
            mock_config.FPS = 60
            mock_config.COLOR_BG = (0, 0, 0)
            mock_config.DEBUG_DRAW_DOOR_TRIGGERS = False
            mock_config.TILE_SIZE = 32
            mock_config.MAP_W = 30
            mock_config.MAP_H = 20
            mock_config.dungeon_params = Mock(return_value={})
            
            game = Game(mock_config)
            
            # Mock del sprite de chip
            game._chip_pickup_sprite = Mock()
            game._chip_pickup_sprite.get_width = Mock(return_value=12)
            game._chip_pickup_sprite.get_height = Mock(return_value=12)
            
            yield game, mock_pickup
    
    def test_drop_microchips_creates_pickups(self, game_with_sprites):
        """Verifica que se crean pickups al matar enemigos."""
        game, mock_pickup = game_with_sprites
        
        enemy = Mock()
        enemy.x = 100
        enemy.y = 100
        enemy.w = 12
        enemy.h = 12
        enemy.gold_reward = 10
        
        room = Mock()
        room.pickups = []
        
        game._drop_enemy_microchips(enemy, room)
        
        # Debe haber creado al menos un pickup
        assert len(room.pickups) > 0
        
    def test_drop_microchips_zero_reward(self, game_with_sprites):
        """Verifica que enemigos sin recompensa no dropean nada."""
        game, mock_pickup = game_with_sprites
        
        enemy = Mock()
        enemy.gold_reward = 0
        
        room = Mock()
        room.pickups = []
        
        game._drop_enemy_microchips(enemy, room)
        
        assert len(room.pickups) == 0
        
    def test_chip_count_for_reward(self, game_with_sprites):
        """Verifica el cálculo correcto de cantidad de chips."""
        game, _ = game_with_sprites
        
        # Recompensa pequeña: 1-2 chips
        min_count, max_count = game._chip_count_for_reward(3)
        assert min_count == 1
        assert max_count == 2
        
        # Recompensa mediana: 2-3 chips
        min_count, max_count = game._chip_count_for_reward(7)
        assert min_count == 2
        assert max_count == 3
        
        # Recompensa grande: 3-4 chips
        min_count, max_count = game._chip_count_for_reward(15)
        assert min_count == 3
        assert max_count == 4


class TestAddPlayerGold:
    """Tests para agregar oro al jugador."""
    
    @pytest.fixture
    def game_with_player(self):
        """Fixture con jugador."""
        with patch('Game.pygame.image.load') as mock_img_load, \
             patch('Game.pygame.Surface') as mock_pygame_surface, \
             patch('Game.Game._create_microchip_sprites', _mock_create_microchip_sprites), \
             patch('Game.Tileset'), \
             patch('Game.Minimap'), \
             patch('Game.Shop'), \
             patch('Game.HudPanels'), \
             patch('Game.StatisticsManager'):
            
            # Mock de surfaces
            mock_surface = _create_mock_surface()
            mock_img_load.return_value = mock_surface
            mock_pygame_surface.return_value = mock_surface
            
            from Game import Game
            mock_config = Mock()
            mock_config.SCREEN_W = 640
            mock_config.SCREEN_H = 480
            mock_config.SCREEN_SCALE = 2
            mock_config.FPS = 60
            mock_config.COLOR_BG = (0, 0, 0)
            mock_config.DEBUG_DRAW_DOOR_TRIGGERS = False
            mock_config.TILE_SIZE = 32
            mock_config.MAP_W = 30
            mock_config.MAP_H = 20
            mock_config.dungeon_params = Mock(return_value={})
            
            game = Game(mock_config)
            game.player = Mock()
            game.player.gold = 0
            
            yield game
    
    def test_add_gold_increases_player_gold(self, game_with_player):
        """Verifica que se suma oro correctamente."""
        game = game_with_player
        
        game._add_player_gold(10)
        assert game.player.gold == 10
        
        game._add_player_gold(5)
        assert game.player.gold == 15
        
    def test_add_gold_negative_amount_ignored(self, game_with_player):
        """Verifica que cantidades negativas se ignoran."""
        game = game_with_player
        game.player.gold = 50
        
        game._add_player_gold(-10)
        assert game.player.gold == 50
        
    def test_add_gold_zero_amount_ignored(self, game_with_player):
        """Verifica que cero no afecta el oro."""
        game = game_with_player
        game.player.gold = 25
        
        game._add_player_gold(0)
        assert game.player.gold == 25


class TestHandlePlayerDeath:
    """Tests para la lógica de muerte del jugador."""
    
    @pytest.fixture
    def game_with_death_setup(self):
        """Fixture con configuración para muerte."""
        with patch('Game.pygame.image.load') as mock_img_load, \
             patch('Game.pygame.Surface') as mock_pygame_surface, \
             patch('Game.Game._create_microchip_sprites', _mock_create_microchip_sprites), \
             patch('Game.Tileset'), \
             patch('Game.Minimap'), \
             patch('Game.Shop'), \
             patch('Game.HudPanels'), \
             patch('Game.StatisticsManager'):
            
            # Mock de surfaces
            mock_surface = _create_mock_surface()
            mock_img_load.return_value = mock_surface
            mock_pygame_surface.return_value = mock_surface
            
            from Game import Game
            mock_config = Mock()
            mock_config.SCREEN_W = 640
            mock_config.SCREEN_H = 480
            mock_config.SCREEN_SCALE = 2
            mock_config.FPS = 60
            mock_config.COLOR_BG = (0, 0, 0)
            mock_config.DEBUG_DRAW_DOOR_TRIGGERS = False
            mock_config.TILE_SIZE = 32
            mock_config.MAP_W = 30
            mock_config.MAP_H = 20
            mock_config.dungeon_params = Mock(return_value={})
            
            game = Game(mock_config)
            game.player = Mock()
            game.player.hp = 0
            game.player.lives = 1
            game.player.max_hp = 3
            game.player.w = 18
            game.player.h = 24
            game.player.gold = 50
            game.player.lose_life = Mock(return_value=True)
            game.player.respawn = Mock()
            
            game.dungeon = Mock()
            game.dungeon.explored = {(0, 0), (1, 0)}
            
            room = Mock()
            room.center_px = Mock(return_value=(320, 240))
            game.dungeon.current_room = room
            
            game._collect_run_summary = Mock(return_value={
                'coins': 50,
                'kills': 10,
                'rooms': 5
            })
            game._record_stats_death = Mock()
            game._finalize_run_statistics = Mock()
            game._show_game_over_screen = Mock(return_value='restart')
            game.start_new_run = Mock()
            
            yield game, room
    
    def test_player_death_with_lives_respawns(self, game_with_death_setup):
        """Verifica que el jugador revive si tiene vidas."""
        game, room = game_with_death_setup
        
        game._handle_player_death(room)
        
        # Debe llamar lose_life y respawn
        game.player.lose_life.assert_called_once()
        game.player.respawn.assert_called_once()
        
        # No debe mostrar game over
        game._show_game_over_screen.assert_not_called()
        
    def test_player_death_no_lives_shows_game_over(self, game_with_death_setup):
        """Verifica que sin vidas se muestra el game over."""
        game, room = game_with_death_setup
        game.player.lose_life = Mock(return_value=False)
        
        game._handle_player_death(room)
        
        # Debe mostrar game over
        game._show_game_over_screen.assert_called_once()
        game._record_stats_death.assert_called_once()
        game._finalize_run_statistics.assert_called_once()
        
    def test_player_death_clears_projectiles(self, game_with_death_setup):
        """Verifica que se limpian los proyectiles al morir."""
        game, room = game_with_death_setup
        game.projectiles = Mock()
        game.enemy_projectiles = Mock()
        
        game._handle_player_death(room)
        
        game.projectiles.clear.assert_called_once()
        game.enemy_projectiles.clear.assert_called_once()


class TestUpdateRoomLock:
    """Tests para el sistema de puertas bloqueadas."""
    
    @pytest.fixture
    def game_with_lockable_room(self):
        """Fixture con sala que puede bloquearse."""
        with patch('Game.pygame.image.load') as mock_img_load, \
             patch('Game.pygame.Surface') as mock_pygame_surface, \
             patch('Game.Game._create_microchip_sprites', _mock_create_microchip_sprites), \
             patch('Game.Tileset'), \
             patch('Game.Minimap'), \
             patch('Game.Shop'), \
             patch('Game.HudPanels'), \
             patch('Game.StatisticsManager'):
            
            # Mock de surfaces
            mock_surface = _create_mock_surface()
            mock_img_load.return_value = mock_surface
            mock_pygame_surface.return_value = mock_surface
            
            from Game import Game
            mock_config = Mock()
            mock_config.SCREEN_W = 640
            mock_config.SCREEN_H = 480
            mock_config.SCREEN_SCALE = 2
            mock_config.FPS = 60
            mock_config.COLOR_BG = (0, 0, 0)
            mock_config.DEBUG_DRAW_DOOR_TRIGGERS = False
            mock_config.TILE_SIZE = 32
            mock_config.MAP_W = 30
            mock_config.MAP_H = 20
            mock_config.dungeon_params = Mock(return_value={})
            
            game = Game(mock_config)
            
            game.dungeon = Mock()
            game.dungeon.grid_w = 7
            game.dungeon.grid_h = 7
            game.dungeon.i = 3
            game.dungeon.j = 3
            game.dungeon.start = (3, 3)
            
            room = Mock()
            room.enemies = []
            room.cleared = False
            room.locked = False
            
            yield game, room
    
    def test_room_locks_with_enemies(self, game_with_lockable_room):
        """Verifica que sala se bloquea con enemigos."""
        game, room = game_with_lockable_room
        
        # Agregar enemigos
        room.enemies = [Mock(), Mock()]
        game.dungeon.i = 2  # No es sala inicial
        
        game._update_room_lock(room)
        
        assert room.locked is True
        
    def test_room_unlocks_without_enemies(self, game_with_lockable_room):
        """Verifica que sala se desbloquea sin enemigos."""
        game, room = game_with_lockable_room
        room.enemies = []
        room.locked = True
        
        game._update_room_lock(room)
        
        assert room.locked is False
        
    def test_start_room_never_locks(self, game_with_lockable_room):
        """Verifica que la sala inicial nunca se bloquea."""
        game, room = game_with_lockable_room
        
        # En sala inicial
        game.dungeon.i = 3
        game.dungeon.j = 3
        game.dungeon.start = (3, 3)
        room.enemies = [Mock(), Mock()]
        
        game._update_room_lock(room)
        
        assert room.locked is False


class TestCollectRunSummary:
    """Tests para la recolección de estadísticas de la partida."""
    
    @pytest.fixture
    def game_with_stats(self):
        """Fixture con estadísticas."""
        with patch('Game.pygame.image.load') as mock_img_load, \
             patch('Game.pygame.Surface') as mock_pygame_surface, \
             patch('Game.Game._create_microchip_sprites', _mock_create_microchip_sprites), \
             patch('Game.Tileset'), \
             patch('Game.Minimap'), \
             patch('Game.Shop'), \
             patch('Game.HudPanels'), \
             patch('Game.StatisticsManager'):
            
            # Mock de surfaces
            mock_surface = _create_mock_surface()
            mock_img_load.return_value = mock_surface
            mock_pygame_surface.return_value = mock_surface
            
            from Game import Game
            mock_config = Mock()
            mock_config.SCREEN_W = 640
            mock_config.SCREEN_H = 480
            mock_config.SCREEN_SCALE = 2
            mock_config.FPS = 60
            mock_config.COLOR_BG = (0, 0, 0)
            mock_config.DEBUG_DRAW_DOOR_TRIGGERS = False
            mock_config.TILE_SIZE = 32
            mock_config.MAP_W = 30
            mock_config.MAP_H = 20
            mock_config.dungeon_params = Mock(return_value={})
            
            game = Game(mock_config)
            game.player = Mock()
            game.player.gold = 75
            
            game.dungeon = Mock()
            game.dungeon.explored = {(0, 0), (1, 0), (0, 1)}
            
            game._run_gold_spent = 25
            game._run_kills = 15
            
            yield game
    
    def test_collect_run_summary_accurate(self, game_with_stats):
        """Verifica que el resumen de partida sea preciso."""
        game = game_with_stats
        
        summary = game._collect_run_summary()
        
        assert summary['coins'] == 100  # 75 actuales + 25 gastados
        assert summary['kills'] == 15
        assert summary['rooms'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])