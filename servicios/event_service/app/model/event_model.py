from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from uuid import UUID 

class Mapa(BaseModel):
    latitud: float
    longitud: float

class ContenidoAdjunto(BaseModel):
    imagenes: List[str] = []
    archivos: List[str] = []
    mapa: Optional[Mapa] = None


# Modelo BASE
class EventBase(BaseModel):
    id_calendario: UUID = Field(..., alias="idCalendario")
    titulo: str = Field(..., min_length=3, example="Concierto de Verano")
    hora_comienzo: datetime = Field(..., alias="horaComienzo", example=datetime.now())
    duracion_minutos: int = Field(..., gt=0, example=120, alias="duracionMinutos")
    lugar: str = Field(..., example="Parque Central")
    organizador: str = Field(..., example="Concejalía de Cultura")
    email_organizador: str = Field(..., alias="emailOrganizador", example="usuario@gmail.com")
    contenido_adjunto: ContenidoAdjunto = Field(default_factory=ContenidoAdjunto, alias="contenidoAdjunto")

# Modelo para CREAR un evento
class EventCreate(EventBase):
    pass

# Modelo para RESPUESTA (lo que devolvemos desde la API)
class EventInDB(EventBase):
    id: UUID = Field(..., alias="_id")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda dt: dt.isoformat()}
    )