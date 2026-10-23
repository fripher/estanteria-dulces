# Cámara para el láser: acomodar piezas en los retazos

Un celular viejo fijo arriba de la cama toma una foto, el programa encuentra los retazos que pusiste y acomoda
dentro de ellos las piezas de tus SVG, sin salirse y dejando margen. Sale un **DXF** para abrir en **RDWorks** y
cortar.

Funciona con el mismo láser como regla: el láser graba una vez un **patrón de calibración**, y la cámara aprende
de ahí dónde cae cada milímetro **en coordenadas del láser**. Por eso no hay que medir nada a mano.

> Las fotos y los cortes se guardan solo en tu PC (`datos/` y `salida/`). No se suben a GitHub.

---

## Lo que necesitas

- El celular Android viejo con la app **IP Webcam** (gratis, Play Store) y su cargador.
- Un **soporte fijo** para el celular arriba de la cama, **que no se mueva** (ver paso 3).
- **Cartulina o cartón** que cubra la cama, para grabar el patrón una sola vez.
- El PC con Python (el mismo de los scripts de Corel).

---

## Instalar y preparar (una sola vez)

### 1. Instalar
Doble clic en **`1 INSTALAR (una vez).bat`**. Debe terminar sin letras rojas de error.

> Si sale un error con `opencv-python`, puede que tu Python sea muy nuevo para esa librería. Instala
> **Python 3.12** desde python.org (marca "Add to PATH") y repite este paso.

### 2. Celular (app IP Webcam)
1. Abre **IP Webcam** → baja hasta **Configuración de vídeo**:
   - **Resolución de foto**: la más alta.
   - **Orientación**: horizontal (landscape), y **no** la cambies después.
2. **Enfoque**: si la app lo permite, déjalo **fijo** (no "continuo"), para que la foto no cambie de tamaño.
3. Desactiva el **ahorro de batería** y el **apagado de pantalla** para esta app.
4. Abajo del todo: **Iniciar servidor**. La pantalla muestra una dirección tipo `http://192.168.1.50:8080`.
5. El celular y el PC deben estar en el **mismo wifi**.

### 3. Soporte del celular
- **Fijo al cuerpo de la máquina, a la pared o al techo. NUNCA en la tapa**: la tapa se mueve y se pierde todo.
- Mirando hacia abajo, más o menos al centro de la cama, a **1 metro o un poco más**, hasta que en la foto se vea
  **toda la cama** con un poquito de sobra.
- Mide con metro la distancia **del lente del celular a la cama**. La vas a escribir en el paso 4.
- Pista: un brazo articulado de celular, un trípode con brazo horizontal, o un listón atornillado a la pared.

### 4. Configuración (`config.json`)
Ábrelo con el Bloc de notas y cambia solo esto:

| Dato | Qué poner |
|---|---|
| `camara` | La dirección de IP Webcam **+ `/photo.jpg`**, por ejemplo `http://192.168.1.50:8080/photo.jpg` |
| `camara_altura_mm` | Lo que mediste del lente a la cama, **en mm** (1 m = `1000`) |
| `cama_ancho_mm`, `cama_alto_mm` | El área de trabajo de tu láser. Viene en **1300 x 900**. Si la tuya es distinta, cámbiala y da doble clic en `0 GENERAR PATRON` |

Lo demás déjalo igual. `margen_mm` (4) es cuánto se separa la pieza del borde del retazo y `separacion_mm` (3)
cuánto se separan las piezas entre sí: súbelos si quieres más seguridad.

Ahora doble clic en **`2 PROBAR CAMARA.bat`**: abre una foto. Revisa que se vea **toda la cama** y que esté nítida.

### 5. Grabar el patrón de calibración (unos 10 minutos de láser)
1. Cubre la cama con **cartulina o cartón**, bien plano (con pesas en las esquinas si hace falta).
2. En **RDWorks**: Archivo → **Importar** (Ctrl+I) → `patron_calibracion.dxf`. **No lo muevas.**
3. Capas:
   - **Negra** → **Grabado (Scan)**, potencia baja y rápido (en cartulina: unos 300–400 mm/s y 10–15 %; haz
     una prueba chiquita antes). Intervalo 0,1–0,2 mm.
   - **Magenta** (el marco) → **Salida: No**. Es solo para que todo quede en su sitio.
4. Posición del trabajo: **Coordenadas absolutas** (en RDWorks: *Absolute coords* / *Coord. absoluta*).
   **Siempre** vas a usar esta misma opción, también al cortar.
5. Graba. Quedan **9 cuadros negros** tipo código QR.

### 6. Calibrar
Sin mover nada, doble clic en **`3 CALIBRAR (con el patron en la cama).bat`**.

- Debe decir **"calibrado con 9 de 9 marcadores"** y un **error promedio menor a 1 mm**.
- Abre `datos/calibracion_verificar.jpg`: los **cuadros rojos** deben caer justo encima de los marcadores.
- Si dice **ESPEJO**, tu láser graba volteado: el programa ya lo tiene en cuenta (la vista previa se verá
  volteada, igual que la ve RDWorks).

> **Guarda la cartulina del patrón**, pero si un día mueves el celular hay que **grabar un patrón nuevo**
> (poner la cartulina vieja "más o menos" en su sitio no sirve).

### 7. Foto de la cama vacía
Quita la cartulina, deja la cama **vacía y limpia**, y doble clic en **`4 FONDO (cama vacia).bat`**.
Repítelo si cambias la luz del taller o la rejilla.

### 8. Primera prueba (5 minutos)
1. Pon un **retazo de cartón** en cualquier parte de la cama.
2. Arrastra **`prueba_circulo_30mm.svg`** encima de **`5 ACOMODAR (arrastra aqui los SVG).bat`**.
3. Grosor: el del cartón. Copias: 3.
4. Abre el DXF de la carpeta `salida` en RDWorks (igual que el patrón: magenta en *Salida: No*, coordenadas
   absolutas) y córtalo.
5. **Los 3 círculos deben salir dentro del cartón**, a unos 4 mm del borde. Si quedan corridos, mira
   "Problemas" abajo.

---

## Uso de todos los días

1. Pon los retazos sobre la cama (pueden estar torcidos o tener huecos).
2. Arrastra el o los **SVG** de las piezas encima de **`5 ACOMODAR (arrastra aqui los SVG).bat`**.
   - Te pregunta el **grosor del material** (mm) y **cuántas copias** de cada pieza.
   - Para copias distintas por archivo, en una consola: `python laser_camara.py acomodar caja.svg=4 tapa.svg=2`
3. Se abre la **vista previa**: verde = retazos encontrados, rojo = piezas acomodadas. Revísala.
   Si dice que algunas **no cupieron**, pon más retazos y vuelve a correrlo.
4. En **RDWorks**: importa el DXF de `salida` (el de la hora más reciente) → **magenta en Salida: No** →
   capa roja = **corte**, azul = **grabado** → **coordenadas absolutas** → **no muevas el dibujo** → corta.

**Los SVG**: los de este proyecto sirven tal cual. Desde Corel: Archivo → Exportar → SVG.
Rojo o negro = corte, azul = grabado, verde y gris = no se usan. Las piezas que comparten una línea de corte
se acomodan juntas, como un bloque.

**Acrílico transparente sin papel, espejos o luz rara**: la cámara puede no verlos. Déjales el papel protector,
o usa **`6 ACOMODAR A MANO`**: clic en las esquinas de cada retazo, **Enter** para cerrarlo, **Q** para terminar.

---

## Reglas de oro

- **El celular no se puede mover.** Si se mueve (o lo bajas para usarlo): nuevo patrón → calibrar → fondo.
- **Siempre "coordenadas absolutas"** en RDWorks, y **nunca muevas el dibujo** después de importarlo.
- **Revisa la vista previa** antes de cortar.
- Un material grueso se ve más grande desde arriba: por eso pregunta el **grosor**. Pon el real.
- ⚠️ **Nunca cortes PVC, vinilo ni Celuka (espumado)**: sueltan cloro, que es tóxico y oxida la máquina.
- No dejes el láser solo y usa gafas si trabajas con la tapa abierta.

## Problemas

| Pasa esto | Haz esto |
|---|---|
| "no pude bajar la foto" | Celular y PC en el mismo wifi, IP Webcam con **Iniciar servidor**, la dirección bien escrita en `config.json` (termina en `/photo.jpg`). Si la IP del celular cambia, cámbiala en el config (o fíjala en el router). |
| "solo encontré N marcadores" | Más luz, foto nítida, que se vea toda la cama. Si el grabado quedó muy claro, grábalo más oscuro. |
| Error de calibración mayor a 1,5 mm | Patrón arrugado o celular movido durante la foto. Repite. |
| Encuentra "retazos" donde no hay nada | Cambió la luz: repite **4 FONDO**. Si sigue, sube `umbral` en el config (22 → 30). |
| No ve un retazo | Baja `umbral` (22 → 15), o usa **6 ACOMODAR A MANO**. |
| El corte sale corrido unos mm, siempre hacia el mismo lado | Revisa que RDWorks esté en **coordenadas absolutas** y que no moviste el dibujo. Si sigue: nuevo patrón y calibrar. |
| El corte sale bien en el centro y corrido en las orillas solo en material grueso | Mide de nuevo `camara_altura_mm`. |

---

## Para quien mire el código

- `laser_camara.py`: todo el programa. Calibración = homografía + distorsión radial del lente ajustadas con las
  36 esquinas de los 9 marcadores ArUco (4x4) que graba el láser; detecta grabado en espejo. Retazos = diferencia
  de color con la foto de la cama vacía, en la vista enderezada (1 px = 1 mm), con corrección por el grosor del
  material. Acomodo = búsqueda con `matchTemplate` sobre máscaras del retazo, piezas grandes primero, varias
  estrategias y gana la que más área mete. DXF R12 con un marco del tamaño de la cama.
- `prueba_simulada.py`: prueba completa sin cámara ni láser (fotos simuladas con perspectiva y lente, retazo con
  hueco y material de 12 mm). `python prueba_simulada.py` debe terminar con **0 errores**.
