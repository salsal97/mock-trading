# Mock Trading

A local classroom market-making simulation using Django REST Framework and React. Participants compete to quote a numerical spread, then choose a one-unit BUY or SELL position against the winning maker. Balances are virtual performance scores.

## Rules

- Any registered user can create a market and administer that market. Everyone can browse markets; there are no groups, passwords, or separate participation verification. The administrator cannot quote or trade in their own market, and its maker cannot trade in it.
- During bidding each participant has one current quote. Revisions may be wider or narrower. Quotes rank by width, then the time of the latest quote (and record ID). The top three and personal rank are shown. A maker is selected from current quotes; activation requires at least one quote.
- Participants choose BUY at the maker's high quote or SELL at the low quote and may switch before close. There is no quantity or entry balance deduction. More than seven participants on a side are shown as a count. The maker can simulate P&L at hypothetical outcomes.
- BUY P&L is `(outcome - entry) × unit_value`; SELL P&L is `(entry - outcome) × unit_value`. Maker P&L is the negative sum. Negative balances are allowed. Unit value can be edited before settlement. Outcome or unit-value changes invalidate prior previews; confirmation must match the displayed preview.
- Confirmation locks the market and affected balances, records settlement entries, and applies results atomically once. Closed markets can be reopened with a future deadline before an outcome is entered. Settled financial results are immutable in ordinary editing.

Current assumptions: quotes are positive whole numbers up to 99,999,999; unit value is positive with two decimals; outcomes range from 0.01 to 999,999.99. Results use the existing ROUND_UP rule to cents and reject amounts or resulting balances outside the stored precision. Authenticated users see names on current quotes and positions; anonymous browsing omits those names. When bidding closes without quotes, both deadlines advance by whole days until bidding close is in the future. The first actual quote sets the spread: no starting spread is used.

## Local startup

The following PowerShell commands use `backend/revival-local.sqlite3`, an isolated, Git-ignored development database. They do not load `.env` or connect to a configured PostgreSQL database. Create a Python virtual environment and install `backend/requirements.txt` if needed.

```powershell
.\.venv\Scripts\python.exe backend/manage.py migrate --settings=mock_trading.revival_local_settings
.\.venv\Scripts\python.exe backend/manage.py runserver 127.0.0.1:8765 --noreload --settings=mock_trading.revival_local_settings
```

In another terminal:

```powershell
cd frontend
npm install
$env:PORT='3100'
$env:REACT_APP_API_BASE_URL='http://127.0.0.1:8765'
npm start
```

Open `http://localhost:3100`, register test accounts, and use the market workspace. The local settings and keys are for disposable development only. The local SQLite file persists until removed.

## Verification

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe backend/manage.py test accounts market --settings=mock_trading.test_settings
.\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run --settings=mock_trading.test_settings
cd frontend
$env:CI='true'
npm test -- --watchAll=false --runInBand
$env:CI='false'
npm run build
```

SQLite tests use an in-memory database. For environments that block Jest's default temporary folder, set `$env:TEMP=(Resolve-Path .).Path; $env:TMP=$env:TEMP` from the frontend directory. PostgreSQL concurrency tests require a new isolated localhost PostgreSQL cluster, a dedicated role allowed to create databases, an empty `revival_isolated` database, and `REVIVAL_TEST_PG_USER`, `REVIVAL_TEST_PG_PASSWORD`, and optionally `REVIVAL_TEST_PG_PORT` (default 55432). Run `python backend/manage.py test market.test_postgresql_concurrency --settings=mock_trading.revival_postgres_test_settings`. This creates and drops `test_revival_isolated`; never use an application cluster or `.env` credentials.

For the headless browser journey, start both isolated local servers above, run `npm install --prefix .browser-test-deps --no-save --ignore-scripts playwright-core` from the repository root, then `node frontend/e2e/revival.cjs`. It uses installed Windows Chrome, unique disposable accounts, and checks a test-only server identity before writing data. Unexpected API errors fail the test.

## Maintenance and builds

`python backend/manage.py maintain_markets --settings=<settings>` advances due markets using locks; `--dry-run` reports without changes and `--market-id ID` narrows the run. Schedule it periodically in the target environment; no scheduler is installed by this repository. API reads also run this service. No-bid delay, activation and closure are idempotent.

`build-frontend.sh` builds React and copies generated assets and its index template into Django for combined serving. Those generated files are ignored rather than checked in. The development server uses the separate frontend server above. Production API requests default to the same origin unless `REACT_APP_API_BASE_URL` is set at build time.

When changing a feature, remove its superseded implementation, tests and documentation; do not retain unreachable compatibility scaffolding without an explicit need. Historical migrations are retained.
