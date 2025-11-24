from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime

# Importaciones de tu proyecto
from ..model.calendar_models import CalendarCreate, CalendarInDB
from ..crud.calendar_crud import CalendarCRUD  # Usamos el CRUD inyectado

class CalendarService:
    """
    Capa de Servicio para Calendarios. Maneja la lógica de negocio.
    """
    def __init__(self, crud_repository: CalendarCRUD):
        """Inyección de Dependencia del CRUD/Repository."""
        self.crud = crud_repository

    
    async def create_calendar(self, calendar: CalendarCreate) -> CalendarInDB:
        """
        Lógica: Asigna el ID (UUID) y llama al CRUD para la inserción.
        """
        calendar_dict = calendar.model_dump(by_alias=True)
        calendar_dict["_id"] = uuid4() 
        
        # Aquí se podría poner lógica de negocio avanzada (ej. validaciones, notificaciones)
        
        return await self.crud.create(calendar_dict)


    async def get_calendar_by_id(self, calendar_id: UUID) -> Optional[CalendarInDB]:
        """Obtiene un calendario por ID."""
        return await self.crud.get_by_id(calendar_id)


    async def list_calendars(
        self,
        titulo: Optional[str] = None,
        organizador: Optional[str] = None,
        palabras_clave: Optional[List[str]] = None,
        es_publico: Optional[bool] = None,
    ) -> List[CalendarInDB]:
        """
        Lógica: Construye el filtro de MongoDB con los parámetros de la API.
        """
        filtro = {}
        
        if titulo:
            filtro["titulo"] = {"$regex": titulo, "$options": "i"}
        if organizador:
            filtro["organizador"] = {"$regex": organizador, "$options": "i"}
        if palabras_clave:
            filtro["palabras_clave"] = {"$in": palabras_clave}
        if es_publico is not None:
            filtro["es_publico"] = es_publico

        return await self.crud.list_by_filter(filtro)


    async def update_calendar(self, calendar_id: UUID, calendar_update: CalendarCreate) -> Optional[CalendarInDB]:
        """Actualiza un calendario."""
        update_data = calendar_update.model_dump(by_alias=True, exclude_unset=True)
        return await self.crud.update(calendar_id, update_data)


    async def delete_calendar(self, calendar_id: UUID) -> bool:
        """Elimina un calendario y devuelve si la operación fue exitosa."""
        deleted_count = await self.crud.delete(calendar_id)
        return deleted_count > 0
    

    async def get_subcalendars(self, parent_id: UUID) -> List[CalendarInDB]:
        """Obtiene los subcalendarios de un calendario padre."""
        return await self.crud.get_subcalendars(parent_id)

    

