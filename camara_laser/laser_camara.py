# Cámara sobre la cama del láser: mira los retazos y acomoda las piezas dentro de ellos.
# Un celular viejo (app IP Webcam) toma la foto; el programa la endereza a milímetros de la cama con un
# patrón que graba el MISMO láser (así las medidas quedan en coordenadas del láser), encuentra los retazos
# comparando con la foto de la cama vacía y acomoda las piezas de un SVG. Sale un DXF para RDWorks.
#
#   python laser_camara.py patron                  → patron_calibracion.dxf / .svg para grabar una vez
#   python laser_camara.py probar                  → toma una foto de prueba
#   python laser_camara.py calibrar [--foto f.jpg] → foto del patrón grabado → datos/calibracion.json
#   python laser_camara.py fondo [--foto f.jpg]    → foto de la cama VACÍA → datos/fondo.png
#   python laser_camara.py acomodar piezas.svg [otra.svg=3] [--grosor 3] [--copias 2] [--manual] [--foto f.jpg]
#
# Medidas en mm. Coordenadas de la cama: x a la derecha, y hacia abajo, (0, 0) en la esquina de arriba a la
# izquierda, igual que en el patrón. Todo sale con un MARCO del tamaño de la cama (color que no se corta) para
# que RDWorks ponga el corte en el mismo sitio que el patrón.
import argparse, glob, json, math, os, sys, time, urllib.request
import numpy as np
import cv2
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.affinity import rotate, translate
from shapely.ops import unary_union

aqui = os.path.dirname(os.path.abspath(__file__))
trabajo = os.environ.get('CAMARA_LASER_TRABAJO', aqui)     # la prueba simulada usa otra carpeta
datos = os.path.join(trabajo, 'datos')
salida = os.path.join(trabajo, 'salida')
CONFIG = os.path.join(aqui, 'config.json')             # solo en este PC (no va a GitHub); sale del ejemplo
DICCIONARIO = cv2.aruco.DICT_4X4_50
DEFECTO = {
    'camara': 'http://192.168.1.50:8080/photo.jpg',   # IP Webcam; también 0 (cámara USB) o la ruta de una foto
    'cama_ancho_mm': 1300, 'cama_alto_mm': 900,
    'marcador_mm': 70, 'marcador_borde_mm': 70,        # tamaño del marcador y distancia de su centro al borde
    'camara_altura_mm': 1000,                          # del lente a la superficie del patrón (para el grosor)
    'grosor_patron_mm': 1,                             # grosor de la lámina donde se grabó el patrón
    'resolucion_mm': 1.0,                              # 1 píxel = 1 mm al acomodar
    'margen_mm': 4,                                    # de la pieza al borde del retazo
    'separacion_mm': 3,                                # entre piezas
    'rotaciones': [0, 90, 180, 270],
    'umbral': 22,                                      # diferencia de color retazo / cama vacía
    'retazo_min_cm2': 20,
}
COLOR_DXF = {'corte': 1, 'grabado': 5, 'marco': 6, 'patron': 7}


def cfg():
    c = dict(DEFECTO)
    ejemplo = os.path.join(aqui, 'config_ejemplo.json')
    if not os.path.isfile(CONFIG) and os.path.isfile(ejemplo) and trabajo == aqui:
        import shutil
        shutil.copy(ejemplo, CONFIG)
        print('Creé config.json: ábrelo con el Bloc de notas y pon la dirección del celular y la altura.')
    if os.path.isfile(CONFIG):
        with open(CONFIG, encoding='utf-8') as f:
            c.update(json.load(f))
    return c


# ---------------------------------------------------------------- foto
def tomar_foto(c, archivo=None):
    fuente = archivo or str(c['camara'])
    if fuente.isdigit():
        cap = cv2.VideoCapture(int(fuente))
        for _ in range(5):
            ok, img = cap.read()
        cap.release()
        if not ok:
            sys.exit(f'ERROR no pude leer la cámara {fuente}')
        return img
    if fuente.startswith('http'):
        try:
            with urllib.request.urlopen(fuente, timeout=20) as r:
                buf = np.frombuffer(r.read(), np.uint8)
        except Exception as e:
            sys.exit(f'ERROR no pude bajar la foto de {fuente}: {e}\n'
                     '¿El celular está en el mismo wifi y la app IP Webcam está en "Iniciar servidor"?')
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    else:
        img = cv2.imread(fuente)
    if img is None:
        sys.exit(f'ERROR no pude abrir la foto {fuente}')
    return img


# ---------------------------------------------------------------- patrón de calibración
def marcadores(c):
    """Centro de cada marcador en la cama: rejilla de 3 x 3 (9 marcadores)."""
    W, H, b = c['cama_ancho_mm'], c['cama_alto_mm'], c['marcador_borde_mm']
    return {3 * j + i: (x, y) for j, y in enumerate((b, H / 2, H - b)) for i, x in enumerate((b, W / 2, W - b))}


def esquinas_marcador(cx, cy, s):
    h = s / 2
    return np.array([(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)], np.float64)


def poligono_marcador(i, cx, cy, s):
    """Parte negra del marcador ArUco como polígono (con huecos) en mm."""
    dic = cv2.aruco.getPredefinedDictionary(DICCIONARIO)
    n = 6                                               # 4 x 4 bits + borde negro
    img = cv2.aruco.generateImageMarker(dic, i, n)
    celda = s / n
    x0, y0 = cx - s / 2, cy - s / 2
    negras = [box(x0 + u * celda, y0 + v * celda, x0 + (u + 1) * celda, y0 + (v + 1) * celda)
              for v in range(n) for u in range(n) if img[v, u] < 128]
    return unary_union(negras)


def cmd_patron(c, a):
    W, H, s = c['cama_ancho_mm'], c['cama_alto_mm'], c['marcador_mm']
    polis = []
    for i, (x, y) in marcadores(c).items():
        g = poligono_marcador(i, x, y, s)
        polis += list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    lineas = [(list(p.exterior.coords), 'patron') for p in polis]
    lineas += [(list(r.coords), 'patron') for p in polis for r in p.interiors]
    os.makedirs(aqui, exist_ok=True)
    guardar_dxf(os.path.join(aqui, 'patron_calibracion.dxf'), lineas, c)
    guardar_svg(os.path.join(aqui, 'patron_calibracion.svg'), lineas, c, rellenar=polis)
    print(f'OK patron_calibracion.dxf y .svg: 9 marcadores de {s / 10:g} cm en una cama de {W / 10:g} x {H / 10:g} cm')
    print('Grábalo (relleno/scan, capa NEGRA) sobre cartulina o MDF delgado que cubra la cama.')
    print('La capa MAGENTA es el marco: déjala en "Salida: No". Usa siempre posición ABSOLUTA.')


# ---------------------------------------------------------------- calibración
def detectar(img):
    dic = cv2.aruco.getPredefinedDictionary(DICCIONARIO)
    if hasattr(cv2.aruco, 'ArucoDetector'):
        det = cv2.aruco.ArucoDetector(dic, cv2.aruco.DetectorParameters())
        esq, ids, _ = det.detectMarkers(img)
    else:
        esq, ids, _ = cv2.aruco.detectMarkers(img, dic)
    if ids is None:
        return {}
    return {int(i): e.reshape(4, 2) for i, e in zip(ids.ravel(), esq)}


def quitar_lente(p, cal):
    """Foto → sin distorsión del lente: q = c + (p - c)·(1 + k1·r² + k2·r⁴), r en anchos de foto."""
    w, h = cal['foto_wh']
    c0 = np.array([w / 2, h / 2])
    d = (np.asarray(p, np.float64) - c0) / w
    r2 = (d * d).sum(1, keepdims=True)
    k1, k2 = cal.get('k', [0, 0])
    return c0 + d * (1 + k1 * r2 + k2 * r2 * r2) * w


def poner_lente(q, cal):
    w, h = cal['foto_wh']
    c0 = np.array([w / 2, h / 2])
    k1, k2 = cal.get('k', [0, 0])
    dq = (np.asarray(q, np.float64) - c0) / w
    d = dq.copy()
    for _ in range(12):                                  # punto fijo: d·(1 + k1 r² + k2 r⁴) = dq
        r2 = (d * d).sum(1, keepdims=True)
        d = dq / (1 + k1 * r2 + k2 * r2 * r2)
    return c0 + d * w


def cama_a_camara(cal, pts):
    """Puntos de la cama (mm) → píxeles de la foto."""
    pts = np.asarray(pts, np.float64).reshape(-1, 2)
    q = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), np.array(cal['H'])).reshape(-1, 2)
    return poner_lente(q, cal)


def ajustar_lente(b, p, cal):
    """Busca k1, k2 que dejan los marcadores más rectos (menor error de la homografía)."""
    def error(k):
        cal['k'] = list(k)
        q = quitar_lente(p, cal)
        H, _ = cv2.findHomography(b, q, 0)
        return np.linalg.norm(cv2.perspectiveTransform(b.reshape(-1, 1, 2), H).reshape(-1, 2) - q, axis=1).mean(), H
    k, paso = [0.0, 0.0], [0.2, 0.2]
    mejor = error(k)[0]
    for _ in range(60):
        cambio = False
        for i in (0, 1):
            for sgn in (1, -1):
                k2 = list(k); k2[i] += sgn * paso[i]
                e = error(k2)[0]
                if e < mejor - 1e-6:
                    mejor, k, cambio = e, k2, True
        if not cambio:
            paso = [x / 2 for x in paso]
            if max(paso) < 1e-4:
                break
    e, H = error(k)
    cal.update(k=list(map(float, k)), H=H.tolist())


def cmd_calibrar(c, a):
    img = tomar_foto(c, a.foto)
    os.makedirs(datos, exist_ok=True)
    cv2.imwrite(os.path.join(datos, 'foto_patron.jpg'), img)
    det, espejo = detectar(img), False
    if len(det) < 4:                                    # el láser pudo grabarlo en espejo
        d2 = detectar(cv2.flip(img, 1))
        if len(d2) > len(det):
            w = img.shape[1]
            det = {i: np.array([(w - 1 - x, y) for x, y in e]) for i, e in d2.items()}   # misma esquina del marcador
            espejo = True
    centros = marcadores(c)
    det = {i: e for i, e in det.items() if i in centros}
    if len(det) < 4:
        sys.exit(f'ERROR solo encontré {len(det)} marcadores (necesito 4 o más; lo ideal son los 9).\n'
                 'Revisa que se vea toda la cama, que haya buena luz y que la foto no esté movida.')
    b = np.concatenate([esquinas_marcador(*centros[i], c['marcador_mm']) for i in sorted(det)])
    p = np.concatenate([det[i] for i in sorted(det)])
    cal = {'espejo': espejo, 'foto_wh': [img.shape[1], img.shape[0]], 'k': [0.0, 0.0],
           'cama': [c['cama_ancho_mm'], c['cama_alto_mm']], 'marcadores': sorted(det)}
    if len(det) >= 6:
        ajustar_lente(b, p, cal)
    else:
        cal['H'] = cv2.findHomography(b, p, 0)[0].tolist()
    # punto de la cama justo debajo del lente (≈ centro de la foto) y altura medida: para el grosor del material
    Hi = np.linalg.inv(np.array(cal['H']))
    nadir = cv2.perspectiveTransform(np.array([[[img.shape[1] / 2, img.shape[0] / 2]]], np.float64), Hi)
    cal.update(nadir=nadir.ravel().tolist(), altura_mm=float(c['camara_altura_mm']))
    err_px = np.linalg.norm(p - cama_a_camara(cal, b), axis=1)
    px_mm = np.linalg.norm(cama_a_camara(cal, [(W2 := c['cama_ancho_mm'] / 2, 0)]) -
                           cama_a_camara(cal, [(W2 + 100, 0)])) / 100
    cal.update(px_por_mm=float(px_mm), error_mm=float(err_px.mean() / px_mm),
               error_max_mm=float(err_px.max() / px_mm), fecha=time.strftime('%Y-%m-%d %H:%M'))
    with open(os.path.join(datos, 'calibracion.json'), 'w', encoding='utf-8') as f:
        json.dump(cal, f, indent=1)
    vista = enderezar(img, cal, c)
    for i in det:
        cv2.polylines(vista, [np.int32(esquinas_marcador(*centros[i], c['marcador_mm']) / c['resolucion_mm'])],
                      True, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(datos, 'calibracion_verificar.jpg'), vista)
    print(f'OK calibrado con {len(det)} de 9 marcadores{" (grabado en ESPEJO, ya lo tuve en cuenta)" if espejo else ""}.')
    print(f'   {px_mm:.2f} píxeles por mm · error promedio {cal["error_mm"]:.2f} mm (máx {cal["error_max_mm"]:.2f} mm)')
    print(f'   lente: k1 = {cal["k"][0]:+.3f}, k2 = {cal["k"][1]:+.3f} · altura del celular (config.json): '
          f'{cal["altura_mm"] / 10:.0f} cm')
    if cal['error_mm'] > 1.5:
        print('   OJO: error alto. Revisa que el celular no se haya movido y que el patrón esté plano.')
    print('   Mira datos/calibracion_verificar.jpg: los cuadros rojos deben caer justo sobre los marcadores.')
    print('   Ahora quita el patrón y corre "fondo" con la cama VACÍA.')


def leer_cal():
    ruta = os.path.join(datos, 'calibracion.json')
    if not os.path.isfile(ruta):
        sys.exit('ERROR falta calibrar: corre primero "calibrar".')
    with open(ruta, encoding='utf-8') as f:
        return json.load(f)


def enderezar(img, cal, c):
    """Foto → vista desde arriba de la cama, 1 píxel = resolucion_mm."""
    r = c['resolucion_mm']
    W, H = cal['cama']
    gx, gy = np.meshgrid(np.arange(0, W, r) + r / 2, np.arange(0, H, r) + r / 2)
    m = cama_a_camara(cal, np.stack([gx.ravel(), gy.ravel()], 1)).astype(np.float32)
    mx, my = m[:, 0].reshape(gx.shape), m[:, 1].reshape(gx.shape)
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))


def cmd_fondo(c, a):
    cal = leer_cal()
    img = tomar_foto(c, a.foto)
    cv2.imwrite(os.path.join(datos, 'fondo.png'), enderezar(img, cal, c))
    print('OK foto de la cama vacía guardada (datos/fondo.png). Repítela si cambias la luz o la rejilla.')


def cmd_probar(c, a):
    img = tomar_foto(c, a.foto)
    os.makedirs(datos, exist_ok=True)
    ruta = os.path.join(datos, 'prueba.jpg')
    cv2.imwrite(ruta, img)
    print(f'OK foto de {img.shape[1]} x {img.shape[0]} px guardada en {ruta}. Revisa que se vea TODA la cama.')
    abrir(ruta)


# ---------------------------------------------------------------- retazos
def detectar_retazos(vista, fondo, c):
    a = cv2.GaussianBlur(cv2.cvtColor(vista, cv2.COLOR_BGR2LAB).astype(np.float32), (0, 0), 2)
    b = cv2.GaussianBlur(cv2.cvtColor(fondo, cv2.COLOR_BGR2LAB).astype(np.float32), (0, 0), 2)
    d = a - b
    d[..., 0] -= np.median(d[..., 0])                  # si cambió un poco la luz
    dist = np.sqrt(0.5 * d[..., 0] ** 2 + d[..., 1] ** 2 + d[..., 2] ** 2)
    m = (dist > c['umbral']).astype(np.uint8) * 255
    m[(vista.sum(2) == 0)] = 0                           # fuera de la foto
    k = lambda mm: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(3, int(mm / c['resolucion_mm'])) | 1,) * 2)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k(5))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k(7))
    return mascara_a_poligonos(m, c), m


def mascara_a_poligonos(m, c):
    r = c['resolucion_mm']
    cont, jer = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    polis = []
    if jer is None:
        return polis
    for i, ct in enumerate(cont):
        if jer[0][i][3] != -1:
            continue
        huecos, h = [], jer[0][i][2]
        while h != -1:
            if len(cont[h]) >= 3:
                huecos.append(cont[h].reshape(-1, 2) * r + r / 2)
            h = jer[0][h][0]
        if len(ct) < 3:
            continue
        p = Polygon(ct.reshape(-1, 2) * r + r / 2, huecos).buffer(0).simplify(r / 2)
        polis += [g for g in getattr(p, 'geoms', [p]) if g.area >= c['retazo_min_cm2'] * 100]
    return polis


def corregir_grosor(p, cal, c, grosor):
    """El borde de arriba de un material grueso se ve más grande (más cerca de la cámara): lo devuelve."""
    h = grosor - c['grosor_patron_mm']
    f = 1 - h / c['camara_altura_mm']
    nx, ny = cal['nadir']
    from shapely.affinity import scale
    return scale(p, f, f, origin=(nx, ny))


def dibujar_retazos(vista):
    """Modo manual: clic en las esquinas de cada retazo. Enter cierra el retazo, Q termina."""
    polis, actual = [], []
    alto = 900
    f = min(1.0, alto / vista.shape[0])
    def raton(ev, x, y, *_):
        if ev == cv2.EVENT_LBUTTONDOWN:
            actual.append((x / f, y / f))
        elif ev == cv2.EVENT_RBUTTONDOWN and actual:
            actual.pop()
    cv2.namedWindow('retazos'); cv2.setMouseCallback('retazos', raton)
    print('MODO MANUAL: clic izquierdo = esquina · clic derecho = borrar · ENTER = cerrar retazo · Q = listo')
    while True:
        v = cv2.resize(vista, None, fx=f, fy=f)
        for p in polis:
            cv2.polylines(v, [np.int32(np.array(p) * f)], True, (0, 255, 0), 2)
        if actual:
            cv2.polylines(v, [np.int32(np.array(actual) * f)], False, (0, 200, 255), 2)
        cv2.imshow('retazos', v)
        k = cv2.waitKey(30) & 0xFF
        if k in (13, 10) and len(actual) >= 3:
            polis.append(list(actual)); actual.clear()
        elif k in (ord('q'), ord('Q'), 27):
            break
    cv2.destroyAllWindows()
    return polis


# ---------------------------------------------------------------- piezas (SVG)
def leer_svg(ruta, paso=0.5):
    """Trazos del SVG en mm: [(puntos, tipo, cerrado)]. Rojo/negro = corte, azul = grabado, verde = no se usa."""
    import svgelements as se
    doc = se.SVG.parse(ruta)                            # todo queda en px a 96 ppi (sirve con mm, cm, in o px)
    mm = 25.4 / 96
    trazos = []
    for el in doc.elements():
        if not isinstance(el, se.Shape) or isinstance(el, se.Image):
            continue
        col = el.stroke if el.stroke is not None and el.stroke.value is not None else el.fill
        tipo = 'corte'
        if col is not None and col.value is not None:
            rr, gg, bb = col.red, col.green, col.blue
            if gg > 150 and rr < 100 and bb < 100:
                continue                                # verde: nombres, no se cortan
            if rr == gg == bb and 100 <= rr <= 235:
                continue                                # gris: marco de la lámina, no se corta
            if bb > 150 and rr < 100:
                tipo = 'grabado'
        p = se.Path(el)
        if len(p) == 0:
            continue
        for sp in p.as_subpaths():
            sp = se.Path(sp)
            largo = sp.length(error=1e-3) * mm
            if not largo:
                continue
            n = max(2, int(largo / paso) + 1)
            pts = np.asarray(sp.npoint(np.linspace(0, 1, n)), np.float64).reshape(-1, 2) * mm
            cerrado = sp.closed or np.linalg.norm(pts[0] - pts[-1]) < 0.05
            trazos.append((pts, tipo, cerrado))
    return trazos


def piezas_de(trazos, bloque=False):
    """Agrupa los trazos en piezas: cada contorno cerrado de afuera con lo que tiene adentro."""
    def solida(pts):                                    # un contorno que se cruza a sí mismo → su envolvente
        g = Polygon(pts).buffer(0)
        return g if isinstance(g, Polygon) else g.convex_hull
    cerr = [(i, solida(t[0])) for i, t in enumerate(trazos) if t[2] and len(t[0]) >= 3]
    cerr = [(i, p) for i, p in cerr if p.area > 1]
    afuera = [(i, p) for i, p in cerr if not any(j != i and q.area > p.area and q.contains(p) for j, q in cerr)]
    if bloque:
        forma = unary_union([p for _, p in afuera]).convex_hull
        return [{'forma': forma, 'trazos': trazos}]
    piezas = [{'forma': Polygon(p.exterior), 'trazos': [trazos[i]]} for i, p in afuera]
    usados = {i for i, _ in afuera}
    for i, t in enumerate(trazos):
        if i in usados:
            continue
        pt = Point(t[0][len(t[0]) // 2])
        for pz in piezas:
            if pz['forma'].buffer(0.5).contains(pt):
                pz['trazos'].append(t)
                break
    return piezas


# ---------------------------------------------------------------- acomodar
def rasterizar(geom, r, ancho, alto, dx=0.0, dy=0.0):
    m = np.zeros((alto, ancho), np.uint8)
    geoms = list(geom.geoms) if hasattr(geom, 'geoms') else [geom]
    for g in geoms:
        if g.is_empty or not hasattr(g, 'exterior'):
            continue
        cv2.fillPoly(m, [np.int32(np.round((np.array(g.exterior.coords) - (dx, dy)) / r))], 1)
        for h in g.interiors:
            cv2.fillPoly(m, [np.int32(np.round((np.array(h.coords) - (dx, dy)) / r))], 0)
    return m


def acomodar(piezas, retazos, c):
    """Prueba varias estrategias y se queda con la que más área de piezas mete."""
    mejor = None
    for orden in ('area', 'largo'):
        for modo in ('compacto', 'arriba', 'izquierda'):
            puestas, sobran = acomodar_una(piezas, retazos, c, orden, modo)
            area = sum(q['forma'].area for q in puestas)
            if mejor is None or area > mejor[0] + 1:
                mejor = (area, puestas, sobran)
    return mejor[1], mejor[2]


def acomodar_una(piezas, retazos, c, orden='area', modo='compacto'):
    """Las piezas más grandes primero, cada una en el retazo más pequeño donde quepa. Dentro del retazo se
    prueban las esquinas libres (no se puede subir ni ir a la izquierda) y gana la que deja el grupo de
    piezas más compacto, así no quedan huecos sueltos."""
    r, sep, mar = c['resolucion_mm'], c['separacion_mm'], c['margen_mm']
    libres = []
    for p in retazos:
        q = p.buffer(-mar + sep / 2)
        libres += [g for g in getattr(q, 'geoms', [q]) if not g.is_empty]
    libres.sort(key=lambda g: g.area)
    ocupado = {i: [] for i in range(len(libres))}        # piezas puestas en cada retazo (con media separación)
    caja = {i: None for i in range(len(libres))}          # rectángulo que encierra lo puesto en cada retazo
    puestas, sobran = [], []
    clave = (lambda p: -p['forma'].area) if orden == 'area' else \
        (lambda p: -max(p['forma'].bounds[2] - p['forma'].bounds[0], p['forma'].bounds[3] - p['forma'].bounds[1]))
    for pz in sorted(piezas, key=clave):
        listo = False
        for i, libre in enumerate(libres):
            if libre.area < pz['forma'].area:
                continue
            x0, y0, x1, y1 = libre.bounds
            W, H = int(math.ceil((x1 - x0) / r)) + 2, int(math.ceil((y1 - y0) / r)) + 2
            bloqueado = 1 - rasterizar(libre, r, W, H, x0, y0)
            for o in ocupado[i]:
                bloqueado |= rasterizar(o, r, W, H, x0, y0)
            bloqueado = bloqueado.astype(np.float32)
            mejor = None
            for ang in c['rotaciones']:
                f = rotate(pz['forma'], ang, origin=(0, 0)).buffer(sep / 2 + r * 0.75)
                fx0, fy0, fx1, fy1 = f.bounds
                tw, th = int(math.ceil((fx1 - fx0) / r)) + 1, int(math.ceil((fy1 - fy0) / r)) + 1
                if tw > W or th > H:
                    continue
                res = cv2.matchTemplate(bloqueado, rasterizar(f, r, tw, th, fx0, fy0).astype(np.float32), cv2.TM_CCORR)
                ok = res < 0.5
                if not ok.any():
                    continue
                arriba = np.ones_like(ok); arriba[1:] = ~ok[:-1]
                izq = np.ones_like(ok); izq[:, 1:] = ~ok[:, :-1]
                ys, xs = np.where(ok & arriba & izq)        # esquinas: pegadas arriba y a la izquierda
                bx0, by0 = x0 + xs * r, y0 + ys * r
                bx1, by1 = bx0 + (fx1 - fx0), by0 + (fy1 - fy0)
                if modo == 'arriba':
                    nota = (by0 - y0) * 1e4 + (bx0 - x0)
                elif modo == 'izquierda':
                    nota = (bx0 - x0) * 1e4 + (by0 - y0)
                else:
                    if caja[i]:
                        cx0, cy0, cx1, cy1 = caja[i]
                        area = (np.maximum(bx1, cx1) - np.minimum(bx0, cx0)) * (np.maximum(by1, cy1) - np.minimum(by0, cy0))
                    else:
                        area = np.zeros(len(xs))
                    nota = area + (by0 - y0 + bx0 - x0) * 1e-3   # compacto; la primera, en la esquina
                k = int(np.argmin(nota))
                if mejor is None or nota[k] < mejor[0]:
                    mejor = (nota[k], ys[k], xs[k], ang, fx0, fy0)
            if mejor:
                _, yy, xx, ang, fx0, fy0 = mejor
                mx, my = x0 + xx * r - fx0, y0 + yy * r - fy0
                forma = translate(rotate(pz['forma'], ang, origin=(0, 0)), mx, my)
                ocupado[i].append(forma.buffer(sep / 2))
                b = forma.bounds
                caja[i] = b if caja[i] is None else (min(b[0], caja[i][0]), min(b[1], caja[i][1]),
                                                    max(b[2], caja[i][2]), max(b[3], caja[i][3]))
                puestas.append({'pieza': pz, 'ang': ang, 'dx': mx, 'dy': my, 'forma': forma})
                listo = True
                break
        if not listo:
            sobran.append(pz)
    return puestas, sobran


def mover(pts, ang, dx, dy):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    x, y = pts[:, 0], pts[:, 1]
    return np.stack([x * ca - y * sa + dx, x * sa + y * ca + dy], 1)


# ---------------------------------------------------------------- archivos de salida
def guardar_dxf(ruta, lineas, c):
    """DXF R12 simple (lo abren RDWorks, LightBurn y Corel). y de la cama hacia abajo → y del DXF hacia arriba."""
    W, H = c['cama_ancho_mm'], c['cama_alto_mm']
    marco = [((0, 0), (W, 0), (W, H), (0, H), (0, 0)), ]
    out = ['0', 'SECTION', '2', 'ENTITIES']
    def poli(pts, capa, color, cerrado):
        out.extend(['0', 'POLYLINE', '8', capa, '62', str(color), '66', '1', '10', '0.0', '20', '0.0', '30', '0.0',
                    '70', '1' if cerrado else '0'])
        for x, y in pts:
            out.extend(['0', 'VERTEX', '8', capa, '10', f'{x:.3f}', '20', f'{H - y:.3f}', '30', '0.0'])
        out.extend(['0', 'SEQEND', '8', capa])
    for pts in marco:
        poli(pts[:-1], 'MARCO_NO_CORTAR', COLOR_DXF['marco'], True)
    for pts, tipo in lineas:
        pts = [tuple(p) for p in pts]
        cerrado = len(pts) > 2 and math.dist(pts[0], pts[-1]) < 0.05
        poli(pts[:-1] if cerrado else pts, tipo.upper(), COLOR_DXF[tipo], cerrado)
    out.extend(['0', 'ENDSEC', '0', 'EOF'])
    with open(ruta, 'w', encoding='ascii', newline='\r\n') as f:
        f.write('\n'.join(out) + '\n')


def guardar_svg(ruta, lineas, c, rellenar=None):
    W, H = c['cama_ancho_mm'], c['cama_alto_mm']
    col = {'corte': '#FF0000', 'grabado': '#0000FF', 'patron': '#000000'}
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
         f'<rect x="0" y="0" width="{W}" height="{H}" fill="none" stroke="#FF00FF" stroke-width="0.3"/>']
    if rellenar:
        for p in rellenar:
            d = ' '.join('M' + ' L'.join(f'{x:.3f},{y:.3f}' for x, y in ring.coords) + ' Z'
                         for ring in [p.exterior, *p.interiors])
            s.append(f'<path d="{d}" fill="#000000" fill-rule="evenodd" stroke="none"/>')
    else:
        for pts, tipo in lineas:
            d = 'M' + ' L'.join(f'{x:.3f},{y:.3f}' for x, y in pts)
            s.append(f'<path d="{d}" fill="none" stroke="{col[tipo]}" stroke-width="0.1"/>')
    s.append('</svg>')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('\n'.join(s))


def abrir(ruta):
    try:
        if os.name == 'nt':
            os.startfile(ruta)
    except Exception:
        pass


def preguntar(texto, defecto):
    try:
        v = input(f'{texto} [{defecto}]: ').strip().replace(',', '.')
    except EOFError:
        v = ''
    return type(defecto)(v) if v else defecto


def cmd_acomodar(c, a):
    cal = leer_cal()
    r = c['resolucion_mm']
    archivos = []
    for arg in a.piezas:
        ruta, _, n = arg.partition('=')
        archivos.append((ruta, int(n) if n else None))
    if not archivos:
        sys.exit('ERROR dime qué SVG acomodar (arrástralo encima de "3 ACOMODAR.bat").')
    grosor = a.grosor if a.grosor is not None else preguntar('Grosor del material en mm', 3.0)
    if a.copias is not None:
        copias = a.copias
    elif all(n for _, n in archivos):
        copias = 1
    else:
        copias = preguntar('Copias de cada pieza', 1)
    piezas = []
    for ruta, n in archivos:
        trazos = leer_svg(ruta)
        if not trazos:
            print(f'OJO {os.path.basename(ruta)}: no encontré trazos para cortar')
        ps = piezas_de(trazos, a.bloque)
        for pz in ps:
            pz['archivo'] = os.path.basename(ruta)
        piezas += ps * (n or copias)
        print(f'{os.path.basename(ruta)}: {len(ps)} pieza(s) x {n or copias}')
    img = tomar_foto(c, a.foto)
    os.makedirs(salida, exist_ok=True)
    vista = enderezar(img, cal, c)
    if a.manual:
        retazos = [Polygon(np.array(p) * r).buffer(0) for p in dibujar_retazos(vista)]
    else:
        ruta_fondo = os.path.join(datos, 'fondo.png')
        if not os.path.isfile(ruta_fondo):
            sys.exit('ERROR falta la foto de la cama vacía: corre "fondo" (o usa --manual).')
        retazos, _ = detectar_retazos(vista, cv2.imread(ruta_fondo), c)
        if not retazos:
            print('No encontré retazos automáticamente: pasa a modo manual.')
            retazos = [Polygon(np.array(p) * r).buffer(0) for p in dibujar_retazos(vista)]
    retazos = [corregir_grosor(p, cal, c, grosor) for p in retazos if p.area > 0]
    print(f'{len(retazos)} retazo(s): ' + ', '.join(f'{p.area / 100:.0f} cm²' for p in sorted(retazos, key=lambda p: -p.area)))
    t0 = time.time()
    puestas, sobran = acomodar(piezas, retazos, c)
    print(f'Acomodé {len(puestas)} de {len(piezas)} piezas en {time.time() - t0:.1f} s.')
    if sobran:
        cuenta = {}
        for p in sobran:
            b = p['forma'].bounds
            k = f'{p["archivo"]} ({b[2] - b[0]:.0f} x {b[3] - b[1]:.0f} mm)'
            cuenta[k] = cuenta.get(k, 0) + 1
        print('NO cupieron: ' + ', '.join(f'{n} x {k}' for k, n in cuenta.items()))
    lineas = [(mover(pts, q['ang'], q['dx'], q['dy']), tipo) for q in puestas for pts, tipo, _ in q['pieza']['trazos']]
    nombre = time.strftime('corte %Y-%m-%d %H%M')
    guardar_dxf(os.path.join(salida, nombre + '.dxf'), lineas, c)
    guardar_svg(os.path.join(salida, nombre + '.svg'), lineas, c)
    # vista previa sobre la foto enderezada
    v = vista.copy()
    for p in retazos:
        for ring in [p.exterior, *p.interiors]:
            cv2.polylines(v, [np.int32(np.array(ring.coords) / r)], True, (0, 255, 0), 2)
        for q in [p.buffer(-c['margen_mm'])] if not p.buffer(-c['margen_mm']).is_empty else []:
            for g in (q.geoms if hasattr(q, 'geoms') else [q]):
                cv2.polylines(v, [np.int32(np.array(g.exterior.coords) / r)], True, (0, 160, 0), 1)
    capa = v.copy()
    for q in puestas:
        cv2.fillPoly(capa, [np.int32(np.array(q['forma'].exterior.coords) / r)], (0, 0, 255))
    v = cv2.addWeighted(capa, 0.35, v, 0.65, 0)
    for pts, tipo in lineas:
        cv2.polylines(v, [np.int32(pts / r)], False, (0, 0, 255) if tipo == 'corte' else (255, 0, 0), 1)
    cv2.putText(v, f'{len(puestas)} de {len(piezas)} piezas', (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3)
    cv2.imwrite(os.path.join(salida, nombre + ' vista.jpg'), v)
    print(f'OK salida/{nombre}.dxf  (ábrelo en RDWorks · posición ABSOLUTA · capa MAGENTA en Salida: No)')
    print(f'   revisa salida/{nombre} vista.jpg antes de cortar')
    abrir(os.path.join(salida, nombre + ' vista.jpg'))
    return puestas, sobran, retazos


def main():
    ap = argparse.ArgumentParser(description='Cámara para acomodar piezas en retazos del láser')
    ap.add_argument('comando', choices=['patron', 'probar', 'calibrar', 'fondo', 'acomodar'])
    ap.add_argument('piezas', nargs='*', help='SVG de las piezas (archivo.svg o archivo.svg=3 para 3 copias)')
    ap.add_argument('--foto', help='usar esta foto en vez de la cámara')
    ap.add_argument('--grosor', type=float, help='grosor del material en mm')
    ap.add_argument('--copias', type=int, help='copias de cada pieza')
    ap.add_argument('--manual', action='store_true', help='marcar los retazos a mano con clics')
    ap.add_argument('--bloque', action='store_true', help='todo el SVG como una sola pieza (no separar)')
    a = ap.parse_args()
    c = cfg()
    {'patron': cmd_patron, 'probar': cmd_probar, 'calibrar': cmd_calibrar, 'fondo': cmd_fondo,
     'acomodar': cmd_acomodar}[a.comando](c, a)


if __name__ == '__main__':
    main()
