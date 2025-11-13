from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pygame


@dataclass(frozen=True)
class GameOverButton:
    """Representa un botón dentro de la pantalla de Game Over."""

    label: str
    action: str


class GameOverScreen:
    """Pantalla mostrada al agotar todas las vidas del jugador."""

    BUTTON_PADDING_X = 40
    BUTTON_PADDING_Y = 18
    BUTTON_GAP = 16
    STATS_GAP = 8

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
                GameOverButton("Reintentar (nueva seed)", "new_seed"),
                GameOverButton("Menú principal", "main_menu"),
            ]
        )

        self.title_font = pygame.font.SysFont(None, 80)
        self.stats_font = pygame.font.SysFont(None, 32)
        self.button_font = pygame.font.SysFont(None, 40)
        self.hint_font = pygame.font.SysFont(None, 24)

        self._title_surface: pygame.Surface | None = None
        self._title_rect: pygame.Rect | None = None
        self._stats_surfaces: list[tuple[pygame.Surface, pygame.Rect]] = []
        self._button_rects: list[tuple[GameOverButton, pygame.Rect]] = []
        self._hint_surface: pygame.Surface | None = None
        self._hint_rect: pygame.Rect | None = None

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------
    def _prepare_layout(self, stats_lines: Sequence[str]) -> None:
        width, height = self.screen.get_size()
        self._title_surface = self.title_font.render("Game Over", True, (255, 255, 255))
        self._title_rect = self._title_surface.get_rect(
            center=(width // 2, int(height * 0.25))
        )

        self._stats_surfaces.clear()
        y = (self._title_rect.bottom if self._title_rect else int(height * 0.35)) + 24
        for line in stats_lines:
            surface = self.stats_font.render(line, True, (230, 230, 230))
            rect = surface.get_rect(center=(width // 2, y))
            self._stats_surfaces.append((surface, rect))
            y += surface.get_height() + self.STATS_GAP

        button_width = self._compute_button_width()
        button_height = self.button_font.get_height() + self.BUTTON_PADDING_Y * 2

        start_y = y + 36
        self._button_rects.clear()
        for button in self.buttons:
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.centerx = width // 2
            rect.y = start_y
            self._button_rects.append((button, rect))
            start_y += button_height + self.BUTTON_GAP

        hint_text = "ESC: Menú  |  ENTER: Reintentar"
        self._hint_surface = self.hint_font.render(hint_text, True, (210, 210, 210))
        self._hint_rect = self._hint_surface.get_rect(center=(width // 2, start_y + 20))

    def _compute_button_width(self) -> int:
        if not self.buttons:
            return 260
        max_label_width = max(self.button_font.size(button.label)[0] for button in self.buttons)
        return max(max_label_width + self.BUTTON_PADDING_X * 2, 280)

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
        if background is not None:
            scaled_background = pygame.transform.smoothscale(background, (width, height))
            self.screen.blit(scaled_background, (0, 0))
        else:
            self.screen.fill((0, 0, 0))

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        if self._title_surface and self._title_rect:
            self.screen.blit(self._title_surface, self._title_rect)

        mouse_pos = pygame.mouse.get_pos()

        for surface, rect in self._stats_surfaces:
            self.screen.blit(surface, rect)

        for button, rect in self._button_rects:
            hovered = rect.collidepoint(mouse_pos)
            fill_color = (180, 70, 70) if hovered else (140, 40, 40)
            border_color = (255, 210, 210)
            pygame.draw.rect(self.screen, fill_color, rect, border_radius=10)
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=10)

            label_surface = self.button_font.render(button.label, True, (255, 255, 255))
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
            f"Monedas conseguidas: {coins}",
            f"Enemigos derrotados: {kills}",
            f"Salas visitadas: {rooms}",
        )
