from fastapi import FastAPI, Request, HTTPException, Response
import os
import httpx
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Gateway")

# URLs internas de los microservicios (definidas en docker-compose)
SERVICES = {
    "calendar": os.getenv("CALENDAR_SERVICE_URL", "http://calendar_service:8000"),
    "event": os.getenv("EVENT_SERVICE_URL", "http://event_service:8000"),
    "comment": os.getenv("COMMENT_SERVICE_URL", "http://comment_service:8000"),
    "external": os.getenv("EXTERNAL_SERVICE_URL", "http://external_service:8000"),
}

# Log de configuración al iniciar
logger.info(f"🚀 Gateway iniciado con servicios: {SERVICES}")

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
@app.api_route("/calendar/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["Calendar Service"])
async def calendar_proxy(path: str, request: Request):
    return await _proxy_request("calendar", path, request)

# --- Event Service Proxy ---
@app.api_route("/event/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["Event Service"])
async def event_proxy(path: str, request: Request):
    return await _proxy_request("event", path, request)

# --- Comment Service Proxy ---
@app.api_route("/comment/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["Comment Service"])
async def comment_proxy(path: str, request: Request):
    return await _proxy_request("comment", path, request)

@app.api_route("/external/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], tags=["External Import"])
async def external_proxy(path: str, request: Request):
    return await _proxy_request("external", path, request)