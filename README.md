# Servicio de IA para Predicción de Ingresos con Metodología CRISP-ML(Q)

**Trabajo Final de Grado / Materia**  
**Institución:** Universidad Católica Boliviana "San Pablo", Sede Tarija  
**Autor:** Alberto Esteban Mamani Donaire  
**Metodología:** CRISP-ML(Q) (Cross-Industry Standard Process for Machine Learning with Quality Assurance)  
**Tipo de Tarea:** Aprendizaje Supervisado — Clasificación Binaria  

---

## 📌 1. Descripción del Proyecto

Este proyecto implementa una solución integral de Inteligencia Artificial que predice si los ingresos anuales de una persona superan el umbral de **$50.000 USD** (`>50K` vs `<=50K`), a partir de variables sociodemográficas y laborales.

### Caso de Negocio Aplicativo
Una entidad de intermediación financiera busca automatizar la precalificación de clientes potenciales para productos crediticios de alto monto:
* **Falso Positivo (FP):** Otorgar el crédito a un cliente sin suficiente solvencia (mayor costo por riesgo de mora/incumplimiento).
* **Falso Negativo (FN):** No ofertar a un cliente solvente (costo de oportunidad, menor gravedad).
* **Criterio de optimización:** Relación de costo 3:1 (FP:FN) con métrica principal **MCC (Matthews Correlation Coefficient)** y **ROC-AUC** debido al desbalance natural del dataset (76% clase `<=50K` / 24% clase `>50K`).

---

## 🏗️ 2. Arquitectura del Sistema

El flujo y componentes del sistema siguen la arquitectura requerida:

```mermaid
flowchart LR
    subgraph Fase0["1° Fase: Exploración y Modelado"]
        Jupyter["Jupyter Notebook\n(notebooks/modelo_crisp_ml.ipynb)"]
    end

    subgraph Backend["Servicio de IA (API REST - Python / FastAPI)"]
        API["FastAPI App\n(backend/app)"]
        Trainer["Motor de Entrenamiento\ny Reentrenamiento"]
        Predictor["Motor de Inferencia\n(Pipeline Scikit-Learn)"]
    end

    subgraph BaseDatos["Base de Datos (Supabase / PostgreSQL)"]
        T_Runs["model_runs\n(Métricas y versiones)"]
        T_Preds["predictions\n(Historial de inferencias)"]
        T_Data["training_datasets\n(Archivos y datos crudos)"]
    end

    subgraph Frontend["Frontend de Uso de la IA"]
        WebUI["Aplicación Web Interactiva\n(Formularios, CSV y Métricas)"]
    end

    Jupyter -.->|"Genera modelo inicial\ny artefactos"| Predictor
    Trainer <-->|"Lee/escribe datasets y runs"| BaseDatos
    Predictor <-->|"Registra y consulta historial"| BaseDatos
    API <-->|"API REST JSON / multipart"| WebUI
```

---

## 📊 3. Dataset

* **Nombre:** Adult Census Income (Censo de EE.UU. 1994, publicado por UCI y disponible en [Kaggle](https://www.kaggle.com/datasets/uciml/adult-census-income)).
* **Tamaño:** ~32.500 registros y 15 variables (14 características de entrada y 1 etiqueta objetivo `income`).
* **Características:** Mezcla de variables numéricas (`age`, `education.num`, `capital.gain`, `capital.loss`, `hours.per.week`) y categóricas (`workclass`, `marital.status`, `occupation`, `relationship`, `race`, `sex`, `native.country`).
* **Tratamiento:** Imputación de nulos (`?`), descarte de `fnlwgt` (peso censal) y de redundancia (`education`), codificación One-Hot y escalado estándar, preservando auditoría de equidad/sesgo sobre `sex` y `race`.

---

## 🔄 4. Fases de la Metodología CRISP-ML(Q)

| Fase | Actividades Principales | Entregables Clave |
|---|---|---|
| **1. Business & Data Understanding** | Definición del objetivo financiero, matriz de costos 3:1, selección de métricas (MCC, ROC-AUC, F1), EDA de clases y correlaciones. | Matriz de costos, EDA en Notebook, `docs/crisp-ml-q/`. |
| **2. Data Preparation** | Limpieza de caracteres de escape `?`, eliminación de `fnlwgt`, preprocesamiento estratificado 70/15/15 y pipelines de transformación. | Pipeline Scikit-Learn reproducible. |
| **3. Modeling** | Comparación justa de modelos: Regresión Logística, Árbol de Decisión, Random Forest y Gradient Boosting bajo validación cruzada. | Comparativa de MCC y latencia < 1000 ms. |
| **4. Evaluation & Quality Assurance** | Evaluación única en test set, optimización de umbral de corte, matriz de confusión, auditoría de sesgo (Fairness) en sexo y raza. | Umbral óptimo, reporte de sesgo, modelo final en `artifacts/`. |
| **5. Deployment** | Desarrollo de API REST con 5 endpoints, persistencia en Supabase y cliente web interactivo. | Código en `backend/` y `frontend/`, Swagger UI. |
| **6. Monitoring & Maintenance** | Detección de Data Drift (métricas PSI), endpoint de re-entrenamiento con nuevo CSV y versionado de modelos en BD. | Endpoint `/retrain` y tabla `model_runs`. |

---

## 🚀 5. Especificación de la API REST (Backend)

La API REST expone **todos los endpoints solicitados por el requerimiento de la materia**:

| Método | Endpoint | Descripción | Requerimiento de la Materia |
|---|---|---|---|
| `POST` | `/api/v1/predict` | Envía características de una persona y devuelve la predicción (`<=50K` o `>50K`), probabilidad calculada y tiempo de latencia. Guarda la transacción en BD. | Requerimiento 2.a |
| `GET` | `/api/v1/history` | Retorna el historial cronológico de predicciones realizadas (datos de entrada, resultado y timestamp). Soporta paginación. | Requerimiento 2.b |
| `GET` | `/api/v1/metrics` | Consulta las métricas de rendimiento del modelo activo (MCC, ROC-AUC, Accuracy, F1, Matriz de Confusión y fecha de entrenamiento). | Requerimiento 2.c |
| `POST` | `/api/v1/retrain` | Dispara el re-entrenamiento del modelo con los datos más recientes o los subidos, genera una nueva versión y actualiza las métricas en BD. | Requerimiento 2.d |
| `POST` | `/api/v1/train/upload` | Recibe un archivo CSV (`multipart/form-data`) con nuevos datos de entrenamiento, valida su esquema y lo almacena para re-entrenamiento. | Requerimiento 2.e |
| `GET` | `/docs` / `/openapi.json` | Documentación interactiva Swagger UI y especificación OpenAPI v3. | Entregable Swagger |

---

## 💻 6. Interfaz Gráfica (Frontend)

El cliente web interactúa con el 100% de los endpoints de la API mediante módulos dedicados:

1. **Formulario de Predicción Individual:** Interfaz con controles intuitivos (edad, ocupación, horas semanales, etc.) con validación y visualización inmediata del veredicto (`>50K` o `<=50K`), barra de probabilidad y latencia en milisegundos.
2. **Historial de Predicciones:** Tabla dinámica con filtros de búsqueda, estado y paginación para auditar consultas pasadas registradas en Supabase.
3. **Panel de Métricas del Modelo:** Dashboard visual con tarjetas de KPI (MCC, ROC-AUC, Precisión, Recall) y representación gráfica de la matriz de confusión.
4. **Gestión de Datos y Re-entrenamiento:**
   * Zona de carga drag & drop para enviar archivos CSV de entrenamiento.
   * Botón para solicitar el re-entrenamiento en segundo plano con indicadores de progreso y confirmación de nueva versión generada.

---

## 🗄️ 7. Base de Datos (Supabase / PostgreSQL)

Estructura de persistencia relacional en Supabase:

* `model_runs`: Registra el historial de versiones del modelo, hiperparámetros, umbral óptimo de decisión, fecha de entrenamiento y métricas calculadas.
* `predictions`: Almacena cada inferencia realizada (payload JSON de entrada, clase predicha, probabilidad, latencia y timestamp).
* `training_datasets`: Registro de archivos CSV cargados, número de filas válidas y fecha de ingestión.

*(El diagrama entidad-relación y el script DDL reproducible se encuentran en `db/schema.sql` y `db/README.md`).*

---

## 📁 8. Estructura del Repositorio

```text
TALLERSIS4/
├── README.md                      # Documentación principal del proyecto
├── requirements.txt               # Dependencias generales del proyecto
├── .env.example                   # Variables de entorno de referencia (Supabase DB URL)
├── .gitignore                     # Exclusión de entornos virtuales, datasets y secretos
├── data/                          # Dataset original (adult.csv referenciado en data/README.md)
│   ├── adult.csv
│   └── README.md
├── notebooks/                     # Notebook Jupyter con CRISP-ML(Q) completo
│   └── modelo_crisp_ml.ipynb
├── artifacts/                     # Modelos serializados (.joblib) y metadatos JSON
├── backend/                       # Servicio de IA (API REST FastAPI)
│   └── README.md
├── frontend/                      # Aplicación web cliente
│   └── README.md
├── db/                            # Scripts SQL y diagramas de base de datos
│   ├── schema.sql
│   └── README.md
└── docs/                          # Documentación formal y entregables
    ├── crisp-ml-q/                # Justificación del dataset y aplicación metodológica
    ├── cronograma/                # Cronograma de trabajo basado en CRISP-ML(Q)
    ├── swagger/                   # Especificación Swagger / OpenAPI
    ├── evidencia-pr/              # Evidencia de revisión de Pull Requests con IA
    └── video/                     # Enlace al video demostrativo de 5 minutos
```

---

## 📋 9. Checklist de Entregables Requeridos

| Entregable | Estado | Ubicación / Referencia |
|---|:---:|---|
| **Código Fuente del Servicio de IA** | ✅ En desarrollo | Carpeta `backend/` |
| **Código Fuente de la Aplicación Web Cliente** | ✅ En desarrollo | Carpeta `frontend/` |
| **Diagrama de BD y Script SQL** | ✅ Planificado | Carpeta `db/schema.sql` y `db/README.md` |
| **Documento Swagger de la API** | ✅ Integrado | `docs/swagger/` y endpoint `/docs` de FastAPI |
| **Video Demostrativo (5 minutos)** | ⏳ Pendiente de grabación | Enlace en `docs/video/` |
| **Documento Metodología CRISP-ML(Q)** | ✅ Listo / Ampliado | Carpeta `docs/crisp-ml-q/` |
| **URL del Repositorio Público GitHub** | ⏳ Pendiente de publicación | Configuración de Git y GitHub |
| **Evidencia de IA de Revisión de PR (Plus)** | ✅ Configurado | Carpeta `docs/evidencia-pr/` |

---

## ⚙️ 10. Guía de Ejecución Rápida

### 1. Clonar el repositorio y configurar el entorno
```bash
git clone <URL_REPOSITORIO>
cd TALLERSIS4

# Crear y activar entorno virtual
python -m venv .venv
# En Windows PowerShell:
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
Copiar `.env.example` a `.env` y configurar la cadena de conexión de Supabase:
```env
SUPABASE_DB_URL="postgresql://postgres.PROJECT_ID:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres"
```

### 3. Ejecutar el Notebook de Entrenamiento
```bash
jupyter notebook notebooks/modelo_crisp_ml.ipynb
```

### 4. Levantar el Servicio de IA (Backend)
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
*Acceso a Swagger UI:* `http://localhost:8000/docs`

### 5. Levantar el Cliente Web (Frontend)
```bash
cd frontend
# Iniciar servidor local
npm run dev # o python -m http.server según la tecnología elegida
```
