from fastapi import APIRouter, Body, Response, status, HTTPException, Query, Depends, File, UploadFile, Form
from typing import List, Annotated, Optional
from uuid import UUID
from datetime import datetime
import cloudinary.uploader

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

# 1. POST /events : Crear un nuevo evento con imágenes
@router.post(
    "/",
    response_model=EventInDB,
    status_code=status.HTTP_201_CREATED,
    response_description="Añadir nuevo evento",
)
async def create_event(
    event_service: EventServiceDep ,
    idCalendario: str = Form(...),
    titulo: str = Form(...),
    horaComienzo: str = Form(...),
    duracionMinutos: int = Form(...),
    lugar: str = Form(...),
    organizador: str = Form(...),
    latitud: Optional[float] = Form(None),
    longitud: Optional[float] = Form(None),
    imagenes: List[UploadFile] = File(default=[]),
):
    """
    Crea un nuevo evento con imágenes subidas desde archivos.
    """
    # Subir imágenes a Cloudinary
    imagen_urls = []
    if imagenes:
        for imagen in imagenes[:3]:  # Máximo 3 imágenes
            try:
                result = cloudinary.uploader.upload(
                    imagen.file,
                    folder="kalendas/events",
                    resource_type="image"
                )
                imagen_urls.append(result['secure_url'])
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error al subir imagen: {str(e)}"
                )
    
    # Construir contenido adjunto
    contenido_adjunto = {
        "imagenes": imagen_urls,
        "archivos": []
    }
    
    if latitud is not None and longitud is not None:
        contenido_adjunto["mapa"] = {
            "latitud": latitud,
            "longitud": longitud
        }
    
    # Crear evento
    event_data = {
        "idCalendario": idCalendario,
        "titulo": titulo,
        "horaComienzo": horaComienzo,
        "duracionMinutos": duracionMinutos,
        "lugar": lugar,
        "organizador": organizador,
        "contenidoAdjunto": contenido_adjunto
    }
    
    event_create = EventCreate(**event_data)
    return await event_service.create_event(event_create)


# 2. GET /events : Obtener una lista de todos los eventos (con filtros opcionales)
@router.get(
    "/",
    response_model=List[EventInDB],
    response_description="Listar todos los eventos con filtros opcionales",
)
async def list_events(
    event_service: EventServiceDep,
    fecha_inicio: Optional[datetime] = Query(None, description="Fecha de inicio del rango"),
    fecha_fin: Optional[datetime] = Query(None, description="Fecha de fin del rango"),
    lugar: Optional[str] = Query(None, description="Filtrar por lugar"),
    organizador: Optional[str] = Query(None, description="Filtrar por organizador"),
    titulo: Optional[str] = Query(None, description="Filtrar por título"),
    duration_minima: Optional[int] = Query(None, description="Filtrar por duración minima en minutos"),
    duration_maxima: Optional[int] = Query(None, description="Filtrar por duración maxima en minutos"),
):
    """
    Devuelve una lista de eventos filtrados.
    """
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
    event = await event_service.get_event_by_id(id)
    if event:
        return event
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evento con ID {id} no encontrado")


# 4. PUT /events/{id} : Actualizar un evento existente
@router.put(
    "/{id}",
    response_model=EventInDB,
    response_description="Actualizar un evento por su ID",
)
async def update_event(
    event_service: EventServiceDep,
    id: UUID,
    titulo: Optional[str] = Form(None),
    horaComienzo: Optional[str] = Form(None),
    duracionMinutos: Optional[int] = Form(None),
    lugar: Optional[str] = Form(None),
    organizador: Optional[str] = Form(None),
    latitud: Optional[float] = Form(None),
    longitud: Optional[float] = Form(None),
    imagenes: List[UploadFile] = File(default=[]),
):
    """
    Actualiza un evento existente.
    """
    update_data = {}
    
    if titulo:
        update_data["titulo"] = titulo
    if horaComienzo:
        update_data["horaComienzo"] = horaComienzo
    if duracionMinutos:
        update_data["duracionMinutos"] = duracionMinutos
    if lugar:
        update_data["lugar"] = lugar
    if organizador:
        update_data["organizador"] = organizador
    
    # Subir nuevas imágenes si se proporcionan
    if imagenes:
        imagen_urls = []
        for imagen in imagenes[:3]:
            try:
                result = cloudinary.uploader.upload(
                    imagen.file,
                    folder="kalendas/events",
                    resource_type="image"
                )
                imagen_urls.append(result['secure_url'])
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error al subir imagen: {str(e)}"
                )
        update_data["contenidoAdjunto.imagenes"] = imagen_urls
    
    if latitud is not None and longitud is not None:
        update_data["contenidoAdjunto.mapa"] = {
            "latitud": latitud,
            "longitud": longitud
        }
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionaron campos para actualizar"
        )
    
    # Necesitas adaptar tu servicio para aceptar dict en lugar de EventCreate
    updated_event = await event_service.update_event_dict(id, update_data)
    
    if updated_event:
        return updated_event
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evento con ID {id} no encontrado")


# 5. DELETE /events/{id} : Eliminar un evento
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Eliminar un evento por su ID",
)
async def delete_event(id: UUID, event_service: EventServiceDep):
    """
    Elimina un evento por su ID.
    """
    was_deleted = await event_service.delete_event(id)

    if not was_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evento con ID {id} no encontrado")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# 6. GET /events/calendar/{calendar_id} : Obtener eventos de un calendario
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