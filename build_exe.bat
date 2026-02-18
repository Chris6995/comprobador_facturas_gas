@echo off
setlocal

echo [1/4] Creando entorno virtual si no existe...
if not exist .venv (
  py -m venv .venv
)

echo [2/4] Activando entorno...
call .venv\Scripts\activate

echo [3/4] Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo [4/4] Generando EXE...
pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --name ValidadorXML ^
  --collect-all streamlit ^
  --add-data "app_chatgpt.py;." ^
  --add-data "backend_chatgpt.py;." ^
  --add-data "data;data" ^
  launcher_streamlit.py

echo.
echo EXE generado en: dist\ValidadorXML.exe
echo.
