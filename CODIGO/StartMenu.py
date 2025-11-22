from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pygame

from Config import Config
from Statistics import StatisticsManager


@dataclass(frozen=True)
class StartMenuResult:
    """Resultado devuelto por el menú de inicio."""
    start_game: bool
    seed: Optional[int]
    skin_path: Optional[str]


class StartMenu:
    """Pantalla de inicio configurable (CyberQuest Edition)."""

    BUTTON_PADDING_X = 32
    BUTTON_PADDING_Y = 14
    BUTTON_GAP = 16
    INPUT_WIDTH = 320
    INPUT_HEIGHT = 48

    # Colores Cyberpunk
    COLOR_NEON_BLUE = (0, 255, 255)
    COLOR_NEON_PINK = (255, 0, 128)
    COLOR_DARK_BG = (10, 10, 20)
    COLOR_GRID = (30, 30, 60)
    COLOR_TEXT_WHITE = (240, 240, 255)

    def __init__(
        self,
        screen: pygame.Surface,
        cfg: Config,
        *,
        stats_manager: StatisticsManager | None = None,
    ) -> None:
        self.screen = screen
        self.cfg = cfg
        self.menu_cfg = cfg.START_MENU
        
        pygame.display.set_caption("CyberQuest")
        self.clock = pygame.time.Clock()

        # --- GESTIÓN DE RUTAS ---
        self.base_dir = Path(__file__).parent.resolve()
        self.ui_assets_dir = self.base_dir / "assets" / "ui"
        self.audio_assets_dir = self.base_dir / "assets" / "audio"  # Nueva ruta para audio

        # Debug info
        print(f"--- DEBUG START MENU ---")
        print(f"Assets UI: {self.ui_assets_dir}")
        print(f"Assets Audio: {self.audio_assets_dir}")

        # --- Volumen ---
        self.volume: float = (
            pygame.mixer.music.get_volume() if pygame.mixer.get_init() else 0.5
        )
        self.dragging_volume = False
        self.VOLUME_BAR_SIZE = (360, 10)
        self.VOLUME_HANDLE_SIZE = (18, 26)
        self.volume_bar_rect = pygame.Rect(0, 0, *self.VOLUME_BAR_SIZE)
        self.volume_handle_rect = pygame.Rect(0, 0, *self.VOLUME_HANDLE_SIZE)

        # --- Inicializar Audio ---
        self._init_audio()

        # --- Volumen ---
        self.volume: float = (
            pygame.mixer.music.get_volume() if pygame.mixer.get_init() else 0.5
        )
        self.dragging_volume = False
        self.VOLUME_BAR_SIZE = (360, 10)
        self.VOLUME_HANDLE_SIZE = (18, 26)
        self.volume_bar_rect = pygame.Rect(0, 0, *self.VOLUME_BAR_SIZE)
        self.volume_handle_rect = pygame.Rect(0, 0, *self.VOLUME_HANDLE_SIZE)

        # --- Carga de Fuentes ---
        self.title_font = self._get_font("VT323-Regular.ttf", 96)
        self.subtitle_font = self._get_font("VT323-Regular.ttf", 42)
        self.button_font = self._get_font("VT323-Regular.ttf", 48)
        self.small_font = self._get_font("VT323-Regular.ttf", 32)

        self.seed_text: str = ""
        self.input_active = False

        self.overlay_key: Optional[str] = None
        self.overlay_lines: tuple[str, ...] = ()
        self.stats_manager = stats_manager

        # --- Skins ---
        self.skin_options = self._build_skin_options()
        self.selected_skin_id = self._infer_default_skin_id()
        self.skin_rects: list[tuple[str, pygame.Rect]] = []
        self.skins_overlay_rect = pygame.Rect(0, 0, 0, 0)

        self.button_rects: list[tuple[str, pygame.Rect]] = []
        self.seed_rect = pygame.Rect(0, 0, self.INPUT_WIDTH, self.INPUT_HEIGHT)

        # --- Carga de Fondo ---
        self.background = self._load_image("fondoMenu.png")
        
        if not self.background and self.menu_cfg.background_image:
             path_cfg = Path(self.menu_cfg.background_image)
             if path_cfg.exists():
                 try:
                    self.background = pygame.image.load(str(path_cfg)).convert_alpha()
                 except:
                     pass

        self.logo = self._load_image(self.menu_cfg.logo_image)

        self._compute_layout()
        self._start_requested = False

    # ------------------------------------------------------------------
    # Audio Management
    # ------------------------------------------------------------------
    def _init_audio(self) -> None:
        """Inicializa el mixer, carga efectos y arranca la música."""
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error:
                print("No se pudo inicializar el módulo de audio.")
                return

        # 1. Cargar SFX Botón
        self.click_sound = self._load_sound("boton.mp3")

        # 2. Cargar y reproducir Música de Fondo
        music_file = "Perturbator.mp3"
        music_path = self._get_audio_path(music_file)
        
        if music_path and music_path.exists():
            try:
                pygame.mixer.music.load(str(music_path))
                pygame.mixer.music.set_volume(0.5) # Volumen al 50%
                pygame.mixer.music.play(-1) # -1 significa loop infinito
                print(f"Reproduciendo música: {music_file}")
            except Exception as e:
                print(f"Error reproduciendo música {music_file}: {e}")
        else:
            print(f"No se encontró música: {music_path}")

        self._apply_volume()

    def _get_audio_path(self, filename: str) -> Path | None:
        """Busca archivos de audio en assets/audio."""
        candidates = [
            self.audio_assets_dir / filename,
            self.base_dir / "assets" / "audio" / filename,
            Path.cwd() / "assets" / "audio" / filename
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _load_sound(self, filename: str) -> pygame.mixer.Sound | None:
        path = self._get_audio_path(filename)
        if path:
            try:
                return pygame.mixer.Sound(str(path))
            except Exception as e:
                print(f"Error cargando SFX {filename}: {e}")
        return None

    def _play_click(self) -> None:
        """Helper para reproducir el sonido de click si existe."""
        if self.click_sound:
            self.click_sound.play()

    # ------------------------------------------------------------------
    # Helpers & Path Finding (UI)
    # ------------------------------------------------------------------
    def _get_path(self, filename: str) -> Path:
        return self.ui_assets_dir / filename

    def _get_font(self, font_name: str, size: int) -> pygame.font.Font:
        font_path = self._get_path(font_name)
        if font_path.exists():
            try:
                return pygame.font.Font(str(font_path), size)
            except Exception as e:
                print(f"Error cargando fuente {font_name}: {e}")
        else:
            # Fallback silencioso si no encuentra la fuente exacta
            pass
        return pygame.font.SysFont("consolas", int(size * 0.7))

    def _load_image(self, filename: Optional[str]) -> Optional[pygame.Surface]:
        if not filename: return None
        clean_name = Path(filename).name
        image_path = self._get_path(clean_name)
        
        if not image_path.exists():
            return None

        try:
            image = pygame.image.load(str(image_path)).convert_alpha()
            return image
        except Exception:
            return None

    def _compute_layout(self) -> None:
        width, height = self.screen.get_size()
        center_x = width // 2

        self.button_rects.clear()

        if not self.menu_cfg.buttons:
            self.seed_rect.center = (center_x, height // 2)
            layout_bottom = self.seed_rect.bottom
        else:
            max_label_width = max(
                self.button_font.size(button.label)[0]
                for button in self.menu_cfg.buttons
            )
            button_width = max(max_label_width + self.BUTTON_PADDING_X * 2, 280)
            button_height = self.button_font.get_height() + self.BUTTON_PADDING_Y * 2

            total_height = len(self.menu_cfg.buttons) * button_height + (
                (len(self.menu_cfg.buttons) - 1) * self.BUTTON_GAP
            )

            start_y = height // 2 - total_height // 2 + 40

            for button in self.menu_cfg.buttons:
                rect = pygame.Rect(0, 0, button_width, button_height)
                rect.centerx = center_x
                rect.y = start_y
                self.button_rects.append((button.action, rect))
                start_y += button_height + self.BUTTON_GAP

            self.seed_rect.size = (self.INPUT_WIDTH, self.INPUT_HEIGHT)
            self.seed_rect.centerx = center_x
            self.seed_rect.y = start_y + 24
            layout_bottom = self.seed_rect.bottom

        self._position_volume_slider(center_x, layout_bottom)

    def _build_skin_options(self) -> list[dict[str, str]]:
        color_names = {
            "blue": "Azul",
            "red": "Rojo",
            "green": "Verde",
            "grey": "Gris",
        }
        body_names = {"flaco": "Flaco", "gordo": "Gordo"}
        base = Path("assets") / "player"
        options: list[dict[str, str]] = []
        for body in ("flaco", "gordo"):
            for color in ("blue", "red", "green", "grey"):
                skin_id = f"{color}_{body}"
                options.append(
                    {
                        "id": skin_id,
                        "label": f"{color_names[color]} {body_names[body]}",
                        "color": color_names[color],
                        "body": body_names[body],
                        "path": str(base / skin_id),
                    }
                )
        return options

    def _infer_default_skin_id(self) -> str:
        default = "blue_flaco"
        current = getattr(self.cfg, "PLAYER_SPRITES_PATH", None)
        if current:
            candidate = Path(current).name
            if any(option["id"] == candidate for option in self.skin_options):
                return candidate
        return default

    def _select_skin(self, skin_id: str) -> None:
        if any(option["id"] == skin_id for option in self.skin_options):
            self.selected_skin_id = skin_id

    def selected_skin_path(self) -> str:
        match = next((opt for opt in self.skin_options if opt["id"] == self.selected_skin_id), None)
        if match:
            return match["path"]
        return str(Path("assets") / "player" / self.selected_skin_id)

    def _position_volume_slider(self, center_x: int, layout_bottom: int) -> None:
        slider_y = layout_bottom + 70
        self.volume_bar_rect.centerx = center_x
        self.volume_bar_rect.y = slider_y
        self._update_volume_handle_pos()

    def _update_volume_handle_pos(self) -> None:
        ratio = max(0.0, min(1.0, self.volume))
        handle_x = self.volume_bar_rect.left + ratio * self.volume_bar_rect.width
        self.volume_handle_rect.center = (
            int(handle_x),
            self.volume_bar_rect.centery,
        )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> StartMenuResult:
        running = True
        while running:
            self.clock.tick(self.cfg.FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._start_requested = False
                    running = False
                    break
                if self.overlay_key:
                    if self.overlay_key == "skins":
                        keep_running = self._handle_skins_event(event)
                    else:
                        keep_running = self._handle_overlay_event(event)
                else:
                    keep_running = self._handle_menu_event(event)

                if not keep_running:
                    running = False
                    break

            if not running:
                break
            
            if self.overlay_key:
                self._draw_menu(dim_background=True)
                if self.overlay_key == "skins":
                    self._draw_skins_overlay()
                else:
                    self._draw_overlay()
            else:
                self._draw_menu()

            pygame.display.flip()

        if self._start_requested:
            # Detener la música del menú con un fadeout de 500ms al iniciar el juego
            pygame.mixer.music.fadeout(500)
            return StartMenuResult(
                start_game=True,
                seed=self.selected_seed(),
                skin_path=self.selected_skin_path(),
            )

        return StartMenuResult(start_game=False, seed=None, skin_path=None)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    def _handle_menu_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._start_requested = False
                return False
            if event.key == pygame.K_RETURN:
                # Sonido al iniciar con Enter
                self._play_click()
                return self._commit_play()
            if event.key == pygame.K_BACKSPACE:
                self.seed_text = self.seed_text[:-1]
            else:
                if event.unicode and event.unicode.isdigit():
                    if len(self.seed_text) < 16:
                        self.seed_text += event.unicode
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._is_over_volume(event.pos):
                self.dragging_volume = True
                self._set_volume_from_mouse(event.pos[0])
                return True
            if self.seed_rect.collidepoint(event.pos):
                self.input_active = True
            else:
                self.input_active = False
                for action, rect in self.button_rects:
                    if rect.collidepoint(event.pos):
                        # Sonido al hacer click en botón
                        self._play_click()
                        return self._trigger_button(action)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_volume = False
        elif event.type == pygame.MOUSEMOTION and self.dragging_volume:
            self._set_volume_from_mouse(event.pos[0])
        return True

    def _handle_overlay_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_ESCAPE,
            pygame.K_RETURN,
            pygame.K_BACKSPACE,
        ):
            self.overlay_key = None
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.overlay_key = None
            return True
        if event.type == pygame.QUIT:
            self._start_requested = False
            return False
        return True

    def _handle_skins_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in (
            pygame.K_ESCAPE,
            pygame.K_RETURN,
            pygame.K_BACKSPACE,
        ):
            self.overlay_key = None
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if (
                self.skins_overlay_rect.width
                and self.skins_overlay_rect.height
                and not self.skins_overlay_rect.collidepoint(event.pos)
            ):
                self.overlay_key = None
                return True
            for skin_id, rect in self.skin_rects:
                if rect.collidepoint(event.pos):
                    self._play_click()
                    self._select_skin(skin_id)
                    return True
        if event.type == pygame.QUIT:
            self._start_requested = False
            return False
        return True

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _trigger_button(self, action: str) -> bool:
        if action == "play":
            return self._commit_play()
        if action == "skins":
            self.overlay_key = action
            self.overlay_lines = ()
            return True
        if action == "credits" or action == "controls":
            if action in self.menu_cfg.sections:
                self.overlay_key = action
                self.overlay_lines = self.menu_cfg.sections[action]
                return True
        if action == "statistics":
            self.overlay_key = action
            self.overlay_lines = self._statistics_lines()
            return True
        if action in self.menu_cfg.sections:
            self.overlay_key = action
            self.overlay_lines = self.menu_cfg.sections[action]
            return True
        if action == "quit":
            return False

        self.overlay_key = action
        self.overlay_lines = (
            f"Acción '{action}' sin comportamiento.",
            "Edita Config.START_MENU.",
        )
        return True

    def _commit_play(self) -> bool:
        self._start_requested = True
        self.overlay_key = None
        return False

    def selected_seed(self) -> Optional[int]:
        if not self.seed_text:
            return None
        try:
            return int(self.seed_text)
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _draw_cyber_grid(self) -> None:
        """Dibuja una cuadrícula estilo synthwave si no hay imagen de fondo."""
        self.screen.fill(self.COLOR_DARK_BG)
        width, height = self.screen.get_size()
        
        for x in range(0, width, 40):
            pygame.draw.line(self.screen, self.COLOR_GRID, (x, 0), (x, height), 1)
        for y in range(0, height, 40):
            pygame.draw.line(self.screen, self.COLOR_GRID, (0, y), (width, y), 1)

    def _draw_menu(self, *, dim_background: bool = False) -> None:
        width, height = self.screen.get_size()

        # 1. Fondo
        if self.background:
            background = pygame.transform.smoothscale(self.background, (width, height))
            self.screen.blit(background, (0, 0))
        else:
            self._draw_cyber_grid()

        if dim_background:
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))

        # 2. Título CYBERQUEST
        title_text = "CYBERQUEST"
        
        # Sombra del título
        shadow_surf = self.title_font.render(title_text, True, self.COLOR_NEON_PINK)
        shadow_rect = shadow_surf.get_rect(center=(width // 2 + 4, height // 5 + 4))
        self.screen.blit(shadow_surf, shadow_rect)

        # Título principal
        title_surf = self.title_font.render(title_text, True, self.COLOR_NEON_BLUE)
        title_rect = title_surf.get_rect(center=(width // 2, height // 5))
        self.screen.blit(title_surf, title_rect)

        # Subtítulo
        if self.menu_cfg.subtitle:
            subtitle_surf = self.subtitle_font.render(
                self.menu_cfg.subtitle, True, (200, 200, 200)
            )
            subtitle_rect = subtitle_surf.get_rect(
                center=(width // 2, title_rect.bottom + 10)
            )
            self.screen.blit(subtitle_surf, subtitle_rect)

        # Logo opcional
        if self.logo:
            logo_rect = self.logo.get_rect()
            logo_rect.center = (width // 2, title_rect.bottom + 80)
            self.screen.blit(self.logo, logo_rect)

        # 3. Botones
        mouse_pos = pygame.mouse.get_pos()

        for button, rect in self.button_rects:
            hovered = rect.collidepoint(mouse_pos)
            
            bg_color = (0, 0, 0, 180) if not hovered else (40, 40, 60, 200)
            border_color = self.COLOR_NEON_BLUE if not hovered else self.COLOR_NEON_PINK
            
            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surf, bg_color, btn_surf.get_rect(), border_radius=4)
            pygame.draw.rect(btn_surf, border_color, btn_surf.get_rect(), 2, border_radius=4)
            self.screen.blit(btn_surf, rect)

            label = next(
                (b.label for b in self.menu_cfg.buttons if b.action == button),
                button,
            ).upper()

            text_color = self.COLOR_TEXT_WHITE if not hovered else self.COLOR_NEON_BLUE
            label_surf = self.button_font.render(label, True, text_color)
            label_rect = label_surf.get_rect(center=rect.center)
            self.screen.blit(label_surf, label_rect)

        self._draw_seed_input()
        self._draw_volume_slider()

    def _draw_seed_input(self) -> None:
        border_color = self.COLOR_NEON_PINK if self.input_active else (80, 80, 80)
        
        pygame.draw.rect(self.screen, (10, 10, 15), self.seed_rect, border_radius=2)
        pygame.draw.rect(self.screen, border_color, self.seed_rect, 2, border_radius=2)

        seed_display = self.seed_text or "SEED (VACIO = RANDOM)"
        text_color = self.COLOR_NEON_BLUE if self.seed_text else (100, 100, 100)
        
        text_surf = self.small_font.render(seed_display, True, text_color)
        text_rect = text_surf.get_rect(midleft=(self.seed_rect.left + 12, self.seed_rect.centery))
        self.screen.blit(text_surf, text_rect)

        hint_lines = [
            "ENTER para Jugar",
        ]
        for i, line in enumerate(hint_lines):
            hint_surf = self.small_font.render(line, True, (150, 150, 150))
            hint_rect = hint_surf.get_rect(
                center=(self.screen.get_width() // 2, self.seed_rect.bottom + 20 + i * 20)
            )
            self.screen.blit(hint_surf, hint_rect)

    def _statistics_lines(self) -> tuple[str, ...]:
        if self.stats_manager is None:
            return ("ESTADISTICAS", "", "No disponibles :: ERROR 404")
        return self.stats_manager.summary_lines()

    def _draw_volume_slider(self) -> None:
        label_surf = self.small_font.render("VOLUMEN", True, self.COLOR_TEXT_WHITE)
        label_rect = label_surf.get_rect(
            center=(self.volume_bar_rect.centerx, self.volume_bar_rect.top - 16)
        )
        self.screen.blit(label_surf, label_rect)

        track_rect = self.volume_bar_rect
        pygame.draw.rect(self.screen, (30, 30, 50), track_rect, border_radius=4)
        fill_width = int(track_rect.width * max(0.0, min(1.0, self.volume)))
        if fill_width > 0:
            fill_rect = pygame.Rect(track_rect.left, track_rect.top, fill_width, track_rect.height)
            pygame.draw.rect(self.screen, self.COLOR_NEON_BLUE, fill_rect, border_radius=4)

        handle_rect = self.volume_handle_rect
        handle_surface = pygame.Surface(handle_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            handle_surface,
            self.COLOR_NEON_PINK if self.dragging_volume else self.COLOR_NEON_BLUE,
            handle_surface.get_rect(),
            border_radius=6,
        )
        pygame.draw.rect(handle_surface, (0, 0, 0), handle_surface.get_rect(), 2, border_radius=6)
        self.screen.blit(handle_surface, handle_rect)

        percent = int(self.volume * 100)
        percent_surf = self.small_font.render(f"{percent}%", True, (180, 180, 180))
        percent_rect = percent_surf.get_rect(
            center=(self.volume_bar_rect.centerx, self.volume_bar_rect.bottom + 16)
        )
        self.screen.blit(percent_surf, percent_rect)

    def _is_over_volume(self, pos: tuple[int, int]) -> bool:
        expanded = self.volume_bar_rect.inflate(0, 16)
        expanded.union_ip(self.volume_handle_rect)
        return expanded.collidepoint(pos)

    def _set_volume_from_mouse(self, mouse_x: int) -> None:
        relative = (mouse_x - self.volume_bar_rect.left) / self.volume_bar_rect.width
        self.volume = max(0.0, min(1.0, relative))
        self._update_volume_handle_pos()
        self._apply_volume()

    def _apply_volume(self) -> None:
        if not pygame.mixer.get_init():
            return
        pygame.mixer.music.set_volume(self.volume)
        if self.click_sound:
            self.click_sound.set_volume(self.volume)
        channel_count = pygame.mixer.get_num_channels()
        for channel_index in range(channel_count):
            pygame.mixer.Channel(channel_index).set_volume(self.volume)

    def _draw_skins_overlay(self) -> None:
        width, height = self.screen.get_size()
        overlay_rect = pygame.Rect(0, 0, int(width * 0.85), int(height * 0.85))
        overlay_rect.center = (width // 2, height // 2)
        self.skins_overlay_rect = overlay_rect

        pygame.draw.rect(self.screen, (10, 10, 20), overlay_rect)
        pygame.draw.rect(self.screen, self.COLOR_NEON_BLUE, overlay_rect, 2)

        title_surf = self.button_font.render("SELECCIONA TU SKIN", True, self.COLOR_TEXT_WHITE)
        title_rect = title_surf.get_rect(center=(width // 2, overlay_rect.top + 50))
        self.screen.blit(title_surf, title_rect)

        columns = 2
        card_width = overlay_rect.width // columns - 60
        card_height = 140
        start_x = overlay_rect.left + 40
        start_y = overlay_rect.top + 110

        self.skin_rects = []
        mouse_pos = pygame.mouse.get_pos()
        for idx, option in enumerate(self.skin_options):
            col = idx % columns
            row = idx // columns
            x = start_x + col * (card_width + 30)
            y = start_y + row * (card_height + 24)
            rect = pygame.Rect(x, y, card_width, card_height)
            self.skin_rects.append((option["id"], rect))

            hovered = rect.collidepoint(mouse_pos)
            selected = option["id"] == self.selected_skin_id
            base_color = pygame.Color(20, 20, 30)
            if selected:
                base_color = pygame.Color(40, 20, 50)
            if hovered:
                base_color += pygame.Color(15, 15, 15)

            border_color = self.COLOR_NEON_PINK if selected else self.COLOR_NEON_BLUE

            pygame.draw.rect(self.screen, base_color, rect, border_radius=8)
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=8)

            label_surf = self.button_font.render(option["label"].upper(), True, self.COLOR_TEXT_WHITE)
            label_rect = label_surf.get_rect(center=(rect.centerx, rect.top + 36))
            self.screen.blit(label_surf, label_rect)

            body_surf = self.small_font.render(f"Tipo: {option['body']}", True, (180, 180, 200))
            body_rect = body_surf.get_rect(midleft=(rect.left + 18, rect.centery - 6))
            self.screen.blit(body_surf, body_rect)

            color_surf = self.small_font.render(f"Color: {option['color']}", True, (180, 180, 200))
            color_rect = color_surf.get_rect(midleft=(rect.left + 18, rect.centery + 20))
            self.screen.blit(color_surf, color_rect)

        hint_text = "Click para elegir / ESC para volver"
        hint_surf = self.small_font.render(hint_text.upper(), True, self.COLOR_NEON_PINK)
        hint_rect = hint_surf.get_rect(center=(width // 2, overlay_rect.bottom - 40))
        self.screen.blit(hint_surf, hint_rect)

    def _draw_overlay(self) -> None:
        width, height = self.screen.get_size()
        
        overlay_rect = pygame.Rect(0, 0, width * 0.8, height * 0.8)
        overlay_rect.center = (width // 2, height // 2)
        
        pygame.draw.rect(self.screen, (10, 10, 20), overlay_rect)
        pygame.draw.rect(self.screen, self.COLOR_NEON_BLUE, overlay_rect, 2)

        lines = self.overlay_lines or ("",)
        start_y = overlay_rect.top + 60
        
        for i, line in enumerate(lines):
            surf = self.button_font.render(line, True, self.COLOR_TEXT_WHITE)
            rect = surf.get_rect(center=(width // 2, start_y + i * 40))
            self.screen.blit(surf, rect)

        exit_hint = self.small_font.render(
            "[ CLICK / ESC ] PARA VOLVER", True, self.COLOR_NEON_PINK
        )
        hint_rect = exit_hint.get_rect(center=(width // 2, overlay_rect.bottom - 40))
        self.screen.blit(exit_hint, hint_rect)