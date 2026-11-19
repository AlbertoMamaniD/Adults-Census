# 🚀 Guía de Ejecución y Replicabilidad del Backend (API REST)

**Servicio de Precalificación Crediticia Automatizada — Metodología CRISP-ML(Q)**  
**Autor:** Alberto Esteban Mamani Donaire  
**Institución:** Universidad Católica Boliviana "San Pablo" (Sede Tarija)  

Este documento detalla los pasos exactos y reproducibles para levantar y probar el servidor FastAPI localmente en cualquier equipo.

---

## 📋 1. Requisitos Previos

* **Python:** Versión `3.11.x` instalada (Importante: evitar Python 3.14 por incompatibilidad binaria de paquetes C en NumPy).
* **Git:** Para clonar y gestionar el repositorio.
* **PowerShell / Terminal:** Con permisos de ejecución de scripts para activar entornos virtuales.

---

## ⚡ 2. Pasos Rápidos de Puesta en Marcha (Windows PowerShell)

### Paso 1: Abrir la terminal en la raíz del proyecto
```powershell
cd C:\TALLERSIS4
```

### Paso 2: Activar el Entorno Virtual (`.venv`)
```powershell
.venv\Scripts\Activate.ps1
```
*(Si la política de ejecución de scripts de Windows está bloqueada, ejecuta previamente: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`).*

### Paso 3: Instalar Dependencias Fijadas
```powershell
pip install -r backend/requirements.txt
```

### Paso 4: Configurar Variables de Entorno (`.env`)
Asegúrate de que exista el archivo `.env` en la raíz con las credenciales de conexión:
```env
SUPABASE_DB_URL=postgresql+psycopg2://postgres.TU_PROJECT_ID:TU_PASSWORD@aws-1-us-west-2.pooler.supabase.com:5432/postgres
JWT_SECRET_KEY=clave_secreta_jwt_personalizada_para_desarrollo
ADMIN_USERNAME=analyst_admin
ADMIN_PASSWORD=clave_acceso_analista
```
> **Nota de Resiliencia:** Si no cuentas con internet o credenciales de Supabase, el sistema conmuta automáticamente a la base de datos local SQLite (`artifacts/local_database.db`).

### Paso 5: Ejecutar la Suite de Pruebas Automatizadas
Verifica que los 19 tests de frontera, seguridad y persistencia pasen al 100%:
```powershell
python -m unittest backend/tests/test_api.py -v
```

### Paso 6: Levantar el Servidor FastAPI
Ejecuta el script lanzador directo:
```powershell
python backend/run_server.py
```
*(O alternativamente vía Uvicorn directo):*
```powershell
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

---

## 🌐 3. Verificación y Acceso

Una vez levantado el servidor en `http://127.0.0.1:8000`:

* **Swagger UI Interactivo:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
  *(Permite probar los endpoints en vivo con formularios interactivos).*
* **ReDoc (Documentación Técnica):** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **Verificación de Salud:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🧪 4. Ejemplo Rápido de Predicción (cURL)

Abre otra ventana de terminal y ejecuta:

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/predict" `
     -H "Content-Type: application/json" `
     -d '{
       "age": 39,
       "workclass": "State-gov",
       "education_num": 13,
       "marital_status": "Never-married",
       "occupation": "Adm-clerical",
       "relationship": "Not-in-family",
       "race": "White",
       "sex": "Male",
       "capital_gain": 2174.0,
       "capital_loss": 0.0,
       "hours_per_week": 40,
       "native_country": "United-States"
     }'
```
