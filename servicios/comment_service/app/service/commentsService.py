from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import os
import httpx
from fastapi import HTTPException, status
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Importaciones de tu proyecto
from ..model.comment_models import CommentCreate, CommentInDB

# URL del microservicio de eventos
EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event_service:8000")

class CommentsService:
    def __init__(self, db):
        self.db = db
        self.comments_collection = db["comentarios"]
        self.users_collection = db["users"]
        self.notif_collection = db["notificaciones"]

    async def create_comment(self, comment: CommentCreate, author_name: str) -> CommentInDB:
        # 1. Crear el objeto comentario
        comment_dict = comment.model_dump(by_alias=True)
        comment_dict["_id"] = uuid4()
        comment_dict["fechaCreacion"] = datetime.now()

        # 2. Insertar en Base de Datos (SIN AWAIT)
        new_comment = self.comments_collection.insert_one(comment_dict)
        created_comment = self.comments_collection.find_one({"_id": new_comment.inserted_id})

        # 3. Lógica de Notificación (CON PROTECCIÓN)
        try:
            if comment.id_evento:
                await self._notify_organizer(comment.id_evento, author_name, comment.contenido)
        except Exception as e:
            print(f"⚠️ Alerta: Comentario guardado, pero falló el sistema de notificación: {e}")

        # 4. Devolver éxito
        return created_comment

    async def get_user_preference(self, email: str):
        # SIN AWAIT
        user = self.users_collection.find_one({"email": email})
        return user.get("notification_pref", "email") if user else "email"

    async def update_user_preference(self, email: str, preference: str):
        if preference not in ["email", "app"]:
            preference = "email"
        
        # SIN AWAIT
        self.users_collection.update_one(
            {"email": email},
            {"$set": {"notification_pref": preference, "email": email}},
            upsert=True
        )
        return preference

    async def _notify_organizer(self, event_id: UUID, author_name: str, content: str):
        # A. Obtener datos del evento (HTTP es async, LLEVA AWAIT)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{EVENT_SERVICE_URL}/events/{event_id}")
                if response.status_code != 200:
                    print(f"⚠️ No se pudo obtener el evento {event_id}")
                    return
                event_data = response.json()
        except Exception as e:
            print(f"❌ Error conectando con EventService: {e}")
            return

        # B. Extraer Email y Preferencias
        organizer_email = event_data.get("emailOrganizador")
        event_title = event_data.get("titulo", "Evento")

        if not organizer_email:
            print(f"⚠️ El evento '{event_title}' no tiene emailOrganizador.")
            return

        # C. Buscar preferencia (SIN AWAIT)
        user_pref_doc = self.users_collection.find_one({"email": organizer_email})
        preference = user_pref_doc.get("notification_pref", "email") if user_pref_doc else "email"

        print(f"🔔 Notificando a {organizer_email} ({preference})")

        if preference == "email":
            self._send_email_sendgrid(organizer_email, author_name, content, event_title)
        else:
            await self._save_app_notification(organizer_email, author_name, content, event_title, event_id)

    def _send_email_sendgrid(self, to_email, author_name, content, event_title):
        remitente = os.getenv('EMAIL_REMITENTE')
        api_key = os.getenv('SENDGRID_API_KEY')

        if not remitente or not api_key:
            error_msg = "Faltan credenciales: Revisa EMAIL_REMITENTE y SENDGRID_API_KEY en el .env"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)

        try:
            message = Mail(
                from_email=remitente,
                to_emails=to_email,
                subject=f'Nuevo comentario en: {event_title}',
                html_content=f'''
                    <h3>¡Tienes un nuevo comentario!</h3>
                    <p><strong>{author_name}</strong> ha comentado en tu evento <em>"{event_title}"</em>:</p>
                    <blockquote style="background: #f8f9fa; padding: 15px; border-left: 4px solid #0d6efd;">
                        "{content}"
                    </blockquote>
                '''
            )
            sg = SendGridAPIClient(api_key)
            sg.send(message)
            print(f"✅ Email enviado correctamente a {to_email}")
        except Exception as e:
            print(f"❌ Error crítico de SendGrid: {e}")
            raise e

    async def _save_app_notification(self, user_email, author_name, content, event_title, event_id):
        notification = {
            "_id": uuid4(),
            "user_email": user_email,
            "message": f"{author_name} comentó en '{event_title}': {content[:50]}...",
            "event_id": str(event_id),
            "read": False,
            "created_at": datetime.now()
        }
        # SIN AWAIT
        self.notif_collection.insert_one(notification)
        print("✅ Notificación guardada en BD con enlace correcto.")

    # --- CRUD y LISTAS (CORREGIDOS) ---
    
    async def get_notifications(self, user_email: str):
        # SIN AWAIT y usando list()
        cursor = self.notif_collection.find({"user_email": user_email}).sort("created_at", -1).limit(50)
        results = list(cursor) 
        for n in results: n["_id"] = str(n["_id"])
        return results

    async def list_comments(self, id_calendario: Optional[UUID], id_evento: Optional[UUID]):
        filtro = {}
        if id_calendario: filtro["idCalendario"] = id_calendario
        if id_evento: filtro["idEvento"] = id_evento
        
        # SIN AWAIT y usando list()
        cursor = self.comments_collection.find(filtro)
        return list(cursor) # 'to_list' falla en PyMongo síncrono

    async def get_comment(self, id: UUID):
        # SIN AWAIT
        return self.comments_collection.find_one({"_id": id})

    async def update_comment(self, id: UUID, comment_update: CommentCreate):
        data = comment_update.model_dump(exclude_unset=True)
        # SIN AWAIT
        self.comments_collection.update_one({"_id": id}, {"$set": data})
        return await self.get_comment(id)

    async def delete_comment(self, id: UUID):
        # SIN AWAIT
        self.comments_collection.delete_one({"_id": id})