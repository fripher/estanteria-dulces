# Un solo archivo con TODO lo que hay que cortar, ordenado en columnas por material y calibre:
#   MDF 9 mm (negro, se forra con vinilo) · MDF 12 mm (moldes) · acrílico 5 mm · acrílico 3 mm (+ caja de prueba)
# Cada lámina de 120 x 90 con su marco gris; títulos dentro del marco general para que Corel no cambie la escala.
import glob, re, os
import generar as G

aqui = os.path.dirname(os.path.abspath(__file__))
W, H = G.LAMINA
SALTO_X, SALTO_Y, CAB = W + 250, H + 120, 260      # separación entre columnas / láminas, alto del título

columnas = [
    ('MDF 12 mm  ·  NEGRO (vinilo)', 'Corte MDF 12mm costados*', 'costados, fondo, zócalo y base'),
    ('ACRÍLICO CRISTAL 5 mm', 'Corte acrilico 5mm*', 'pisos, contrahuellas, topes y soporte'),
]


def cuerpo(f):
    s = open(f, encoding='utf-8').read()
    w = float(re.search(r'width="([\d.]+)mm"', s).group(1)); h = float(re.search(r'height="([\d.]+)mm"', s).group(1))
    s = re.sub(r'^<svg[^>]*>', '', s).replace('</svg>', '')
    s = re.sub(r'<title>.*?</title>', '', s)
    return s, w, h


out, alto = [], 0
for c, (titulo, patron, detalle) in enumerate(columnas):
    hojas = sorted(glob.glob(os.path.join(aqui, patron + '.svg')))
    extra = []
    x = 60 + c * SALTO_X
    out.append(f'<text x="{x}" y="120" font-family="Arial" font-weight="bold" font-size="60" fill="#333333">{titulo}</text>')
    out.append(f'<text x="{x}" y="200" font-family="Arial" font-size="42" fill="#666666">{len(hojas)} lámina(s) de 120 x 90  ·  {detalle}</text>')
    y = CAB
    for i, f in enumerate(hojas + extra):
        s, w, h = cuerpo(f)
        nombre = f'LÁMINA {i + 1} de {len(hojas)}' if i < len(hojas) else 'CAJA DE PRUEBA (retazo)'
        out.append(f'<text x="{x}" y="{y - 20}" font-family="Arial" font-size="36" fill="#00A000">{nombre}</text>')
        out.append(f'<g transform="translate({x},{y})">{s}</g>')
        y += h + 120 if h < H else SALTO_Y
    alto = max(alto, y)
ancho = 60 + len(columnas) * SALTO_X
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}mm" height="{alto}mm" viewBox="0 0 {ancho} {alto}">',
       f'<rect x="0" y="0" width="{ancho}" height="{alto}" fill="none" stroke="#B0B0B0" stroke-width="1"/>'] + out + ['</svg>']
open(os.path.join(aqui, 'TODO PARA CORTAR.svg'), 'w', encoding='utf-8').write('\n'.join(svg))
print(f'OK {ancho:.0f} x {alto:.0f} mm')
