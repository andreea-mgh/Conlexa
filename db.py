import psycopg2
import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", 5432),
    "dbname": os.getenv("DB_NAME", "conlang"),
    "user": os.getenv("DB_USER", "conlexa"),
    "password": os.getenv("DB_PASSWORD", "password"),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)
