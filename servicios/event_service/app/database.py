from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from dotenv import load_dotenv
import os


load_dotenv()

uri = os.getenv('MONGODB_URI')
client = MongoClient(uri, server_api=ServerApi('1'), uuidRepresentation='standard')
db = client['KalendasDB']
eventos_collection = db['eventos']