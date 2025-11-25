from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import pygame

from Config import Config

# Nota: Esta es la única implementación activa de la cinemática.
# Se eliminaron versiones previas (Cinematic, Cinematica) para evitar duplicados.
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

        self.slides = self._build_slides()

        # Control para avance con espacio
        self.space_just_pressed = False
        self.space_was_pressed = False

    def _build_slides(self) -> List[Dict[str, object]]:
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
        ]

        self.image_sequence: List[Tuple[str, str]] = [
            (
                "img1.png",
                "La MotherBoard liberó fragmentos de datos corruptos; "
                "sus restos flotan como asteroides en un vacío digital.",
            ),
            (
                "img2.png",
                "Un enjambre de virus recorre los circuitos principales; "
                "cada chispa es una alerta roja encendida en el sistema.",
            ),
            (
                "img3.png",
                "Los defensores automáticos se reorganizan; luces de defensa "
                "parpadean intentando restaurar el control.",
            ),
            (
                "img4.png",
                "Se abre un portal de datos: nuevas rutas cifradas aparecen "
                "para alcanzar el núcleo aislado.",
            ),
            (
                "img5.png",
                "Entre el caos, un mapa del ciberespacio señala nodos aliados "
                "que aún resisten el apagón.",
            ),
            (
                "img6.png",
                "En las grietas del código crecen algoritmos ferales; cada "
                "uno acecha como un glitch a punto de expandirse.",
            ),
            (
                "img7.png",
                "CYBER-EA9 cae en un corredor luminoso; el camino vibra con "
                "paquetes de datos comprimidos.",
            ),
            (
                "img8.png",
                "El protocolo de inmersión protege al agente: un campo de "
                "criptografía gira como escudo temporal.",
            ),
            (
                "img9.png",
                "Objetivo visible: el núcleo de control. Si cae, el mundo de "
                "los datos quedará en silencio.",
            ),
        ]

        self.loaded_images: Dict[str, pygame.Surface] = {}
        self._load_images()
        
        # Control para avance con espacio
        self.space_just_pressed = False
        self.space_was_pressed = False

    def run(self) -> bool:
        slide_index = 0
        char_progress = 0.0
        finished_time = 0.0
        hold_timer = 0.0
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

            current_slide = self.slides[slide_index]
            current_text: str = current_slide["text"]  # type: ignore[index]

            prev_char_progress = int(char_progress)

            # Si se presiona espacio y el slide no ha terminado, completarlo
            if self.space_just_pressed and not slide_finished:
                char_progress = len(current_text)
                slide_finished = True
                finished_time = 0.0
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
            # Si se presiona espacio y el slide ya terminó, avanzar al siguiente
            elif self.space_just_pressed and slide_finished:
                if slide_index < len(self.slides) - 1:
                    slide_index += 1
                    char_progress = 0.0
                    finished_time = 0.0
                    slide_finished = False
                else:
                    # Último slide: ir al slideshow de imágenes
                    self._draw_slide(history, current, slide_index, hold_timer)
                    pygame.display.flip()
                    return self._play_image_sequence()
            # Animación normal de escritura
            elif char_progress < len(current_text):
                char_progress += self.TYPEWRITER_SPEED * dt
                finished_time = 0.0

                # Reproducir sonido de escritura si hay caracteres nuevos
                new_char_progress = int(char_progress)
                if new_char_progress > prev_char_progress and self.typing_sound:
                    if not pygame.mixer.Channel(0).get_busy():
                        pygame.mixer.Channel(0).play(self.typing_sound, loops=-1)

                # Marcar como terminado cuando se completa
                if char_progress >= len(current_text):
                    slide_finished = True
                    if self.typing_sound:
                        pygame.mixer.Channel(0).stop()
            else:
                # Detener sonido cuando termine de escribir
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
                finished_time += dt
                # Auto-avance después de SLIDE_PAUSE
                if finished_time >= self.SLIDE_PAUSE:
                    if slide_index < len(self.slides) - 1:
                        slide_index += 1
                        char_progress = 0.0
                        finished_time = 0.0
                        slide_finished = False
                        continue
                    else:
                        self._draw_slide(current_slide, current_text, slide_index, hold_timer)
                        pygame.display.flip()
                        return self._play_image_sequence()

            visible_text = current_text[: int(char_progress)]
            self._draw_slide(current_slide, visible_text, slide_index, hold_timer)
            pygame.display.flip()

        return self._play_image_sequence()

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

    def _draw_slide(
        self, slide: Dict[str, object], text: str, slide_index: int, hold_timer: float
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

        dots = " ".join("●" if i == slide_index else "○" for i in range(len(self.slides)))
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

    def _play_image_sequence(self) -> bool:
        hold_timer = 0.0
        slide_index = 0
        char_progress = 0.0
        finished_time = 0.0
        overlay_finished = False
        self.space_was_pressed = False

        while slide_index < len(self.image_sequence):
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False

            keys = pygame.key.get_pressed()
            space_just_pressed = keys[pygame.K_SPACE] and not self.space_was_pressed
            self.space_was_pressed = keys[pygame.K_SPACE]

            if keys[pygame.K_SPACE]:
                hold_timer += dt
            else:
                hold_timer = 0.0

            if hold_timer >= self.SKIP_HOLD_TIME:
                return True

            filename, overlay_text = self.image_sequence[slide_index]
            prev_progress = int(char_progress)
            if space_just_pressed and not overlay_finished:
                char_progress = len(overlay_text)
                overlay_finished = True
                finished_time = 0.0
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
            elif space_just_pressed and overlay_finished:
                if slide_index < len(self.image_sequence) - 1:
                    slide_index += 1
                    char_progress = 0.0
                    finished_time = 0.0
                    overlay_finished = False
                else:
                    return True
            elif char_progress < len(overlay_text):
                char_progress += self.TYPEWRITER_SPEED * dt
                finished_time = 0.0
                new_progress = int(char_progress)
                if new_progress > prev_progress and self.typing_sound:
                    if not pygame.mixer.Channel(0).get_busy():
                        pygame.mixer.Channel(0).play(self.typing_sound, loops=-1)
                if char_progress >= len(overlay_text):
                    overlay_finished = True
                    if self.typing_sound:
                        pygame.mixer.Channel(0).stop()
            else:
                if self.typing_sound:
                    pygame.mixer.Channel(0).stop()
                finished_time += dt
                if finished_time >= self.SLIDE_PAUSE:
                    if slide_index < len(self.image_sequence) - 1:
                        slide_index += 1
                        char_progress = 0.0
                        finished_time = 0.0
                        overlay_finished = False
                        continue
                    return True

            visible_overlay = overlay_text[: int(char_progress)]
            self._draw_image_slide(filename, visible_overlay, hold_timer)
            pygame.display.flip()

        return True

    def _draw_image_slide(self, filename: str, overlay_text: str, hold_timer: float) -> None:
        self.screen.fill(self.BG_COLOR)
        image = self.loaded_images.get(filename)
        if image:
            self._draw_shaky_frame(image)

        metrics = self._skip_hint_metrics()
        self._draw_story_bubble(overlay_text, metrics["y"], pygame.time.get_ticks())
        self._draw_skip_hint(hold_timer)

    def _load_images(self) -> None:
        for filename, _ in self.image_sequence:
            path = self.cinematics_dir / filename
            if path.exists():
                try:
                    image = pygame.image.load(str(path)).convert_alpha()
                    self.loaded_images[filename] = image
                except pygame.error:
                    continue

    def _draw_shaky_frame(self, frame: pygame.Surface) -> None:
        width, height = self.screen.get_size()
        img_w, img_h = image.get_size()
        scale = min((width * 0.78) / img_w, (height * 0.82) / img_h)
        new_size = (int(img_w * scale), int(img_h * scale))
        scaled = pygame.transform.smoothscale(image, new_size)

        scale = min(width * 0.9 / frame_w, height * 0.82 / frame_h)
        new_size = (int(frame_w * scale), int(frame_h * scale))
        scaled = pygame.transform.smoothscale(frame, new_size)

        time_ms = pygame.time.get_ticks()
        shake_x = math.sin(time_ms / 90.0) * 2.5
        shake_y = math.cos(time_ms / 110.0) * 2.5

        rect = scaled.get_rect(center=(width // 2 + shake_x, int(height * 0.45) + shake_y))
        self.screen.blit(scaled, rect)
        return rect

    def _draw_story_bubble(self, text: str, baseline_y: int, time_ms: int) -> None:
        if not text:
            return

        width, _ = self.screen.get_size()
        bubble_width = min(int(width * 0.42), width - 120)
        bubble_x = 42 + math.sin(time_ms / 140.0) * 1.5
        bubble_y = baseline_y + math.cos(time_ms / 160.0) * 1.5

        paragraphs: list[str] = []
        for raw_paragraph in text.split("\n"):
            paragraphs.extend(self._wrap_text(raw_paragraph.strip(), bubble_width - 32))

        text_height = sum(
            self.body_font.render(line, True, self.TEXT_COLOR).get_height() + 8
            for line in paragraphs
        )
        bubble_height = text_height + 28
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)

        pygame.draw.rect(self.screen, (12, 14, 30), bubble_rect, border_radius=10)
        pygame.draw.rect(self.screen, self.ACCENT_COLOR, bubble_rect, width=2, border_radius=10)

        y = bubble_rect.top + 14
        for line in paragraphs:
            rendered = self.body_font.render(line, True, self.TEXT_COLOR)
            self.screen.blit(rendered, (bubble_rect.left + 16, y))
            y += rendered.get_height() + 8
