import os
from anthropic import Anthropic
import anthropic

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

    
