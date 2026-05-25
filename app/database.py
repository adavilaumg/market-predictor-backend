from pymongo import MongoClient 
import certifi 
import os 
from dotenv import load_dotenv 
from pathlib import Path 
 
# Esta línea asegura que estás cargando desde el archivo correcto 
env_path = Path(__file__).parent / '.env' 
load_dotenv(dotenv_path=env_path) 
 
client = MongoClient( 
    os.getenv("MONGODB_URI"), 
    tlsCAFile=certifi.where() 
) 
 
db = client["churn_db"] 
collection = db["predictions"] 