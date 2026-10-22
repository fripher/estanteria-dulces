# Lado nube: crea una orden para el puente y muestra resultados.
#   python puente/orden.py ping
#   python puente/orden.py importar_svg svg="Corte acrilico 5mm ... (1 de 3).svg" nombre="Estanteria 140 - ..." ancho_mm=1200
#   python puente/orden.py --ver [id]        (último resultado, o el de ese id)
import glob, json, os, sys

puente = os.path.dirname(os.path.abspath(__file__))
ordenes, resultados = os.path.join(puente, 'ordenes'), os.path.join(puente, 'resultados')

if sys.argv[1] == '--ver':
    hechos = sorted(glob.glob(os.path.join(resultados, '*.json')))
    ruta = os.path.join(resultados, sys.argv[2] + '.json') if len(sys.argv) > 2 else (hechos or [None])[-1]
    print(open(ruta, encoding='utf-8').read() if ruta and os.path.exists(ruta) else 'todavía no hay resultado')
    sys.exit()

os.makedirs(ordenes, exist_ok=True)
numeros = [int(os.path.basename(f)[:4]) for f in glob.glob(os.path.join(ordenes, '[0-9]' * 4 + '*.json'))]
oid = f'{max(numeros, default=0) + 1:04d}-{sys.argv[1]}'
args = dict(a.split('=', 1) for a in sys.argv[2:])
with open(os.path.join(ordenes, oid + '.json'), 'w', encoding='utf-8') as f:
    json.dump({'accion': sys.argv[1], 'args': args}, f, ensure_ascii=False, indent=2)
print(f'orden puente/ordenes/{oid}.json')
