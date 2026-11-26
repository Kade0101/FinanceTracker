
import json
import re

from pathlib import Path
from difflib import get_close_matches


# --------------------------------------------------
# File paths
# --------------------------------------------------

JSON_PATH = Path(__file__).parent / "vendor_aliases.json"
UNKNOWN_VENDORS_PATH = Path(__file__).parent / "unknown_vendors.json"
PAYEES_PATH = Path(__file__).parent / "known_payees.json"


# --------------------------------------------------
# In-memory caches
# --------------------------------------------------

_aliases_cache = None
_canonical_lookup = None
_alias_pattern = None
_alias_pattern_lookup = None

_unknown_vendors_cache = None
_payees_cache = None


# --------------------------------------------------
# Unknown vendor management
# --------------------------------------------------

def load_unknown_vendors():
    global _unknown_vendors_cache

    if _unknown_vendors_cache is None:
        if UNKNOWN_VENDORS_PATH.exists():
            with open(UNKNOWN_VENDORS_PATH, "r", encoding="utf-8") as file:
                vendors = json.load(file)
        else:
            vendors = []

        # Store case-insensitive keys while preserving original names.
        _unknown_vendors_cache = {
            vendor.casefold(): vendor
            for vendor in vendors
        }

    return _unknown_vendors_cache


def save_unknown_vendor(vendor):
    vendor = vendor.strip()

    if not vendor:
        return

    unknown_vendors = load_unknown_vendors()
    vendor_key = vendor.casefold()

    if vendor_key in unknown_vendors:
        return

    unknown_vendors[vendor_key] = vendor

    with open(UNKNOWN_VENDORS_PATH, "w", encoding="utf-8") as file:
        json.dump(
            sorted(unknown_vendors.values(), key=str.casefold),
            file,
            indent=4,
            ensure_ascii=False
        )


# --------------------------------------------------
# Vendor alias management
# --------------------------------------------------

def load_vendor_aliases():
    global _aliases_cache

    if _aliases_cache is None:
        with open(JSON_PATH, "r", encoding="utf-8") as file:
            _aliases_cache = json.load(file)

    return _aliases_cache


def save_vendor_aliases(aliases):
    global _aliases_cache, _canonical_lookup
    global _alias_pattern, _alias_pattern_lookup

    with open(JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(aliases, file, indent=4, ensure_ascii=False)

    _aliases_cache = aliases

    # Invalidate lookup and regex caches.
    _canonical_lookup = None
    _alias_pattern = None
    _alias_pattern_lookup = None


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


def _get_alias_pattern():
    global _alias_pattern, _alias_pattern_lookup

    if _alias_pattern is None:
        lookup = _get_canonical_lookup()

        # Longest aliases first to prefer more specific matches.
        sorted_aliases = sorted(
            lookup.keys(),
            key=len,
            reverse=True
        )

        _alias_pattern_lookup = lookup

        if sorted_aliases:
            _alias_pattern = re.compile(
                r"(?<!\w)("
                + "|".join(
                    re.escape(alias) for alias in sorted_aliases
                )
                + r")(?!\w)"
            )

    return _alias_pattern, _alias_pattern_lookup


def get_vendor_canonical(vendor):
    vendor = vendor.casefold().strip()

    lookup = _get_canonical_lookup()

    # First, check for an exact match.
    exact_match = lookup.get(vendor)

    if exact_match is not None:
        return exact_match

    # Otherwise, check for an alias at the beginning of the vendor.
    pattern, alias_lookup = _get_alias_pattern()

    if pattern is not None and alias_lookup is not None:
        match = pattern.match(vendor)

        if match:
            return alias_lookup[match.group(1)]

    return None


def find_similar_canonical(vendor, aliases=None):
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

    # Reuse an existing canonical vendor if recognised.
    existing_name = get_vendor_canonical(canonical_name)

    if existing_name is not None:
        canonical_name = existing_name

    else:
        # Similar names produce a warning, not automatic rejection.
        similar_names = find_similar_canonical(canonical_name, aliases)

        if similar_names:
            print(
                f"Possible similar vendors for '{canonical_name}' "
                "(saving as a separate vendor):"
            )

            for name in similar_names:
                print(f"- {name}")

        aliases[canonical_name] = []

    # Add aliases while protecting existing ownership.
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


# --------------------------------------------------
# Known payee management
# --------------------------------------------------

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
        json.dump(
            payees,
            file,
            indent=4,
            ensure_ascii=False
        )

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
