# Piso de arriba (piso 4): 2 cajas abiertas en las puntas + 9 torres cuadradas en el medio, todo de 17 cm,
# acrílico 3 mm pegado a tope (como las demás), en UNA lámina de 120 x 90 con corte en línea común.
import os, math
from shapely.geometry import box
import generar as G

aqui = os.path.dirname(os.path.abspath(__file__))
t = G.CAJA_T
ALTO = 170.0
CAJA = (190.0, 125.0)            # cajas de las puntas (galletas)
TORRE = (100.0, 100.0)           # torres (barquillos, pitillos, chupetas): por dentro 94 x 94 = ancho de un mug 11 oz
N_TORRES = 9
items = [('CAJA', *CAJA)] + [('TORRE', *TORRE)] * N_TORRES + [('CAJA', *CAJA)]
gap = (G.interior() - sum(w for _, w, _ in items)) / (len(items) + 1)


def abierta(W, D, H, tag):
    """Caja abierta pegada a tope: base completa, lados a todo el fondo, frente y atrás entre los lados."""
    pz = [('BASE', box(0, 0, W, D), [box(0, 0, W, D)] and []),
          ('LADO', box(0, 0, D, H - t), []), ('LADO', box(0, 0, D, H - t), []),
          ('FRENTE', box(0, 0, W - 2 * t, H - t), [box(8, 25, W - 2 * t - 8, 65)] if W > 150 else []),
          ('ATRAS', box(0, 0, W - 2 * t, H - t), [])]
    return [[(f'{n} {tag}', g, gr, None)] for n, g, gr in pz]


bloques, n_c, n_t = [], 0, 0
for tipo, w, d in items:
    if tipo == 'CAJA':
        n_c += 1; bloques += abierta(w, d, ALTO, f'C{n_c}')
    else:
        n_t += 1; bloques += abierta(w, d, ALTO, f'T{n_t}')
col = G.empacar(bloques, s=0)
hojas = max(int(g.bounds[1] // G.SALTO_HOJA) for _, g, _, _ in col) + 1
assert hojas == 1, 'no cabe en una lámina'
uso = sum(g.area for _, g, _, _ in col) / (G.LAMINA[0] * G.LAMINA[1]) * 100
G.escribir_svg(os.path.join(aqui, 'Corte acrilico 3mm PISO 4 (2 cajas + 9 torres).svg'), col,
               f'Piso 4: 2 cajas + {N_TORRES} torres, acrílico 3 mm', comun=True)
print(f'1 lámina, uso {uso:.0f}%, separación entre piezas del piso {gap:.1f} mm')

# dibujo de frente del piso 4 para ver cómo queda
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(14, 3.6), dpi=110)
x = gap
ax.add_patch(plt.Rectangle((-G.MDF_T, -10), G.interior() + 2 * G.MDF_T, 10, color='#cfe6f7'))
ax.add_patch(plt.Rectangle((-G.MDF_T, -10), G.MDF_T, 230, color='#222'))
ax.add_patch(plt.Rectangle((G.interior(), -10), G.MDF_T, 230, color='#222'))
ax.add_patch(plt.Rectangle((0, ALTO + 2), G.interior(), 200 - ALTO, color='#333', alpha=0.15))
for tipo, w, d in items:
    ax.add_patch(plt.Rectangle((x, 0), w, ALTO, fill=True, fc=(0.75, 0.88, 1, 0.5), ec='#4a7fb0', lw=1.2))
    if tipo == 'TORRE':
        for k in range(5):
            ax.plot([x + 18 + k * 15, x + 22 + k * 15], [20, ALTO + 45], color='#d9a441', lw=4, solid_capstyle='round')
        ax.text(x + w / 2, -28, 'torre\n10x10', ha='center', va='top', fontsize=8)
    else:
        ax.text(x + w / 2, ALTO / 2, 'galletas', ha='center', fontsize=9, color='#4a7fb0')
        ax.text(x + w / 2, -28, 'caja\n19x12,5', ha='center', va='top', fontsize=8)
    x += w + gap
ax.set_xlim(-60, G.interior() + 60); ax.set_ylim(-80, 260); ax.set_aspect('equal'); ax.axis('off')
ax.set_title(f'Piso de arriba visto de frente: 2 cajas + {N_TORRES} torres, todo de {ALTO / 10:g} cm (zona gris = fondo hasta 75 cm)', fontsize=11)
plt.tight_layout(); plt.savefig(os.path.join(aqui, 'Piso 4 de frente.png'))
