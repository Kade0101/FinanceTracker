import os
import json
import asyncio
from ollama import AsyncClient
import vendor_alias_manager
from vendor_alias_manager import load_vendor_aliases, save_vendor_aliases

# Initialize the modern async client natively supported by Ollama
async_client = AsyncClient()

OLLAMA_MODEL = "qwen3:4b-instruct"

# Restrict concurrency to 5 parallel tasks to safeguard 12GB VRAM allocation
CONCURRENCY_LIMIT = 5
SEMAPHORE = asyncio.Semaphore(CONCURRENCY_LIMIT)

CATEGORIES = [
    "Groceries",
    "Bills",
    "Fuel",
    "Transport",
    "Travel",
    "Gambling",
    "Entertainment",
    "Nightlife",
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

async def ollama_chat_async(prompt, max_tokens=100):
    """Replaces the blocking requests.post structure with an async event loop socket call."""
    response = await async_client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0,
            "num_predict": max_tokens
        }
    )
    return response["message"]["content"].strip()

async def parallel_categorise_transactions(transactions):
    """Fires all transaction processing steps down native async loops simultaneously."""
    # NO to_thread wrapper. We pass execution entirely down the async pool.
    tasks = [categorise_transaction_async(t) for t in transactions]
    return await asyncio.gather(*tasks)

async def categorise_transaction_async(description):
    """The async-native execution path for categorisation."""
    prompt = (
        "You are a financial transaction classification system.\n\n"
        "Identify the business and determine the most appropriate "
        "financial category for the transaction.\n\n"
        "Available categories:\n"
        f"{', '.join(CATEGORIES)}\n\n"
        "Category definitions and exclusions:\n"
        "- Groceries: supermarkets, grocery stores, and grocery delivery.\n"
        "- Bills: recurring household, utility, insurance, government, or service bills.\n"
        "- Fuel: petrol stations, diesel stations, and vehicle fuel purchases.\n"
        "- Transport: public transport, taxis, rideshare, parking, tolls, and other vehicle costs.\n"
        "- Travel: flights, accommodation, hotels, travel bookings, and other trip-related costs.\n"
        "- Gambling: betting, wagering, casinos, lotteries, and sports-betting transactions.\n"
        "- Entertainment: cinemas, games, streaming, museums, zoos, attractions, sport, and recreational activities.\n"
        "- Nightlife: bars, pubs, nightclubs, live-music venues, and places primarily visited for evening drinking or dancing.\n"
        "- Shopping: retail purchases, clothing, electronics, hardware, gifts, and physical goods.\n"
        "- Restaurant Dining: sit-down meals, restaurants, cafes, and dine-in food venues.\n"
        "- Fast Food: takeaway, quick-service meals, and drive-through food.\n"
        "- Income: wages, salary, benefits, refunds, rebates, or other money received.\n"
        "- Transfer: movement between the user's own accounts or financial products.\n"
        "- Other: use only when the transaction cannot be confidently assigned elsewhere.\n\n"
        "Classification guidelines:\n"
        "- Categorise based on the primary business activity or transaction purpose.\n"
        "- Use your knowledge of businesses, including Australian businesses.\n"
        "- Supermarkets and grocery delivery services: Groceries.\n"
        "- Fuel stations and petrol stations: Fuel.\n"
        "- Public transport providers: Transport.\n"
        "- Retailers selling camping, fishing, boating and outdoor "
        "recreation equipment: Shopping.\n"
        "- Hardware and home improvement stores: Shopping.\n"
        "- Ticketing platforms and cinemas: Entertainment.\n"
        "- Music and streaming subscriptions: Entertainment.\n"
        "- Keep Nightlife separate from Entertainment when the primary activity is going out at night.\n"
        "- Do not use Nightlife for restaurants, cafes, fast food, shops, public transport, fuel, parking,\n"
        "  cinemas, museums, ticketed attractions, sport, or recreational activities.\n"
        "- Do not use Entertainment for ordinary retail, transport, restaurant, or nightlife transactions.\n"
        "- Meal kit delivery services: Groceries.\n"
        "- Cryptocurrency exchanges and investment platforms: Investments.\n"
        "- Betting, wagering, casino, lottery, and sports-betting transactions: Gambling.\n"
        "- Do not classify a business as Other if its primary activity clearly fits an available category.\n"
        "Category selection rules:\n"
        "- Choose the closest matching category, even if the business has multiple activities.\n"
        "- Shopping includes specialist retailers selling physical goods.\n"
        "- Clubs and venues with mixed activities should be classified by the most likely purpose of the transaction.\n"
        "- If a venue could be either a restaurant or nightlife venue and the description gives no useful clue,\n"
        "  prefer Restaurant Dining rather than guessing Nightlife.\n"
        "- Never use Other simply because a business has multiple activities.\n"
        "- Do not invent business information.\n"
        "- If you cannot confidently identify the business, return Other.\n"
        "- Return exactly one category.\n"
        "- Do not provide explanations or reasoning.\n\n"
        f"Transaction: {description}"
    )

    # Use semaphore to limit simultaneous GPU requests
    async with SEMAPHORE:
        try:
            print("-----------Categorising transaction with Ollama---------")
            category = await ollama_chat_async(prompt, max_tokens=20)
            print("AI response:", category)

            for valid_category in CATEGORIES:
                if category.casefold() == valid_category.casefold():
                    return valid_category

            print("Invalid category returned. Using Other.")
            return "Other"

        except Exception as error:
            print("Ollama categorisation error:", error)
            return "Other"

async def get_or_create_vendor_async(vendor, description):
    """Async variation for merchant registry creation patterns."""
    existing_vendor = vendor_alias_manager.get_vendor_canonical(vendor) # may be redundant if vendor variable is already canonical from a previous get_vendor_canonical call

    if existing_vendor is not None:
        return existing_vendor
        
    # File I/O operations are synchronous blocks; keeping them simple here
    with open("unknown_vendors.json", "r") as f:
        unknown_list = json.load(f)
        
    if vendor.casefold() in [v.casefold() for v in unknown_list]:
        print(f"Vendor '{vendor}' is already in unknown vendors.")
        return None
        
    result = await identify_vendor_with_ai_async(vendor, description)

    if result is None:
        with open("unknown_vendors.json", "r") as f:
            unknown_vendors = json.load(f)
        if vendor not in unknown_vendors:
            unknown_vendors.append(vendor)
            with open("unknown_vendors.json", "w") as f:
                json.dump(unknown_vendors, f)
        return None

    canonical_name, alias_list = result
    if vendor.casefold() not in [alias.casefold() for alias in alias_list]:
        alias_list.append(vendor)

    print(f"Adding vendor: {canonical_name} with aliases: {alias_list}")
    return vendor_alias_manager.add_vendor(canonical_name, alias_list)


async def identify_vendor_with_ai_async(vendor, description):
    """Asynchronously infers structured merchant boundaries from inputs."""
    prompt = (
        "You are a bank transaction merchant normalisation system.\n\n"

        "Your task is to identify and standardise the merchant name "
        "from a bank transaction description.\n\n"

        "Return JSON in exactly this format:\n"
        '{"canonical_name": "Business Name", '
        '"aliases": ["Alternative merchant names"]}\n\n'

        "CANONICAL NAME RULES:\n"
        "- Identify the merchant, not the transaction details.\n"
        "- Recognise Australian businesses and international brands.\n"
        "- Standardise recognised businesses to their commonly used name.\n"
        "- Remove branch numbers, store locations, geographical references "
        "and terminal identifiers from the canonical name.\n"
        "- If you do not recognise the business, preserve the identifiable "
        "merchant name without inventing or expanding its identity.\n"
        "- Do not interpret personal names as businesses.\n"
        "- If the description clearly represents a personal transfer, "
        "return an empty canonical_name and empty aliases.\n\n"
        "- Preserve all distinctive words that identify the merchant.\n"
        "- Do not shorten a multi-word business name to just one of its "
        "generic words or business types.\n"
        "- Words such as Hotel, Restaurant, Cafe, Bar, Shop and Store "
        "must not be used as standalone canonical names when the "
        "description provides a more distinctive business name.\n"
        "- Prefer the complete identifiable merchant name over an "
        "overly broad or generic name.\n"

        "ALIAS RULES:\n"
        "- Only include aliases that genuinely identify the same merchant.\n"
        "- An alias must be a complete alternative merchant name or "
        "recognised trading name.\n"
        "- Preserve useful variations of the original merchant wording "
        "when they help identify the same business.\n"
        "- Never use individual words extracted from a merchant name "
        "as standalone aliases.\n"
        "- Never use suburbs, cities, states, street names or other "
        "geographical references as standalone aliases.\n"
        "- Never use generic transaction terms or payment descriptions "
        "as aliases.\n"
        "- Do not include the canonical name itself as an alias.\n"
        "- If no genuine alternative names exist, return an empty list.\n\n"

        "GENERAL RULES:\n"
        "- Do not guess when information is insufficient.\n"
        "- Do not invent businesses, aliases or relationships.\n"
        "- Return valid JSON only, without explanations or markdown.\n\n"

        f"Detected vendor: {vendor}\n"
        f"Original transaction description: {description}"
    )

    async with SEMAPHORE:
        try:
            print("-----------Identifying vendor with Ollama---------")
            print("VENDOR INPUT:", repr(description))
            raw_response = await ollama_chat_async(prompt, max_tokens=150)
            print("AI response:", raw_response)
        except Exception as error:
            print("Ollama vendor identification error:", error)
            return None

    try:
        json_start = raw_response.index("{")
        result, _ = json.JSONDecoder().raw_decode(raw_response[json_start:])
    except (ValueError, json.JSONDecodeError):
        print("Could not parse Ollama's vendor response:", raw_response)
        return None

    if not isinstance(result, dict):
        print("Ollama returned an invalid vendor response.")
        return None

    canonical_name = result.get("canonical_name", "").strip()
    alias_list = result.get("aliases", [])

    if not canonical_name:
        print("Ollama could not identify the vendor. Description:", description)
        return None

    if not isinstance(alias_list, list) or not all(isinstance(a, str) for a in alias_list):
        print("Ollama returned an invalid alias list.")
        return None

    # Strip whitespace/duplicates logic fits here...
    return canonical_name, alias_list
