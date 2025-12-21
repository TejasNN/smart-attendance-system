# backend/fastapi_app/db/connection.py
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from backend.fastapi_app.core.config import settings

def get_pg_connection():
    
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        cursor_factory=RealDictCursor
    )
    return conn

def get_mongo_client():
    client = MongoClient(settings.MONGO_URI)
    return client