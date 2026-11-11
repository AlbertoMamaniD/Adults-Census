# Documentación Swagger / OpenAPI de la API REST

Este directorio contiene la especificación y documentación interactiva de la API REST del Servicio de Inteligencia Artificial.

---

## 🌐 Acceso a la Documentación Swagger en Vivo

Cuando el servicio backend esté en ejecución local (`http://localhost:8000`):

* **Swagger UI interactivo:** [http://localhost:8000/docs](http://localhost:8000/docs)
  Permite probar interactivamente todos los endpoints (`/predict`, `/history`, `/metrics`, `/retrain`, `/train/upload`) directamente desde el navegador con payloads de ejemplo.
* **Redoc UI alternativo:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Especificación OpenAPI (JSON crudo):** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 📄 Archivo Estático OpenAPI / Swagger

Para la entrega formal del proyecto, se puede exportar el archivo estático en formato JSON o YAML en esta misma carpeta:

```bash
# Para exportar la especificación a un archivo local:
curl http://localhost:8000/openapi.json -o docs/swagger/swagger.json
```

O guardar aquí el archivo `swagger.yaml` correspondiente para su visualización offline o importación en herramientas como Postman o Insomnia.

