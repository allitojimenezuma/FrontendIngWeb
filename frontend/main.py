from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import httpx
import os
from typing import Optional, List
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="Kalendas Frontend")

# --- CONFIGURACIÓN ---

# Configuración de Sesiones (Cookies)
app.add_middleware(SessionMiddleware, secret_key="clave_super_secreta_kalendas")

# Client ID de Google (Asegúrate de que coincida con tu consola de Google Cloud)
GOOGLE_CLIENT_ID = "853773773260-c4a0jh7ii2bbql2cbb7mseb421vnor94.apps.googleusercontent.com"

# Archivos estáticos y Plantillas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# URL del Gateway
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://gateway:8000')

# --- HELPERS ---

def get_messages(request: Request):
    """Recupera mensajes flash de la URL para mostrar alertas."""
    msg = request.query_params.get("msg")
    cat = request.query_params.get("cat")
    if msg:
        return [(cat or "info", msg)]
    return []

def get_current_user(request: Request):
    """Obtiene el usuario actual de la sesión (cookie)."""
    return request.session.get("user")


# --- RUTAS DE AUTENTICACIÓN ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/auth/google")
async def auth_google(request: Request, token: str = Form(...)):
    try:
        # Verificar el token con Google
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        # Guardar datos del usuario en la sesión
        request.session["user"] = {
            "name": idinfo.get("name"),
            "email": idinfo.get("email"),
            "picture": idinfo.get("picture")
        }
        
        return RedirectResponse(url="/?msg=Sesión iniciada correctamente&cat=success", status_code=303)
    except ValueError:
        return RedirectResponse(url="/login?msg=Token inválido&cat=danger", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/?msg=Sesión cerrada&cat=info", status_code=303)


# --- RUTA PRINCIPAL (HOME) ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{GATEWAY_URL}/calendar/calendars/")
            calendars = response.json() if response.status_code == 200 else []
        except httpx.RequestError:
            calendars = []
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "calendars": calendars,
        "messages": get_messages(request),
        "user": get_current_user(request)
    })


# --- RUTAS DE CALENDARIOS (ORDEN IMPORTANTE) ---

# 1. CREAR CALENDARIO (Específica)
@app.get("/calendar/new", response_class=HTMLResponse)
async def create_calendar_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?msg=Debes iniciar sesión&cat=warning", status_code=303)

    return templates.TemplateResponse("forms.html", {
        "request": request, 
        "type": "calendar",
        "messages": get_messages(request),
        "user": user
    })

@app.post("/calendar/new")
async def create_calendar(
    request: Request,
    titulo: str = Form(...),
    organizador: str = Form(...),
    palabras_clave: str = Form(...),
    es_publico: Optional[str] = Form(None),
    idCalendarioPadre: Optional[str] = Form(None)
):
    if not get_current_user(request):
         return RedirectResponse("/login", status_code=303)

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
        except httpx.RequestError:
            return RedirectResponse(url=f"/calendar/new?msg=Error de conexión&cat=danger", status_code=303)


# 2. IMPORTAR CALENDARIO (¡IMPORTANTE! Antes que /{id})
@app.get("/calendar/import", response_class=HTMLResponse)
async def import_calendar_form(request: Request):
    """Muestra el formulario para importar calendarios."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?msg=Debes iniciar sesión&cat=warning", status_code=303)

    return templates.TemplateResponse("forms.html", {
        "request": request, 
        "type": "import",  # Tipo específico para la vista
        "messages": get_messages(request),
        "user": user
    })

@app.post("/calendar/import")
async def process_import_calendar(
    request: Request,
    url_ical: str = Form(..., alias="url"), # 'url' viene del name del input HTML
    titulo: str = Form(...)
):
    """Procesa la importación llamando al Gateway -> External Service."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Preparamos el payload para el External Service
    data = {
        "url": url_ical,
        "titulo_importado": titulo,
        "organizador": user.get("name", "Usuario Importador")
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Llamada al Gateway que redirige al External Service
            response = await client.post(f"{GATEWAY_URL}/external/import/ical", json=data)
            
            if response.status_code == 200:
                result = response.json()
                count = result.get('events_imported', 0)
                return RedirectResponse(
                    url=f"/?msg=Importación exitosa: {count} eventos creados&cat=success", 
                    status_code=303
                )
            else:
                # Si falla, mostramos el detalle del error
                error_detail = response.json().get('detail', response.text)
                return RedirectResponse(
                    url=f"/calendar/import?msg=Error: {error_detail}&cat=danger", 
                    status_code=303
                )
        except httpx.RequestError:
            return RedirectResponse(
                url=f"/calendar/import?msg=Error de conexión con el servicio de importación&cat=danger", 
                status_code=303
            )


# 3. DETALLE DE CALENDARIO (Dinámica /{id})
# Debe ir AL FINAL de las rutas /calendar/... para no "comerse" a /new o /import
@app.get("/calendar/{id}", response_class=HTMLResponse)
async def calendar_detail(id: str, request: Request):
    async with httpx.AsyncClient() as client:
        try:
            # Obtener calendario
            cal_res = await client.get(f"{GATEWAY_URL}/calendar/calendars/{id}")
            if cal_res.status_code != 200:
                return RedirectResponse(url="/?msg=Calendario no encontrado&cat=danger", status_code=303)
            calendar = cal_res.json()
            
            # Obtener eventos (y eventos de subcalendarios si aplica)
            events_res = await client.get(f"{GATEWAY_URL}/event/events/calendar/{id}")
            events = events_res.json() if events_res.status_code == 200 else []
            
            # Obtener subcalendarios
            sub_res = await client.get(f"{GATEWAY_URL}/calendar/calendars/{id}/subcalendars")
            subcalendars = sub_res.json() if sub_res.status_code == 200 else []
            
            return templates.TemplateResponse("calendar_detail.html", {
                "request": request,
                "calendar": calendar,
                "events": events,
                "subcalendars": subcalendars,
                "messages": get_messages(request),
                "user": get_current_user(request)
            })
        except httpx.RequestError:
            return RedirectResponse(url="/?msg=Error de conexión&cat=danger", status_code=303)

@app.post("/calendar/{id}/delete")
async def delete_calendar(id: str, request: Request):
    if not get_current_user(request): return RedirectResponse("/login", status_code=303)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{GATEWAY_URL}/calendar/calendars/{id}")
            if response.status_code == 204:
                return RedirectResponse(url="/?msg=Calendario eliminado&cat=success", status_code=303)
            else:
                return RedirectResponse(url=f"/calendar/{id}?msg=No se pudo eliminar&cat=danger", status_code=303)
        except httpx.RequestError:
            return RedirectResponse(url=f"/calendar/{id}?msg=Error de conexión&cat=danger", status_code=303)


# --- RUTAS DE EVENTOS ---

@app.get("/event/new/{calendar_id}", response_class=HTMLResponse)
async def create_event_form(calendar_id: str, request: Request):
    user = get_current_user(request)
    if not user: return RedirectResponse("/login?msg=Debes iniciar sesión&cat=warning", status_code=303)

    return templates.TemplateResponse("forms.html", {
        "request": request, 
        "type": "event", 
        "calendar_id": calendar_id,
        "messages": get_messages(request),
        "user": user
    })

@app.post("/event/new/{calendar_id}")
async def create_event(
    request: Request,
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
    if not get_current_user(request): return RedirectResponse("/login", status_code=303)

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
            event_res = await client.get(f"{GATEWAY_URL}/event/events/{id}")
            if event_res.status_code != 200:
                return RedirectResponse(url="/?msg=Evento no encontrado&cat=danger", status_code=303)
            event = event_res.json()
            
            comments_res = await client.get(f"{GATEWAY_URL}/comment/comments/", params={"idEvento": id})
            comments = comments_res.json() if comments_res.status_code == 200 else []
            
            return templates.TemplateResponse("event_detail.html", {
                "request": request,
                "event": event,
                "comments": comments,
                "messages": get_messages(request),
                "user": get_current_user(request)
            })
        except httpx.RequestError:
            return RedirectResponse(url="/?msg=Error de conexión&cat=danger", status_code=303)

@app.post("/event/{id}/comment")
async def add_comment(
    id: str, 
    request: Request,
    contenido: str = Form(...),
    notif_pref: str = Form("email")
):
    data = {
        "contenido": contenido,
        "idEvento": id,
        "idCalendario": None
    }
    enviar_email = (notif_pref != "app")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{GATEWAY_URL}/comment/comments/", 
                json=data,
                params={"enviar_email": enviar_email} 
            )
            
            if response.status_code == 201:
                return RedirectResponse(url=f"/event/{id}?msg=Comentario añadido&cat=success", status_code=303)
            else:
                return RedirectResponse(url=f"/event/{id}?msg=Error al comentar&cat=danger", status_code=303)
        except httpx.RequestError:
            return RedirectResponse(url=f"/event/{id}?msg=Error de conexión&cat=danger", status_code=303)


# --- OTRAS RUTAS ---

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: Optional[str] = None):
    results = {'calendars': [], 'events': []}
    if q:
        async with httpx.AsyncClient() as client:
            try:
                # Búsqueda paralela (secuencial en este caso por simplicidad)
                cal_res = await client.get(f"{GATEWAY_URL}/calendar/calendars/", params={'titulo': q})
                if cal_res.status_code == 200: results['calendars'] = cal_res.json()
                
                event_res = await client.get(f"{GATEWAY_URL}/event/events/", params={'titulo': q})
                if event_res.status_code == 200: results['events'] = event_res.json()
            except httpx.RequestError: pass 
            
    return templates.TemplateResponse("search.html", {
        "request": request,
        "results": results,
        "query": q,
        "messages": get_messages(request),
        "user": get_current_user(request)
    })

@app.get("/settings-mock", response_class=HTMLResponse)
async def settings_page(request: Request):
    if not get_current_user(request): return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("settings.html", {"request": request, "user": get_current_user(request)})

@app.get("/notifications-mock", response_class=HTMLResponse)
async def notifications_page(request: Request):
    if not get_current_user(request): return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("notifications.html", {"request": request, "user": get_current_user(request)})