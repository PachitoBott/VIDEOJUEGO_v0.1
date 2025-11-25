from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Config import Config

__all__ = ["Cinamatic"]


class Cinamatic:
    """Reproduce una breve cinemática tipo slideshow con efecto de máquina de escribir."""

    TYPEWRITER_SPEED = 42  # caracteres por segundo
    SLIDE_PAUSE = 2.0  # segundos que permanece el slide tras terminar de escribirse
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

        # Cargar sonido de escritura
        self.typing_sound = None
        self._load_typing_sound()

        self.text_slides = self._build_text_slides()
        self.image_slides = self._build_image_slides()

        # Control para avance con espacio
        self.space_just_pressed = False
        self.space_was_pressed = False

    def _build_text_slides(self) -> List[str]:
        return [
            (
                "Night fell over the neon grid while the skyline dimmed. "
                "From the rooftops we watched the first blackout creeping in."
            ),
            (
                "Inside the command hub, monitors flooded with red warnings. "
                "Unknown packets bypassed every filter we trusted."
            ),
            (
                "Technicians rerouted power while I prepped the immersion rig. "
                "There was no other way to reach the source."
            ),
            (
                "The arcade shell opened like a shrine—old circuitry, new firmware—"
                "all pointing at a single objective: dive inside."
            ),
            (
                "Fragments of the virus floated like embers, learning and copying "
                "our own protocols as they spread."
            ),
        ]

    def _build_image_slides(self) -> List[Dict[str, object]]:
        """Genera la lista de slides con imagen y texto asociado."""

        narrative = [
            (
                "Night fell over the neon grid while the skyline dimmed. "
                "From the rooftops we watched the first blackout creeping in."
            ),
            (
                "Inside the command hub, monitors flooded with red warnings. "
                "Unknown packets bypassed every filter we trusted."
            ),
            (
                "Technicians rerouted power while I prepped the immersion rig. "
                "There was no other way to reach the source."
            ),
            (
                "The arcade shell opened like a shrine—old circuitry, new firmware—"
                "all pointing at a single objective: dive inside."
            ),
            (
                "Fragments of the virus floated like embers, learning and copying "
                "our own protocols as they spread."
            ),
            (
                "I synced my visor, tightened the gloves, and locked the harness. "
                "The machine hummed like a pulse waiting to fire."
            ),
            (
                "The gateway roared to life. Magnetic rails aligned, guiding me "
                "toward the motherboard's inner corridors."
            ),
            (
                "Light ripped apart into polygons; the system pushed back, as if "
                "it already knew I was coming."
            ),
            (
                "No turning back. Every firewall we lost will be reclaimed from the inside. "
                "I leapt into the breach."
            ),
        ]

        slides: List[Dict[str, object]] = []
        for index, text in enumerate(narrative, start=1):
            image_path = self.cinematics_dir / f"img{index}.png"
            slides.append(
                {
                    "image": self._load_image(image_path),
                    "text": text,
                    "path": image_path,
                }
            )
        return slides

    def run(self) -> bool:
        intro_status = self._run_intro_text()
        if intro_status == "quit":
            return False
        if intro_status == "skip":
            return True

        return self._run_image_slideshow()

    def _run_intro_text(self) -> str:
        slide_index = 0
        history: list[str] = []
        char_progress = 0.0
        finished_time = 0.0
        hold_timer = 0.0
        slide_finished = False

        while slide_index < len(self.text_slides):
            dt = self.clock.tick(self.cfg.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"

            keys = pygame.key.get_pressed()
            self.space_just_pressed = keys[pygame.K_SPACE] and not self.space_was_pressed
            self.space_was_pressed = keys[pygame.K_SPACE]

            if keys[pygame.K_SPACE]:
                hold_timer += dt
            else:
                hold_timer = 0.0

            if hold_timer >= self.SKIP_HOLD_TIME:
                return "skip"

            current = self.text_slides[slide_index]
            prev_char_progress = int(char_progress)

            if self.space_just_pressed and not slide_finished:
                char_progress = len(current_text)
                slide_finished = True
                finished_time = 0.0
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
            elif self.space_just_pressed and slide_finished:
                if slide_index < len(self.text_slides) - 1:
                    history.append(current)
                    slide_index += 1
                    char_progress = 0.0
                    finished_time = 0.0
                    slide_finished = False
                else:
                    self._draw_text_slide(history, current, slide_index, hold_timer)
                    pygame.display.flip()
                    return "done"
            elif char_progress < len(current):
                char_progress += self.TYPEWRITER_SPEED * dt
                finished_time = 0.0

                new_char_progress = int(char_progress)
                if new_char_progress > prev_char_progress and self.typing_sound:
                    if not pygame.mixer.Channel(0).get_busy():
                        pygame.mixer.Channel(0).play(self.typing_sound, loops=-1)

                if char_progress >= len(current):
                    slide_finished = True
                    if self.typing_sound:
                        pygame.mixer.Channel(0).stop()
            else:
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
                finished_time += dt
                if finished_time >= self.SLIDE_PAUSE:
                    if slide_index < len(self.text_slides) - 1:
                        history.append(current)
                        slide_index += 1
                        char_progress = 0.0
                        finished_time = 0.0
                        slide_finished = False
                        continue
                    else:
                        self._draw_text_slide(history, current, slide_index, hold_timer)
                        pygame.display.flip()
                        return "done"

            visible_text = current[: int(char_progress)]
            self._draw_text_slide(history, visible_text, slide_index, hold_timer)
            pygame.display.flip()

        return "done"

    def _run_image_slideshow(self) -> bool:
        slide_index = 0
        char_progress = 0.0
        finished_time = 0.0
        hold_timer = 0.0
        slide_finished = False

        while slide_index < len(self.image_slides):
            dt = self.clock.tick(self.cfg.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False

            keys = pygame.key.get_pressed()
            self.space_just_pressed = keys[pygame.K_SPACE] and not self.space_was_pressed
            self.space_was_pressed = keys[pygame.K_SPACE]

            if keys[pygame.K_SPACE]:
                hold_timer += dt
            else:
                hold_timer = 0.0

            if hold_timer >= self.SKIP_HOLD_TIME:
                return True

            current_slide = self.image_slides[slide_index]
            current_text: str = current_slide["text"]  # type: ignore[index]

            prev_char_progress = int(char_progress)

            if self.space_just_pressed and not slide_finished:
                char_progress = len(current_text)
                slide_finished = True
                finished_time = 0.0
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
            elif self.space_just_pressed and slide_finished:
                if slide_index < len(self.image_slides) - 1:
                    slide_index += 1
                    char_progress = 0.0
                    finished_time = 0.0
                    slide_finished = False
                else:
                    self._draw_image_slide(current_slide, current_text, slide_index, hold_timer)
                    pygame.display.flip()
                    return True
            elif char_progress < len(current_text):
                char_progress += self.TYPEWRITER_SPEED * dt
                finished_time = 0.0

                new_char_progress = int(char_progress)
                if new_char_progress > prev_char_progress and self.typing_sound:
                    if not pygame.mixer.Channel(0).get_busy():
                        pygame.mixer.Channel(0).play(self.typing_sound, loops=-1)

                if char_progress >= len(current_text):
                    slide_finished = True
                    if self.typing_sound:
                        pygame.mixer.Channel(0).stop()
            else:
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
                finished_time += dt
                if finished_time >= self.SLIDE_PAUSE:
                    if slide_index < len(self.image_slides) - 1:
                        slide_index += 1
                        char_progress = 0.0
                        finished_time = 0.0
                        slide_finished = False
                        continue
                    else:
                        self._draw_image_slide(current_slide, current_text, slide_index, hold_timer)
                        pygame.display.flip()
                        return True

            visible_text = current_text[: int(char_progress)]
            self._draw_image_slide(current_slide, visible_text, slide_index, hold_timer)
            pygame.display.flip()

        return True

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

    def _draw_image_slide(
        self, slide: Dict[str, object], text: str, slide_index: int, hold_timer: float
    ) -> None:
        self.screen.fill(self.BG_COLOR)
        width, height = self.screen.get_size()

        shake_image = self._shake_offset(3.0, 3.6)
        shake_bubble = self._shake_offset(2.0, 5.2)

        image_surface: pygame.Surface = slide["image"]  # type: ignore[index]
        image_rect = self._draw_image_frame(image_surface, shake_image)

        title = self.title_font.render("// SYSTEM BREACH", True, self.ACCENT_COLOR)
        title_rect = title.get_rect(midbottom=(image_rect.centerx, image_rect.top - 12))
        self.screen.blit(title, title_rect)

        metrics = self._skip_hint_metrics()
        self._draw_overlay_bubble(text, metrics["y"], shake_bubble)

        dots = " ".join("●" if i == slide_index else "○" for i in range(len(self.image_slides)))
        dots_surface = self.small_font.render(dots, True, self.ACCENT_COLOR)
        dots_rect = dots_surface.get_rect(midtop=(width // 2, metrics["y"] - 60))
        self.screen.blit(dots_surface, dots_rect)

        self._draw_skip_hint(hold_timer)

    def _draw_text_slide(
        self, history: list[str], text: str, slide_index: int, hold_timer: float
    ) -> None:
        self.screen.fill(self.BG_COLOR)
        width, height = self.screen.get_size()

        shake_image = self._shake_offset(3.0, 3.6)
        shake_bubble = self._shake_offset(2.0, 5.2)

        image_surface: pygame.Surface = slide["image"]  # type: ignore[index]
        image_rect = self._draw_image_frame(image_surface, shake_image)

        # Panel título encima de la imagen
        title = self.title_font.render("// SYSTEM BREACH", True, self.ACCENT_COLOR)
        title_rect = title.get_rect(midbottom=(image_rect.centerx, image_rect.top - 12))
        self.screen.blit(title, title_rect)

        metrics = self._skip_hint_metrics()
        self._draw_overlay_bubble(text, metrics["y"], shake_bubble)

        dots = " ".join("●" if i == slide_index else "○" for i in range(len(self.text_slides)))
        dots_surface = self.small_font.render(dots, True, self.ACCENT_COLOR)
        dots_rect = dots_surface.get_rect(midtop=(width // 2, metrics["y"] - 60))
        self.screen.blit(dots_surface, dots_rect)

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

    def _load_typing_sound(self) -> None:
        """Carga el sonido de escritura para el efecto de máquina de escribir."""
        try:
            audio_path = Path("assets/audio/typing_sfx.mp3")

            if not audio_path.exists():
                # Intentar ruta relativa desde CODIGO
                audio_path = Path(__file__).parent / "assets" / "audio" / "typing_sfx.mp3"

            if audio_path.exists():
                self.typing_sound = pygame.mixer.Sound(audio_path.as_posix())
                self.typing_sound.set_volume(0.15)  # 15% del volumen
            else:
                self.typing_sound = None
        except (pygame.error, FileNotFoundError):
            self.typing_sound = None

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

    def _load_image(self, path: Path) -> pygame.Surface:
        fallback = pygame.Surface((640, 360)).convert()
        fallback.fill((16, 18, 32))
        pygame.draw.rect(fallback, self.ACCENT_COLOR, fallback.get_rect(), 4)
        if path.exists():
            try:
                return pygame.image.load(path.as_posix()).convert_alpha()
            except pygame.error:
                return fallback
        return fallback

    def _draw_image_frame(
        self, image: pygame.Surface, shake: Tuple[float, float]
    ) -> pygame.Rect:
        width, height = self.screen.get_size()
        img_w, img_h = image.get_size()
        scale = min((width * 0.78) / img_w, (height * 0.82) / img_h)
        new_size = (int(img_w * scale), int(img_h * scale))
        scaled = pygame.transform.smoothscale(image, new_size)

        rect = scaled.get_rect(center=(int(width * 0.6) + int(shake[0]), int(height * 0.5) + int(shake[1])))

        panel_rect = rect.inflate(32, 32)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, panel_rect, border_radius=10)
        inner_rect = panel_rect.inflate(-8, -8)
        pygame.draw.rect(self.screen, self.PANEL_COLOR, inner_rect, border_radius=10)

        self.screen.blit(scaled, rect)
        return rect

    def _draw_overlay_bubble(
        self, text: str, baseline_y: int, shake: Tuple[float, float]
    ) -> None:
        if not text:
            return

        width, _ = self.screen.get_size()
        bubble_width = min(int(width * 0.42), width - 120)
        bubble_x = 42 + int(shake[0])
        bubble_y = baseline_y + int(shake[1])

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

    def _shake_offset(self, amplitude: float, speed: float) -> Tuple[float, float]:
        t = pygame.time.get_ticks() / 1000.0
        return (
            math.sin(t * speed) * amplitude,
            math.cos(t * speed * 0.85) * amplitude * 0.6,
        )
