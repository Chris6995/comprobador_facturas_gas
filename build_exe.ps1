$ErrorActionPreference = "Stop"

Write-Host "[1/4] Creando entorno virtual si no existe..."
if (!(Test-Path ".venv")) {
    py -m venv .venv
}

Write-Host "[2/4] Activando entorno..."
& ".\.venv\Scripts\Activate.ps1"

Write-Host "[3/4] Instalando dependencias..."
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

Write-Host "[4/4] Generando EXE..."
pyinstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name ValidadorXML `
    --collect-all streamlit `
    --add-data "app.py;." `
    --add-data "backend.py;." `
    --add-data "data;data" `
    launcher_streamlit.py

Write-Host ""
Write-Host "EXE generado en: dist\ValidadorXML.exe"
Write-Host ""
