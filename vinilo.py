# Paneles para imprimir en vinilo y forrar el MDF: textura negra tipo melamina RH con veta suave, a tamaño real
# (medidas de generar.py + sangrado para envolver cantos). Rectángulos: se pega el vinilo y se recorta al borde.
#   python vinilo.py        → vinilo/*.jpg (150 dpi, tamaño real) + vinilo/TODO vinilo.pdf + vinilo/muestra.png
import os
import numpy as np
from PIL import Image
import generar as g

DPI = 150
SANGRADO = 30.0          # mm por lado: 12 del canto + 18 de vuelta
BASE, VETA, GRANO = 24, 2.5, 1.2     # gris del negro (0-255), contraste de la veta y del granito: muy bajo, casi liso
aqui = os.path.dirname(os.path.abspath(__file__))
salida = os.path.join(aqui, 'vinilo')


def px(mm):
    return int(round(mm / 25.4 * DPI))


def ruido(h, w, alto, largo, rng):
    """Ruido suave estirado a lo largo (la veta corre horizontal)."""
    chico = rng.random((max(2, h // alto), max(2, w // largo))).astype(np.float32)
    return np.asarray(Image.fromarray(chico, 'F').resize((w, h), Image.BICUBIC))


def textura(ancho_mm, alto_mm, semilla):
    w, h = px(ancho_mm), px(alto_mm)
    rng = np.random.default_rng(semilla)
    v = 0.7 * ruido(h, w, 8, 600, rng) + 0.3 * ruido(h, w, 3, 250, rng)
    v = (v - v.mean()) / (v.std() + 1e-6)
    img = BASE + VETA * np.tanh(v) + GRANO * rng.standard_normal((h, w)).astype(np.float32)
    gris = np.clip(img, 0, 255).astype(np.uint8)
    return Image.merge('RGB', [Image.fromarray(gris)] * 3)


def paneles():
    m = {p.nombre: p.final.bounds for p in g.estructura() if g.color_de(p.nombre) == 'mdf'}
    ancho = lambda b: b[2] - b[0]
    alto = lambda b: b[3] - b[1]
    c, f, z = m['COSTADO IZQ'], (m['FONDO IZQ'][0], 0, m['FONDO DER'][2], m['FONDO DER'][3]), \
        (m['ZOCALO IZQ'][0], 0, m['ZOCALO DER'][2], m['ZOCALO DER'][3])
    return [  # (nombre, ancho, alto de la pieza en mm, cuántos)
        ('COSTADO afuera', ancho(c), alto(c), 2),
        ('COSTADO adentro', ancho(c), alto(c), 2),
        ('FONDO frente (una sola pieza que cruza el centro)', ancho(f), alto(f), 1),
        ('ZOCALO frente (una sola tira)', ancho(z), alto(z), 1),
    ]


if __name__ == '__main__':
    os.makedirs(salida, exist_ok=True)
    hojas, total = [], 0.0
    for i, (nom, a, h, n) in enumerate(paneles()):
        A, H = a + 2 * SANGRADO, h + 2 * SANGRADO
        img = textura(A, H, 7 + i)
        ruta = os.path.join(salida, f'{nom.split(" (")[0]} - imprimir {n} - {A / 10:.0f} x {H / 10:.0f} cm.jpg')
        img.save(ruta, quality=92, dpi=(DPI, DPI))
        hojas += [img] * n
        total += n * A * H / 1e6
        print(f'{os.path.basename(ruta)}  ({n} copia(s); pieza {a / 10:.1f} x {h / 10:.1f} cm + {SANGRADO / 10:g} cm de sangrado)')
    hojas[0].save(os.path.join(salida, 'TODO vinilo.pdf'), save_all=True, append_images=hojas[1:], resolution=DPI)
    muestra = textura(300, 300, 99)
    muestra.resize((600, 600)).save(os.path.join(salida, 'muestra.png'))
    print(f'vinilo total: {total:.2f} m² (sin contar desperdicio del rollo)')
