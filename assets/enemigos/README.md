# Sprites de enemigos

Coloca los sprites animados de cada tipo de enemigo dentro de una carpeta
con el nombre del variant. Para la versión actual existen estas variantes:

- `yellow_shooter` — enemigos amarillos que disparan.
- `green_chaser` — enemigos verdes que persiguen.
- `blue_shooter` — disparador azul que lanza muchas balas (el "tank").
  Si quieres seguir usando el nombre anterior puedes dejar los sprites en
  `tank/` y el juego los tomará como respaldo.

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
