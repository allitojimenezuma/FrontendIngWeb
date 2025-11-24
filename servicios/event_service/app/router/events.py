from fastapi import APIRouter, Body, Response, status, HTTPException, Query, Depends
from typing import List, Annotated, Optional
from uuid import UUID
from datetime import datetime

from ..service.eventService import EventService 
from ..dependencies import get_event_service 
from ..model.event_model import EventCreate, EventInDB

router = APIRouter(
    prefix="/events",
    tags=["Eventos"]
)

# Definición del tipo inyectado (Dependencia del Servicio)
EventServiceDep = Annotated[EventService, Depends(get_event_service)]

# --- Endpoints ---

# 1. POST /events : Crear un nuevo evento
@router.post(
    "/",
    response_model=EventInDB,
    status_code=status.HTTP_201_CREATED,
    response_description="Añadir nuevo evento",
)
async def create_event(
    event: Annotated[EventCreate, Body(
        examples=[{
            "idCalendario": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "titulo": "Concierto de Verano",
            "horaComienzo": "2025-08-15T21:30:00",
            "duracionMinutos": 150,
            "lugar": "Parque de la Ciudad",
            "organizador": "Concejalía de Cultura",
            "contenidoAdjunto": {
                "imagenes": [
                    "https://ejemplo.com/concierto.jpg",
                    "https://ejemplo.com/cartel.jpg"
                ],
                "archivos": [
                    "https://ejemplo.com/programa.pdf"
                ],
                "mapa": {
                    "latitud": 36.7188,
                    "longitud": -4.4332
                }
            }
        }]
    )],
    event_service: EventServiceDep # 👈 Inyección del Service
):
    """
    Crea un nuevo evento en la base de datos.
    """
    # Llama al Servicio y le pasa el modelo Pydantic validado.
    return await event_service.create_event(event) 


# 2. GET /events : Obtener una lista de todos los eventos (con filtros opcionales)
@router.get(
    "/",
    response_model=List[EventInDB],
    response_description="Listar todos los eventos con filtros opcionales",
)
async def list_events(
    event_service: EventServiceDep, # 👈 Inyección del Service
    fecha_inicio: Optional[datetime] = Query(
        None, 
        description="Fecha de inicio del rango (formato ISO: YYYY-MM-DDTHH:MM:SS)",
        example="2025-01-01T00:00:00"
    ),
    fecha_fin: Optional[datetime] = Query(
        None, 
        description="Fecha de fin del rango (formato ISO: YYYY-MM-DDTHH:MM:SS)",
        example="2025-12-31T23:59:59"
    ),
    lugar: Optional[str] = Query(None, description="Filtrar por lugar"),
    organizador: Optional[str] = Query(None, description="Filtrar por organizador"),
    titulo: Optional[str] = Query(None, description="Filtrar por título"),
    duration_minima: Optional[int] = Query(None, description="Filtrar por duración minima en minutos"),
    duration_maxima: Optional[int] = Query(None, description="Filtrar por duración maxima en minutos"),
):
    """
    Devuelve una lista de eventos filtrados. La lógica de construcción del filtro se delega al Servicio.
    """
    # Llama al Servicio con los parámetros de la Query.
    return await event_service.list_events(
        fecha_inicio, fecha_fin, lugar, organizador, titulo, duration_minima, duration_maxima
    )


# 3. GET /events/{id} : Obtener un evento específico por su ID
@router.get(
    "/{id}",
    response_model=EventInDB,
    response_description="Obtener un evento por su ID",
)
async def get_event(id: UUID, event_service: EventServiceDep):
    """
    Busca un evento por su ID. Devuelve 404 si no lo encuentra.
    """
    event = await event_service.get_event_by_id(id) # Llama al Servicio
    if event:
        return event

    # El manejo de errores de "No encontrado" (404) permanece en el router.
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evento con ID {id} no encontrado")


# 4. PUT /events/{id} : Actualizar un evento existente
@router.put(
    "/{id}",
    response_model=EventInDB,
    response_description="Actualizar un evento por su ID",
)
async def update_event(
    id: UUID, 
    event_update: Annotated[EventCreate, Body(...)],
    event_service: EventServiceDep
):
    """
    Actualiza un evento existente. Devuelve 404 si no lo encuentra.
    """
    updated_event = await event_service.update_event(id, event_update) # Llama al Servicio

    if updated_event:
        return updated_event
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se pudo actualizar, evento con ID {id} no encontrado")


# 5. DELETE /events/{id} : Eliminar un evento
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Eliminar un evento por su ID",
)
async def delete_event(id: UUID, event_service: EventServiceDep):
    """
    Elimina un evento por su ID. Devuelve 204 si tiene éxito o 404 si no lo encuentra.
    """
    was_deleted = await event_service.delete_event(id) # Llama al Servicio (solo devuelve True/False)

    if not was_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evento con ID {id} no encontrado")

    # Si fue eliminado, devuelve la respuesta de éxito sin contenido.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# 6. GET /events/calendar/{calendar_id} : Obtener eventos de un calendario y sus subcalendarios
@router.get(
    "/calendar/{calendar_id}",
    response_model=List[EventInDB],
    response_description="Listar los eventos de un calendario y de sus subcalendarios",
)
async def get_events_from_calendar(
    calendar_id: UUID,
    event_service: EventServiceDep
):
    """
    Devuelve todos los eventos del calendario indicado y de sus subcalendarios.
    """
    events = await event_service.get_events_by_calendar_and_subcalendars(calendar_id)
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron eventos para el calendario {calendar_id}",
        )
    return events

