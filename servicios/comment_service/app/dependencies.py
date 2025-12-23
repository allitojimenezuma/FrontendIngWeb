from app.service.commentsService import CommentsService
from app.crud.comment_crud import CommentCRUD

# Instancia única del CRUD (Singleton)
COMMENT_CRUD_INSTANCE = CommentCRUD()

def get_comments_service() -> CommentsService:
    """Inyecta el CRUD en el Servicio y devuelve la instancia del Servicio."""
    return CommentsService(crud=COMMENT_CRUD_INSTANCE)