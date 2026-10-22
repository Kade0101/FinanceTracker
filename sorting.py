
from datetime import date


today = date.today()
one_year_ago = today.replace(year=today.year - 1) #leap year edge case not handled


def sum_categories(transactions):
    category_sums = {}

    for transaction in transactions:
        category = transaction.get("category")

        if category:
            credit = float(transaction.get("credit") or 0)
            debit = float(transaction.get("debit") or 0)

            category_sums[category] = (
                category_sums.get(category, 0) + debit - credit
            )
    category_sums = dict(sorted(category_sums.items(), key=lambda item: item[1], reverse=True))
    return category_sums
