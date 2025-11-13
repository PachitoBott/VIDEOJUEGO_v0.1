# Obstacles sprites

Coloca aquí los sprites PNG para los obstáculos de las salas hostiles.

## Convenciones de nombres

Los sprites se detectan automáticamente si siguen el patrón:

```
<variant>_<ancho>x<alto>.png
```

Por ejemplo `silla_1x1.png`, `pantalla_2x1.png` o `pantallas_azules_4x2.png`. El juego
también acepta la variante `obstacle_<variant>_<ancho>x<alto>.png` y, como último
recurso, intentará cargar `obstacle_<variant>.png` o `<variant>.png`.

Los sprites incluidos por defecto son:

- `silla.png`
- `hoyo.png`
- `caneca.png`
- `tubo_verde_1x2.png`
- `pantalla_2x1.png`
- `impresora_2x1.png`
- `pantallas_2x2.png`
- `pantallas_azules_4x2.png`

## Escalado rápido

El tamaño de la caja de colisión depende exclusivamente del número de tiles del
obstáculo. Para ajustar el tamaño visual sin tocar la colisión puedes usar las
funciones expuestas en `Room.py`:

- `Room.set_obstacle_sprite_scale("silla", 1.2)` para escalar una variante concreta.
- `Room.set_global_obstacle_scale(0.9)` para aplicar un factor a **todos** los sprites.

Tras cambiar la escala en tiempo de ejecución llama a `Room.clear_obstacle_sprite_cache()`
si quieres forzar que las imágenes se vuelvan a generar inmediatamente.
