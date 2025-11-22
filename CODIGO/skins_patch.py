# CODIGO/skins_patch.py
"""
Script to patch the skins system to support subdirectories (gordo/flaco variants).
Run this after manual edits to complete the implementation.
"""

import re
from pathlib import Path

# Path to files
BASE = Path(__file__).parent
START_MENU = BASE / "StartMenu.py"
MAIN = BASE / "Main.py"

def patch_start_menu():
    """Patch StartMenu.py to add skin_data support and fix discovery."""
    content = START_MENU.read_text(encoding='utf-8')
    
    # 1. Add skin_data to StartMenuResult
    content = re.sub(
        r'(@dataclass\(frozen=True\)\s+class StartMenuResult:.*?seed: Optional\[int\])',
        r'\1\n    skin_data: Optional[dict] = None',
        content,
        flags=re.DOTALL
    )
    
   # 2. Update _discover_skins to search subdirectories
    discover_method = '''    def _discover_skins(self) -> list[dict]:
        """Descubre todas las skins disponibles incluyendo subdirectorios."""
        player_dir = Path(self.cfg.PLAYER_SPRITES_PATH) if self.cfg.PLAYER_SPRITES_PATH else None
        if not player_dir or not player_dir.exists():
            return [{"name": "player", "folder": None, "prefix": "player"}]
        
        skins = []
        
        # Root directory skins
        for file in player_dir.glob("*_idle.png"):
            prefix = file.stem.replace("_idle", "")
            skins.append({"name": prefix, "folder": None, "prefix": prefix})
        
        # Subdirectory skins
        for subdir in player_dir.iterdir():
            if subdir.is_dir():
                idle_files = list(subdir.glob("idle_*.png"))
                if idle_files:
                    # Extract prefix from idle_PREFIX.png
                    prefix = idle_files[0].stem.replace("idle_", "")
                    display_name = subdir.name.replace("_", " ")
                    skins.append({
                        "name": display_name,
                        "folder": subdir.name,
                        "prefix": prefix
                    })
        
        if not skins:
            skins = [{"name": "player", "folder": None, "prefix": "player"}]
        
        print(f"[SKINS] Skins descubiertas: {[s['name'] for s in skins]}")
        return skins'''
    
    content = re.sub(
        r'def _discover_skins\(self\).*?return skin_list',
        discover_method,
        content,
        flags=re.DOTALL
    )
    
    # 3. Update run() to return skin_data
    content = re.sub(
        r'(pygame\.mixer\.music\.fadeout\(500\)\s+)return StartMenuResult\(start_game=True, seed=self\.selected_seed\(\)\)',
        r'\1current = self.available_skins[self.current_skin_index]\n            skin_data = {\n                "folder": current["folder"],\n                "prefix": current["prefix"]\n            }\n            return StartMenuResult(start_game=True, seed=self.selected_seed(), skin_data=skin_data)',
        content
    )
    
    # 4. Update _get_skin_preview to handle subdirectories
    preview_method = '''    def _get_skin_preview(self, skin_dict: dict) -> pygame.Surface | None:
        """Obtiene preview de la skin desde folder/prefix."""
        cache_key = skin_dict["name"]
        if cache_key in self.skin_preview_cache:
            return self.skin_preview_cache[cache_key]
        
        player_dir = Path(self.cfg.PLAYER_SPRITES_PATH) if self.cfg.PLAYER_SPRITES_PATH else None
        if not player_dir:
            return None
        
        folder = skin_dict["folder"]
        prefix = skin_dict["prefix"]
        
        if folder:
            base_dir = player_dir / folder
            candidates = [
                base_dir / f"idle_{prefix}.png",
                base_dir / f"idle_{prefix}_0.png",
            ]
        else:
            candidates = [
                player_dir / f"{prefix}_idle.png",
                player_dir / f"{prefix}_idle_0.png",
            ]
        
        for path in candidates:
            if path.exists():
                try:
                    surface = pygame.image.load(str(path)).convert_alpha()
                    scaled = pygame.transform.smoothscale(surface, (128, 128))
                    self.skin_preview_cache[cache_key] = scaled
                    return scaled
                except Exception as e:
                    print(f"[SKINS] Error: {e}")
        
        return None'''
    
    content = re.sub(
        r'def _get_skin_preview\(self, skin_name.*?return None',
        preview_method,
        content,
        flags=re.DOTALL
    )
    
    # 5. Update _change_skin to use new prefix
    content = re.sub(
        r'(self\.current_skin_index.*?\n.*?new_skin = self\.available_skins.*?\n.*?)(object\.__setattr__\(CFG.*?\n)',
        r'\1new_prefix = new_skin["prefix"]\n        object.__setattr__(CFG, \'PLAYER_SPRITE_PREFIX\', new_prefix)\n        ',
        content
    )
    
    # 6. Update _draw_skin_selector to use dict
    content = re.sub(
        r'current_skin = self\.available_skins\[self\.current_skin_index\]',
        r'current_skin_dict = self.available_skins[self.current_skin_index]',
        content
    )
    content = re.sub(
        r'(current_skin_dict.*?\n.*?)preview = self\._get_skin_preview\(current_skin\)',
        r'\1preview = self._get_skin_preview(current_skin_dict)',
        content
    )
    content = re.sub(
        r'skin_name_display = current_skin\.replace',
        r'skin_name_display = current_skin_dict["name"].replace',
        content
    )
    
    START_MENU.write_text(content, encoding='utf-8')
    print("✓ StartMenu.py patched")

def patch_main():
    """Simplify Main.py to use default initialization."""
    content = '''from Config import CFG
from Game import Game

if __name__ == "__main__":
    Game(CFG).run()
'''
    MAIN.write_text(content, encoding='utf-8')
    print("✓ Main.py patched")

if __name__ == "__main__":
    print("Applying skins patches...")
    patch_start_menu()
    patch_main()
    print("\\n✓ All patches applied! You can now run Main.py")
