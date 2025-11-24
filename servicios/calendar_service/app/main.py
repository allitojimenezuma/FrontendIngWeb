from fastapi import FastAPI
from .router import calendars


app = FastAPI(
    title="API de Kalendas",
    description="API para la gestión de calendarios y eventos.",
    version="1.0.0"
)

app.include_router(calendars.router)


@app.get("/")
def root():
    return {"message": "Calendar Service activo y conectado"}
