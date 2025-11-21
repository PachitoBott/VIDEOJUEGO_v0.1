from __future__ import annotations
import pygame


class LootNotification:
    """Pequeña tarjeta de texto que se desvanece tras un tiempo."""

    def __init__(
        self,
        text: str,
        font: pygame.font.Font,
        *,
        duration: float = 2.5,
        fade_duration: float = 0.65,
        start_pos: tuple[float, float] = (0.0, 0.0),
        scale: float = 1.5,
        bg_color: pygame.Color | tuple[int, int, int, int] = (22, 28, 40, 200),
        text_color: pygame.Color | tuple[int, int, int] = (240, 240, 240),
    ) -> None:
        self.text = text
        self.font = font
        self.duration = max(0.1, float(duration))
        self.fade_duration = max(0.1, float(fade_duration))
        self.position = pygame.Vector2(start_pos)
        self.target_position = pygame.Vector2(start_pos)
        self.age = 0.0
        self.alpha = 255
        self.scale = max(0.1, float(scale))

        padding_x, padding_y = 10, 6
        text_surface = font.render(text, True, text_color)
        width = text_surface.get_width() + padding_x * 2
        height = text_surface.get_height() + padding_y * 2
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill(bg_color)
        text_rect = text_surface.get_rect(center=(width // 2, height // 2))
        surface.blit(text_surface, text_rect)

        # Borde sutil
        pygame.draw.rect(surface, (80, 120, 180, 220), surface.get_rect(), width=1, border_radius=4)

        if self.scale != 1.0:
            scaled_size = (
                max(1, int(surface.get_width() * self.scale)),
                max(1, int(surface.get_height() * self.scale)),
            )
            surface = pygame.transform.smoothscale(surface, scaled_size)

        self.surface = surface

    @property
    def height(self) -> float:
        return float(self.surface.get_height())

    def update(self, dt: float) -> None:
        self.age += dt
        if self.age >= self.duration:
            fade_progress = min(1.0, (self.age - self.duration) / self.fade_duration)
            self.alpha = int(255 * (1.0 - fade_progress))
        else:
            self.alpha = 255

        smoothness = min(1.0, dt * 10.0)
        self.position.update(
            self.position.x + (self.target_position.x - self.position.x) * smoothness,
            self.position.y + (self.target_position.y - self.position.y) * smoothness,
        )

    def draw(self, surface: pygame.Surface) -> None:
        if self.alpha <= 0:
            return
        self.surface.set_alpha(self.alpha)
        surface.blit(self.surface, self.position)

    def expired(self) -> bool:
        return self.age >= (self.duration + self.fade_duration)


class LootNotificationManager:
    """Controla la pila de notificaciones de botín."""

    def __init__(
        self,
        font: pygame.font.Font,
        *,
        anchor_margin: tuple[float, float] = (110.0, 210.0),
        line_spacing: float = 6.0,
        scale: float = 1.3,
    ) -> None:
        self.font = font
        self.anchor_margin = pygame.Vector2(anchor_margin)
        self.line_spacing = float(line_spacing)
        self.scale = max(0.1, float(scale))
        self.notifications: list[LootNotification] = []
        self._surface_size = pygame.Vector2(0.0, 0.0)

    def set_surface_size(self, size: tuple[int, int]) -> None:
        width, height = size
        self._surface_size.update(width, height)

    def push(self, message: str) -> None:
        base_x = self.anchor_margin.x
        base_y = self._surface_size.y - self.anchor_margin.y
        start_pos = (base_x, base_y + 40.0)
        note = LootNotification(message, self.font, start_pos=start_pos, scale=self.scale)
        self.notifications.append(note)
        self._update_targets()

    def clear(self) -> None:
        self.notifications.clear()

    def update(self, dt: float, surface: pygame.Surface | None = None) -> None:
        if surface is not None:
            self.set_surface_size(surface.get_size())
        for note in self.notifications:
            note.update(dt)
        self.notifications = [note for note in self.notifications if not note.expired()]
        self._update_targets()

    def draw(self, surface: pygame.Surface) -> None:
        for note in self.notifications:
            note.draw(surface)

    def _update_targets(self) -> None:
        if not self.notifications:
            return
        base_x = self.anchor_margin.x
        base_y = self._surface_size.y - self.anchor_margin.y
        for idx, note in enumerate(self.notifications):
            from_bottom = len(self.notifications) - 1 - idx
            target_y = base_y - from_bottom * (note.height + self.line_spacing)
            note.target_position.update(base_x, target_y)
