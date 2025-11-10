from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import pygame


@dataclass(frozen=True)
class PauseMenuButton:
    """Representa un botón de acción dentro del menú de pausa."""

    label: str
    action: str


class PauseMenu:
    """Menú simple mostrado durante la partida para acciones rápidas."""

    BUTTON_PADDING_X = 36
    BUTTON_PADDING_Y = 18
    BUTTON_GAP = 14

    def __init__(
        self,
        screen: pygame.Surface,
        *,
        buttons: Sequence[PauseMenuButton] | None = None,
        title: str = "Pausa",
        font: pygame.font.Font | None = None,
    ) -> None:
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.title = title
        self.buttons: list[PauseMenuButton] = list(buttons) if buttons else [
            PauseMenuButton("Reanudar", "resume"),
            PauseMenuButton("Menú principal", "main_menu"),
            PauseMenuButton("Salir del juego", "quit"),
        ]

        self.title_font = pygame.font.SysFont(None, 64)
        self.button_font = font or pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 24)

        self._button_layout: list[tuple[PauseMenuButton, pygame.Rect]] = []
        self._compute_layout()

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

        max_label_width = max(self.button_font.size(button.label)[0] for button in self.buttons)
        button_width = max(max_label_width + self.BUTTON_PADDING_X * 2, 240)
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
        """Muestra el menú hasta que se seleccione una acción.

        Devuelve la acción asociada al botón pulsado.
        """

        while True:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return "resume"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button, rect in self._button_layout:
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
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title_surf = self.title_font.render(self.title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(width // 2, height // 3))
        self.screen.blit(title_surf, title_rect)

        mouse_pos = pygame.mouse.get_pos()
        for button, rect in self._button_layout:
            hovered = rect.collidepoint(mouse_pos)
            color = (80, 100, 220) if hovered else (40, 60, 160)
            border_color = (240, 240, 255) if hovered else (210, 210, 210)
            pygame.draw.rect(self.screen, color, rect, border_radius=10)
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=10)

            label_surf = self.button_font.render(button.label, True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=rect.center)
            self.screen.blit(label_surf, label_rect)

        hint_text = self.small_font.render("Pulsa ESC para reanudar", True, (220, 220, 220))
        hint_rect = hint_text.get_rect(center=(width // 2, title_rect.bottom + 40))
        self.screen.blit(hint_text, hint_rect)
