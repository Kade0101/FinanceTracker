
from datetime import date
import sqlite3


def sum_categories(transactions, time_period=None):
    category_sums = {}

    for transaction in transactions:
        transaction_date = transaction.get("date")

        if not transaction_date:
            print("Transaction missing date, skipping.", transaction)
            continue

        transaction_date = date.fromisoformat(transaction_date)

        if time_period is not None and transaction_date < time_period:
            continue

        category = transaction.get("category")

        if not category or category == "Transfer":
            continue

        credit = float(transaction.get("credit") or 0)
        debit = float(transaction.get("debit") or 0)

        category_sums[category] = (
            category_sums.get(category, 0) + credit + debit
        )

    return dict(
        sorted(
            category_sums.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )


def top_vendors_by_category2(limit=3):
    query = """
    WITH VendorSpending AS (
        SELECT
            category,
            vendor,
            SUM(ABS(debit)) AS total_spent
        FROM TransactionList
        WHERE debit < 0
          AND vendor IS NOT NULL
          AND category IS NOT NULL
          AND category != 'Transfer'
        GROUP BY category, vendor
    ),
    RankedVendors AS (
        SELECT
            category,
            vendor,
            total_spent,
            ROW_NUMBER() OVER (
                PARTITION BY category
                ORDER BY total_spent DESC
            ) AS vendor_rank
        FROM VendorSpending
    )
    SELECT category, vendor, total_spent, vendor_rank
    FROM RankedVendors
    WHERE vendor_rank <= ?
    ORDER BY category, vendor_rank;
    """

    conn = sqlite3.connect("database.db")

    try:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        current_category = None

        for category, vendor, total_spent, rank in rows:
            if category != current_category:
                current_category = category
                print(f"\n--- {category} ---")

            print(f"{rank}. {vendor}: ${total_spent:,.2f}")

    finally:
        conn.close()




def top_vendors_by_category(limit=3):
    query = """
        WITH VendorSpending AS (
            SELECT
                t.category,
                v.vendor_name AS canonical_vendor,
                COUNT(t.id) AS transaction_count,
                SUM(ABS(t.debit)) AS total_spent
            FROM TransactionList t
            JOIN Vendors v
                ON t.canonical_id = v.id
            WHERE t.debit < 0
              AND t.category IS NOT NULL
              AND t.category != 'Transfer'
            GROUP BY t.category, v.id, v.vendor_name
        ),
        RankedVendors AS (
            SELECT
                category,
                canonical_vendor,
                transaction_count,
                total_spent,
                ROW_NUMBER() OVER (
                    PARTITION BY category
                    ORDER BY total_spent DESC
                ) AS vendor_rank
            FROM VendorSpending
        )
        SELECT
            category,
            canonical_vendor,
            transaction_count,
            total_spent,
            vendor_rank
        FROM RankedVendors
        WHERE vendor_rank <= ?
        ORDER BY category, vendor_rank;
    """

    conn = sqlite3.connect("database.db")

    try:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        current_category = None

        for category, vendor, transaction_count, total_spent, rank in rows:
            if category != current_category:
                current_category = category
                print(f"\n--- {category} ---")

            print(
                f"{rank}. {vendor}: ${total_spent:,.2f} "
                f"({transaction_count} transactions)"
            )

    finally:
        conn.close()
        
def top_significant_unnassigned_vendors(limit=5):
    query = """
        SELECT 
            Vendors.id,
            Vendors.vendor_name,
            Vendors.category,
            COUNT(TransactionList.id) AS transaction_count,
            SUM(ABS(TransactionList.debit)) AS total_spent

        FROM TransactionList

        JOIN Vendors
            ON TransactionList.canonical_id = Vendors.id 

        WHERE Vendors.category = 'Other'

        GROUP BY Vendors.id, Vendors.vendor_name, Vendors.category

        ORDER BY total_spent DESC
        LIMIT 10
    """
    

    conn = sqlite3.connect("database.db")

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        print(rows)
    finally:
        conn.close()