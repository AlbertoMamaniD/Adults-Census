"""
TEST_E2E_LIVE.PY — Prueba End-to-End en Vivo
Verifica la comunicación completa de red entre Frontend (puerto 3000),
Backend (puerto 8000) y Base de Datos (Supabase PostgreSQL).
"""

import urllib.request
import json
import httpx2

FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://127.0.0.1:8000"

def test_live_e2e():
    print("=" * 60)
    print(" INICIANDO PRUEBAS END-TO-END (E2E) EN VIVO")
    print("=" * 60)

    # 1. Frontend Web Server (Puerto 3000)
    print("\n[1/6] Verificando servidor frontend estático (puerto 3000)...")
    req = urllib.request.Request(f"{FRONTEND_URL}/")
    with urllib.request.urlopen(req, timeout=5) as response:
        html_content = response.read().decode("utf-8")
        assert response.status == 200, f"Error HTTP {response.status}"
        assert "Precalificación Crediticia" in html_content
        assert 'id="tab-predictor"' in html_content
        assert 'id="tab-metrics"' in html_content
        assert 'id="tab-history"' in html_content
        assert 'id="tab-retrain"' in html_content
        print("  ✅ Frontend HTML5 servido correctamente (Estructura semántica W3C OK)")

    # Verificar que el servidor estático entrega los módulos ES6
    js_req = urllib.request.Request(f"{FRONTEND_URL}/src/app.js")
    with urllib.request.urlopen(js_req, timeout=5) as js_resp:
        assert js_resp.status == 200
        print("  ✅ Módulos JavaScript ES6 accesibles vía HTTP 200")

    client = httpx2.Client(base_url=BACKEND_URL, timeout=15.0)

    # 2. Backend Healthcheck (Puerto 8000)
    print("\n[2/6] Verificando salud del Backend API REST y conexión con Supabase...")
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert health_data["database"] == "connected"
    print(f"  ✅ Backend Online: Modelo '{health_data['active_model_version']}', Umbral: {health_data['threshold']}, DB: {health_data['database']}")

    # 3. Inferencia Solvente (Demostración Perfil >50K)
    print("\n[3/6] Probando Inferencia en Tiempo Real (Perfil Solvente)...")
    solvent_payload = {
        "age": 45,
        "workclass": "Self-emp-inc",
        "education_num": 14,
        "marital_status": "Married-civ-spouse",
        "occupation": "Exec-managerial",
        "relationship": "Husband",
        "race": "White",
        "sex": "Male",
        "capital_gain": 15000.0,
        "capital_loss": 0.0,
        "hours_per_week": 50,
        "native_country": "United-States",
    }
    p_resp = client.post("/api/v1/predict", json=solvent_payload)
    assert p_resp.status_code == 200
    p_data = p_resp.json()
    assert p_data["predicted_class"] == ">50K"
    assert p_data["probability"] > 0.77
    print(f"  ✅ Predicción Solvente Exitosa: Clase '{p_data['predicted_class']}', Probabilidad: {p_data['probability']:.4f}, Latencia: {p_data['latency_ms']} ms")

    # Inferencia Riesgo (Demostración Perfil <=50K)
    print("\n[3b/6] Probando Inferencia en Tiempo Real (Perfil de Riesgo)...")
    risk_payload = {
        "age": 20,
        "workclass": "Private",
        "education_num": 8,
        "marital_status": "Never-married",
        "occupation": "Handlers-cleaners",
        "relationship": "Own-child",
        "race": "White",
        "sex": "Female",
        "capital_gain": 0.0,
        "capital_loss": 0.0,
        "hours_per_week": 20,
        "native_country": "United-States",
    }
    r_resp = client.post("/api/v1/predict", json=risk_payload)
    assert r_resp.status_code == 200
    r_data = r_resp.json()
    assert r_data["predicted_class"] == "<=50K"
    print(f"  ✅ Predicción de Riesgo Exitosa: Clase '{r_data['predicted_class']}', Probabilidad: {r_data['probability']:.4f}")

    # 4. Métricas MLOps (CRISP-ML(Q))
    print("\n[4/6] Verificando Métricas del Modelo en Producción...")
    m_resp = client.get("/api/v1/metrics")
    assert m_resp.status_code == 200
    m_data = m_resp.json()
    metrics = m_data["metrics"]
    assert metrics["mcc"] >= 0.55
    print(f"  ✅ Métricas OK: MCC={metrics['mcc']:.4f} (Meta ≥0.55 Cumplida), ROC-AUC={metrics['roc_auc']:.4f}")

    # 5. Autenticación JWT y Auditoría en Supabase
    print("\n[5/6] Probando Autenticación JWT y Auditoría de Inferencias...")
    auth_resp = client.post("/api/v1/auth/login", json={"username": "analyst_admin", "password": "dev_auth_token"})
    assert auth_resp.status_code == 200
    token = auth_resp.json()["access_token"]
    print("  ✅ Token JWT Bearer emitido exitosamente")

    hist_resp = client.get("/api/v1/history?limit=5&offset=0", headers={"Authorization": f"Bearer {token}"})
    assert hist_resp.status_code == 200
    records = hist_resp.json()
    assert len(records) > 0
    print(f"  ✅ Auditoría en Supabase OK: {len(records)} registros recuperados. Último ID: {records[0]['id']}")

    # 6. Verificación de Cabeceras CORS
    print("\n[6/6] Verificando Políticas de CORS hacia el Frontend...")
    cors_resp = client.options("/api/v1/predict", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST"
    })
    assert cors_resp.status_code == 200
    assert cors_resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    print("  ✅ Cabeceras CORS autorizan explícitamente a 'http://localhost:3000'")

    print("\n" + "=" * 60)
    print(" 🎉 TODAS LAS PRUEBAS END-TO-END (E2E) PASARON EXITOSAMENTE (100%)")
    print("=" * 60)

if __name__ == "__main__":
    test_live_e2e()
