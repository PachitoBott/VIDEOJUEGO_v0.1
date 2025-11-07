from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pygame


class HudPanels:
    """Administrador de los paneles gráficos del HUD.

    Por defecto busca tres imágenes PNG dentro de ``assets/ui`` con los nombres:

    * ``panel_inventario.png`` — marco principal para la información del jugador.
    * ``panel_minimapa.png`` — marco que "abraza" al minimapa cuadrado.
    * ``panel_esquina.png`` — adorno decorativo para la esquina inferior izquierda.

    Una vez instanciada, puedes ajustar la escala o las posiciones modificando los
    atributos públicos ``scale``, ``inventory_panel_position``,
    ``inventory_content_offset``, ``minimap_panel_offset`` y
    ``corner_panel_margin``. Llama a :meth:`set_scale` después de cambiar
    ``scale`` para regenerar las superficies.
    """

    INVENTORY_FILENAME = "panel_inventario.png"
    MINIMAP_FILENAME = "panel_minimapa.png"
    CORNER_FILENAME = "panel_esquina.png"

    def __init__(self, *, scale: float = 1.0, assets_dir: str | Path | None = None) -> None:
        self.scale = scale
        self.assets_dir = Path(assets_dir) if assets_dir is not None else Path("assets/ui")

        self.inventory_panel_position = pygame.Vector2(16, 16)
        self.inventory_content_offset = pygame.Vector2(28, 36)
        self.minimap_panel_offset = pygame.Vector2(-20, -20)
        self.corner_panel_margin = pygame.Vector2(16, 16)

        self._inventory_original: pygame.Surface | None = None
        self._minimap_original: pygame.Surface | None = None
        self._corner_original: pygame.Surface | None = None

        self.inventory_panel: pygame.Surface | None = None
        self.minimap_panel: pygame.Surface | None = None
        self.corner_panel: pygame.Surface | None = None

        self._load_assets()
        self._apply_scale()

    # ------------------------------------------------------------------
    # Configuración
    # ------------------------------------------------------------------
    def _load_assets(self) -> None:
        self._inventory_original = self._load_surface(self.assets_dir / self.INVENTORY_FILENAME)
        self._minimap_original = self._load_surface(self.assets_dir / self.MINIMAP_FILENAME)
        self._corner_original = self._load_surface(self.assets_dir / self.CORNER_FILENAME)

    def _load_surface(self, path: Path) -> pygame.Surface | None:
        try:
            surface = pygame.image.load(path.as_posix()).convert_alpha()
        except FileNotFoundError:
            print(f"[HUD] Advertencia: no se encontró la imagen '{path}'. Se usará un marcador transparente.")
            surface = None
        except pygame.error as exc:  # pragma: no cover - depende de SDL
            print(f"[HUD] Error al cargar '{path}': {exc}. Se usará un marcador transparente.")
            surface = None
        return surface

    def set_scale(self, scale: float) -> None:
        self.scale = scale
        self._apply_scale()

    def _apply_scale(self) -> None:
        self.inventory_panel = self._scale_surface(self._inventory_original)
        self.minimap_panel = self._scale_surface(self._minimap_original)
        self.corner_panel = self._scale_surface(self._corner_original)

    def _scale_surface(self, surface: pygame.Surface | None) -> pygame.Surface | None:
        if surface is None:
            return None
        if self.scale == 1.0:
            return surface.copy()
        width = max(1, int(surface.get_width() * self.scale))
        height = max(1, int(surface.get_height() * self.scale))
        return pygame.transform.smoothscale(surface, (width, height))

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def blit_inventory_panel(self, surface: pygame.Surface) -> pygame.Rect:
        panel_surface = self.inventory_panel
        position = self.inventory_panel_position
        if panel_surface is not None:
            rect = panel_surface.get_rect(topleft=(int(position.x), int(position.y)))
            surface.blit(panel_surface, rect.topleft)
        else:
            rect = pygame.Rect(int(position.x), int(position.y), 0, 0)
        return rect

    def inventory_content_anchor(self) -> Tuple[int, int]:
        """Devuelve el punto superior-izquierdo sugerido para dibujar el texto."""

        return (
            int(self.inventory_panel_position.x + self.inventory_content_offset.x),
            int(self.inventory_panel_position.y + self.inventory_content_offset.y),
        )

    def blit_minimap_panel(
        self,
        surface: pygame.Surface,
        minimap_surface: pygame.Surface,
        minimap_position: Tuple[int, int],
    ) -> pygame.Rect:
        panel_surface = self.minimap_panel
        offset = self.minimap_panel_offset
        minimap_rect = minimap_surface.get_rect(topleft=minimap_position)
        if panel_surface is not None:
            panel_pos = (
                minimap_rect.left + int(offset.x),
                minimap_rect.top + int(offset.y),
            )
            surface.blit(panel_surface, panel_pos)
        surface.blit(minimap_surface, minimap_rect.topleft)
        return minimap_rect

    def blit_corner_panel(self, surface: pygame.Surface) -> pygame.Rect:
        panel_surface = self.corner_panel
        if panel_surface is None:
            return pygame.Rect(0, 0, 0, 0)
        x = int(self.corner_panel_margin.x)
        y = surface.get_height() - panel_surface.get_height() - int(self.corner_panel_margin.y)
        rect = panel_surface.get_rect(topleft=(x, y))
        surface.blit(panel_surface, rect.topleft)
        return rect
