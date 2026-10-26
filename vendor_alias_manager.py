
import json
from pathlib import Path
from difflib import get_close_matches

JSON_PATH = Path(__file__).parent / "vendor_aliases.json"

# In-memory caches so repeated lookups don't re-read the JSON files.
_aliases_cache = None
_canonical_lookup = None


def load_vendor_aliases(): # Load the vendor aliases from the JSON file
    global _aliases_cache

    if _aliases_cache is None:
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            _aliases_cache = json.load(file)

    return _aliases_cache


def save_vendor_aliases(aliases): # Save the vendor aliases to the JSON file
    global _aliases_cache, _canonical_lookup

    with open(JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(aliases, file, indent=4, ensure_ascii=False)

    _aliases_cache = aliases
    _canonical_lookup = None


def _get_canonical_lookup():
    global _canonical_lookup

    if _canonical_lookup is None:
        _canonical_lookup = {}

        for canonical_name, alias_list in load_vendor_aliases().items():
            _canonical_lookup.setdefault(
                canonical_name.casefold(), canonical_name
            )

            for alias in alias_list:
                _canonical_lookup.setdefault(
                    alias.casefold(), canonical_name
                )

    return _canonical_lookup


def get_vendor_canonical(vendor): # Get the canonical name for a given vendor, if it exists
    return _get_canonical_lookup().get(vendor.casefold().strip())


def find_similar_canonical(vendor, aliases=None): # Find similar canonical names for a given vendor using difflib's get_close_matches
    if aliases is None:
        aliases = load_vendor_aliases()

    canonical_names = list(aliases.keys())

    return get_close_matches(
        vendor.strip(),
        canonical_names,
        n=3,
        cutoff=0.6
    )

def add_vendor(canonical_name, alias_list):
    aliases = load_vendor_aliases()
    canonical_name = canonical_name.strip()

    if not canonical_name:
        return None

    # If this vendor already exists as a canonical name or alias,
    # reuse its existing canonical name.
    existing_name = get_vendor_canonical(canonical_name)

    if existing_name is not None:
        canonical_name = existing_name
    else:
        # Similar names produce a warning, not an automatic rejection.
        similar_names = find_similar_canonical(canonical_name, aliases)

        if similar_names:
            print(
                f"Possible similar vendors for '{canonical_name}' "
                "(saving as a separate vendor):"
            )

            for name in similar_names:
                print(f"- {name}")

        aliases[canonical_name] = []

    # Add aliases, avoiding duplicates and protecting aliases
    # that already belong to another vendor.
    for alias in alias_list:
        alias = alias.strip()

        if not alias:
            continue

        alias_owner = None

        for name, existing_aliases in aliases.items():
            if alias.casefold() == name.casefold():
                alias_owner = name
                break

            for existing_alias in existing_aliases:
                if alias.casefold() == existing_alias.casefold():
                    alias_owner = name
                    break

            if alias_owner is not None:
                break

        if alias_owner is None:
            aliases[canonical_name].append(alias)

        elif alias_owner != canonical_name:
            print(
                f"'{alias}' already belongs to '{alias_owner}'. "
                "Skipping this alias."
            )

    save_vendor_aliases(aliases)
    print(f"Saved vendor: {canonical_name}")

    return canonical_name


PAYEES_PATH = Path(__file__).parent / "known_payees.json"

_payees_cache = None


def load_known_payees():
    global _payees_cache

    if _payees_cache is None:
        with open(PAYEES_PATH, "r", encoding="utf-8") as file:
            _payees_cache = json.load(file)

    return _payees_cache


def is_known_payee(payee):
    payees = load_known_payees()

    return any(
        saved_payee.casefold() == payee.casefold()
        for saved_payee in payees
    )



def save_known_payee(payee):
    global _payees_cache

    payee = payee.strip()

    if not payee:
        return

    payees = load_known_payees()

    # Avoid duplicates, ignoring capitalisation.
    for saved_payee in payees:
        if saved_payee.casefold() == payee.casefold():
            return

    payees.append(payee)
    payees.sort(key=str.casefold)

    with open(PAYEES_PATH, "w", encoding="utf-8") as file:
        json.dump(payees, file, indent=4, ensure_ascii=False)

    _payees_cache = payees
    print(f"Saved known payee: {payee}")


def extract_osko_payee(description):
    marker = " - Osko Payment"
    description_lower = description.casefold()

    marker_position = description_lower.find(marker.casefold())

    if marker_position == -1:
        return None

    prefix = description[:marker_position].strip()
    parts = prefix.split()

    if len(parts) < 2:
        return None

    return " ".join(parts[:2]).strip()
