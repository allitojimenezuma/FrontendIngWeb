from typing import List, Optional
from uuid import UUID
from pymongo import ReturnDocument

# Importaciones de tu proyecto
from .. import database
from ..model.comment_models import CommentCreate, CommentInDB 

# Alias para la colección de MongoDB (simplifica el código)
CommentCollection = database.comentarios_collection 

class CommentCRUD:
    """
    Capa de Acceso a Datos (Repository) para Comentarios (MongoDB).
    Toda la sintaxis de PyMongo se encapsula aquí.
    """

    async def create(self, comment_data: dict) -> CommentInDB:
        """Inserta el diccionario de comentario en la BD y lo recupera."""
        new_comment = CommentCollection.insert_one(comment_data)
        created_comment = CommentCollection.find_one({"_id": new_comment.inserted_id})
        return CommentInDB.model_validate(created_comment)


    async def get_by_id(self, comment_id: UUID) -> Optional[CommentInDB]:
        """Busca un comentario por ID."""
        comment_data = CommentCollection.find_one({"_id": comment_id})
        if comment_data:
            return CommentInDB.model_validate(comment_data)
        return None

    
    async def list_by_filter(self, filters: dict) -> List[CommentInDB]:
        """Devuelve una lista de comentarios aplicando el filtro de MongoDB."""
        cursor = CommentCollection.find(filters)
        comment_list = list(cursor)
        return [CommentInDB.model_validate(comment) for comment in comment_list]


    async def update(self, comment_id: UUID, update_data: dict) -> Optional[CommentInDB]:
        """Actualiza y devuelve el documento actualizado."""
        updated_data = CommentCollection.find_one_and_update(
            {"_id": comment_id},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )
        if updated_data:
            return CommentInDB.model_validate(updated_data)
        return None


    async def delete(self, comment_id: UUID) -> int:
        """Elimina un comentario y devuelve el número de documentos eliminados (0 o 1)."""
        delete_result = CommentCollection.delete_one({"_id": comment_id})
        return delete_result.deleted_count
    

    async def get_by_calendar(self, calendar_id: UUID) -> List[CommentInDB]:
        """Devuelve los comentarios que pertenecen a un calendario específico."""
        filtro = {"idCalendario": calendar_id}
        cursor = CommentCollection.find(filtro)
        comment_list = list(cursor)
        return [CommentInDB.model_validate(comment) for comment in comment_list]


    async def get_by_event(self, event_id: UUID) -> List[CommentInDB]:
        """Devuelve los comentarios que pertenecen a un evento específico."""
        filtro = {"idEvento": event_id}
        cursor = CommentCollection.find(filtro)
        comment_list = list(cursor)
        return [CommentInDB.model_validate(comment) for comment in comment_list]