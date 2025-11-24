from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from dotenv import load_dotenv
import os
import uuid # Aseguramos que uuid esté importado

# Cargar variables de entorno desde el archivo .env
load_dotenv()

uri = os.getenv('MONGODB_URI')

# --- Conexión a MongoDB ---
# Aseguramos que la representación de UUID sea 'standard'
client = MongoClient(uri, server_api=ServerApi('1'), uuidRepresentation='standard')
db = client['KalendasDB']

try:
    # Eliminamos las colecciones si ya existen para empezar desde cero.
    print("\nLimpiando colecciones antiguas...")
    db.drop_collection('calendarios')
    db.drop_collection('eventos')
    db.drop_collection('comentarios')
    print("🧹 Colecciones 'calendarios', 'eventos' y 'comentarios' eliminadas.")

    # Obtenemos las colecciones (se crearán automáticamente al insertar datos)
    calendarios_collection = db['calendarios']
    eventos_collection = db['eventos']
    comentarios_collection = db['comentarios']

    # --- Creación de Datos de Ejemplo ---
    print("\nGenerando datos de ejemplo...")

    # Generamos los UUIDs para los IDs
    calendario_principal_id = uuid.uuid4()
    sub_calendario_id = uuid.uuid4()
    otro_calendario_id = uuid.uuid4()

    # 1. Insertar Calendarios
    calendarios_collection.insert_many([
        {
            "_id": calendario_principal_id,
            "titulo": "Calendario Principal de la Ciudad",
            "organizador": "Ayuntamiento Central",
            "palabras_clave": ["ciudad", "eventos", "público"],
            "es_publico": True,
            "idCalendarioPadre": None
        },
        {
            "_id": sub_calendario_id,
            "titulo": "Eventos Deportivos",
            "organizador": "Concejalía de Deportes",
            "palabras_clave": ["deporte", "competición"],
            "es_publico": True,
            "idCalendarioPadre": calendario_principal_id
        },
        {
            "_id": otro_calendario_id,
            "titulo": "Agenda Cultural Privada",
            "organizador": "Centro Cultural Independiente",
            "palabras_clave": ["cultura", "exposición", "música"],
            "es_publico": False,
            "idCalendarioPadre": None
        }
    ])
    print("✅ 3 calendarios de ejemplo insertados.")

    # 2. Insertar Eventos
    evento_maraton_id = uuid.uuid4()
    evento_noche_blanco_id = uuid.uuid4()
    
    eventos_collection.insert_many([
        {
            "_id": evento_maraton_id,
            "idCalendario": sub_calendario_id,
            "titulo": "Maratón de la Ciudad",
            "horaComienzo": datetime(2025, 11, 15, 9, 0, 0),
            "duracionMinutos": 240,
            "lugar": "Salida desde el Estadio Municipal",
            "organizador": "Concejalía de Deportes",
            "contenidoAdjunto": {
                "imagenes": [], "archivos": [], "mapa": {"latitud": 36.7213, "longitud": -4.4214}
            }
        },
        {
            "_id": evento_noche_blanco_id,
            "idCalendario": calendario_principal_id,
            "titulo": "Noche en Blanco",
            "horaComienzo": datetime(2025, 10, 26, 20, 0, 0),
            "duracionMinutos": 360,
            "lugar": "Varios lugares en el centro",
            "organizador": "Ayuntamiento Central",
            "contenidoAdjunto": {"imagenes": ["https://ejemplo.com/noche_en_blanco.jpg"], "archivos": [], "mapa": None}
        }
    ])
    print("✅ 2 eventos de ejemplo insertados.")

    # 3. Insertar Comentarios
    comentarios_collection.insert_many([
        {
            "_id": uuid.uuid4(),
            "contenido": "¡Excelente maratón! Muy bien organizado y el recorrido estuvo perfecto.",
            "idCalendario": None,
            "idEvento": evento_maraton_id,
            "fechaCreacion": datetime(2025, 11, 16, 10, 30, 0)
        },
        {
            "_id": uuid.uuid4(),
            "contenido": "Gran iniciativa de la ciudad. Esperamos más eventos así.",
            "idCalendario": calendario_principal_id,
            "idEvento": None,
            "fechaCreacion": datetime(2025, 10, 20, 15, 45, 0)
        },
        {
            "_id": uuid.uuid4(),
            "contenido": "La Noche en Blanco fue increíble, muchas actividades culturales.",
            "idCalendario": None,
            "idEvento": evento_noche_blanco_id,
            "fechaCreacion": datetime(2025, 10, 27, 9, 15, 0)
        },
        {
            "_id": uuid.uuid4(),
            "contenido": "Me encanta este calendario deportivo, tiene eventos muy variados.",
            "idCalendario": sub_calendario_id,
            "idEvento": None,
            "fechaCreacion": datetime(2025, 11, 5, 12, 0, 0)
        }
    ])
    print("✅ 4 comentarios de ejemplo insertados.")

    print("\n🎉 Base de datos poblada con éxito.")

except Exception as e:
    print(f"❌ Error al insertar los datos: {e}")

finally:
    # Cerramos la conexión al finalizar
    client.close()
    print("\nConexión a MongoDB cerrada.")