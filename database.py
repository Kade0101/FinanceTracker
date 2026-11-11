from datetime import datetime
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "database.db"

def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def create_tables():
    print("Creating database tables...")
    connection = get_connection()
    
    connection.execute("""
        CREATE TABLE IF NOT EXISTS Vendors (
            id INTEGER PRIMARY KEY,
            vendor_name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL
        )
    """)
    
    connection.execute("""
        CREATE TABLE IF NOT EXISTS TransactionList (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            credit REAL DEFAULT 0,
            debit REAL DEFAULT 0,
            balance REAL,
            vendor TEXT,
            canonical_id INTEGER,
            category TEXT,
            cleaned_description TEXT,
            transaction_type TEXT NOT NULL DEFAULT 'Unclassified',
            FOREIGN KEY (canonical_id) REFERENCES Vendors(id)
        )
    """)


    
    connection.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_transaction
    ON TransactionList (date, description, credit, debit, balance)
""")
    
    # Add the columns to existing databases if they are missing
    existing_columns = {
        column[1]
        for column in connection.execute(
            "PRAGMA table_info(TransactionList)"
        ).fetchall()
    }
    
    if "category" not in existing_columns:
        connection.execute(
        "ALTER TABLE TransactionList ADD COLUMN category TEXT"
    )

    if "vendor" not in existing_columns:
        connection.execute(
            "ALTER TABLE TransactionList ADD COLUMN vendor TEXT"
        )

    if "cleaned_description" not in existing_columns:
        connection.execute(
            "ALTER TABLE TransactionList ADD COLUMN cleaned_description TEXT"
        )
        
    if "transaction_type" not in existing_columns:
        connection.execute("""
            ALTER TABLE TransactionList
            ADD COLUMN transaction_type TEXT NOT NULL DEFAULT 'Unclassified'
        """)
        
    if "canonical_id" not in existing_columns:
        connection.execute(
            "ALTER TABLE TransactionList ADD COLUMN canonical_id INTEGER"
        )

    connection.commit()
    connection.close()


def normalise_date(date_text):
    date_text = date_text.strip()

    for date_format in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(
                date_text, date_format
            ).date().isoformat()
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {date_text!r}")

def populate_transactions(transactions):
    connection = get_connection()

    try:
        changes_before = connection.total_changes

        for row in transactions:
            connection.execute("""
                INSERT OR IGNORE INTO TransactionList
                    (date, description, credit, debit, balance,
                     vendor, cleaned_description, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                normalise_date(row["Date"]),
                row["Description"],
                float(row["Credit"] or 0),
                float(row["Debit"] or 0),
                float(row["Balance"] or 0),
                row["Vendor"],
                row["Cleaned_Description"],
                None
            ))

        imported = connection.total_changes - changes_before
        connection.commit()
    finally:
        connection.close()

    return {
        "imported": imported,
        "duplicates_skipped": len(transactions) - imported,
    }



def update_transaction_details(transactions):
    connection = get_connection()

    try:
        updated = 0

        for row in transactions:
            cursor = connection.execute("""
                UPDATE TransactionList
                SET
                    vendor = ?,
                    cleaned_description = ?,
                    transaction_type = ?
                WHERE date = ?
                  AND description = ?
                  AND credit = ?
                  AND debit = ?
                  AND balance = ?
            """, (
                row["Vendor"],
                row["Cleaned_Description"],
                row["Transaction_Type"],
                normalise_date(row["Date"]),
                row["Description"],
                float(row["Credit"] or 0),
                float(row["Debit"] or 0),
                float(row["Balance"] or 0)
            ))

            updated += cursor.rowcount

        connection.commit()

        print(f"Updated transaction details: {updated}")

        return updated

    finally:
        connection.close()



def check_for_cached_vendor(vendor_name):
    connection = get_connection()

    try:
        cursor = connection.execute("""
            SELECT id, category
            FROM Vendors
            WHERE vendor_name = ?
        """, (vendor_name,))

        return cursor.fetchone()

    finally:
        connection.close()

def cache_vendor(vendor_name, category):
    connection = get_connection()

    try:
        connection.execute("""
            INSERT INTO Vendors (vendor_name, category)
            VALUES (?, ?)
            ON CONFLICT(vendor_name)
            DO UPDATE SET category = excluded.category
        """, (vendor_name, category))

        connection.commit()

        cursor = connection.execute("""
            SELECT id
            FROM Vendors
            WHERE vendor_name = ?
        """, (vendor_name,))

        return cursor.fetchone()[0]

    finally:
        connection.close()
def retrieve_description(start_date=None):
    connection = get_connection()
    print(f"Retrieving descriptions from {start_date}")
    if not start_date:
        cursor = connection.execute("""
            SELECT description
            FROM TransactionList
        """)
    else:
        cursor = connection.execute("""
            SELECT description
            FROM TransactionList
            WHERE date >= ?
        """, (start_date,))

    results = cursor.fetchall()
    connection.close()

    return [row[0] for row in results]

def update_transaction_category(description, category, canonical_id=None):
    connection = get_connection()

    try:
        connection.execute("""
            UPDATE TransactionList
            SET
                category = ?,
                canonical_id = COALESCE(?, canonical_id)
            WHERE cleaned_description = ?
        """, (category, canonical_id, description))

        connection.commit()

    finally:
        connection.close()

def retrieve_transactions():
    connection = sqlite3.connect("database.db")

    try:
        cursor = connection.execute("""
            SELECT category, credit, debit, date
            FROM TransactionList
            WHERE category IS NOT NULL
        """)

        return [
            {
                "category": row[0],
                "credit": row[1] or 0,
                "debit": row[2] or 0,
                "date": row[3]
            }
            for row in cursor.fetchall()
        ]
    finally:
        connection.close()
        
def get_vendor_id(vendor_name):
    connection = get_connection()

    try:
        cursor = connection.execute("""
            SELECT id
            FROM Vendors
            WHERE vendor_name = ? COLLATE NOCASE
        """, (vendor_name,))

        result = cursor.fetchone()
        return result[0] if result else None

    finally:
        connection.close()