from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, ConfigDict
import httpx
from icalendar import Calendar # type: ignore
import os
from datetime import datetime

app = FastAPI(title="External Calendar Adapter")

# URLs de tus otros microservicios
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
    Importa un calendario y muestra errores detallados si fallan los eventos.
    """
    # Header User-Agent para evitar bloqueo de Google
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    client = httpx.AsyncClient(follow_redirects=True, headers=headers)
    
    # 1. Descargar .ics
    try:
        response = await client.get(str(request.url))
        response.raise_for_status()
    except Exception as e:
        await client.aclose()
        print(f"❌ Error descargando ICS: {e}")
        raise HTTPException(status_code=400, detail=f"Error descargando URL externa: {str(e)}")

    # 2. Parsear
    try:
        cal_content = Calendar.from_ical(response.content)
    except Exception as e:
        await client.aclose()
        print(f"❌ Error parseando ICS: {e}")
        raise HTTPException(status_code=422, detail="El archivo no es un .ics válido")

    # 3. Crear Calendario Padre
    new_calendar_payload = {
        "titulo": request.titulo_importado,
        "organizador": request.organizador,
        "palabras_clave": ["importado", "externo"],
        "es_publico": True,
        "idCalendarioPadre": None
    }
    
    try:
        cal_response = await client.post(f"{CALENDAR_SERVICE_URL}/calendars/", json=new_calendar_payload)
        cal_response.raise_for_status() # Lanza error si falla
    except Exception as e:
        await client.aclose()
        print(f"❌ Error creando calendario contenedor: {cal_response.text}")
        raise HTTPException(status_code=500, detail=f"Error creando calendario interno: {cal_response.text}")
    
    calendar_data = cal_response.json()
    calendar_id = calendar_data["_id"]
    print(f"✅ Calendario creado: {calendar_id}")

    # 4. Procesar Eventos con Control de Errores
    imported_count = 0
    errors_count = 0
    
    for component in cal_content.walk():
        if component.name == "VEVENT":
            try:
                summary = str(component.get('summary', 'Sin título'))
                # Validación básica: Si no tiene título o es muy corto, EventService podría rechazarlo
                if len(summary) < 3: summary += " (Importado)"

                dtstart = component.get('dtstart').dt
                
                # Normalización de Fechas (datetime vs date)
                if not isinstance(dtstart, datetime):
                    dtstart = datetime.combine(dtstart, datetime.min.time())
                
                # Normalización de Timezone (MongoDB prefiere naive o UTC)
                if dtstart.tzinfo is not None:
                    dtstart = dtstart.replace(tzinfo=None)

                # Duración
                dtend = component.get('dtend')
                duration_min = 60
                if dtend:
                    dtend = dtend.dt
                    if not isinstance(dtend, datetime):
                        dtend = datetime.combine(dtend, datetime.min.time())
                    # Quitar timezone también en fin
                    if dtend.tzinfo is not None:
                        dtend = dtend.replace(tzinfo=None)
                        
                    duration_min = int((dtend - dtstart).total_seconds() / 60)
                
                if duration_min <= 0: duration_min = 30 # Evitar duraciones negativas/cero

                location = str(component.get('location', 'Remoto'))

                event_payload = {
                    "idCalendario": calendar_id,
                    "titulo": summary[:100], # Cortar si es muy largo
                    "horaComienzo": dtstart.isoformat(),
                    "duracionMinutos": duration_min,
                    "lugar": location[:100],
                    "organizador": request.organizador,
                    "contenidoAdjunto": {
                        "imagenes": [], "archivos": [], "mapa": None
                    }
                }

                # INSERTAR Y VERIFICAR RESPUESTA
                evt_resp = await client.post(f"{EVENT_SERVICE_URL}/events/", json=event_payload)
                
                if evt_resp.status_code == 201:
                    imported_count += 1
                else:
                    errors_count += 1
                    print(f"⚠️ Fallo al importar evento '{summary}': {evt_resp.status_code} - {evt_resp.text}")

            except Exception as e:
                errors_count += 1
                print(f"⚠️ Excepción procesando evento: {str(e)}")

    await client.aclose()
    
    return {
        "message": f"Proceso finalizado. Importados: {imported_count}. Fallidos: {errors_count}",
        "calendar_id": calendar_id,
        "events_imported": imported_count,
        "events_failed": errors_count
    }