# Video Demostrativo del Proyecto (5 Minutos)

Este directorio contiene el enlace y el guion estructurado para la grabación del video demostrativo de **5 minutos** exigido en los entregables del Trabajo Final.

---

## 🔗 Enlace al Video

* **Plataforma:** [YouTube / Google Drive / Loom]
* **URL del video:** *(Colocar aquí el enlace público o no listado al video grabado)*
* **Duración:** ~5 minutos

---

## ⏱️ Guion Estructurado para el Video (5 Minutos)

| Minuto | Sección | Contenido a Mostrar en Pantalla | Qué decir |
|---|---|---|---|
| **0:00 - 0:45** | **1. Introducción y Negocio** | Diapositiva inicial o `README.md` | Presentarse (Alberto Esteban Mamani Donaire), materia, universidad (UCB Tarija). Explicar el problema: preclasificación de crédito para ingresos `>50K` usando el dataset Adult Census Income y metodología CRISP-ML(Q). |
| **0:45 - 1:45** | **2. Modelo y Metodología CRISP-ML(Q)** | Mostrar el notebook `notebooks/modelo_crisp_ml.ipynb` y gráficos | Explicar las 6 fases: tratamiento de nulos y desbalance (76/24), métrica MCC (no accuracy), comparación de modelos (Random Forest/Gradient Boosting), umbral óptimo y métricas alcanzadas. |
| **1:45 - 2:45** | **3. Servicio de IA (API REST y Swagger)** | Navegador en `http://localhost:8000/docs` | Mostrar los 5 endpoints requeridos en Swagger: `/predict`, `/history`, `/metrics`, `/retrain` y `/train/upload`. Ejecutar una predicción de prueba en Swagger. Mostrar la base de datos en Supabase con las tablas `model_runs` y `predictions`. |
| **2:45 - 4:15** | **4. Aplicación Web Cliente (Frontend)** | Interfaz gráfica en el navegador | Demostrar en vivo: 1) Llenar el formulario y obtener una predicción en vivo con su probabilidad y latencia; 2) Ver el registro en la tabla de historial; 3) Visualizar el dashboard de métricas del modelo; 4) Subir un CSV y disparar el reentrenamiento. |
| **4:15 - 5:00** | **5. Conclusiones y Plus de Revisión PR** | Repositorio GitHub y Pull Request con IA | Mostrar el repositorio público en GitHub, la evidencia de revisión del PR realizada por una IA (el plus de la materia), y cerrar con una conclusión breve. |

