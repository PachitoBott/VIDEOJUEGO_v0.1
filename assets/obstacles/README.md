# Obstacles sprites

Coloca aquí los sprites PNG para los obstáculos de las salas hostiles.

## Convenciones de nombres rápidas

Si subes un archivo con alguno de estos nombres, el juego lo detectará automáticamente:

- `silla.png` (1x1)
- `hoyo.png` (1x1)
- `caneca.png` (1x1)
- `tubo_verde_1x2.png`
- `pantalla_2x1.png`
- `impresora_2x1.png`
- `pantallas_2x2.png`
- `pantallas_azules_4x2.png`

Puedes añadir más variantes siguiendo el patrón:

```
<variant>_<ancho>x<alto>.png
```

o bien `obstacle_<variant>_<ancho>x<alto>.png`.

## Manifest opcional

Si necesitas un nombre diferente, crea (o edita) `manifest.json` en esta misma carpeta. Ejemplo:

```json
{
  "silla": {
    "1x1": "mi_silla.png"
  },
  "pantallas_azules": {
    "4x2": "setup/pantalla_azul.png"
  },
  "tubo_verde": {
    "default": "tubo.png"
  }
}
```

Las rutas pueden ser relativas a esta carpeta o absolutas. Tras modificar el manifiesto puedes usar `Room.clear_obstacle_sprite_cache()` para recargar los sprites en caliente.
