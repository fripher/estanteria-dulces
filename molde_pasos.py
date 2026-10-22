# Dibuja paso a paso cómo se arma y se usa el molde para pegar las cajas → "Molde paso a paso.png"
import os, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import generar as G

t, W, D, B, j, tm = G.CAJA_T, G.CAJA_W, G.CAJA_D, G.MOLDE_BORDE, G.MOLDE_JUEGO, G.MOLDE_T
MDF = (0.80, 0.62, 0.42, 1.0)
MDF2 = (0.70, 0.52, 0.34, 1.0)
ACR = (0.62, 0.82, 0.97, 0.55)
TAPA = (0.45, 0.70, 0.95, 0.55)


def caja(x0, y0, z0, dx, dy, dz, color):
    x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    caras = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 3, 7, 4]]
    return [([v[i] for i in c], color) for c in caras]


def marco(z0, color=MDF):
    """Marco: 4 barras alrededor del hueco (caja por fuera + juego)."""
    hx0, hy0, hx1, hy1 = B - j, B - j, B + W + j, B + D + j
    X, Y = W + 2 * B, D + 2 * B
    return (caja(0, 0, z0, X, hy0, tm, color) + caja(0, hy1, z0, X, Y - hy1, tm, color) +
            caja(0, hy0, z0, hx0, hy1 - hy0, tm, color) + caja(hx1, hy0, z0, X - hx1, hy1 - hy0, tm, color))


def nucleo(z0, capas, sep=0.0, x=None, y=None):
    x = B + t if x is None else x
    y = B + t if y is None else y
    res = []
    for i in range(capas):
        res += caja(x + j, y + j, z0 + i * (tm + sep), W - 2 * t - 2 * j, D - 2 * t - 2 * j, tm, MDF if i % 2 == 0 else MDF2)
    return res


def paredes(z0, x=B, y=B, con_tapa=True):
    m = G.tapa_marco()
    res = caja(x, y, z0, W, D, t, ACR)                                     # base
    res += caja(x, y, z0 + t, t, D, G.CAJA_HB - t, ACR)                    # lado izq
    res += caja(x + W - t, y, z0 + t, t, D, G.CAJA_HB - t, ACR)            # lado der
    res += caja(x + t, y, z0 + t, W - 2 * t, t, G.CAJA_HF - t, ACR)        # frente
    res += caja(x + t, y + D - t, z0 + t, W - 2 * t, t, m['tras_h'] - t, ACR)   # atrás
    if con_tapa:
        a = m['ang']; L = m['largo']
        y0 = y - G.TAPA_VUELO; z_0 = z0 + m['y0']
        p0 = (x + m['x0'], y0, z_0); p1 = (x + m['x0'] + m['ancho'], y0, z_0)
        p2 = (p1[0], y0 + L * math.cos(a), z_0 + L * math.sin(a)); p3 = (p0[0], p2[1], p2[2])
        res.append(([p0, p1, p2, p3], TAPA))
    return res


def dibujar(ax, piezas, titulo, texto):
    ax.add_collection3d(Poly3DCollection([p for p, _ in piezas], facecolors=[c for _, c in piezas],
                                         edgecolors=(0.25, 0.18, 0.1, 0.6), linewidths=0.4))
    X, Y = W + 2 * B, D + 2 * B
    ax.set_xlim(0, X); ax.set_ylim(-20, Y + 20); ax.set_zlim(0, 260)
    ax.set_box_aspect((X, Y + 40, 260)); ax.view_init(24, -62); ax.set_axis_off()
    ax.set_title(titulo, fontsize=12, fontweight='bold', loc='left', color='#1b2a41')
    ax.text2D(0.0, -0.04, texto, transform=ax.transAxes, fontsize=9, va='top', color='#333', wrap=True)


pasos = [
    ('1. Marco', 'Pega las 2 piezas MARCO una encima de\notra (bordes parejos). El hueco mide\nexacto la caja por fuera.',
     marco(0)),
    ('2. Núcleo', 'Pega las 7 piezas NUCLEO una encima de\notra = un bloque de 6,3 cm. Mide exacto\nla caja por dentro. El hueco es para el dedo.',
     nucleo(0, 4, sep=12)),
    ('3. Base + núcleo', 'Pon cinta en marco y núcleo. Mete la BASE\nde acrílico en el hueco del marco y el\nnúcleo encima: queda una ranura de 3 mm.',
     marco(0) + caja(B, B, 0, W, D, t, ACR) + nucleo(t, 4)),
    ('4. Paredes en la ranura', 'Frente, atrás y un lado en la ranura;\nla tapa con sus orejitas en ese lado;\nluego el 2.º lado. Pega con cloroformo.',
     marco(0) + nucleo(t, 4) + paredes(0)),
    ('5. Sacar', 'A los 30 min saca la caja hacia arriba,\nabre la tapa y saca el núcleo con el dedo.\nLa caja sale recta y a escuadra.',
     marco(0) + paredes(95) + nucleo(110, 4, x=B + t, y=B + t)),
]
fig = plt.figure(figsize=(17, 4.6), dpi=110)
fig.suptitle('Molde para pegar las cajitas (MDF 12 mm) — haz 2 — cómo se arma y cómo se usa', fontsize=14, fontweight='bold', color='#1b2a41', x=0.02, ha='left')
for i, (tit, txt, pz) in enumerate(pasos):
    ax = fig.add_subplot(1, 5, i + 1, projection='3d')
    dibujar(ax, pz, tit, txt)
plt.subplots_adjust(left=0.01, right=0.99, top=0.86, bottom=0.18, wspace=0.02)
plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Molde paso a paso.png'), facecolor='white')
print('ok')
