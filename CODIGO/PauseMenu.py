from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, Optional

import pygame


@dataclass(frozen=True)
class PauseMenuButton:
    """Representa un botón de acción dentro del menú de pausa."""

    label: str
    action: str


class PauseMenu:
    """Menú simple mostrado durante la partida para acciones rápidas (Estilo CyberQuest)."""

    BUTTON_PADDING_X = 36
    BUTTON_PADDING_Y = 18
    BUTTON_GAP = 16
    
    # Colores Cyberpunk
    COLOR_NEON_BLUE = (0, 255, 255)
    COLOR_NEON_PINK = (255, 0, 128)
    COLOR_TEXT_WHITE = (240, 240, 255)

    def __init__(
        self,
        screen: pygame.Surface,
        *,
        buttons: Sequence[PauseMenuButton] | None = None,
        title: str = "PAUSA",
        font: pygame.font.Font | None = None,
    ) -> None:
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.title = title
        self.buttons: list[PauseMenuButton] = list(buttons) if buttons else [
            PauseMenuButton("Reanudar", "resume"),
            PauseMenuButton("Menú Principal", "main_menu"),
            PauseMenuButton("Salir del Juego", "quit"),
        ]

        # --- Inicializar Audio ---
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error:
                pass
        
        # Cargar sonido (busca en assets/audio)
        self.click_sound = self._load_sound("boton.mp3")

        # --- Carga de Fuentes (Estilo Retro) ---
        self.title_font = self._get_font("VT323-Regular.ttf", 96)
        self.button_font = font or self._get_font("VT323-Regular.ttf", 48)
        self.small_font = self._get_font("VT323-Regular.ttf", 32)

        self._button_layout: list[tuple[PauseMenuButton, pygame.Rect]] = []
        self._compute_layout()

    # ------------------------------------------------------------------
    # Helpers & Path Finding
    # ------------------------------------------------------------------
    def _resolve_path(self, filename: str) -> Path | None:
        """Busca el archivo en assets/ui basándose en la ubicación del script."""
        script_dir = Path(__file__).parent.resolve()
        candidates = [
            script_dir / "assets" / "ui" / filename,
            script_dir / ".." / "assets" / "ui" / filename,
            Path.cwd() / "assets" / "ui" / filename,
            script_dir / filename 
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _load_sound(self, filename: str) -> pygame.mixer.Sound | None:
        """Busca y carga sonidos en assets/audio."""
        script_dir = Path(__file__).parent.resolve()
        # Rutas posibles para el audio
        candidates = [
            script_dir / "assets" / "audio" / filename,
            script_dir / ".." / "assets" / "audio" / filename,
            Path.cwd() / "assets" / "audio" / filename,
        ]
        
        for path in candidates:
            if path.exists():
                try:
                    return pygame.mixer.Sound(str(path))
                except pygame.error:
                    print(f"Error al cargar sonido: {filename}")
                    return None
        
        # print(f"Advertencia: Sonido '{filename}' no encontrado en assets/audio")
        return None

    def _get_font(self, font_name: str, size: int) -> pygame.font.Font:
        """Carga la fuente personalizada o usa sistema si falla."""
        font_path = self._resolve_path(font_name)
        if font_path:
            try:
                return pygame.font.Font(str(font_path), size)
            except pygame.error:
                pass
        return pygame.font.SysFont("consolas", int(size * 0.7))

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def set_buttons(self, buttons: Iterable[PauseMenuButton]) -> None:
        """Reemplaza la lista de botones mostrados en el menú."""
        self.buttons = list(buttons)
        self._compute_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _compute_layout(self) -> None:
        width, height = self.screen.get_size()
        center_x = width // 2

        self._button_layout.clear()
        if not self.buttons:
            return

        max_label_width = max(self.button_font.size(button.label.upper())[0] for button in self.buttons)
        button_width = max(max_label_width + self.BUTTON_PADDING_X * 2, 280)
        button_height = self.button_font.get_height() + self.BUTTON_PADDING_Y * 2

        total_height = len(self.buttons) * button_height
        total_height += max(0, len(self.buttons) - 1) * self.BUTTON_GAP

        start_y = height // 2 - total_height // 2
        for button in self.buttons:
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.centerx = center_x
            rect.y = start_y
            self._button_layout.append((button, rect))
            start_y += button_height + self.BUTTON_GAP

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self, *, background: pygame.Surface | None = None) -> str:
        """Muestra el menú hasta que se seleccione una acción."""
        while True:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    # Reproducir sonido al reanudar con ESC
                    if self.click_sound:
                        self.click_sound.play()
                    return "resume"
                
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button, rect in self._button_layout:
                        if rect.collidepoint(event.pos):
                            # Reproducir sonido al hacer clic
                            if self.click_sound:
                                self.click_sound.play()
                            return button.action

            self._draw(background)
            pygame.display.flip()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _draw(self, background: pygame.Surface | None) -> None:
        width, height = self.screen.get_size()
        
        # 1. Fondo (Juego congelado de fondo)
        if background is not None:
            scaled_background = pygame.transform.smoothscale(background, (width, height))
            self.screen.blit(scaled_background, (0, 0))
        else:
            self.screen.fill((10, 10, 20))

        # 2. Overlay oscuro (Dimmer)
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # 3. Título con efecto de sombra (Estilo CyberQuest)
        # Sombra (Pink)
        shadow_surf = self.title_font.render(self.title, True, self.COLOR_NEON_PINK)
        shadow_rect = shadow_surf.get_rect(center=(width // 2 + 4, height // 4 + 4))
        self.screen.blit(shadow_surf, shadow_rect)
        
        # Principal (Blue)
        title_surf = self.title_font.render(self.title, True, self.COLOR_NEON_BLUE)
        title_rect = title_surf.get_rect(center=(width // 2, height // 4))
        self.screen.blit(title_surf, title_rect)

        # 4. Botones
        mouse_pos = pygame.mouse.get_pos()
        for button, rect in self._button_layout:
            hovered = rect.collidepoint(mouse_pos)
            
            # Fondo botón
            bg_color = (0, 0, 0, 180) if not hovered else (40, 40, 60, 200)
            border_color = self.COLOR_NEON_BLUE if not hovered else self.COLOR_NEON_PINK
            
            # Dibujar superficie con alpha para el fondo del botón
            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surf, bg_color, btn_surf.get_rect(), border_radius=4)
            pygame.draw.rect(btn_surf, border_color, btn_surf.get_rect(), 2, border_radius=4)
            self.screen.blit(btn_surf, rect)

            # Texto botón
            text_color = self.COLOR_TEXT_WHITE if not hovered else self.COLOR_NEON_BLUE
            label_surf = self.button_font.render(button.label.upper(), True, text_color)
            label_rect = label_surf.get_rect(center=rect.center)
            self.screen.blit(label_surf, label_rect)

        # 5. Hint
        hint_text = self.small_font.render("[ ESC PARA REANUDAR ]", True, (150, 150, 150))
        hint_rect = hint_text.get_rect(center=(width // 2, title_rect.bottom + 30))
        self.screen.blit(hint_text, hint_rect)