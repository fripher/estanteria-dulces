# Prueba sin cámara ni láser: fabrica fotos de una cámara torcida (perspectiva + lente) con el patrón, la cama
# vacía y retazos encima (uno con hueco, uno grueso), corre todo el proceso y revisa que ninguna pieza se salga.
#   python prueba_simulada.py [piezas.svg]
import os, sys, tempfile, types
import numpy as np
import cv2
from shapely.geometry import Polygon, Point
from shapely.affinity import scale

tmp = tempfile.mkdtemp(prefix='camara_laser_')
os.environ['CAMARA_LASER_TRABAJO'] = tmp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import laser_camara as L

c = L.cfg()
c.update(camara='no-se-usa', camara_altura_mm=1000, grosor_patron_mm=1)
W, H = c['cama_ancho_mm'], c['cama_alto_mm']
K = 2                                                   # px por mm de la "cama" dibujada
FW, FH = 4000, 3000                                     # foto del celular
rng = np.random.default_rng(3)

# cámara: perspectiva + distorsión de lente (barril)
quad = np.float32([(420, 260), (3650, 330), (3560, 2700), (500, 2780)])
Hc = cv2.getPerspectiveTransform(np.float32([(0, 0), (W, 0), (W, H), (0, H)]), quad)
K1, cen = -0.06, np.array([FW / 2, FH / 2])


def fotografiar(cama_img, escala=None):
    """Cada píxel de la foto mira un punto de la cama (inverso de lente + perspectiva)."""
    u, v = np.meshgrid(np.arange(FW, dtype=np.float64), np.arange(FH, dtype=np.float64))
    d = (np.stack([u, v], -1) - cen) / FW
    r2 = (d ** 2).sum(-1, keepdims=True)
    q = cen + d * (1 + K1 * r2) * FW
    b = cv2.perspectiveTransform(q.reshape(-1, 1, 2), np.linalg.inv(Hc)).reshape(FH, FW, 2)
    if escala:                                          # material grueso: se ve más grande desde el nadir
        f, (nx, ny) = escala
        b = (b - (nx, ny)) * f + (nx, ny)
    m = (b * K).astype(np.float32)
    return cv2.remap(cama_img, m[..., 0], m[..., 1], cv2.INTER_LINEAR, borderValue=(40, 40, 40))


def lienzo(color):
    return np.full((H * K, W * K, 3), color, np.uint8)


def pintar(img, poly, color):
    cv2.fillPoly(img, [np.int32(np.array(poly.exterior.coords) * K)], color)
    for h in poly.interiors:
        cv2.fillPoly(img, [np.int32(np.array(h.coords) * K)], (0, 0, 0))
    return img


# 1. patrón grabado sobre cartulina
pat = lienzo((205, 225, 235))
for i, (x, y) in L.marcadores(c).items():
    g = L.poligono_marcador(i, x, y, c['marcador_mm'])
    for p in getattr(g, 'geoms', [g]):
        cv2.fillPoly(pat, [np.int32(np.array(p.exterior.coords) * K)], (25, 30, 40))
        for h in p.interiors:
            cv2.fillPoly(pat, [np.int32(np.array(h.coords) * K)], (205, 225, 235))
cv2.imwrite(os.path.join(tmp, 'f_patron.jpg'), fotografiar(pat))

# 2. cama vacía: rejilla de panal gris oscuro
cama = lienzo((70, 72, 75))
for yy in range(0, H * K, 14):
    for xx in range((yy // 14) % 2 * 7, W * K, 14):
        cv2.circle(cama, (xx, yy), 4, (45, 46, 48), -1)
cv2.imwrite(os.path.join(tmp, 'f_fondo.jpg'), fotografiar(cama))

# 3. retazos: MDF con hueco, acrílico con papel (claro), retazo chico
retazos = [Polygon([(60, 80), (640, 60), (700, 420), (90, 470)], [[(300, 200), (420, 200), (420, 300), (300, 300)]]),
           Polygon([(780, 120), (1240, 140), (1220, 560), (820, 520)]),
           Polygon([(150, 560), (520, 590), (480, 840), (170, 820)])]
colores = [(110, 160, 200), (215, 225, 220), (100, 150, 190)]
grosor = 12
c['_grosor'] = grosor
# lo que ve la cámara: la cara de arriba del material grueso (más cerca → más grande)
cal_nadir = None
foto_esc = cama.copy()
for p, col in zip(retazos, colores):
    pintar(foto_esc, p, col)
foto_esc = foto_esc.copy()
# nadir real: punto de la cama bajo el centro de la foto
nad = cv2.perspectiveTransform(np.array([[cen]], np.float64), np.linalg.inv(Hc)).ravel()
f = 1 - (grosor - c['grosor_patron_mm']) / c['camara_altura_mm']
esc = fotografiar(foto_esc, (f, nad))                   # mirar con f: el punto real b se ve en nadir+(b-nadir)/f
esc = np.clip(esc.astype(np.float32) * 0.96 + rng.normal(0, 3, esc.shape), 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(tmp, 'f_escaneo.jpg'), esc)

A = lambda **k: types.SimpleNamespace(**{'foto': None, 'piezas': [], 'grosor': None, 'copias': None,
                                         'manual': False, 'bloque': False, **k})
L.cfg = lambda: c
L.cmd_calibrar(c, A(foto=os.path.join(tmp, 'f_patron.jpg')))
L.cmd_fondo(c, A(foto=os.path.join(tmp, 'f_fondo.jpg')))
svg = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Caja de prueba 3mm.svg')
puestas, sobran, detectados = L.cmd_acomodar(c, A(foto=os.path.join(tmp, 'f_escaneo.jpg'), piezas=[svg],
                                                  grosor=grosor, copias=4))

# revisión contra los retazos reales
errores = 0
for d in detectados:
    real = max(retazos, key=lambda r: r.intersection(d).area)
    print(f'  retazo detectado vs real: diferencia de borde ≈ {d.symmetric_difference(real).area / real.length:.2f} mm')
for i, q in enumerate(puestas):
    dentro = [r for r in retazos if r.buffer(-(c['margen_mm'] - 1.5)).contains(q['forma'])]
    if not dentro:
        errores += 1
        print('  ERROR pieza', i, 'se sale del retazo o no respeta el margen')
    for j, o in enumerate(puestas[:i]):
        if q['forma'].distance(o['forma']) < c['separacion_mm'] - 0.5:
            errores += 1
            print('  ERROR piezas', j, i, 'muy juntas')
print(f'PRUEBA: {len(puestas)} piezas puestas, {len(sobran)} sin espacio, {errores} errores · archivos en {tmp}')
sys.exit(1 if errores else 0)
