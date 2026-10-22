    
    connection.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_transaction
    ON TransactionList (date, description, credit, debit, balance)
""")