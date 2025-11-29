import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def enviar_notificacion_email(destinatario: str, nombre_evento: str, contenido_comentario: str):
    """
    Función auxiliar para enviar correos usando la API de SendGrid.
    Se conecta al archivo .env para leer las claves.
    """
    api_key = os.environ.get('SENDGRID_API_KEY')
    remitente = os.environ.get('EMAIL_REMITENTE')

    # Validación básica de seguridad
    if not api_key or not remitente:
        print("⚠️ ALERTA: Faltan SENDGRID_API_KEY o EMAIL_REMITENTE en el archivo .env")
        return False

    # Diseño del correo (HTML)
    cuerpo_html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #0d6efd;">🔔 Nueva actividad en tu evento</h2>
        <p>Hola, el evento <strong>{nombre_evento}</strong> ha recibido un nuevo comentario:</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #0d6efd; margin: 20px 0;">
            <p style="margin: 0; font-style: italic; color: #555;">"{contenido_comentario}"</p>
        </div>
        
        <p style="font-size: 12px; color: #888;">
            Has recibido esto porque eres el organizador de este evento en Kalendas.
        </p>
    </div>
    """

    mensaje = Mail(
        from_email=remitente,
        to_emails=destinatario,
        subject=f'Nuevo comentario en: {nombre_evento}',
        html_content=cuerpo_html
    )

    try:
        sg = SendGridAPIClient(api_key)
        respuesta = sg.send(mensaje)
        print(f"📧 [SendGrid] Correo enviado a {destinatario}. Status: {respuesta.status_code}")
        return True
    except Exception as e:
        print(f"❌ [SendGrid] Error enviando correo: {str(e)}")
        return False