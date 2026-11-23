# ==============================================================================
# START_APP.PS1 — Lanzador de 1 Clic para Backend y Frontend
# Precalificación Crediticia Automatizada (CRISP-ML(Q))
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Iniciando Sistema de Precalificación Crediticia (MLOps)" -ForegroundColor Green
Write-Host " UCB San Pablo - Trabajo Final de Grado" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ROOT_DIR = $PSScriptRoot
$EscapedPythonExe = "$ROOT_DIR\.venv\Scripts\python.exe".Replace("'", "''")

# 0. Asegurar entorno virtual Python si es primera ejecución tras clonar
$PythonExe = "$ROOT_DIR\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[SETUP] Primera ejecución detectada: Creando entorno virtual .venv..." -ForegroundColor Cyan
    python -m venv "$ROOT_DIR\.venv"
    Write-Host "[SETUP] Instalando dependencias de producción..." -ForegroundColor Cyan
    & "$PythonExe" -m pip install --upgrade pip
    & "$PythonExe" -m pip install -r "$ROOT_DIR\requirements.txt"
}

# 1. Iniciar Backend FastAPI en una ventana independiente con directorio de trabajo explícito y rutas escapadas (Qodo Finding 7)
Write-Host "[1/3] Lanzando Backend API REST (FastAPI) en http://127.0.0.1:8000..." -ForegroundColor Yellow
$BackendCmd = "& '$EscapedPythonExe' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -WorkingDirectory "$ROOT_DIR\backend" -ArgumentList "-NoExit", "-Command", $BackendCmd

# 2. Iniciar Frontend Web en una ventana independiente con directorio de trabajo explícito
Write-Host "[2/3] Lanzando Frontend Web en http://localhost:3000..." -ForegroundColor Yellow
$FrontendCmd = "python -m http.server 3000"
Start-Process powershell -WorkingDirectory "$ROOT_DIR\frontend" -ArgumentList "-NoExit", "-Command", $FrontendCmd

# 3. Esperar inicialización y abrir navegador automáticamente
Start-Sleep -Seconds 2
Write-Host "[3/3] Abriendo navegador en la aplicación web..." -ForegroundColor Green
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "¡Sistema levantado con éxito!" -ForegroundColor Green
Write-Host " - Frontend Web:    http://localhost:3000" -ForegroundColor White
Write-Host " - Swagger API:     http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host " - Autenticación:   Credenciales configuradas en .env o variables de entorno" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
