from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pygame

from Config import Config


@dataclass(frozen=True)
class StartMenuResult:
    """Resultado devuelto por el menú de inicio."""

    start_game: bool
    seed: Optional[int]


class StartMenu:
    """Pantalla de inicio configurable antes de arrancar la partida."""

    BUTTON_PADDING_X = 32
    BUTTON_PADDING_Y = 14
    BUTTON_GAP = 12
    INPUT_WIDTH = 320
    INPUT_HEIGHT = 48

    def __init__(self, screen: pygame.Surface, cfg: Config) -> None:
        self.screen = screen
        self.cfg = cfg
        self.menu_cfg = cfg.START_MENU
        pygame.display.set_caption(self.menu_cfg.title)
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont(None, 72)
        self.subtitle_font = pygame.font.SysFont(None, 32)
        self.button_font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 24)

        self.seed_text: str = ""
        self.input_active = False

        self.overlay_key: Optional[str] = None
        self.overlay_lines: tuple[str, ...] = ()

        self.button_rects: list[tuple[str, pygame.Rect]] = []
        self.seed_rect = pygame.Rect(0, 0, self.INPUT_WIDTH, self.INPUT_HEIGHT)

        self.background = self._load_image(self.menu_cfg.background_image)
        self.logo = self._load_image(self.menu_cfg.logo_image)

        self._compute_layout()
        self._start_requested = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_image(self, path: Optional[str]) -> Optional[pygame.Surface]:
        if not path:
            return None
        image_path = Path(path)
        if not image_path.exists():
            return None
        try:
            image = pygame.image.load(str(image_path)).convert_alpha()
        except pygame.error:
            return None
        return image

    def _compute_layout(self) -> None:
        width, height = self.screen.get_size()
        center_x = width // 2

        # Seed input position beneath buttons; will adjust later
        self.button_rects.clear()

        if not self.menu_cfg.buttons:
            self.seed_rect.center = (center_x, height // 2)
            return

        max_label_width = max(
            self.button_font.size(button.label)[0]
            for button in self.menu_cfg.buttons
        )
        button_width = max(max_label_width + self.BUTTON_PADDING_X * 2, 240)
        button_height = self.button_font.get_height() + self.BUTTON_PADDING_Y * 2

        total_height = len(self.menu_cfg.buttons) * button_height + (
            (len(self.menu_cfg.buttons) - 1) * self.BUTTON_GAP
        )
        start_y = height // 2 - total_height // 2
        if self.menu_cfg.subtitle:
            start_y += 40

        for button in self.menu_cfg.buttons:
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.centerx = center_x
            rect.y = start_y
            self.button_rects.append((button.action, rect))
            start_y += button_height + self.BUTTON_GAP

        self.seed_rect.size = (self.INPUT_WIDTH, self.INPUT_HEIGHT)
        self.seed_rect.centerx = center_x
        self.seed_rect.y = start_y + 16

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
                self._draw_overlay()
            else:
                self._draw_menu()

            pygame.display.flip()

        if self._start_requested:
            return StartMenuResult(start_game=True, seed=self.selected_seed())
        return StartMenuResult(start_game=False, seed=None)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    def _handle_menu_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._start_requested = False
                return False
            if event.key == pygame.K_RETURN:
                return self._commit_play()
            if event.key == pygame.K_BACKSPACE:
                self.seed_text = self.seed_text[:-1]
            else:
                if event.unicode and event.unicode.isdigit():
                    if len(self.seed_text) < 16:
                        self.seed_text += event.unicode
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.seed_rect.collidepoint(event.pos):
                self.input_active = True
            else:
                self.input_active = False
                for action, rect in self.button_rects:
                    if rect.collidepoint(event.pos):
                        return self._trigger_button(action)
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

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _trigger_button(self, action: str) -> bool:
        if action == "play":
            return self._commit_play()
        if action == "credits" or action == "controls":
            if action in self.menu_cfg.sections:
                self.overlay_key = action
                self.overlay_lines = self.menu_cfg.sections[action]
                return True
        if action in self.menu_cfg.sections:
            self.overlay_key = action
            self.overlay_lines = self.menu_cfg.sections[action]
            return True
        if action == "quit":
            return False

        # Acción desconocida: mostrar mensaje temporal
        self.overlay_key = action
        self.overlay_lines = (
            f"Acción '{action}' sin comportamiento asignado.",
            "Edita Config.START_MENU para personalizarla.",
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
    def _draw_menu(self, *, dim_background: bool = False) -> None:
        width, height = self.screen.get_size()

        if self.background:
            background = pygame.transform.smoothscale(self.background, (width, height))
            self.screen.blit(background, (0, 0))
        else:
            self.screen.fill(self.cfg.COLOR_BG)

        if dim_background:
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))

        title_surf = self.title_font.render(self.menu_cfg.title, True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(width // 2, height // 4))
        self.screen.blit(title_surf, title_rect)

        if self.menu_cfg.subtitle:
            subtitle_surf = self.subtitle_font.render(
                self.menu_cfg.subtitle, True, (200, 200, 200)
            )
            subtitle_rect = subtitle_surf.get_rect(
                center=(width // 2, title_rect.bottom + 28)
            )
            self.screen.blit(subtitle_surf, subtitle_rect)

        if self.logo:
            logo_rect = self.logo.get_rect()
            logo_rect.center = (width // 2, title_rect.bottom + 80)
            self.screen.blit(self.logo, logo_rect)

        mouse_pos = pygame.mouse.get_pos()

        for button, rect in self.button_rects:
            hovered = rect.collidepoint(mouse_pos)
            color = (90, 110, 220) if hovered else (50, 70, 180)
            border_color = (255, 255, 255) if hovered else (220, 220, 220)
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=8)

            label = next(
                (b.label for b in self.menu_cfg.buttons if b.action == button),
                button,
            )
            label_surf = self.button_font.render(label, True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=rect.center)
            self.screen.blit(label_surf, label_rect)

        self._draw_seed_input()

    def _draw_seed_input(self) -> None:
        color = (255, 255, 255) if self.input_active else (220, 220, 220)
        pygame.draw.rect(self.screen, (20, 30, 60), self.seed_rect, border_radius=6)
        pygame.draw.rect(self.screen, color, self.seed_rect, 2, border_radius=6)

        seed_display = self.seed_text or self.menu_cfg.seed_placeholder
        text_color = (255, 255, 255) if self.seed_text else (180, 180, 180)
        text_surf = self.small_font.render(seed_display, True, text_color)
        text_rect = text_surf.get_rect(midleft=(self.seed_rect.left + 12, self.seed_rect.centery))
        self.screen.blit(text_surf, text_rect)

        hint_lines = [
            "Escribe números para usar una seed personalizada.",
            "Deja el campo vacío para una seed aleatoria.",
            "Pulsa Enter o haz clic en Jugar para comenzar.",
        ]
        for i, line in enumerate(hint_lines):
            hint_surf = self.small_font.render(line, True, (200, 200, 200))
            hint_rect = hint_surf.get_rect(
                center=(self.screen.get_width() // 2, self.seed_rect.bottom + 24 + i * 20)
            )
            self.screen.blit(hint_surf, hint_rect)

    def _draw_overlay(self) -> None:
        width, height = self.screen.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        lines = self.overlay_lines or ("",)
        start_y = height // 4
        for i, line in enumerate(lines):
            surf = self.button_font.render(line, True, (255, 255, 255))
            rect = surf.get_rect(center=(width // 2, start_y + i * 36))
            self.screen.blit(surf, rect)

        exit_hint = self.small_font.render(
            "Haz clic o pulsa ESC para volver.", True, (200, 200, 200)
        )
        hint_rect = exit_hint.get_rect(center=(width // 2, start_y + len(lines) * 36 + 30))
        self.screen.blit(exit_hint, hint_rect)

