from fastapi import APIRouter, Body, Response, status, HTTPException, Query
from fastapi.responses import JSONResponse
from pymongo import ReturnDocument
from typing import List, Annotated, Optional
from uuid import UUID, uuid4
import os

# --- IMPORTACIONES DE SENDGRID ---
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
# ---------------------------------

# Importaciones de tus modelos y base de datos
# Asegúrate de que estas rutas sean correctas según tu estructura
from ..model.comment_models import CommentCreate, CommentInDB
from .. import database

router = APIRouter(
    prefix="/comments",
    tags=["Comentarios"]
)

# --- FUNCIÓN DE EMAIL (Directamente aquí para evitar errores de import) ---
def enviar_notificacion_email(destinatario: str, nombre_evento: str, contenido_comentario: str):
    api_key = os.environ.get('SENDGRID_API_KEY')
    remitente = os.environ.get('EMAIL_REMITENTE')

    if not api_key or not remitente:
        print("⚠️ Faltan claves de SendGrid en .env")
        return False

    mensaje = Mail(
        from_email=remitente,
        to_emails=destinatario,
        subject=f'Nuevo comentario en evento: {nombre_evento}',
        html_content=f'''
            <div style="font-family: Arial; padding: 20px; border: 1px solid #eee;">
                <h2 style="color: #0d6efd;">Nuevo comentario</h2>
                <p>El evento <strong>{nombre_evento}</strong> tiene una nueva interacción:</p>
                <blockquote style="background: #f9f9f9; padding: 10px; border-left: 5px solid #0d6efd;">
                    "{contenido_comentario}"
                </blockquote>
                <p style="font-size: 12px; color: #888;">Enviado desde Kalendas</p>
            </div>
        '''
    )
    try:
        sg = SendGridAPIClient(api_key)
        sg.send(mensaje)
        print(f"📧 Correo enviado a {destinatario}")
        return True
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False
# -------------------------------------------------------------------------


# 1. POST /comments : Crear un nuevo comentario (VERSIÓN UNIFICADA)
@router.post(
    "/",
    response_model=CommentInDB,
    status_code=status.HTTP_201_CREATED,
    response_description="Añadir nuevo comentario",
)
async def create_comment(
    comment: Annotated[CommentCreate, Body(...)],
    enviar_email: bool = Query(True) # Por defecto es True, pero el frontend puede mandar False
):
    # ... validaciones de IDs ...
    if not comment.id_calendario and not comment.id_evento:
        raise HTTPException(status_code=400, detail="Faltan IDs")
    
    # 1. Guardar en BD (Igual que antes)
    comment_dict = comment.model_dump(by_alias=True)
    comment_dict["_id"] = uuid4()
    new_comment = database.comentarios_collection.insert_one(comment_dict)
    created_comment = database.comentarios_collection.find_one({"_id": new_comment.inserted_id})

    # 2. LOGICA CONDICIONAL DE EMAIL
    if enviar_email:  # <--- SOLO ENTRA SI ES TRUE
        try:
            email_demo = "PON_TU_EMAIL_AQUI@gmail.com"
            ref_id = str(comment.id_evento) if comment.id_evento else str(comment.id_calendario)
            
            enviar_notificacion_email(
                destinatario=email_demo, 
                nombre_evento=f"ID: {ref_id}", 
                contenido_comentario=comment.contenido
            )
        except Exception as e:
            print(f"⚠️ Error notificando: {e}")
    else:
        print("ℹ️ Notificación por email saltada por preferencia de usuario (Modo App).")

    return created_comment


# 2. GET /comments : Obtener lista
@router.get(
    "/",
    response_model=List[CommentInDB],
    response_description="Listar todos los comentarios",
)
async def list_comments(
    id_calendario: Optional[UUID] = Query(None, alias="idCalendario"),
    id_evento: Optional[UUID] = Query(None, alias="idEvento"),
):
    filtro = {}
    if id_calendario:
        filtro["idCalendario"] = id_calendario
    if id_evento:
        filtro["idEvento"] = id_evento
    
    return list(database.comentarios_collection.find(filtro))


# 3. GET /comments/{id} : Obtener uno
@router.get(
    "/{id}",
    response_model=CommentInDB,
    response_description="Obtener un comentario por su ID",
)
async def get_comment(id: UUID):
    comment = database.comentarios_collection.find_one({"_id": id})
    if comment:
        return comment
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comentario {id} no encontrado")


# 4. PUT /comments/{id} : Actualizar
@router.put(
    "/{id}",
    response_model=CommentInDB,
    response_description="Actualizar un comentario",
)
async def update_comment(id: UUID, comment_update: Annotated[CommentCreate, Body(...)]):
    updated_comment = database.comentarios_collection.find_one_and_update(
        {"_id": id},
        {"$set": comment_update.model_dump(by_alias=True, exclude_unset=True)},
        return_document=ReturnDocument.AFTER
    )
    if updated_comment:
        return updated_comment
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comentario {id} no encontrado")


# 5. DELETE /comments/{id} : Eliminar
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Eliminar un comentario",
)
async def delete_comment(id: UUID):
    delete_result = database.comentarios_collection.delete_one({"_id": id})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comentario {id} no encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


