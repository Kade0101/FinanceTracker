
from database import (
    create_tables,
    populate_transactions,
    check_for_cached_vendor,
    cache_vendor,
    retrieve_description,
    update_transaction_details,
    update_transaction_category,
    retrieve_transactions,
)

from csv_import import (
    clean_description,
    import_transactions,
    normalise_vendor,
    strip_emojis,
)

from sorting import sum_categories, top_vendors_by_category

from ai import (
    categorise_transaction_async,
    get_or_create_vendor_async,
)

from vendor_alias_manager import (
    get_vendor_canonical,
    extract_osko_payee,
    is_known_payee,
    save_known_payee,
)

import time
import sys
import asyncio


# Ensure console output supports UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="backslashreplace"
    )

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="backslashreplace"
    )

eligible_for_review = []

def main():
    create_tables()

    transactions = import_transactions()
    populate_transactions(transactions)
    update_transaction_details(transactions)
    eligible_for_review.clear() # Reset the list of vendors eligible for review.

    # Run the categorisation process.
    asyncio.run(assign_category_to_vendor())

    # Retrieve transactions again after categorisation.
    transactions = retrieve_transactions()

    print("\nNumber of categorised transactions:", len(transactions))

    category_sums = sum_categories(transactions)

    for category, total in category_sums.items():
        print(f"{category}: ${total:,.2f}")

    print("\nTop vendors by category:")

    top_vendors_by_category()


async def assign_category_to_vendor(time_period=None, progress_callback=None):

    descriptions_list = retrieve_description(time_period)

    total = len(descriptions_list)
    categorised = 0

    # Track time spent in each operation.
    timings = {
        "Vendor lookup": 0.0,
        "AI vendor identification": 0.0,
        "Category cache lookup": 0.0,
        "AI categorisation": 0.0,
        "Database update": 0.0,
    }

    for index, original_description in enumerate(descriptions_list, start=1):

        if progress_callback:
            progress_callback(index, total)

        # Repair encoding issues and remove emojis.
        description = strip_emojis(original_description)

        # Extract Osko payee before cleaning the description.
        payee = extract_osko_payee(description)

        # Clean the transaction description.
        description = clean_description(description)

        # Initialise values for this transaction.
        canonical_id = None
        canonical_vendor = None

        # Handle internal transfers first.
        if "internal transfer" in description.casefold():

            category = "Transfer"

        # Handle Osko payments.
        elif payee is not None:

            if not is_known_payee(payee):
                save_known_payee(payee)

            category = "Other"

        else:

            vendor = normalise_vendor(description)   
            # Resolve the vendor using existing aliases.
            start = time.perf_counter()

            canonical_vendor = get_vendor_canonical(vendor)

            timings["Vendor lookup"] += (
                time.perf_counter() - start
            )

            # Ask AI to identify the vendor only when unknown.
            if canonical_vendor is None:

                start = time.perf_counter()

                canonical_vendor = await get_or_create_vendor_async(
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

            vendor_record = check_for_cached_vendor(canonical_vendor)

            timings["Category cache lookup"] += (
                time.perf_counter() - start
            )

            # Ask AI to categorise only if the vendor is not cached.
            if vendor_record is None:

                start = time.perf_counter()

                category = await categorise_transaction_async(description)

                timings["AI categorisation"] += (
                    time.perf_counter() - start
                )

                # Save the vendor and retrieve its canonical database ID.
                canonical_id = cache_vendor(
                    canonical_vendor,
                    category
                )

            else:

                # Reuse the existing canonical ID and category.
                canonical_id, category = vendor_record

            print(
                f"\nVendor: {vendor} | "
                f"Canonical: {canonical_vendor} | "
                f"ID: {canonical_id} | "
                f"Category: {category}"
            )

        # Update the transaction regardless of whether the vendor
        # was cached, newly categorised, a transfer, or an Osko payment.
        start = time.perf_counter()

        update_transaction_category(
            description,
            category,
            canonical_id
        )

        timings["Database update"] += (
            time.perf_counter() - start
        )

        categorised += 1

        # Display progress.
        percentage = (index / total) * 100 if total else 100
        remaining = total - index

        print(
            f"\rProgress: {index}/{total} "
            f"({percentage:.1f}%) | "
            f"Remaining: {remaining}",
            end="",
            flush=True
        )

    # Display timing results after processing all transactions.
    print("\n\n--- Timing results ---")

    for operation, elapsed in timings.items():
        print(f"{operation}: {elapsed:.2f} seconds")

    print(f"\nCategorisation complete! {categorised} transactions processed.")

    return categorised


#if __name__ == "__main__":
    #main()
