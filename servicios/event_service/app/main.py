from fastapi import FastAPI
from .router import events
import cloudinary

app = FastAPI(
    title="API de Kalendas",
    description="API para la gestión de calendarios y eventos.",
    version="1.0.0"
)

# Configurar Cloudinary
cloudinary.config(
    cloud_name="dkfavafuw",
    api_key="951366356974856",
    api_secret="VvAvqEnn8HG2sI-sM_p72Gq0UPI",
    secure=True
)

# Incluimos el router de eventos en la aplicación principal.
app.include_router(events.router)


@app.get("/")
def root():
    return {"message": "Event Service activo y conectado"}