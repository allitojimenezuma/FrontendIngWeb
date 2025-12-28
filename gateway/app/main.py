from fastapi import FastAPI, Request, HTTPException, Response, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os
import httpx
import logging
import jwt
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar seguridad HTTP Bearer para Swagger UI
security = HTTPBearer(auto_error=False)

app = FastAPI(
    title="API Gateway",
    description="Gateway para la API de Kalendas con autenticación JWT",
    version="1.0.0"
)

# Clave secreta para validar tokens JWT (debe ser la misma que en el frontend)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "clave_super_secreta_jwt_kalendas_2024")
JWT_ALGORITHM = "HS256"

# URLs internas de los microservicios (definidas en docker-compose)
SERVICES = {
    "calendar": os.getenv("CALENDAR_SERVICE_URL", "http://calendar_service:8000"),
    "event": os.getenv("EVENT_SERVICE_URL", "http://event_service:8000"),
    "comment": os.getenv("COMMENT_SERVICE_URL", "http://comment_service:8000"),
    "external": os.getenv("EXTERNAL_SERVICE_URL", "http://external_service:8000"),
}

# Log de configuración al iniciar
logger.info(f"🚀 Gateway iniciado con servicios: {SERVICES}")

# Log de configuración al iniciar
logger.info(f"🚀 Gateway iniciado con servicios: {SERVICES}")

# --- Funciones de Autenticación ---

def verify_jwt_token(authorization: Optional[str]) -> dict:
    """
    Verifica el token JWT de la cabecera Authorization.
    Retorna los datos del usuario si el token es válido.
    Lanza HTTPException si el token es inválido o no está presente.
    """
    if not authorization:
        print("No se proporcionó cabecera Authorization")
        raise HTTPException(
            status_code=401, 
            detail="No autorizado. Cabecera Authorization requerida"
        )
    
    # Verificar que empiece con "Bearer "
    if not authorization.startswith("Bearer "):
        print("Formato de token inválido")
        raise HTTPException(
            status_code=401, 
            detail="Formato de token inválido. Use: Authorization: Bearer <token>"
        )
    
    # Extraer el token
    token = authorization.replace("Bearer ", "")
    
    try:
        # Decodificar y validar el token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Verificar que no haya expirado
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            print("Token expirado")
            raise HTTPException(status_code=401, detail="Token expirado")
        
        return payload
    except jwt.ExpiredSignatureError:
        print("Token expirado")
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        print("Token inválido")
        raise HTTPException(status_code=401, detail="Token inválido")

def is_frontend_request(request: Request) -> bool:
    """
    Detecta si la petición viene del frontend web (interno de Kalendas)
    o es una petición directa a la API REST externa.
    """
    # Si tiene el header especial del frontend, es petición interna
    frontend_header = request.headers.get("x-frontend-request")
    if frontend_header == "true":
        return True
    
    # Si tiene Authorization Bearer, es petición externa a la API
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return False
    
    # Por defecto, asumimos que es petición externa que requiere auth
    return False

# --- Lógica de Proxy Reutilizable ---
async def _proxy_request(service: str, path: str, request: Request):
    """Función genérica para reenviar una petición a un microservicio."""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Servicio '{service}' no encontrado")

    service_base_url = SERVICES[service]
    
    body = await request.body()
    
    # Construir la URL completa, preservando la barra final si existe
    # Usar request.url.path para obtener la ruta original completa
    original_path = str(request.url.path)
    # Remover el prefijo del servicio (ej: /calendar/)
    service_prefix = f"/{service}/"
    if original_path.startswith(service_prefix):
        remaining_path = original_path[len(service_prefix):]
    else:
        remaining_path = path
    
    target_url = f"{service_base_url}/{remaining_path}"
    
    logger.info(f"🔄 Proxy request: {request.method} {target_url}")
    
    # Filtrar headers problemáticos que no deben reenviarse
    headers_to_exclude = {"host", "content-length", "transfer-encoding", "connection"}
    filtered_headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in headers_to_exclude
    }
    
    # Cliente sin base_url, usar URLs completas
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=filtered_headers,
                params=request.query_params,
                content=body,
                follow_redirects=True,
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Error al conectar con {service}: {str(e)}")

# --- Rutas Explícitas para cada Microservicio ---

@app.get("/")
def root():
    return {"message": "Bienvenido a la API de Kalendas. Visita /docs para ver la documentación."}

# --- Calendar Service Proxy ---
@app.get("/calendar/{path:path}", tags=["Calendar Service"])
@app.post("/calendar/{path:path}", tags=["Calendar Service"])
@app.put("/calendar/{path:path}", tags=["Calendar Service"])
@app.delete("/calendar/{path:path}", tags=["Calendar Service"])
async def calendar_proxy(
    path: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    # Solo verificar JWT si NO es una petición del frontend web
    if not is_frontend_request(request):
        # Obtener el token de HTTPBearer (Swagger) o del header directo
        auth_header = None
        if credentials:
            auth_header = f"Bearer {credentials.credentials}"
        else:
            auth_header = request.headers.get("authorization")
        
        verify_jwt_token(auth_header)
    
    return await _proxy_request("calendar", path, request)

# --- Event Service Proxy ---
@app.get("/event/{path:path}", tags=["Event Service"])
@app.post("/event/{path:path}", tags=["Event Service"])
@app.put("/event/{path:path}", tags=["Event Service"])
@app.delete("/event/{path:path}", tags=["Event Service"])
async def event_proxy(
    path: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    # Solo verificar JWT si NO es una petición del frontend web
    if not is_frontend_request(request):
        auth_header = None
        if credentials:
            auth_header = f"Bearer {credentials.credentials}"
        else:
            auth_header = request.headers.get("authorization")
        
        verify_jwt_token(auth_header)
    
    return await _proxy_request("event", path, request)

# --- Comment Service Proxy ---
@app.get("/comment/{path:path}", tags=["Comment Service"])
@app.post("/comment/{path:path}", tags=["Comment Service"])
@app.put("/comment/{path:path}", tags=["Comment Service"])
@app.delete("/comment/{path:path}", tags=["Comment Service"])
async def comment_proxy(
    path: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    # Solo verificar JWT si NO es una petición del frontend web
    if not is_frontend_request(request):
        auth_header = None
        if credentials:
            auth_header = f"Bearer {credentials.credentials}"
        else:
            auth_header = request.headers.get("authorization")
        
        verify_jwt_token(auth_header)
    
    return await _proxy_request("comment", path, request)

@app.post("/external/{path:path}", tags=["External Import"])
async def external_proxy(
    path: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    # Solo verificar JWT si NO es una petición del frontend web
    if not is_frontend_request(request):
        auth_header = None
        if credentials:
            auth_header = f"Bearer {credentials.credentials}"
        else:
            auth_header = request.headers.get("authorization")
        
        verify_jwt_token(auth_header)
    
    return await _proxy_request("external", path, request)