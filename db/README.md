# Base de Datos: Información de Predicciones y Modelos de IA

Este directorio contiene el script DDL de creación de la base de datos, el diagrama entidad-relación y el procedimiento para su generación en **Supabase** (PostgreSQL).

---

## 📊 Diagrama Entidad-Relación (ERD)

```mermaid
erDiagram
    model_runs {
        int id PK
        varchar model_version UK "Identificador único de versión"
        varchar model_name "Nombre del algoritmo"
        timestamptz trained_at "Fecha de entrenamiento"
        float threshold "Umbral calibrado (theta = 0.77)"
        jsonb metrics "MCC, ROC-AUC, Matriz de Confusión"
        jsonb parameters "Hiperparámetros óptimos"
        boolean is_active "Único modelo activo (Partial Index)"
        timestamptz created_at
    }

    predictions {
        int id PK
        timestamptz created_at "Timestamp de la petición"
        varchar model_version FK "Referencia a model_runs"
        jsonb input_data "Las 12 variables censales enviadas"
        varchar predicted_class "Clase predicha (>50K o <=50K)"
        float probability "Probabilidad continua calculada"
        float latency_ms "Tiempo de respuesta en milisegundos"
    }

    training_datasets {
        int id PK
        varchar filename "Nombre original del archivo"
        timestamptz uploaded_at "Fecha de carga"
        int row_count "Cantidad de registros censales"
        bigint file_size_bytes "Tamaño en bytes"
        varchar status "uploaded | processing | processed | error"
        text notes "Nombre físico en almacenamiento seguro"
    }

    model_runs ||--o{ predictions : "registra inferencias con (FK)"
    training_datasets ||--o{ model_runs : "origina version entrenada"
```

---

## 📋 Descripción de Tablas

1. **`model_runs`**:
   * Controla las versiones y ciclos de vida del modelo de ML.
   * Guarda los hiperparámetros seleccionados y las métricas obtenidas (MCC, ROC-AUC, Matriz de Confusión) en formato semiestructurado JSONB.
   * Almacena el `threshold` óptimo (umbral de probabilidad calibrado para minimizar el costo financiero 3:1).

2. **`predictions`**:
   * Cumple con el **Requerimiento 2.b**: almacena cada petición realizada al endpoint `/predict`.
   * Guarda los datos demográficos y laborales enviados (`input_data`), la clase predicha (`<=50K` o `>50K`), la probabilidad calculada y la latencia del cálculo en milisegundos.

3. **`training_datasets`**:
   * Cumple con el **Requerimiento 2.e**: registra los archivos CSV de entrenamiento cargados desde la interfaz web para auditoría y trazabilidad del re-entrenamiento.

---

## 🛠️ Procedimiento de Generación en Supabase

### Opción 1: Mediante el SQL Editor de Supabase (Recomendada)
1. Iniciar sesión en el panel web de [Supabase](https://supabase.com).
2. Seleccionar el proyecto del curso.
3. Ir a la pestaña **SQL Editor** en el menú lateral izquierdo.
4. Crear una nueva consulta (`+ New query`).
5. Copiar y pegar el contenido íntegro de [`schema.sql`](./schema.sql).
6. Presionar **Run** (Ejecutar). Verificar que las tablas aparezcan en el **Table Editor**.

### Opción 2: Automáticamente desde el Notebook o Backend
El notebook `notebooks/modelo_crisp_ml.ipynb` y el backend en FastAPI utilizan SQLAlchemy con `MetaData.create_all(engine)` para verificar y autogenerar las tablas si aún no existen, utilizando la cadena de conexión definida en `SUPABASE_DB_URL`.

