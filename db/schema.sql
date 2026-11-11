-- =============================================================================
-- Script DDL Profesional: Base de Datos para Servicio de IA y CRISP-ML(Q)
-- Gestor: PostgreSQL 15+ / Supabase
-- Autor: Alberto Esteban Mamani Donaire
-- Descripción:
--   Implementa el almacenamiento relacional y semiestructurado para:
--   1. Versionado, parámetros y métricas de modelos de IA (model_runs).
--   2. Registro transaccional de inferencias y auditoría de drift (predictions).
--   3. Trazabilidad de archivos cargados para re-entrenamiento (training_datasets).
-- =============================================================================

-- Extensiones recomendadas en PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. TABLA: model_runs (Ciclos de vida y métricas del modelo de IA)
-- =============================================================================
CREATE TABLE IF NOT EXISTS model_runs (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(40) NOT NULL UNIQUE,
    model_name VARCHAR(100) NOT NULL,
    trained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    threshold DOUBLE PRECISION NOT NULL CHECK (threshold >= 0.0 AND threshold <= 1.0),
    metrics JSONB NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE model_runs IS 'Almacena versiones, hiperparámetros y métricas de calidad de cada modelo entrenado según CRISP-ML(Q).';
COMMENT ON COLUMN model_runs.model_version IS 'Identificador semántico o timestamp único de la versión del modelo (ej. v20261111180000).';
COMMENT ON COLUMN model_runs.threshold IS 'Umbral de decisión óptimo calibrado en el conjunto de validación para minimizar la función de costo 3:1.';
COMMENT ON COLUMN model_runs.metrics IS 'Objeto JSONB con métricas de evaluación: MCC, ROC-AUC, Precision, Recall, F1 y Matriz de Confusión.';
COMMENT ON COLUMN model_runs.parameters IS 'Objeto JSONB con los hiperparámetros óptimos seleccionados durante el modelado.';
COMMENT ON COLUMN model_runs.is_active IS 'Flag booleano que indica cuál es el modelo desplegado actualmente en producción.';

-- =============================================================================
-- 2. TABLA: predictions (Historial transaccional de inferencias de la API)
-- =============================================================================
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version VARCHAR(40) NOT NULL,
    input_data JSONB NOT NULL,
    predicted_class VARCHAR(10) NOT NULL CHECK (predicted_class IN ('>50K', '<=50K')),
    probability DOUBLE PRECISION NOT NULL CHECK (probability >= 0.0 AND probability <= 1.0),
    latency_ms DOUBLE PRECISION NOT NULL CHECK (latency_ms >= 0.0),
    CONSTRAINT fk_predictions_model_version
        FOREIGN KEY (model_version)
        REFERENCES model_runs (model_version)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

COMMENT ON TABLE predictions IS 'Historial transaccional de inferencias solicitadas al endpoint POST /predict para auditoría y monitoreo de drift.';
COMMENT ON COLUMN predictions.input_data IS 'Payload JSONB completo con las 12 características demográficas y laborales enviadas por el usuario.';
COMMENT ON COLUMN predictions.predicted_class IS 'Categoría predicha por el modelo (>50K o <=50K).';
COMMENT ON COLUMN predictions.probability IS 'Probabilidad calculada por la función sigmoide/árbol para la clase positiva (>50K).';
COMMENT ON COLUMN predictions.latency_ms IS 'Tiempo de ejecución de la inferencia en milisegundos medido en el backend.';

-- =============================================================================
-- 3. TABLA: training_datasets (Auditoría de cargas CSV de re-entrenamiento)
-- =============================================================================
CREATE TABLE IF NOT EXISTS training_datasets (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_count INTEGER NOT NULL CHECK (row_count > 0),
    file_size_bytes BIGINT,
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'processed', 'error')),
    notes TEXT
);

COMMENT ON TABLE training_datasets IS 'Registro y trazabilidad de archivos CSV enviados al endpoint POST /api/v1/train/upload para re-entrenamiento.';

-- =============================================================================
-- 4. ÍNDICES DE ALTO RENDIMIENTO
-- =============================================================================
-- Optimización de consultas cronológicas para el endpoint GET /history
CREATE INDEX IF NOT EXISTS idx_predictions_created_at_desc ON predictions (created_at DESC);

-- Optimización de filtrado por versión de modelo
CREATE INDEX IF NOT EXISTS idx_predictions_model_version ON predictions (model_version);

-- Índice GIN para búsquedas y consultas complejas dentro del JSONB de entrada
CREATE INDEX IF NOT EXISTS idx_predictions_input_data_gin ON predictions USING GIN (input_data);

-- Optimización para obtener el modelo activo en O(1)
CREATE INDEX IF NOT EXISTS idx_model_runs_is_active ON model_runs (is_active) WHERE is_active = TRUE;

-- =============================================================================
-- 5. SEGURIDAD Y POLÍTICAS (Supabase Row Level Security)
-- =============================================================================
ALTER TABLE IF EXISTS model_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS training_datasets ENABLE ROW LEVEL SECURITY;

-- Políticas permisivas por defecto para el backend de servicio
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'model_runs' AND policyname = 'service_access_model_runs'
    ) THEN
        CREATE POLICY service_access_model_runs ON model_runs FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'predictions' AND policyname = 'service_access_predictions'
    ) THEN
        CREATE POLICY service_access_predictions ON predictions FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'training_datasets' AND policyname = 'service_access_training_datasets'
    ) THEN
        CREATE POLICY service_access_training_datasets ON training_datasets FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;
