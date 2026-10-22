# Pone un SVG en Corel en un documento NUEVO del tamaño exacto y lo guarda como .cdr (sin depender de macros).
#   python poner_cdr.py <svg> <nombre> <ancho_mm>
import os, sys, time
import win32com.client

svg, nombre, ancho = os.path.abspath(sys.argv[1]), sys.argv[2], float(sys.argv[3])
dest_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'FRIPHER HD', 'Vectores')
os.makedirs(dest_dir, exist_ok=True)
cdr = os.path.join(dest_dir, nombre + '.cdr')
n = 2
while os.path.exists(cdr):
    cdr = os.path.join(dest_dir, f'{nombre} ({n}).cdr'); n += 1

app = win32com.client.Dispatch('CorelDRAW.Application')
doc = app.CreateDocument()
doc.Unit = 3                                  # milímetros
lay = doc.ActiveLayer
doc.ClearSelection()
opts = app.CreateStructImportOptions()
lay.Import(svg, 0, opts)
sel = app.ActiveSelectionRange
if sel.Count == 0:
    sys.exit('ERROR Corel no importó el archivo')
grupo = sel.Group() if sel.Count > 1 else sel.Item(1)
grupo.SetSize(ancho, grupo.SizeHeight * ancho / grupo.SizeWidth)
doc.ActivePage.SetSize(grupo.SizeWidth, grupo.SizeHeight)
grupo.Move(doc.ActivePage.LeftX - grupo.LeftX, doc.ActivePage.TopY - grupo.TopY)
grupo.Name = nombre
doc.SaveAs(cdr, app.CreateStructSaveAsOptions())
print(f'OK {os.path.basename(cdr)} · {grupo.SizeWidth / 10:.1f} x {grupo.SizeHeight / 10:.1f} cm · {cdr}')
