# AGENTS.md — Directrices Técnicas para Agentes de Inteligencia Artificial

> **Directiva del Repositorio:** Este archivo establece el contexto de negocio, arquitectura de software, especificación de contratos REST, sistema de diseño visual y directrices de ingeniería de código limpio para cualquier agente de IA (Antigravity, GitHub Copilot, Cursor, PR-Agent, etc.) que opere en este repositorio.

---

## 📌 1. Información General del Proyecto

* **Materia:** Trabajo Final de Grado / Taller de Sistemas.
* **Institución:** Universidad Católica Boliviana "San Pablo", Sede Tarija.
* **Autor:** Alberto Esteban Mamani Donaire.
* **Metodología Oficial:** **CRISP-ML(Q)** (*Cross-Industry Standard Process for Machine Learning with Quality Assurance*).
* **Problema de Negocio:** Precalificación crediticia automatizada simulada. El modelo predice si un solicitante tiene ingresos brutos anuales superiores a $50.000 USD (`>50K` vs `<=50K`), habilitando la oferta de productos financieros de alto monto.
* **Dataset:** Adult Census Income (Kaggle: `uciml/adult-census-income`, 32.561 registros censales, 15 atributos).
* **Métrica Principal:** **MCC (*Matthews Correlation Coefficient*) $\ge 0.55$** (métrica obligatoria debido al desbalance 76% clase `<=50K` / 24% clase `>50K`).
* **Función de Costo Asimétrica:** $C = 3 \times FP + 1 \times FN$.
  * **Falso Positivo (FP):** Otorgar crédito a un cliente insolvente (riesgo crítico de mora, penalización 3x).
  * **Falso Negativo (FN):** Dejar pasar un cliente solvente (costo de oportunidad comercial, penalización 1x).
  * **Umbral de Decisión Calibrado:** `threshold = 0.79` (determinado en validación para minimizar el costo esperado).

---

## 🏗️ 2. Stack Tecnológico y Versiones Exactas

Todo agente de código debe respetar estrictamente estas versiones y entornos:

| Componente | Tecnología | Versión de Referencia | Propósito |
|---|---|:---:|---|
| **Intérprete Python** | Python (CPython) | `3.11.x` | Entorno de ejecución en `.venv` (No usar 3.14 por incompatibilidad C/NumPy). |
| **Backend Web** | FastAPI | `0.110.0+` | Framework REST asíncrono de alto rendimiento. |
| **Servidor ASGI** | Uvicorn | `0.28.0+` | Servidor HTTP de producción con soporte uvloop/httptools. |
| **Validación de Datos** | Pydantic v2 | `2.6.0+` | Validación estricta de esquemas de entrada y serialización de salida. |
| **Carga de Archivos** | python-multipart | `0.0.9+` | Procesamiento de formularios `multipart/form-data` para subida de CSV. |
| **Base de Datos ORM** | SQLAlchemy | `2.0.0+` | Mapeo objeto-relacional y pooling de conexiones. |
| **Driver PostgreSQL** | psycopg2-binary | `2.9.9+` | Driver nativo C optimizado para PostgreSQL. |
| **Machine Learning** | Scikit-Learn | `1.4.0+` | Pipelines (`ColumnTransformer`, `HistGradientBoostingClassifier`). |
| **Serialización ML** | Joblib | `1.3.0+` | Serialización binaria de artefactos de inferencia. |
| **Base de Datos Cloud** | Supabase PostgreSQL | `15.x / 16.x` | Base de datos relacional con pooler IPv4 (`aws-1-us-west-2`). |
| **Frontend Web** | HTML5 Semántico + CSS3 + Vanilla JS ES6+ | Estándar W3C | Cliente web interactivo, desacoplado, responsivo y sin bundles pesados. |

---

## 🎨 3. Sistema de Diseño (Design System) y Frontend Guidelines

Para garantizar una interfaz gráfica con nivel de producto financiero profesional, cualquier agente que genere o modifique código en `frontend/` **DEBE invocar o aplicar los principios del skill `impeccable` y `generative_ui`**, respetando estas pautas visuales:

### 3.1 Paleta Cromática Institucional (Fintech Palette)
* **Primario / Marca:** `#0f172a` (Slate 900) y `#1e293b` (Slate 800) para barras de navegación, encabezados y estructura.
* **Acento Interactivo:** `#2563eb` (Blue 600) y `#1d4ed8` (Blue 700) para botones principales de acción y estados activos.
* **Clase Positiva (`>50K` / Aprobado):** `#059669` (Emerald 600) con fondo `#ecfdf5` (Emerald 50) y borde `#a7f3d0`.
* **Clase Negativa (`<=50K` / No Califica):** `#dc2626` (Red 600) con fondo `#fef2f2` (Red 50) y borde `#fecaca`.
* **Advertencias y KPIs Secundarios:** `#d97706` (Amber 600) con fondo `#fffbeb` (Amber 50).
* **Superficies y Fondos:** `#f8fafc` (Slate 50) para el fondo general del lienzo, `#ffffff` para tarjetas/contenedores con sombra suave `box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1)`.
* **Bordes y Divisores:** `#e2e8f0` (Slate 200).

### 3.2 Tipografía y Jerarquía
* **Familia Tipográfica:** `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`.
* **Jerarquía:**
  * **H1 (Título de Página):** `1.875rem (30px)`, `font-weight: 700`, `letter-spacing: -0.025em`.
  * **H2 (Encabezado de Módulo):** `1.5rem (24px)`, `font-weight: 600`.
  * **H3 (Subtítulo de Tarjeta):** `1.125rem (18px)`, `font-weight: 600`.
  * **Cuerpo de Texto:** `0.875rem (14px)` a `0.9375rem (15px)`, `line-height: 1.5`, color `#334155` (Slate 700).
  * **Microcopy / Etiquetas:** `0.75rem (12px)`, `font-weight: 500`, `text-transform: uppercase`, `letter-spacing: 0.05em`, color `#64748b`.

### 3.3 Principios de Código Limpio y Separación de Responsabilidades
El frontend **NO debe mezclar código en archivos monolíticos**. Se debe mantener una separación estricta:
1. **Estructura (`frontend/public/index.html` o páginas modulares):**
   * HTML5 semántico puro (`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`).
   * Cero estilos en línea (`style="..."`).
   * Formularios accesibles con etiquetas `<label for="...">` explícitas e inputs con validación nativa (`required`, `min`, `max`, `pattern`).
2. **Estilos (`frontend/src/styles/` o `css/`):**
   * Variables CSS personalizadas (`--color-primary`, `--color-accent`, etc.) para mantenimiento centralizado.
   * Flexbox y CSS Grid para diagramación fluida.
   * **100% Responsivo:** Mobile-first con breakpoints estandarizados:
     * Móvil: `< 640px` (formulario en columna única, tablas con scroll horizontal o vista de tarjetas).
     * Tablet: `640px - 1024px` (grid de 2 columnas).
     * Desktop: `> 1024px` (dashboard amplio en 3 o 4 columnas).
   * Micro-interacciones sutiles en botones (`hover`, `active`, `focus-visible`) y transiciones suaves (`transition: all 0.2s ease`).
3. **Lógica (`frontend/src/services/` y `frontend/src/components/`):**
   * JavaScript ES6+ modular (usar `async/await`, `fetch`, módulos ES con `import/export`).
   * Servicio de cliente API desacoplado (`apiService.js`) con manejo de errores de red y timeout.
   * Control de estados en la UI:
     * Estado de Carga: Indicadores visuales / spinners en botones durante peticiones REST.
     * Estado de Éxito: Modales o banners confirmando predicción o subida de CSV.
     * Estado de Error: Mensajes semánticos claros ante fallos 400 o 500.

---

## 📡 4. Contratos de la API REST (Mandatorio)

Cualquier endpoint generado en `backend/app/routes/` debe implementar esquemas Pydantic v2 exactos:

### Endpoint 1: Inferencia en Tiempo Real
* **Ruta:** `POST /api/v1/predict`
* **Request Body:**
  ```json
  {
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
  }
  ```
* **Response Body (200 OK):**
  ```json
  {
    "predicted_class": "<=50K",
    "probability": 0.1824,
    "threshold_applied": 0.79,
    "latency_ms": 12.4,
    "model_version": "v20261111222307",
    "recommendation": "No califica para producto de crédito de alto monto."
  }
  ```

### Endpoint 2: Historial de Predicciones
* **Ruta:** `GET /api/v1/history?limit=50&offset=0`
* **Response Body (200 OK):** Array de objetos con ID, `created_at`, `model_version`, `input_data`, `predicted_class`, `probability` y `latency_ms`.

### Endpoint 3: Métricas del Modelo Activo
* **Ruta:** `GET /api/v1/metrics`
* **Response Body (200 OK):**
  ```json
  {
    "model_version": "v20261111222307",
    "model_name": "Gradient boosting",
    "trained_at": "2026-11-11T22:27:25Z",
    "threshold": 0.79,
    "metrics": {
      "mcc": 0.6236,
      "precision": 0.8044,
      "recall": 0.6110,
      "roc_auc": 0.9248,
      "accuracy": 0.8695,
      "confusion_matrix": { "tn": 4713, "fp": 227, "fn": 629, "tp": 939 }
    }
  }
  ```

### Endpoint 4: Carga de Dataset de Entrenamiento
* **Ruta:** `POST /api/v1/train/upload`
* **Content-Type:** `multipart/form-data` (`file: UploadFile`)
* **Response Body (200 OK):**
  ```json
  {
    "status": "success",
    "filename": "adult_actualizado.csv",
    "rows_ingested": 32561,
    "dataset_id": 1,
    "message": "Archivo validado y registrado en training_datasets."
  }
  ```

### Endpoint 5: Solicitud de Re-entrenamiento
* **Ruta:** `POST /api/v1/retrain`
* **Response Body (200 OK):**
  ```json
  {
    "status": "success",
    "message": "Pipeline CRISP-ML(Q) completado con éxito.",
    "new_model_version": "v20261118153000",
    "updated_metrics": { "mcc": 0.625, "precision": 0.81, "recall": 0.62, "roc_auc": 0.925 }
  }
  ```

---

## 🗄️ 5. Base de Datos (Supabase / PostgreSQL)

* **Cadena de Conexión:** Reside exclusivamente en `.env` bajo la clave `SUPABASE_DB_URL`.
* **Tablas Definidas:**
  1. `model_runs`: Versiones, hiperparámetros, umbrales y métricas JSONB.
  2. `predictions`: Historial de inferencias con clave foránea referenciando `model_runs(model_version)` e índice GIN sobre `input_data`.
  3. `training_datasets`: Archivos CSV cargados y trazabilidad de lotes.
* **Seguridad:** Todas las tablas tienen `Row Level Security (RLS)` habilitado con políticas de servicio en [`db/schema.sql`](../db/schema.sql).

---

## 🤖 6. Directivas para Skills y Agentes de IA

1. **Skill `impeccable`:**
   * Utilizar para cualquier trabajo de maquetación, estilo, auditoría de accesibilidad, paleta visual y comportamiento responsivo de la interfaz web.
2. **Skill `generative_ui`:**
   * Utilizar para renderizar tarjetas de métricas, componentes interactivos de matriz de confusión y barras de probabilidad animadas.
3. **Flujo de Pull Requests y Revisiones:**
   * Al proponer cambios significativos, trabajar en ramas nombradas con la convención: `feature/nombre-funcionalidad`, `fix/correccion` o `docs/documentacion`.
   * Incluir descripciones detalladas con la lista de verificación de CRISP-ML(Q) para que la IA de revisión de PR (Qodo Merge / PR-Agent) pueda auditar el diff eficientemente.

