from .crud.comment_crud import CommentCRUD
from .service.commentsService import CommentsService

# Instanciación estática del CRUD (si no requiere sesión/estado)
COMMENT_CRUD_INSTANCE = CommentCRUD()

def get_comment_crud() -> CommentCRUD:
    """Provee la instancia del CRUD (útil para otros servicios o tests)."""
    return COMMENT_CRUD_INSTANCE

def get_comment_service() -> CommentsService:
    """Provee la instancia del CommentsService, inyectándole el CRUD."""
    return CommentsService(crud=COMMENT_CRUD_INSTANCE)