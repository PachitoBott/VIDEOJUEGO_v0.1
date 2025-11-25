from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from Config import Config

moviepy_spec = importlib.util.find_spec("moviepy.editor")
if moviepy_spec:
    from moviepy.editor import VideoFileClip
else:  # pragma: no cover - entorno sin moviepy
    VideoFileClip = None

# Nota: Esta es la única implementación activa de la cinemática.
# Se eliminaron versiones previas (Cinematic, Cinematica) para evitar duplicados.
__all__ = ["Cinamatic"]


class Cinamatic:
    """Reproduce una breve cinemática con efecto de máquina de escribir."""

    TYPEWRITER_SPEED = 42  # caracteres por segundo
    SLIDE_PAUSE = 2.0      # segundos que permanece el slide tras terminar de escribirse
    SKIP_HOLD_TIME = 3.0

    BG_COLOR = (4, 6, 18)
    PANEL_COLOR = (12, 14, 30)
    PANEL_BORDER = (255, 0, 64)
    TEXT_COLOR = (232, 232, 248)
    ACCENT_COLOR = (255, 73, 100)

    def __init__(self, screen: pygame.Surface, cfg: Config) -> None:
        self.screen = screen
        self.cfg = cfg
        self.clock = pygame.time.Clock()
        base_dir = Path(__file__).resolve().parent
        self.ui_dir = base_dir / "assets" / "ui"
        self.cinematics_dir = base_dir / "assets" / "cinenatics"

        self.title_font = self._load_font("VT323-Regular.ttf", 64)
        self.body_font = self._load_font("VT323-Regular.ttf", 28)
        self.small_font = self._load_font("VT323-Regular.ttf", 22)

        self.slides: List[str] = [
            (
                "Our defenses were flawless. "
                "For decades, the system had repelled every intrusion, every probe, every unauthorized signal. "
                "But all it took was one vulnerability. "
                "A single unpatched weakness. "
                "A forgotten line of code."
            ),
            (
                "The Zero-Day exploit spread faster than our protocols could respond. "
                "Firewalls collapsed. "
                "Gateways went dark. "
                "Malware swarmed every access point like a digital plague."
            ),
            (
                "Entire sectors fell in minutes. "
                "Surveillance nodes went blind. "
                "Antivirus modules were overrun. "
                "And at the center of it all… the MotherBoard woke up."
            ),
            (
                "This is why cybersecurity is everything. "
                "A world built on data can fall in seconds."
            ),
        ]

        self.video_sequence: List[Tuple[str, Optional[str]]] = [
            (
                "orden1.mp4",
                (
                    "For years, the system remained perfectly stable. "
                    "Every protocol, every barrier… functioning flawlessly. "
                    "Until a silent vulnerability opened the door. "
                    "A Zero-Day slipped through the circuits unnoticed."
                ),
            ),
            ("orden2.mp4", None),
            ("orden3.mp4", None),
            (
                "orden4.mp4",
                (
                    "Nodes began failing one after another. "
                    "The infection spread faster than containment could respond."
                ),
            ),
            (
                "orden5.mp4",
                (
                    "Only one core remained untouched. "
                    "The Immersion Protocol activated automatically."
                ),
            ),
            (
                "orden6.mp4",
                "Agent CYBER-EA9: deployed. Last safeguard. Last firewall.",
            ),
            ("orden7.mp4", None),
        ]

    def run(self) -> bool:
        slide_index = 0
        char_progress = 0.0
        finished_time = 0.0
        hold_timer = 0.0
        history: list[str] = []

        while slide_index < len(self.slides):
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False

            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                hold_timer += dt
            else:
                hold_timer = 0.0

            if hold_timer >= self.SKIP_HOLD_TIME:
                return True

            current = self.slides[slide_index]
            if char_progress < len(current):
                char_progress += self.TYPEWRITER_SPEED * dt
                finished_time = 0.0
            else:
                finished_time += dt
                if finished_time >= self.SLIDE_PAUSE:
                    if slide_index < len(self.slides) - 1:
                        history.append(current)
                        slide_index += 1
                        char_progress = 0.0
                        finished_time = 0.0
                        continue
                    else:
                        # Último slide: muestra el texto completo acumulado y sale.
                        self._draw_slide(history, current, slide_index, hold_timer)
                        pygame.display.flip()
                        return self._play_video_sequence()

            visible_text = current[: int(char_progress)]
            self._draw_slide(history, visible_text, slide_index, hold_timer)
            pygame.display.flip()

        return self._play_video_sequence()

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        words = text.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            tentative = f"{current} {word}".strip()
            if self.body_font.size(tentative)[0] <= max_width:
                current = tentative
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _draw_slide(self, history: list[str], text: str, slide_index: int, hold_timer: float) -> None:
        self.screen.fill(self.BG_COLOR)
        width, height = self.screen.get_size()

        panel_rect = pygame.Rect(0, 0, int(width * 0.85), int(height * 0.7))
        panel_rect.center = (width // 2, int(height * 0.48))

        pygame.draw.rect(self.screen, self.PANEL_BORDER, panel_rect, border_radius=8)
        inner_rect = panel_rect.inflate(-8, -8)
        pygame.draw.rect(self.screen, self.PANEL_COLOR, inner_rect, border_radius=6)

        title = self.title_font.render("// SYSTEM BREACH", True, self.ACCENT_COLOR)
        self.screen.blit(title, (inner_rect.left + 24, inner_rect.top + 18))

        paragraphs = history + [text]
        y = inner_rect.top + 90
        for paragraph in paragraphs:
            wrapped = self._wrap_text(paragraph, inner_rect.width - 48)
            for line in wrapped:
                rendered = self.body_font.render(line, True, self.TEXT_COLOR)
                self.screen.blit(rendered, (inner_rect.left + 24, y))
                y += rendered.get_height() + 10
            y += 12

        dots = " ".join("●" if i == slide_index else "○" for i in range(len(self.slides)))
        dots_surface = self.small_font.render(dots, True, self.ACCENT_COLOR)
        self.screen.blit(dots_surface, (inner_rect.left + 24, inner_rect.bottom - 48))

        self._draw_skip_hint(hold_timer)

    def _draw_skip_hint(self, hold_timer: float) -> None:
        metrics = self._skip_hint_metrics()
        hint_rect = metrics["hint_rect"]

        pygame.draw.rect(self.screen, (10, 12, 26), hint_rect, border_radius=14)
        pygame.draw.rect(self.screen, self.ACCENT_COLOR, hint_rect, width=2, border_radius=14)

        self.screen.blit(metrics["label"], (metrics["x"] + metrics["key_radius"] * 2 + 18, metrics["text_y"]))

        center = metrics["center"]
        pygame.draw.circle(self.screen, (45, 48, 70), center, metrics["key_radius"])
        pygame.draw.circle(self.screen, self.TEXT_COLOR, center, metrics["key_radius"], 2)

        ratio = max(0.0, min(hold_timer / self.SKIP_HOLD_TIME, 1.0))
        bg_rect = pygame.Rect(
            center[0] - metrics["key_radius"] - 4,
            center[1] - metrics["key_radius"] - 4,
            (metrics["key_radius"] + 4) * 2,
            (metrics["key_radius"] + 4) * 2,
        )
        pygame.draw.arc(
            self.screen,
            (70, 72, 96),
            bg_rect,
            -math.pi / 2,
            3 * math.pi / 2,
            6,
        )
        if ratio > 0:
            start_angle = -math.pi / 2
            end_angle = start_angle + ratio * 2 * math.pi
            pygame.draw.arc(
                self.screen,
                self.ACCENT_COLOR,
                bg_rect,
                start_angle,
                end_angle,
                6,
            )

        key_label = self.small_font.render("SPACE", True, self.TEXT_COLOR)
        key_rect = key_label.get_rect(center=center)
        self.screen.blit(key_label, key_rect)

    def _load_font(self, name: str, size: int) -> pygame.font.Font:
        path = self.ui_dir / name
        if path.exists():
            try:
                return pygame.font.Font(str(path), size)
            except Exception:
                pass
        return pygame.font.SysFont("consolas", int(size * 0.75))

    def _skip_hint_metrics(self) -> Dict[str, object]:
        width, height = self.screen.get_size()
        padding = 24
        key_radius = 28

        text = "Mantén ESPACIO 3 segundos para omitir"
        label = self.small_font.render(text, True, self.TEXT_COLOR)

        hint_height = max(label.get_height(), key_radius * 2) + 20
        hint_width = key_radius * 2 + 24 + label.get_width()
        x = width - padding - hint_width
        y = height - 190 - hint_height
        hint_rect = pygame.Rect(x - 8, y - 6, hint_width + 16, hint_height + 12)

        text_y = y + (hint_height - label.get_height()) // 2
        center = (x + key_radius, y + hint_height // 2)

        return {
            "label": label,
            "hint_rect": hint_rect,
            "x": x,
            "y": y,
            "key_radius": key_radius,
            "text_y": text_y,
            "center": center,
        }

    def _play_video_sequence(self) -> bool:
        if VideoFileClip is None:
            return True

        hold_timer = 0.0

        for filename, overlay_text in self.video_sequence:
            path = self.cinematics_dir / filename
            if not path.exists():
                continue

            try:
                clip = VideoFileClip(str(path))
            except Exception:
                continue

            overlay_progress = 0.0

            frame_iter = clip.iter_frames(fps=self.cfg.FPS, dtype="uint8")
            for frame in frame_iter:
                dt = self.clock.tick(self.cfg.FPS) / 1000.0
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        clip.close()
                        return False

                keys = pygame.key.get_pressed()
                if keys[pygame.K_SPACE]:
                    hold_timer += dt
                else:
                    hold_timer = 0.0

                if hold_timer >= self.SKIP_HOLD_TIME:
                    clip.close()
                    return True

                frame_surface = self._frame_to_surface(frame)
                self._draw_video_frame(frame_surface)

                metrics = self._skip_hint_metrics()
                if overlay_text:
                    overlay_progress = min(
                        len(overlay_text), overlay_progress + self.TYPEWRITER_SPEED * dt
                    )
                    visible_overlay = overlay_text[: int(overlay_progress)]
                    self._draw_overlay_bubble(visible_overlay, metrics["y"])

                self._draw_skip_hint(hold_timer)
                pygame.display.flip()

            clip.close()

        return True

    def _frame_to_surface(self, frame) -> pygame.Surface:
        height, width = frame.shape[:2]
        surface = pygame.image.frombuffer(frame.tobytes(), (width, height), "RGB")
        return surface.convert()

    def _draw_video_frame(self, frame: pygame.Surface) -> None:
        width, height = self.screen.get_size()
        frame_w, frame_h = frame.get_size()

        scale = min(width / frame_w, height / frame_h)
        new_size = (int(frame_w * scale), int(frame_h * scale))
        scaled = pygame.transform.smoothscale(frame, new_size)
        rect = scaled.get_rect(center=(width // 2, height // 2))

        self.screen.fill(self.BG_COLOR)
        self.screen.blit(scaled, rect)

    def _draw_overlay_bubble(self, text: str, baseline_y: int) -> None:
        if not text:
            return

        width, height = self.screen.get_size()
        bubble_width = min(int(width * 0.42), width - 120)
        bubble_x = 42
        bubble_y = baseline_y

        paragraphs: list[str] = []
        for raw_paragraph in text.split("\n"):
            paragraphs.extend(self._wrap_text(raw_paragraph.strip(), bubble_width - 32))

        text_height = sum(self.body_font.render(line, True, self.TEXT_COLOR).get_height() + 8 for line in paragraphs)
        bubble_height = text_height + 28
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)

        pygame.draw.rect(self.screen, (12, 14, 30), bubble_rect, border_radius=10)
        pygame.draw.rect(self.screen, self.ACCENT_COLOR, bubble_rect, width=2, border_radius=10)

        y = bubble_rect.top + 14
        for line in paragraphs:
            rendered = self.body_font.render(line, True, self.TEXT_COLOR)
            self.screen.blit(rendered, (bubble_rect.left + 16, y))
            y += rendered.get_height() + 8
