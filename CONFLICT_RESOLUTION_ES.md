# Cómo resolver conflictos de merge en Git

Cuando Git detecta cambios incompatibles entre tu rama y la rama remota/base, marca los archivos en conflicto con delimitadores especiales. Estos pasos te ayudan a resolverlos sin perder trabajo.

## 1. Detecta los conflictos
1. Ejecuta `git status` para ver los archivos con conflictos.
2. Abre cada archivo marcado; verás bloques delimitados por `<<<<<<<`, `=======` y `>>>>>>>`.

## 2. Elige qué contenido conservar
En cada bloque tienes tres opciones:
- **Aceptar cambio actual**: conservar lo que ya estaba en tu rama (sección encima de `=======`).
- **Aceptar cambio entrante**: conservar lo que viene de la rama que estás integrando (sección debajo de `=======`).
- **Combinar ambos**: edita el bloque para mezclar manualmente ambos fragmentos si necesitas partes de los dos.

> Consejo: los botones "Accept Current Change", "Accept Incoming Change" o "Accept Both Changes" en tu editor solo automatizan esta elección. Puedes editar el bloque directamente y borrar los marcadores.

## 3. Limpia los marcadores
Asegúrate de eliminar todas las líneas con `<<<<<<<`, `=======` y `>>>>>>>` después de decidir el contenido final. Guarda el archivo sin esos marcadores.

## 4. Verifica que el código compile o funcione
Ejecuta tus pruebas o comandos de compilación habituales para asegurarte de que el archivo resuelto no tiene errores.

## 5. Marca los archivos como resueltos
Usa `git add <archivo>` para cada archivo corregido. Revisa el estado con `git status` para confirmar que ya no hay conflictos pendientes.

## 6. Completa el merge o rebase
- Si estabas en un **merge**, ejecuta `git merge --continue` (o simplemente `git commit` si ya estabas en ese paso).
- Si estabas en un **rebase**, ejecuta `git rebase --continue`.

## 7. Vuelve a intentarlo
Cuando el merge/rebase termine sin conflictos, puedes hacer push normalmente: `git push origin <rama>`.

## Ejemplo rápido
```bash
git status              # identifica archivos en conflicto
nano CODIGO/Game.py     # resuelve el bloque con marcadores
# borra <<<<<<<, ======= y >>>>>>> y deja solo el código final
python -m compileall CODIGO  # comprueba que no haya errores de sintaxis
git add CODIGO/Game.py  # marca el archivo como resuelto
git merge --continue    # o git rebase --continue, según el caso
git push origin work
```

Si vuelves a ver tres conflictos, repite el proceso en cada archivo. Así tendrás el historial limpio y podrás hacer push sin bloqueos.
