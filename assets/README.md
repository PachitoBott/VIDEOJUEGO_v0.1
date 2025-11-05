# Assets

Coloca aquí el archivo `tileset.png` (o la imagen de tu preferencia) con los sprites del piso, muros y esquinas. El motor lo buscará usando la ruta configurada en `CODIGO/Config.py` (`assets/tileset.png` por defecto).

Los sprites deben organizarse en una sola fila de celdas de 32×32 píxeles en el siguiente orden: piso, muro superior, muro inferior, muro izquierdo, muro derecho, esquina noroeste, esquina noreste, esquina suroeste y esquina sureste.

## Sprites del jugador

Las animaciones del jugador se cargan desde la carpeta indicada en `Config.PLAYER_SPRITES_PATH` (`assets/player` por defecto). Cada imagen debe medir 32×32 píxeles (si no, se reescalará automáticamente) y seguir la convención de nombres `player_<estado>_<frame>.png`.

- Idle: `player_idle.png` (un único archivo).
- Correr: `player_run_0.png` a `player_run_3.png`.
- Recargar: `player_reload_0.png` a `player_reload_4.png`.
- Disparar: `player_shoot_0.png` a `player_shoot_3.png`.

Puedes cambiar el prefijo (`player`) modificando `Config.PLAYER_SPRITE_PREFIX` si necesitas organizar varios personajes.
