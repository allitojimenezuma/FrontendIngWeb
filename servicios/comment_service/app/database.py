import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Recuperamos la URI del entorno
MONGO_URI = os.getenv("MONGODB_URI")

# Conectamos a Mongo con soporte para UUID estándar
client = MongoClient(MONGO_URI, uuidRepresentation='standard')

# Exportamos el objeto de base de datos completo 'db'
db = client['KalendasDB']