
#import cleanexisting
from database import (
    create_tables,
    populate_transactions,
    check_for_cached_vendor,
    cache_vendor,
    retrieve_description,
    update_transaction_details,
    update_transaction_category,
    retrieve_transactions,
    normalise_date
)
from csv_import import clean_description, import_transactions, normalise_vendor
from sorting import sum_categories
from ai import categorise_transaction, get_or_create_vendor
from vendor_alias_manager import get_vendor_canonical, extract_osko_payee, is_known_payee, save_known_payee
from app_state import today, last_year, last_month
import time

IGNORED_PAYMENT_METHODS = (
    "Osko Payment",
    "BPAY",
)


def main():
    create_tables()

    # transactions = import_transactions()
    # populate_transactions(transactions)
    # update_transaction_details(transactions)

    transactions = retrieve_transactions()
    print("Number of transactions:", len(transactions))
    print("First transaction:", transactions[0] if transactions else "List is empty")

    category_sums = sum_categories(transactions, last_year)
    for category, total in category_sums.items():
        print(f"{category}: ${total:,.2f}")

    assign_category_to_vendor(last_year)

    counter = 0
    for transaction in transactions:
        if not transaction.get("category"):
            print("Transaction missing category:", transaction)
            counter += 1

    print("Number of transactions missing category:", counter)


def assign_category_to_vendor(time_period=None):
    descriptions_list = retrieve_description(time_period)
    total = len(descriptions_list)

    # Track total time spent in each operation.
    timings = {
        "Vendor lookup": 0.0,
        "AI vendor identification": 0.0,
        "Category cache lookup": 0.0,
        "AI categorisation": 0.0,
        "Database update": 0.0,
    }

    
    for index, description in enumerate(descriptions_list, start=1):

        original_description = description
        payee = extract_osko_payee(original_description)

        description = clean_description(description)

        # Handle internal transfers first.
        if "internal transfer" in description.casefold():
            update_transaction_category(description, "Transfer")
            continue

        # Handle Osko payments using the ORIGINAL description.
        if payee is not None:
            print(f"\nOsko payment detected: {original_description}")
            print(f"Extracted payee: {payee}")

            if not is_known_payee(payee):
                save_known_payee(payee)

            update_transaction_category(description, "Other")
            continue

        # Check whether this exact description is a known payee.
        if is_known_payee(description):
            update_transaction_category(description, "Other")
            continue

        vendor = normalise_vendor(description)




        if any(
            vendor.casefold().startswith(method.casefold())
            for method in IGNORED_PAYMENT_METHODS
        ):
            continue

        if vendor.casefold() == "transfer":
            category = "Transfer"

            start = time.perf_counter()
            update_transaction_category(description, category)
            timings["Database update"] += time.perf_counter() - start

        else:
            # Resolve the vendor using existing aliases.
            start = time.perf_counter()
            canonical_vendor = get_vendor_canonical(vendor)
            timings["Vendor lookup"] += time.perf_counter() - start

            # Ask AI to identify the vendor only when it is unknown.
            if canonical_vendor is None:
                start = time.perf_counter()
                canonical_vendor = get_or_create_vendor(
                    vendor,
                    description
                )
                timings["AI vendor identification"] += (
                    time.perf_counter() - start
                )

            # Fall back to the normalised vendor if AI cannot identify it.
            if canonical_vendor is None:
                canonical_vendor = vendor

            # Check the category cache.
            start = time.perf_counter()
            category = check_for_cached_vendor(canonical_vendor)
            timings["Category cache lookup"] += (
                time.perf_counter() - start
            )

            # Ask AI to categorise only if the category is not cached.
            if category is None:
                start = time.perf_counter()
                category = categorise_transaction(description)
                timings["AI categorisation"] += (
                    time.perf_counter() - start
                )

                cache_vendor(canonical_vendor, category)

            # Update the transaction's category in the database.
            start = time.perf_counter()
            update_transaction_category(description, category)
            timings["Database update"] += time.perf_counter() - start

        percentage = (index / total) * 100 if total else 100
        remaining = total - index

        print(
            f"\rProgress: {index}/{total} "
            f"({percentage:.1f}%) | "
            f"Remaining: {remaining}",
            end="",
            flush=True
        )

    print("\n\n--- Timing results ---")

    for operation, elapsed in timings.items():
        print(f"{operation}: {elapsed:.2f} seconds")

    print("Categorisation complete!")


if __name__ == "__main__":
    main()
