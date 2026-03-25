"""
PostgreSQL database connection and query utilities.
"""
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "graph_system"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}


def get_connection():
    """Get a new PostgreSQL connection."""
    return psycopg2.connect(**DB_CONFIG)


def execute_query(sql, params=None, fetch=True):
    """Execute a SQL query and return results as list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch:
                rows = cur.fetchall()
                return [dict(row) for row in rows]
            conn.commit()
            return []
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def execute_query_safe(sql, params=None, timeout_seconds=10):
    """Execute a SQL query with a timeout. Returns (results, error)."""
    conn = get_connection()
    try:
        conn.autocommit = False
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SET statement_timeout = '{timeout_seconds * 1000}'")
            cur.execute(sql, params)
            rows = cur.fetchall()
            conn.rollback()  # read-only, rollback any implicit transaction
            return [dict(row) for row in rows], None
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        conn.close()


def get_schema_info():
    """Get all table names, columns, and types from the database."""
    sql = """
        SELECT 
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """
    rows = execute_query(sql)
    schema = {}
    for row in rows:
        table = row["table_name"]
        if table not in schema:
            schema[table] = []
        schema[table].append({
            "column": row["column_name"],
            "type": row["data_type"],
            "nullable": row["is_nullable"] == "YES",
        })
    return schema


def get_table_counts():
    """Get row counts for all tables."""
    schema = get_schema_info()
    counts = {}
    for table in schema:
        rows = execute_query(f'SELECT COUNT(*) as cnt FROM "{table}"')
        counts[table] = rows[0]["cnt"]
    return counts
