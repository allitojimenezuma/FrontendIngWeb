from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID 

# Modelo BASE
class CalendarBase(BaseModel):
    titulo: str = Field(..., min_length=3, json_schema_extra={"example": "Eventos Culturales de la Ciudad"})
    organizador: str = Field(..., json_schema_extra={"example": "Ayuntamiento Central"})
    palabras_clave: List[str] = Field(default=[], json_schema_extra={"example": ["cultura", "ciudad"]})
    es_publico: bool = True
    id_calendario_padre: Optional[UUID] = Field(default=None, alias="idCalendarioPadre")

# Modelo para CREAR un calendario
class CalendarCreate(CalendarBase):
    pass

# Modelo para RESPUESTA (lo que devolvemos desde la API)
class CalendarInDB(CalendarBase):
    id: UUID = Field(..., alias="_id")

    # Configuración para Pydantic v2
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479", 
                "titulo": "Eventos Culturales de la Ciudad",
                "organizador": "Ayuntamiento Central",
                "palabras_clave": ["cultura", "ciudad"],
                "es_publico": True,
                "id_calendario_padre": None
            }
        }
    )