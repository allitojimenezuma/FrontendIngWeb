from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException, status

from ..model.comment_models import CommentCreate, CommentInDB
from ..crud.comment_crud import CommentCRUD


class CommentsService:
    """
    Lógica de negocio para Comentarios.
    Se comunica con la capa CRUD (Repository) y aplica validaciones de negocio.
    """

    def __init__(self, crud: CommentCRUD):
        self.crud = crud


    async def create_comment(self, comment_data: CommentCreate) -> CommentInDB:
        """
        Crea un nuevo comentario.
        Valida que se proporcione al menos idCalendario o idEvento.
        """
        # Validación de negocio: debe haber al menos un ID
        if not comment_data.id_calendario and not comment_data.id_evento:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar idCalendario o idEvento"
            )

        # Convertir el modelo Pydantic a diccionario y añadir el _id
        comment_dict = comment_data.model_dump(by_alias=True)
        comment_dict["_id"] = uuid4()

        # Llamar al CRUD para insertar
        return await self.crud.create(comment_dict)


    async def get_comment(self, comment_id: UUID) -> CommentInDB:
        """
        Obtiene un comentario por su ID.
        Lanza 404 si no existe.
        """
        comment = await self.crud.get_by_id(comment_id)
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comentario con ID {comment_id} no encontrado"
            )
        return comment


    async def list_comments(
        self, 
        id_calendario: Optional[UUID] = None,
        id_evento: Optional[UUID] = None
    ) -> List[CommentInDB]:
        """
        Lista comentarios con filtros opcionales.
        Si no se proporciona filtro, devuelve todos los comentarios.
        """
        filtro = {}
        
        if id_calendario:
            filtro["idCalendario"] = id_calendario
        
        if id_evento:
            filtro["idEvento"] = id_evento
        
        return await self.crud.list_by_filter(filtro)


    async def update_comment(
        self, 
        comment_id: UUID, 
        comment_data: CommentCreate
    ) -> CommentInDB:
        """
        Actualiza un comentario existente.
        Lanza 404 si no existe.
        """
        update_dict = comment_data.model_dump(by_alias=True, exclude_unset=True)
        
        updated_comment = await self.crud.update(comment_id, update_dict)
        
        if not updated_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se pudo actualizar, comentario con ID {comment_id} no encontrado"
            )
        
        return updated_comment


    async def delete_comment(self, comment_id: UUID) -> None:
        """
        Elimina un comentario.
        Lanza 404 si no existe.
        """
        deleted_count = await self.crud.delete(comment_id)
        
        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comentario con ID {comment_id} no encontrado"
            )


    async def get_comments_by_calendar(self, calendar_id: UUID) -> List[CommentInDB]:
        """Obtiene todos los comentarios de un calendario específico."""
        return await self.crud.get_by_calendar(calendar_id)


    async def get_comments_by_event(self, event_id: UUID) -> List[CommentInDB]:
        """Obtiene todos los comentarios de un evento específico."""
        return await self.crud.get_by_event(event_id)