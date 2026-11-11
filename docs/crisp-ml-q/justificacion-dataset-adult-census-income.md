# Justificación de la elección del dataset Adult Census Income

## 1. De qué trata el dataset

Adult Census Income es un conjunto de datos del censo de Estados Unidos de 1994, publicado por UCI y disponible en Kaggle. Cada fila representa a una persona adulta con sus datos demográficos y laborales. La última columna indica si esa persona gana más de 50.000 dólares al año o no.

- Tamaño: cerca de 32.500 registros.
- Columnas: 15 en total, 14 variables de entrada y 1 variable objetivo.
- Fuente: https://www.kaggle.com/datasets/uciml/adult-census-income

## 2. Variables

| Variable | Descripción | Tipo |
|---|---|---|
| age | Edad de la persona | Numérica |
| workclass | Tipo de empleador: privado, gobierno, independiente, etc. | Categórica |
| fnlwgt | Peso estadístico del censo | Numérica |
| education | Nivel educativo alcanzado | Categórica |
| education.num | Nivel educativo expresado en número | Numérica |
| marital.status | Estado civil | Categórica |
| occupation | Ocupación o tipo de trabajo | Categórica |
| relationship | Rol dentro del hogar | Categórica |
| race | Raza | Categórica |
| sex | Sexo | Categórica |
| capital.gain | Ganancias de capital del año | Numérica |
| capital.loss | Pérdidas de capital del año | Numérica |
| hours.per.week | Horas trabajadas por semana | Numérica |
| native.country | País de origen | Categórica |
| income | Variable objetivo: ingreso menor o igual a 50K, o mayor a 50K | Binaria |

Observaciones sobre las variables:

- education y education.num expresan lo mismo, por lo que se conserva solo una.
- fnlwgt describe el muestreo del censo y no a la persona, por lo que se descarta.
- workclass, occupation y native.country traen valores faltantes marcados con el símbolo ?, que se tratan en la fase de preparación de datos.

## 3. Qué se quiere lograr

Construir un modelo de clasificación supervisada que, a partir de los datos demográficos y laborales de una persona, prediga si su ingreso anual supera los 50.000 dólares.

En el escenario de negocio, una entidad financiera usaría el modelo para preclasificar solicitantes de un producto de mayor monto. Con esto se busca:

1. Reducir el tiempo de evaluación inicial de cada solicitud.
2. Evitar ofrecer productos a clientes sin capacidad de pago.
3. No perder clientes de ingreso alto que sí deberían recibir la oferta.

El modelo se expone mediante una API con un endpoint POST que recibe los datos de una persona y devuelve la clase predicha junto con su probabilidad. Cada predicción se guarda en una base de datos y el modelo se reentrena siguiendo CRISP-ML(Q).

## 4. Por qué elegí este dataset

### 4.1 Es apto para aprendizaje supervisado

Tiene una variable objetivo binaria bien definida y suficientes registros para entrenar, validar y probar con particiones estables. Permite usar modelos lineales como la regresión logística y también modelos de árboles como random forest y gradient boosting, lo que facilita comparar enfoques.

### 4.2 Mezcla de variables numéricas y categóricas

Obliga a aplicar preparación de datos real: codificación de categóricas, escalado de numéricas, tratamiento de valores faltantes y selección de variables. Esto permite documentar bien la fase de preparación de datos de CRISP-ML(Q).

### 4.3 Clases desbalanceadas

Aproximadamente 76 % de los registros son de ingreso menor o igual a 50K y 24 % de ingreso mayor. Esto justifica de forma natural el uso de MCC y F1 en lugar de accuracy, porque un modelo que siempre prediga la clase mayoritaria ya tendría 76 % de accuracy sin aprender nada.

### 4.4 Permite definir costos de error con sentido

El objetivo de negocio se traduce directo a decisiones de crédito u oferta de productos:

- Un falso positivo es ofrecer un producto a alguien que no tiene la capacidad de pago. Es el error más costoso.
- Un falso negativo es dejar pasar a un cliente valioso. Es un costo de oportunidad, menos grave.

Los costos son un supuesto del escenario, con una relación de referencia de 3 a 1 entre falso positivo y falso negativo.

### 4.5 Métricas esperadas razonables

Con este dataset, un gradient boosting o un random forest bien afinado suele alcanzar:

| Métrica | Meta |
|---|---|
| MCC | mayor o igual a 0.55 |
| Precisión de la clase mayor a 50K | mayor o igual a 0.75 |
| Recall de la clase mayor a 50K | mayor o igual a 0.60 |
| ROC-AUC | mayor o igual a 0.90 |

Estas metas son estimaciones basadas en el comportamiento habitual del dataset y se confirman al ejecutar el entrenamiento.

### 4.6 Se integra bien con el sistema completo

Es liviano y se carga fácilmente en una base de datos. Esto permite construir el flujo completo: tabla de datos, pipeline de entrenamiento, modelo versionado, API con endpoint POST, registro de predicciones, monitoreo y reentrenamiento.

### 4.7 Permite aplicar todas las fases de CRISP-ML(Q)

| Fase | Cómo se aplica con este dataset |
|---|---|
| Entendimiento del negocio y de los datos | Objetivo cuantificable, costos de error y exploración de variables |
| Preparación de datos | Limpieza de valores faltantes, codificación y selección de variables |
| Modelado | Comparación de modelos lineales, random forest y boosting |
| Evaluación y aseguramiento de calidad | MCC, matriz de confusión y análisis de sesgo por sexo y raza |
| Despliegue | API con POST conectada a la base de datos |
| Monitoreo y mantenimiento | Detección de drift y reentrenamiento cuando el MCC baje del umbral |

### 4.8 Es distinto al ejemplo de clase

No es el dataset de cáncer de mama que se mostró en el ejemplo del docente, por lo que el trabajo es propio y diferenciado.

## 5. Limitaciones que reconozco

Dejo explícitas las limitaciones para que no queden como puntos ciegos:

1. **El escenario es una simulación.** Los datos son de un censo de Estados Unidos de 1994, no de una entidad financiera. El umbral de 50K se usa como proxy de capacidad de pago, no como medida de solvencia real.
2. **Los costos de error son supuestos.** La relación de 3 a 1 entre falso positivo y falso negativo es una decisión razonada del escenario, no un dato observado.
3. **Variables sensibles.** El dataset incluye sexo y raza. Se auditan en la fase de aseguramiento de calidad y se evalúa excluirlas de la decisión para evitar sesgo.
4. **Antigüedad de los datos.** Al ser de 1994, el dataset sirve para demostrar el monitoreo de drift, pero no representa la realidad actual.
5. **Metas de métricas estimadas.** Se validan solo al entrenar los modelos.

## 6. Conclusión

Elegí Adult Census Income porque cumple todos los requisitos técnicos de la tarea, es apto para aprendizaje supervisado, permite justificar la métrica y los costos de error de forma coherente y deja aplicar cada fase de CRISP-ML(Q), incluyendo el despliegue con base de datos y API. Reconozco que el escenario de negocio es una simulación y lo declaro desde el inicio, de modo que las decisiones del proyecto quedan justificadas y no dependen de supuestos ocultos.
