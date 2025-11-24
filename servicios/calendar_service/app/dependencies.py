from app.service.calendarService import CalendarService
from app.crud.calendar_crud import CalendarCRUD

# Instanciación estática del CRUD (si no requiere sesión/estado)
# Si CalendarCRUD requiriera una sesión de BD, esto usaría 'yield' y el patrón Context Manager
CALENDAR_CRUD_INSTANCE = CalendarCRUD()

def get_calendar_crud() -> CalendarCRUD:
    """Provee la instancia del CRUD (útil para otros servicios o tests)."""
    return CALENDAR_CRUD_INSTANCE

def get_calendar_service() -> CalendarService:
    """Provee la instancia del CalendarService, inyectándole el CRUD."""
    return CalendarService(crud_repository=CALENDAR_CRUD_INSTANCE)