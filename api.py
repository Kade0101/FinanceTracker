
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

# Allow the React frontend to communicate with this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "FinanceTracker API is running"}


@app.get("/transactions")
def get_transactions():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.execute("""
            SELECT
                id,
                date,
                description,
                credit,
                debit,
                balance,
                vendor,
                category,
                cleaned_description
            FROM TransactionList
            ORDER BY date DESC, id DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()
