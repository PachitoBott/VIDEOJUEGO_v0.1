from dataclasses import dataclass
from pathlib import Path

import pygame

from asset_paths import assets_dir


@dataclass
class FrameAnimation:
    frames: list[pygame.Surface]
    frame_time: float
    loop: bool
    index: int = 0
    timer: float = 0.0
    finished: bool = False

    def reset(self) -> None:
        self.index = 0
        self.timer = 0.0
        self.finished = False

    def update(self, dt: float) -> None:
        if self.finished or len(self.frames) <= 1:
            return
        self.timer += dt
        while self.timer >= self.frame_time:
            self.timer -= self.frame_time
            self.index += 1
            if self.index >= len(self.frames):
                if self.loop:
                    self.index = 0
                else:
                    self.index = len(self.frames) - 1
                    self.finished = True
                    break

    def current_frame(self) -> pygame.Surface:
        return self.frames[self.index]


class Shopkeeper(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()  # ← SIN argumentos (no pasamos pos aquí)

        self.interact_radius = 22  # px para permitir interacción
        self._last_tick = pygame.time.get_ticks()
        self._facing_left = False

        self._animations = self._build_animations()
        self._current_animation = "idle"

        self.image = self._animations[self._current_animation].current_frame()
        self.rect = self.image.get_rect(center=pos)

    # ------------------------------------------------------------------
    # Animaciones y orientación
    # ------------------------------------------------------------------
    def _build_animations(self) -> dict[str, FrameAnimation]:
        idle_frames = self._load_frames("idle", 5)
        talk_frames = self._load_frames("talk", 2)
        return {
            "idle": FrameAnimation(idle_frames, frame_time=0.22, loop=True),
            "talk": FrameAnimation(talk_frames, frame_time=0.16, loop=True),
        }

    def _load_frames(self, prefix: str, count: int) -> list[pygame.Surface]:
        folder = Path(assets_dir("shopkeeper"))
        frames: list[pygame.Surface] = []
        for i in range(count):
            path = folder / f"{prefix}_{i}.png"
            frame = pygame.image.load(path).convert_alpha()
            frames.append(frame)
        return frames

    def _update_animation(self, dt: float, talk_active: bool) -> None:
        target = "talk" if talk_active else "idle"
        if target != self._current_animation:
            self._animations[target].reset()
            self._current_animation = target
        self._animations[self._current_animation].update(dt)

    def _face_towards(self, player_rect) -> None:
        if callable(player_rect):
            player_rect = player_rect()
        try:
            px = player_rect.centerx
        except Exception:
            try:
                px = player_rect[0]
            except Exception:
                return
        cx = self.rect.centerx
        if abs(px - cx) < 0.5:
            return
        self._facing_left = px < cx

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def can_interact(self, player_rect):
        # acepta rect o callable que devuelve rect
        if callable(player_rect):
            player_rect = player_rect()
        if not isinstance(player_rect, pygame.Rect):
            try:
                player_rect = pygame.Rect(*player_rect)
            except Exception:
                return False

        area = self.rect.inflate(self.interact_radius*2, self.interact_radius*2)
        return area.colliderect(player_rect)

    def draw(self, surface, talk_active: bool = False, player_rect=None, cam_x: int = 0, cam_y: int = 0):
        now = pygame.time.get_ticks()
        dt = (now - self._last_tick) / 1000.0
        self._last_tick = now

        if player_rect is not None:
            self._face_towards(player_rect)
        self._update_animation(dt, talk_active)

        sprite = self._animations[self._current_animation].current_frame()
        if self._facing_left:
            sprite = pygame.transform.flip(sprite, True, False)

        center = (self.rect.centerx - cam_x, self.rect.centery - cam_y)
        self.image = sprite
        draw_rect = self.image.get_rect(center=center)
        surface.blit(self.image, draw_rect)
