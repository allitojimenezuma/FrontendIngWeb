from fastapi import APIRouter, Body, Response, status, HTTPException, Query, Depends
from typing import List, Annotated, Optional
from uuid import UUID

from ..service.calendarService import CalendarService 
from ..dependencies import get_calendar_service 
from ..model.calendar_models import CalendarCreate, CalendarInDB

router = APIRouter(
    prefix="/calendars",
    tags=["Calendarios"]
)

# Definición del tipo inyectado (Dependencia del Servicio)
CalendarServiceDep = Annotated[CalendarService, Depends(get_calendar_service)]

# --- Endpoints ---

# 1. POST /calendars : Crear un nuevo calendario
@router.post(
    "/",
    response_model=CalendarInDB,
    status_code=status.HTTP_201_CREATED,
    response_description="Añadir nuevo calendario",
)
async def create_calendar(
    calendar: Annotated[CalendarCreate, Body(
        examples=[{
            "titulo": "Actividades Deportivas UMA",
            "organizador": "Universidad de Málaga",
            "palabras_clave": ["deporte", "universidad"],
            "es_publico": True,
            "idCalendarioPadre": None,
        }]
    )],
    calendar_service: CalendarServiceDep  # 👈 Inyección del Service
):
    """
    Crea un nuevo calendario en la base de datos.
    """
    # Llama al Servicio y le pasa el modelo Pydantic validado.
    return await calendar_service.create_calendar(calendar)


# 2. GET /calendars : Obtener una lista de todos los calendarios (con filtros opcionales)
@router.get(
    "/",
    response_model=List[CalendarInDB],
    response_description="Listar todos los calendarios con filtros opcionales",
)
async def list_calendars(
    calendar_service: CalendarServiceDep,  # 👈 Inyección del Service
    titulo: Optional[str] = Query(None, description="Filtrar por título"),
    organizador: Optional[str] = Query(None, description="Filtrar por organizador"),
    palabras_clave: Optional[List[str]] = Query(None, description="Filtrar por palabras clave"),
    es_publico: Optional[bool] = Query(None, description="Filtrar por visibilidad pública"),
):
    """
    Devuelve una lista de calendarios filtrados. La lógica de construcción del filtro se delega al Servicio.
    """
    # Llama al Servicio con los parámetros de la Query.
    return await calendar_service.list_calendars(
        titulo=titulo,
        organizador=organizador,
        palabras_clave=palabras_clave,
        es_publico=es_publico
    )


# 3. GET /calendars/{id} : Obtener un calendario específico por su ID
@router.get(
    "/{id}",
    response_model=CalendarInDB,
    response_description="Obtener un calendario por su ID",
)
async def get_calendar(id: UUID, calendar_service: CalendarServiceDep):
    """
    Busca un calendario por su ID. Devuelve 404 si no lo encuentra.
    """
    calendar = await calendar_service.get_calendar_by_id(id)  # Llama al Servicio
    if calendar:
        return calendar

    # El manejo de errores de "No encontrado" (404) permanece en el router.
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Calendario con ID {id} no encontrado")


# 4. PUT /calendars/{id} : Actualizar un calendario existente
@router.put(
    "/{id}",
    response_model=CalendarInDB,
    response_description="Actualizar un calendario por su ID",
)
async def update_calendar(
    id: UUID, 
    calendar_update: Annotated[CalendarCreate, Body(...)],
    calendar_service: CalendarServiceDep
):
    """
    Actualiza un calendario existente. Devuelve 404 si no lo encuentra.
    """
    updated_calendar = await calendar_service.update_calendar(id, calendar_update)  # Llama al Servicio

    if updated_calendar:
        return updated_calendar
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se pudo actualizar, calendario con ID {id} no encontrado")


# 5. DELETE /calendars/{id} : Eliminar un calendario
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Eliminar un calendario por su ID",
)
async def delete_calendar(id: UUID, calendar_service: CalendarServiceDep):
    """
    Elimina un calendario por su ID. Devuelve 204 si tiene éxito o 404 si no lo encuentra.
    """
    was_deleted = await calendar_service.delete_calendar(id)  # Llama al Servicio

    if not was_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Calendario con ID {id} no encontrado")

    # Si fue eliminado, devuelve la respuesta de éxito sin contenido.
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# 6. GET /calendars/{id}/subcalendars : Obtener los subcalendarios de un calendario padre
@router.get(
    "/{id}/subcalendars",
    response_model=List[CalendarInDB],
    response_description="Listar los subcalendarios de un calendario padre",
)
async def get_subcalendars(
    id: UUID,
    calendar_service: CalendarServiceDep
):
    """
    Devuelve todos los subcalendarios cuyo campo id_calendario_padre coincide con el ID proporcionado.
    """
    subcalendars = await calendar_service.get_subcalendars(id) #Llama al Servicio

    if not subcalendars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Noo se encontraron subcalendarios para el calendario {id}")

    return subcalendars

