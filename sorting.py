
from datetime import date

def sum_categories(transactions, time_period=None):
    category_sums = {}

    for transaction in transactions:
        transaction_date = transaction.get("date")
        
        if not transaction_date:
            print ("Transaction missing date, skipping.", transaction)
            continue

        transaction_date = date.fromisoformat(transaction_date)
        if time_period is not None:
            if transaction_date < time_period:
                continue

        category = transaction.get("category")
        
        if category == "Transfer":
            continue
        if category:
            credit = float(transaction.get("credit") or 0)
            debit = float(transaction.get("debit") or 0)

            category_sums[category] = (
                category_sums.get(category, 0) + debit - credit
            )

    category_sums = dict(
        sorted(
            category_sums.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )

    return category_sums
