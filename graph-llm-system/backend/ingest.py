"""
Data ingestion script: reads JSONL files from sap-o2c-data/ and loads into PostgreSQL.
Run this once to populate the database.
"""
import json
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "graph_system"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "sap-o2c-data")

# Map folder names -> table names (snake_case)
TABLE_MAP = {
    "sales_order_headers": "sales_order_headers",
    "sales_order_items": "sales_order_items",
    "sales_order_schedule_lines": "sales_order_schedule_lines",
    "outbound_delivery_headers": "outbound_delivery_headers",
    "outbound_delivery_items": "outbound_delivery_items",
    "billing_document_headers": "billing_document_headers",
    "billing_document_items": "billing_document_items",
    "billing_document_cancellations": "billing_document_cancellations",
    "journal_entry_items_accounts_receivable": "journal_entry_items",
    "payments_accounts_receivable": "payments",
    "business_partners": "business_partners",
    "business_partner_addresses": "business_partner_addresses",
    "customer_company_assignments": "customer_company_assignments",
    "customer_sales_area_assignments": "customer_sales_area_assignments",
    "plants": "plants",
    "products": "products",
    "product_descriptions": "product_descriptions",
    "product_plants": "product_plants",
    "product_storage_locations": "product_storage_locations",
}


def camel_to_snake(name):
    """Convert camelCase to snake_case."""
    import re
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def read_jsonl_folder(folder_path):
    """Read all JSONL files in a folder and return list of dicts."""
    records = []
    for filename in sorted(os.listdir(folder_path)):
        if not filename.endswith(".jsonl"):
            continue
        filepath = os.path.join(folder_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def infer_pg_type(value):
    """Infer PostgreSQL column type from a Python value."""
    if value is None:
        return "TEXT"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE PRECISION"
    return "TEXT"


def create_table_and_insert(conn, table_name, records):
    """Create a table from records and bulk insert."""
    if not records:
        print(f"  [SKIP] {table_name}: no records")
        return

    # Convert all keys to snake_case
    converted_records = []
    for rec in records:
        converted = {}
        for k, v in rec.items():
            col_name = camel_to_snake(k)
            # Convert None-like values
            if v == "":
                v = None
            # Convert nested dicts/lists to JSON strings
            elif isinstance(v, (dict, list)):
                v = json.dumps(v)
            converted[col_name] = v
        converted_records.append(converted)

    # Collect all unique columns across all records
    all_columns = {}
    for rec in converted_records:
        for k, v in rec.items():
            if k not in all_columns and v is not None:
                all_columns[k] = infer_pg_type(v)
    # Add any columns that were always None
    for rec in converted_records:
        for k in rec:
            if k not in all_columns:
                all_columns[k] = "TEXT"

    columns = list(all_columns.keys())
    col_types = [all_columns[c] for c in columns]

    with conn.cursor() as cur:
        # Drop and create table
        cur.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
        col_defs = ", ".join(
            f'"{col}" {typ}' for col, typ in zip(columns, col_types)
        )
        cur.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

        # Bulk insert using execute_values for speed
        from psycopg2.extras import execute_values

        # Build rows with consistent column order
        rows = []
        for rec in converted_records:
            row = tuple(rec.get(col) for col in columns)
            rows.append(row)

        placeholders = ", ".join(["%s"] * len(columns))
        col_names = ", ".join(f'"{c}"' for c in columns)
        insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES %s'

        template = f'({", ".join(["%s"] * len(columns))})'
        execute_values(cur, insert_sql, rows, template=template, page_size=500)

    conn.commit()
    print(f"  [OK] {table_name}: {len(converted_records)} records, {len(columns)} columns")


def create_indexes(conn):
    """Create indexes on foreign key columns for fast joins."""
    indexes = [
        ('sales_order_headers', 'sold_to_party'),
        ('sales_order_items', 'sales_order'),
        ('sales_order_items', 'material'),
        ('sales_order_items', 'production_plant'),
        ('sales_order_schedule_lines', 'sales_order'),
        ('outbound_delivery_items', 'delivery_document'),
        ('outbound_delivery_items', 'reference_sd_document'),
        ('outbound_delivery_items', 'plant'),
        ('billing_document_headers', 'sold_to_party'),
        ('billing_document_headers', 'accounting_document'),
        ('billing_document_items', 'billing_document'),
        ('billing_document_items', 'reference_sd_document'),
        ('billing_document_items', 'material'),
        ('billing_document_cancellations', 'billing_document'),
        ('billing_document_cancellations', 'cancelled_billing_document'),
        ('journal_entry_items', 'reference_document'),
        ('journal_entry_items', 'customer'),
        ('journal_entry_items', 'accounting_document'),
        ('payments', 'customer'),
        ('payments', 'invoice_reference'),
        ('payments', 'sales_document'),
        ('business_partner_addresses', 'business_partner'),
        ('customer_company_assignments', 'customer'),
        ('customer_sales_area_assignments', 'customer'),
        ('product_descriptions', 'product'),
        ('product_plants', 'product'),
        ('product_plants', 'plant'),
        ('product_storage_locations', 'product'),
        ('product_storage_locations', 'plant'),
    ]

    with conn.cursor() as cur:
        for table, column in indexes:
            idx_name = f"idx_{table}_{column}"
            try:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table}" ("{column}")')
            except Exception as e:
                print(f"  [WARN] Index {idx_name}: {e}")
                conn.rollback()
                continue
    conn.commit()
    print(f"  [OK] Created {len(indexes)} indexes")


def main():
    print("=" * 60)
    print("SAP O2C Data Ingestion → PostgreSQL")
    print("=" * 60)

    # Connect
    print(f"\nConnecting to PostgreSQL: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("  [OK] Connected\n")
    except Exception as e:
        print(f"  [ERROR] Could not connect: {e}")
        print(f"\n  Make sure the database '{DB_CONFIG['dbname']}' exists.")
        print(f"  Run: CREATE DATABASE {DB_CONFIG['dbname']};")
        sys.exit(1)

    # Ingest each folder
    print("Ingesting data tables:")
    for folder_name, table_name in TABLE_MAP.items():
        folder_path = os.path.join(DATA_DIR, folder_name)
        if not os.path.isdir(folder_path):
            print(f"  [SKIP] {folder_name}: folder not found")
            continue
        records = read_jsonl_folder(folder_path)
        create_table_and_insert(conn, table_name, records)

    # Create indexes
    print("\nCreating indexes:")
    create_indexes(conn)

    # Print summary
    print("\n" + "=" * 60)
    print("Ingestion complete! Table summary:")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        for t in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            count = cur.fetchone()[0]
            print(f"  {t}: {count} rows")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
