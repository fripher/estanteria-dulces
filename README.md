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
