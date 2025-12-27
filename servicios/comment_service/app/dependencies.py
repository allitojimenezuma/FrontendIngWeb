from app.service.commentsService import CommentsService
from app.database import db 

def get_comments_service() -> CommentsService:
    return CommentsService(db=db) # Pasa 'db', NO 'crud'