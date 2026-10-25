from datetime import datetime
import sqlite3


def create_tables():
    connection = sqlite3.connect("database.db")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS TransactionList (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            credit REAL DEFAULT 0,
            debit REAL DEFAULT 0,
            balance REAL,
            vendor TEXT,
            category TEXT,
            cleaned_description TEXT
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS Vendors (
            id INTEGER PRIMARY KEY,
            vendor_name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL
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
    connection = sqlite3.connect("database.db")

    try:
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

        connection.commit()
    finally:
        connection.close()



def update_transaction_details(transactions):
    connection = sqlite3.connect("database.db")

    try:
        for row in transactions:
            connection.execute("""
                UPDATE TransactionList
                SET vendor = ?,
                    cleaned_description = ?
                WHERE date = ?
                  AND description = ?
                  AND credit = ?
                  AND debit = ?
                  AND balance = ?
            """, (
                row["Vendor"],
                row["Cleaned_Description"],
                normalise_date(row["Date"]),
                row["Description"],
                float(row["Credit"] or 0),
                float(row["Debit"] or 0),
                float(row["Balance"] or 0)
            ))

        connection.commit()
    finally:
        connection.close()



def check_for_cached_vendor(vendor_name):
    connection = sqlite3.connect("database.db")
    cursor = connection.execute("""
        SELECT category
        FROM Vendors
        WHERE vendor_name = ?
    """, (vendor_name,))
    result = cursor.fetchone()
    connection.close()
    return result[0] if result else None

def cache_vendor(vendor_name, category):
    connection = sqlite3.connect("database.db")
    connection.execute("""
        INSERT OR REPLACE INTO Vendors (vendor_name, category)
        VALUES (?, ?)
    """, (vendor_name, category))
    connection.commit()
    connection.close()
print("Database created successfully!")

def retrieve_description(start_date=None):
    connection = sqlite3.connect("database.db")
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

def update_transaction_category(description, category):
    connection = sqlite3.connect("database.db")

    try:
        connection.execute("""
            UPDATE TransactionList
            SET category = ?
            WHERE cleaned_description = ?
        """, (category, description))

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
