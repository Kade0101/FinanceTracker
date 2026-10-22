
import cleanexisting
from database import create_tables, populate_transactions,check_for_cached_vendor, cache_vendor, retrieve_description, update_transaction_details, update_transaction_category, retrieve_transactions
from csv_import import clean_description, import_transactions, normalise_vendor
from sorting import sum_categories
from ai import categorise_transaction

IGNORED_PAYMENT_METHODS = (
    "Osko Payment",
    "BPAY",
    "Internal Transfer"
)
def main():
    create_tables()
    #transactions = import_transactions()
    #populate_transactions(transactions) #Imports transactions from CSV into the database
    #update_transaction_details(transactions)
    transactions = retrieve_transactions()
    category_sums = sum_categories(transactions)
    for category, total in category_sums.items():
        print(f"{category}: ${total:,.2f}")

    assign_category_to_vendor()
    


def assign_category_to_vendor():
    descriptions_list = retrieve_description()
    total = len(descriptions_list)

    for index, description in enumerate(descriptions_list, start=1):
        description = clean_description(description)
        vendor = normalise_vendor(description)

        if any(
            vendor.casefold().startswith(method.casefold())
            for method in IGNORED_PAYMENT_METHODS
        ):
            continue
        else:
            category = check_for_cached_vendor(vendor)

            if category is None:
                category = categorise_transaction(description)
                cache_vendor(vendor, category)

            update_transaction_category(description, category)

        percentage = (index / total) * 100 if total else 100
        remaining = total - index

        print(
            f"\rProgress: {index}/{total} "
            f"({percentage:.1f}%) | "
            f"Remaining: {remaining}",
            end="",
            flush=True
        )

    print("\nCategorisation complete!")

            
if __name__ == "__main__":
    main()


