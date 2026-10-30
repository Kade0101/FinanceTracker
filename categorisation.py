import time
from database import (
    retrieve_description,
    update_transaction_category,
    check_for_cached_vendor,
    cache_vendor
)
from csv_import import clean_description, normalise_vendor
from ai import categorise_transaction, get_or_create_vendor
from vendor_alias_manager import (
    get_vendor_canonical,
    extract_osko_payee,
    is_known_payee,
    save_known_payee
)
IGNORED_PAYMENT_METHODS = (
    "Osko Payment",
    "BPAY",
)

def assign_category_to_vendor(time_period=None, progress_callback=None):
    descriptions_list = retrieve_description(time_period)
    total = len(descriptions_list)
    categorised = 0

    # Track total time spent in each operation.
    timings = {
        "Vendor lookup": 0.0, # Time spent looking up vendors in the database
        "AI vendor identification": 0.0, # Time spent identifying vendors using AI
        "Category cache lookup": 0.0, # Time spent looking up categories in the cache
        "AI categorisation": 0.0, # Time spent categorising transactions using AI
        "Database update": 0.0, # Time spent updating the database with new categories
    }

    
    for index, description in enumerate(descriptions_list, start=1):

        if progress_callback:
            progress_callback(index, total)

        original_description = description
        payee = extract_osko_payee(original_description)

        description = clean_description(description)

        # Handle internal transfers first.
        if "internal transfer" in description.casefold():
            update_transaction_category(description, "Transfer")
            categorised += 1
            continue

        # Handle Osko payments using the ORIGINAL description.
        if payee is not None:
            print(f"\nOsko payment detected: {original_description}")
            print(f"Extracted payee: {payee}")

            if not is_known_payee(payee):
                save_known_payee(payee)

            update_transaction_category(description, "Other")
            categorised += 1
            continue

        # Check whether this exact description is a known payee.
        if is_known_payee(description):
            update_transaction_category(description, "Other")
            categorised += 1
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
            categorised += 1

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
            categorised += 1

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

    return categorised