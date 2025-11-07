# Paneles del HUD

Coloca aquí los archivos PNG para los paneles del HUD:

- `panel_inventario.png`
- `panel_minimapa.png`
- `panel_esquina.png`

Los nombres deben coincidir exactamente para que el cargador automático de `HudPanels` los encuentre.

### Ajustar tamaños

En el código puedes escalar cada panel de forma independiente llamando a:

```python
self.hud_panels.set_inventory_scale(1.2)
self.hud_panels.set_minimap_scale(0.9)
self.hud_panels.set_corner_scale(1.0)
```

Usa valores mayores que `1.0` para agrandar y menores para reducir; las superficies se regeneran automáticamente.
