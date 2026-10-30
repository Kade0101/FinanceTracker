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

print(classify_income())