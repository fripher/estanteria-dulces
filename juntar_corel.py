# Une las camas de cada material en un solo SVG para Corel (una debajo de otra, con su marco)
import glob, re
import generar as G
grupos = {}
for f in sorted(glob.glob('Corte *.svg')):
    grupos.setdefault(re.sub(r' \(\d+ de \d+\)', '', f[:-4]), []).append(f)
W, H, salto = G.LAMINA[0], G.LAMINA[1], G.SALTO_HOJA
for base, fs in grupos.items():
    total = H + salto * (len(fs) - 1)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{total}mm" viewBox="0 0 {W} {total}">']
    for i, f in enumerate(fs):
        body = re.sub(r'^<svg[^>]*>', '', open(f, encoding='utf-8').read()).replace('</svg>', '')
        out.append(f'<g transform="translate(0,{i * salto})">{body}</g>')
    out.append('</svg>')
    open(f'Corel {base[6:]}.svg', 'w', encoding='utf-8').write('\n'.join(out))
    print(f'{base[6:]}: {len(fs)} camas')
