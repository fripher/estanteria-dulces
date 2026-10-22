# Puente nube <-> PC: revisa GitHub cada 30 s, ejecuta las órdenes nuevas de puente/ordenes/ y sube el
# resultado a puente/resultados/. Solo hace las acciones de ACCIONES (nunca comandos libres ni el láser).
# Solo Windows, con Git, Python + pywin32 y CorelDRAW 2024.
#   python puente\puente_pc.py          (o doble clic en "INICIAR PUENTE.bat")
import glob, json, os, re, shutil, subprocess, sys, time, traceback, urllib.request

ESPERA = 30                                    # segundos entre revisiones
puente = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(puente)
ordenes, resultados = os.path.join(puente, 'ordenes'), os.path.join(puente, 'resultados')
vectores = os.path.join(os.path.expanduser('~'), 'Documents', 'FRIPHER HD', 'Vectores')
NOMBRE_OK = re.compile(r'^[\w áéíóúÁÉÍÓÚñÑ().,+-]{1,80}$')


def git(*args, revisar=True):
    r = subprocess.run(['git', '-c', 'user.name=Puente PC', '-c', 'user.email=puente@localhost', *args],
                       cwd=raiz, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if revisar and r.returncode:
        raise RuntimeError(f'git {" ".join(args)}: {r.stderr.strip() or r.stdout.strip()}')
    return r.stdout.strip()


def limpiar(texto):
    """Quita la ruta de la carpeta del usuario de lo que se sube."""
    return str(texto).replace(os.path.expanduser('~'), '~')


def repo_publico():
    """Sin login, GitHub solo muestra el repo si es público (si es privado da 404)."""
    url = re.sub(r'\.git$', '', git('remote', 'get-url', 'origin'))
    m = re.search(r'github\.com[/:]([^/]+/[^/]+)$', url)
    if not m:
        return True
    try:
        with urllib.request.urlopen(f'https://api.github.com/repos/{m.group(1)}', timeout=15) as r:
            return not json.load(r).get('private', False)
    except Exception:
        return False


def corel():
    import win32com.client
    return win32com.client.Dispatch('CorelDRAW.Application')


def correr(cmd, limite):
    r = subprocess.run(cmd, cwd=raiz, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=limite)
    salida = (r.stdout + ('\n' + r.stderr if r.stderr else '')).strip()
    if r.returncode:
        raise RuntimeError(f'terminó con error {r.returncode}:\n{salida}')
    return salida


def ruta_en_repo(rel, extension):
    ruta = os.path.realpath(os.path.join(raiz, rel))
    if not ruta.startswith(os.path.realpath(raiz) + os.sep) or not ruta.lower().endswith(extension):
        raise ValueError(f'ruta no permitida: {rel}')
    if not os.path.isfile(ruta):
        raise FileNotFoundError(f'no existe en el repo: {rel}')
    return ruta


def nombre_estanteria(nombre):
    """Solo se tocan los documentos de la estantería, para no subir trabajos de otros clientes."""
    nombre = os.path.splitext(nombre)[0]
    if not NOMBRE_OK.match(nombre) or not nombre.startswith('Estanteria 140 - '):
        raise ValueError(f'nombre no permitido (debe empezar por "Estanteria 140 - "): {nombre}')
    return nombre


def documento(app, nombre):
    for d in app.Documents:
        if os.path.splitext(d.Name)[0] == nombre:
            return d
    raise LookupError(f'no está abierto en Corel: {nombre}')


# ---------------------------------------------------------------- acciones permitidas
def a_ping(args, oid):
    try:
        docs = [d.Name for d in corel().Documents]
        estado = f'Corel abierto, {len(docs)} documento(s)'
    except Exception as e:
        estado = f'Corel no responde: {e}'
    return f'puente OK · Python {sys.version.split()[0]} · {estado} · repo público: {PUBLICO}'


def a_documentos(args, oid):
    filas = []
    for d in corel().Documents:
        d.Unit = 3
        p = d.ActivePage
        filas.append(f'{d.Name} · {d.Pages.Count} pág · {p.SizeWidth / 10:.1f} x {p.SizeHeight / 10:.1f} cm'
                     f'{" · SIN GUARDAR" if d.Dirty else ""}')
    return '\n'.join(filas) or 'no hay documentos abiertos'


def a_importar_svg(args, oid):
    svg = ruta_en_repo(args['svg'], '.svg')
    nombre = nombre_estanteria(args['nombre'])
    ancho = float(args['ancho_mm'])
    if not 1 <= ancho <= 3000:
        raise ValueError(f'ancho fuera de rango: {ancho}')
    return correr([sys.executable, os.path.join(raiz, 'poner_cdr.py'), svg, nombre, str(ancho)], 300)


def a_abrir_cdr(args, oid):
    nombre = nombre_estanteria(args['nombre'])
    ruta = os.path.join(vectores, nombre + '.cdr')
    if not os.path.isfile(ruta):
        raise FileNotFoundError(f'no existe en Vectores: {nombre}.cdr')
    corel().OpenDocument(ruta)
    return f'abierto {nombre}.cdr'


def a_listar_vectores(args, oid):
    return '\n'.join(os.path.basename(f) for f in sorted(glob.glob(os.path.join(vectores, 'Estanteria 140 - *.cdr')))) \
        or 'no hay archivos "Estanteria 140 - *.cdr" en Vectores'


def a_exportar_png(args, oid):
    d = documento(corel(), nombre_estanteria(args['nombre']))
    png = os.path.join(resultados, oid + '.png')
    d.ExportBitmap(png, 802).Finish()           # 802 = cdrPNG
    return f'exportado {d.Name} -> puente/resultados/{oid}.png'


def a_captura_corel(args, oid):
    if PUBLICO:
        raise PermissionError('el repo es público: no subo capturas de pantalla. Hazlo privado y reinicia el puente.')
    png = os.path.join(resultados, oid + '.png')
    ps = r'''
Add-Type -AssemblyName System.Drawing
Add-Type 'using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
public struct R { public int L, T, X, B; }
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f); }'
$p = Get-Process CorelDRW -ErrorAction Stop | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
$h = $p.MainWindowHandle; $r = New-Object W+R; [W]::GetWindowRect($h, [ref]$r) | Out-Null
$b = New-Object Drawing.Bitmap ($r.X - $r.L), ($r.B - $r.T); $g = [Drawing.Graphics]::FromImage($b)
$dc = $g.GetHdc(); [W]::PrintWindow($h, $dc, 2) | Out-Null; $g.ReleaseHdc($dc); $b.Save($env:PUENTE_PNG)
'''
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps], cwd=raiz,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60,
                       env={**os.environ, 'PUENTE_PNG': png})
    if r.returncode or not os.path.isfile(png):
        raise RuntimeError(f'no se pudo capturar Corel: {r.stderr.strip()}')
    return f'captura -> puente/resultados/{oid}.png'


def a_poner_todo(args, oid):
    salida = correr(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                     os.path.join(raiz, 'poner_todo.ps1')], 900)
    img = os.path.join(raiz, 'FRIPHER 3D armada.png')
    if os.path.isfile(img):                     # la imagen va al resultado; el archivo del repo queda igual
        shutil.copy(img, os.path.join(resultados, oid + '.png'))
        git('checkout', '--', 'FRIPHER 3D armada.png', revisar=False)
    return salida


ACCIONES = {
    'ping': a_ping,                     # ¿está vivo el puente y Corel?
    'documentos': a_documentos,         # documentos abiertos en Corel
    'listar_vectores': a_listar_vectores,
    'importar_svg': a_importar_svg,     # {svg, nombre, ancho_mm}: SVG del repo -> .cdr nuevo en Vectores
    'abrir_cdr': a_abrir_cdr,           # {nombre}
    'exportar_png': a_exportar_png,     # {nombre}: página activa a PNG
    'captura_corel': a_captura_corel,   # captura de la ventana de Corel (solo si el repo es privado)
    'poner_todo': a_poner_todo,         # poner_todo.ps1 completo (Corel + FRIPHER 3D)
}


# ---------------------------------------------------------------- ciclo
def hacer(ruta):
    oid = os.path.splitext(os.path.basename(ruta))[0]
    res = {'id': oid, 'inicio': time.strftime('%Y-%m-%d %H:%M:%S')}
    try:
        with open(ruta, encoding='utf-8') as f:
            orden = json.load(f)
        res['accion'] = accion = orden.get('accion')
        if accion not in ACCIONES:
            raise ValueError(f'acción no permitida: {accion}. Permitidas: {", ".join(ACCIONES)}')
        print(f'[{res["inicio"]}] {oid}: {accion} ...', flush=True)
        res['salida'] = limpiar(ACCIONES[accion](orden.get('args', {}), oid))
        res['ok'] = True
    except Exception as e:
        res['ok'], res['error'] = False, limpiar(f'{type(e).__name__}: {e}')
        res['detalle'] = limpiar(traceback.format_exc(limit=3))
    res['fin'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(os.path.join(resultados, oid + '.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f'    {"OK" if res["ok"] else "ERROR"}: {res.get("salida") or res.get("error")}', flush=True)
    git('add', '--', 'puente/resultados')
    git('commit', '-m', f'puente: resultado {oid} ({res.get("accion")})', revisar=False)


def ciclo():
    git('pull', '--rebase', '--autostash', '-q')
    for ruta in sorted(glob.glob(os.path.join(ordenes, '*.json'))):
        if not os.path.exists(os.path.join(resultados, os.path.splitext(os.path.basename(ruta))[0] + '.json')):
            hacer(ruta)
    if 'ahead' in git('status', '-sb').splitlines()[0]:
        git('pull', '--rebase', '--autostash', '-q')
        git('push', '-q')
        print('    resultados subidos a GitHub', flush=True)


if __name__ == '__main__':
    os.makedirs(resultados, exist_ok=True)
    git('rev-parse', '--git-dir')
    PUBLICO = repo_publico()
    print(f'Puente listo en la rama {git("rev-parse", "--abbrev-ref", "HEAD")}. Reviso GitHub cada {ESPERA} s.')
    print('Repo PÚBLICO: no se suben capturas.' if PUBLICO else 'Repo privado: capturas permitidas.')
    print('Para parar: Ctrl+C o cerrar esta ventana.\n', flush=True)
    while True:
        try:
            ciclo()
        except Exception as e:
            print(f'[{time.strftime("%H:%M:%S")}] no se pudo sincronizar: {limpiar(e)}', flush=True)
        time.sleep(ESPERA)
