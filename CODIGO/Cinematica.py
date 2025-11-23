import pygame


class Cinematica:
    """Muestra una pantalla final con efecto de máquina de escribir."""

    TEXT = (
        "Our defenses were flawless.\n"
        "For decades, the system had repelled every intrusion, every probe, every unauthorized signal.\n"
        "But all it took was one vulnerability.\n"
        "A single unpatched weakness.\n"
        "A forgotten line of code.\n"
        "The Zero-Day exploit spread faster than our protocols could respond.\n"
        "Firewalls collapsed.\n"
        "Gateways went dark.\n"
        "Malware swarmed every access point like a digital plague.\n"
        "Entire sectors fell in minutes.\n"
        "Surveillance nodes went blind.\n"
        "Antivirus modules were overrun.\n"
        "And at the center of it all… the MotherBoard woke up.\n"
        "This is why cybersecurity is everything.\n"
        "A world built on data can fall in seconds."
    )

    def __init__(self, screen: pygame.Surface, cfg, *, text: str | None = None) -> None:
        self.screen = screen
        self.cfg = cfg
        self.text = text or self.TEXT
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 22)
        self.text_color = (255, 0, 0)
        self.bg_color = (0, 0, 0)
        self.chars_per_second = 45
        self.post_text_delay = 2.0
        self.skip_key = pygame.K_o
        self.skip_hold_required = 3.0

    def play(self) -> None:
        visible_characters = 0
        accumulator = 0.0
        finished = False
        finished_timer = 0.0
        skip_hold = 0.0

        while True:
            dt = self.clock.tick(self.cfg.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and finished:
                    return

            if not finished:
                accumulator += self.chars_per_second * dt
                while accumulator >= 1.0 and visible_characters < len(self.text):
                    visible_characters += 1
                    accumulator -= 1.0
                finished = visible_characters >= len(self.text)
            else:
                finished_timer += dt
                pressed = pygame.key.get_pressed()
                if finished_timer >= self.post_text_delay or any(pressed):
                    return

            pressed_keys = pygame.key.get_pressed()
            if pressed_keys[self.skip_key]:
                skip_hold += dt
                if skip_hold >= self.skip_hold_required:
                    return
            else:
                skip_hold = 0.0

            self._render_text(self.text[:visible_characters])

    def _render_text(self, text: str) -> None:
        self.screen.fill(self.bg_color)
        y = 80
        line_height = self.font.get_linesize() + 6
        for line in text.splitlines():
            rendered = self.font.render(line, True, self.text_color)
            self.screen.blit(rendered, (40, y))
            y += line_height
        pygame.display.flip()
