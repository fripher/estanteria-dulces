# Piso 4 en KITS para cortar en retazos: cada torre, cada caja y cada tramo de la base portatorres en su
# propio cuadro, con el tamaño mínimo de retazo. Dentro de cada kit las piezas van pegadas (línea común).
import os
from shapely.geometry import box
from shapely.affinity import translate, scale as sscale
from shapely.ops import unary_union
import generar as G
import piso4 as P4

aqui = os.path.dirname(os.path.abspath(__file__))
t, H = P4.t, P4.ALTO


def kit_compacto(bloques):
    """Prueba varios anchos y deja el acomodo de menor área (rectángulo más pequeño)."""
    mejor = None
    for ancho in range(220, 760, 10):
        col = G.empacar(bloques, ancho=ancho, m=0, s=0)
        if any(int(g.bounds[1] // G.SALTO_HOJA) for _, g, _, _ in col):
            continue
        x0, y0, x1, y1 = unary_union([g for _, g, _, _ in col]).bounds
        if mejor is None or (x1 - x0) * (y1 - y0) < mejor[0]:
            mejor = ((x1 - x0) * (y1 - y0), col, x1 - x0, y1 - y0)
    return mejor[1], mejor[2], mejor[3]


kits = []
for i in range(2):
    col, w, h = kit_compacto(P4.abierta(*P4.CAJA, H, f'C{i + 1}', True))
    kits.append((f'CAJA GALLETAS {i + 1}  ·  acrílico 3 mm', col, w, h))
for i in range(P4.N):
    col, w, h = kit_compacto(P4.abierta(P4.TORRE, P4.TORRE, H, f'T{i + 1}'))
    kits.append((f'TORRE {i + 1}  ·  acrílico 3 mm', col, w, h))
# por si alguna torre sale de retazo de 2 mm: misma medida por fuera (10 x 10), paredes de 2 mm (cópiala las veces que necesites)
P4.t = 2.0
col, w, h = kit_compacto(P4.abierta(P4.TORRE, P4.TORRE, H, 'T 2mm'))
kits.append(('TORRE VERSIÓN 2 mm (cópiala si la necesitas)  ·  acrílico 2 mm', col, w, h))
P4.t = 3.0
# (sin base portatorres: el cliente no la quiere; las torres van sueltas detrás del tope)

# acomodar los kits en una hoja grande (no es una lámina: cada kit se lleva a su retazo)
MARGEN, CAB, ANCHO_HOJA = 15, 22, 2000
out, x, y, fila = [], 20, 20, 0
for titulo, col, w, h in kits:
    W, Hk = w + 2 * MARGEN, h + 2 * MARGEN + CAB
    if x + W > ANCHO_HOJA - 20:
        x, y, fila = 20, y + fila + 30, 0
    x0 = min(g.bounds[0] for _, g, _, _ in col); y0 = min(g.bounds[1] for _, g, _, _ in col)
    geos = [translate(g, x + MARGEN - x0, y + MARGEN + CAB - y0) for _, g, _, _ in col]
    grs = [translate(e, x + MARGEN - x0, y + MARGEN + CAB - y0) for _, _, gr, _ in col for e in gr]
    out.append(f'<rect x="{x}" y="{y}" width="{W:.1f}" height="{Hk:.1f}" fill="none" stroke="#B0B0B0" stroke-width="0.6"/>')
    out.append(f'<text x="{x + 6}" y="{y + 11}" font-family="Arial" font-size="8" fill="#00A000">{titulo}</text>')
    out.append(f'<text x="{x + 6}" y="{y + 19}" font-family="Arial" font-size="7" fill="#00A000">retazo mínimo {w / 10 + 0.4:.1f} x {h / 10 + 0.4:.1f} cm</text>')
    for a, b in [s for s in []]:
        pass
    for tr in G.encadenar(G.lineas_comunes(geos)):
        out.append('<path d="M' + ' L'.join(f'{px:.3f},{py:.3f}' for px, py in tr) + '" fill="none" stroke="#FF0000" stroke-width="0.01"/>')
    for e in grs:
        out.append(G.svg_poligono(e, '#0000FF'))
    x += W + 30; fila = max(fila, Hk)
alto = y + fila + 20
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO_HOJA}mm" height="{alto:.1f}mm" viewBox="0 0 {ANCHO_HOJA} {alto:.1f}">',
       f'<rect x="0" y="0" width="{ANCHO_HOJA}" height="{alto:.1f}" fill="none" stroke="#B0B0B0" stroke-width="1"/>'] + out + ['</svg>']
open(os.path.join(aqui, 'PISO 4 kits para retazos.svg'), 'w', encoding='utf-8').write('\n'.join(svg))
for titulo, col, w, h in kits:
    print(f'{titulo}: retazo mínimo {w / 10 + 0.4:.1f} x {h / 10 + 0.4:.1f} cm')
print(f'hoja {ANCHO_HOJA} x {alto:.0f} mm')
