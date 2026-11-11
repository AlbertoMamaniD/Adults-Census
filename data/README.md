# Directorio de Datos (`data/`)

Este directorio contiene los conjuntos de datos utilizados para el entrenamiento, validación y prueba del modelo de Inteligencia Artificial.

## 1. Dataset Principal: Adult Census Income

* **Archivo esperado:** `adult.csv`
* **Fuente oficial:** [Kaggle - Adult Census Income](https://www.kaggle.com/datasets/uciml/adult-census-income)
* **Tamaño aproximado:** 32.561 registros y 15 columnas.
* **Nota de versión:** Excluido del control de versiones (`.gitignore`) para evitar subir archivos voluminosos al repositorio público.

## 2. Estructura y Diccionario de Datos

| Columna | Tipo de Dato | Rol | Valores de Ejemplo / Rango |
|---|---|---|---|
| `age` | Numérico (int) | Característica | 17 a 90 años |
| `workclass` | Categórico (str) | Característica | `Private`, `Self-emp-not-inc`, `Local-gov`, `?` |
| `fnlwgt` | Numérico (int) | Descartado | Ponderación censal (no representativo del individuo) |
| `education` | Categórico (str) | Descartado | Nivel educativo textual (duplicado con `education.num`) |
| `education.num` | Numérico (int) | Característica | 1 a 16 (años/nivel de educación formal) |
| `marital.status` | Categórico (str) | Característica | `Married-civ-spouse`, `Never-married`, `Divorced`, etc. |
| `occupation` | Categórico (str) | Característica | `Tech-support`, `Craft-repair`, `Exec-managerial`, `?` |
| `relationship` | Categórico (str) | Característica | `Husband`, `Not-in-family`, `Own-child`, `Unmarried` |
| `race` | Categórico (str) | Auditoría / Característica | `White`, `Black`, `Asian-Pac-Islander`, etc. |
| `sex` | Categórico (str) | Auditoría / Característica | `Male`, `Female` |
| `capital.gain` | Numérico (float) | Característica | Ganancias de capital ($0 a $99.999) |
| `capital.loss` | Numérico (float) | Característica | Pérdidas de capital ($0 a $4.356) |
| `hours.per.week` | Numérico (int) | Característica | Horas trabajadas por semana (1 a 99) |
| `native.country` | Categórico (str) | Característica | `United-States`, `Mexico`, `Germany`, `?` |
| `income` | Categórico (str) | **Variable Objetivo (Target)** | `<=50K` (0) o `>50K` (1) |

## 3. Requisitos para Archivos de Re-entrenamiento

Cuando se utilice el endpoint de subida de datos de entrenamiento (`POST /api/v1/train/upload`) desde la interfaz gráfica:
1. El archivo debe estar en formato **CSV** delimitado por comas.
2. Debe contener las mismas cabeceras descritas en la tabla anterior.
3. Los valores nulos o desconocidos pueden representarse con `?` o vacíos (el pipeline de preprocesamiento se encarga de su imputación adecuada).
4. La columna objetivo `income` debe estar presente con valores válidos (`<=50K` o `>50K`).
