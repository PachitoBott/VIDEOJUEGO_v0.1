from __future__ import annotations

import math
import random
from typing import Callable

import pygame

from Config import CFG
from Enemy import CHASE, WANDER, Enemy, FastChaserEnemy
from Projectile import Projectile
from enemy_sprites import LayeredBossAnimator, load_boss_animation_layers
from asset_paths import assets_dir

DEBUG_BOSS_HP = True

class BossEnemy(Enemy):
    """Base genérica para bosses con fases y efectos de suelo."""

    SPRITE_VARIANT = "boss_core"
    _CANONICAL_COLLIDER: tuple[float, float, float] | None = None
    _PUDDLE_SPRITES: list[pygame.Surface] = []
    _AIRSTRIKE_SPRITE: pygame.Surface | None = None
    _EXPLOSION_FRAMES: list[pygame.Surface] = []

    @classmethod
    def _load_puddle_sprites(cls) -> list[pygame.Surface]:
        if cls._PUDDLE_SPRITES:
            return cls._PUDDLE_SPRITES

        sprites: list[pygame.Surface] = []
        for filename in ("Charco_Verde1.png", "Charco_Verde2.png"):
            path = assets_dir("obstacles", filename)
            try:
                surface = pygame.image.load(path.as_posix()).convert_alpha()
            except Exception:
                continue
            sprites.append(surface)

        cls._PUDDLE_SPRITES = sprites
        return sprites

    @classmethod
    def _load_airstrike_sprite(cls) -> pygame.Surface | None:
        if cls._AIRSTRIKE_SPRITE is not None:
            return cls._AIRSTRIKE_SPRITE

        path = assets_dir("effects", "AirStrike.png")
        try:
            cls._AIRSTRIKE_SPRITE = pygame.image.load(path.as_posix()).convert_alpha()
        except Exception:
            cls._AIRSTRIKE_SPRITE = None
        return cls._AIRSTRIKE_SPRITE

    @classmethod
    def _load_explosion_frames(cls) -> list[pygame.Surface]:
        if cls._EXPLOSION_FRAMES:
            return cls._EXPLOSION_FRAMES

        frames: list[pygame.Surface] = []
        for idx in range(1, 9):
            path = assets_dir("effects", f"explosion-1-b-{idx}.png")
            try:
                surface = pygame.image.load(path.as_posix()).convert_alpha()
            except Exception:
                continue
            frames.append(surface)

        cls._EXPLOSION_FRAMES = frames
        return frames

    def _choose_puddle_sprite(self, rect: pygame.Rect) -> pygame.Surface | None:
        sprites = self._load_puddle_sprites()
        if not sprites:
            return None

        base = random.choice(sprites)
        if base.get_size() != rect.size:
            try:
                return pygame.transform.smoothscale(base, rect.size)
            except Exception:
                return pygame.transform.scale(base, rect.size)
        return base

    def draw_health_bar_hud(self, surf: "pygame.Surface", *, index: int = 0, top_padding: int = 8) -> None:
        """Dibuja la barra del boss en la HUD (coordenadas de pantalla, no cámara)."""
        import pygame

        try:
            screen_w, screen_h = surf.get_size()
        except Exception:
            return

        bar_w = int(screen_w * 0.5)
        bar_h = max(8, int(screen_h * 0.025))
        gap = 6
        x = screen_w // 2 - bar_w // 2
        y = top_padding + index * (bar_h + gap)

        bg_rect = pygame.Rect(x, y, bar_w, bar_h)
        pygame.draw.rect(surf, (30, 30, 30), bg_rect)

        max_hp = getattr(self, "max_hp", 1) or 1
        hp = max(0, getattr(self, "hp", 0))
        frac = max(0.0, min(1.0, float(hp) / float(max_hp)))
        fg_rect = pygame.Rect(x, y, int(bar_w * frac), bar_h)
        if fg_rect.width > 0:
            pygame.draw.rect(surf, (34, 177, 76), fg_rect)
        pygame.draw.rect(surf, (180, 50, 50), bg_rect, 1)

        # DEBUG: confirmar que se dibuja
        if DEBUG_BOSS_HP:
            try:
                print(f"[HUD BAR] boss hp {hp}/{max_hp} frac={frac:.2f} at {bg_rect}")
            except Exception:
                pass

    def draw_health_bar(self, surf: "pygame.Surface") -> None:
        import pygame

        def is_rect_like(o):
            return (hasattr(o, "width") and hasattr(o, "height") and hasattr(o, "top"))

        # Intentar resolver un rect seguro desde varias fuentes.
        dest = None
        candidates = ("dest", "dest_rect", "rect", "get_rect")
        for name in candidates:
            cand = getattr(self, name, None)
            if cand is None:
                continue
            # Si es callable, intentar llamar sin argumentos
            if callable(cand):
                try:
                    cand = cand()
                except TypeError:
                    # no-arg call falló: no forzar más llamadas
                    cand = None
                except Exception:
                    cand = None
            if cand is None:
                continue
            if is_rect_like(cand):
                dest = cand
                break

        # Fallback: construir rect centrado en self.x,self.y usando sprite size
        if not is_rect_like(dest):
            sprite_w = int(getattr(self, "sprite_w", getattr(self, "w", 64)))
            sprite_h = int(getattr(self, "sprite_h", getattr(self, "h", 64)))
            try:
                cx = int(getattr(self, "x"))
                cy = int(getattr(self, "y"))
            except Exception:
                return
            dest = pygame.Rect(cx - sprite_w // 2, cy - sprite_h // 2, sprite_w, sprite_h)

        # Dibujar barra sobre el boss
        bar_w = int(dest.width * 0.9)
        bar_h = max(4, int(dest.height * 0.08))
        bar_x = dest.centerx - bar_w // 2
        bar_y = dest.top - 8 - bar_h

        full_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(surf, (40, 40, 40), full_rect)
        if getattr(self, "max_hp", 0) > 0:
            frac = max(0.0, min(1.0, float(getattr(self, "hp", 0)) / float(self.max_hp)))
        else:
            frac = 0.0
        fg_rect = pygame.Rect(bar_x, bar_y, int(bar_w * frac), bar_h)
        if fg_rect.width > 0:
            pygame.draw.rect(surf, (34, 177, 76), fg_rect)
        pygame.draw.rect(surf, (180, 50, 50), full_rect, 1)

        if DEBUG_BOSS_HP:
            try:
                print("HP BAR:", getattr(self, "hp", None), "/", getattr(self, "max_hp", None), "dest", (dest.x, dest.y, dest.w if hasattr(dest,'w') else dest.width), "surf", surf.get_size())
            except Exception:
                print("HP BAR: debug print failed")

    def __init__(self, x: float, y: float, *, max_hp: int = 50, gold_reward: int = 60) -> None:
        super().__init__(x, y, hp=max_hp, gold_reward=gold_reward)
        self.max_hp = max_hp
        self.hp = self.max_hp
        self.phase = 1
        self.enraged = False
        self.is_boss = True
        self.contact_damage = 2
        self.detect_radius = 9999.0
        self.lose_radius = 9999.0
        self.reaction_delay = 0.0
        self.telegraphs: list[dict] = []
        self.puddles: list[dict] = []
        self.explosions: list[dict] = []
        self._player_rect_cache: pygame.Rect | None = None
        self._phase_thresholds = (0.6, 0.3)
        self._tracked_room = None
        self._prev_anim_pos: tuple[float, float] = (x, y)
        # Animación en capas (piernas/torso + muerte completa)
        self.animations = load_boss_animation_layers(self.sprite_variant)
        self.animator = LayeredBossAnimator(
            self.animations,
            leg_fps={"idle": 5.0, "run": 10.0},
            torso_fps={
                "idle": 5.0,
                "shoot1": 10.0,
                "shoot2": 12.0,
                "shoot3": 10.0,
            },
            default_fps=8.0,
            death_fps=12.0,
        )
        # Ajustar el collider al tamaño real del sprite y mantenerlo centrado
        fallback_w, fallback_h = self.animations.fallback.get_size()
        if fallback_w > 0 and fallback_h > 0:
            self._fit_collider_to_sprite(fallback_w, fallback_h)

    def take_damage(
        self,
        amount: int,
        knockback_dir: tuple[float, float] | None = None,
        stun_duration: float = 0.22,
        knockback_strength: float = 150.0,
    ) -> bool:
        """Reduce el retroceso aplicado a los bosses para que mantengan presencia."""

        if knockback_strength > 0.0:
            knockback_strength *= 0.35
        return super().take_damage(
            amount,
            knockback_dir,
            stun_duration=stun_duration,
            knockback_strength=knockback_strength,
        )

    def _fit_collider_to_sprite(self, sprite_w: int, sprite_h: int) -> None:
        """Redimensiona el hitbox según el sprite actual.

        El boss de las moscas tiene mucha decoración en la parte superior; se
        recorta más por arriba y ligeramente por los lados para que el collider
        se sienta justo.
        """

        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        width = sprite_w
        height = sprite_h
        y_offset = 0.0

        shared_hitbox_variants = {"boss_core", "boss_security"}
        if self.sprite_variant in shared_hitbox_variants:
            side_trim = max(6, int(width * 0.1))
            top_trim = max(18, int(height * 0.36))
            bottom_trim = max(5, int(height * 0.12))
            width = max(12, width - side_trim * 2)
            height = max(12, height - (top_trim + bottom_trim))
            downward_bias = max(6.0, height * 0.12)
            y_offset = (top_trim - bottom_trim) / 2 + downward_bias
            if BossEnemy._CANONICAL_COLLIDER is None:
                BossEnemy._CANONICAL_COLLIDER = (width, height, y_offset)
            else:
                width, height, y_offset = BossEnemy._CANONICAL_COLLIDER

        self.w = width
        self.h = height
        self.x = cx - self.w / 2
        self.y = cy - self.h / 2 + y_offset

    def on_spawn(self, room) -> None:
        self._tracked_room = room

    def update(self, dt: float, player, room) -> None:
        self._prev_anim_pos = (self.x, self.y)
        self._tracked_room = room
        self._player_rect_cache = self._player_rect(player)
        self._update_phase_state()
        super().update(dt, player, room)
        self._update_telegraphs(dt, player)
        self._update_puddles(dt, player)
        self._update_explosions(dt)

    def on_phase_changed(self, new_phase: int) -> None:  # pragma: no cover - gancho opcional
        self.enraged = new_phase >= 3

    def draw_floor_effects(self, surface: pygame.Surface) -> None:
        for entry in self.telegraphs:
            rect: pygame.Rect = entry["rect"]
            duration = max(0.01, entry.get("duration", 0.8))
            alpha = int(60 + 160 * (entry["timer"] / duration))
            color = entry.get("color", (255, 80, 80, 140))
            sprite: pygame.Surface | None = entry.get("sprite")
            if sprite is not None:
                surface.blit(sprite, rect.topleft)
            else:
                overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                overlay.fill((*color[:3], min(255, max(0, alpha))))
                surface.blit(overlay, rect.topleft)
                pygame.draw.rect(surface, (255, 200, 200), rect, 2)
        for puddle in self.puddles:
            rect: pygame.Rect = puddle["rect"]
            sprite: pygame.Surface | None = puddle.get("sprite")
            if sprite is not None:
                surface.blit(sprite, rect.topleft)
            else:
                color = puddle.get("color", (120, 40, 40, 140))
                overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                overlay.fill((*color[:3], color[3] if len(color) > 3 else 150))
                surface.blit(overlay, rect.topleft)
                pygame.draw.rect(surface, (255, 180, 120), rect, 1)
        for explosion in self.explosions:
            sprite: pygame.Surface | None = explosion.get("frame")
            if sprite is None:
                continue
            rect: pygame.Rect = explosion["rect"]
            surface.blit(sprite, rect.topleft)

    def draw(self, surf: pygame.Surface) -> None:
        legs, torso = self.animator.current_surfaces()
        if not self._facing_right:
            legs = pygame.transform.flip(legs, True, False)
            if torso:
                torso = pygame.transform.flip(torso, True, False)

        center = self.rect().center
        leg_dest = legs.get_rect(center=center)
        surf.blit(legs, leg_dest)

        if torso is not None:
            torso_dest = torso.get_rect(center=center)
            surf.blit(torso, torso_dest)

        if CFG.DEBUG_DRAW_BOSS_HITBOX_LAYOUT:
            self._draw_hitbox_layout(surf, leg_dest, torso_dest)

        # Asegurarse de dibujar la barra de vida después del sprite (para que sea visible)
        try:
            self.draw_health_bar(surf)
        except Exception:
            # No romper el juego si algo sale mal al dibujar la barra
            pass

    def _draw_hitbox_layout(
        self,
        surf: pygame.Surface,
        leg_dest: pygame.Rect,
        torso_dest: pygame.Rect | None,
    ) -> None:
        collider_rect = self.rect()
        sprite_rect = leg_dest.union(torso_dest) if torso_dest is not None else leg_dest

        # Overlay directo en la escena
        pygame.draw.rect(surf, (0, 200, 255), sprite_rect, 1)
        pygame.draw.rect(surf, (255, 90, 90), collider_rect, 2)
        cx, cy = collider_rect.center
        pygame.draw.line(surf, (255, 90, 90), (cx - 6, cy), (cx + 6, cy))
        pygame.draw.line(surf, (255, 90, 90), (cx, cy - 6), (cx, cy + 6))

        # Diagrama miniatura para ver proporciones de hitbox vs sprite
        diagram_size = 104
        padding = 8
        base_max = max(1, max(sprite_rect.w, sprite_rect.h))
        scale = (diagram_size - padding * 2) / base_max

        def _scaled_rect(rect: pygame.Rect) -> pygame.Rect:
            return pygame.Rect(
                int(padding + (rect.x - sprite_rect.x) * scale),
                int(padding + (rect.y - sprite_rect.y) * scale),
                max(1, int(rect.w * scale)),
                max(1, int(rect.h * scale)),
            )

        diagram = pygame.Surface((diagram_size, diagram_size), pygame.SRCALPHA)
        diagram.fill((10, 10, 10, 180))
        mini_sprite = _scaled_rect(sprite_rect)
        mini_collider = _scaled_rect(collider_rect)
        pygame.draw.rect(diagram, (0, 200, 255, 180), mini_sprite, 1)
        pygame.draw.rect(diagram, (255, 90, 90, 220), mini_collider, 2)

        font = pygame.font.Font(None, 16)
        label_texts = [
            "Layout hitbox",
            f"Sprite: {sprite_rect.w}x{sprite_rect.h}",
            f"Collider: {self.w}x{self.h}",
        ]
        text_y = diagram_size - padding - len(label_texts) * 14
        for text in label_texts:
            rendered = font.render(text, True, (240, 240, 240))
            diagram.blit(rendered, (padding, text_y))
            text_y += 14

        diagram_dest = diagram.get_rect()
        diagram_dest.topleft = (sprite_rect.right + 10, sprite_rect.top - 6)

        # Evitar que salga completamente de pantalla
        surf_w, surf_h = surf.get_size()
        if diagram_dest.right > surf_w:
            diagram_dest.right = surf_w - 4
        if diagram_dest.top < 0:
            diagram_dest.top = 4
        if diagram_dest.bottom > surf_h:
            diagram_dest.bottom = surf_h - 4

        surf.blit(diagram, diagram_dest.topleft)

    def add_telegraph(
        self,
        rect: pygame.Rect,
        delay: float = 0.8,
        damage: int = 1,
        color: tuple[int, int, int, int] = (255, 80, 80, 150),
    ) -> None:
        sprite = self._get_airstrike_sprite(rect.size)
        self.telegraphs.append(
            {
                "rect": rect,
                "timer": delay,
                "duration": delay,
                "damage": max(1, damage),
                "color": color,
                "sprite": sprite,
            }
        )

    def add_puddle(
        self,
        rect: pygame.Rect,
        duration: float = 4.0,
        damage: int = 1,
        tick_interval: float = 0.55,
        color: tuple[int, int, int, int] = (120, 0, 0, 180),
    ) -> None:
        sprite = self._choose_puddle_sprite(rect)
        self.puddles.append(
            {
                "rect": rect,
                "timer": duration,
                "damage": max(1, damage),
                "tick": tick_interval,
                "tick_timer": 0.0,
                "color": color,
                "sprite": sprite,
            }
        )

    def _update_phase_state(self) -> None:
        ratio = 1.0 if self.max_hp <= 0 else max(0.0, self.hp / self.max_hp)
        new_phase = 1
        if ratio <= self._phase_thresholds[1]:
            new_phase = 3
        elif ratio <= self._phase_thresholds[0]:
            new_phase = 2
        if new_phase != self.phase:
            self.phase = new_phase
            self.on_phase_changed(new_phase)

    def _player_rect(self, player) -> pygame.Rect:
        if hasattr(player, "rect"):
            rect_callable = player.rect
            if isinstance(rect_callable, pygame.Rect):
                return rect_callable.copy()
            if callable(rect_callable):
                return rect_callable()
        width = int(getattr(player, "w", 16))
        height = int(getattr(player, "h", 16))
        return pygame.Rect(int(getattr(player, "x", 0)), int(getattr(player, "y", 0)), width, height)

    def _update_telegraphs(self, dt: float, player) -> None:
        if not self.telegraphs:
            return
        remaining: list[dict] = []
        for entry in self.telegraphs:
            entry["timer"] -= dt
            if entry["timer"] <= 0.0:
                self._trigger_telegraph(entry, player)
            else:
                remaining.append(entry)
        self.telegraphs = remaining

    def _trigger_telegraph(self, entry: dict, player) -> None:
        rect: pygame.Rect = entry["rect"]
        damage = entry.get("damage", 1)
        player_rect = self._player_rect_cache or self._player_rect(player)
        if player_rect.colliderect(rect):
            self._apply_damage_to_player(player, damage)
        self._spawn_explosion_effect(rect)

    def _update_puddles(self, dt: float, player) -> None:
        if not self.puddles:
            return
        player_rect = self._player_rect_cache or self._player_rect(player)
        survivors: list[dict] = []
        for puddle in self.puddles:
            duration = puddle.get("timer")
            if duration is not None:
                puddle["timer"] = duration - dt
                if puddle["timer"] <= 0:
                    continue

            tick_interval = puddle.get("tick", 0.5)
            if tick_interval > 0:
                puddle["tick_timer"] = puddle.get("tick_timer", 0.0) - dt
            if player_rect.colliderect(puddle["rect"]):
                if tick_interval <= 0 or puddle.get("tick_timer", 0.0) <= 0:
                    self._apply_damage_to_player(player, puddle.get("damage", 1))
                    if tick_interval > 0:
                        puddle["tick_timer"] = tick_interval
            survivors.append(puddle)
        self.puddles = survivors

    def _update_explosions(self, dt: float) -> None:
        if not self.explosions:
            return

        remaining: list[dict] = []
        for explosion in self.explosions:
            explosion["elapsed"] += dt
            duration = explosion["duration"]
            frame_duration = explosion["frame_duration"]
            frames: list[pygame.Surface] = explosion["frames"]
            if duration <= 0 or not frames:
                continue
            if explosion["elapsed"] < duration:
                frame_index = min(len(frames) - 1, int(explosion["elapsed"] / frame_duration))
                scaled_frames: list[pygame.Surface] = explosion["scaled_frames"]
                explosion["frame"] = scaled_frames[frame_index]
                remaining.append(explosion)
        self.explosions = remaining

    def _spawn_explosion_effect(self, rect: pygame.Rect) -> None:
        frames = self._load_explosion_frames()
        if not frames:
            return

        try:
            scaled_frames = [pygame.transform.smoothscale(frame, rect.size) for frame in frames]
        except Exception:
            scaled_frames = [pygame.transform.scale(frame, rect.size) for frame in frames]

        duration = max(0.01, 0.5)
        frame_duration = duration / max(1, len(scaled_frames))
        self.explosions.append(
            {
                "rect": rect.copy(),
                "elapsed": 0.0,
                "duration": duration,
                "frame_duration": frame_duration,
                "frames": frames,
                "scaled_frames": scaled_frames,
                "frame": scaled_frames[0],
            }
        )

    def _get_airstrike_sprite(self, size: tuple[int, int]) -> pygame.Surface | None:
        base = self._load_airstrike_sprite()
        if base is None:
            return None
        if base.get_size() == size:
            return base
        try:
            return pygame.transform.smoothscale(base, size)
        except Exception:
            return pygame.transform.scale(base, size)

    def _apply_damage_to_player(self, player, amount: int) -> None:
        taker: Callable[[int], bool] | None = getattr(player, "take_damage", None)
        if callable(taker):
            taker(amount)

    def _update_animation(self, dt: float) -> None:
        prev_x, prev_y = getattr(self, "_prev_anim_pos", (self.x, self.y))
        moved_dist = math.hypot(self.x - prev_x, self.y - prev_y)

        base_state = "run" if moved_dist > 0.1 else "idle"
        self.animator.set_leg_state(base_state)
        self.animator.set_torso_base_state("idle")
        self.animator.update(dt)
        self._prev_anim_pos = (self.x, self.y)

    def trigger_shoot_animation(self, variant: str = "shoot1") -> None:
        if self._is_dying:
            return
        self.animator.trigger_shoot(variant)

    def draw_health_bar_hud(self, surf: "pygame.Surface", *, index: int = 0, top_padding: int = 8) -> None:
        """
        Dibuja la barra del boss en la HUD (arriba de la pantalla).
        index: para apilar varias barras si hay >1 boss (0 = la primera, centrada).
        """
        import pygame

        screen_w, screen_h = surf.get_size()
        bar_w = int(screen_w * 0.5)  # ancho relativo en HUD (ajusta a tu gusto)
        bar_h = max(8, int(screen_h * 0.025))
        gap = 6
        x = screen_w // 2 - bar_w // 2
        y = top_padding + index * (bar_h + gap)

        # Fondo
        bg_rect = pygame.Rect(x, y, bar_w, bar_h)
        pygame.draw.rect(surf, (30, 30, 30), bg_rect)
        # Fracción de vida
        max_hp = getattr(self, "max_hp", 1) or 1
        hp = max(0, getattr(self, "hp", 0))
        frac = max(0.0, min(1.0, float(hp) / float(max_hp)))
        fg_rect = pygame.Rect(x, y, int(bar_w * frac), bar_h)
        if fg_rect.width > 0:
            pygame.draw.rect(surf, (34, 177, 76), fg_rect)
        # Borde y texto simple (opcional)
        pygame.draw.rect(surf, (180, 50, 50), bg_rect, 1)
        try:
            font = pygame.font.get_default_font()
            f = pygame.font.Font(font, max(12, bar_h - 2))
            txt = f"{hp} / {max_hp}"
            text_surf = f.render(txt, True, (255, 255, 255))
            ts_rect = text_surf.get_rect(center=bg_rect.center)
            surf.blit(text_surf, ts_rect)
        except Exception:
            # Si no hay fuente o falla, saltar el texto
            pass

class CorruptedServerBoss(BossEnemy):
    SPRITE_VARIANT = "boss_core"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, max_hp=50, gold_reward=90)
        self.chase_speed = 35.0
        self.wander_speed = 0.0
        self.contact_damage = 2
        self.radial_cooldown = 1.8
        self.line_cooldown = 2.6
        self.minion_cooldown = 8.2
        self.telegraph_cooldown = 5.0
        self.laser_cooldown = 4.5
        self._radial_timer = 1.4
        self._line_timer = 1.8
        self._minion_timer = 6.0
        self._telegraph_timer = 3.5
        self._laser_timer = 2.5

    def on_phase_changed(self, new_phase: int) -> None:
        super().on_phase_changed(new_phase)
        if new_phase >= 3:
            self.chase_speed = 0.0

    def maybe_shoot(self, dt, player, room, out_bullets) -> bool:
        fired = False
        self._radial_timer -= dt
        self._line_timer -= dt
        self._minion_timer -= dt
        self._telegraph_timer -= dt
        self._laser_timer -= dt
        if self.phase == 1:
            if self._radial_timer <= 0.0:
                self._fire_radial(out_bullets, speed=140.0, bullets=18)
                self._radial_timer = self.radial_cooldown
                self.trigger_shoot_animation("shoot1")
                fired = True
            if self._line_timer <= 0.0:
                self._fire_line(player, out_bullets, speed=140.0, bullets=7)
                self._line_timer = self.line_cooldown
                self.trigger_shoot_animation("shoot2")
                fired = True
        elif self.phase == 2:
            if self._radial_timer <= 0.0:
                self._fire_radial(out_bullets, speed=200.0, bullets=12)
                self._radial_timer = max(0.9, self.radial_cooldown * 0.75)
                self.trigger_shoot_animation("shoot1")
                fired = True
            if self._line_timer <= 0.0:
                self._fire_line(player, out_bullets, speed=182.0, bullets=5)
                self._line_timer = max(1.2, self.line_cooldown * 0.7)
                self.trigger_shoot_animation("shoot2")
                fired = True
            if self._minion_timer <= 0.0:
                self._spawn_minions(room)
                self._minion_timer = self.minion_cooldown
                self.trigger_shoot_animation("shoot1")
                fired = True
        else:
            if self._telegraph_timer <= 0.0:
                self._spawn_telegraphs(player)
                self._telegraph_timer = max(2.5, self.telegraph_cooldown * 0.6)
                self.trigger_shoot_animation("shoot3")
                fired = True
            if self._laser_timer <= 0.0:
                self._fire_laser(player, out_bullets)
                self._laser_timer = max(2.8, self.laser_cooldown * 0.75)
                self.trigger_shoot_animation("shoot2")
                fired = True
        return fired

    def _fire_radial(self, out_bullets, *, bullets: int, speed: float) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        for i in range(bullets):
            angle = math.tau * (i / bullets)
            dx = math.cos(angle)
            dy = math.sin(angle)
            proj = Projectile(
                cx + dx * 12,
                cy + dy * 12,
                dx,
                dy,
                speed=speed,
                radius=6,
                color=(180, 220, 255),
                is_boss_projectile=True,
            )
            out_bullets.add(proj)

    def _fire_line(self, player, out_bullets, *, speed: float, bullets: int) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        target = self._player_rect_cache or self._player_rect(player)
        tx, ty = target.center
        dx = tx - cx
        dy = ty - cy
        dist = math.hypot(dx, dy) or 1.0
        dx /= dist
        dy /= dist
        for i in range(bullets):
            offset = 14 + i * 12
            proj = Projectile(
                cx + dx * offset,
                cy + dy * offset,
                dx,
                dy,
                speed=speed,
                radius=6,
                color=(255, 160, 80),
                is_boss_projectile=True,
            )
            out_bullets.add(proj)

    def _spawn_minions(self, room) -> None:
        if not hasattr(room, "enemies"):
            return
        count = random.randint(1, 3)
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            distance = random.randint(38, 72)
            px = cx + math.cos(angle) * distance
            py = cy + math.sin(angle) * distance
            minion = FastChaserEnemy(px - 6, py - 6)
            minion.detect_radius = 150.0
            minion.lose_radius = 210.0
            room.enemies.append(minion)

    def _spawn_telegraphs(self, player) -> None:
        target = self._player_rect_cache or self._player_rect(player)
        base_x, base_y = target.center
        for _ in range(3):
            offset_x = random.randint(-30, 30)
            offset_y = random.randint(-30, 30)
            size = CFG.TILE_SIZE + random.randint(-6, 12)
            rect = pygame.Rect(
                int(base_x + offset_x - size // 2),
                int(base_y + offset_y - size // 2),
                size,
                size,
            )
            self.add_telegraph(rect, delay=0.8, damage=2)

    def _fire_laser(self, player, out_bullets) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        target = self._player_rect_cache or self._player_rect(player)
        tx, ty = target.center
        dx = tx - cx
        dy = ty - cy
        dist = math.hypot(dx, dy) or 1.0
        dx /= dist
        dy /= dist
        for i in range(6):
            offset = 12 + i * 18
            proj = Projectile(
                cx + dx * offset,
                cy + dy * offset,
                dx,
                dy,
                speed=320.0,
                radius=5,
                color=(255, 255, 120),
                is_boss_projectile=True,
            )
            out_bullets.add(proj)


class SecurityManagerBoss(BossEnemy):
    SPRITE_VARIANT = "boss_security"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, max_hp=65, gold_reward=110)
        self.chase_speed = 55.0
        self.contact_damage = 2
        self._dash_cooldown = 4.2
        self._dash_timer = 1.5
        self._dash_active = False
        self._dash_dir = pygame.Vector2(0, 0)
        self._dash_remaining = 0.0
        self._dash_windup = 0.0
        self._cone_timer = 1.0
        self._cone_cooldown = 2.6
        self._dash_origin: pygame.Vector2 | None = None
        self._dash_trail: list[dict] = []
        self._dash_trail_timer = 0.0
        self._dash_trail_interval = 0.02
        self._dash_trail_lifetime = 0.22
        self._dash_trail_size = max(8, int(self.w * 0.45))

    def on_phase_changed(self, new_phase: int) -> None:
        super().on_phase_changed(new_phase)
        if new_phase >= 2:
            self.chase_speed = 70.0
            self._dash_cooldown = 3.5
            self._cone_cooldown = 2.0

    def update(self, dt: float, player, room) -> None:
        super().update(dt, player, room)
        self._update_dash(dt, room)
        self._update_dash_trail(dt, self._dash_active)

    def maybe_shoot(self, dt, player, room, out_bullets) -> bool:
        fired = False
        self._dash_timer = max(0.0, self._dash_timer - dt)
        self._cone_timer = max(0.0, self._cone_timer - dt)
        if not self._dash_active and self._dash_windup <= 0 and self._dash_timer <= 0:
            self._queue_dash(player)
            self._dash_timer = self._dash_cooldown
            fired = True
        elif self._cone_timer <= 0 and not self._dash_active:
            self._fire_cone(player, out_bullets)
            self._cone_timer = self._cone_cooldown
            fired = True
        return fired

    def _queue_dash(self, player) -> None:
        target = self._player_rect_cache or self._player_rect(player)
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        dx = target.centerx - cx
        dy = target.centery - cy
        dist = math.hypot(dx, dy) or 1.0
        dx /= dist
        dy /= dist
        self._dash_dir.update(dx, dy)
        self._dash_windup = 0.45 if self.phase == 1 else 0.28
        self._dash_remaining = 0.45 if self.phase == 1 else 0.55
        self.lock_movement(self._dash_windup + self._dash_remaining)
        self._dash_origin = pygame.Vector2(cx, cy)

    def _update_dash(self, dt: float, room) -> None:
        if self._dash_windup > 0:
            self._dash_windup = max(0.0, self._dash_windup - dt)
            if self._dash_windup == 0:
                self._dash_active = True
        if not self._dash_active:
            return
        dash_speed = 210.0 if self.phase == 1 else 250.0
        self.move(
            self._dash_dir.x,
            self._dash_dir.y,
            dt * (dash_speed / max(1e-6, self.speed)),
            room,
        )
        self._dash_remaining -= dt
        if self._dash_remaining <= 0:
            self._dash_active = False
            if self.phase >= 2:
                self._leave_puddle()

    def _update_dash_trail(self, dt: float, dash_active: bool) -> None:
        for segment in self._dash_trail:
            segment["life"] -= dt
        self._dash_trail = [seg for seg in self._dash_trail if seg["life"] > 0.0]

        self._dash_trail_timer = max(0.0, self._dash_trail_timer - dt)
        if dash_active and self._dash_trail_timer <= 0.0:
            self._dash_trail_timer = self._dash_trail_interval
            cx = self.x + self.w / 2
            cy = self.y + self.h / 2
            vertical_offset = max(14, int(self.h * 0.22))
            self._dash_trail.append(
                {
                    "pos": (cx, cy + vertical_offset),
                    "life": self._dash_trail_lifetime,
                }
            )

    def _draw_dash_trail(self, surf: pygame.Surface) -> None:
        if not self._dash_trail:
            return

        max_life = self._dash_trail_lifetime if self._dash_trail_lifetime > 0 else 0.0001
        size = self._dash_trail_size
        for segment in self._dash_trail:
            life = segment["life"]
            alpha = max(0, min(255, int(255 * (life / max_life))))
            trail_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            dark_green = (25, 90, 60, int(alpha * 0.75))
            bright_green = (120, 255, 170, alpha)

            inner_size = max(2, int(size * 0.58))
            inner_margin = (size - inner_size) // 2

            pygame.draw.rect(
                trail_surface,
                dark_green,
                pygame.Rect(0, 0, size, size),
            )
            pygame.draw.rect(
                trail_surface,
                bright_green,
                pygame.Rect(inner_margin, inner_margin, inner_size, inner_size),
            )
            pos_x, pos_y = segment["pos"]
            surf.blit(trail_surface, (pos_x - size / 2, pos_y - size / 2))

    def _leave_puddle(self) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        size = int(CFG.TILE_SIZE * 1.4)
        rect = pygame.Rect(int(cx - size // 2), int(cy - size // 2), size, size)
        self.add_puddle(rect, duration=float("inf"), damage=2, tick_interval=0.0)

    def _fire_cone(self, player, out_bullets) -> None:
        cx = self.x + self.w / 2
        cy = self.y + self.h / 2
        target = self._player_rect_cache or self._player_rect(player)
        tx, ty = target.center
        base_dx = tx - cx
        base_dy = ty - cy
        base_angle = math.atan2(base_dy, base_dx)
        spread = math.radians(55)
        pellets = 9
        speed = 168.0 if self.phase == 1 else 208.0
        for i in range(pellets):
            if pellets == 1:
                angle = base_angle
            else:
                t = i / (pellets - 1)
                angle = base_angle - spread / 2 + spread * t
            dx = math.cos(angle)
            dy = math.sin(angle)
            proj = Projectile(
                cx + dx * 14,
                cy + dy * 14,
                dx,
                dy,
                speed=speed,
                radius=4,
                color=(255, 120, 90),
            )
            out_bullets.add(proj)

    def draw(self, surf: pygame.Surface) -> None:
        self._draw_dash_trail(surf)
        super().draw(surf)


BOSS_BLUEPRINTS = [CorruptedServerBoss, SecurityManagerBoss]

__all__ = [
    "BossEnemy",
    "CorruptedServerBoss",
    "SecurityManagerBoss",
    "BOSS_BLUEPRINTS",
]
