@echo off
rem Arrastra uno o varios SVG encima de este archivo.
cd /d "%~dp0"
python laser_camara.py acomodar %*
pause
