@echo off
rem Instala lo que necesita el programa de la camara. Solo la primera vez.
cd /d "%~dp0"
python -m pip install --upgrade opencv-python numpy shapely svgelements
pause
