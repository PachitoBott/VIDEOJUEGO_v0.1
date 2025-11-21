# Sprites de enemigos

Coloca los sprites animados de cada tipo de enemigo dentro de una carpeta
con el nombre del variant. Para la versión actual existen estas variantes:

- `yellow_shooter` — enemigos amarillos que disparan.
- `green_chaser` — enemigos verdes que persiguen.
- `blue_shooter` — disparador azul que lanza muchas balas (el shooter).
- `tank` — enemigo pesado con escopeta. Si prefieres reutilizar los sprites
  del disparador azul, puedes dejarlos en `blue_shooter/` y el juego hará el
  intercambio automáticamente.

Dentro de cada carpeta se esperan los siguientes archivos PNG:

- `idle_0.png`, `idle_1.png`, `idle_2.png`, `idle_3.png`
- `run_0.png`, `run_1.png`, `run_2.png`, `run_3.png`
- `shoot_0.png`, `shoot_1.png`, `shoot_2.png`, `shoot_3.png`
- `attack_0.png`, `attack_1.png`, `attack_2.png`, `attack_3.png` *(opcional para los
  enemigos cuerpo a cuerpo)*
- `death_0.png` … `death_N.png` (coloca todos los cuadros consecutivos; el motor
  detecta automáticamente cuántos hay disponibles)

Cada sprite debe incluir canal alfa y estar orientado mirando hacia la
**derecha**; el motor se encarga de voltear la animación cuando el enemigo
mira hacia la izquierda.

## Sprites de boss

Coloca los PNG del boss dentro de `assets/enemigos/boss/`.

- **Opción 1 (recomendada):** crea una subcarpeta con el nombre de la variante,
  por ejemplo `assets/enemigos/boss/boss_core/`, y coloca ahí las capas
  `legs_*`, `torso_*` y `death_*`.
- **Opción 2:** si prefieres no usar subcarpeta, puedes dejar los archivos
  directamente en `assets/enemigos/boss/`; el cargador ahora detecta y usa
  esos sprites automáticamente.
