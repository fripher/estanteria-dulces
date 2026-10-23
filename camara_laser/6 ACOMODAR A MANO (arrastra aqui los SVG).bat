@echo off
rem Igual que el 5, pero tu marcas los retazos con clics (acrilico transparente, luz rara).
cd /d "%~dp0"
python laser_camara.py acomodar --manual %*
pause
