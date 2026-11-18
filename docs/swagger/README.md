# 📑 Documentación Swagger / OpenAPI de la API REST

Este directorio contiene la especificación formal y documentación interactiva de la API REST del Servicio de Inteligencia Artificial para la precalificación crediticia automatizada simulada.

---

## 🌐 1. Acceso a la Documentación Interactiva en Vivo

Cuando el servicio backend esté en ejecución local (`http://127.0.0.1:8000`):

* **Swagger UI interactivo:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
  Permite probar interactivamente todos los endpoints (`/api/v1/predict`, `/api/v1/history`, `/api/v1/metrics`, `/api/v1/train/upload`, `/api/v1/retrain`, `/api/v1/auth/login`, `/health`) directamente desde el navegador con payloads de ejemplo predefinidos.
* **Redoc UI alternativo:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
  Vista de especificación técnica formal y estructurada para desarrolladores y auditoría.
* **Especificación OpenAPI (JSON crudo):** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 📄 2. Archivo Estático OpenAPI Exportado (`swagger.json`)

Para la entrega formal del proyecto académico y trazabilidad de software, se encuentra exportado el archivo estático:

* **Ruta del artefacto:** `docs/swagger/swagger.json`
* **Formato:** OpenAPI Specification v3.1.0 (JSON).
* **Compatibilidad:** Puede ser importado directamente en **Postman**, **Insomnia**, **Swagger Editor** o herramientas de generación de SDKs clientes.

Para actualizar o re-exportar la especificación en cualquier momento tras modificaciones en los endpoints:
```powershell
# Opción directa vía cURL con el backend corriendo:
curl http://127.0.0.1:8000/openapi.json -o docs/swagger/swagger.json
```
