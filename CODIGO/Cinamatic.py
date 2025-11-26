from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from Config import Config

# Intentamos importar moviepy, si no está disponible, VideoFileClip será None
try:
    from moviepy.editor import VideoFileClip
except (ModuleNotFoundError, ImportError):
    VideoFileClip = None

# Nota: Esta es la única implementación activa de la cinemática.
# Se eliminaron versiones previas (Cinematic, Cinematica) para evitar duplicados.
__all__ = ["Cinamatic"]


class Cinamatic:
    """Reproduce una breve cinemática con efecto de máquina de escribir."""

    TYPEWRITER_SPEED = 42  # caracteres por segundo
    SLIDE_PAUSE = 4.0      # segundos que permanece el slide tras terminar de escribirse (extendido para permitir skip)
    SKIP_HOLD_TIME = 3.0
    TRANSITION_FADE_DURATION = 0.4  # duración de las transiciones en segundos

    BG_COLOR = (4, 6, 18)
    PANEL_COLOR = (12, 14, 30)
    PANEL_BORDER = (255, 0, 64)
    TEXT_COLOR = (232, 232, 248)
    ACCENT_COLOR = (255, 73, 100)
    TRANSITION_COLOR = (20, 5, 10)  # Dark crimson for ominous transitions

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

        self.image_sequence: List[Tuple[str, str]] = [
            (
                "img1.png",
                "This is the Network Core. Our world. Every node, every connection vital to survival."
            ),
            (
                "img2.png",
                "The infection spread fast. Red zones multiplied. Critical systems began failing."
            ),
            (
                "img3.png",
                "GENERAL PROTOCOL: 'They've breached the perimeter. All defensive layers compromised.'"
            ),
            (
                "img4.png",
                "Node by node, the network collapsed. Explosions tore through the infrastructure."
            ),
            (
                "img5.png",
                "But from the chaos, a signal emerged. A beacon of hope materialized in the void."
            ),
            (
                "img6.png",
                "I was digitized. Reconstructed from pure data. The last defense against extinction."
            ),
            (
                "img7.png",
                "They're everywhere. Corrupted entities flooding the corridors. No retreat."
            ),
            (
                "img8.png",
                "The MotherBoard. The source of all malware. It's waiting for me."
            ),
            (
                "img9.png",
                "This is what I'm up against. Total digital annihilation. But I'm ready."
            ),
        ]
        
        # Control para avance con espacio
        self.space_just_pressed = False
        self.space_was_pressed = False

    def run(self) -> bool:
        slide_index = 0
        char_progress = 0.0
        finished_time = 0.0
        hold_timer = 0.0
        history: list[str] = []
        slide_finished = False

        while slide_index < len(self.slides):
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            
            # Detectar eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False

            keys = pygame.key.get_pressed()
            
            # Detectar presión única de espacio (no mantener)
            self.space_just_pressed = keys[pygame.K_SPACE] and not self.space_was_pressed
            self.space_was_pressed = keys[pygame.K_SPACE]
            
            # Timer para skip manteniendo espacio
            if keys[pygame.K_SPACE]:
                hold_timer += dt
            else:
                hold_timer = 0.0

            if hold_timer >= self.SKIP_HOLD_TIME:
                return True

            current = self.slides[slide_index]
            prev_char_progress = int(char_progress)
            
            # Si se presiona espacio y el slide no ha terminado, completarlo
            if self.space_just_pressed and not slide_finished:
                char_progress = len(current)
                slide_finished = True
                finished_time = 0.0
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
            # Si se presiona espacio y el slide ya terminó, avanzar al siguiente
            elif self.space_just_pressed and slide_finished:
                if slide_index < len(self.slides) - 1:
                    history.append(current)
                    slide_index += 1
                    char_progress = 0.0
                    finished_time = 0.0
                    slide_finished = False
                else:
                    # Último slide: ir a las imágenes
                    self._draw_slide(history, current, slide_index, hold_timer)
                    pygame.display.flip()
                    return self._play_image_slideshow()
            # Animación normal de escritura
            elif char_progress < len(current):
                char_progress += self.TYPEWRITER_SPEED * dt
                finished_time = 0.0
                
                # Reproducir sonido de escritura si hay caracteres nuevos
                new_char_progress = int(char_progress)
                if new_char_progress > prev_char_progress and self.typing_sound:
                    if not pygame.mixer.Channel(0).get_busy():
                        pygame.mixer.Channel(0).play(self.typing_sound, loops=-1)
                
                # Marcar como terminado cuando se completa
                if char_progress >= len(current):
                    slide_finished = True
                    if self.typing_sound:
                        pygame.mixer.Channel(0).stop()
            else:
                # Detener sonido cuando termine de escribir
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
                finished_time += dt
                # Auto-avance después de SLIDE_PAUSE (comportamiento original)
                if finished_time >= self.SLIDE_PAUSE:
                    if slide_index < len(self.slides) - 1:
                        history.append(current)
                        slide_index += 1
                        char_progress = 0.0
                        finished_time = 0.0
                        slide_finished = False
                        continue
                    else:
                        # Último slide: muestra el texto completo acumulado y sale.
                        self._draw_slide(history, current, slide_index, hold_timer)
                        pygame.display.flip()
                        return self._play_image_slideshow()

            visible_text = current[: int(char_progress)]
            self._draw_slide(history, visible_text, slide_index, hold_timer)
            pygame.display.flip()

        return self._play_image_slideshow()

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

    def _play_image_slideshow(self) -> bool:
        """Display slideshow of 9 images with text bubbles, typewriter effect, and dark transitions."""
        hold_timer = 0.0
        
        for img_index, (filename, story_text) in enumerate(self.image_sequence):
            path = self.cinematics_dir / filename
            if not path.exists():
                continue
            
            try:
                image = pygame.image.load(str(path)).convert()
            except Exception:
                continue
            
            # Fade in transition from dark
            self._transition_fade_in(image)
            
            # Typewriter effect for the story text
            text_progress = 0.0
            text_complete = False
            pause_timer = 0.0
            space_just_pressed = False
            space_was_pressed = False
            
            # Play typing sound at start
            if self.typing_sound:
                pygame.mixer.Channel(0).play(self.typing_sound, loops=-1)
            
            while True:
                dt = self.clock.tick(self.cfg.FPS) / 1000.0
                
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        if self.typing_sound:
                            pygame.mixer.Channel(0).stop()
                        return False
                
                keys = pygame.key.get_pressed()
                
                # Detect space press
                space_just_pressed = keys[pygame.K_SPACE] and not space_was_pressed
                space_was_pressed = keys[pygame.K_SPACE]
                
                # Skip timer
                if keys[pygame.K_SPACE]:
                    hold_timer += dt
                else:
                    hold_timer = 0.0
                
                if hold_timer >= self.SKIP_HOLD_TIME:
                    if self.typing_sound:
                        pygame.mixer.Channel(0).stop()
                    return True
                
                # Space to complete text or advance to next image
                if space_just_pressed:
                    if not text_complete:
                        # Complete the text instantly
                        text_progress = len(story_text)
                        text_complete = True
                        if self.typing_sound:
                            pygame.mixer.Channel(0).stop()
                    else:
                        # Advance to next image with fade out
                        if self.typing_sound:
                            pygame.mixer.Channel(0).stop()
                        if img_index < len(self.image_sequence) - 1:
                            self._transition_fade_out(image, story_text)
                        break
                
                # Animate typewriter effect
                if text_progress < len(story_text):
                    text_progress += self.TYPEWRITER_SPEED * dt
                    if text_progress >= len(story_text):
                        text_complete = True
                        if self.typing_sound:
                            pygame.mixer.Channel(0).stop()
                else:
                    pause_timer += dt
                    # Auto-advance after pause
                    if pause_timer >= self.SLIDE_PAUSE:
                        if self.typing_sound:
                            pygame.mixer.Channel(0).stop()
                        if img_index < len(self.image_sequence) - 1:
                            self._transition_fade_out(image, story_text)
                        break
                
                visible_text = story_text[:int(text_progress)]
                
                # Draw everything
                self._draw_image_frame(image)
                shake_offset = self._get_shake_offset()
                self._draw_overlay_bubble_with_shake(visible_text, shake_offset)
                self._draw_skip_hint(hold_timer)
                pygame.display.flip()
        
        return True
    
    def _transition_fade_in(self, image: pygame.Surface) -> None:
        """Fade in from dark crimson overlay."""
        steps = int(self.TRANSITION_FADE_DURATION * self.cfg.FPS)
        for step in range(steps):
            alpha = int(255 * (1 - step / steps))  # Start at 255, fade to 0
            
            self._draw_image_frame(image)
            
            # Draw dark overlay
            overlay = pygame.Surface(self.screen.get_size())
            overlay.fill(self.TRANSITION_COLOR)
            overlay.set_alpha(alpha)
            self.screen.blit(overlay, (0, 0))
            
            pygame.display.flip()
            self.clock.tick(self.cfg.FPS)
    
    def _transition_fade_out(self, image: pygame.Surface, text: str) -> None:
        """Fade out to dark crimson overlay."""
        steps = int(self.TRANSITION_FADE_DURATION * self.cfg.FPS)
        for step in range(steps):
            alpha = int(255 * (step / steps))  # Start at 0, fade to 255
            
            self._draw_image_frame(image)
            shake_offset = self._get_shake_offset()
            self._draw_overlay_bubble_with_shake(text, shake_offset)
            self._draw_skip_hint(0.0)
            
            # Draw dark overlay
            overlay = pygame.Surface(self.screen.get_size())
            overlay.fill(self.TRANSITION_COLOR)
            overlay.set_alpha(alpha)
            self.screen.blit(overlay, (0, 0))
            
            pygame.display.flip()
            self.clock.tick(self.cfg.FPS)
    
    def _get_shake_offset(self) -> Tuple[int, int]:
        """Generate subtle shake offset for arcade-style cinematics."""
        return (random.randint(-2, 2), random.randint(-2, 2))
    
    def _draw_image_frame(self, image: pygame.Surface) -> None:
        """Draw an image scaled to fit the screen."""
        width, height = self.screen.get_size()
        img_w, img_h = image.get_size()
        
        scale = min(width / img_w, height / img_h)
        new_size = (int(img_w * scale), int(img_h * scale))
        scaled = pygame.transform.smoothscale(image, new_size)
        rect = scaled.get_rect(center=(width // 2, height // 2))
        
        self.screen.fill(self.BG_COLOR)
        self.screen.blit(scaled, rect)
    
    def _draw_overlay_bubble_with_shake(self, text: str, shake_offset: Tuple[int, int]) -> None:
        """Draw text bubble at left side, perfectly parallel to skip button."""
        if not text:
            return
        
        width, height = self.screen.get_size()
        bubble_width = min(int(width * 0.42), width - 120)
        bubble_x = 42 + shake_offset[0]
        # Position EXACTLY parallel to skip button
        # Skip button: y = height - 190 - hint_height, where hint_height ≈ 76
        # So skip button y ≈ height - 266
        bubble_y = height - 266 + shake_offset[1]
        
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