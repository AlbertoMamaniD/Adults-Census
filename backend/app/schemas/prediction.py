from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PredictionInput(BaseModel):
    age: int = Field(..., ge=17, le=100, description="Edad del solicitante (años, rango 17-100)", examples=[39])
    workclass: str = Field(..., min_length=1, max_length=100, description="Sector laboral o tipo de empleo", examples=["State-gov"])
    education_num: int = Field(..., ge=1, le=16, description="Años de educación formal completados (1-16)", examples=[13])
    marital_status: str = Field(..., min_length=1, max_length=100, description="Estado civil", examples=["Never-married"])
    occupation: str = Field(..., min_length=1, max_length=100, description="Ocupación o cargo desempeñado", examples=["Adm-clerical"])
    relationship: str = Field(..., min_length=1, max_length=100, description="Rol en el núcleo familiar", examples=["Not-in-family"])
    race: str = Field(..., min_length=1, max_length=100, description="Grupo étnico reportado", examples=["White"])
    sex: str = Field(..., min_length=1, max_length=50, description="Sexo biológico", examples=["Male"])
    capital_gain: float = Field(default=0.0, ge=0.0, le=1000000.0, description="Ganancias de capital anuales ($ USD)", examples=[2174.0])
    capital_loss: float = Field(default=0.0, ge=0.0, le=1000000.0, description="Pérdidas de capital anuales ($ USD)", examples=[0.0])
    hours_per_week: int = Field(..., ge=1, le=100, description="Horas promedio trabajadas por semana (1-100)", examples=[40])
    native_country: str = Field(..., min_length=1, max_length=100, description="País de origen", examples=["United-States"])

    @field_validator("workclass", "marital_status", "occupation", "relationship", "race", "sex", "native_country", mode="before")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        if isinstance(v, str):
            clean = v.strip()
            if not clean:
                raise ValueError("El campo de texto no puede estar vacío ni contener solo espacios.")
            return clean
        return v

    def to_inference_dict(self) -> dict:
        """Convierte los atributos validados en diccionario con los tipos esperados por el pipeline."""
        return {
            "age": int(self.age),
            "workclass": str(self.workclass).strip(),
            "education_num": int(self.education_num),
            "marital_status": str(self.marital_status).strip(),
            "occupation": str(self.occupation).strip(),
            "relationship": str(self.relationship).strip(),
            "race": str(self.race).strip(),
            "sex": str(self.sex).strip(),
            "capital_gain": float(self.capital_gain),
            "capital_loss": float(self.capital_loss),
            "hours_per_week": int(self.hours_per_week),
            "native_country": str(self.native_country).strip(),
        }


class PredictionResponse(BaseModel):
    predicted_class: str = Field(..., description="Clase predicha ('>50K' o '<=50K')", examples=["<=50K"])
    probability: float = Field(..., description="Probabilidad estimada de la clase positiva '>50K'", examples=[0.1824])
    threshold_applied: float = Field(..., description="Umbral de decisión calibrado aplicado", examples=[0.77])
    latency_ms: float = Field(..., description="Latencia de inferencia en milisegundos", examples=[12.4])
    model_version: str = Field(..., description="Identificador inmutable de la versión del modelo", examples=["v20261117002816"])
    recommendation: str = Field(..., description="Recomendación comercial y de riesgo crediticio", examples=["No califica para producto de crédito de alto monto."])
    prediction_id: Optional[int] = Field(default=None, description="Identificador único del registro auditado en base de datos")
