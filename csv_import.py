import csv
import re

VENDOR_ALIASES = {
    "Woolworths": ["woolworths", "woolies"],
    "KFC": ["kfc", "kentucky fried chicken"],
    "Coles": ["coles"],
    "McDonald's": ["mcdonalds", "mcdonald's"],
}

def normalise_vendor(description):
    description_lower = description.casefold()

    for canonical_name, aliases in VENDOR_ALIASES.items():
        for alias in aliases:
            if re.search(
                rf"(?<!\w){re.escape(alias.casefold())}(?!\w)",
                description_lower
            ):
                return canonical_name

    # Unknown merchant: use the existing extraction as a fallback
    return description.split(" - ")[0].strip()



def clean_description(description):
    description = re.sub(
        r"\bCard\s+\S+", "", description, flags=re.IGNORECASE
    )
    description = re.sub(
        r"\bReceipt\s+\S+", "", description, flags=re.IGNORECASE
    )
    # Remove OSKO payment details and everything after " - Osko"
    description = re.sub(
        r"\s*-\s*Osko\b.*$",
        "",
        description,
        flags=re.IGNORECASE
    )


    description = re.sub(r"\s+", " ", description).strip()
    return description



def import_transactions():
    with open(
        "TransactionList.csv",
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)
        transactions = list(reader)

    for transaction in transactions:
        raw_description = transaction["Description"]

        cleaned = clean_description(raw_description)

        # Keep the original description intact
        transaction["Cleaned_Description"] = cleaned

        # Extract the vendor from the cleaned description
        transaction["Vendor"] = normalise_vendor(cleaned)

    return transactions


