# backend/fastapi_app/db/connection.py
import psycopg2
from psycopg2.extras import RealDictCursor
from desktop_app.config import POSTGRES_CONFIG
from pymongo import MongoClient
from desktop_app.config import MONGO_CONFIG

def get_pg_connection():
    """
    Returns a new psycopg2 connection using POSTGRES_CONFIG.
    Keep behavior consistent with existing design (caller manages cursor/closing).
    """
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    return conn

def get_mongo_client():
    client = MongoClient(MONGO_CONFIG['host'], MONGO_CONFIG['port'])
    return client