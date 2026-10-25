import os
from anthropic import Anthropic
import json
import vendor_alias_manager
from vendor_alias_manager import load_vendor_aliases, save_vendor_aliases

api_key = os.environ.get("ANTHROPIC_API_KEY")

client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

CATEGORIES = [
    "Groceries",
    "Bills",
    "Transport",
    "Entertainment",
    "Shopping",
    "Income",
    "Restaurant Dining",
    "Fast Food",
    "Transfer",
    "Other"
]
def create_new_vendor_cannonical(alias):

    aliases = load_vendor_aliases()
    canonical_name = alias
    if canonical_name not in aliases:
        aliases[canonical_name] = []
        save_vendor_aliases(aliases)

def categorise_transaction(description):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=30,
        messages=[
            {
                "role": "user",
                "content": (
                    "Categorise this bank transaction into exactly "
                    "one of these categories: "
                    f"{', '.join(CATEGORIES)}.\n"
                    f"Transaction description: {description}\n"
                    "Return only the category name. "
                    "If uncertain, return Other."
                )
            }
        ]
    
    )
    print("Categorising transaction with API")

    category = response.content[0].text.strip()

    if category not in CATEGORIES:
        return "Other"

    return category

def get_or_create_vendor(vendor, description):
    existing_vendor = vendor_alias_manager.get_vendor_canonical(vendor)

    if existing_vendor is not None:
        return existing_vendor
    if vendor.casefold() in [v.casefold() for v in json.load(open("unknown_vendors.json", "r"))]:
        print(f"Vendor '{vendor}' is already in unknown vendors.")
        return None
    result = identify_vendor_with_ai(description)

    if result is None:
        unknown_vendors = json.load(open("unknown_vendors.json", "r"))
        if vendor not in unknown_vendors:
            unknown_vendors.append(vendor)
            json.dump(unknown_vendors, open("unknown_vendors.json", "w"))
        return None

    canonical_name, alias_list = result
    if vendor.casefold() not in [
        alias.casefold() for alias in alias_list
    ]:
        alias_list.append(vendor)

    print(f"Adding vendor: {canonical_name} with aliases: {alias_list}")

    return vendor_alias_manager.add_vendor(
        canonical_name,
        alias_list
    )


def identify_vendor_with_ai(description):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=150,
        messages=[
            {
                "role": "user",
                "content": (
                    "Identify the business in this bank transaction.\n"
                    f"Transaction: {description}\n\n"
                    "Return a JSON object in this format:\n"
                    '{"canonical_name": "Business Name", '
                    '"aliases": ["alias1", "alias2"]}\n\n'
                    "Do not include transaction numbers, locations, "
                    "or dates as aliases. If you cannot confidently "
                    "identify a business, return an empty canonical_name "
                    "and an empty aliases list. Do not identify personal "
                    "names as businesses."
                )
            }
        ]
    )

    raw_response = response.content[0].text.strip()

    # Extract the first JSON object, ignoring text around it.
    try:
        json_start = raw_response.index("{")
        result, _ = json.JSONDecoder().raw_decode(
            raw_response[json_start:]
        )
    except (ValueError, json.JSONDecodeError):
        print("Could not parse Claude's vendor response:")
        print(raw_response)
        return None

    if not isinstance(result, dict):
        print("Claude returned an invalid vendor response.")
        return None

    canonical_name = result.get("canonical_name", "")
    alias_list = result.get("aliases", [])

    if not isinstance(canonical_name, str):
        print("Claude returned an invalid canonical name.")
        return None

    canonical_name = canonical_name.strip()

    # An empty name means Claude couldn't identify a business.
    if not canonical_name:
        print("\n")
        print("Claude could not identify the vendor.")
        print("Description:", description)
        return None

    if not isinstance(alias_list, list) or not all(
        isinstance(alias, str) for alias in alias_list
    ):
        print("Claude returned an invalid alias list.")
        return None

    # Remove blank aliases and duplicate aliases.
    cleaned_aliases = []
    seen_aliases = set()
    for alias in alias_list:
        alias = alias.strip()

        if alias and alias.casefold() not in seen_aliases:
            cleaned_aliases.append(alias)
            seen_aliases.add(alias.casefold())

    return canonical_name, cleaned_aliases

    
