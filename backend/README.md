# 🏦 Backend: Servicio de Inteligencia Artificial (API REST)

Servicio RESTful desacoplado de alto rendimiento para la **precalificación crediticia automatizada simulada**, gobernado por la metodología **CRISP-ML(Q)**. Construido con **FastAPI**, **Pydantic v2**, **Scikit-Learn** y **Supabase PostgreSQL**.

> [!TIP]
> **¿Buscando cómo arrancar el servidor rápidamente?** Consulta la guía paso a paso dedicada: **[GUIA_DE_EJECUCION.md](./GUIA_DE_EJECUCION.md)**.

---

## 🎯 Contratos de la API REST Implementados

El servicio implementa todos los endpoints estipulados en la rúbrica académica y directrices técnicas ([AGENTS.md](../AGENTS.md)):

| Requerimiento | Método | Endpoint | Entrada | Salida | Autenticación |
|---|:---:|---|---|---|:---:|
| **1. Inferencia en Tiempo Real** | `POST` | `/api/v1/predict` | JSON con 12 atributos censales | Clase predicha (`>50K` / `<=50K`), probabilidad, umbral dinámico ($0.77$), latencia en ms y recomendación. Audita en Supabase. | Opcional / Pública |
| **2. Historial de Predicciones** | `GET` | `/api/v1/history` | Query params `limit` y `offset` | Lista cronológica de inferencias registradas en la tabla `predictions` de Supabase. | Opcional / Pública |
| **3. Métricas del Modelo Activo** | `GET` | `/api/v1/metrics` | Ninguna | MCC, Precision, Recall, ROC-AUC, Accuracy, Matriz de Confusión y umbral calibrado ($0.77$). | Pública |
| **4. Carga de Dataset** | `POST` | `/api/v1/train/upload` | `multipart/form-data` (`.csv`) | Validación de esquema, conteo de filas válidas y registro en `training_datasets`. | Pública |
| **5. Re-entrenamiento Asíncrono** | `POST` | `/api/v1/retrain` | Ninguna | Ejecuta pipeline CRISP-ML(Q), actualiza artefactos inmutables y registra nuevo run en DB. | Pública |
| **6. Eventos en Vivo (WebSocket)** | `WS` | `/ws/retrain` | Conexión WebSocket | Streaming en tiempo real del progreso (0% $\rightarrow$ 25% $\rightarrow$ 50% $\rightarrow$ 75% $\rightarrow$ 100%). | Pública |
| **7. Autenticación Analistas** | `POST` | `/api/v1/auth/login` | JSON `username` y `password` | Token JWT Bearer firmado (`HS256`) con vigencia de 24 horas. | Pública |
| **8. Salud del Sistema** | `GET` | `/health` | Ninguna | Estado del servicio, versión del modelo activo y conectividad con Supabase. | Pública |

---

## 🛠️ Guía Paso a Paso de Replicabilidad y Puesta en Marcha

Para que cualquier docente, tribunal examinador o desarrollador replique y levante el servicio desde cero en cualquier máquina:

### 1. Requisitos Previos del Entorno
* **Python:** Versión `3.11.x` (Requerido: no usar Python 3.14 por compatibilidad de binarios con NumPy/Scikit-Learn).
* **Git:** Para clonar y gestionar ramas.
* **Sistema Operativo:** Windows 10/11, Linux (Ubuntu 22.04+) o macOS.

---

### 2. Clonación y Navegación
```powershell
# Clonar el repositorio oficial
git clone https://github.com/AlbertoMamaniD/Adults-Census.git
cd Adults-Census

# Verificar que estés en la rama adecuada (develop o feature/backend-api-rest)
git checkout develop
```

---

### 3. Creación y Activación del Entorno Virtual (`.venv`)
```powershell
# Crear entorno virtual con Python 3.11
python -m venv .venv

# Activar en Windows (PowerShell):
.venv\Scripts\Activate.ps1

# (O si usas Linux/macOS):
# source .venv/bin/activate
```

---

### 4. Instalación de Dependencias Exactas
```powershell
# Actualizar gestor de paquetes
python -m pip install --upgrade pip

# Instalar dependencias estrictamente fijadas del backend
pip install -r backend/requirements.txt
```

---

### 5. Configuración de Variables de Entorno (`.env`)
Crear un archivo `.env` en la raíz del proyecto (o renombrar `.env.example` a `.env`):

```env
# Conexión a Base de Datos Supabase (Pooler IPv4)
SUPABASE_DB_URL=postgresql+psycopg2://postgres.TU_PROJECT_ID:TU_PASSWORD@aws-1-us-west-2.pooler.supabase.com:5432/postgres

# Seguridad JWT y credenciales de acceso
JWT_SECRET_KEY=clave_secreta_jwt_personalizada_para_desarrollo
ADMIN_USERNAME=analyst_admin
ADMIN_PASSWORD=clave_acceso_analista
```

> **Modo de Resiliencia Offline:** Si no se especifica `SUPABASE_DB_URL`, el sistema conmuta automáticamente a una base de datos local SQLite (`artifacts/local_database.db`), garantizando que la API funcione incluso en entornos sin acceso a internet.

---

### 6. Ejecución de la Suite de Pruebas Automatizadas
Antes de iniciar el servidor, verificar la integridad del sistema corriendo las **19 pruebas**:

```powershell
python -m unittest backend/tests/test_api.py -v
```
*Salida esperada:* `Ran 19 tests in ~17s ... OK (100% de éxito)`.

---

### 7. Levantar el Servidor de Inferencia FastAPI
Puedes elegir cualquiera de las dos alternativas:

```powershell
# Alternativa A: Vía script lanzador optimizado (Recomendado)
python backend/run_server.py

# Alternativa B: Directamente mediante Uvicorn
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

El servidor quedará escuchando en `http://127.0.0.1:8000`.

---

### 8. Verificación y Pruebas Interactivas
* **Documentación Interactiva Swagger UI:** Abrir en el navegador [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **Comprobación de Salud (cURL o Navegador):**
  ```powershell
  curl http://127.0.0.1:8000/health
  ```
  *Respuesta:* `{"status": "healthy", "database": "connected", "threshold": 0.77, ...}`

---

## 📋 Ejemplos de Peticiones y Respuestas

### 1. Inferencia Crediticia (`POST /api/v1/predict`)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/predict" \
     -H "Content-Type: application/json" \
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

**Respuesta Exitosa (200 OK):**
```json
{
  "predicted_class": "<=50K",
  "probability": 0.0202,
  "threshold_applied": 0.77,
  "latency_ms": 14.2,
  "model_version": "v20261117002816",
  "recommendation": "No califica para producto de crédito de alto monto (Riesgo crediticio elevado o ingresos inferiores al umbral).",
  "prediction_id": 14
}
```

---

### 2. Métricas del Modelo Activo (`GET /api/v1/metrics`)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/metrics"
```

**Respuesta (200 OK):**
```json
{
  "model_version": "v20261117002816",
  "model_name": "Gradient boosting",
  "trained_at": "2026-11-17T00:32:24.374443+00:00",
  "threshold": 0.77,
  "metrics": {
    "mcc": 0.6192,
    "precision": 0.7840,
    "recall": 0.6250,
    "roc_auc": 0.9217,
    "accuracy": 0.8682,
    "confusion_matrix": {
      "tn": 4670,
      "fp": 270,
      "fn": 588,
      "tp": 980
    },
    "expected_cost": 1398.0
  }
}
```

---

## 🏗️ Arquitectura del Repositorio

```text
backend/
├── README.md                    # Guía técnica y de replicabilidad completa
├── requirements.txt             # Dependencias estrictamente fijadas (Python 3.11)
├── run_server.py                # Script de lanzamiento directo
├── app/
│   ├── __init__.py
│   ├── main.py                  # Servidor FastAPI, CORS, middlewares y manejadores 422/500
│   ├── config.py                # Configuración centralizada, rutas y resolución de DB
│   ├── database/                # Capa ORM SQLAlchemy y modelos relacionales
│   │   ├── __init__.py
│   │   ├── connection.py        # Pooler resiliente pre-ping para Supabase IPv4
│   │   └── models.py            # Modelos ModelRun, Prediction y TrainingDataset
│   ├── schemas/                 # Validación de entrada/salida Pydantic v2
│   │   ├── __init__.py
│   │   ├── auth.py              # LoginRequest y TokenResponse
│   │   ├── prediction.py        # PredictionInput y PredictionResponse (con sanitización)
│   │   ├── history.py           # PredictionHistoryItem
│   │   ├── metrics.py           # ModelMetricsResponse y ConfusionMatrix
│   │   └── training.py          # UploadDatasetResponse y RetrainResponse
│   ├── services/                # Lógica de negocio y pipelines
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Criptografía JWT y dependencias de seguridad
│   │   ├── ml_service.py        # Singleton de inferencia, umbral dinámico y auditoría DB
│   │   ├── retrain_service.py   # Reentrenamiento CRISP-ML(Q) y calibración 3:1
│   │   └── websocket_manager.py # Gestor de retransmisión bidireccional WebSocket
│   └── routes/                  # Controladores REST modulares
│       ├── __init__.py
│       ├── auth.py
│       ├── predict.py
│       ├── history.py
│       ├── metrics.py
│       ├── train.py
│       └── websocket.py
└── tests/                       # Suite automatizada de pruebas unitarias y de integración
    ├── __init__.py
    └── test_api.py              # 19 pruebas de frontera, seguridad, persistencia y WS
```
