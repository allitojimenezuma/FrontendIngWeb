from fastapi import FastAPI
from .router import events


app = FastAPI(
    title="API de Kalendas",
    description="API para la gestión de calendarios y eventos.",
    version="1.0.0"
)

# Incluimos el router de eventos en la aplicación principal.
app.include_router(events.router)


@app.get("/")
def root():
    return {"message": "Event Service activo y conectado"}
