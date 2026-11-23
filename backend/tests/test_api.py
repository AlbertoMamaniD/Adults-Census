import io
import json
import sys
from pathlib import Path
import unittest

# Asegurar backend en PYTHONPATH
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.main import app, lifespan
from app.services.ml_service import ml_service
from app.database.connection import SessionLocal
from app.database.models import ModelRun, Prediction, TrainingDataset


class TestRobustBackendAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Asegurar creación de tablas en SQLite o verificar conexión
        from app.database.connection import Base, engine
        Base.metadata.create_all(bind=engine)

        # 2. Inicializar registro del modelo activo si no existe (CI / entornos efímeros SQLite)
        with SessionLocal() as db:
            active_model = db.query(ModelRun).filter(ModelRun.model_version == ml_service.model_version).first()
            raw_m = ml_service.metadata.get("metrics", {})
            cm = raw_m.get("confusion_matrix", {})
            tn = cm.get("tn") if "tn" in cm else raw_m.get("true_negatives", 0)
            fp = cm.get("fp") if "fp" in cm else raw_m.get("false_positives", 0)
            fn = cm.get("fn") if "fn" in cm else raw_m.get("false_negatives", 0)
            tp = cm.get("tp") if "tp" in cm else raw_m.get("true_positives", 0)
            norm_m = {
                **raw_m,
                "confusion_matrix": {
                    "tn": int(tn),
                    "fp": int(fp),
                    "fn": int(fn),
                    "tp": int(tp),
                },
            }
            # Desactivar cualquier otro modelo activo para respetar la restricción única de un solo activo
            db.query(ModelRun).filter(ModelRun.is_active == True).update({"is_active": False})

            if not active_model:
                run_entry = ModelRun(
                    model_version=ml_service.model_version,
                    model_name=ml_service.metadata.get("model_name", "HistGradientBoostingClassifier"),
                    threshold=ml_service.threshold,
                    metrics=norm_m,
                    parameters=ml_service.metadata.get("parameters", {}),
                    is_active=True,
                )
                db.add(run_entry)
            else:
                active_model.metrics = norm_m
                active_model.is_active = True
            db.commit()

        cls.client = TestClient(app)
        # Iniciar sesión para obtener token de autenticación para rutas protegidas
        login_resp = cls.client.post(
            "/api/v1/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        )
        if login_resp.status_code == 200:
            cls.token = login_resp.json()["access_token"]
            cls.auth_headers = {"Authorization": f"Bearer {cls.token}"}
        else:
            cls.token = ""
            cls.auth_headers = {}

    # =========================================================================
    # 1. PRUEBAS DE SALUD Y ARQUITECTURA
    # =========================================================================
    def test_01_healthcheck_and_headers(self):
        """Verifica el estado de salud, conexión a Supabase y cabeceras de tiempo."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("active_model_version", data)
        self.assertAlmostEqual(data["threshold"], ml_service.threshold, places=2)
        # Verificar header de tiempo de procesamiento inyectado por middleware
        self.assertIn("x-process-time-ms", response.headers)
        # Verificar cabeceras de seguridad OWASP
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(response.headers.get("x-frame-options"), "DENY")
        self.assertEqual(response.headers.get("referrer-policy"), "strict-origin-when-cross-origin")

    # =========================================================================
    # 2. PRUEBAS DE SEGURIDAD Y AUTENTICACIÓN JWT
    # =========================================================================
    def test_02_auth_login_success(self):
        """Login exitoso parametrizado con credenciales de configuración."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["username"], settings.ADMIN_USERNAME)

    def test_03_auth_login_invalid_password(self):
        """Rechazo con 401 por credencial incorrecta."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": "incorrect_test_credential_val"},
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("detail", data)

    def test_04_auth_login_invalid_username(self):
        """Rechazo con 401 por cuenta inexistente."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "unregistered_test_account", "password": settings.ADMIN_PASSWORD},
        )
        self.assertEqual(response.status_code, 401)

    # =========================================================================
    # 3. PRUEBAS DE INFERENCIA EN TIEMPO REAL Y CASOS DE NEGOCIO
    # =========================================================================
    def test_05_predict_standard_insolvent_profile(self):
        """Inferencia para un perfil con ingresos típicos <=50K."""
        payload = {
            "age": 25,
            "workclass": "Private",
            "education_num": 9,
            "marital_status": "Never-married",
            "occupation": "Handlers-cleaners",
            "relationship": "Own-child",
            "race": "Black",
            "sex": "Male",
            "capital_gain": 0.0,
            "capital_loss": 0.0,
            "hours_per_week": 35,
            "native_country": "United-States",
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["predicted_class"], "<=50K")
        self.assertLess(data["probability"], ml_service.threshold)
        self.assertAlmostEqual(data["threshold_applied"], ml_service.threshold, places=2)
        self.assertIn("No califica", data["recommendation"])
        self.assertGreater(data["latency_ms"], 0.0)

    def test_06_predict_high_solvency_profile(self):
        """Inferencia para un perfil solvente (alta probabilidad de >50K)."""
        payload = {
            "age": 52,
            "workclass": "Self-emp-inc",
            "education_num": 16,  # Doctorado
            "marital_status": "Married-civ-spouse",
            "occupation": "Exec-managerial",
            "relationship": "Husband",
            "race": "White",
            "sex": "Male",
            "capital_gain": 99999.0,  # Alta ganancia de capital
            "capital_loss": 0.0,
            "hours_per_week": 60,
            "native_country": "United-States",
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["predicted_class"], ">50K")
        self.assertGreaterEqual(data["probability"], ml_service.threshold)
        self.assertIn("Califica para producto de crédito", data["recommendation"])

    def test_07_predict_unseen_category_robustness(self):
        """Resiliencia ante categorías no vistas en entrenamiento (handle_unknown='ignore')."""
        payload = {
            "age": 40,
            "workclass": "Cyber-Industry-99",  # Categoría inédita
            "education_num": 12,
            "marital_status": "Custom-Status",
            "occupation": "AI-Prompt-Engineer",  # Categoría inédita
            "relationship": "Unspecified",
            "race": "Other",
            "sex": "Female",
            "capital_gain": 1000.0,
            "capital_loss": 0.0,
            "hours_per_week": 40,
            "native_country": "Moon-Colony",  # País inédito
        }
        response = self.client.post("/api/v1/predict", json=payload)
        # No debe colapsar con 500, debe manejar la categoría desconocida e inferir
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["predicted_class"], [">50K", "<=50K"])

    # =========================================================================
    # 4. PRUEBAS DE FRONTERA Y VALIDACIÓN ESTRICTA (422 UNPROCESSABLE ENTITY)
    # =========================================================================
    def test_08_predict_validation_underage(self):
        """Rechazo si el solicitante es menor a 17 años."""
        payload = {
            "age": 16,  # Límite inferior violado
            "workclass": "Private",
            "education_num": 10,
            "marital_status": "Never-married",
            "occupation": "Other-service",
            "relationship": "Own-child",
            "race": "White",
            "sex": "Male",
            "capital_gain": 0.0,
            "capital_loss": 0.0,
            "hours_per_week": 20,
            "native_country": "United-States",
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_09_predict_validation_overage(self):
        """Rechazo si la edad supera los 100 años."""
        payload = {
            "age": 105,  # Límite superior violado
            "workclass": "Private",
            "education_num": 10,
            "marital_status": "Never-married",
            "occupation": "Other-service",
            "relationship": "Own-child",
            "race": "White",
            "sex": "Male",
            "capital_gain": 0.0,
            "capital_loss": 0.0,
            "hours_per_week": 20,
            "native_country": "United-States",
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_10_predict_validation_negative_capital(self):
        """Rechazo si la ganancia de capital es negativa."""
        payload = {
            "age": 35,
            "workclass": "Private",
            "education_num": 10,
            "marital_status": "Never-married",
            "occupation": "Sales",
            "relationship": "Not-in-family",
            "race": "White",
            "sex": "Female",
            "capital_gain": -150.0,  # Inválido
            "capital_loss": 0.0,
            "hours_per_week": 40,
            "native_country": "United-States",
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_11_predict_validation_empty_whitespace_string(self):
        """Rechazo si un atributo de texto contiene únicamente espacios en blanco."""
        payload = {
            "age": 35,
            "workclass": "   ",  # Vacío tras sanitizar
            "education_num": 10,
            "marital_status": "Never-married",
            "occupation": "Sales",
            "relationship": "Not-in-family",
            "race": "White",
            "sex": "Female",
            "capital_gain": 0.0,
            "capital_loss": 0.0,
            "hours_per_week": 40,
            "native_country": "United-States",
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_12_predict_validation_missing_field(self):
        """Rechazo cuando falta una propiedad requerida del contrato."""
        payload = {
            "age": 35,
            # Falta workclass
            "education_num": 10,
            "marital_status": "Never-married",
            "occupation": "Sales",
            "relationship": "Not-in-family",
            "race": "White",
            "sex": "Female",
            "capital_gain": 0.0,
            "capital_loss": 0.0,
            "hours_per_week": 40,
            "native_country": "United-States",
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 422)

    # =========================================================================
    # 5. PRUEBAS DE MÉTRICAS Y CONTRATO CRISP-ML(Q)
    # =========================================================================
    def test_13_metrics_contract_and_thresholds(self):
        """Verifica que las métricas expuestas satisfagan todas las metas de negocio."""
        response = self.client.get("/api/v1/metrics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertAlmostEqual(data["threshold"], ml_service.threshold, places=2)
        metrics = data["metrics"]
        self.assertGreaterEqual(metrics["mcc"], 0.55, "MCC debe ser >= 0.55")
        self.assertGreaterEqual(metrics["precision"], 0.75, "Precision debe ser >= 0.75")
        self.assertGreaterEqual(metrics["recall"], 0.60, "Recall debe ser >= 0.60")
        self.assertGreaterEqual(metrics["roc_auc"], 0.90, "ROC-AUC debe ser >= 0.90")
        
        cm = metrics["confusion_matrix"]
        self.assertTrue(all(k in cm for k in ["tn", "fp", "fn", "tp"]))
        self.assertGreater(cm["tp"], 0)
        self.assertGreater(cm["tn"], 0)

    # =========================================================================
    # 6. PRUEBAS DE HISTORIAL Y PROTECCIÓN DE DATOS (FINDING 3)
    # =========================================================================
    def test_14_history_unauthenticated_rejected(self):
        """Rechazo con 401 en /history para peticiones anónimas sin token Bearer."""
        response = self.client.get("/api/v1/history")
        self.assertEqual(response.status_code, 401)

    def test_14b_history_authenticated_pagination(self):
        """Verifica la consulta con paginación y token de autenticación en Supabase."""
        response = self.client.get("/api/v1/history?limit=3&offset=0", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertLessEqual(len(data), 3)
        if len(data) >= 2:
            self.assertGreaterEqual(data[0]["id"], data[1]["id"])

    # =========================================================================
    # 7. PRUEBAS DE CARGA DE DATASET, SEGURIDAD Y VALIDACIÓN (FINDINGS 2, 3, 7, 11)
    # =========================================================================
    def test_15_upload_dataset_unauthenticated_rejected(self):
        """Rechazo con 401 en /train/upload si no se proporciona autenticación."""
        fake_file = io.BytesIO(b"age,income\n30,<=50K")
        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("dataset.csv", fake_file, "text/csv")},
        )
        self.assertEqual(response.status_code, 401)

    def test_15b_upload_dataset_reject_non_csv(self):
        """Rechazo con 400 si el archivo subido no es CSV."""
        fake_file = io.BytesIO(b"some binary or text content")
        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("dataset.txt", fake_file, "text/plain")},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Solo se admiten archivos con extensión .csv", response.json()["detail"])

    def test_16_upload_dataset_reject_empty_csv(self):
        """Rechazo con 400 si el archivo CSV está vacío (0 bytes)."""
        empty_file = io.BytesIO(b"")
        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("empty.csv", empty_file, "text/csv")},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_17_upload_dataset_reject_missing_columns(self):
        """Rechazo con 400 si el CSV no contiene las columnas censales obligatorias."""
        bad_csv = io.BytesIO(b"name,surname,phone\n" + b"Juan,Perez,71234567\n" * 12)
        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("invalido.csv", bad_csv, "text/csv")},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("carece de las siguientes columnas requeridas", response.json()["detail"])

    def test_17b_upload_dataset_reject_single_class(self):
        """Rechazo con 400 si el CSV contiene solo una clase (Finding 7)."""
        csv_header = "age,workclass,education_num,marital_status,occupation,relationship,race,sex,capital_gain,capital_loss,hours_per_week,native_country,income\n"
        row_single = "30,Private,10,Never-married,Sales,Not-in-family,White,Male,0,0,40,United-States,<=50K\n"
        csv_content = (csv_header + row_single * 12).encode("utf-8")
        file_obj = io.BytesIO(csv_content)

        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("single_class.csv", file_obj, "text/csv")},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("debe contener ambas clases", response.json()["detail"])

    def test_18_upload_dataset_success(self):
        """Carga y validación exitosa de un mini-dataset válido con ambas clases (Finding 7)."""
        csv_header = "age,workclass,education_num,marital_status,occupation,relationship,race,sex,capital_gain,capital_loss,hours_per_week,native_country,income\n"
        row_low = "30,Private,10,Never-married,Sales,Not-in-family,White,Male,0,0,40,United-States,<=50K\n"
        row_high = "45,Private,13,Married-civ-spouse,Exec-managerial,Husband,White,Male,5000,0,50,United-States,>50K\n"
        csv_content = (csv_header + row_low * 6 + row_high * 6).encode("utf-8")
        valid_file = io.BytesIO(csv_content)

        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("mini_adult_test.csv", valid_file, "text/csv")},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["rows_ingested"], 12)
        self.assertIn("dataset_id", data)

    def test_18b_upload_dataset_dotted_headers_success(self):
        """Carga exitosa soportando cabeceras con puntos de Kaggle (Finding 2)."""
        csv_header = "age,workclass,education.num,marital.status,occupation,relationship,race,sex,capital.gain,capital.loss,hours.per.week,native.country,income\n"
        row_low = "28,Private,9,Never-married,Handlers-cleaners,Not-in-family,Black,Male,0,0,40,United-States,<=50K\n"
        row_high = "50,Self-emp-inc,14,Married-civ-spouse,Prof-specialty,Husband,White,Male,10000,0,45,United-States,>50K\n"
        csv_content = (csv_header + row_low * 6 + row_high * 6).encode("utf-8")
        valid_file = io.BytesIO(csv_content)

        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("kaggle_dotted_adult.csv", valid_file, "text/csv")},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["rows_ingested"], 12)

    def test_18c_retrain_unauthenticated_rejected(self):
        """Rechazo con 401 en /retrain si no se suministra token Bearer (Finding 3)."""
        response = self.client.post("/api/v1/retrain")
        self.assertEqual(response.status_code, 401)

    # =========================================================================
    # 8. PRUEBAS DE COMUNICACIÓN EN TIEMPO REAL (WEBSOCKET) (FINDINGS 1, 8, 12)
    # =========================================================================
    def test_19_websocket_retrain_stream(self):
        """Verifica el handshake WebSocket, recepción de bienvenida y respuesta a ping."""
        with self.client.websocket_connect("/ws/retrain") as websocket:
            welcome_msg = websocket.receive_json()
            self.assertEqual(welcome_msg["stage"], "connected")
            self.assertIn("Conectado", welcome_msg["message"])

            # Probar ping - pong
            websocket.send_text("ping")
            pong_msg = websocket.receive_text()
            self.assertEqual(pong_msg, "pong")

    def test_19b_websocket_invalid_token_rejected(self):
        """Rechazo del handshake con código de política violada ante token inválido (Finding 1)."""
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/retrain?token=invalid_forged_token"):
                pass

    # =========================================================================
    # 9. PRUEBAS DE RESILIENCIA EN ARRANQUE Y RECUPERACIÓN DE MLOPS (QODO BUGS)
    # =========================================================================
    def test_20_predict_recovery_in_fallback_preserves_active_run(self):
        """Verifica que la auto-recuperación de ModelRun en fallback no reactive modelos obsoletos (Qodo Issue 1)."""
        original_fallback = ml_service.is_fallback
        original_version = ml_service.model_version
        test_fallback_version = "v_test_fallback_recovery_999"
        test_active_version = "v_test_active_retrained_999"

        with SessionLocal() as db:
            # Limpiar previos si existieran respetando restricciones de integridad referencial
            db.query(Prediction).filter(Prediction.model_version.in_([test_fallback_version, test_active_version])).delete()
            db.query(ModelRun).filter(ModelRun.model_version.in_([test_fallback_version, test_active_version])).delete()
            # Desactivar temporalmente el modelo activo real para respetar el índice de unicidad parcial
            db.query(ModelRun).filter(ModelRun.is_active == True).update({"is_active": False})
            # Crear un run activo existente en DB
            active_run = ModelRun(
                model_version=test_active_version,
                model_name="HistGradientBoostingClassifier",
                threshold=0.77,
                metrics={"mcc": 0.65, "confusion_matrix": {"tn": 10, "fp": 1, "fn": 1, "tp": 10}},
                is_active=True,
            )
            db.add(active_run)
            db.commit()

        try:
            # Simular que el servicio está en modo degradado (fallback)
            ml_service.is_fallback = True
            ml_service.model_version = test_fallback_version

            # Ejecutar una predicción que disparará la auto-recuperación de ModelRun en DB
            payload = {
                "age": 35,
                "workclass": "Private",
                "education_num": 13,
                "marital_status": "Married-civ-spouse",
                "occupation": "Exec-managerial",
                "relationship": "Husband",
                "race": "White",
                "sex": "Male",
                "capital_gain": 0.0,
                "capital_loss": 0.0,
                "hours_per_week": 40,
                "native_country": "United-States",
            }
            resp = self.client.post("/api/v1/predict", json=payload)
            self.assertEqual(resp.status_code, 200)

            # Verificar en DB que la versión de fallback se insertó como is_active=False
            with SessionLocal() as db:
                rec_run = db.query(ModelRun).filter(ModelRun.model_version == test_fallback_version).first()
                self.assertIsNotNone(rec_run)
                self.assertFalse(rec_run.is_active, "El run de respaldo insertado por predict no debe marcarse como activo")

                active_check = db.query(ModelRun).filter(ModelRun.model_version == test_active_version).first()
                self.assertIsNotNone(active_check)
                self.assertTrue(active_check.is_active, "El run retrenado activo debe permanecer como activo")
        finally:
            ml_service.is_fallback = original_fallback
            ml_service.model_version = original_version
            with SessionLocal() as db:
                db.query(Prediction).filter(Prediction.model_version.in_([test_fallback_version, test_active_version])).delete()
                db.query(ModelRun).filter(ModelRun.model_version.in_([test_fallback_version, test_active_version])).delete()
                current_real = db.query(ModelRun).order_by(ModelRun.id.desc()).first()
                if current_real:
                    current_real.is_active = True
                db.commit()

    def test_21_startup_reconciliation_handles_concurrent_version_change(self):
        """Verifica que el arranque maneje cambios concurrentes de versión activa en DB (Qodo Issue 2)."""
        test_new_active_version = "v_test_concurrent_active_888"

        with SessionLocal() as db:
            db.query(ModelRun).filter(ModelRun.model_version == test_new_active_version).delete()
            db.query(ModelRun).filter(ModelRun.is_active == True).update({"is_active": False})
            new_run = ModelRun(
                model_version=test_new_active_version,
                model_name="HistGradientBoostingClassifier",
                threshold=0.77,
                metrics={"mcc": 0.62, "confusion_matrix": {"tn": 10, "fp": 1, "fn": 1, "tp": 10}},
                is_active=True,
            )
            db.add(new_run)
            db.commit()

        try:
            # Simular la secuencia de startup de lifespan:
            # 1. Probe inicial ve None o versión previa
            active_db_version = "v_previa_inexistente"
            ml_service.load_active_model(target_version=active_db_version, raise_on_missing=False)

            # 2. La segunda consulta en DB descubre que ahora la activa es test_new_active_version
            with SessionLocal() as db:
                current_active = db.query(ModelRun).filter(ModelRun.is_active == True).order_by(ModelRun.id.desc()).first()
                current_active_version = current_active.model_version if current_active else None

                self.assertNotEqual(current_active_version, active_db_version)

                # El arranque detecta el cambio e intenta recargar la versión actual
                active_db_version = current_active_version
                ml_service.load_active_model(target_version=active_db_version, raise_on_missing=False)

                # Como test_new_active_version no tiene archivo en disco, entra en modo fallback
                self.assertTrue(ml_service.is_fallback)

                # Y verifica que la versión activa en DB NO haya sido desactivada
                active_check = db.query(ModelRun).filter(ModelRun.model_version == test_new_active_version).first()
                self.assertTrue(active_check.is_active)
        finally:
            with SessionLocal() as db:
                db.query(ModelRun).filter(ModelRun.model_version == test_new_active_version).delete()
                # Restaurar el modelo actual como activo
                current_real = db.query(ModelRun).order_by(ModelRun.id.desc()).first()
                if current_real:
                    current_real.is_active = True
                db.commit()
            ml_service.load_active_model(raise_on_missing=False)

    def test_22_concurrent_active_unique_constraint_enforced(self):
        """Verifica que el índice único parcial impida tener más de un modelo activo en base de datos."""
        v_test_a = "v_test_unique_active_a"
        v_test_b = "v_test_unique_active_b"

        with SessionLocal() as db:
            db.query(ModelRun).filter(ModelRun.model_version.in_([v_test_a, v_test_b])).delete()
            # Desactivar temporalmente cualquier activo
            db.query(ModelRun).filter(ModelRun.is_active == True).update({"is_active": False})
            run_a = ModelRun(
                model_version=v_test_a,
                model_name="HistGradientBoostingClassifier",
                threshold=0.77,
                metrics={"mcc": 0.60, "confusion_matrix": {"tn": 1, "fp": 0, "fn": 0, "tp": 1}},
                is_active=True,
            )
            db.add(run_a)
            db.commit()

            # Intentar insertar un segundo modelo con is_active=True debe disparar IntegrityError
            run_b = ModelRun(
                model_version=v_test_b,
                model_name="HistGradientBoostingClassifier",
                threshold=0.77,
                metrics={"mcc": 0.60, "confusion_matrix": {"tn": 1, "fp": 0, "fn": 0, "tp": 1}},
                is_active=True,
            )
            db.add(run_b)
            with self.assertRaises(IntegrityError):
                db.commit()
            db.rollback()

            # Pero insertarlo como inactivo sí está permitido
            run_b_inactive = ModelRun(
                model_version=v_test_b,
                model_name="HistGradientBoostingClassifier",
                threshold=0.77,
                metrics={"mcc": 0.60, "confusion_matrix": {"tn": 1, "fp": 0, "fn": 0, "tp": 1}},
                is_active=False,
            )
            db.add(run_b_inactive)
            db.commit()

            # Limpiar
            db.query(ModelRun).filter(ModelRun.model_version.in_([v_test_a, v_test_b])).delete()
            # Restaurar el modelo real más reciente como activo
            current_real = db.query(ModelRun).order_by(ModelRun.id.desc()).first()
            if current_real:
                current_real.is_active = True
            db.commit()


if __name__ == "__main__":
    unittest.main()
