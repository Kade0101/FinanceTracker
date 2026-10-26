
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import threading
import time

from csv_import import import_transactions
from database import (
    create_tables,
    populate_transactions,
    update_transaction_details,
)
from main import assign_category_to_vendor

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


# Progress shared between the worker thread and the status endpoint.
process_state = {
    "active": False,
    "stage": "",
    "current": 0,
    "total": 0,
    "result": None,
    "error": None,
}


def run_csv_pipeline():
    start = time.perf_counter()

    try:
        process_state["stage"] = "Reading CSV"
        transactions = import_transactions()

        process_state["stage"] = "Importing transactions"
        create_tables()
        import_stats = populate_transactions(transactions)
        update_transaction_details(transactions)

        process_state["stage"] = "Categorising transactions"

        def report_progress(current, total):
            process_state["current"] = current
            process_state["total"] = total

        categorised = assign_category_to_vendor(
            progress_callback=report_progress
        )

        process_state["result"] = {
            "rows_in_csv": len(transactions),
            "imported": import_stats["imported"],
            "duplicates_skipped": import_stats["duplicates_skipped"],
            "categorised": categorised,
            "elapsed_seconds": round(time.perf_counter() - start, 2),
        }

    except FileNotFoundError:
        process_state["error"] = (
            "TransactionList.csv not found on the server."
        )
    except Exception as exc:
        process_state["error"] = str(exc)
    finally:
        process_state["active"] = False


@app.post("/process-csv")
def process_csv():
    if process_state["active"]:
        raise HTTPException(
            status_code=409,
            detail="A CSV processing run is already in progress."
        )

    process_state.update(
        active=True,
        stage="Starting",
        current=0,
        total=0,
        result=None,
        error=None,
    )

    threading.Thread(target=run_csv_pipeline, daemon=True).start()
    return {"started": True}


@app.get("/process-csv/status")
def process_csv_status():
    return process_state


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
