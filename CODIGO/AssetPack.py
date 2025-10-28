import json
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pygame


class AssetPack:
    """Carga sprites y animaciones desde un manifest JSON opcional."""

    def __init__(
        self,
        base_path: Optional[str],
        manifest_name: str = "pack.json",
        *,
        tile_size: int = 16,
    ) -> None:
        self.base_path = base_path
        self.manifest_name = manifest_name
        self.tile_size = tile_size
        self.loaded = False
        self.sprites: Dict[str, pygame.Surface] = {}
        self.animations: Dict[str, List[pygame.Surface]] = {}
        self.metadata: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}

        if base_path:
            self._load_manifest()

    # ------------------------------------------------------------------ #
    # Acceso público
    # ------------------------------------------------------------------ #
    def sprite(self, sprite_id: Optional[str], fallback: Optional[pygame.Surface] = None) -> Optional[pygame.Surface]:
        if sprite_id is None:
            return fallback
        sprite = self.sprites.get(sprite_id)
        if sprite is None:
            return fallback
        return sprite

    def animation(self, anim_id: str) -> List[pygame.Surface]:
        return self.animations.get(anim_id, [])

    def draw(
        self,
        surface: pygame.Surface,
        sprite_id: Optional[str],
        position: tuple[int, int],
        *,
        anchor: str = "center",
        fallback_color: Optional[tuple[int, int, int]] = None,
        size: Optional[tuple[int, int]] = None,
    ) -> None:
        sprite = self.sprite(sprite_id)
        if sprite is not None:
            rect = sprite.get_rect()
            setattr(rect, anchor, position)
            surface.blit(sprite, rect)
            return
        if fallback_color is not None and size is not None:
            rect = pygame.Rect(0, 0, *size)
            setattr(rect, anchor, position)
            pygame.draw.rect(surface, fallback_color, rect)

    # ------------------------------------------------------------------ #
    # Carga interna
    # ------------------------------------------------------------------ #
    def _load_manifest(self) -> None:
        manifest_path = os.path.join(self.base_path, self.manifest_name)
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            self.errors["manifest"] = "No se encontró el manifest del asset pack."
            return
        except json.JSONDecodeError as exc:
            self.errors["manifest"] = f"Error de sintaxis en manifest: {exc}"
            return

        self.metadata = {k: v for k, v in data.items() if k not in {"sprites", "animations", "tile_size"}}

        manifest_tile = data.get("tile_size")
        if isinstance(manifest_tile, int) and manifest_tile > 0:
            self.tile_size = manifest_tile

        sprites = data.get("sprites", {})
        for sprite_id, definition in sprites.items():
            loaded = self._load_sprite_definition(sprite_id, definition)
            if loaded is None:
                continue
            if isinstance(loaded, list):
                self.animations[sprite_id] = loaded
                if loaded:
                    self.sprites[sprite_id] = loaded[0]
            else:
                self.sprites[sprite_id] = loaded

        animations = data.get("animations", {})
        for anim_id, definition in animations.items():
            frames = self._load_sprite_frames(anim_id, definition)
            if frames:
                self.animations[anim_id] = frames

        self.loaded = True

    def _load_sprite_definition(self, sprite_id: str, definition: Any) -> Optional[pygame.Surface | List[pygame.Surface]]:
        if isinstance(definition, str):
            image = self._load_image(definition)
            return image
        if isinstance(definition, dict):
            frames = self._load_sprite_frames(sprite_id, definition)
            if frames:
                if definition.get("mode") == "animation":
                    return frames
                return frames[0]
        self.errors[sprite_id] = "Definición de sprite no soportada"
        return None

    def _load_sprite_frames(self, sprite_id: str, definition: Any) -> List[pygame.Surface]:
        if not isinstance(definition, dict):
            self.errors[sprite_id] = "Definición inválida"
            return []
        path = definition.get("path") or definition.get("image")
        if not isinstance(path, str):
            self.errors[sprite_id] = "Falta 'path' en la definición"
            return []
        image = self._load_image(path)
        if image is None:
            self.errors[sprite_id] = "No se pudo cargar la imagen"
            return []

        frame_w = definition.get("frame_width") or definition.get("width") or definition.get("size")
        frame_h = definition.get("frame_height") or definition.get("height") or definition.get("size")
        if isinstance(frame_w, int) and not isinstance(frame_h, int):
            frame_h = frame_w
        if isinstance(frame_h, int) and not isinstance(frame_w, int):
            frame_w = frame_h

        if not isinstance(frame_w, int) or not isinstance(frame_h, int):
            # sin tamaño se considera sprite único
            return [self._apply_scale(image, definition)]

        margin = int(definition.get("margin", 0))
        spacing = int(definition.get("spacing", 0))
        columns = int(definition.get("columns", max(1, (image.get_width() - margin * 2 + spacing) // (frame_w + spacing))))
        frames = int(definition.get("frames", columns * max(1, (image.get_height() - margin * 2 + spacing) // (frame_h + spacing))))

        result: List[pygame.Surface] = []
        for index in range(frames):
            col = index % columns
            row = index // columns
            rect = pygame.Rect(
                margin + col * (frame_w + spacing),
                margin + row * (frame_h + spacing),
                frame_w,
                frame_h,
            )
            if rect.right > image.get_width() or rect.bottom > image.get_height():
                break
            frame = image.subsurface(rect).copy()
            frame = self._apply_scale(frame, definition)
            result.append(frame)
        return result

    def _apply_scale(self, surface: pygame.Surface, definition: Dict[str, Any]) -> pygame.Surface:
        if "scale" in definition:
            scale = float(definition["scale"])
            if scale != 1.0:
                w = max(1, int(surface.get_width() * scale))
                h = max(1, int(surface.get_height() * scale))
                surface = pygame.transform.smoothscale(surface, (w, h))
        elif "size" in definition and isinstance(definition["size"], Sequence) and len(definition["size"]) == 2:
            w, h = definition["size"]
            surface = pygame.transform.smoothscale(surface, (int(w), int(h)))
        return surface

    def _load_image(self, relative_path: str) -> Optional[pygame.Surface]:
        if not self.base_path:
            return None
        full_path = os.path.join(self.base_path, relative_path)
        if not os.path.isfile(full_path):
            self.errors[relative_path] = "Archivo no encontrado"
            return None
        try:
            image = pygame.image.load(full_path).convert_alpha()
        except Exception as exc:  # pragma: no cover - dependiente de pygame
            self.errors[relative_path] = f"Error cargando imagen: {exc}"
            return None
        return image

    def available_sprites(self) -> Iterable[str]:
        return self.sprites.keys()

    def available_animations(self) -> Iterable[str]:
        return self.animations.keys()
