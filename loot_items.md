# Apariencia y probabilidades de botín en el suelo (nuevas instrucciones)

Estas notas consolidan cómo debe verse cada ítem de botín en el suelo y con qué frecuencia aparecen, aplicando los cambios solicitados (sin modificar el código todavía).

## Distribución de aparición
- **Microchips (oro): 70 %**
- **Cápsula de vida amarilla (pequeña, roja): 20 %**
- **Batería verde de vida completa: 10 %**
- **Mejora morada: 10 %**
- **Paquetes (oro + curación): 5 %**
- **Armas raras: 1 %**

> Todos los demás ítems o consumibles anteriores quedan eliminados.

## Apariencia de cada pickup

### Microchip (oro)
- **Sprite**: icono cuadrado procedural de 32×32 px, cuerpo turquesa con marco vino y pines dorados a ambos lados.
- **Pickup**: se escala a ~16 px de ancho para el suelo y **flota** con vaivén senoidal (~2 px de amplitud).

### Cápsula de vida amarilla (nueva)
- **Sprite**: frasco **pequeño rojo** (para indicar curación menor), ~12×14 px; cuerpo rojo en dos tonos, brillo lateral claro, cruz crema y tapa rojo oscuro con aro dorado.
- **Curación**: recupera solo un impacto de la batería actual.
- **Animación**: flota con el mismo vaivén suave que el resto de botines.

### Batería verde (vida completa)
- **Sprite**: batería/frasco verde de 14×18 px con dos tonos y tapa verde oscura; cruz blanca centrada.
- **Curación**: recarga por completo la vida en uso.
- **Animación**: vaivén senoidal compartido.

### Mejora (upgrade morada)
- **Sprite**: hexágono lila claro de 16×16 px con contorno morado oscuro y chispa blanca rectangular en el centro.
- **Efecto**: mejora pasiva (velocidad, recarga, dash, etc.).
- **Animación**: flota con vaivén senoidal.

### Paquete (bundle)
- **Sprite**: caja de 16×16 px detallada: madera marrón con vetas y borde oscuro, doble cinta amarilla cruzada y lazo rojo texturizado con brillo.
- **Contenido**: combinaciones de oro + curación (y nada más); deben ser mucho más raros de ver.
- **Animación**: vaivén senoidal compartido.

### Arma rara
- **Sprite**: silueta estilizada de arma (20×8 px aprox.), cañón gris azulado, empuñadura gris oscuro y acentos dorados.
- **Efecto**: otorga un arma rara específica.
- **Animación**: flota con el mismo vaivén de botín.

## Ítems eliminados
- Se **elimina el consumible azul** u otros consumibles no listados arriba.
- No deben generarse pickups fuera de los tipos descritos.
