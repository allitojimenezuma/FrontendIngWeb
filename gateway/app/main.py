from fastapi import FastAPI, Request, HTTPException, Response, UploadFile, File, Form
import os
import httpx
from typing import Optional

app = FastAPI(title="API Gateway")

# URLs internas de los microservicios (definidas en docker-compose)
SERVICES = {
    "calendar": os.getenv("CALENDAR_SERVICE_URL", "http://calendar_service:8000"),
    "event": os.getenv("EVENT_SERVICE_URL", "http://event_service:8000"),
    "comment": os.getenv("COMMENT_SERVICE_URL", "http://comment_service:8000"),
}

# --- Lógica de Proxy Reutilizable ---
async def _proxy_request(service: str, path: str, request: Request):
    """Función genérica para reenviar una petición a un microservicio."""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Servicio '{service}' no encontrado")

    service_base_url = SERVICES[service]
    
    # Verificar si es multipart/form-data (para archivos)
    content_type = request.headers.get("content-type", "")
    
    async with httpx.AsyncClient(base_url=service_base_url, timeout=30.0) as client:
        try:
            if "multipart/form-data" in content_type:
                # Para formularios con archivos, reenviar el body completo
                body = await request.body()
                response = await client.request(
                    method=request.method,
                    url=f"/{path}",
                    headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                    params=request.query_params,
                    content=body,
                    follow_redirects=True,
                )
            else:
                # Para peticiones normales (JSON, etc.)
                body = await request.body()
                response = await client.request(
                    method=request.method,
                    url=f"/{path}",
                    headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
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
async def calendar_proxy(path: str, request: Request):
    return await _proxy_request("calendar", path, request)

# --- Event Service Proxy ---
@app.get("/event/{path:path}", tags=["Event Service"])
@app.post("/event/{path:path}", tags=["Event Service"])
@app.put("/event/{path:path}", tags=["Event Service"])
@app.delete("/event/{path:path}", tags=["Event Service"])
async def event_proxy(path: str, request: Request):
    return await _proxy_request("event", path, request)

# --- Comment Service Proxy ---
@app.get("/comment/{path:path}", tags=["Comment Service"])
@app.post("/comment/{path:path}", tags=["Comment Service"])
@app.put("/comment/{path:path}", tags=["Comment Service"])
@app.delete("/comment/{path:path}", tags=["Comment Service"])
async def comment_proxy(path: str, request: Request):
    return await _proxy_request("comment", path, request)