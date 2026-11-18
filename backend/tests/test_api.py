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
from app.config import settings
from app.main import app


class TestRobustBackendAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

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
        self.assertAlmostEqual(data["threshold"], 0.77, places=2)
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
        self.assertLess(data["probability"], 0.77)
        self.assertAlmostEqual(data["threshold_applied"], 0.77, places=2)
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
        self.assertGreaterEqual(data["probability"], 0.77)
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
        self.assertAlmostEqual(data["threshold"], 0.77, places=2)
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
    # 6. PRUEBAS DE HISTORIAL Y PAGINACIÓN
    # =========================================================================
    def test_14_history_pagination_and_ordering(self):
        """Verifica la consulta con paginación y orden cronológico en Supabase."""
        response = self.client.get("/api/v1/history?limit=3&offset=0")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertLessEqual(len(data), 3)
        if len(data) >= 2:
            # Comprobar que viene ordenado de más reciente a más antiguo
            self.assertGreaterEqual(data[0]["id"], data[1]["id"])

    # =========================================================================
    # 7. PRUEBAS DE CARGA DE DATASET (UPLOAD) Y VALIDACIÓN DE ARCHIVOS
    # =========================================================================
    def test_15_upload_dataset_reject_non_csv(self):
        """Rechazo con 400 si el archivo subido no es CSV."""
        fake_file = io.BytesIO(b"some binary or text content")
        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("dataset.txt", fake_file, "text/plain")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Solo se admiten archivos con extensión .csv", response.json()["detail"])

    def test_16_upload_dataset_reject_empty_csv(self):
        """Rechazo con 400 si el archivo CSV está vacío (0 bytes)."""
        empty_file = io.BytesIO(b"")
        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("empty.csv", empty_file, "text/csv")},
        )
        self.assertEqual(response.status_code, 400)

    def test_17_upload_dataset_reject_missing_columns(self):
        """Rechazo con 400 si el CSV no contiene las columnas censales obligatorias."""
        bad_csv = io.BytesIO(b"name,surname,phone\n" + b"Juan,Perez,71234567\n" * 12)
        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("invalido.csv", bad_csv, "text/csv")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("carece de las siguientes columnas requeridas", response.json()["detail"])

    def test_18_upload_dataset_success(self):
        """Carga y validación exitosa de un mini-dataset válido."""
        csv_header = "age,workclass,education_num,marital_status,occupation,relationship,race,sex,capital_gain,capital_loss,hours_per_week,native_country,income\n"
        row = "30,Private,10,Never-married,Sales,Not-in-family,White,Male,0,0,40,United-States,<=50K\n"
        csv_content = (csv_header + row * 12).encode("utf-8")
        valid_file = io.BytesIO(csv_content)

        response = self.client.post(
            "/api/v1/train/upload",
            files={"file": ("mini_adult_test.csv", valid_file, "text/csv")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["rows_ingested"], 12)
        self.assertIn("dataset_id", data)

    # =========================================================================
    # 8. PRUEBAS DE COMUNICACIÓN EN TIEMPO REAL (WEBSOCKET)
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


if __name__ == "__main__":
    unittest.main()
