# 📑 Guía de Uso: Swagger UI y Especificación OpenAPI v3

**Servicio de Precalificación Crediticia Automatizada — Metodología CRISP-ML(Q)**  
**Autor:** Alberto Esteban Mamani Donaire  
**Institución:** Universidad Católica Boliviana "San Pablo" (Sede Tarija)  

Este documento describe la especificación formal y las herramientas interactivas de documentación de la API REST del proyecto.

---

## 🌐 1. Documentación Interactiva en Vivo

Con el servidor backend en ejecución local (`http://127.0.0.1:8000`):

* **Swagger UI Interactivo:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
  Permite probar interactivamente todos los endpoints (`/api/v1/predict`, `/api/v1/history`, `/api/v1/metrics`, `/api/v1/train/upload`, `/api/v1/retrain`, `/api/v1/auth/login`, `/health`) con esquemas y payloads precargados.
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
  Vista estructurada y formal para desarrolladores y auditoría.
* **Esquema OpenAPI Crudo (JSON):** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 📄 2. Artefacto Estático Exportado (`swagger.json`)

Para la entrega académica y visualización offline se exportó la especificación formal:

* **Archivo:** [docs/swagger/swagger.json](./swagger.json)
* **Formato:** OpenAPI Specification v3.1.0 (JSON).
* **Compatibilidad:** Importable en Postman, Insomnia, Swagger Editor o generadores de código cliente.
