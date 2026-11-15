FinanceTracker
==============

FinanceTracker is a local personal-finance transaction importer and analysis
tool. It reads bank transactions from a CSV export, cleans bank-generated
descriptions, identifies and normalises vendors, assigns each transaction to a
financial category, stores the results in an SQLite database, and presents the results in
a React dashboard.

The project is designed for Australian transaction data. Vendor recognition and
category classification are assisted by a local Ollama language model, so the
application can operate without sending transaction descriptions to a hosted AI
service. The application also maintains local vendor aliases and category
decisions so repeated imports become faster and more consistent over time.


What the program does
---------------------

The normal workflow is:

1. A bank CSV containing all transactions which can be obtained from most digital first banks is placed in the project directory (This program currently supports just ING).
2. The backend reads the CSV and converts each row into the application's
   transaction format.
3. Descriptions are repaired and cleaned. This includes removing card and
   receipt metadata, Visa purchase location/date text, Osko suffixes, extra
   whitespace, emoji, and common UTF-8/Latin-1 mojibake.
4. A vendor is extracted from the cleaned description.
5. Known vendor aliases are resolved locally. For an unfamiliar vendor, Ollama
   attempts to identify the canonical business name and save the new alias
   relationship.
6. A category is assigned. Existing vendor/category decisions are reused from
   SQLite. Only uncached vendors are sent to Ollama for classification.
7. The transaction and its classification are written to SQLite.
8. The frontend reads the database through the FastAPI API and displays a
   financial summary.

The default categories are:

    Groceries
    Bills
    Transport
    Entertainment
    Shopping
    Income
    Restaurant Dining
    Fast Food
    Transfer
    Other

The classifier is instructed to use the closest available category and to
recognise Australian businesses. It includes guidance for supermarkets, fuel
stations, public transport, hardware stores, outdoor retailers, cinemas,
streaming services, meal-kit providers, cryptocurrency exchanges, and RSL
clubs.


Processing and classification details
-------------------------------------

Internal transfers are detected before normal vendor classification and are
assigned to `Transfer`. The dashboard keeps transfers in the transaction list,
but excludes them from income, expense, net-cash-flow, and spending-breakdown
totals. This prevents moving money between personal accounts from being counted
as spending.

Osko payments are handled separately. The payee is extracted from the
description, unknown payees are added to `known_payees.json`, and the payment is
initially assigned to `Other` rather than being guessed as a merchant purchase.

Some incoming transactions are recognised by description patterns, including
salary/payroll payments, selected employers, tax refunds, crypto sales, and
online-wagering withdrawals. These transaction-type labels are stored with the row
and are separate from the spending category.

If Ollama cannot identify a vendor, or returns an invalid category, the program
falls back safely. An unrecognised vendor uses the normalised bank description,
and an uncertain or invalid AI category becomes `Other`. Unknown vendors are
recorded in `unknown_vendors.json` for later review.

The Ollama client uses the `qwen3:4b-instruct` model, temperature `0`, and short
responses appropriate for vendor/category answers. At most five Ollama requests
are allowed to run concurrently to limit GPU and memory usage.


Vendor learning and caching
---------------------------

`vendor_aliases.json` is the local vendor registry. Its keys are canonical
vendor names and its values are lists of bank-description aliases. Multiple
descriptions referring to the same Australian retailer can therefore resolve to
one canonical vendor.

Vendor resolution follows this order:

* exact canonical-name or alias lookup;
* beginning-of-description alias matching, with longer aliases preferred;
* Ollama vendor identification for an unknown description;
* fallback to the normalised description if no reliable vendor is found.

After a vendor has a category, the vendor and category are cached in the
`Vendors` SQLite table. Later transactions for that vendor reuse the cached
answer and do not need another AI classification request. This improves both
speed and consistency.


Input CSV format
----------------

The importer expects a UTF-8 or UTF-8-with-BOM CSV with these column headers:

    Date,Description,Credit,Debit,Balance

Dates may be in either `YYYY-MM-DD` or `DD/MM/YYYY` format. Credit, debit, and
balance values must be parseable as numbers; blank credit/debit values are
treated as zero.

The original description is preserved. The importer also stores a cleaned
description, extracted vendor, transaction type, category, and canonical vendor
ID. A unique SQLite index on date, description, credit, debit, and balance
prevents the same bank row from being imported twice.

Example CSV row:

    Date,Description,Credit,Debit,Balance
    05/11/2026,"WOOLWORTHS 1234 - Visa Purchase - In Brisbane",0,-86.40,1250.60

When a CSV is processed through the web interface, the API reports the number of
rows read, new rows imported, duplicates skipped, rows categorised, elapsed
time, and live progress stages.

The database and personal transaction data are ignored by Git. Does not commit
real bank exports, SQLite databases, or other private financial information.


Setup on Windows PowerShell
---------------------------

Prerequisites:

* Python 3.11 or another compatible recent Python 3 release.
* Node.js and npm for the React frontend.
* Ollama, installed from https://ollama.com/download.

1. Clone the repository and enter the project directory.

2. Create and activate a Python virtual environment:

       py -m venv .venv
       .\\.venv\\Scripts\\Activate.ps1

   If PowerShell blocks activation, use an activated terminal supported by your
   Python installation or adjust the PowerShell execution policy for your user.

3. Install the Python dependencies listed in `requirements.txt`:

       python -m pip install --upgrade pip
       python -m pip install -r requirements.txt

   The source imports the Ollama Python client (`from ollama import
   AsyncClient`). If that package is not already installed, install it inside
   the same virtual environment:

       python -m pip install ollama

   The Ollama desktop/server program is a separate prerequisite from the Python
   client package.

4. Install and prepare the local model:

       ollama pull qwen3:4b-instruct

   Start Ollama if it is not already running. The Python client uses Ollama's
   default local service, normally `http://localhost:11434`.

5. Put a compatible bank export at:

       .\\TransactionList.csv

   Keep real bank data local. For public GitHub testing, use anonymised or
   synthetic rows instead of personal financial data.

6. Install frontend dependencies:

       cd frontend
       npm install
       cd ..


Running the application
-----------------------

Use two terminals from the project directory.

Terminal 1 - start the FastAPI backend:

    .\\.venv\\Scripts\\Activate.ps1
    uvicorn api:app --reload --host 127.0.0.1 --port 8000

The API is then available at `http://127.0.0.1:8000`. FastAPI's interactive
documentation is available at `http://127.0.0.1:8000/docs`.

Terminal 2 - start the React development server:

    cd frontend
    npm run dev

Open the Vite URL shown in the terminal, normally
`http://localhost:5173`.

The dashboard loads existing transactions on startup. Click `Process CSV` to
read the current CSV, import new rows, categorise them, and refresh the
dashboard when the background operation finishes. The button cannot start a
second run while one is active.

The current `main.py` contains the command-line pipeline and reporting logic,
but its `if __name__ == "__main__"` invocation is commented out. The supported
interactive workflow is therefore the FastAPI server plus the React frontend.


Backend API
-----------

    GET  /                         Health check
    POST /process-csv              Start asynchronous CSV run (Main process)
    GET  /process-csv/status       Read processing stage, progress, result, error
    GET  /transactions             Return stored transactions
    GET  /vendors/review            Return high-spend vendors currently marked Other
    POST /vendors/review            Save reviewed vendor categories

When a reviewed vendor is reclassified, all transactions linked to that vendor
are updated as well. This lets a developer correct an uncertain AI result once
instead of editing each transaction independently.


Using the dashboard
-------------------

The Overview page shows total income, total expenses, net cash flow, a spending
breakdown, and recent transactions. The reporting period can be changed to all
time, this month, last month, last three months, or this year.

The Transactions page supports text search across vendor, description, and
category, plus category filtering.

The Categories page presents category-level spending information.

The Vendor Review page lists high-spend vendors currently categorised as
`Other`. Select a more appropriate existing category and save the changes. The
category list is populated from categories already present in the vendor cache.


Preparing public example JSON data
----------------------------------

The repository already uses JSON files as small local knowledge stores. A future
set of anonymised Australian vendor examples can be added without exposing
personal transactions. Useful public fixtures could include:

* vendor aliases: a canonical business name and common bank-description
  variants that should resolve to it;
* unknown vendors: example descriptions that intentionally require review;
* known Osko payees: synthetic payee names used to exercise the Osko path.

Do not publish account numbers, card numbers, balances, addresses, reference
numbers, personal names, or unredacted bank descriptions. Prefer synthetic
descriptions such as `WOOLWORTHS BRISBANE STORE 123`, while keeping the same
format and punctuation patterns found in real bank exports. A separate example
CSV is also useful because the importer requires the five CSV headers described
above.

When adding fixtures, document whether each example should resolve from
`vendor_aliases.json`, trigger Ollama identification, fall back to `Other`, or
appear in the Vendor Review page. This makes the fixtures useful as repeatable
manual tests for another developer.


Data files and reset behaviour
------------------------------

The application writes local state to:

* `database.db`: transactions and cached vendor categories;
* `vendor_aliases.json`: canonical vendors and aliases learned from AI results;
* `unknown_vendors.json`: vendor strings that could not be identified;
* `known_payees.json`: Osko payees seen by the importer.

To preserve learning between runs, keep these files. To start a clean local
experiment, back them up first and then remove or replace only the specific
state files intended for reset. The next backend run recreates the SQLite
tables, but a missing or empty JSON registry may need to be restored with the
expected JSON structure before importing.


Troubleshooting
---------------

* `TransactionList.csv not found`: place the file in the project root and
  confirm its spelling and required headers.
* `No module named ollama`: install the Python client with
  `python -m pip install ollama` inside the active virtual environment.
* Ollama connection errors: start Ollama, confirm that `ollama list` works, and
  pull `qwen3:4b-instruct`.
* The frontend cannot load data: confirm that the backend is running on port
  8000 and the frontend is running on port 5173. The frontend currently uses
  hard-coded URLs for `127.0.0.1:8000`.
* A transaction is not imported again: this may be expected. Rows matching the
  date, description, credit, debit, and balance unique key are skipped.
* A result is `Other`: the vendor may be unknown, an AI response may not have
  matched one of the allowed categories, or the transaction may be an Osko
  payment awaiting manual interpretation.
* A vendor is repeatedly sent for identification: check the alias and unknown
  vendor JSON files and make sure they are valid JSON and writable by the
  current user.


Privacy and safety
------------------

Ollama runs locally, but the application still handles sensitive
financial data, and the SQLite database plus JSON files should be protected as
private data. Use anonymisation when sharing issues or demonstrations on
GitHub.
