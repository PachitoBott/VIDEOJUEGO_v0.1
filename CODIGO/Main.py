from Config import CFG
from Game import Game

if __name__ == "__main__":
    print("[Main] creando Game…")
    g = Game(CFG)
    print("[Main] ejecutando run()…")
    g.run()
