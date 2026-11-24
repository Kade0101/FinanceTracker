import sqlite3

def classify_income():
    query = """
SELECT
    vendor,
    COUNT(*) AS payment_count,
    COUNT(DISTINCT strftime('%Y-%m', date)) AS months_paid,
    ROUND(SUM(credit), 2) AS total_received,
    ROUND(AVG(credit), 2) AS average_payment
FROM TransactionList
WHERE credit >= 1
  AND (
      description LIKE '%Salary%'
      OR description LIKE '%Wages%'
      OR description LIKE '%Payroll%'
  )
GROUP BY vendor
ORDER BY total_received DESC;
    """
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    connection.close()
    return rows
def classify_subscriptions():
    query = """
WITH daily_vendor_totals AS (
    SELECT 
        LOWER(TRIM(vendor)) AS vendor_key,
        debit AS amount_key,
        date
    FROM TransactionList
    WHERE debit < 0 
      AND vendor IS NOT NULL 
      AND TRIM(vendor) <> ''
    GROUP BY LOWER(TRIM(vendor)), debit, date
),
ordered_transactions AS (
    SELECT 
        vendor_key,
        amount_key,
        julianday(date) - julianday(
            LAG(date) OVER (PARTITION BY vendor_key, amount_key ORDER BY date)
        ) AS days_since_last
    FROM daily_vendor_totals
),
recurring_vendors AS (
    SELECT vendor_key, amount_key
    FROM ordered_transactions
    WHERE days_since_last IS NOT NULL
    GROUP BY vendor_key, amount_key
    HAVING COUNT(*) >= 3
       AND AVG(days_since_last) BETWEEN 25 AND 45
       AND AVG(CASE WHEN days_since_last BETWEEN 25 AND 35 THEN 1.0 ELSE 0.0 END) >= 0.70
       AND MAX(days_since_last) <= 70
)
SELECT 
    MIN(t.vendor) AS vendor,
    ABS(r.amount_key) AS fixed_amount,
    COUNT(*) AS transaction_count,
    ROUND(SUM(ABS(t.debit)), 2) AS total_debit,
    MAX(t.date) AS last_seen_date,
    GROUP_CONCAT(DISTINCT t.category) AS categories
FROM TransactionList AS t
JOIN recurring_vendors AS r 
  ON LOWER(TRIM(t.vendor)) = r.vendor_key
 AND t.debit = r.amount_key
WHERE t.debit < 0
GROUP BY r.vendor_key, r.amount_key
ORDER BY total_debit DESC;
    """
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    connection.close()
    return rows
#print(classify_income())
for vendor, _, _, total, last_seen,_ in classify_subscriptions():
    print(vendor, total, last_seen)
