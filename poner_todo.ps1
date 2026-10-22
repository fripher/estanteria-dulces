# Reemplaza los archivos "Estanteria 140 - *" en Corel, arma la estantería en FRIPHER 3D y saca la imagen.
# Maneja FRIPHER 3D con mensajes de ventana (no mueve el mouse del usuario).
$ErrorActionPreference = 'Stop'
$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $aqui
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, System.Drawing
Add-Type @'
using System; using System.Runtime.InteropServices; using System.Text;
public class FV { public delegate bool P(IntPtr h, IntPtr l);
[DllImport("user32.dll")] public static extern bool EnumWindows(P p, IntPtr l);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
[DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, int m, IntPtr w, IntPtr l);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r); public struct RECT { public int L, T, R, B; }
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
public static void Clic(IntPtr h, int x, int y){ IntPtr lp = (IntPtr)((y << 16) | (x & 0xFFFF)); PostMessage(h, 0x200, IntPtr.Zero, lp); PostMessage(h, 0x201, (IntPtr)1, lp); PostMessage(h, 0x202, IntPtr.Zero, lp); }
public static IntPtr Ventana(uint pid){ IntPtr r=IntPtr.Zero; EnumWindows((h,l)=>{uint p; GetWindowThreadProcessId(h,out p); if(p==pid && IsWindowVisible(h)){var s=new StringBuilder(200); GetWindowText(h,s,200); if(s.ToString().StartsWith("FRIPHER 3D")){r=h; return false;}} return true;}, IntPtr.Zero); return r;} }
'@
$app = New-Object -ComObject CorelDRAW.Application
Get-Process Fripher3D -ErrorAction SilentlyContinue | Stop-Process
$v = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'FRIPHER HD\Vectores'
foreach ($d in @($app.Documents)) { if ($d.Name -like 'Estanteria 140 - *') { if ($d.Dirty) { throw "El documento $($d.Name) tiene cambios sin guardar; guárdalo o ciérralo primero." }; $d.Close() } }
Get-ChildItem $v -Filter 'Estanteria 140 - *' | Remove-Item
$s = "C:\Users\FRIPHER\Desktop\FRIPHER HD\redibujo\poner_en_corel.ps1"
foreach ($f in Get-ChildItem $aqui -Filter 'Corel *.svg') {
  $n = 'Estanteria 140 - ' + $f.BaseName.Substring(6)
  & powershell -ExecutionPolicy Bypass -File $s -Svg $f.FullName -Nombre $n -AnchoCm 120 }
$W = [double]((Select-String -Path "Estanteria ARMADO 3D.svg" -Pattern 'width="([\d.]+)mm"').Matches[0].Groups[1].Value)
& powershell -ExecutionPolicy Bypass -File $s -Svg "$aqui\Estanteria ARMADO 3D.svg" -Nombre "Estanteria 140 - ARMADO 3D" -AnchoCm ($W / 10)
foreach ($d in $app.Documents) { if ($d.Name -eq 'Estanteria 140 - ARMADO 3D.cdr') { $doc = $d; $d.Windows.Item(1).Activate() } }
$doc.Unit = 3; $doc.ActivePage.Shapes.All().UngroupAll() | Out-Null
foreach ($x in @($doc.ActivePage.Shapes.All())) { if ($x.SizeWidth -gt ($W - 10)) { $x.Delete() } }
$doc.ActivePage.Shapes.All().CreateSelection()
$app.GMSManager.RunMacro('FripherNeon', 'modFripher3D.Exportar3D', "$env:TEMP\est_export.txt"); $doc.Save()
python armar_fripher3d.py armado "$env:TEMP\est_export.txt" "$($doc.Name)"
# FRIPHER 3D
$doc.Windows.Item(1).Activate(); $doc.ActivePage.Shapes.All().CreateSelection()
$app.GMSManager.RunMacro('FripherNeon', 'modFripher3D.Abrir3D')
$h = [IntPtr]::Zero; for ($i = 0; $i -lt 30 -and $h -eq [IntPtr]::Zero; $i++) { Start-Sleep 1; $p = Get-Process Fripher3D -ErrorAction SilentlyContinue; if ($p) { $h = [FV]::Ventana($p[0].Id) } }
Start-Sleep 8; [FV]::ShowWindow($h, 9) | Out-Null; [FV]::SetForegroundWindow($h) | Out-Null; Start-Sleep 1
$w = [Windows.Automation.AutomationElement]::FromHandle($h)
function Todo { $w.FindAll([Windows.Automation.TreeScope]::Descendants, [Windows.Automation.Condition]::TrueCondition) }
$bt = @(Todo | Where-Object { $q = $_.Current.BoundingRectangle; [math]::Abs($q.Width - 88) -le 3 -and [math]::Abs($q.Height - 70) -le 3 } | Sort-Object { $_.Current.BoundingRectangle.Y }, { $_.Current.BoundingRectangle.X })
[FV]::Clic([IntPtr]$bt[7].Current.NativeWindowHandle, 44, 35)
$estado = ''; for ($i = 0; $i -lt 60 -and $estado -notmatch 'armadas'; $i++) { Start-Sleep 1; $estado = (Todo | Where-Object { $_.Current.Name -match 'armadas' } | Select-Object -First 1).Current.Name }
"FRIPHER 3D: $estado"
foreach ($n in @('3D', 'Centrar')) { $e = Todo | Where-Object { $_.Current.Name -eq $n } | Select-Object -First 1; [FV]::Clic([IntPtr]$e.Current.NativeWindowHandle, 20, 14); Start-Sleep 5 }
if ([FV]::IsIconic($h)) { [FV]::ShowWindow($h, 4) | Out-Null; Start-Sleep 2 }
$r = New-Object FV+RECT; [FV]::GetWindowRect($h, [ref]$r) | Out-Null
$bmp = New-Object Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T); $g = [Drawing.Graphics]::FromImage($bmp); $dc = $g.GetHdc(); [FV]::PrintWindow($h, $dc, 2) | Out-Null; $g.ReleaseHdc($dc)
$bmp.Save("$aqui\FRIPHER 3D armada.png"); "imagen OK"
