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
128×128 px (o cualquier tamaño similar) y ajustar la escala y la posición desde
el código (`Game.weapon_icon_scale`, `Game.weapon_icon_offset`,
`Game.weapon_ammo_offset`).
