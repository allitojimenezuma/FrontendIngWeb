from app.service.eventService import EventService
from app.crud.event_crud import EventCRUD
# Instanciación estática del CRUD (si no requiere sesión/estado)
# Si EventCRUD requiriera una sesión de BD, esto usaría 'yield' y el patrón Context Manager
EVENT_CRUD_INSTANCE = EventCRUD() 

def get_event_crud() -> EventCRUD:
    """Provee la instancia del CRUD (útil para otros servicios o tests)."""
    return EVENT_CRUD_INSTANCE

def get_event_service() -> EventService:
    """Provee la instancia del EventService, inyectándole el CRUD."""
    return EventService(crud_repository=EVENT_CRUD_INSTANCE)