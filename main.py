
#import cleanexisting
from database import create_tables, populate_transactions,check_for_cached_vendor, cache_vendor, retrieve_description, update_transaction_details, update_transaction_category, retrieve_transactions, normalise_date
from csv_import import clean_description, import_transactions, normalise_vendor
from sorting import sum_categories
from ai import categorise_transaction
from app_state import today, last_year, last_month

IGNORED_PAYMENT_METHODS = (
    "Osko Payment",
    "BPAY", #i dont think this is doing anything depending on where bpay is in the description
)



def main():
    create_tables()
    #transactions = import_transactions()
    #populate_transactions(transactions) #Imports transactions from CSV into the database
    #update_transaction_details(transactions)
    
    transactions = retrieve_transactions()
    print("Number of transactions:", len(transactions))
    print("First transaction:", transactions[0] if transactions else "List is empty")
    category_sums = sum_categories(transactions)
    for category, total in category_sums.items():
        print(f"{category}: ${total:,.2f}")
    assign_category_to_vendor()
    counter = 0
    for transaction in transactions:
        if not transaction.get("category"):
            print("Transaction missing category:", transaction)
            counter += 1
    print("Number of transactions missing category:", counter)
    


def assign_category_to_vendor(time_period=None):
    descriptions_list = retrieve_description(time_period)
    total = len(descriptions_list)

    for index, description in enumerate(descriptions_list, start=1):
 
        description = clean_description(description)
        vendor = normalise_vendor(description)

        if any(
            vendor.casefold().startswith(method.casefold())
            for method in IGNORED_PAYMENT_METHODS
        ):
            continue
        
        if vendor.casefold() == "transfer":
            category = "Transfer"
            update_transaction_category(description, category)
            
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


