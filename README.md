# Estantería de dulces en acrílico + MDF (corte láser)

Generador paramétrico de una estantería escalonada para dulces de 140 x 60 x 75 cm:
4 pisos, estructura de MDF 12 mm (costados, fondo y zócalo) y acrílico cristal 5 mm
(pisos, contrahuellas, topes y soporte central), con cajas de acrílico 3 mm con tapa
y bisagra integrada.

- `generar.py`: arma todas las piezas, los encajes (dedos y pestañas), las verifica en 3D
  y saca los SVG de corte por material, acomodados en láminas de 120 x 90 cm.
- `piso4.py` / `piso4_kits.py`: piso de arriba (2 cajas abiertas + 9 torres) y kits para retazos.
- `juntar_corel.py`, `juntar_todo.py`: juntan las láminas por material / en un solo archivo.
- `molde_pasos.py`: dibujo del molde para pegar las cajas.
- `protectores_3d.py`: piezas STL opcionales (esquineros, cantos en U).
- `armar_fripher3d.py`, `poner_cdr.py`, `poner_todo.ps1`: integración con CorelDRAW (solo Windows).

Medidas en mm. Colores en los SVG: rojo = corte, azul = grabado, verde = nombres (no se cortan).

## Puente nube ↔ PC (`puente/`)

Para trabajar desde una sesión en la nube con CorelDRAW en el PC. GitHub hace de buzón:
la nube deja órdenes en `puente/ordenes/` y `puente/puente_pc.py` (en el PC) las revisa cada 30 s,
las ejecuta y sube el resultado a `puente/resultados/`.

- Solo hace las acciones de la lista `ACCIONES` (ping, documentos, listar_vectores, importar_svg,
  abrir_cdr, exportar_png, captura_corel, poner_todo). Nunca comandos libres ni el láser.
- Solo toca documentos que empiezan por `Estanteria 140 - ` y SVG que están dentro del repo.
- Si el repo es público no sube capturas de pantalla.
- Encender en el PC: doble clic en `puente/INICIAR PUENTE.bat` (deja la ventana abierta).
- Mandar una orden desde la nube: `python puente/orden.py ping`, luego commit y push;
  ver el resultado: `git pull` y `python puente/orden.py --ver`.
