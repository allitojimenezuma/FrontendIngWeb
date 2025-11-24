from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import httpx
from fastapi import HTTPException, status

# Importaciones de tu proyecto
from ..model.event_model import EventCreate, EventInDB
from ..crud.event_crud import EventCRUD # Usamos el CRUD inyectado

CALENDAR_SERVICE_URL = "http://calendar_service:8000"

class EventService:
    """
    Capa de Servicio para Eventos. Maneja la lógica de negocio.
    """
    def __init__(self, crud_repository: EventCRUD):
        """Inyección de Dependencia del CRUD/Repository."""
        self.crud = crud_repository

    
    async def create_event(self, event: EventCreate) -> EventInDB:
        """
        Lógica: Asigna el ID (UUID) y llama al CRUD para la inserción.
        """
        event_dict = event.model_dump(by_alias=True)
        event_dict["_id"] = uuid4() 
        
        # Aquí se podría poner lógica de negocio avanzada (ej. notificaciones, validaciones cruzadas)
        
        return await self.crud.create(event_dict)


    async def get_event_by_id(self, event_id: UUID) -> Optional[EventInDB]:
        """Obtiene un evento por ID."""
        return await self.crud.get_by_id(event_id)


    async def list_events(
        self,
        fecha_inicio: Optional[datetime],
        fecha_fin: Optional[datetime],
        lugar: Optional[str],
        organizador: Optional[str],
        titulo: Optional[str],
        duration_minima: Optional[int],
        duration_maxima: Optional[int],
    ) -> List[EventInDB]:
        """
        Lógica: Construye el filtro de MongoDB con los parámetros de la API.
        """
        filtro = {}
        
        # Lógica de construcción de filtros (es lógica de consulta, va en el Service)
        if fecha_inicio or fecha_fin:
            filtro["horaComienzo"] = {}
            if fecha_inicio:
                filtro["horaComienzo"]["$gte"] = fecha_inicio
            if fecha_fin:
                filtro["horaComienzo"]["$lte"] = fecha_fin
        
        if lugar:
            filtro["lugar"] = {"$regex": lugar, "$options": "i"}
        if organizador:
            filtro["organizador"] = {"$regex": organizador, "$options": "i"}
        if titulo:
            filtro["titulo"] = {"$regex": titulo, "$options": "i"}
        
        if duration_minima or duration_maxima:
            filtro["duracionMinutos"] = {}
            if duration_minima:
                filtro["duracionMinutos"]["$gte"] = duration_minima
            if duration_maxima:
                filtro["duracionMinutos"]["$lte"] = duration_maxima

        return await self.crud.list_by_filter(filtro)


    async def update_event(self, event_id: UUID, event_update: EventCreate) -> Optional[EventInDB]:
        """Actualiza un evento."""
        update_data = event_update.model_dump(by_alias=True, exclude_unset=True)
        return await self.crud.update(event_id, update_data)


    async def delete_event(self, event_id: UUID) -> bool:
        """Elimina un evento y devuelve si la operación fue exitosa."""
        deleted_count = await self.crud.delete(event_id)
        return deleted_count > 0
    
    async def get_events_by_calendar_and_subcalendars(self, calendar_id: UUID) -> List[EventInDB]:
        """
        Llama al microservicio de calendarios para obtener los subcalendarios
        y devuelve los eventos que pertenecen tanto al calendario padre como
        a sus subcalendarios.
        """
        # Llamada al microservicio de calendarios
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{CALENDAR_SERVICE_URL}/calendars/{calendar_id}/subcalendars")

                if response.status_code == 404:
                    subcalendars = []  # El calendario no tiene subcalendarios
                else:
                    response.raise_for_status()
                    subcalendars = response.json()

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo conectar al servicio de calendarios: {str(e)}"
            )
 
        # Extraer los IDs de los subcalendarios
        subcalendar_ids = [UUID(sub["_id"]) for sub in subcalendars]
        all_calendar_ids = [calendar_id] + subcalendar_ids

        # Buscar los eventos de todos esos calendarios
        filtro = {"idCalendario": {"$in": all_calendar_ids}}
        events = await self.crud.list_by_filter(filtro)

        return events