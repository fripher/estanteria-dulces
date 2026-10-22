# Piso de arriba (piso 4): 2 cajas abiertas en las puntas + 9 TORRES SUELTAS en el medio, todo de 17 cm.
# Las torres no se pegan: entran en los huecos de una "base portatorres" de acrílico 5 mm pegada al piso
# (no se corren ni se voltean, y se sacan para lavarlas).
#   - lámina 120 x 90 de acrílico 3 mm: 2 cajas + 9 torres (corte en línea común)
#   - retazo de acrílico 5 mm: la base portatorres
import os
from shapely.geometry import box
import generar as G

aqui = os.path.dirname(os.path.abspath(__file__))
t = G.CAJA_T
ALTO = 170.0
CAJA = (190.0, 125.0)            # cajas de las puntas (galletas)
TORRE = 100.0                    # torre cuadrada: por dentro 94 x 94 (ancho de un mug de 11 oz)
N = 9
items = [('CAJA', CAJA[0])] + [('TORRE', TORRE)] * N + [('CAJA', CAJA[0])]
GAP = (G.interior() - sum(w for _, w in items)) / (len(items) + 1)
JUEGO = 0.3                      # holgura por lado del hueco (más la quema del láser) para que la torre entre suave
MARGEN_FRENTE = 6.0              # material delante de los huecos de la base portatorres


def abierta(W, D, H, tag, grabado=False):
    pz = [('BASE', box(0, 0, W, D), []),
          ('LADO', box(0, 0, D, H - t), []), ('LADO', box(0, 0, D, H - t), []),
          ('FRENTE', box(0, 0, W - 2 * t, H - t), [box(8, 25, W - 2 * t - 8, 65)] if grabado else []),
          ('ATRAS', box(0, 0, W - 2 * t, H - t), [])]
    return [[(f'{n} {tag}', g, gr, None)] for n, g, gr in pz]


def portatorres():
    """Placa de 5 mm con un hueco por torre. Va de la mitad del espacio junto a una caja a la mitad del otro."""
    largo = N * TORRE + N * GAP
    fondo = CAJA[1]
    placa = box(0, 0, largo, fondo)
    x = GAP / 2
    for _ in range(N):
        placa = placa.difference(box(x - JUEGO, MARGEN_FRENTE - JUEGO, x + TORRE + JUEGO, MARGEN_FRENTE + TORRE + JUEGO))
        x += TORRE + GAP
    return placa


for f in os.listdir(aqui):
    if f.startswith('Corte acrilico 3mm PISO 4') or f.startswith('Corte acrilico 5mm PISO 4'):
        os.remove(os.path.join(aqui, f))

# lámina de 3 mm
bloques = abierta(*CAJA, ALTO, 'C1', True) + abierta(*CAJA, ALTO, 'C2', True)
for i in range(N):
    bloques += abierta(TORRE, TORRE, ALTO, f'T{i + 1}')
col = G.empacar(bloques, s=0)
assert max(int(g.bounds[1] // G.SALTO_HOJA) for _, g, _, _ in col) == 0, 'no cabe en una lámina'
uso = sum(g.area for _, g, _, _ in col) / (G.LAMINA[0] * G.LAMINA[1]) * 100
G.escribir_svg(os.path.join(aqui, 'Corte acrilico 3mm PISO 4 (2 cajas + 9 torres sueltas).svg'), col,
               'Piso 4: 2 cajas + 9 torres, acrílico 3 mm', comun=True)

# base portatorres en 5 mm (retazo)
placa = portatorres()
W5, H5 = placa.bounds[2] + 20, placa.bounds[3] + 20
from shapely.affinity import translate, scale as sscale
pg = translate(sscale(placa, 1, -1, origin=(0, 0)), 10, placa.bounds[3] + 10)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W5:.1f}mm" height="{H5:.1f}mm" viewBox="0 0 {W5:.1f} {H5:.1f}">',
       f'<rect x="0" y="0" width="{W5:.1f}" height="{H5:.1f}" fill="none" stroke="#B0B0B0" stroke-width="0.5"/>',
       G.svg_poligono(pg, '#FF0000'),
       f'<text x="{W5 / 2:.1f}" y="{H5 - 3:.1f}" text-anchor="middle" font-family="Arial" font-size="6" fill="#00A000">BASE PORTATORRES - acrilico cristal 5 mm (retazo)</text>',
       '</svg>']
open(os.path.join(aqui, 'Corte acrilico 5mm PISO 4 base portatorres.svg'), 'w', encoding='utf-8').write('\n'.join(svg))
print(f'3 mm: 1 lámina, uso {uso:.0f}% · separación {GAP:.1f} mm · portatorres 5 mm: {placa.bounds[2]:.1f} x {placa.bounds[3]:.1f} mm (retazo {W5 / 10:.1f} x {H5 / 10:.1f} cm)')

# dibujos: de frente y desde arriba
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, (a1, a2) = plt.subplots(2, 1, figsize=(14, 6.4), dpi=110, gridspec_kw={'height_ratios': [1.6, 1]})
for a in (a1, a2):
    for x0 in (-G.MDF_T, G.interior()):
        a.add_patch(plt.Rectangle((x0, -10), G.MDF_T, 230 if a is a1 else 145, color='#222'))
a1.add_patch(plt.Rectangle((0, -10), G.interior(), 10, color='#cfe6f7'))
a1.add_patch(plt.Rectangle((0, ALTO + 2), G.interior(), 200 - ALTO, color='#333', alpha=0.15))
x = GAP
x_placa = None
for tipo, w in items:
    if tipo == 'TORRE' and x_placa is None:
        x_placa = x - GAP / 2
    a1.add_patch(plt.Rectangle((x, 0), w, ALTO, fc=(0.75, 0.88, 1, 0.5), ec='#4a7fb0', lw=1.2))
    if tipo == 'TORRE':
        for j in range(5):
            a1.plot([x + 14 + j * 16, x + 18 + j * 16], [20, ALTO + 45], color='#d9a441', lw=4, solid_capstyle='round')
        a2.add_patch(plt.Rectangle((x, MARGEN_FRENTE), w, w, fc=(0.75, 0.88, 1, 0.6), ec='#4a7fb0'))
    else:
        a1.text(x + w / 2, ALTO / 2, 'galletas', ha='center', fontsize=9, color='#4a7fb0')
        a2.add_patch(plt.Rectangle((x, 0), w, CAJA[1], fc=(0.75, 0.88, 1, 0.6), ec='#4a7fb0'))
    x += w + GAP
a1.add_patch(plt.Rectangle((x_placa, 0), N * (TORRE + GAP), 5, color='#7fb8e8'))
pl = translate(placa, x_placa, 0)
for r in [pl.exterior, *pl.interiors]:
    a2.plot(*r.xy, color='#d62728', lw=1)
a1.set_title(f'De frente: 2 cajas + 9 torres SUELTAS de {ALTO / 10:g} cm (franja azul = base portatorres 5 mm)', fontsize=10)
a2.set_title('Desde arriba: cada torre entra en su hueco de la base portatorres (rojo), pegada al piso', fontsize=10)
for a in (a1, a2):
    a.set_xlim(-40, G.interior() + 40); a.set_aspect('equal'); a.axis('off')
a1.set_ylim(-20, 260); a2.set_ylim(-15, 140)
plt.tight_layout(); plt.savefig(os.path.join(aqui, 'Piso 4 de frente.png'))
