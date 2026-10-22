# Arma la estantería en FRIPHER 3D ("Mis piezas de Corel").
#   python armar_fripher3d.py svg                     → "Estanteria ARMADO 3D.svg" (estructura + 12 cajas, sin textos)
#   python armar_fripher3d.py armado <export.txt> <nombre doc Corel>
#        lee lo que exporta modFripher3D.Exportar3D y escribe la posición exacta de cada pieza
#        en %LOCALAPPDATA%\FRIPHER 3D\armado.txt (mismo formato v2 que guarda el programa).
import math, os, sys
import numpy as np
import generar as G
from shapely.affinity import translate

aqui = os.path.dirname(os.path.abspath(__file__))
SEP = G.LAMINA[0] + 100.0   # las cajas van a la derecha de la estructura
ANCHO_SVG = SEP + G.LAMINA[0]


def colocadas():
    """Todas las piezas: las láminas de la estructura una debajo de otra y las cajas a la derecha."""
    est = G.estructura()
    cajaP, tapa = G.caja()
    res, dy = [], 0.0
    for c, col in G.laminas_estructura(est).items():
        for n, g, gr, (P, mo) in col:
            res.append((n, translate(g, 0, dy), [translate(e, 0, dy) for e in gr], P, ('M', mo), P.final))
        dy += max(g.bounds[3] for _, g, _, _ in col) + 100
    for n, g, gr, (P, b) in G.lamina_cajas(cajaP, tapa, G.caja_alta()):
        g = translate(g, SEP, 0); gr = [translate(e, SEP, 0) for e in gr]
        res.append((n, g, gr, P, b, tapa if P == 'TAPA' else P.final))
    return res


def svg():
    col = colocadas()
    W = ANCHO_SVG; H = max(c[1].bounds[3] for c in col) + 6
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="none" stroke="#B0B0B0" stroke-width="0.5"/>']
    # el color de la línea dice el material en FRIPHER 3D (es el color de cara de cada material)
    tono = {'mdf': '#26262C', 'opal': '#F2F2F4', 'transparente': '#AAD7F0'}
    for n, g, gr, P, b, src in col:
        mat = 'transparente' if b is not None and not isinstance(b, tuple) else G.color_de(P.nombre)
        out.append(G.svg_poligono(g, tono[mat], 0.5))
        for e in gr:
            out.append(G.svg_poligono(e, '#0000FF'))
    out.append('</svg>')
    open(os.path.join(aqui, 'Estanteria ARMADO 3D.svg'), 'w', encoding='utf-8').write(chr(10).join(out))


def ajuste(src, dst):
    """Matriz 2x2 que lleva los vértices de la pieza (u, v) a donde quedaron en el SVG."""
    a = np.array(src.exterior.coords[:-1]); b = np.array(dst.exterior.coords[:-1])
    a1 = np.hstack([a, np.ones((len(a), 1))])
    M, *_ = np.linalg.lstsq(a1, b, rcond=None)
    L = M[:2].T
    if np.abs(a1 @ M - b).max() > 0.05:
        raise SystemExit('no pude relacionar los vértices de una pieza')
    return np.round(L, 9)


def leer_export(ruta):
    formas, f = [], None
    lineas = open(ruta, encoding='latin-1').read().splitlines()
    i = 0
    while i < len(lineas):
        t = lineas[i].split()
        if t and t[0] == 'S':
            f = {'id': t[1], 'subs': []}; formas.append(f)
        elif t and t[0] == 'C':
            n = int(t[2]); pts = [tuple(map(float, lineas[i + 1 + j].split())) for j in range(n)]
            f['subs'].append(pts); i += n
        i += 1
    for f in formas:
        def area(p):
            return abs(sum(p[k][0] * p[k - 1][1] - p[k - 1][0] * p[k][1] for k in range(len(p)))) / 2
        borde = max(f['subs'], key=area)
        xs = [p[0] for p in borde]; ys = [p[1] for p in borde]
        f['caja'] = (min(xs), min(ys), max(xs), max(ys)); f['area'] = area(borde)
    return formas


def armado(ruta_export, doc):
    formas = leer_export(ruta_export)
    # piezas = formas que no quedan dentro de otra más grande (lo de adentro son grabados)
    formas.sort(key=lambda f: -f['area'])
    piezas = []
    for f in formas:
        x0, y0, x1, y1 = f['caja']
        if any(p['caja'][0] - 0.5 <= x0 and p['caja'][1] - 0.5 <= y0 and x1 <= p['caja'][2] + 0.5 and y1 <= p['caja'][3] + 0.5 for p in piezas):
            continue
        piezas.append(f)
    col = colocadas()
    # dónde quedó el SVG dentro de Corel: se ubica con el FONDO (la única de ANCHO x ALTO)
    sx0 = min(c[1].bounds[0] for c in col); sy0 = min(c[1].bounds[1] for c in col)
    cx0 = min(p['caja'][0] for p in piezas); cy1 = max(p['caja'][3] for p in piezas)
    ox = cx0 - sx0; oy = cy1 + sy0
    t = G.ESTRUCTURA_T
    xs = G.cajas_x()
    zfs = G.frentes()
    m = G.tapa_marco(); ca, sa = math.cos(m['ang']), math.sin(m['ang'])
    lineas, usadas = [], set()
    for n, g, gr, P, b, src in col:
        bx0, by0, bx1, by1 = g.bounds
        cx, cy = (bx0 + bx1) / 2 + ox, oy - (by0 + by1) / 2
        f = min(piezas, key=lambda p: math.hypot((p['caja'][0] + p['caja'][2]) / 2 - cx, (p['caja'][1] + p['caja'][3]) / 2 - cy))
        if math.hypot((f['caja'][0] + f['caja'][2]) / 2 - cx, (f['caja'][1] + f['caja'][3]) / 2 - cy) > 2 or f['id'] in usadas:
            raise SystemExit(f'no encontré en Corel la pieza {n}')
        usadas.add(f['id'])
        Lc = np.diag([1, -1]) @ ajuste(src, g)          # (u, v) de la pieza → (x, y) de Corel
        sb = src.bounds; uc, vc = (sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2
        # A: (u, v, w) locales → mundo FRIPHER 3D (X largo, Y fondo, Z alto)
        if P == 'TAPA':
            A = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]], float)
            o = np.array([m['x0'], m['z0'], m['y0']])
            wc = G.CAJA_T / 2
        else:
            A = {'x': np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], float),
                 'y': np.eye(3),
                 'z': np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], float)}[P.normal]
            o = np.zeros(3); wc = (P.rango[0] + P.rango[1]) / 2
        if isinstance(b, tuple):                       # pieza de estructura del módulo b[1]
            o = o + np.array([b[1] * G.ANCHO, 0, 0])
        elif b is not None:                            # caja número b
            mo, r = divmod(b, G.CAJAS_POR_PISO * len(G.PISOS_Y))
            k, i = divmod(r, G.CAJAS_POR_PISO)
            o = o + np.array([mo * G.ANCHO + xs[i], G.z_cajas(k), G.PISOS_Y[k]])
        centro = A @ np.array([uc, vc, wc]) + o
        B = np.eye(3); B[:2, :2] = np.linalg.inv(Lc)
        R = A @ B
        if np.linalg.det(R) < 0:
            R[:, 2] *= -1                                  # el grosor es simétrico: da igual hacia qué lado
        R = np.where(np.abs(R) < 1e-10, 0, R)
        datos = ['0', '1'] + [repr(float(v)) for v in centro] + [repr(float(v)) for v in R.flatten()]
        lineas.append(f'{doc}|{f["id"]}|v2 ' + ' '.join(datos))
    arch = os.path.join(os.environ['LOCALAPPDATA'], 'FRIPHER 3D', 'armado.txt')
    viejas = open(arch, encoding='utf-8').read().splitlines() if os.path.exists(arch) else []
    viejas = [l for l in viejas if not l.startswith(doc + '|')]
    os.makedirs(os.path.dirname(arch), exist_ok=True)
    open(arch, 'w', encoding='utf-8').write('\n'.join(viejas + lineas) + '\n')
    print(f'OK {len(lineas)} piezas armadas para «{doc}» ({len(piezas)} piezas en Corel)')


if __name__ == '__main__':
    if sys.argv[1] == 'svg':
        svg(); print('OK svg')
    else:
        armado(sys.argv[2], sys.argv[3])
