from fastapi import APIRouter, Body, Response, status, Query, Depends
from typing import List, Annotated, Optional
from uuid import UUID

from ..service.commentsService import CommentsService
from ..dependencies import get_comments_service
from ..model.comment_models import CommentCreate, CommentInDB

router = APIRouter(prefix="/comments", tags=["Comentarios"])

# Inyección de Dependencia
ServiceDep = Annotated[CommentsService, Depends(get_comments_service)]

@router.post("/", response_model=CommentInDB, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment: Annotated[CommentCreate, Body(...)],
    service: ServiceDep,
    enviar_email: bool = Query(True)
):
    # Delegamos TODO al servicio
    return await service.create_comment(comment, enviar_email)

@router.get("/", response_model=List[CommentInDB])
async def list_comments(
    service: ServiceDep,
    id_calendario: Optional[UUID] = Query(None, alias="idCalendario"),
    id_evento: Optional[UUID] = Query(None, alias="idEvento")
):
    return await service.list_comments(id_calendario, id_evento)

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