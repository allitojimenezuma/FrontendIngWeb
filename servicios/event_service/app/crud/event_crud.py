from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pymongo import ReturnDocument

# Importaciones de tu proyecto
from .. import database
from ..model.event_model import EventCreate, EventInDB 

# Alias para la colección de MongoDB (simplifica el código)
EventCollection = database.eventos_collection 

class EventCRUD:
    """
    Capa de Acceso a Datos (Repository) para Eventos (MongoDB).
    Toda la sintaxis de PyMongo se encapsula aquí.
    """

    async def create(self, event_data: dict) -> EventInDB:
        """Inserta el diccionario de evento en la BD y lo recupera."""
        new_event = EventCollection.insert_one(event_data)
        created_event = EventCollection.find_one({"_id": new_event.inserted_id})
        return EventInDB.model_validate(created_event) # Convierte el dict de Mongo a Pydantic


    async def get_by_id(self, event_id: UUID) -> Optional[EventInDB]:
        """Busca un evento por ID."""
        event_data = EventCollection.find_one({"_id": event_id})
        if event_data:
            return EventInDB.model_validate(event_data)
        return None

    
    async def list_by_filter(self, filters: dict) -> List[EventInDB]:
        """Devuelve una lista de eventos aplicando el filtro de MongoDB."""
        cursor = EventCollection.find(filters)
        event_list = list(cursor)
        return [EventInDB.model_validate(event) for event in event_list]


    async def update(self, event_id: UUID, update_data: dict) -> Optional[EventInDB]:
        """Actualiza y devuelve el documento actualizado."""
        updated_data = EventCollection.find_one_and_update(
            {"_id": event_id},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )
        if updated_data:
            return EventInDB.model_validate(updated_data)
        return None


    async def delete(self, event_id: UUID) -> int:
        """Elimina un evento y devuelve el número de documentos eliminados (0 o 1)."""
        delete_result = EventCollection.delete_one({"_id": event_id})
        return delete_result.deleted_count