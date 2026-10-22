# Protectores para imprimir en 3D (PETG): tapan las orillas del vinilo y protegen el MDF del agua.
#   1) ESQUINERO PATA x4: esquinas de abajo (costado + zócalo / costado + fondo). Levanta el mueble 3 mm de la mesa.
#   2) ESQUINERO TRIANGULAR x2: esquinas de arriba del fondo (canto de un tablero de 12 mm): triángulo por las 2 caras.
#   3) CANTO U: tramo recto que se mete en el canto del MDF donde termina el vinilo (los que necesites).
import os, math
import numpy as np
import trimesh
from shapely.geometry import Polygon, box as sbox
from shapely.affinity import translate

aqui = os.path.dirname(os.path.abspath(__file__))
salida = os.path.join(aqui, 'Impresion 3D')
os.makedirs(salida, exist_ok=True)

MDF = 12.0 + 0.6        # MDF 12 mm + vinilo en las 2 caras + juego para que entre sin forzar
W = 2.4                 # grosor de pared impresa
L = 45.0                # largo de cada brazo
P = 3.0                 # grosor de la base de la pata (lo que levanta el mueble)
H = 45.0                # alto del esquinero pata en la esquina


def extruir(poly, h, eje='z'):
    m = trimesh.creation.extrude_polygon(poly, h)
    if eje == 'x':      # polígono en (y, z), grosor en x
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    return m


def unir(ms):
    return trimesh.boolean.union(ms, engine='manifold')


def pared(perfil, mapa):
    """Extruye un perfil (u, v) con grosor W y reacomoda los ejes con `mapa(u, v, e) -> (x, y, z)`."""
    m = trimesh.creation.extrude_polygon(perfil, W)
    v = m.vertices.copy()
    m.vertices = np.array([mapa(p[0], p[1], p[2]) for p in v])
    m.fix_normals()
    return m


def esquinero_pata():
    """Esquina de abajo, por fuera. El mueble ocupa x>0, y>0, z>0 (z = alto).
    Base de 3 mm debajo de la esquina + 2 paredes triangulares (altas en la esquina, bajas en la punta)."""
    base = trimesh.creation.box(bounds=[[-W, -W, -P], [L, L, 0]])
    perfil = Polygon([(-W, -P), (L, -P), (L, 8), (-W, H)])                      # (largo, alto)
    frente = pared(perfil, lambda u, v, e: (u, e - W, v))                        # sobre la cara y = 0
    costado = pared(perfil, lambda u, v, e: (e - W, u, v))                       # sobre la cara x = 0
    m = unir([base, frente, costado])
    # redondear la arista vertical de afuera
    corte = trimesh.creation.box(bounds=[[-W - 1, -W - 1, -P - 1], [0, 0, H + 1]])
    m = trimesh.boolean.difference([m, corte], engine='manifold')
    cil = trimesh.creation.cylinder(radius=W, height=H + P, sections=48); cil.apply_translation([0, 0, (H - P) / 2])
    cuarto = trimesh.boolean.intersection([cil, trimesh.creation.box(bounds=[[-W, -W, -P], [0, 0, H]])], engine='manifold')
    return unir([m, cuarto])


def esquinero_triangular():
    """Esquina de un tablero de 12 mm (arriba del fondo). Tablero: x>0, y<0, grosor en z de 0 a MDF.
    Triángulo en las 2 caras + tapa de los 2 cantos."""
    tri = Polygon([(-W, W), (L, W), (-W, -L)])
    cara1 = trimesh.creation.extrude_polygon(tri, W); cara1.apply_translation([0, 0, -W])
    cara2 = trimesh.creation.extrude_polygon(tri, W); cara2.apply_translation([0, 0, MDF])
    canto_sup = trimesh.creation.box(bounds=[[-W, 0, -W], [L, W, MDF + W]])          # tapa el canto de arriba
    canto_lat = trimesh.creation.box(bounds=[[-W, -L, -W], [0, W, MDF + W]])         # tapa el canto del lado
    return unir([cara1, cara2, canto_sup, canto_lat])


def canto_u(largo=120.0, alas=8.0):
    """Perfil en U que se mete sobre el canto del MDF (donde termina el vinilo)."""
    perfil = Polygon([(-W, -alas), (-W, MDF + 0), (0, MDF), (0, 0), (MDF, 0), (MDF, -alas), (MDF + W, -alas),
                      (MDF + W, W), (-W, W)])
    perfil = sbox(-W, -alas, MDF + W, W).difference(sbox(0, -alas - 1, MDF, 0))
    m = trimesh.creation.extrude_polygon(perfil, largo)
    return m


def calce_soporte(largo=50.0, ancho=16.0, ranura=5.6, prof=4.0):
    """Calce de 3 mm para el canto de abajo del soporte transparente del centro (que quede a la altura de las patas).
    Tiene una ranura donde entra el soporte de 5 mm para que no se corra."""
    m = trimesh.creation.box(bounds=[[0, 0, 0], [largo, ancho, P + prof]])
    r = trimesh.creation.box(bounds=[[-1, (ancho - ranura) / 2, P], [largo + 1, (ancho + ranura) / 2, P + prof + 1]])
    return trimesh.boolean.difference([m, r], engine='manifold')


piezas = {
    'Esquinero pata (imprimir 4)': esquinero_pata(),
    'Esquinero triangular arriba del fondo (imprimir 2)': esquinero_triangular(),
    'Canto U recto 12cm (imprimir los que necesites)': canto_u(),
    'Calce soporte central (imprimir 2)': calce_soporte(),
}
for nombre, m in piezas.items():
    m.export(os.path.join(salida, nombre + '.stl'))
    e = m.bounds[1] - m.bounds[0]
    print(f'{nombre}: {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm · {m.volume / 1000:.1f} cm3 · cerrado={m.is_watertight}')

# vista previa
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
fig = plt.figure(figsize=(18, 5), dpi=100)
for k, (nombre, m) in enumerate(piezas.items()):
    ax = fig.add_subplot(1, 4, k + 1, projection='3d')
    luz = np.array([0.4, -0.5, 0.8]); luz /= np.linalg.norm(luz)
    tono = 0.35 + 0.65 * np.clip(m.face_normals @ luz, 0, 1)
    ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolors=[(0.15 * s + 0.1, 0.15 * s + 0.1, 0.17 * s + 0.12) for s in tono], edgecolor='none'))
    mn, mx = m.bounds; c = (mn + mx) / 2; r = (mx - mn).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(22, -135 if k == 0 else -55); ax.set_axis_off(); ax.set_title(nombre, fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(salida, 'Protectores 3D vista.png'))
