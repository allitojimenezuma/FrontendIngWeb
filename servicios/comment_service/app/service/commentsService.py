from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException, status
import os

# Importaciones del proyecto
from ..model.comment_models import CommentCreate, CommentInDB
from ..crud.comment_crud import CommentCRUD
from ..email_utils import enviar_notificacion_email  # 👈 Usamos tu utilidad existente

class CommentsService:
    def __init__(self, crud: CommentCRUD):
        self.crud = crud

    async def create_comment(self, comment_data: CommentCreate, enviar_email: bool = True) -> CommentInDB:
        # 1. Validación de Negocio
        if not comment_data.id_calendario and not comment_data.id_evento:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar idCalendario o idEvento"
            )

        # 2. Preparar datos
        comment_dict = comment_data.model_dump(by_alias=True)
        comment_dict["_id"] = uuid4()

        # 3. Persistencia (CRUD)
        new_comment = await self.crud.create(comment_dict)

        # 4. Lógica de Notificación (Side Effect)
        if enviar_email:
            # En un entorno real, buscaríamos el email del organizador llamando al EventService.
            # Para la demo/entrega, usamos el email definido en .env o uno de prueba.
            destinatario = os.getenv("EMAIL_REMITENTE") # O el email hardcodeado para pruebas
            
            ref_id = str(comment_data.id_evento) if comment_data.id_evento else str(comment_data.id_calendario)
            
            # Llamada asíncrona "fire and forget" o await según necesidad.
            # Aquí lo hacemos síncrono por simplicidad del script de sendgrid.
            enviar_notificacion_email(
                destinatario=destinatario,
                nombre_evento=f"ID: {ref_id}",
                contenido_comentario=comment_data.contenido
            )
        
        return new_comment

    async def get_comment(self, comment_id: UUID) -> CommentInDB:
        comment = await self.crud.get_by_id(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail=f"Comentario {comment_id} no encontrado")
        return comment

    async def list_comments(self, id_calendario: Optional[UUID], id_evento: Optional[UUID]) -> List[CommentInDB]:
        filtro = {}
        if id_calendario: filtro["idCalendario"] = id_calendario
        if id_evento: filtro["idEvento"] = id_evento
        return await self.crud.list_by_filter(filtro)

    async def update_comment(self, comment_id: UUID, comment_data: CommentCreate) -> CommentInDB:
        update_dict = comment_data.model_dump(by_alias=True, exclude_unset=True)
        updated = await self.crud.update(comment_id, update_dict)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Comentario {comment_id} no encontrado")
        return updated

    async def delete_comment(self, comment_id: UUID) -> None:
        deleted = await self.crud.delete(comment_id)
        if deleted == 0:
            raise HTTPException(status_code=404, detail=f"Comentario {comment_id} no encontrado")