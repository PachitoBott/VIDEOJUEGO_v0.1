from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Optional

import pygame


@dataclass(frozen=True)
class GameOverButton:
    """Representa un botón dentro de la pantalla de Game Over."""

    label: str
    action: str


class GameOverScreen:
    """Pantalla mostrada al agotar todas las vidas (Estilo CyberQuest)."""

    BUTTON_PADDING_X = 40
    BUTTON_PADDING_Y = 18
    BUTTON_GAP = 16
    STATS_GAP = 12

    # Colores Cyberpunk
    COLOR_NEON_BLUE = (0, 255, 255)
    COLOR_NEON_PINK = (255, 0, 128)
    COLOR_NEON_GREEN = (50, 255, 50) # Para estadísticas positivas
    COLOR_TEXT_WHITE = (240, 240, 255)

    def __init__(
        self,
        screen: pygame.Surface,
        *,
        buttons: Sequence[GameOverButton] | None = None,
    ) -> None:
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.buttons: list[GameOverButton] = (
            list(buttons)
            if buttons is not None
            else [
                GameOverButton("Reintentar (Nueva Seed)", "new_seed"),
                GameOverButton("Menú Principal", "main_menu"),
            ]
        )

        # --- Carga de Fuentes (Estilo Retro) ---
        self.title_font = self._get_font("VT323-Regular.ttf", 110) # Título masivo
        self.stats_font = self._get_font("VT323-Regular.ttf", 38)
        self.button_font = self._get_font("VT323-Regular.ttf", 48)
        self.hint_font = self._get_font("VT323-Regular.ttf", 28)

        self._title_surface: pygame.Surface | None = None
        self._title_rect: pygame.Rect | None = None
        self._stats_surfaces: list[tuple[pygame.Surface, pygame.Rect]] = []
        self._button_rects: list[tuple[GameOverButton, pygame.Rect]] = []
        self._hint_surface: pygame.Surface | None = None
        self._hint_rect: pygame.Rect | None = None

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
    # Layout helpers
    # ------------------------------------------------------------------
    def _prepare_layout(self, stats_lines: Sequence[str]) -> None:
        width, height = self.screen.get_size()
        
        # Título principal (Solo guardamos el rect base, el dibujo lo hacemos dinámico en _draw)
        # Usamos el título para calcular posición
        temp_surf = self.title_font.render("GAME OVER", True, (255,255,255))
        self._title_rect = temp_surf.get_rect(
            center=(width // 2, int(height * 0.20))
        )

        # Estadísticas (Estilo terminal)
        self._stats_surfaces.clear()
        y = (self._title_rect.bottom if self._title_rect else int(height * 0.30)) + 30
        
        # Cabecera de estadisticas
        header_surf = self.stats_font.render("- REPORTE DE MISION -", True, self.COLOR_NEON_PINK)
        header_rect = header_surf.get_rect(center=(width // 2, y))
        self._stats_surfaces.append((header_surf, header_rect))
        y += 40

        for line in stats_lines:
            surface = self.stats_font.render(line.upper(), True, self.COLOR_NEON_GREEN)
            rect = surface.get_rect(center=(width // 2, y))
            self._stats_surfaces.append((surface, rect))
            y += surface.get_height() + self.STATS_GAP

        button_width = self._compute_button_width()
        button_height = self.button_font.get_height() + self.BUTTON_PADDING_Y * 2

        start_y = y + 50 # Separación antes de los botones
        self._button_rects.clear()
        for button in self.buttons:
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.centerx = width // 2
            rect.y = start_y
            self._button_rects.append((button, rect))
            start_y += button_height + self.BUTTON_GAP

        hint_text = "[ ESC: MENU  |  ENTER: REINTENTAR ]"
        self._hint_surface = self.hint_font.render(hint_text, True, (150, 150, 150))
        self._hint_rect = self._hint_surface.get_rect(center=(width // 2, height - 40))

    def _compute_button_width(self) -> int:
        if not self.buttons:
            return 260
        max_label_width = max(self.button_font.size(button.label.upper())[0] for button in self.buttons)
        return max(max_label_width + self.BUTTON_PADDING_X * 2, 300)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(
        self,
        stats: dict[str, int],
        *,
        background: pygame.Surface | None = None,
    ) -> str:
        stats_lines = self._format_stats(stats)
        self._prepare_layout(stats_lines)

        while True:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "main_menu"
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return self.buttons[0].action if self.buttons else "new_seed"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button, rect in self._button_rects:
                        if rect.collidepoint(event.pos):
                            return button.action

            self._draw(background)
            pygame.display.flip()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _draw(self, background: pygame.Surface | None) -> None:
        width, height = self.screen.get_size()
        
        # 1. Fondo (Juego oscurecido)
        if background is not None:
            scaled_background = pygame.transform.smoothscale(background, (width, height))
            self.screen.blit(scaled_background, (0, 0))
            
            # Overlay rojo/oscuro para indicar muerte
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((20, 0, 10, 210)) # Tintado rojizo oscuro
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill((10, 0, 10))

        # 2. Título GAME OVER con efecto Glitch
        title_text = "GAME OVER"
        if self._title_rect:
            # Sombra roja/pink desplazada
            shadow_surf = self.title_font.render(title_text, True, self.COLOR_NEON_PINK)
            shadow_rect = shadow_surf.get_rect(center=(self._title_rect.centerx + 5, self._title_rect.centery + 5))
            self.screen.blit(shadow_surf, shadow_rect)
            
            # Texto principal Cyan
            title_surf = self.title_font.render(title_text, True, self.COLOR_NEON_BLUE)
            self.screen.blit(title_surf, self._title_rect)

        # 3. Stats
        for surface, rect in self._stats_surfaces:
            self.screen.blit(surface, rect)

        # 4. Botones Interactivos
        mouse_pos = pygame.mouse.get_pos()

        for button, rect in self._button_rects:
            hovered = rect.collidepoint(mouse_pos)
            
            # Colores dinámicos
            bg_color = (0, 0, 0, 180) if not hovered else (60, 20, 40, 200)
            border_color = self.COLOR_NEON_BLUE if not hovered else self.COLOR_NEON_PINK
            
            # Fondo botón
            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(btn_surf, bg_color, btn_surf.get_rect(), border_radius=4)
            pygame.draw.rect(btn_surf, border_color, btn_surf.get_rect(), 2, border_radius=4)
            self.screen.blit(btn_surf, rect)

            # Etiqueta
            text_color = self.COLOR_TEXT_WHITE if not hovered else self.COLOR_NEON_BLUE
            label_surface = self.button_font.render(button.label.upper(), True, text_color)
            label_rect = label_surface.get_rect(center=rect.center)
            self.screen.blit(label_surface, label_rect)

        if self._hint_surface and self._hint_rect:
            self.screen.blit(self._hint_surface, self._hint_rect)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _format_stats(self, stats: dict[str, int]) -> tuple[str, ...]:
        coins = max(0, int(stats.get("coins", 0)))
        kills = max(0, int(stats.get("kills", 0)))
        rooms = max(0, int(stats.get("rooms", 0)))
        return (
            f"Monedas:  {coins}",
            f"Enemigos: {kills}",
            f"Salas:    {rooms}",
        )
