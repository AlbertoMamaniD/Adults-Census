# Backend: Servicio de Inteligencia Artificial (API REST)

Este directorio contiene la implementación del servicio web que expone el modelo de Machine Learning mediante una API REST en **FastAPI** (Python).

---

## 🎯 Cumplimiento de Endpoints Requeridos

El servicio implementa los 5 endpoints estipulados en la rúbrica del Trabajo Final:

| Requerimiento | Método | Endpoint | Entrada | Salida |
|---|:---:|---|---|---|
| **2.a Predicción / Clasificación** | `POST` | `/api/v1/predict` | JSON con datos de una persona (edad, educación, ocupación, horas semanales, etc.) | Clase predicha (`<=50K` / `>50K`), probabilidad (`0.0 - 1.0`), latencia (ms) y timestamp. Registra en BD. |
| **2.b Historial de Predicciones** | `GET` | `/api/v1/history` | Query params opcionales (`limit`, `offset`) | Lista de predicciones previas con payload de entrada y resultado. |
| **2.c Métricas de Rendimiento** | `GET` | `/api/v1/metrics` | Ninguna | MCC, ROC-AUC, Accuracy, Precision, Recall, Matriz de Confusión y versión activa. |
| **2.d Solicitud de Re-entrenamiento** | `POST` | `/api/v1/retrain` | Opcional: versión o parámetros | Estado de re-entrenamiento, nuevas métricas calculadas y confirmación de actualización de versión. |
| **2.e Envío de Archivo de Entrenamiento** | `POST` | `/api/v1/train/upload` | `multipart/form-data` (archivo `.csv`) | Validación de columnas, cantidad de filas cargadas y confirmación de almacenamiento. |

---

## 🏗️ Estructura Sugerida del Backend

```text
backend/
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py                  # Punto de entrada de FastAPI y configuración de CORS
│   ├── config.py                # Lectura de variables de entorno (SUPABASE_DB_URL)
│   ├── schemas/                 # Esquemas Pydantic de validación
│   │   ├── predict.py           # Esquema de entrada y salida para inferencia
│   │   ├── history.py           # Esquema del historial
│   │   └── metrics.py           # Esquema de métricas
│   ├── routes/                  # Routers de FastAPI
│   │   ├── predict.py           # Endpoint 2.a y 2.b
│   │   ├── metrics.py           # Endpoint 2.c
│   │   └── train.py             # Endpoints 2.d y 2.e
│   ├── services/                # Lógica de negocio
│   │   ├── model_service.py     # Carga de pipeline, inferencia con umbral óptimo
│   │   └── trainer_service.py   # Lógica de re-entrenamiento y persistencia de métricas
│   └── database/                # Conexión SQLAlchemy a Supabase
│       ├── connection.py
│       └── models.py            # Modelos ORM (model_runs, predictions, datasets)
└── tests/                       # Pruebas unitarias de endpoints
```

---

## ⚡ Ejecución Local

1. Asegúrate de tener las dependencias instaladas en el entorno virtual (`pip install -r ../requirements.txt`).
2. Configurar la variable `SUPABASE_DB_URL` en tu archivo `.env` o en la consola:
   ```powershell
   $env:SUPABASE_DB_URL = "postgresql://..."
   ```
3. Iniciar el servidor con recarga automática:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
4. Consultar la documentación interactiva en:
   * **Swagger UI:** `http://localhost:8000/docs`
   * **Redoc:** `http://localhost:8000/redoc`
   * **OpenAPI JSON:** `http://localhost:8000/openapi.json`

