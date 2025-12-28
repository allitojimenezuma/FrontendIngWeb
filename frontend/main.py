from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from google.oauth2 import id_token # type: ignore
from google.auth.transport import requests as google_requests # type: ignore
import httpx
import os
from typing import Optional, List
from dotenv import load_dotenv
import unicodedata
import jwt
from datetime import datetime, timedelta

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="Kalendas Frontend")

# --- CONFIGURACIÓN ---

# Configuración de Sesiones (Cookies)
app.add_middleware(SessionMiddleware, secret_key="clave_super_secreta_kalendas")

# Client ID de Google
GOOGLE_CLIENT_ID = "853773773260-c4a0jh7ii2bbql2cbb7mseb421vnor94.apps.googleusercontent.com"

# Clave secreta para firmar tokens JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "clave_super_secreta_jwt_kalendas_2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Lista de emails de administradores
ADMIN_EMAILS = [
    "pruebaparaingweb@gmail.com",
    "guillesanznieto@gmail.com",
    # Puedes añadir más administradores aquí
]

# Archivos estáticos y Plantillas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# URL del Gateway
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://gateway:8000')

# --- HELPERS ---

def get_frontend_headers() -> dict:
    """
    Retorna headers especiales que identifican peticiones del frontend.
    Esto permite al gateway distinguir entre:
    - Peticiones del frontend web (autenticado con cookies)
    - Peticiones directas a la API REST (requieren JWT)
    """
    return {
        "X-Frontend-Request": "true",
        "X-Service-Name": "kalendas-frontend"
    }

def create_jwt_token(user_data: dict) -> str:
    """Crea un token JWT con los datos del usuario."""
    payload = {
        "email": user_data.get("email"),
        "name": user_data.get("name"),
        "role": user_data.get("role"),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token

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

def is_admin(request: Request) -> bool:
    """Verifica si el usuario actual es administrador."""
    user = get_current_user(request)
    if user and user.get("email") in ADMIN_EMAILS:
        return True
    return False

def require_admin(request: Request):
    """Verifica que el usuario sea administrador. Redirige si no lo es."""
    if not is_admin(request):
        return False
    return True


# --- RUTAS DE AUTENTICACIÓN ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/auth/google")
async def auth_google(request: Request, token: str = Form(...)):
    try:
        # --- CORRECCIÓN AQUÍ: Añadimos clock_skew_in_seconds=10 ---
        # Esto le dice a la librería: "Si la hora varía por menos de 10 segundos, acéptalo".
        # Soluciona el error "Token used too early" típico de Docker en Mac/Windows.
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10 
        )
        
        email = idinfo.get("email")
        
        # Determinar el rol del usuario
        role = "admin" if email in ADMIN_EMAILS else "user"
        
        # Guardar datos del usuario en la sesión
        user_data = {
            "name": idinfo.get("name"),
            "email": email,
            "picture": idinfo.get("picture"),
            "role": role 
        }
        request.session["user"] = user_data
        
        # Generar y guardar el token JWT en la sesión
        jwt_token = create_jwt_token(user_data)
        request.session["jwt_token"] = jwt_token
        
        return RedirectResponse(url="/?msg=Sesión iniciada correctamente&cat=success", status_code=303)
    except ValueError as e:
        print(f"❌ Error Login (Detalle): {e}") # Debug para ver si sigue fallando
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
            response = await client.get(
                f"{GATEWAY_URL}/calendar/calendars/",
                headers=get_frontend_headers()
            )
            calendars = response.json() if response.status_code == 200 else []
        except httpx.RequestError:
            calendars = []
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "calendars": calendars,
        "messages": get_messages(request),
        "user": get_current_user(request),
        "is_admin": is_admin(request)  # Pasar info de admin a la plantilla
    })


# --- RUTAS DE CALENDARIOS ---

# 1. CREAR CALENDARIO
@app.get("/calendar/new", response_class=HTMLResponse)
async def create_calendar_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?msg=Debes iniciar sesión&cat=warning", status_code=303)

    return templates.TemplateResponse("forms.html", {
        "request": request, 
        "type": "calendar",
        "messages": get_messages(request),
        "user": user,
        "is_admin": is_admin(request)
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
            response = await client.post(
                f"{GATEWAY_URL}/calendar/calendars/",
                json=data,
                headers=get_frontend_headers()
            )
            if response.status_code == 201:
                return RedirectResponse(url="/?msg=Calendario creado&cat=success", status_code=303)
            else:
                return RedirectResponse(url=f"/calendar/new?msg=Error: {response.text}&cat=danger", status_code=303)
        except httpx.RequestError:
            return RedirectResponse(url=f"/calendar/new?msg=Error de conexión&cat=danger", status_code=303)


# 2. IMPORTAR CALENDARIO
@app.get("/calendar/import", response_class=HTMLResponse)
async def import_calendar_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?msg=Debes iniciar sesión&cat=warning", status_code=303)

    return templates.TemplateResponse("forms.html", {
        "request": request, 
        "type": "import",
        "messages": get_messages(request),
        "user": user,
        "is_admin": is_admin(request)
    })

@app.post("/calendar/import")
async def process_import_calendar(
    request: Request,
    url_ical: str = Form(..., alias="url"),
    titulo: str = Form(...)
):
    """Procesa la importación llamando al Gateway -> External Service."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    data = {
        "url": url_ical,
        "titulo_importado": titulo,
        "organizador": user.get("name", "Usuario Importador")
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{GATEWAY_URL}/external/import/ical",
                json=data,
                headers=get_frontend_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                count = result.get('events_imported', 0)
                return RedirectResponse(
                    url=f"/?msg=Importación exitosa: {count} eventos creados&cat=success", 
                    status_code=303
                )
            else:
                error_detail = response.json().get('detail', response.text)
                return RedirectResponse(
                    url=f"/calendar/import?msg=Error: {error_detail}&cat=danger", 
                    status_code=303
                )
        except httpx.ReadTimeout: 
            return RedirectResponse(
                url=f"/calendar/import?msg=El servidor está tardando demasiado. El calendario se creará en segundo plano.&cat=warning", 
                status_code=303
            )
        except httpx.RequestError:
            return RedirectResponse(
                url=f"/calendar/import?msg=Error de conexión con el servicio de importación&cat=danger", 
                status_code=303
            )

# 3. DETALLE DE CALENDARIO
@app.get("/calendar/{id}", response_class=HTMLResponse)
async def calendar_detail(id: str, request: Request):
    user = get_current_user(request)
    
    # DEBUG: Imprimir información del usuario
    print(f"DEBUG - Usuario actual: {user}")
    print(f"DEBUG - Es admin: {is_admin(request)}")
    
    async with httpx.AsyncClient() as client:
        try:
            cal_res = await client.get(
                f"{GATEWAY_URL}/calendar/calendars/{id}",
                headers=get_frontend_headers()
            )
            if cal_res.status_code != 200:
                return RedirectResponse(url="/?msg=Calendario no encontrado&cat=danger", status_code=303)
            calendar = cal_res.json()
            
            # DEBUG: Imprimir información del calendario
            print(f"DEBUG - Organizador del calendario: {calendar.get('organizador')}")
            
            # Verificar acceso: calendario público O usuario logueado O admin
            if not calendar.get("es_publico", False):
                if not user:
                    return RedirectResponse(url="/login?msg=Este calendario es privado&cat=warning", status_code=303)
            
            events_res = await client.get(
                f"{GATEWAY_URL}/event/events/calendar/{id}",
                headers=get_frontend_headers()
            )
            events = events_res.json() if events_res.status_code == 200 else []
            
            sub_res = await client.get(
                f"{GATEWAY_URL}/calendar/calendars/{id}/subcalendars",
                headers=get_frontend_headers()
            )
            subcalendars = sub_res.json() if sub_res.status_code == 200 else []
            
            # Determinar si puede editar (es el organizador O es admin)
            can_edit = False
            if user:
                is_owner = calendar.get("organizador") == user.get("name")
                is_user_admin = is_admin(request)
                can_edit = is_owner or is_user_admin
                
                # DEBUG: Imprimir resultado
                print(f"DEBUG - Es propietario: {is_owner}")
                print(f"DEBUG - Es admin: {is_user_admin}")
                print(f"DEBUG - Puede editar: {can_edit}")
            
            return templates.TemplateResponse("calendar_detail.html", {
                "request": request,
                "calendar": calendar,
                "events": events,
                "subcalendars": subcalendars,
                "messages": get_messages(request),
                "user": user,
                "is_admin": is_admin(request),
                "can_edit": can_edit
            })
        except httpx.RequestError:
            return RedirectResponse(url="/?msg=Error de conexión&cat=danger", status_code=303)

# ...existing code...
@app.post("/calendar/{id}/delete")
async def delete_calendar(id: str, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    
    # Verificar permisos: solo el propietario o admin puede eliminar
    async with httpx.AsyncClient() as client:
        try:
            cal_res = await client.get(
                f"{GATEWAY_URL}/calendar/calendars/{id}",
                headers=get_frontend_headers()
            )
            if cal_res.status_code == 200:
                calendar = cal_res.json()
                is_owner = calendar.get("organizador") == user.get("name")
                
                if not is_owner and not is_admin(request):
                    return RedirectResponse(
                        url=f"/calendar/{id}?msg=No tienes permisos para eliminar este calendario&cat=danger",
                        status_code=303
                    )
            
            response = await client.delete(
                f"{GATEWAY_URL}/calendar/calendars/{id}",
                headers=get_frontend_headers()
            )
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
    if not user:
        return RedirectResponse("/login?msg=Debes iniciar sesión&cat=warning", status_code=303)

    return templates.TemplateResponse("forms.html", {
        "request": request, 
        "type": "event", 
        "calendar_id": calendar_id,
        "messages": get_messages(request),
        "user": user,
        "is_admin": is_admin(request)
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
    imagenes: List[UploadFile] = File(default=[]),
    latitud: Optional[float] = Form(None),
    longitud: Optional[float] = Form(None)
):
    if not get_current_user(request):
        return RedirectResponse("/login", status_code=303)

    # Preparar los datos del formulario
    data = {
        'idCalendario': calendar_id,
        'titulo': titulo,
        'horaComienzo': horaComienzo,
        'duracionMinutos': str(duracionMinutos),
        'lugar': lugar,
        'organizador': organizador,
    }
    
    if latitud is not None:
        data['latitud'] = str(latitud)
    if longitud is not None:
        data['longitud'] = str(longitud)
    
    # Preparar archivos de imagen
    files = []
    if imagenes:
        for imagen in imagenes[:3]:
            content = await imagen.read()
            if content:  # Solo si hay contenido
                files.append(('imagenes', (imagen.filename, content, imagen.content_type)))
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{GATEWAY_URL}/event/events/",
                data=data,
                files=files if files else None,
                headers=get_frontend_headers()
            )
            
            if response.status_code == 201:
                return RedirectResponse(url=f"/calendar/{calendar_id}?msg=Evento creado&cat=success", status_code=303)
            else:
                return RedirectResponse(url=f"/event/new/{calendar_id}?msg=Error: {response.text}&cat=danger", status_code=303)
        except httpx.RequestError as e:
            return RedirectResponse(url=f"/event/new/{calendar_id}?msg=Error de conexión: {str(e)}&cat=danger", status_code=303)

@app.get("/event/{id}", response_class=HTMLResponse)
async def event_detail(id: str, request: Request):
    user = get_current_user(request)
    
    async with httpx.AsyncClient() as client:
        try:
            event_res = await client.get(
                f"{GATEWAY_URL}/event/events/{id}",
                headers=get_frontend_headers()
            )
            if event_res.status_code != 200:
                return RedirectResponse(url="/?msg=Evento no encontrado&cat=danger", status_code=303)
            event = event_res.json()
            
            comments_res = await client.get(
                f"{GATEWAY_URL}/comment/comments/",
                params={"idEvento": id},
                headers=get_frontend_headers()
            )
            comments = comments_res.json() if comments_res.status_code == 200 else []
            
            # Determinar si puede editar (es el organizador O es admin)
            can_edit = False
            if user:
                is_owner = event.get("organizador") == user.get("name")
                can_edit = is_owner or is_admin(request)
            
            return templates.TemplateResponse("event_detail.html", {
                "request": request,
                "event": event,
                "comments": comments,
                "messages": get_messages(request),
                "user": user,
                "is_admin": is_admin(request),
                "can_edit": can_edit
            })
        except httpx.RequestError:
            return RedirectResponse(url="/?msg=Error de conexión&cat=danger", status_code=303)

@app.post("/event/{id}/delete")
async def delete_event(id: str, request: Request):
    """Eliminar un evento (solo propietario o admin)."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    
    async with httpx.AsyncClient() as client:
        try:
            # Primero obtener el evento para verificar permisos
            event_res = await client.get(
                f"{GATEWAY_URL}/event/events/{id}",
                headers=get_frontend_headers()
            )
            if event_res.status_code == 200:
                event = event_res.json()
                is_owner = event.get("organizador") == user.get("name")
                calendar_id = event.get("idCalendario")
                
                if not is_owner and not is_admin(request):
                    return RedirectResponse(
                        url=f"/event/{id}?msg=No tienes permisos para eliminar este evento&cat=danger",
                        status_code=303
                    )
                
                # Eliminar el evento
                response = await client.delete(
                    f"{GATEWAY_URL}/event/events/{id}",
                    headers=get_frontend_headers()
                )
                if response.status_code == 204:
                    return RedirectResponse(url=f"/calendar/{calendar_id}?msg=Evento eliminado&cat=success", status_code=303)
                else:
                    return RedirectResponse(url=f"/event/{id}?msg=No se pudo eliminar&cat=danger", status_code=303)
            else:
                return RedirectResponse(url="/?msg=Evento no encontrado&cat=danger", status_code=303)
        except httpx.RequestError:
            return RedirectResponse(url=f"/event/{id}?msg=Error de conexión&cat=danger", status_code=303)


@app.post("/event/{id}/comment")
async def add_comment(
    id: str, 
    request: Request,
    contenido: str = Form(...),
    notif_pref: str = Form("email") # Recibimos esto pero ya no lo usamos para lógica, lo gestiona el backend
):
    # 1. Obtenemos el usuario de la sesión
    user = get_current_user(request)
    
    # Preparamos los datos del comentario
    data = {
        "contenido": contenido,
        "idEvento": id,
        "idCalendario": None
    }
    
    # 2. Preparamos las cabeceras
    # Si hay usuario logueado, mandamos su nombre. Si no, no mandamos nada (backend pondrá Anónimo)
    headers = {}
    if user and "name" in user:
        # Limpiamos el nombre: "Gálvez" se convierte en "Galvez" para evitar error 500
        nombre_limpio = ''.join(
            c for c in unicodedata.normalize('NFD', user["name"])
            if unicodedata.category(c) != 'Mn'
        )
        headers["X-User-Name"] = nombre_limpio

    async with httpx.AsyncClient() as client:
        try:
            # 3. Enviamos la petición AL GATEWAY con los headers correctos
            # Nota: Ya no enviamos el query param 'enviar_email' porque el servicio lo calcula solo
            frontend_headers = get_frontend_headers()
            if headers:
                frontend_headers.update(headers)
            
            response = await client.post(
                f"{GATEWAY_URL}/comment/comments/", 
                json=data,
                headers=frontend_headers
            )
            
            if response.status_code == 201:
                return RedirectResponse(url=f"/event/{id}?msg=Comentario añadido&cat=success", status_code=303)
            else:
                return RedirectResponse(url=f"/event/{id}?msg=Error al comentar: {response.text}&cat=danger", status_code=303)
        except httpx.RequestError:
            return RedirectResponse(url=f"/event/{id}?msg=Error de conexión&cat=danger", status_code=303)

# --- RUTAS DE ADMINISTRACIÓN (SOLO ADMIN) ---

@app.get("/admin/calendars", response_class=HTMLResponse)
async def admin_calendars(request: Request):
    """Panel de administración para ver TODOS los calendarios (solo admin)."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login?msg=Debes iniciar sesión&cat=warning", status_code=303)
    
    if not is_admin(request):
        return RedirectResponse("/?msg=No tienes permisos de administrador&cat=danger", status_code=303)
    
    async with httpx.AsyncClient() as client:
        try:
            # Obtener TODOS los calendarios (públicos y privados)
            response = await client.get(
                f"{GATEWAY_URL}/calendar/calendars/",
                headers=get_frontend_headers()
            )
            calendars = response.json() if response.status_code == 200 else []
        except httpx.RequestError:
            calendars = []
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "calendars": calendars,
        "messages": get_messages(request),
        "user": user,
        "is_admin": True,
        "admin_view": True  # Flag para mostrar que es vista de admin
    })


# --- OTRAS RUTAS ---

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: Optional[str] = None):
    results = {'calendars': [], 'events': []}
    if q:
        async with httpx.AsyncClient() as client:
            try:
                cal_res = await client.get(
                    f"{GATEWAY_URL}/calendar/calendars/",
                    params={'titulo': q},
                    headers=get_frontend_headers()
                )
                if cal_res.status_code == 200:
                    results['calendars'] = cal_res.json()
                
                event_res = await client.get(
                    f"{GATEWAY_URL}/event/events/",
                    params={'titulo': q},
                    headers=get_frontend_headers()
                )
                if event_res.status_code == 200:
                    results['events'] = event_res.json()
            except httpx.RequestError:
                pass
            
    return templates.TemplateResponse("search.html", {
        "request": request,
        "results": results,
        "query": q,
        "messages": get_messages(request),
        "user": get_current_user(request),
        "is_admin": is_admin(request)
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    
    current_pref = "email" # Valor por defecto
    
    # Consultamos al backend qué tiene el usuario configurado
    async with httpx.AsyncClient() as client:
        try:
            # OJO: La URL debe coincidir con tu Router (/comments/preferences/...)
            # Si tu Gateway redirige /comment a /comments del servicio:
            res = await client.get(
                f"{GATEWAY_URL}/comment/comments/preferences/{user['email']}",
                headers=get_frontend_headers()
            )
            
            # NOTA: Ajusta la URL según cómo tengas el Gateway. 
            # Si en gateway es /comment -> servicio /comments, entonces la url es correcta.
            
            if res.status_code == 200:
                current_pref = res.json().get("preference", "email")
        except httpx.RequestError:
            print("⚠️ Backend no disponible para preferencias")

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user": user,
        "current_pref": current_pref, # Pasamos la preferencia al HTML
        "is_admin": is_admin(request)
    })

@app.post("/settings")
async def update_settings(request: Request, notif_option: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    async with httpx.AsyncClient() as client:
        try:
            payload = {"email": user["email"], "preference": notif_option}
            
            # Enviamos la nueva preferencia al backend
            await client.post(
                f"{GATEWAY_URL}/comment/comments/preferences",
                json=payload,
                headers=get_frontend_headers()
            )
            
            return RedirectResponse("/settings?msg=Preferencias guardadas&cat=success", status_code=303)
        except httpx.RequestError:
            return RedirectResponse("/settings?msg=Error de conexión&cat=danger", status_code=303)
        


@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    notificaciones = []
    
    # Llamamos al Backend para pedir la lista real de Mongo
    async with httpx.AsyncClient() as client:
        try:
            # Petición al Gateway -> Servicio Comentarios -> Mis Notificaciones
            response = await client.get(
                f"{GATEWAY_URL}/comment/comments/notifications",
                params={"email": user["email"]},
                headers=get_frontend_headers()
            )
            if response.status_code == 200:
                notificaciones = response.json()
        except httpx.RequestError:
            print("⚠️ Error conectando con el servicio de notificaciones")

    # Renderizamos la plantilla con los datos reales
    return templates.TemplateResponse("notifications.html", {
        "request": request,
        "user": user,
        "notificaciones": notificaciones, 
        "is_admin": is_admin(request)
    })
@app.get("/token", tags=["Auth"])
async def get_token(request: Request):
    """
    Devuelve el token JWT del usuario autenticado.
    Este token puede usarse en la cabecera Authorization: Bearer <token>
    para acceder a los métodos protegidos de la API.
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    
    # Obtener el token JWT de la sesión
    jwt_token = request.session.get("jwt_token")
    
    if not jwt_token:
        # Si por alguna razón no existe, generarlo ahora
        jwt_token = create_jwt_token(user)
        request.session["jwt_token"] = jwt_token
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role")
        }
    }
