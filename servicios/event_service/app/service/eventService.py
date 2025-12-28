from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import httpx
from fastapi import HTTPException, status
import os

# Importaciones de tu proyecto
from ..model.event_model import EventCreate, EventInDB
from ..crud.event_crud import EventCRUD

# URL del servicio de calendarios
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL", "http://calendar_service:8000")

class EventService:
    def __init__(self, crud_repository: EventCRUD):
        self.crud = crud_repository

    async def create_event(self, event: EventCreate) -> EventInDB:
        event_dict = event.model_dump(by_alias=True)
        event_dict["_id"] = uuid4() 
        return await self.crud.create(event_dict)

    async def get_event_by_id(self, event_id: UUID) -> Optional[EventInDB]:
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
        filtro = {}
        if fecha_inicio or fecha_fin:
            filtro["horaComienzo"] = {}
            if fecha_inicio: filtro["horaComienzo"]["$gte"] = fecha_inicio
            if fecha_fin: filtro["horaComienzo"]["$lte"] = fecha_fin
        
        if lugar: filtro["lugar"] = {"$regex": lugar, "$options": "i"}
        if organizador: filtro["organizador"] = {"$regex": organizador, "$options": "i"}
        if titulo: filtro["titulo"] = {"$regex": titulo, "$options": "i"}
        
        if duration_minima or duration_maxima:
            filtro["duracionMinutos"] = {}
            if duration_minima: filtro["duracionMinutos"]["$gte"] = duration_minima
            if duration_maxima: filtro["duracionMinutos"]["$lte"] = duration_maxima

        return await self.crud.list_by_filter(filtro)

    async def update_event(self, event_id: UUID, event_update: EventCreate) -> Optional[EventInDB]:
        update_data = event_update.model_dump(by_alias=True, exclude_unset=True)
        return await self.crud.update(event_id, update_data)

    async def delete_event(self, event_id: UUID) -> bool:
        deleted_count = await self.crud.delete(event_id)
        return deleted_count > 0
    
    async def get_events_by_calendar_and_subcalendars(self, calendar_id: UUID) -> List[EventInDB]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{CALENDAR_SERVICE_URL}/calendars/{calendar_id}/subcalendars")
                if response.status_code == 404:
                    subcalendars = []
                else:
                    response.raise_for_status()
                    subcalendars = response.json()
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo conectar al servicio de calendarios: {str(e)}"
            )
 
        subcalendar_ids = [UUID(sub["_id"]) for sub in subcalendars]
        all_calendar_ids = [calendar_id] + subcalendar_ids

        filtro = {"idCalendario": {"$in": all_calendar_ids}}
        events = await self.crud.list_by_filter(filtro)

        return events