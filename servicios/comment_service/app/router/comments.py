from fastapi import APIRouter, Body, Response, status, Query, Depends, Header
from typing import List, Annotated, Optional
from uuid import UUID
from pydantic import BaseModel

from ..service.commentsService import CommentsService
from ..dependencies import get_comments_service
from ..model.comment_models import CommentCreate, CommentInDB

router = APIRouter(prefix="/comments", tags=["Comentarios"])

# Inyección de Dependencia
ServiceDep = Annotated[CommentsService, Depends(get_comments_service)]

class PreferenceUpdate(BaseModel):
    email: str
    preference: str  # "email" o "app"

@router.post("/", response_model=CommentInDB, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment: Annotated[CommentCreate, Body(...)],
    service: ServiceDep,
    # Recibimos el nombre del usuario si el Frontend lo manda (o ponemos Anónimo)
    x_user_name: Optional[str] = Header("Usuario Anónimo", alias="X-User-Name")
):
    """
    Crea un comentario y notifica al organizador.
    """
    # Llamamos al servicio con los argumentos correctos (modelo + nombre autor)
    return await service.create_comment(comment, x_user_name)

@router.get("/", response_model=List[CommentInDB])
async def list_comments(
    service: ServiceDep,
    id_calendario: Optional[UUID] = Query(None, alias="idCalendario"),
    id_evento: Optional[UUID] = Query(None, alias="idEvento")
):
    return await service.list_comments(id_calendario, id_evento)

@router.get("/notifications", tags=["Notificaciones"])
async def get_my_notifications(
    service: ServiceDep,
    x_user_email: str = Query(..., alias="email") # Recibimos email por query param
):
    return await service.get_notifications(x_user_email)

@router.get("/{id}", response_model=CommentInDB)
async def get_comment(id: UUID, service: ServiceDep):
    return await service.get_comment(id)

@router.put("/{id}", response_model=CommentInDB)
async def update_comment(id: UUID, comment_update: CommentCreate, service: ServiceDep):
    return await service.update_comment(id, comment_update)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(id: UUID, service: ServiceDep):
    await service.delete_comment(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/preferences/{email}", tags=["Preferencias"])
async def get_preferences(email: str, service: ServiceDep):
    """Obtiene la preferencia de notificación de un usuario."""
    pref = await service.get_user_preference(email)
    return {"preference": pref}

@router.post("/preferences", tags=["Preferencias"])
async def save_preferences(data: PreferenceUpdate, service: ServiceDep):
    """Guarda la preferencia (Email o App)."""
    saved_pref = await service.update_user_preference(data.email, data.preference)
    return {"status": "ok", "saved": saved_pref}