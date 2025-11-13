"""Utilities to resolve project asset directories regardless of CWD."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

# ---------------------------------------------------------------------------
# Directorios de assets
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def project_root() -> Path:
    """Return the absolute path to the repository root."""

    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=None)
def assets_dir(*extra: str | Path) -> Path:
    """Return the absolute path to the ``assets`` directory (optionally joined).

    Parameters
    ----------
    *extra:
        Optional path components to append to the base ``assets`` directory.
    """

    base = project_root() / "assets"
    if extra:
        return base.joinpath(*extra)
    return base


# ---------------------------------------------------------------------------
# Rutas de sprites para armas
# ---------------------------------------------------------------------------

# Mapeo explícito de ``weapon_id`` -> nombre de archivo esperado dentro de
# ``assets/weapons``.  Mantén esta lista sincronizada con las armas
# registradas en ``Weapons.WeaponFactory``.
WEAPON_SPRITE_FILENAMES: dict[str, str] = {
    "short_rifle": "short_rifle.png",
    "dual_pistols": "dual_pistols.png",
    "light_rifle": "light_rifle.png",
    "arcane_salvo": "arcane_salvo.png",
    "pulse_rifle": "pulse_rifle.png",
    "tesla_gloves": "tesla_gloves.png",
    "ember_carbine": "ember_carbine.png",
}


def weapon_sprite_path(weapon_id: str) -> Path:
    """Devuelve la ruta absoluta al sprite del arma indicada.

    Si el arma no está registrada, asumirá ``<weapon_id>.png`` como nombre de
    archivo para permitir añadir nuevos sprites sin romper el flujo.
    """

    filename = WEAPON_SPRITE_FILENAMES.get(weapon_id, f"{weapon_id}.png")
    return assets_dir("weapons", filename)
