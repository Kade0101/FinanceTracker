import csv
import re
from vendor_alias_manager import load_vendor_aliases

VENDOR_ALIASES = load_vendor_aliases()


TRANSACTION_TYPE_RULES = [
    # Employment income: specific employer and payroll descriptions

    (
        "Employment Income",
        [
            r"\bTIMEVALE\s+P/L\b",
            r"\bREDCAPE HOTEL\b",
            r"\bHOSPITALITY FORC\b",
            r"\bAUSSIE WORLD\b",
            r"\bAWX LABOUR\b",
        ],
    ),


    # Internal transfers between your own accounts
    (
        "Internal Transfer",
        [
            r"\bINTERNAL TRANSFER\b",
        ],
    ),

    # Known tax refunds
    (
        "Tax Refund",
        [
            r"\bTAX REFUND\b",
            r"\bAUSTRALIA POST\b.*\bRECEIPT 44916\b",
        ],
    ),

    # Known crypto provider
    (
        "Crypto Sale",
        [
            r"\bCOINSPOT\b",
        ],
    ),

    # Known gambling provider; review the description before
    # treating every withdrawal as winnings.
    (
        "Gambling Winnings",
        [
            r"\bSPORTSBET\b.*\bWITHDRAWAL\b",
        ],
    ),
]


def classify_transaction(description, credit=0, debit=0):
    """Return a transaction type based on known description patterns."""
    text = (description or "").upper()

    # Don't classify outgoing payments as income types.
    if credit and credit > 0:
        for transaction_type, patterns in TRANSACTION_TYPE_RULES:
            if any(re.search(pattern, text) for pattern in patterns):
                return transaction_type

    return "Unclassified"


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
        raw_description = strip_emojis(transaction["Description"])

        cleaned = clean_description(raw_description)

        # Keep the original description intact
        transaction["Cleaned_Description"] = cleaned

        # Extract the vendor from the cleaned description
        transaction["Vendor"] = normalise_vendor(cleaned)
        
        
        try:
            credit = float(transaction.get("Credit") or 0)
        except (ValueError, TypeError):
            credit = 0

        try:
            debit = float(transaction.get("Debit") or 0)
        except (ValueError, TypeError):
            debit = 0

        transaction["Transaction_Type"] = classify_transaction(
            raw_description,
            credit=credit,
            debit=debit,
        )


    return transactions


def repair_mojibake(text: str) -> str:
    """Repair text that was decoded as Latin-1 instead of UTF-8."""
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text



def strip_emojis(text: str) -> str:
    """Repair common encoding issues and remove emoji or mojibake fragments."""
    text = repair_mojibake(text)

    # Remove actual emoji characters and related Unicode selectors/joiners.
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E6-\U0001F1FF"
        "\U00002700-\U000027BF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U0000FE0E-\U0000FE0F"
        "\U0001F3FB-\U0001F3FF"
        "\U0000200D"
        "]+"
    )
    text = emoji_pattern.sub("", text)

    # Remove common mojibake fragments left when decoding cannot be reversed.
    mojibake_pattern = re.compile(
        r"(?:ðŸ|ï¸|â˜|â€|\\x[89A-Fa-f][0-9A-Fa-f])"
        r"[^\s-]*"
    )
    text = mojibake_pattern.sub("", text)

    return " ".join(text.split())


if __name__ == "__main__":
    transactions = import_transactions()

    classified = {}
    examples = {}

    for transaction in transactions:
        transaction_type = transaction.get(
            "Transaction_Type", "Unclassified"
        )

        classified[transaction_type] = (
            classified.get(transaction_type, 0) + 1
        )

        examples.setdefault(transaction_type, [])
        if len(examples[transaction_type]) < 5:
            examples[transaction_type].append(
                transaction.get("Description", "")
            )

    print("\nTRANSACTION CLASSIFICATION PREVIEW")
    print("-" * 40)

    for transaction_type, count in sorted(classified.items()):
        print(f"\n{transaction_type}: {count} transactions")

        for description in examples[transaction_type]:
            print(f"  - {description}")

    print("\nPreview only — no database changes made.")

