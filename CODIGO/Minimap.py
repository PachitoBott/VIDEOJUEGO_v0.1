import pygame

class Minimap:
    def __init__(self, cell: int = 20, padding: int = 10) -> None:
        self.cell = cell
        self.padding = padding
        self.bg = (20, 20, 20)
        self.border = (255, 255, 255)
        self.grid = (120, 120, 140)
        self.explored = (180, 180, 200)
        self.current = (255, 100, 100)

    def render(self, dungeon) -> pygame.Surface:
        gw = int(getattr(dungeon, "grid_w", 3))
        gh = int(getattr(dungeon, "grid_h", 3))
        explored = getattr(dungeon, "explored", set())
        cur = (int(getattr(dungeon, "i", 0)), int(getattr(dungeon, "j", 0)))

        w = gw * self.cell + self.padding * 2
        h = gh * self.cell + self.padding * 2

        surf = pygame.Surface((w, h))  # opaco
        surf.fill(self.bg)
        pygame.draw.rect(surf, self.border, (0, 0, w, h), 2)

        for j in range(gh):
            for i in range(gw):
                x = self.padding + i * self.cell
                y = self.padding + j * self.cell
                rect = pygame.Rect(x, y, self.cell - 2, self.cell - 2)
                color = self.grid
                if (i, j) in explored: color = self.explored
                if (i, j) == cur:      color = self.current
                pygame.draw.rect(surf, color, rect)
        return surf
