# Estantería de dulces en acrílico — generador de piezas para corte láser.
# Todas las medidas en mm. Cambia ESTRUCTURA_T / CAJA_T por el grosor REAL medido con calibrador
# y vuelve a correr:  python generar.py   → SVG para Corel + vista 3D + verificación de encajes.
import math, random, sys
from shapely.geometry import box, Polygon, Point
from shapely.affinity import rotate, translate, scale as sscale
from shapely.ops import unary_union
from shapely import set_precision

ESTRUCTURA_T = 5.0      # acrílico de la estructura (costados, pisos, contrahuellas, fondo, topes)
CON_BASE = False        # base de MDF abajo: no hace falta (patas 3D levantan el mueble); True para ponerla
MDF_T = 12.0            # MDF (normal, sellado y forrado en vinilo) de costados, fondo, zócalo y base
CAJA_T = 3.0            # acrílico de las cajas dispensadoras
ANCHO_TOTAL, FONDO, ALTO = 1400.0, 600.0, 750.0
MODULOS = 1                      # una sola estantería; las piezas largas van en dos mitades sobre el soporte central
ANCHO = ANCHO_TOTAL / MODULOS    # ancho de UN módulo
PISOS_Y = [75.0, 235.0, 395.0, 550.0]   # altura de la cara superior de cada piso (4 pisos)
PASO = 150.0                     # profundidad de cada escalón (FONDO / número de pisos)
BARANDA = 30.0                   # cuánto sube el costado por encima de cada piso
TOPE_H = 15.0                    # tope frontal transparente, bajito para no tapar las cajas
CAJAS_POR_PISO = 7               # 7 por piso = 28 cajas (más anchas)
CAJA_W, CAJA_D, CAJA_HF, CAJA_HB, CAJA_FONDO_H = 190.0, 125.0, 95.0, 120.0, 125.0
CAJA_ALTA_H = 200.0              # las del último piso: más altas y sin tapa (llegan justo a ALTO)
TAPA_VUELO = 12.0                # la tapa sobresale adelante para levantarla con el dedo
LAMINA = (1200.0, 900.0)         # lámina de 120 x 90 cm (cabe en la cama del láser de 130 x 90)


def frentes():
    """z de la cara frontal de cada piso (el primero arranca adelante, los demás sobre su contrahuella)."""
    return [0.0] + [k * PASO - ESTRUCTURA_T for k in range(1, len(PISOS_Y))]


class Pieza:
    """Placa plana: eje normal, rango en ese eje y polígono en los otros dos ejes."""
    EJES2D = {'x': ('z', 'y'), 'y': ('x', 'z'), 'z': ('x', 'y')}

    def __init__(self, nombre, normal, rango, poly, prio, t):
        self.nombre, self.normal, self.rango, self.poly, self.prio, self.t = nombre, normal, rango, poly, prio, t
        self.cortes, self.agujeros, self.grabados = [], [], []
        self.lado = 'I' if nombre.endswith(' IZQ') else 'D' if nombre.endswith(' DER') else None
        self.final = None

    def rect(self, lim):
        (a, b) = self.EJES2D[self.normal]
        return box(lim[a][0], lim[b][0], lim[a][1], lim[b][1])

    def tramo(self, eje, rng):
        """Intervalo del polígono en el otro eje, restringido a eje∈rng."""
        (a, b) = self.EJES2D[self.normal]
        big = 1e5
        lim = {eje: rng}
        otro = b if eje == a else a
        lim[otro] = (-big, big)
        inter = self.poly.intersection(self.rect(lim)).buffer(0)     # sin líneas ni puntos sueltos
        if inter.is_empty or inter.area <= 1e-9:
            return None
        x0, y0, x1, y1 = inter.bounds
        return (x0, x1) if otro == a else (y0, y1)

    def contiene(self, p):
        if not (self.rango[0] < p[self.normal] < self.rango[1]):
            return False
        (a, b) = self.EJES2D[self.normal]
        return self.final.contains(Point(p[a], p[b]))


# Solo estas piezas llevan encajes (dedos); entre las demás (acrílico con acrílico) la unión es a tope, pegada
CON_DEDOS = ('COSTADO', 'FONDO', 'DIVISOR', 'BASE')


def unir(piezas, ancho_dedo):
    """Encajes tipo dedo/caja entre cada par de placas perpendiculares que se cruzan."""
    for i, A in enumerate(piezas):
        for B in piezas[i + 1:]:
            if A.normal == B.normal or 'DIVISOR' in (A.nombre, B.nombre):
                continue
            if A.lado and B.lado and A.lado != B.lado and not A.nombre.startswith('COSTADO') and not B.nombre.startswith('COSTADO'):
                continue                      # mitades distintas: solo se tocan dentro del divisor
            c = ({'x', 'y', 'z'} - {A.normal, B.normal}).pop()
            ia, ib = A.tramo(B.normal, B.rango), B.tramo(A.normal, A.rango)
            if not ia or not ib:
                continue
            c0, c1 = max(ia[0], ib[0]), min(ia[1], ib[1])
            if c1 - c0 <= 1e-6:
                continue
            if c == 'x' and (A.lado or B.lado):
                xd0, xd1 = divisor_x()
                if 'I' in (A.lado, B.lado) and not (A.nombre.startswith('COSTADO') or B.nombre.startswith('COSTADO')):
                    c1 = min(c1, xd0)
                if 'D' in (A.lado, B.lado) and not (A.nombre.startswith('COSTADO') or B.nombre.startswith('COSTADO')):
                    c0 = max(c0, xd1)
                if c1 - c0 <= 1e-6:
                    continue
            n = max(3, int(round((c1 - c0) / ancho_dedo)))
            if n % 2 == 0:
                n += 1
            if not any(p.nombre.startswith(CON_DEDOS) for p in (A, B)):
                n = 1                         # a tope (pegado): la pieza de más prioridad se queda la esquina
            alto, bajo = (A, B) if A.prio > B.prio else (B, A)
            s = (c1 - c0) / n
            for k in range(n):
                seg = (c0 + k * s, c0 + (k + 1) * s)
                duenio, pierde = (alto, bajo) if k % 2 == 0 else (bajo, alto)
                pierde.cortes.append(pierde.rect({duenio.normal: duenio.rango, c: seg}))
    # divisor central: cada tramo se reparte entre divisor, mitad izquierda y mitad derecha (D, I, D, R, D...)
    D = next((p for p in piezas if p.nombre == 'DIVISOR'), None)
    if D:
        for I in [p for p in piezas if p.lado == 'I' and not p.nombre.startswith('COSTADO')]:
            R = next(p for p in piezas if p.nombre == I.nombre[:-4] + ' DER')
            c = ({'x', 'y', 'z'} - {'x', I.normal}).pop()
            ia, idv = I.tramo('x', D.rango), D.tramo(I.normal, I.rango)
            if not ia or not idv:
                continue
            c0, c1 = max(ia[0], idv[0]), min(ia[1], idv[1])
            if c1 - c0 <= 1e-6:
                continue
            n = max(5, int(round((c1 - c0) / ancho_dedo)))
            while n % 4 != 1:
                n += 1
            s = (c1 - c0) / n
            for k in range(n):
                seg = (c0 + k * s, c0 + (k + 1) * s)
                duenio = {0: D, 1: I, 2: D, 3: R}[k % 4]
                for p in (I, R):
                    if p is not duenio:
                        p.cortes.append(p.rect({'x': D.rango, c: seg}))
                if duenio is not D:
                    D.cortes.append(D.rect({I.normal: I.rango, c: seg}))
    for P in piezas:
        f = P.poly.difference(unary_union(P.cortes)) if P.cortes else P.poly
        for h in P.agujeros:
            f = f.difference(h)
        P.final = set_precision(f, 0.001)
        if P.final.geom_type != 'Polygon':
            sys.exit(f'ERROR {P.nombre} quedó partida en pedazos: {P.final.geom_type}')


def verificar(piezas, paso=0.5):
    """Cada punto de cada zona de unión debe pertenecer a UNA sola pieza (sin huecos ni choques)."""
    malos = 0
    for i, A in enumerate(piezas):
        for B in piezas[i + 1:]:
            if A.normal == B.normal:
                continue
            c = ({'x', 'y', 'z'} - {A.normal, B.normal}).pop()
            ia, ib = A.tramo(B.normal, B.rango), B.tramo(A.normal, A.rango)
            if not ia or not ib:
                continue
            c0, c1 = max(ia[0], ib[0]), min(ia[1], ib[1])
            if c1 - c0 <= 1e-6:
                continue
            def rango(r, st):
                v = r[0] + st * 0.37                 # nunca justo en un borde
                while v < r[1]:
                    yield v
                    v += st
            for va in rango(A.rango, paso):
                for vb in rango(B.rango, paso):
                    for vc in rango((c0, c1), 1.0):
                        p = {A.normal: va, B.normal: vb, c: vc}
                        if not (A.poly.contains(Point(*[p[e] for e in Pieza.EJES2D[A.normal]])) and
                                B.poly.contains(Point(*[p[e] for e in Pieza.EJES2D[B.normal]]))):
                            continue
                        n = sum(1 for P in piezas if P.contiene(p))
                        if n == 0 and any(f[0] < p[e] < f[1] for e, f in REBAJES):
                            continue                  # hueco de 4 mm a propósito (se rellena con masilla)
                        if n != 1:
                            malos += 1
                            if malos < 6:
                                print(f'  ! punto {p} está en {n} piezas ({A.nombre} / {B.nombre})')
    # choques fuera de las uniones: muestreo aleatorio
    xs = [min(P.final.bounds[0] for P in piezas)]
    rnd = random.Random(1)
    lo = {e: min(P.rango[0] if P.normal == e else P.final.bounds[Pieza.EJES2D[P.normal].index(e)] for P in piezas) for e in 'xyz'}
    hi = {e: max(P.rango[1] if P.normal == e else P.final.bounds[Pieza.EJES2D[P.normal].index(e) + 2] for P in piezas) for e in 'xyz'}
    for _ in range(60000):
        p = {e: rnd.uniform(lo[e], hi[e]) for e in 'xyz'}
        if sum(1 for P in piezas if P.contiene(p)) > 1:
            malos += 1
    return malos


# ---------------------------------------------------------------- ESTRUCTURA (con empates)
COLOR = {'COSTADO': 'mdf', 'FONDO': 'mdf', 'ZOCALO': 'mdf', 'BASE': 'mdf',          # MDF (negro): solo costados, fondo y zócalo
         'DIVISOR': 'transparente', 'CONTRAHUELLA': 'transparente', 'PISO': 'transparente', 'TOPE': 'transparente'}


def espesor_de(color):
    return MDF_T if color == 'mdf' else ESTRUCTURA_T


def color_de(nombre):
    return next(v for k, v in COLOR.items() if nombre.startswith(k))


def perfil_costado():
    """Costado con una sola diagonal (como la foto): pasa por encima de cada piso + BARANDA."""
    zf = frentes()
    y0, y1 = PISOS_Y[0] + BARANDA, PISOS_Y[-1] + BARANDA
    m = (y1 - y0) / zf[-1]
    falta = max(PISOS_Y[k] + BARANDA - (y0 + m * zf[k]) for k in range(len(PISOS_Y)))
    b = y0 + max(0.0, falta)
    return Polygon([(0, 0), (FONDO, 0), (FONDO, b + m * zf[-1]), (zf[-1], b + m * zf[-1]), (0, b)])


def interior():
    """Ancho libre entre los costados de MDF."""
    return ANCHO - 2 * MDF_T


def divisor_x():
    """Caras del soporte central (x de 0 a interior() es el espacio entre costados)."""
    t = ESTRUCTURA_T
    xi1 = interior()
    return xi1 / 2 - t / 2, xi1 / 2 + t / 2


def cajas_x():
    """x de cada caja de un piso: repartidas parejo a todo lo largo (el soporte no se ve por encima)."""
    gap = (interior() - CAJAS_POR_PISO * CAJA_W) / (CAJAS_POR_PISO + 1)
    return [gap + i * (CAJA_W + gap) for i in range(CAJAS_POR_PISO)]


def z_tope(k):
    """Cara delantera del tope del piso k (el del piso 1 queda detrás del zócalo de MDF)."""
    return frentes()[k] + 8.0          # el zócalo va debajo del piso: el tope no choca con él


def z_cajas(k):
    """Dónde empiezan las cajas del piso k (detrás del tope)."""
    return z_tope(k) + ESTRUCTURA_T + 2


def perfil_soporte():
    """Soporte central transparente: solo debajo de los escalones, al ras de cada piso."""
    zf = frentes()
    pts = [(0, 0)]
    for k, yk in enumerate(PISOS_Y):
        pts += [(zf[k], yk), (zf[k + 1] if k + 1 < len(PISOS_Y) else FONDO, yk)]
    pts += [(FONDO, 0)]
    return Polygon(pts)


def estructura():
    """Una sola estantería: costados negros en las puntas y un soporte transparente en la mitad.
    Pisos y fondo van en dos mitades que se traban dentro del soporte; contrahuellas y zócalo llegan
    a su cara; los topes se juntan al centro, encima del soporte."""
    t = ESTRUCTURA_T                          # acrílico
    tm = MDF_T                                # MDF
    xi1 = interior()                          # interior entre costados
    xd0, xd1 = divisor_x()
    xm = xi1 / 2
    n = len(PISOS_Y)
    zf = frentes()
    y4 = PISOS_Y[-1]
    P = []
    perfil = perfil_costado()
    P.append(Pieza('COSTADO IZQ', 'x', (-tm, 0), perfil, 9, tm))
    P.append(Pieza('COSTADO DER', 'x', (xi1, xi1 + tm), perfil, 9, tm))
    P.append(Pieza('DIVISOR', 'x', (xd0, xd1), perfil_soporte(), 9, t))
    for lado, Xp, Xc, Xt in ((' IZQ', (-tm, xd1), (-tm, xd0), (-tm, xm)), (' DER', (xd0, xi1 + tm), (xd1, xi1 + tm), (xm, xi1 + tm))):
        # Xp: atraviesa el soporte · Xc: llega a la cara del soporte · Xt: llega al centro
        fondo = box(Xp[0], 0, Xp[1], y4).union(box(Xt[0], y4 - 1, Xt[1], ALTO))
        P.append(Pieza('FONDO' + lado, 'z', (FONDO - tm, FONDO), fondo, 8, tm))
        # base de MDF por dentro (entre costados, fondo y zócalo): la estantería sigue midiendo ALTO
        if CON_BASE:
            P.append(Pieza('BASE' + lado, 'y', (0, tm), box(Xp[0], 0, Xp[1], FONDO), 7.5, tm))
        for k, yk in enumerate(PISOS_Y):
            P.append(Pieza(f'PISO {k + 1}{lado}', 'y', (yk - t, yk), box(Xp[0], zf[k], Xp[1], (k + 1) * PASO), 7, t))
        P.append(Pieza('ZOCALO' + lado, 'z', (0, tm), box(Xc[0], 0, Xc[1], PISOS_Y[0]), 6, tm))
        for k in range(1, n):
            P.append(Pieza(f'CONTRAHUELLA {k}{lado}', 'z', (zf[k], zf[k] + t), box(Xc[0], PISOS_Y[k - 1] - t, Xc[1], PISOS_Y[k]), 6, t))
        for k, yk in enumerate(PISOS_Y):
            tope = box(Xt[0], yk - t, Xt[1], yk + TOPE_H).difference(box(xd0, yk - t - 1, xd1, yk))
            zt = z_tope(k)
            P.append(Pieza(f'TOPE {k + 1}{lado}', 'z', (zt, zt + t), tope, 5, t))
    for p in P:
        x0 = 40 if p.lado == 'I' else xd1 + 40
        if p.nombre.startswith('CONTRAHUELLA'):
            p.agujeros.append(Point(x0, p.poly.bounds[1] + 25).buffer(5, 32))      # cable del LED
        if p.nombre.startswith('FONDO'):
            p.agujeros.append(Point(x0, 40).buffer(6, 32))
            a, b = (60, xm - 1) if p.lado == 'I' else (xm + 1, xi1 - 60)
            p.grabados.append(box(a, y4 + BARANDA + 25, b, ALTO - 15))   # zona de logo (se junta al centro)
    unir(P, 55)
    rebajar_pestanas(P)
    return P


REBAJE = 4.0     # las pestañas del acrílico entran 8 de los 12 mm del MDF: el hueco de afuera se rellena con masilla
REBAJES = []     # cajas 3D de esos huecos (para que la verificación no los cuente como error)


def rebajar_pestanas(P):
    """Acorta las pestañas del acrílico que atraviesan el MDF: dejan REBAJE mm libres por la cara de afuera."""
    REBAJES.clear()
    exterior = {'COSTADO IZQ': 0, 'COSTADO DER': 1, 'FONDO': 1, 'BASE': 0}     # 0 = cara rango[0] da afuera
    big = 1e5
    for M in P:
        lado = next((v for k, v in exterior.items() if M.nombre.startswith(k)), None)
        if lado is None or color_de(M.nombre) != 'mdf':
            continue
        a0, a1 = M.rango
        franja = (a0 - 0.01, a0 + REBAJE) if lado == 0 else (a1 - REBAJE, a1 + 0.01)
        for A in P:
            if color_de(A.nombre) != 'transparente' or M.normal == A.normal:
                continue
            ejes = Pieza.EJES2D[A.normal]
            lim = {e: (-big, big) for e in ejes}
            lim[M.normal] = franja
            corte = A.rect(lim)
            if A.final.intersection(corte).area > 0:
                REBAJES.append((M.normal, franja))
                A.final = set_precision(A.final.difference(corte), 0.001)
                if A.final.geom_type != 'Polygon':
                    sys.exit(f'ERROR {A.nombre} quedó partida al rebajar pestañas')


# ---------------------------------------------------------------- CAJA (sin empates, pegada a tope)
def tapa_marco():
    """Tapa inclinada entre los dos lados, con bisagra de pivote integrada (orejitas en huecos redondos)."""
    t = CAJA_T
    s = (CAJA_HB - CAJA_HF) / CAJA_D                 # pendiente de la cara de abajo de la tapa
    ang = math.atan(s); ca, sa = math.cos(ang), math.sin(ang)
    z0, y0 = -TAPA_VUELO, CAJA_HF - TAPA_VUELO * s    # borde delantero, cara de abajo
    largo = (CAJA_D - t + TAPA_VUELO) / ca           # hasta la cara de adentro de la pared de atrás: así el hueco
                                                     # de la bisagra queda cerrado dentro del lado (la orejita no se sale)
    vA = largo - t / 2                               # eje de giro: a medio grosor, t/2 antes del final
    zA = z0 + vA * ca - (t / 2) * sa
    yA = y0 + vA * sa + (t / 2) * ca
    juego = 0.5
    return {'t': t, 's': s, 'ang': ang, 'z0': z0, 'y0': y0, 'largo': largo, 'vA': vA, 'zA': zA, 'yA': yA,
            'x0': t + juego, 'ancho': CAJA_W - 2 * t - 2 * juego, 'oreja': juego + t - 0.5,
            'hueco': 2.3, 'tras_h': yA - math.hypot(t / 2, t / 2) - 0.7}


def caja():
    t = CAJA_T
    W, D = CAJA_W, CAJA_D
    m = tapa_marco()
    arriba = lambda z: CAJA_HF + m['s'] * z + t / math.cos(m['ang'])     # cara de arriba de la tapa
    eje = Point(m['zA'], m['yA'])
    lado = Polygon([(0, t), (D, t), (D, arriba(D)), (0, arriba(0))])
    lado = lado.union(eje.buffer(6, 48).intersection(box(0, t, D, 1000)))   # nudillo de la bisagra
    P = [Pieza('CAJA BASE', 'y', (0, t), box(0, 0, W, D), 6, t),
         Pieza('CAJA LADO', 'x', (0, t), lado, 5, t),
         Pieza('CAJA LADO', 'x', (W - t, W), lado, 5, t),
         Pieza('CAJA FRENTE', 'z', (0, t), box(t, t, W - t, CAJA_HF), 4, t),
         Pieza('CAJA TRASERA', 'z', (D - t, D), box(t, t, W - t, m['tras_h']), 4, t)]
    for p in P:
        if p.nombre == 'CAJA LADO':
            p.agujeros.append(eje.buffer(m['hueco'], 48))
        if p.nombre == 'CAJA FRENTE':
            p.grabados.append(box(t + 12, t + 14, W - t - 12, CAJA_HF - 14))   # nombre del dulce
        f = p.poly
        for h in p.agujeros:
            f = f.difference(h)
        p.final = set_precision(f, 0.001)
    # tapa: u = a lo ancho (0 = borde de la tapa), v = desde el borde delantero hacia atrás
    Wl, L, vA, o = m['ancho'], m['largo'], m['vA'], m['oreja']
    tapa = box(0, 0, Wl, L).union(box(-o, vA - t / 2, 0, vA + t / 2)).union(box(Wl, vA - t / 2, Wl + o, vA + t / 2))
    r = 6
    tapa = tapa.difference(box(0, 0, r, r)).difference(box(Wl - r, 0, Wl, r)).union(
        Point(r, r).buffer(r, 24)).union(Point(Wl - r, r).buffer(r, 24))
    return P, set_precision(tapa, 0.001)


def caja_alta():
    """Caja del último piso: abierta (sin tapa), CAJA_ALTA_H de alto, pegada a tope como las demás."""
    t = CAJA_T
    W, D, H = CAJA_W, CAJA_D, CAJA_ALTA_H
    P = [Pieza('CAJA ALTA BASE', 'y', (0, t), box(0, 0, W, D), 6, t),
         Pieza('CAJA ALTA LADO', 'x', (0, t), box(0, t, D, H), 5, t),
         Pieza('CAJA ALTA LADO', 'x', (W - t, W), box(0, t, D, H), 5, t),
         Pieza('CAJA ALTA FRENTE', 'z', (0, t), box(t, t, W - t, H), 4, t),
         Pieza('CAJA ALTA TRASERA', 'z', (D - t, D), box(t, t, W - t, H), 4, t)]
    P[3].grabados.append(box(t + 12, t + 20, W - t - 12, t + 70))      # nombre del dulce
    for p in P:
        p.final = set_precision(p.poly, 0.001)
    return P


def es_alta(i):
    """¿La caja número i va en el último piso?"""
    return (i % (CAJAS_POR_PISO * len(PISOS_Y))) // CAJAS_POR_PISO == len(PISOS_Y) - 1


def tapa_3d(u, v, w, m):
    """Punto de la tapa (u, v, w) → (x, y, z) dentro de la caja, con la tapa cerrada."""
    ca, sa = math.cos(m['ang']), math.sin(m['ang'])
    return (m['x0'] + u, m['y0'] + v * sa + w * ca, m['z0'] + v * ca - w * sa)


def verificar_bisagra():
    """La orejita cabe en el hueco y la tapa puede girar sin chocar con la pared de atrás."""
    m = tapa_marco(); t = m['t']
    diag = math.hypot(t / 2, t / 2)
    ok = diag < m['hueco']
    esquina_baja = m['yA'] - diag
    ok &= esquina_baja > m['tras_h']
    ok &= m['x0'] - m['oreja'] > 0          # la orejita no se asoma por fuera del lado
    pared = CAJA_D - (m['zA'] + m['hueco'])   # material entre el hueco y el borde de atrás del lado
    ok &= pared >= 1.5
    return ok, f'orejita {t:g}x{t:g} (diagonal {2 * diag:.2f} mm) en hueco Ø{2 * m["hueco"]:.1f} mm, ' \
               f'holgura con la pared de atrás {esquina_baja - m["tras_h"]:.1f} mm, '                f'pared detrás del hueco {pared:.1f} mm (cerrado)'


# ---------------------------------------------------------------- MOLDE PARA PEGAR LAS CAJAS
MOLDE_JUEGO = 0.0      # sin juego: la quema del láser (~0,2 mm) ya deja la ranura justa para la pared con su papel
MOLDE_BORDE = 30.0
MOLDE_T = 12.0         # MDF del molde
MOLDE_CAPAS_MARCO, MOLDE_CAPAS_NUCLEO, MOLDES = 1, 4, 2   # por molde: 1 marco + núcleo de 4 capas; 2 moldes


def molde():
    """Molde en MDF: un MARCO (hueco = caja por fuera) y un NÚCLEO (= caja por dentro).
    La base va dentro del marco, el núcleo encima, y las paredes entran en la ranura que queda entre los dos:
    así cada caja sale recta y a escuadra. Sirve para las cajas con tapa y para las altas (misma base)."""
    t, W, D, B, j = CAJA_T, CAJA_W, CAJA_D, MOLDE_BORDE, MOLDE_JUEGO
    hueco = box(B - j, B - j, B + W + j, B + D + j)
    for x, y in ((B - j, B - j), (B + W + j, B - j), (B - j, B + D + j), (B + W + j, B + D + j)):
        hueco = hueco.union(Point(x, y).buffer(2.0, 24))          # alivio en las esquinas (pegante y canto)
    # ventanas en el marco: dejan llegar la jeringa a la unión de abajo (base con paredes)
    VW, VP = 25.0, 15.0                     # ancho de cada ventana y cuánto entra en el marco
    for k in range(3):                      # lados largos (frente y atrás)
        xc = B + W * (k + 1) / 4
        hueco = hueco.union(box(xc - VW / 2, B - j - VP, xc + VW / 2, B - j + 1)).union(box(xc - VW / 2, B + D + j - 1, xc + VW / 2, B + D + j + VP))
    for k in range(2):                      # lados cortos
        yc = B + D * (k + 1) / 3
        hueco = hueco.union(box(B - j - VP, yc - VW / 2, B - j + 1, yc + VW / 2)).union(box(B + W + j - 1, yc - VW / 2, B + W + j + VP, yc + VW / 2))
    marco = box(0, 0, W + 2 * B, D + 2 * B).difference(hueco)
    nw, nd = W - 2 * t - 2 * j, D - 2 * t - 2 * j
    nucleo = box(0, 0, nw, nd).difference(Point(nw / 2, nd / 2).buffer(16, 48))   # hueco para sacarlo con el dedo
    for x, y in ((0, 0), (nw, 0), (0, nd), (nw, nd)):
        nucleo = nucleo.difference(Point(x, y).buffer(10, 48))   # lunitas: la aguja llega por dentro a cada esquina
    piezas = []
    for mo in range(MOLDES):
        piezas += [(f'MARCO M{mo + 1}', set_precision(marco, 0.001)) for i in range(MOLDE_CAPAS_MARCO)]
        piezas += [(f'NUCLEO M{mo + 1}', set_precision(nucleo, 0.001)) for i in range(MOLDE_CAPAS_NUCLEO)]
    return piezas


# ---------------------------------------------------------------- SVG
def svg_poligono(g, color, ancho=0.01):
    def anillo(r):
        pts = list(r.coords)
        return 'M' + ' L'.join(f'{x:.3f},{y:.3f}' for x, y in pts[:-1]) + ' Z'
    d = anillo(g.exterior) + ''.join(' ' + anillo(i) for i in g.interiors)
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{ancho}" fill-rule="evenodd"/>'


def plano_geo(g):
    return sscale(g, 1, -1, origin=(0, 0))


def pareja(g1, g2, sep=5):
    """Encaja dos piezas iguales una contra otra (la primera girada 180°) para ahorrar material."""
    g1 = rotate(g1, 180, origin=(0, 0)); g1 = translate(g1, -g1.bounds[0], -g1.bounds[1])
    g2 = translate(g2, -g2.bounds[0], -g2.bounds[1])
    mejor = None
    for dx in range(-60, 61, 2):
        lo, hi = -2000.0, 2000.0
        g = translate(g2, dx, 0)
        while hi - lo > 0.3:
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if translate(g, 0, mid).distance(g1) >= sep and mid > 0 else (mid, hi)
        gg = translate(g, 0, hi)
        u = unary_union([g1, gg]).bounds
        area = (u[2] - u[0]) * (u[3] - u[1])
        if mejor is None or area < mejor[0]:
            mejor = (area, gg)
    return g1, mejor[1]


SALTO_HOJA = LAMINA[1] + 100.0     # cada lámina nueva se dibuja debajo de la anterior


def empacar(bloques, ancho=LAMINA[0], m=6, s=5):
    """bloques = [[(nombre, geo, grabados, fuente), ...], ...]. Estantes por lámina, el primero donde quepa
    (también probando el bloque girado 90°); si no cabe en ninguna, lámina nueva."""
    def bb(gs):
        return unary_union(gs).bounds
    def girar(bl):
        c = bb([g for _, g, _, _ in bl])
        return [(n, rotate(g, 90, origin=(c[0], c[1])), [rotate(e, 90, origin=(c[0], c[1])) for e in gr], f) for n, g, gr, f in bl]
    # las tiras largas se paran (lado largo vertical) si caben, así entran varias una al lado de otra
    def parar(bl):
        x0, y0, x1, y1 = bb([g for _, g, _, _ in bl])
        return girar(bl) if (x1 - x0) > (y1 - y0) and (x1 - x0) <= LAMINA[1] - 2 * m else bl
    bloques = [parar(bl) for bl in bloques]
    bloques = sorted(bloques, key=lambda bl: (-(bb([g for _, g, _, _ in bl])[3] - bb([g for _, g, _, _ in bl])[1]),
                                              -unary_union([g for _, g, _, _ in bl]).area))
    hojas = []          # cada hoja: lista de estantes [y, alto, x_usado]
    col = []
    for bl in bloques:
        puesto = None
        for opcion in (bl, girar(bl)):
            x0, y0, x1, y1 = bb([g for _, g, _, _ in opcion])
            w, h = x1 - x0, y1 - y0
            for hi, est in enumerate(hojas):
                for e in est:            # estante existente con espacio
                    if h <= e[1] + 0.01 and e[2] + w <= ancho - m:
                        puesto = (opcion, hi, e, None); break
                if puesto: break
                fondo = est[-1][0] + est[-1][1] + s if est else m
                if fondo + h <= LAMINA[1] - m and w <= ancho - 2 * m:
                    puesto = (opcion, hi, None, fondo); break
            if puesto: break
        if not puesto:
            hojas.append([]); x0, y0, x1, y1 = bb([g for _, g, _, _ in bl])
            puesto = (bl if x1 - x0 <= ancho - 2 * m else girar(bl), len(hojas) - 1, None, m)
        opcion, hi, e, fondo = puesto
        x0, y0, x1, y1 = bb([g for _, g, _, _ in opcion])
        if e is None:
            e = [fondo, y1 - y0, m]; hojas[hi].append(e)
        ox, oy = e[2] - x0, hi * SALTO_HOJA + e[0] - y0
        for n, g, gr, f in opcion:
            col.append((n, translate(g, ox, oy), [translate(q, ox, oy) for q in gr], f))
        e[2] += x1 - x0 + s
    return col


def hojas_de(col):
    """Separa una lista empacada en láminas, cada una con su y desde 0."""
    res = {}
    for n, g, gr, f in col:
        h = int(g.bounds[1] // SALTO_HOJA)
        res.setdefault(h, []).append((n, translate(g, 0, -h * SALTO_HOJA), [translate(e, 0, -h * SALTO_HOJA) for e in gr], f))
    return [res[k] for k in sorted(res)]


def laminas_estructura(P):
    """Una lámina por color de acrílico: {color: [(nombre, geo, grabados, pieza), ...]}."""
    res = {}
    por = {p.nombre: p for p in P}
    for c in ('mdf', 'transparente'):
        bloques = []
        for p in P:
            if color_de(p.nombre) != c or p.nombre == 'COSTADO DER':
                continue
            for mo in range(MODULOS):
                suf = f' M{mo + 1}' if MODULOS > 1 else ''
                if p.nombre == 'COSTADO IZQ':
                    d = por['COSTADO DER']
                    a, b = pareja(plano_geo(p.final), plano_geo(d.final))
                    bloques.append([('COSTADO IZQ' + suf, a, [], (p, mo)), ('COSTADO DER' + suf, b, [], (d, mo))])
                else:
                    bloques.append([(p.nombre + suf, plano_geo(p.final), [plano_geo(e) for e in p.grabados], (p, mo))])
        if bloques:
            res[c] = empacar(bloques)
    return res


def lamina_cajas(P, tapa, PA=None):
    PA = PA or caja_alta()
    def lados_de(Q, nombre):
        ls = [p for p in Q if p.nombre == nombre]
        return ls, pareja(plano_geo(ls[0].final), plano_geo(ls[1].final))
    normal = lados_de(P, 'CAJA LADO')
    alta = lados_de(PA, 'CAJA ALTA LADO')
    cajas = []                                   # cada caja con TODAS sus piezas
    for i in range(CAJAS_POR_PISO * len(PISOS_Y) * MODULOS):
        Q, (ls, (a, b)) = (PA, alta) if es_alta(i) else (P, normal)
        bl = []
        for p in Q:
            if p.nombre.endswith('LADO'):
                continue
            bl.append([(f'{p.nombre[5:]} {i + 1}', plano_geo(p.final), [plano_geo(e) for e in p.grabados], (p, i))])
        if not es_alta(i):
            bl.append([(f'TAPA {i + 1}', plano_geo(tapa), [], ('TAPA', i))])
        bl.append([(f'LADOS {i + 1}', a, [], (ls[0], i)), ('', b, [], (ls[1], i))])
        cajas.append(bl)
    # cada lámina lleva solo CAJAS COMPLETAS: se agregan cajas mientras quepan enteras en la lámina
    def cabe(bloques):
        return all(g.bounds[3] <= LAMINA[1] for _, g, _, _ in empacar(bloques))
    hojas, actual = [], []
    for bl in cajas:
        if cabe(actual + bl):
            actual = actual + bl
        else:
            hojas.append(actual); actual = bl
    hojas.append(actual)
    res = []
    for k, h in enumerate(hojas):
        for n, g, gr, f in empacar(h):
            res.append((n, translate(g, 0, k * SALTO_HOJA), [translate(e, 0, k * SALTO_HOJA) for e in gr], f))
    return res


LAMINAS_CAJAS_COMPLETAS = 2      # las primeras láminas de 3 mm llevan sí o sí cajas completas (las que tienes ya)


def lamina_cajas_ahorro(P, tapa, PA=None, completas=LAMINAS_CAJAS_COMPLETAS):
    """Ahorro máximo de acrílico de 3 mm:
    - en las primeras `completas` láminas entran todas las CAJAS COMPLETAS que quepan,
    - el espacio que sobra en esas láminas se rellena con piezas sueltas de las demás cajas,
    - las piezas restantes van mezcladas en las láminas siguientes,
    - las piezas van pegadas (separación 0) para cortar en LÍNEA COMÚN: el borde compartido se corta una vez."""
    PA = PA or caja_alta()
    def lados_de(Q, nombre):
        ls = [p for p in Q if p.nombre == nombre]
        return ls, pareja(plano_geo(ls[0].final), plano_geo(ls[1].final), sep=0.3)
    normal = lados_de(P, 'CAJA LADO')
    alta = lados_de(PA, 'CAJA ALTA LADO')
    cajas = []
    for i in range(CAJAS_POR_PISO * len(PISOS_Y) * MODULOS):
        Q, (ls, (a, b)) = (PA, alta) if es_alta(i) else (P, normal)
        bl = [[(f'{p.nombre[5:]} {i + 1}', plano_geo(p.final), [plano_geo(e) for e in p.grabados], (p, i))]
              for p in Q if not p.nombre.endswith('LADO')]
        if not es_alta(i):
            bl.append([(f'TAPA {i + 1}', plano_geo(tapa), [], ('TAPA', i))])
        bl.append([(f'LADOS {i + 1}', a, [], (ls[0], i)), ('', b, [], (ls[1], i))])
        cajas.append(bl)
    pack = lambda bls: empacar(bls, s=0)
    cabe = lambda bls: all(gg.bounds[3] <= LAMINA[1] for _, gg, _, _ in pack(bls))
    hojas, sueltas, k = [], [], 0
    for _ in range(completas):
        h = []
        while k < len(cajas) and cabe(h + cajas[k]):
            h += cajas[k]; k += 1
        hojas.append(h)
    sueltas = [bl for c in cajas[k:] for bl in c]
    area = lambda bl: unary_union([gg for _, gg, _, _ in bl]).envelope.area
    sueltas.sort(key=area, reverse=True)
    for h in hojas:                                  # relleno de las láminas de cajas completas
        resto = []
        for bl in sueltas:
            if cabe(h + [bl]):
                h.append(bl)
            else:
                resto.append(bl)
        sueltas = resto
    res = []
    for n_h, h in enumerate(hojas):
        for n, gg, gr, f in pack(h):
            res.append((n, translate(gg, 0, n_h * SALTO_HOJA), [translate(e, 0, n_h * SALTO_HOJA) for e in gr], f))
    base = len(hojas)
    for n, gg, gr, f in pack(sueltas):               # lo demás, mezclado
        res.append((n, translate(gg, 0, base * SALTO_HOJA), [translate(e, 0, base * SALTO_HOJA) for e in gr], f))
    return res, k


def lineas_comunes(geos, decimales=2):
    """Bordes de todas las piezas como segmentos; los que coinciden (piezas pegadas) se dejan una sola vez.
    Las puntas se conservan exactas (sin redondear) para que después se puedan encadenar."""
    import math as _m
    grupos = {}
    for gg in geos:
        for anillo in [gg.exterior, *gg.interiors]:
            pts = list(anillo.coords)
            for p0, p1 in zip(pts, pts[1:]):
                (x0, y0), (x1, y1) = p0, p1
                if _m.hypot(x1 - x0, y1 - y0) < 1e-6:
                    continue
                ang = _m.atan2(y1 - y0, x1 - x0) % _m.pi
                ux, uy = _m.cos(ang), _m.sin(ang)
                clave = (round(ang, 4), round(-uy * x0 + ux * y0, decimales))
                t0, t1 = ux * x0 + uy * y0, ux * x1 + uy * y1
                if t0 > t1:
                    t0, t1, p0, p1 = t1, t0, p1, p0
                grupos.setdefault(clave, []).append((t0, t1, p0, p1))
    segs = []
    for iv in grupos.values():
        iv.sort(key=lambda s: s[0])
        a, b, pa, pb = iv[0]
        for s in iv[1:] + [None]:
            if s is not None and s[0] <= b + 1e-3:
                if s[1] > b:
                    b, pb = s[1], s[3]
                continue
            segs.append((pa, pb))
            if s is not None:
                a, b, pa, pb = s
    return segs


def encadenar(segs, tol=0.01):
    """Une segmentos que comparten punta en trazos continuos (menos objetos en Corel y menos saltos del láser)."""
    from collections import defaultdict
    k = lambda p: (round(p[0] / tol), round(p[1] / tol))
    ady = defaultdict(list)
    for i, (a, b) in enumerate(segs):
        ady[k(a)].append(i); ady[k(b)].append(i)
    usado, trazos = [False] * len(segs), []
    # empezar por puntas sueltas (grado impar) para hacer trazos largos
    orden = sorted(range(len(segs)), key=lambda i: -(len(ady[k(segs[i][0])]) % 2 + len(ady[k(segs[i][1])]) % 2))
    for i0 in orden:
        if usado[i0]:
            continue
        usado[i0] = True
        a, b = segs[i0]
        if len(ady[k(a)]) % 2 == 0 and len(ady[k(b)]) % 2 == 1:
            a, b = b, a
        tr = [a, b]
        while True:
            sig = next((j for j in ady[k(tr[-1])] if not usado[j]), None)
            if sig is None:
                break
            usado[sig] = True
            p, q = segs[sig]
            tr.append(q if k(p) == k(tr[-1]) else p)
        trazos.append(tr)
    return trazos


def escribir_svg(ruta, colocadas, titulo, alto=None, comun=False):
    W, H = LAMINA[0], alto or LAMINA[1]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
           f'<title>{titulo}</title>',
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="none" stroke="#B0B0B0" stroke-width="0.5"/>',
           '<g id="CORTE">']
    if comun:
        segs = lineas_comunes([g for _, g, *_ in colocadas])
        for tr in encadenar(segs):
            d = 'M' + ' L'.join(f'{x:.3f},{y:.3f}' for x, y in tr)
            out.append(f'<path d="{d}" fill="none" stroke="#FF0000" stroke-width="0.01"/>')
    else:
        for nombre, g, gr, *_ in colocadas:
            out.append(svg_poligono(g, '#FF0000'))
    out.append('</g><g id="GRABADO">')
    for nombre, g, gr, *_ in colocadas:
        for e in gr:
            out.append(svg_poligono(e, '#0000FF'))
    out.append('</g><g id="NOMBRES_NO_CORTAR">')
    for nombre, g, gr, *_ in colocadas:
        if nombre:
            # centrado dentro de la pieza; en piezas paradas va vertical, para que nunca se salga de la lámina
            x0, y0, x1, y1 = g.bounds
            from shapely.geometry import Point as _P
            c = _P((x0 + x1) / 2, (y0 + y1) / 2)      # centro de la pieza: el texto nunca queda fuera de la lámina
            vert = (y1 - y0) > 1.5 * (x1 - x0)
            largo = len(nombre) * 5.5
            if largo > (y1 - y0 if vert else x1 - x0) - 4:
                continue
            rot = f' transform="rotate(-90 {c.x:.1f} {c.y:.1f})"' if vert else ''
            out.append(f'<text x="{c.x:.1f}" y="{c.y:.1f}" text-anchor="middle" font-family="Arial" font-size="9" fill="#00A000"{rot}>{nombre}</text>')
    out.append('</g></svg>')
    open(ruta, 'w', encoding='utf-8').write('\n'.join(out))
    malos = 0
    for i, (n1, g1, *_) in enumerate(colocadas):
        if not box(0, 0, W, H).contains(g1):
            print(f'  ! {n1} se sale de la lámina'); malos += 1
        for n2, g2, *_ in colocadas[i + 1:]:
            if (g1.intersection(g2).area > 0.01) if comun else (g1.distance(g2) < 3):
                print(f'  ! {n1} y {n2} se montan / quedan muy juntas'); malos += 1
    return malos


# ---------------------------------------------------------------- VISTA 3D
TONO = {'mdf': (0.12, 0.12, 0.15, 0.95), 'opal': (0.97, 0.97, 1.0, 0.95), 'transparente': (0.75, 0.88, 1.0, 0.35)}


def vista_3d(est, cajaP, tapa, ruta):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    caras, colores = [], []
    def a3d(P, u, v, w, dx=0, dy=0, dz=0):
        p = {Pieza.EJES2D[P.normal][0]: u, Pieza.EJES2D[P.normal][1]: v, P.normal: w}
        return (p['x'] + dx, p['z'] + dz, p['y'] + dy)
    def placa(P, color, dx=0, dy=0, dz=0):
        ext = list(P.final.exterior.coords)
        for w in P.rango:
            caras.append([a3d(P, u, v, w, dx, dy, dz) for u, v in ext]); colores.append(color)
        for (u0, v0), (u1, v1) in zip(ext, ext[1:]):
            caras.append([a3d(P, u0, v0, P.rango[0], dx, dy, dz), a3d(P, u1, v1, P.rango[0], dx, dy, dz),
                          a3d(P, u1, v1, P.rango[1], dx, dy, dz), a3d(P, u0, v0, P.rango[1], dx, dy, dz)])
            colores.append(color)
    for mo in range(MODULOS):
        for P in est:
            placa(P, TONO[color_de(P.nombre)], mo * ANCHO)
    m = tapa_marco()
    xs = cajas_x()
    dulces = [(0.95, 0.3, 0.4), (0.3, 0.8, 0.4), (1.0, 0.75, 0.2), (0.6, 0.4, 0.95)]
    ext = list(tapa.exterior.coords)
    for k, (yk, zf) in enumerate(zip(PISOS_Y, frentes())):
        for i in range(CAJAS_POR_PISO * MODULOS):
            dx, dz = (i // CAJAS_POR_PISO) * ANCHO + xs[i % CAJAS_POR_PISO], z_cajas(k)
            alta = k == len(PISOS_Y) - 1
            for P in (caja_alta() if alta else cajaP):
                placa(P, TONO['transparente'], dx, yk, dz)
            c = dulces[(i + k) % 4]
            hb = CAJA_HF * 0.8
            caras.append([(dx + 4, dz + 4, yk + hb), (dx + CAJA_W - 4, dz + 4, yk + hb),
                          (dx + CAJA_W - 4, dz + CAJA_D - 4, yk + hb), (dx + 4, dz + CAJA_D - 4, yk + hb)])
            colores.append(c + (0.9,))
            if alta:
                continue
            pts = [tapa_3d(u, v, 0, m) for u, v in ext]
            caras.append([(dx + x, dz + z, yk + y) for x, y, z in pts]); colores.append(TONO['transparente'])
    fig = plt.figure(figsize=(14, 7), dpi=110)
    for n, (elev, az) in enumerate([(18, -58), (8, -120)]):
        ax = fig.add_subplot(1, 2, n + 1, projection='3d')
        ax.add_collection3d(Poly3DCollection(caras, facecolors=colores, edgecolors=(0.2, 0.3, 0.45, 0.35), linewidths=0.25))
        ax.set_xlim(-50, ANCHO_TOTAL + 50); ax.set_ylim(-100, FONDO + 100); ax.set_zlim(0, ALTO + 20)
        ax.set_box_aspect((ANCHO_TOTAL + 100, FONDO + 200, ALTO + 20)); ax.view_init(elev, az)
        ax.set_xlabel(f'largo {ANCHO_TOTAL / 10:g} cm'); ax.set_ylabel(f'fondo {FONDO / 10:g} cm'); ax.set_zlabel(f'alto {ALTO / 10:g} cm')
    plt.tight_layout(); plt.savefig(ruta); plt.close()


if __name__ == '__main__':
    import os
    aqui = os.path.dirname(os.path.abspath(__file__))
    est = estructura()
    cajaP, tapa = caja()
    print('Verificando encajes de la estructura…'); me = verificar(est, 1.0)
    print('Verificando que las piezas de la caja no se crucen…'); mc = verificar(cajaP, 0.5) + verificar(caja_alta(), 0.5)
    ok, txt = verificar_bisagra()
    print(f'puntos con error: estructura {me}, caja {mc} · bisagra {"OK" if ok else "MAL"}: {txt}')
    malos, cuenta = 0, {}
    def guardar(nombre, col, titulo, comun=False):
        hs = hojas_de(col)
        cuenta[nombre] = len(hs)
        for i, h in enumerate(hs):
            suf = f' ({i + 1} de {len(hs)})' if len(hs) > 1 else ''
            yield escribir_svg(os.path.join(aqui, f'{nombre}{suf}.svg'), h, titulo + suf, comun=comun)
    for c, col in laminas_estructura(est).items():
        nom = f'MDF {MDF_T:g}mm costados fondo zocalo' if c == 'mdf' else f'acrilico {ESTRUCTURA_T:g}mm pisos contrahuellas topes soporte'
        malos += sum(guardar(f'Corte {nom}', col, nom))
    col_c, n_completas = lamina_cajas_ahorro(cajaP, tapa)
    print(f'cajas completas en las primeras {LAMINAS_CAJAS_COMPLETAS} láminas de 3 mm: {n_completas}')
    malos += sum(guardar(f'Corte acrilico {CAJA_T:g}mm cajas', col_c,
                         f'{CAJAS_POR_PISO * len(PISOS_Y) * MODULOS} cajas acrílico transparente {CAJA_T:g} mm', comun=True))
    malos += sum(guardar(f'Corte MDF {MOLDE_T:g}mm molde para pegar cajas (2 moldes)', empacar([[(n, geo, [], None)] for n, geo in molde()]),
                         f'Molde para pegar cajas MDF {MOLDE_T:g} mm'))
    print('láminas:', ', '.join(f'{k}: {v}' for k, v in cuenta.items()))
    print('láminas:', 'OK' if malos == 0 else f'{malos} problemas')
    vista_3d(est, cajaP, tapa, os.path.join(aqui, 'vista 3D.png'))
    for c in sorted(set(COLOR.values())):
        print(f'  {c:12s} {MODULOS * sum(p.final.area for p in est if color_de(p.nombre) == c) / 1e6:.2f} m² de {espesor_de(c):g} mm')
    n_alta = CAJAS_POR_PISO * MODULOS
    n_baja = CAJAS_POR_PISO * (len(PISOS_Y) - 1) * MODULOS
    area_c = ((sum(p.final.area for p in cajaP) + tapa.area) * n_baja + sum(p.final.area for p in caja_alta()) * n_alta) / 1e6
    print(f'  cajas        {area_c:.2f} m² de {CAJA_T:g} mm transparente')
