from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, HttpUrl, ConfigDict
import httpx
from icalendar import Calendar
import os
from datetime import datetime
from uuid import uuid4

app = FastAPI(title="External Calendar Adapter")

# URLs de tus otros microservicios (comunicación interna)
CALENDAR_SERVICE_URL = os.getenv("CALENDAR_SERVICE_URL", "http://calendar_service:8000")
EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event_service:8000")

class ImportRequest(BaseModel):
    url: HttpUrl
    titulo_importado: str
    organizador: str
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://www.officeholidays.com/ics/spain",
                "titulo_importado": "Festivos España 2025",
                "organizador": "OfficeHolidays"
            }
        }
    )

@app.post("/import/ical")
async def import_from_ical(request: ImportRequest):
    """
    Importa un calendario desde una URL .ics (Google, TeamUp, Outlook)
    """
    client = httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
    
    # 1. Descargar el archivo .ics externo
    try:
        response = await client.get(str(request.url))
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo acceder a la URL externa: {str(e)}")

    # 2. Parsear el contenido iCalendar
    try:
        cal_content = Calendar.from_ical(response.content)
    except Exception:
        raise HTTPException(status_code=422, detail="El archivo no es un formato de calendario válido (.ics)")

    # 3. Crear el Calendario en Kalendas (Llamada al Calendar Service)
    # Asumimos que es público por defecto al importarlo, o podrías pedirlo en el request
    new_calendar_payload = {
        "titulo": request.titulo_importado,
        "organizador": request.organizador,
        "palabras_clave": ["importado", "externo"],
        "es_publico": True,
        "idCalendarioPadre": None
    }
    
    cal_response = await client.post(f"{CALENDAR_SERVICE_URL}/calendars/", json=new_calendar_payload)
    if cal_response.status_code != 201:
        raise HTTPException(status_code=500, detail="Error creando el calendario contenedor interno")
    
    calendar_data = cal_response.json()
    calendar_id = calendar_data["_id"]

    # 4. Procesar Eventos e insertarlos (Llamada al Event Service)
    imported_count = 0
    
    for component in cal_content.walk():
        if component.name == "VEVENT":
            # Extraer datos básicos del estándar iCal
            summary = str(component.get('summary', 'Sin título'))
            dtstart = component.get('dtstart').dt
            
            # iCal a veces devuelve fecha sin hora (date), lo convertimos a datetime
            if not isinstance(dtstart, datetime):
                dtstart = datetime.combine(dtstart, datetime.min.time())

            # Calcular duración o usar default
            dtend = component.get('dtend')
            duration_min = 60
            if dtend:
                dtend = dtend.dt
                if not isinstance(dtend, datetime):
                    dtend = datetime.combine(dtend, datetime.min.time())
                duration_min = int((dtend - dtstart).total_seconds() / 60)

            location = str(component.get('location', 'Ubicación remota'))

            # Crear payload para Event Service
            event_payload = {
                "idCalendario": calendar_id,
                "titulo": summary,
                "horaComienzo": dtstart.isoformat(),
                "duracionMinutos": duration_min,
                "lugar": location,
                "organizador": request.organizador,
                "contenidoAdjunto": {
                    "imagenes": [], "archivos": [], "mapa": None
                }
            }

            # Insertar evento
            await client.post(f"{EVENT_SERVICE_URL}/events/", json=event_payload)
            imported_count += 1

    await client.aclose()
    
    return {
        "message": "Importación exitosa",
        "calendar_id": calendar_id,
        "events_imported": imported_count
    }