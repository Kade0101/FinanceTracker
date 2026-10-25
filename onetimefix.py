import sqlite3
from datetime import datetime

connection = sqlite3.connect("database.db")
cursor = connection.cursor()

try:
    cursor.execute("BEGIN")

    cursor.execute("""
        SELECT rowid, date
        FROM TransactionList
        WHERE date IS NOT NULL
    """)

    rows = cursor.fetchall()

    for rowid, date_text in rows:
        converted_date = datetime.strptime(
            date_text, "%d/%m/%Y"
        ).date().isoformat()

        cursor.execute("""
            UPDATE TransactionList
            SET date = ?
            WHERE rowid = ?
        """, (converted_date, rowid))

    connection.commit()
    print(f"Successfully converted {len(rows)} dates.")

except Exception:
    connection.rollback()
    raise

finally:
    connection.close()