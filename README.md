<div align="center">

# FinanceTracker

Personal finance transaction importer and dashboard for Australian bank CSV files.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=111827)
![Ollama](https://img.shields.io/badge/Ollama-local%20AI-black?style=flat-square)

</div>

This is a small hobby project. It imports transactions, cleans up bank descriptions, guesses vendors and categories with a local Ollama model, and shows the results in a React dashboard.

## What it does

- Imports an ING CSV export
- Cleans up transaction descriptions
- Recognises vendors and categories
- Remembers vendor aliases and previous category decisions
- Stores data in SQLite and local JSON files
- Shows income, expenses, cash flow, categories, and transactions
- Lets you review vendors that were classified as `Other`

Ollama runs locally, so transaction descriptions are not sent to a hosted AI service.

## Requirements

- Python 3.11 or newer
- Node.js and npm
- [Ollama](https://ollama.com/download)
- An ING CSV export

## Setup

### Backend

From the project folder, open PowerShell and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install ollama
```

Download the model used by the project:

```powershell
ollama pull qwen3:4b-instruct
```

## Testing with the example data

The repository includes fake data so it can be tested without using anyone's real bank information.

From a clean clone, run these commands in PowerShell:

```powershell
git clone https://github.com/Kade0101/FinanceTracker.git
cd FinanceTracker

py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install ollama

cd frontend
npm install
cd ..

Copy-Item example-TransactionList.csv TransactionList.csv
Copy-Item example-vendor_aliases.json vendor_aliases.json
Copy-Item example-known_payees.json known_payees.json
Set-Content unknown_vendors.json -Value "[]"
```

The application uses the normal local filenames shown below. The `example-*` files are only safe templates:

```text
example-TransactionList.csv  ->  TransactionList.csv
example-vendor_aliases.json  ->  vendor_aliases.json
example-known_payees.json    ->  known_payees.json
```

If `database.db` already exists from an earlier run, move it out of the way before testing so the sample rows are not treated as duplicates:

```powershell
if (Test-Path database.db) {
    Move-Item database.db database-before-example-test.db
}
```

The example CSV contains 53 synthetic transactions. On the first run, the dashboard should report approximately 53 imported and 0 duplicates. A second run will correctly report 53 duplicates because those rows are already in the database.

When testing your own data later, keep the same application filenames and replace the local files with your own ignored files. Do not edit the Python paths or commit those files.

### Frontend

```powershell
cd frontend
npm install
cd ..
```

## Running it

Use two PowerShell terminals.

In the first terminal, start the backend:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

In the second terminal, start the frontend:

```powershell
cd frontend
npm run dev
```

Open the Vite URL shown in the terminal. It is usually:

```text
http://localhost:5173
```

The backend API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Importing a CSV

Put your file in the project folder as `TransactionList.csv`.

The CSV must have these columns:

```csv
Date,Description,Credit,Debit,Balance
05/11/2026,"WOOLWORTHS BRISBANE STORE 123",0,-86.40,1250.60
```

Supported date formats are `YYYY-MM-DD` and `DD/MM/YYYY`.

Click **Process CSV** in the dashboard to import the file. Duplicate rows are skipped automatically.

## Dashboard pages

- **Overview** — income, expenses, net cash flow, spending breakdown, and recent transactions
- **Transactions** — search and filter imported transactions
- **Categories** — view spending by category
- **Vendor Review** — correct vendors that were placed in `Other`

Transfers are kept in the transaction list but are not counted as income or spending.

## Categories

The current categories are:

`Groceries`, `Bills`, `Fuel`, `Transport`, `Travel`, `Gambling`, `Entertainment`, `Nightlife`, `Shopping`, `Income`, `Restaurant Dining`, `Fast Food`, `Transfer`, and `Other`.

Unknown or uncertain results are placed in `Other` so the import can continue safely.

## Local data files

The application creates these files while it runs:

- `database.db` — imported transactions and cached categories
- `vendor_aliases.json` — vendor names learned over time
- `unknown_vendors.json` — vendors that could not be identified
- `known_payees.json` — Osko payees found during imports

These files contain personal or sensitive information. They are intended to stay local and are ignored by Git.

## Troubleshooting

**`TransactionList.csv not found`**

Check that the file is in the project folder and has the correct name.

**`No module named ollama`**

Activate the virtual environment and run:

```powershell
python -m pip install ollama
```

**Ollama connection errors**

Start Ollama and check that the model is installed:

```powershell
ollama list
```

**The dashboard cannot load data**

Make sure the backend is running on port `8000` and the frontend is running on port `5173`.

## Development checks

```powershell
cd frontend
npm run lint
npm run build
```

Do not commit real bank exports, account numbers, balances, or other private financial information.

