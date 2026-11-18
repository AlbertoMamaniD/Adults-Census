from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from app.database.connection import Base, engine

# Usar JSONB si el motor es PostgreSQL, sino JSON generico
JsonType = JSONB if engine.dialect.name == "postgresql" else JSON


class ModelRun(Base):
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    model_version = Column(String(40), unique=True, nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    trained_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    threshold = Column(Float, nullable=False)
    metrics = Column(JsonType, nullable=False)
    parameters = Column(JsonType, nullable=False, default=dict)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    model_version = Column(String(40), ForeignKey("model_runs.model_version", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False, index=True)
    input_data = Column(JsonType, nullable=False)
    predicted_class = Column(String(10), nullable=False)
    probability = Column(Float, nullable=False)
    latency_ms = Column(Float, nullable=False)


class TrainingDataset(Base):
    __tablename__ = "training_datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    row_count = Column(Integer, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)
    status = Column(String(50), default="uploaded", nullable=False)
    notes = Column(Text, nullable=True)
