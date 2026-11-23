from collections import defaultdict
from contextlib import asynccontextmanager
import logging
import time
import traceback
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
from app.config import settings
from app.database.connection import Base, engine, SessionLocal
from app.database.models import ModelRun
from app.routes import auth, history, metrics, predict, train, websocket
from app.services.ml_service import ml_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main_app")

# -----------------------------------------------------------------------------
# PROTECCIÓN CONTRA ABUSOS Y RATE LIMITING (Control por IP)
# -----------------------------------------------------------------------------
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_REQUESTS_PER_WINDOW = 120  # Máximo 120 peticiones por minuto por dirección IP
_client_request_history = defaultdict(list)

# -----------------------------------------------------------------------------
# METADATOS Y DESCRIPCIONES PARA SWAGGER UI / OPENAPI
# -----------------------------------------------------------------------------
tags_metadata = [
    {
        "name": "Inferencia en Tiempo Real",
        "description": (
            "**Evaluación de precalificación crediticia.** Procesa los 12 atributos censales del solicitante, "
            "ejecuta inferencia mediante `HistGradientBoostingClassifier`, aplica el umbral robusto calibrado "
            "(**θ = 0.77**) minimizando la función de costo asimétrica ($3\\times FP + 1\\times FN$), calcula la latencia "
            "en milisegundos y audita la predicción en la base de datos Supabase PostgreSQL."
        ),
    },
    {
        "name": "Historial de Predicciones",
        "description": (
            "**Auditoría y trazabilidad transaccional.** Recupera las predicciones registradas cronológicamente "
            "con soporte de paginación (`limit`, `offset`) para análisis de drift y auditoría de decisiones."
        ),
    },
    {
        "name": "Métricas y MLOps",
        "description": (
            "**Reporte de calidad del modelo activo (CRISP-ML(Q)).** Expone el desempeño en el conjunto de prueba: "
            "**MCC** (meta $\\ge 0.55$, alcanzado $0.6192$), **Precisión** ($\\ge 0.75$, alcanzado $0.7840$), "
            "**Sensibilidad** ($\\ge 0.60$, alcanzado $0.6250$), **ROC-AUC** ($\\ge 0.90$, alcanzado $0.9217$) y "
            "la matriz de confusión completa ($TN, FP, FN, TP$)."
        ),
    },
    {
        "name": "Entrenamiento y MLOps",
        "description": (
            "**Ingesta de datos y ciclo de reentrenamiento continuo.** Permite la subida segura de archivos CSV (hasta 50 MB) "
            "con validación de esquema censal, y el disparo asíncrono del pipeline completo con protección de concurrencia (`asyncio.Lock`)."
        ),
    },
    {
        "name": "WebSocket Streaming",
        "description": (
            "**Canal bidireccional de eventos en vivo.** Retransmite el progreso de reentrenamiento paso a paso "
            "(25% preprocesamiento $\\rightarrow$ 50% entrenamiento $\\rightarrow$ 75% evaluación $\\rightarrow$ 100% despliegue)."
        ),
    },
    {
        "name": "Autenticación",
        "description": (
            "**Seguridad de acceso para analistas.** Emisión y validación de tokens criptográficos **JWT Bearer (HS256)** "
            "con vigencia de 24 horas y protección contra ataques de temporización (*Timing Attacks*)."
        ),
    },
    {
        "name": "Salud del Sistema",
        "description": (
            "**Monitoreo y disponibilidad.** Comprobación de conectividad con Supabase PostgreSQL, estado del servicio "
            "y versión inmutable del modelo activo."
        ),
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando servicio FastAPI de Precalificación Crediticia...")
    
    # 1. Asegurar tablas si se usa SQLite local o verificar conexión con Supabase
    try:
        if settings.DATABASE_URL.startswith("sqlite"):
            Base.metadata.create_all(bind=engine)
            logger.info("Tablas locales inicializadas en SQLite.")
        else:
            with engine.connect() as conn:
                logger.info("Conexión con Supabase PostgreSQL establecida correctamente.")
    except Exception as e:
        logger.warning(f"Aviso de conexión a base de datos en arranque: {e}")

    # 2. Precargar modelo en memoria y asegurar coherencia referencial en base de datos (Qodo Finding 8)
    try:
        bundled_manifest_version = None
        active_version_file = settings.ARTIFACTS_DIR / "active_version.json"
        if active_version_file.exists():
            try:
                with open(active_version_file, "r", encoding="utf-8") as f:
                    v_manifest = json.load(f)
                    bundled_manifest_version = v_manifest.get("model_version")
            except Exception as mf_err:
                logger.warning(f"Aviso leyendo active_version.json: {mf_err}")

        active_db_version = None
        try:
            with SessionLocal() as db_probe:
                active_db_run = db_probe.query(ModelRun).filter(ModelRun.is_active == True).order_by(ModelRun.id.desc()).first()
                if active_db_run:
                    active_db_version = active_db_run.model_version
        except Exception as db_probe_err:
            logger.warning(f"Aviso al consultar versión activa en base de datos: {db_probe_err}")

        # Si el manifiesto empaquetado en disco es más reciente o la DB no tiene activo, priorizarlo
        target_version = None
        if bundled_manifest_version:
            if active_db_version is None or bundled_manifest_version >= active_db_version:
                target_version = bundled_manifest_version
            else:
                target_version = active_db_version
        else:
            target_version = active_db_version

        # Intentar cargar la versión objetivo o el manifiesto atómico
        ml_service.load_active_model(target_version=target_version, raise_on_missing=False)

        if ml_service.model is not None:
            logger.info(
                f"Modelo cargado: {ml_service.model_version} (Umbral: {ml_service.threshold}) "
                f"[Modo Fallback: {ml_service.is_fallback}]"
            )
            try:
                with SessionLocal() as db:
                    # Coordinar con lock a nivel de base de datos para serializar transiciones de modelo activo (Qodo Finding 1)
                    if db.bind.dialect.name == "postgresql":
                        db.execute(text("SELECT pg_advisory_xact_lock(742198)"))

                    # Re-verificar la versión activa bajo esta coordinación
                    current_active = db.query(ModelRun).filter(ModelRun.is_active == True).order_by(ModelRun.id.desc()).first()
                    current_active_version = current_active.model_version if current_active else None

                    if (
                        current_active_version is not None
                        and current_active_version != ml_service.model_version
                        and current_active_version > ml_service.model_version
                    ):
                        logger.info(
                            f"Detectada versión activa más reciente en base de datos: '{current_active_version}' "
                            f"(versión cargada: '{ml_service.model_version}'). Intentando recargar..."
                        )
                        target_version = current_active_version
                        ml_service.load_active_model(target_version=target_version, raise_on_missing=False)

                    raw_m = ml_service.metadata.get("metrics", {})
                    cm = raw_m.get("confusion_matrix", {})
                    tn = cm.get("tn") if "tn" in cm else raw_m.get("true_negatives", 0)
                    fp = cm.get("fp") if "fp" in cm else raw_m.get("false_positives", 0)
                    fn = cm.get("fn") if "fn" in cm else raw_m.get("false_negatives", 0)
                    tp = cm.get("tp") if "tp" in cm else raw_m.get("true_positives", 0)
                    normalized_metrics = {
                        **raw_m,
                        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
                    }

                    if ml_service.is_fallback:
                        # Modo degradado: NO sobrescribir ni desactivar el run activo en DB (Finding: Restarts can permanently roll back a model)
                        logger.warning(
                            f"Estado degradado: La versión activa en base de datos '{current_active_version}' no está disponible "
                            f"en el sistema de archivos local. Sirviendo temporalmente la versión de respaldo '{ml_service.model_version}' "
                            f"sin desactivar '{current_active_version}' en la base de datos."
                        )
                        fallback_run = db.query(ModelRun).filter(ModelRun.model_version == ml_service.model_version).first()
                        if not fallback_run:
                            run_entry = ModelRun(
                                model_version=ml_service.model_version,
                                model_name=ml_service.metadata.get("model_name", "HistGradientBoostingClassifier"),
                                threshold=ml_service.threshold,
                                metrics=normalized_metrics,
                                parameters=ml_service.metadata.get("parameters", {}),
                                is_active=False,
                            )
                            db.add(run_entry)
                            db.commit()
                    else:
                        # Promover y activar el nuevo modelo si es el actual o más reciente
                        active_under_lock = db.query(ModelRun).filter(ModelRun.is_active == True).order_by(ModelRun.id.desc()).first()
                        active_version_under_lock = active_under_lock.model_version if active_under_lock else None

                        if (
                            active_version_under_lock is None
                            or active_version_under_lock == ml_service.model_version
                            or ml_service.model_version >= active_version_under_lock
                        ):
                            db.query(ModelRun).filter(
                                ModelRun.is_active == True,
                                ModelRun.model_version != ml_service.model_version
                            ).update({"is_active": False})

                            existing_run = db.query(ModelRun).filter(ModelRun.model_version == ml_service.model_version).first()
                            if not existing_run:
                                run_entry = ModelRun(
                                    model_version=ml_service.model_version,
                                    model_name=ml_service.metadata.get("model_name", "HistGradientBoostingClassifier"),
                                    threshold=ml_service.threshold,
                                    metrics=normalized_metrics,
                                    parameters=ml_service.metadata.get("parameters", {}),
                                    is_active=True,
                                )
                                db.add(run_entry)
                            else:
                                existing_run.is_active = True
                                existing_run.threshold = ml_service.threshold
                                existing_run.metrics = normalized_metrics

                            db.commit()
                            logger.info(f"Versión de modelo '{ml_service.model_version}' verificada y activa en base de datos.")
                        else:
                            # Se detectó un modelo activo más nuevo en BD que no pudimos cargar o que cambió
                            logger.warning(
                                f"Existe un modelo activo más nuevo en BD ('{active_version_under_lock}'). "
                                f"Preservándolo y entrando en modo degradado sin sobrescribir."
                            )
                            ml_service.is_fallback = True
            except Exception as db_err:
                logger.warning(f"Aviso de sincronización de model_runs en arranque: {db_err}")
    except Exception as e:
        logger.error(f"Error al inicializar artefacto del modelo: {e}")

    yield

    logger.info("Apagando servicio...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "### Servicio de Inteligencia Artificial para Precalificación Crediticia Automatizada\n\n"
        "API REST asíncrona desacoplada construida bajo el estándar **CRISP-ML(Q)** (*Cross-Industry Standard Process "
        "for Machine Learning with Quality Assurance*).\n\n"
        "**Características Principales:**\n"
        "- **Modelo Clasificador:** HistGradientBoostingClassifier (Scikit-Learn 1.9.1).\n"
        "- **Umbral de Decisión Calibrado:** $\\theta = 0.77$ (optimizado bajo costo asimétrico $3\\times FP + 1\\times FN$).\n"
        "- **Métrica de Calidad Principal:** Matthews Correlation Coefficient ($MCC = 0.6192 \\ge 0.55$).\n"
        "- **Seguridad y Auditoría:** Autenticación JWT Bearer, Rate Limiting (120 req/min), headers OWASP y persistencia en Supabase PostgreSQL."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
)

# 1. Middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Middleware de Seguridad: Rate Limiting, Medición de Latencia y Headers OWASP
@app.middleware("http")
async def security_and_latency_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    path = request.url.path

    # Aplicar Rate Limiting contra abusos (excluyendo rutas de documentación Swagger)
    if not (path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi.json")):
        now = time.time()
        # Limpieza de timestamps fuera de la ventana de 60 segundos
        recent_requests = [t for t in _client_request_history[client_ip] if now - t < RATE_LIMIT_WINDOW_SECONDS]
        if len(recent_requests) >= MAX_REQUESTS_PER_WINDOW:
            logger.warning(f"Rate Limit excedido para IP {client_ip} en {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "rate_limit_exceeded",
                    "message": "Límite de peticiones excedido (máximo 120 peticiones por minuto).",
                    "detail": "Protección contra ataques de denegación de servicio y saturación de inferencia activa.",
                    "retry_after_seconds": RATE_LIMIT_WINDOW_SECONDS,
                },
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )
        recent_requests.append(now)
        _client_request_history[client_ip] = recent_requests

        # Control de memoria del Rate Limiter (Finding 14): purga periódica de IPs inactivas
        if len(_client_request_history) > 200:
            stale_ips = [
                ip for ip, timestamps in list(_client_request_history.items())
                if not timestamps or (now - timestamps[-1] >= RATE_LIMIT_WINDOW_SECONDS)
            ]
            for ip in stale_ips:
                _client_request_history.pop(ip, None)

    # Medición de tiempo de ejecución
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"Error no controlado en petición {request.method} {request.url.path}: {exc}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "detail": "Error interno del servidor. Consulte los registros de auditoría.",
                "path": request.url.path,
            },
        )
    process_time = (time.perf_counter() - start_time) * 1000

    # Inyección de headers de diagnóstico y endurecimiento OWASP
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# 3. Manejador Global de Errores de Validación Pydantic (422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Error de validación")
        errors.append({"field": field, "message": msg, "type": err.get("type")})
    
    logger.warning(f"Error de validación 422 en {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "validation_error",
            "message": "Los datos enviados no cumplen con el esquema de validación.",
            "errors": errors,
            "path": request.url.path,
        },
    )


# 4. Manejador Global de Excepciones HTTP (400, 401, 404, etc.)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "http_error",
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
        },
    )


# Endpoint de Verificación de Salud
@app.get("/health", tags=["Salud del Sistema"], status_code=status.HTTP_200_OK, summary="Verificación de salud del servicio")
@app.get("/api/v1/health", tags=["Salud del Sistema"], status_code=status.HTTP_200_OK, summary="Verificación de salud del servicio (v1)")
def health_check():
    db_status = "connected"
    try:
        with engine.connect() as conn:
            pass
    except Exception:
        db_status = "unavailable_or_degraded"

    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "active_model_version": ml_service.model_version,
        "threshold": ml_service.threshold,
        "database": db_status,
    }


# Inclusión de Routers bajo /api/v1
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(predict.router, prefix=settings.API_V1_PREFIX)
app.include_router(history.router, prefix=settings.API_V1_PREFIX)
app.include_router(metrics.router, prefix=settings.API_V1_PREFIX)
app.include_router(train.router, prefix=settings.API_V1_PREFIX)

# Inclusión de Rutas WebSocket
app.include_router(websocket.router)
app.include_router(websocket.router, prefix=settings.API_V1_PREFIX)
