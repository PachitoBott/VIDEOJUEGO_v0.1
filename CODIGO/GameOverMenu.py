"""Pantalla mostrada al finalizar una partida."""

from dataclasses import dataclass
from typing import Iterable, Sequence

import pygame


@dataclass(frozen=True)
class GameOverButton:
    label: str
    action: str


class GameOverMenu:
    """Menú simple mostrado cuando el jugador se queda sin vidas."""

    BUTTON_PADDING_X = 34
    BUTTON_PADDING_Y = 16
    BUTTON_GAP = 14

    def __init__(
        self,
        screen: pygame.Surface,
        *,
        buttons: Sequence[GameOverButton] | None = None,
        summary_lines: Iterable[str] | None = None,
        title: str = "Game Over",
    ) -> None:
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.title = title
        self.buttons: list[GameOverButton] = list(buttons) if buttons else [
            GameOverButton("Menú principal", "main_menu"),
            GameOverButton("Nueva seed", "new_seed"),
            GameOverButton("Salir del juego", "quit"),
        ]
        self.summary_lines = [line for line in summary_lines or () if line]

        self.title_font = pygame.font.SysFont(None, 72)
        self.button_font = pygame.font.SysFont(None, 34)
        self.summary_font = pygame.font.SysFont(None, 26)
        self.small_font = pygame.font.SysFont(None, 22)

        self._button_layout: list[tuple[GameOverButton, pygame.Rect]] = []
        self._compute_layout()

    def set_buttons(self, buttons: Iterable[GameOverButton]) -> None:
        self.buttons = list(buttons)
        self._compute_layout()

    def _compute_layout(self) -> None:
        width, height = self.screen.get_size()
        center_x = width // 2

        self._button_layout.clear()
        if not self.buttons:
            return

        max_label_width = max(self.button_font.size(button.label)[0] for button in self.buttons)
        button_width = max(max_label_width + self.BUTTON_PADDING_X * 2, 280)
        button_height = self.button_font.get_height() + self.BUTTON_PADDING_Y * 2

        total_height = len(self.buttons) * button_height
        total_height += max(0, len(self.buttons) - 1) * self.BUTTON_GAP

        start_y = height // 2 - total_height // 2 + 80
        for button in self.buttons:
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.centerx = center_x
            rect.y = start_y
            self._button_layout.append((button, rect))
            start_y += button_height + self.BUTTON_GAP

    def run(self, *, background: pygame.Surface | None = None) -> str:
        while True:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                        if self.buttons:
                            return self.buttons[0].action
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button, rect in self._button_layout:
                        if rect.collidepoint(event.pos):
                            return button.action

            self._draw(background)
            pygame.display.flip()

    def _draw(self, background: pygame.Surface | None) -> None:
        width, height = self.screen.get_size()
        if background is not None:
            scaled_background = pygame.transform.smoothscale(background, (width, height))
            self.screen.blit(scaled_background, (0, 0))
        else:
            self.screen.fill((0, 0, 0))

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((10, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        title_surf = self.title_font.render(self.title, True, (255, 230, 230))
        title_rect = title_surf.get_rect(center=(width // 2, height // 3))
        self.screen.blit(title_surf, title_rect)

        summary_y = title_rect.bottom + 10
        for line in self.summary_lines:
            summary_surf = self.summary_font.render(line, True, (250, 210, 210))
            summary_rect = summary_surf.get_rect(center=(width // 2, summary_y))
            self.screen.blit(summary_surf, summary_rect)
            summary_y += summary_surf.get_height() + 4

        mouse_pos = pygame.mouse.get_pos()
        for button, rect in self._button_layout:
            hovered = rect.collidepoint(mouse_pos)
            color = (150, 60, 60) if hovered else (90, 30, 30)
            border_color = (255, 220, 220) if hovered else (220, 180, 180)
            pygame.draw.rect(self.screen, color, rect, border_radius=10)
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=10)

            label_surf = self.button_font.render(button.label, True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=rect.center)
            self.screen.blit(label_surf, label_rect)

        hint_surf = self.small_font.render(
            "Haz clic en una opción para continuar", True, (230, 200, 200)
        )
        hint_rect = hint_surf.get_rect(center=(width // 2, self._button_layout[-1][1].bottom + 32))
        self.screen.blit(hint_surf, hint_rect)
