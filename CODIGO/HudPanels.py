from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pygame

from asset_paths import assets_dir as get_assets_dir


class HudPanels:
    """Administrador de los paneles gráficos del HUD.

    Por defecto busca tres imágenes PNG dentro de ``assets/ui`` con los nombres:

    * ``panel_inventario.png`` — marco principal para la información del jugador.
    * ``panel_minimapa.png`` — marco que "abraza" al minimapa cuadrado.
    * ``panel_esquina.png`` — adorno decorativo para la esquina inferior izquierda.

    Una vez instanciada, puedes ajustar la escala o las posiciones modificando los
    atributos públicos ``inventory_panel_position``, ``inventory_content_offset``,
    ``minimap_panel_offset`` y ``corner_panel_margin``.

    Para la escala, hay tres multiplicadores independientes:

    * :attr:`inventory_scale`
    * :attr:`minimap_scale`
    * :attr:`corner_scale`

    Usa :meth:`set_inventory_scale`, :meth:`set_minimap_scale` y
    :meth:`set_corner_scale` para recalcular cada superficie de manera
    individual, o :meth:`set_scale` para aplicar el mismo factor a los tres
    paneles a la vez.
    """

    INVENTORY_FILENAME = "panel_inventario.png"
    MINIMAP_FILENAME = "panel_minimapa.png"
    CORNER_FILENAME = "panel_esquina.png"

    def __init__(self, *, scale: float = 1.0, assets_dir: str | Path | None = None) -> None:
        self.scale = scale
        self.assets_dir = Path(assets_dir) if assets_dir is not None else get_assets_dir("ui")

        self.inventory_scale = 0.4
        self.minimap_scale = 0.6
        self.corner_scale = 0.8

        self.inventory_panel_position = pygame.Vector2(10, 160)
        self.inventory_content_offset = pygame.Vector2(28, 36)
        self.minimap_panel_offset = pygame.Vector2(-80, 20)
        self.minimap_margin = pygame.Vector2(16, 100)
        self.minimap_anchor = "top-right"
        self.corner_panel_margin = pygame.Vector2(-70, 70)

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
        self.inventory_scale = scale
        self.minimap_scale = scale
        self.corner_scale = scale
        self._apply_scale()

    def set_inventory_scale(self, scale: float) -> None:
        self.inventory_scale = scale
        self._apply_scale()

    def set_minimap_scale(self, scale: float) -> None:
        self.minimap_scale = scale
        self._apply_scale()

    def set_minimap_anchor(self, anchor: str, margin: Tuple[float, float] | pygame.Vector2 | None = None) -> None:
        """Define la esquina/base desde la que se posiciona el minimapa.

        ``anchor`` puede ser uno de ``"top-left"``, ``"top-right"``,
        ``"bottom-left"``, ``"bottom-right"`` o ``"corner"``. Este
        último centra el panel del minimapa dentro del panel de esquina
        (si existe) y permite aplicar un ``margin`` adicional como ajuste
        fino.
        """

        self.minimap_anchor = anchor
        if margin is not None:
            if isinstance(margin, pygame.Vector2):
                self.minimap_margin.update(margin)
            else:
                self.minimap_margin.update(*margin)

    def set_corner_scale(self, scale: float) -> None:
        self.corner_scale = scale
        self._apply_scale()

    def _apply_scale(self) -> None:
        self.inventory_panel = self._scale_surface(self._inventory_original, self.inventory_scale)
        self.minimap_panel = self._scale_surface(self._minimap_original, self.minimap_scale)
        self.corner_panel = self._scale_surface(self._corner_original, self.corner_scale)

    def _scale_surface(self, surface: pygame.Surface | None, scale: float) -> pygame.Surface | None:
        if surface is None:
            return None
        if scale == 1.0:
            return surface.copy()
        width = max(1, int(surface.get_width() * scale))
        height = max(1, int(surface.get_height() * scale))
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
        surface.blit(minimap_surface, minimap_rect.topleft)
        if panel_surface is not None:
            panel_pos = (
                minimap_rect.left + int(offset.x),
                minimap_rect.top + int(offset.y),
            )
            surface.blit(panel_surface, panel_pos)
        
        return minimap_rect

    def corner_panel_rect(self, surface: pygame.Surface) -> pygame.Rect:
        panel_surface = self.corner_panel
        if panel_surface is None:
            return pygame.Rect(0, 0, 0, 0)
        x = int(self.corner_panel_margin.x)
        y = surface.get_height() - panel_surface.get_height() - int(self.corner_panel_margin.y)
        return panel_surface.get_rect(topleft=(x, y))

    def blit_corner_panel(self, surface: pygame.Surface) -> pygame.Rect:
        rect = self.corner_panel_rect(surface)
        if rect.width and rect.height and self.corner_panel is not None:
            surface.blit(self.corner_panel, rect.topleft)
        return rect

    def compute_minimap_position(
        self,
        target_surface: pygame.Surface,
        minimap_surface: pygame.Surface,
    ) -> Tuple[int, int]:
        """Calcula la posición topleft para el minimapa según el anchor."""

        sw, sh = target_surface.get_size()
        mw, mh = minimap_surface.get_size()
        margin_x = int(self.minimap_margin.x)
        margin_y = int(self.minimap_margin.y)
        anchor = (self.minimap_anchor or "top-right").lower()

        if anchor == "top-left":
            x = margin_x
            y = margin_y
        elif anchor == "top-right":
            x = sw - mw - margin_x
            y = margin_y
        elif anchor == "bottom-left":
            x = margin_x
            y = sh - mh - margin_y
        elif anchor == "corner":
            corner_rect = self.corner_panel_rect(target_surface)
            panel_surface = self.minimap_panel
            if panel_surface is not None and corner_rect.width and corner_rect.height:
                panel_w, panel_h = panel_surface.get_size()
                offset_x = int(self.minimap_panel_offset.x)
                offset_y = int(self.minimap_panel_offset.y)
                x = corner_rect.left + (corner_rect.width - panel_w) // 2 - offset_x + margin_x
                y = corner_rect.top + (corner_rect.height - panel_h) // 2 - offset_y + margin_y
            else:
                x = sw - mw - margin_x
                y = margin_y
        else:  # bottom-right por defecto / fallback
            x = sw - mw - margin_x
            y = sh - mh - margin_y

        return (x, y)
