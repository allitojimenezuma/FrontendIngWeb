from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import os
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Kalendas Frontend")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Gateway URL
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://gateway:8000')

# --- Helper for Flash Messages (Simple Cookie-based) ---
# In a real app, use a session middleware like starlette-session
def flash(request: Request, message: str, category: str = "info"):
    # This is a simplified way to pass messages to the next request via cookies or query params
    # For this practice, we will pass them in the redirect URL or context if possible.
    # Since standard Flash doesn't exist in FastAPI, we'll use a simple workaround:
    # We will append ?msg=...&cat=... to redirects and read them in templates.
    pass 

# Helper to get messages from query params
def get_messages(request: Request):
    msg = request.query_params.get("msg")
    cat = request.query_params.get("cat")
    if msg:
        return [(cat or "info", msg)]
    return []

# Inject messages into templates
@app.middleware("http")
async def add_messages_to_context(request: Request, call_next):
    response = await call_next(request)
    return response

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{GATEWAY_URL}/calendar/calendars/")
            calendars = response.json() if response.status_code == 200 else []
        except httpx.RequestError:
            calendars = []
            # In a real scenario, we'd handle the error better
    
    print(f"DEBUG: Calendars received: {calendars}")
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "calendars": calendars,
        "messages": get_messages(request)
    })

@app.get("/calendar/new", response_class=HTMLResponse)
async def create_calendar_form(request: Request):
    return templates.TemplateResponse("forms.html", {
        "request": request, 
        "type": "calendar",
        "messages": get_messages(request)
    })

@app.post("/calendar/new")
async def create_calendar(
    titulo: str = Form(...),
    organizador: str = Form(...),
    palabras_clave: str = Form(...),
    es_publico: Optional[str] = Form(None),
    idCalendarioPadre: Optional[str] = Form(None)
):
    data = {
        "titulo": titulo,
        "organizador": organizador,
        "palabras_clave": [k.strip() for k in palabras_clave.split(',')] if palabras_clave else [],
        "es_publico": es_publico == 'on',
        "idCalendarioPadre": idCalendarioPadre or None
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{GATEWAY_URL}/calendar/calendars/", json=data)
            if response.status_code == 201:
                return RedirectResponse(url="/?msg=Calendario creado&cat=success", status_code=303)
            else:
                return RedirectResponse(url=f"/calendar/new?msg=Error: {response.text}&cat=danger", status_code=303)
        except httpx.RequestError as e:
            return RedirectResponse(url=f"/calendar/new?msg=Error de conexión&cat=danger", status_code=303)

@app.get("/calendar/{id}", response_class=HTMLResponse)
async def calendar_detail(id: str, request: Request):
    async with httpx.AsyncClient() as client:
        try:
            # Get Calendar
            cal_res = await client.get(f"{GATEWAY_URL}/calendar/calendars/{id}")
            if cal_res.status_code != 200:
                return RedirectResponse(url="/?msg=Calendario no encontrado&cat=danger", status_code=303)
            calendar = cal_res.json()
            
            # Get Events
            events_res = await client.get(f"{GATEWAY_URL}/event/events/calendar/{id}")
            events = events_res.json() if events_res.status_code == 200 else []
            
            # Get Subcalendars
            sub_res = await client.get(f"{GATEWAY_URL}/calendar/calendars/{id}/subcalendars")
            subcalendars = sub_res.json() if sub_res.status_code == 200 else []
            
            return templates.TemplateResponse("calendar_detail.html", {
                "request": request,
                "calendar": calendar,
                "events": events,
                "subcalendars": subcalendars,
                "messages": get_messages(request)
            })
        except httpx.RequestError:
            return RedirectResponse(url="/?msg=Error de conexión&cat=danger", status_code=303)

@app.post("/calendar/{id}/delete")
async def delete_calendar(id: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{GATEWAY_URL}/calendar/calendars/{id}")
            if response.status_code == 204:
                return RedirectResponse(url="/?msg=Calendario eliminado&cat=success", status_code=303)
            else:
                return RedirectResponse(url=f"/calendar/{id}?msg=No se pudo eliminar&cat=danger", status_code=303)
        except httpx.RequestError:
            return RedirectResponse(url=f"/calendar/{id}?msg=Error de conexión&cat=danger", status_code=303)

@app.get("/event/new/{calendar_id}", response_class=HTMLResponse)
async def create_event_form(calendar_id: str, request: Request):
    return templates.TemplateResponse("forms.html", {
        "request": request, 
        "type": "event", 
        "calendar_id": calendar_id,
        "messages": get_messages(request)
    })

@app.post("/event/new/{calendar_id}")
async def create_event(
    calendar_id: str,
    titulo: str = Form(...),
    horaComienzo: str = Form(...),
    duracionMinutos: int = Form(...),
    lugar: str = Form(...),
    organizador: str = Form(...),
    imagenes: Optional[str] = Form(None),
    latitud: Optional[float] = Form(None),
    longitud: Optional[float] = Form(None)
):
    data = {
        "idCalendario": calendar_id,
        "titulo": titulo,
        "horaComienzo": horaComienzo,
        "duracionMinutos": duracionMinutos,
        "lugar": lugar,
        "organizador": organizador,
        "contenidoAdjunto": {
            "imagenes": [img.strip() for img in imagenes.split(',')] if imagenes else [],
            "mapa": {"latitud": latitud, "longitud": longitud} if latitud and longitud else None
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{GATEWAY_URL}/event/events/", json=data)
            if response.status_code == 201:
                return RedirectResponse(url=f"/calendar/{calendar_id}?msg=Evento creado&cat=success", status_code=303)
            else:
                return RedirectResponse(url=f"/event/new/{calendar_id}?msg=Error: {response.text}&cat=danger", status_code=303)
        except httpx.RequestError:
            return RedirectResponse(url=f"/event/new/{calendar_id}?msg=Error de conexión&cat=danger", status_code=303)

@app.get("/event/{id}", response_class=HTMLResponse)
async def event_detail(id: str, request: Request):
    async with httpx.AsyncClient() as client:
        try:
            # Get Event
            event_res = await client.get(f"{GATEWAY_URL}/event/events/{id}")
            if event_res.status_code != 200:
                return RedirectResponse(url="/?msg=Evento no encontrado&cat=danger", status_code=303)
            event = event_res.json()
            
            # Get Comments
            comments_res = await client.get(f"{GATEWAY_URL}/comment/comments/", params={"idEvento": id})
            comments = comments_res.json() if comments_res.status_code == 200 else []
            
            return templates.TemplateResponse("event_detail.html", {
                "request": request,
                "event": event,
                "comments": comments,
                "messages": get_messages(request)
            })
        except httpx.RequestError:
            return RedirectResponse(url="/?msg=Error de conexión&cat=danger", status_code=303)

@app.post("/event/{id}/comment")
async def add_comment(id: str, contenido: str = Form(...)):
    data = {
        "contenido": contenido,
        "idEvento": id,
        "idCalendario": None
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{GATEWAY_URL}/comment/comments/", json=data)
            if response.status_code == 201:
                return RedirectResponse(url=f"/event/{id}?msg=Comentario añadido&cat=success", status_code=303)
            else:
                return RedirectResponse(url=f"/event/{id}?msg=Error al comentar&cat=danger", status_code=303)
        except httpx.RequestError:
            return RedirectResponse(url=f"/event/{id}?msg=Error de conexión&cat=danger", status_code=303)

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: Optional[str] = None):
    results = {'calendars': [], 'events': []}
    
    if q:
        async with httpx.AsyncClient() as client:
            try:
                # Search calendars
                cal_res = await client.get(f"{GATEWAY_URL}/calendar/calendars/", params={'titulo': q})
                if cal_res.status_code == 200:
                    results['calendars'] = cal_res.json()
                    
                # Search events
                event_res = await client.get(f"{GATEWAY_URL}/event/events/", params={'titulo': q})
                if event_res.status_code == 200:
                    results['events'] = event_res.json()
            except httpx.RequestError:
                pass # Handle error gracefully in UI
            
    return templates.TemplateResponse("search.html", {
        "request": request,
        "results": results,
        "query": q,
        "messages": get_messages(request)
    })
