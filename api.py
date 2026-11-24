
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sqlite3
import threading
import time
from pydantic import BaseModel

from csv_import import import_transactions
from database import (
    create_tables,
    populate_transactions,
    update_transaction_details,
)
from categorisation import assign_category_to_vendor

app = FastAPI()


class VendorCategorySelection(BaseModel):
    vendor_id: int
    category: str


class VendorCategoryUpdateRequest(BaseModel):
    selections: list[VendorCategorySelection]

# Allow the React frontend to communicate with this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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


def classify_cash_flow(transaction):
    description = (transaction["description"] or "").casefold()
    transaction_type = (
        transaction["transaction_type"] or ""
    ).casefold()

    if (
        transaction_type == "internal transfer"
        or "internal transfer" in description
    ):
        return "internal_transfer"

    category = (transaction["category"] or "").casefold()
    if category in ("investment", "investments"):
        return "investment"

    amount = (transaction["credit"] or 0) + (transaction["debit"] or 0)
    return "income" if amount > 0 else "expense"


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

        categorised = asyncio.run(
            assign_category_to_vendor(progress_callback=report_progress)
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
                cleaned_description,
                transaction_type
            FROM TransactionList
            ORDER BY date DESC, id DESC
        """)

        return [
            {
                **dict(row),
                "cash_flow_type": classify_cash_flow(row),
            }
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()

@app.get("/vendors/review")
def get_vendors_for_review():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row

    try:
        vendors = connection.execute("""
            SELECT
                v.id,
                v.vendor_name,
                COUNT(t.id) AS transaction_count,
                SUM(ABS(t.debit)) AS total_spent

            FROM TransactionList t

            JOIN Vendors v
                ON t.canonical_id = v.id

            WHERE v.category IN ('Other', 'Transfer')
              AND t.debit < 0

            GROUP BY v.id, v.vendor_name

            ORDER BY total_spent DESC

            LIMIT 10
        """).fetchall()

        categories = connection.execute("""
            SELECT category
            FROM (
                SELECT DISTINCT category
                FROM Vendors
                WHERE category IS NOT NULL
                  AND category != ''
                  AND category != 'Other'

                UNION

                SELECT 'Investments'
            )
            ORDER BY category
        """).fetchall()

        return {
            "vendors": [dict(row) for row in vendors],
            "categories": [row["category"] for row in categories]
        }

    finally:
        connection.close()
        
@app.post("/vendors/review")
def save_vendor_review(request: VendorCategoryUpdateRequest):
    connection = sqlite3.connect("database.db")

    try:
        connection.execute("BEGIN")
        vendor_ids = [selection.vendor_id for selection in request.selections]

        if len(vendor_ids) != len(set(vendor_ids)):
            raise ValueError("Duplicate vendor IDs in request")
        
        if not request.selections:
            raise ValueError("No vendor categories were provided")

        # Retrieve all valid categories once.
        categories = {
            row[0]
            for row in connection.execute("""
                SELECT category
                FROM (
                    SELECT DISTINCT category
                    FROM Vendors
                    WHERE category IS NOT NULL
                      AND category != ''
                      AND category != 'Other'

                    UNION

                    SELECT 'Investments'
                )
            """).fetchall()
        }

        for selection in request.selections:
            vendor_id = selection.vendor_id
            category = selection.category.strip()

            if category not in categories:
                raise ValueError(f"Invalid category: {category}")

            cursor = connection.execute("""
                UPDATE Vendors
                SET category = ?
                WHERE id = ?
                  AND category IN ('Other', 'Transfer')
            """, (category, vendor_id))

            if cursor.rowcount == 0:
                raise ValueError(
                    f"Vendor {vendor_id} no longer requires review"
                )

            connection.execute("""
                UPDATE TransactionList
                SET category = ?
                WHERE canonical_id = ?
            """, (category, vendor_id))

        connection.commit()

        return {
            "success": True,
            "updated_vendors": len(request.selections)
        }

    except ValueError as error:
        connection.rollback()
        raise HTTPException(status_code=400, detail=str(error))

    except Exception:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to save vendor categories"
        )

    finally:
        connection.close()
