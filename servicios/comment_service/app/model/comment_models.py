from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID 

# Modelo BASE
class CommentBase(BaseModel):
    contenido: str = Field(..., min_length=1, max_length=1000, json_schema_extra={"example": "Excelente evento, muy recomendable"})
    id_calendario: Optional[UUID] = Field(default=None, alias="idCalendario", json_schema_extra={"example": None})
    id_evento: Optional[UUID] = Field(default=None, alias="idEvento", json_schema_extra={"example": "a47ac10b-58cc-4372-a567-0e02b2c3d470"})
    fecha_creacion: datetime = Field(default_factory=datetime.now, alias="fechaCreacion")

# Modelo para CREAR un comentario
class CommentCreate(CommentBase):
    pass

# Modelo para RESPUESTA (lo que devolvemos desde la API)
class CommentInDB(CommentBase):
    id: UUID = Field(..., alias="_id")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda dt: dt.isoformat()},
        json_schema_extra={
            "example": {
                "id": "c47ac10b-58cc-4372-a567-0e02b2c3d481",
                "contenido": "Excelente evento, muy recomendable",
                "id_calendario": None,
                "id_evento": "a47ac10b-58cc-4372-a567-0e02b2c3d470",
                "fecha_creacion": "2025-11-04T10:30:00"
            }
        }
    )
    