from fastapi import APIRouter, Body, Response, status, HTTPException, Query
from pymongo import ReturnDocument
from typing import List, Annotated, Optional
from uuid import UUID, uuid4

from ..model.comment_models import CommentCreate, CommentInDB
from .. import database

# Router que agrupará todos los endpoints de comentarios.
router = APIRouter(
    prefix="/comments",
    tags=["Comentarios"]
)

# --- Endpoints ---

# 1. POST /comments : Crear un nuevo comentario
@router.post(
    "/",
    response_model=CommentInDB,
    status_code=status.HTTP_201_CREATED,
    response_description="Añadir nuevo comentario",
)
async def create_comment(
    comment: Annotated[CommentCreate, Body(
        examples=[{
            "contenido": "Excelente evento, muy bien organizado",
            "idCalendario": None,
            "idEvento": "a47ac10b-58cc-4372-a567-0e02b2c3d470"
        }]
    )]
):
    """
    Crea un nuevo comentario en la base de datos.
    Debe proporcionar al menos idCalendario o idEvento.
    """
    # Validar que se proporcione al menos un ID
    if not comment.id_calendario and not comment.id_evento:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar idCalendario o idEvento"
        )
    
    comment_dict = comment.model_dump(by_alias=True)
    comment_dict["_id"] = uuid4()
    new_comment = database.comentarios_collection.insert_one(comment_dict)
    created_comment = database.comentarios_collection.find_one({"_id": new_comment.inserted_id})
    return created_comment


# 2. GET /comments : Obtener una lista de todos los comentarios
@router.get(
    "/",
    response_model=List[CommentInDB],
    response_description="Listar todos los comentarios con filtros opcionales",
)
async def list_comments(
    id_calendario: Optional[UUID] = Query(None, alias="idCalendario", description="Filtrar por ID de calendario"),
    id_evento: Optional[UUID] = Query(None, alias="idEvento", description="Filtrar por ID de evento"),
):
    """
    Devuelve una lista de comentarios filtrados.
    - **idCalendario**: Filtra comentarios de un calendario específico
    - **idEvento**: Filtra comentarios de un evento específico
    
    Si no se proporciona ningún filtro, devuelve todos los comentarios.
    """
    filtro = {}
    
    if id_calendario:
        filtro["idCalendario"] = id_calendario
    
    if id_evento:
        filtro["idEvento"] = id_evento
    
    return list(database.comentarios_collection.find(filtro))


# 3. GET /comments/{id} : Obtener un comentario específico por su ID
@router.get(
    "/{id}",
    response_model=CommentInDB,
    response_description="Obtener un comentario por su ID",
)
async def get_comment(id: UUID):
    """
    Busca un comentario por su ID. Devuelve 404 si no lo encuentra.
    """
    comment = database.comentarios_collection.find_one({"_id": id})
    if comment:
        return comment

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comentario con ID {id} no encontrado")


# 4. PUT /comments/{id} : Actualizar un comentario existente
@router.put(
    "/{id}",
    response_model=CommentInDB,
    response_description="Actualizar un comentario por su ID",
)
async def update_comment(
    id: UUID, 
    comment_update: Annotated[CommentCreate, Body(...)]
):
    """
    Actualiza un comentario existente. Devuelve 404 si no lo encuentra.
    """
    updated_comment = database.comentarios_collection.find_one_and_update(
        {"_id": id},
        {"$set": comment_update.model_dump(by_alias=True, exclude_unset=True)},
        return_document=ReturnDocument.AFTER
    )

    if updated_comment:
        return updated_comment

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se pudo actualizar, comentario con ID {id} no encontrado")


# 5. DELETE /comments/{id} : Eliminar un comentario
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Eliminar un comentario por su ID",
)
async def delete_comment(id: UUID):
    """
    Elimina un comentario por su ID. Devuelve 204 si tiene éxito o 404 si no lo encuentra.
    """
    delete_result = database.comentarios_collection.delete_one({"_id": id})

    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comentario con ID {id} no encontrado")

    return Response(status_code=status.HTTP_204_NO_CONTENT)