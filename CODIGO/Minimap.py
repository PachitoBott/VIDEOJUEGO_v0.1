import pygame

class Minimap:
    def __init__(self, cell: int = 20, padding: int = 10) -> None:
        self.cell = cell
        self.padding = padding

        # Colores
        self.bg       = (20, 20, 20)
        self.border   = (255, 255, 255)
        self.grid     = (120, 120, 140)   # celdas no exploradas
        self.explored = (180, 180, 200)   # celdas exploradas
        self.current  = (255, 100, 100)   # posición del jugador
        self.shop_col = (255, 215, 0)     # dorado para la tienda
        self.treasure_col = (130, 205, 255)  # azul claro para cofres
        self.boss_col = (255, 130, 60)    # naranja intenso para boss

        # Opcional: mostrar icono $ sobre la tienda
        self.show_shop_icon = True
        self._font = None  # se inicializa lazy en render()

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            # Tamaño proporcional a la celda
            size = max(10, int(self.cell * 0.75))
            self._font = pygame.font.SysFont(None, size)
        return self._font

    def render(self, dungeon) -> pygame.Surface:
        gw = int(getattr(dungeon, "grid_w", 3))
        gh = int(getattr(dungeon, "grid_h", 3))
        explored = getattr(dungeon, "explored", set())
        cur_room = getattr(dungeon, "current_room", None)
        cur = (int(getattr(dungeon, "i", 0)), int(getattr(dungeon, "j", 0)))

        w = gw * self.cell + self.padding * 2
        h = gh * self.cell + self.padding * 2

        surf = pygame.Surface((w, h))  # opaco
        surf.fill(self.bg)
        pygame.draw.rect(surf, self.border, (0, 0, w, h), 2)

        # Cache de font si se va a usar el icono
        font = self._get_font() if self.show_shop_icon else None
        shop_glyph = None
        if font:
            shop_glyph = font.render("$", True, (10, 10, 10))  # sombra oscura
            shop_glyph2 = font.render("$", True, (255, 255, 255))  # brillo
        else:
            shop_glyph2 = None

        room_groups: dict[object, list[tuple[int, int]]] = {}
        if hasattr(dungeon, "rooms"):
            for pos, room in dungeon.rooms.items():
                room_groups.setdefault(room, []).append(pos)

        explored_rooms = {room for room, cells in room_groups.items() if any(p in explored for p in cells)}

        for j in range(gh):
            for i in range(gw):
                x = self.padding + i * self.cell
                y = self.padding + j * self.cell
                rect = pygame.Rect(x, y, self.cell - 2, self.cell - 2)

                color = self.grid
                room = dungeon.rooms.get((i, j)) if hasattr(dungeon, "rooms") else None
                room_type = getattr(room, "type", "normal")
                logical_explored = room in explored_rooms

                if logical_explored:
                    if room_type == "shop":
                        color = self.shop_col
                    elif room_type == "treasure":
                        color = self.treasure_col
                    elif room_type == "boss":
                        color = self.boss_col
                    else:
                        color = self.explored

                if room is not None and room is cur_room:
                    color = self.current
                elif (i, j) == cur:
                    color = self.current

                pygame.draw.rect(surf, color, rect)

        if self.show_shop_icon and room_groups:
            for room, cells in room_groups.items():
                room_type = getattr(room, "type", "normal")
                if room_type != "shop":
                    continue
                if room not in explored_rooms:
                    continue
                if not (shop_glyph and shop_glyph2):
                    continue
                avg_x = sum(p[0] for p in cells) / len(cells)
                avg_y = sum(p[1] for p in cells) / len(cells)
                gx = self.padding + int(avg_x * self.cell) + (self.cell - 2) // 2
                gy = self.padding + int(avg_y * self.cell) + (self.cell - 2) // 2
                surf.blit(shop_glyph, shop_glyph.get_rect(center=(gx + 1, gy + 1)))
                surf.blit(shop_glyph2, shop_glyph2.get_rect(center=(gx, gy)))

        return surf
