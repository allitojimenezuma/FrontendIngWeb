from typing import List, Optional
from uuid import UUID
from pymongo import ReturnDocument

# Importaciones de tu proyecto
from .. import database
from ..model.calendar_models import CalendarCreate, CalendarInDB 

# Alias para la colección de MongoDB (simplifica el código)
CalendarCollection = database.calendarios_collection 

class CalendarCRUD:
    """
    Capa de Acceso a Datos (Repository) para Calendarios (MongoDB).
    Toda la sintaxis de PyMongo se encapsula aquí.
    """

    async def create(self, calendar_data: dict) -> CalendarInDB:
        """Inserta el diccionario de calendario en la BD y lo recupera."""
        new_calendar = CalendarCollection.insert_one(calendar_data)
        created_calendar = CalendarCollection.find_one({"_id": new_calendar.inserted_id})
        return CalendarInDB.model_validate(created_calendar)  # Convierte el dict de Mongo a Pydantic


    async def get_by_id(self, calendar_id: UUID) -> Optional[CalendarInDB]:
        """Busca un calendario por ID."""
        calendar_data = CalendarCollection.find_one({"_id": calendar_id})
        if calendar_data:
            return CalendarInDB.model_validate(calendar_data)
        return None

    
    async def list_by_filter(self, filters: dict) -> List[CalendarInDB]:
        """Devuelve una lista de calendarios aplicando el filtro de MongoDB."""
        cursor = CalendarCollection.find(filters)
        calendar_list = list(cursor)
        return [CalendarInDB.model_validate(calendar) for calendar in calendar_list]


    async def update(self, calendar_id: UUID, update_data: dict) -> Optional[CalendarInDB]:
        """Actualiza y devuelve el documento actualizado."""
        updated_data = CalendarCollection.find_one_and_update(
            {"_id": calendar_id},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )
        if updated_data:
            return CalendarInDB.model_validate(updated_data)
        return None


    async def delete(self, calendar_id: UUID) -> int:
        """Elimina un calendario y devuelve el número de documentos eliminados (0 o 1)."""
        delete_result = CalendarCollection.delete_one({"_id": calendar_id})
        return delete_result.deleted_count
    

    async def get_subcalendars(self, parent_id: UUID) -> List[CalendarInDB]:
        """Devuelve los subcalendarios que tienen como padre el ID indicado."""
        filtro = {"idCalendarioPadre": parent_id}
        cursor = CalendarCollection.find(filtro)
        calendar_list = list(cursor)
        return [CalendarInDB.model_validate(calendar) for calendar in calendar_list]


