# Sprites de armas

Coloca aquí los sprites PNG de cada arma del juego. Usa los siguientes nombres de
archivo para que el HUD los cargue automáticamente:

- `short_rifle.png`
- `dual_pistols.png`
- `light_rifle.png`
- `arcane_salvo.png`
- `pulse_rifle.png`
- `tesla_gloves.png`
- `ember_carbine.png`

Las imágenes se escalan en tiempo de ejecución, por lo que puedes subirlas en
128×128 px (o cualquier tamaño similar). Para modificar dónde se dibuja y qué
tan grande aparece cada icono puedes editar los valores ``HUD_WEAPON_*`` en
``CODIGO/Config.py`` o llamar a ``Game.configure_weapon_hud(...)`` en tu código.
