from fastapi import FastAPI
from .router import comments


app = FastAPI(
    title="API de Kalendas",
    description="API para la gestión de calendarios y eventos.",
    version="1.0.0"
)

# Incluimos el router de comentarios en la aplicación principal.
app.include_router(comments.router)


@app.get("/")
def root():
    return {"message": "Comment Service activo y conectado"}
