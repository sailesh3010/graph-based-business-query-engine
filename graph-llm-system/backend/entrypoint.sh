#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('DB_NAME', 'graph_system'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '')
    )
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  echo "Database is unavailable - sleeping 2s"
  sleep 2
done

echo "PostgreSQL is up - checking if database needs initialization..."

TABLE_COUNT=$(python -c "
import psycopg2, os
conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'db'),
    port=int(os.getenv('DB_PORT', 5432)),
    dbname=os.getenv('DB_NAME', 'graph_system'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', '')
)
cur = conn.cursor()
cur.execute(\"SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'\")
print(cur.fetchone()[0])
")

if [ "$TABLE_COUNT" -eq "0" ]; then
    echo "Database is empty. Running initial O2C data ingestion..."
    python ingest.py
else
    echo "Database already contains $TABLE_COUNT tables. Skipping ingestion."
fi

echo "Starting FastAPI server..."
exec "$@"
