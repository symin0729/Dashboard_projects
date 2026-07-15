---
name: dashboard-supabase-refresh
description: Upgrade a self-contained static CSV-based dashboard (the kind with an aggregate.py that prints JSON and an index.html holding a `const DATA = {...}` block) so its data lives in Supabase (managed Postgres) instead of loose CSV files, refreshed by a one-button GitHub Actions pipeline. Use this whenever someone wants a static dashboard's data "in a database instead of CSVs", wants the dashboard to "update when the data changes" without hand-pasting JSON, asks about Supabase/Postgres as a backing store for a static site, or wants a manual-trigger (button) refresh pipeline on GitHub Actions. Also use it to run that refresh later ("reload the new CSV and rebuild the dashboard"). It deliberately keeps the frontend fully static — the database is a private data source touched only at refresh time, never called from the browser.
---

# Static dashboard → Supabase data source + one-button refresh

## Why this shape (read before changing it)

This builds on the `dashboard-from-csvs` pattern: a single static `index.html` with the numbers baked into a `const DATA = {...}` line, plus an `aggregate.py` that recomputes that JSON. That pattern's one rough edge is the refresh: someone reruns a script and hand-pastes JSON into the HTML. This skill removes the hand-pasting and moves the source data off loose files into a real database — **without turning the site into a dynamic app.**

The key design decision, and the reason this is safe for sensitive data: **the browser never talks to Supabase.** The frontend stays 100% static. Supabase is read *only* at refresh time, by a server-side script running in GitHub Actions. So the database credential lives in one encrypted GitHub secret, the raw rows are never exposed publicly, and the deployed page still contains nothing but aggregated public-safe numbers. Contrast this with the common "frontend connects directly to Supabase with an API key + row-level security" approach — that exposes a key in the browser and widens the attack surface, which is the wrong trade when the underlying data is sensitive (payments to professionals, health data, HR data).

The refresh is a **human-pressed button** (`workflow_dispatch`), not a schedule or a webhook. That's intentional: the upstream data changes only when a person swaps in a new CSV, so there's nothing to gain from scheduled polling, and a button keeps the moving parts (and the "who refreshed this and when" audit trail in git history) minimal. Don't add cron/pg_cron/Edge Functions unless the user genuinely needs unattended refresh — it adds runtime surfaces to maintain and works against the "few moving parts" goal that motivated this in the first place.

## What you're building

Five artifacts land in the repo, plus two things the user sets up in web UIs:

| Artifact | Role |
|---|---|
| `supabase/schema.sql` | Single source of truth for the two tables' column types |
| `apply_schema.py` | Applies `schema.sql` to Supabase (once, and on schema changes) |
| `load_csv_to_supabase.py` | Loads a CSV into its table (TRUNCATE + append, preserving types) |
| `aggregate.py` (edited) | Reads from Supabase instead of CSV; otherwise unchanged |
| `update_dashboard.py` | Runs the aggregation and rewrites the `const DATA = {...}` line |
| `.github/workflows/update-dashboard.yml` | The one-button (`workflow_dispatch`) refresh |

User-side, in web UIs (you cannot do these — they involve account creation and credentials): create the Supabase project and get its connection string; register that string as the `SUPABASE_DB_URL` GitHub Actions secret.

Generic, ready-to-adapt versions of all five files are in [assets/](assets/). Copy them into the repo and adjust column names/metrics to the actual data — don't rewrite from scratch.

## Prerequisites — verify, don't assume

1. **The dashboard is already the `dashboard-from-csvs` shape.** Confirm there's an `aggregate.py` printing one JSON object and an `index.html` with a single `const DATA = {...};` line. If not, that skill comes first.
2. **A real Python with pandas + sqlalchemy + psycopg2.** On Windows especially, `python` on PATH is often the Microsoft Store stub, not a real install. Check `python --version` and `python -c "import pandas"`. If missing, `winget install --id Python.Python.3.12 -e` (Windows) / `brew install python` (macOS), then `python -m pip install pandas sqlalchemy psycopg2-binary`. A shell opened before the install may keep a stale PATH — if `python` still won't resolve, call the interpreter by full path (e.g. `AppData\Local\Programs\Python\Python312\python.exe`). Add these three packages to `requirements.txt`; Actions installs from it.
3. **Shell reality.** On Windows the default shell is often PowerShell, where the `SUPABASE_DB_URL=... python ...` inline-env syntax in the docs below does **not** work — use `$env:SUPABASE_DB_URL = '...'` on its own line first, then `python ...`. The inline form is fine in bash.

## The connection string is the hard part — get it right first

Most of the friction in this whole process is the Postgres connection string. Understand these three facts before touching anything, because they'll save an hour of "password authentication failed":

- **Use the Session pooler string, not the direct connection.** Supabase's direct host (`db.<ref>.supabase.co`) is **IPv6-only** by default; on a typical IPv4 machine it fails DNS with "could not translate host name". The pooler host (`...pooler.supabase.com`) is IPv4-reachable. In the Supabase dashboard: **Connect** button → **Session pooler** (port **5432**), not "Direct connection", and not the transaction pooler (port 6543 — that mode can choke on the bulk inserts pandas does).
- **The username is `postgres.<project-ref>`** in the pooler string (e.g. `postgres.abcdefgh...`), not plain `postgres`. This is already baked into the string Supabase shows you; just don't "simplify" it.
- **If the user doesn't know the password, reset it — that's normal.** The DB password is shown once at project creation and never again. Settings → Database → **Reset database password**. Recommend an **alphanumeric-only** password (no `@ : / ?`): special characters must be percent-encoded in the URL and are a common silent breakage. A reset can take a few seconds to propagate.

A "password authentication failed" error means the network path and username are fine and only the password is wrong (often: the reset wasn't actually saved). A "could not translate host name" error means you're on the wrong (direct/IPv6) host. Full troubleshooting matrix in [references/connection_and_auth.md](references/connection_and_auth.md).

Never hardcode or commit the string. It comes from an env var (`SUPABASE_DB_URL`) locally and from a GitHub secret in CI. Add `.env` to `.gitignore`.

**Always verify the connection before building on it** with a throwaway check, so a bad string fails loudly and early rather than deep inside a load:
```
python -c "import os,psycopg2; c=psycopg2.connect(os.environ['SUPABASE_DB_URL'],connect_timeout=15); print('OK', c.cursor().execute('select 1'))"
```

## Step 1 — Define the schema from the real data, not guesses

An explicit `supabase/schema.sql` is the point of moving to a database — it gives correct, documented column types (identifiers as `bigint`, money as `double precision`, etc.) and makes the tables reproducible. But an explicit schema also means **a load fails if a declared type doesn't match the actual CSV values**, so derive the types by inspecting the data, never by eyeballing headers.

Run [scripts/inspect_csv.py](scripts/inspect_csv.py) on each CSV. It prints every column's dtype, null count, and — crucially — how many values can't be parsed as numbers (with examples). This catches the two traps that otherwise blow up the load:

- **Government/CMS-style suppression markers.** Columns that look numeric may contain `#` or `*` (privacy suppression). Those columns must be `text`, not numeric. The inspector flags them under "non-numeric".
- **Integer columns that read as float** because of a few nulls (pandas promotes them to float64, so IDs come out as `1093852253.0`). Declare these `bigint` in the schema and coerce them to a nullable integer in the loader (see Step 2).

Write `supabase/schema.sql` with `create table if not exists`. Map inspected dtypes to Postgres types: `str→text`, clean `int64→bigint`, `float64→double precision`, identifier columns → `bigint`, suppression-flag/marker columns → `text`, all-empty columns → whatever's harmless.

**Quote every column name that isn't already lowercase_snake_case.** Unquoted identifiers get folded to lowercase by Postgres, but pandas `to_sql` queries them exactly as written — so a CamelCase column like `Prscrbr_NPI` created unquoted becomes `prscrbr_npi` and the load fails with "column does not exist". Quoting them (`"Prscrbr_NPI" bigint`) keeps the casing and matches what `to_sql` and `read_sql_table` expect. See the annotated [assets/schema.sql](assets/schema.sql).

Apply it: set `SUPABASE_DB_URL` (session pooler, 5432) and run `python apply_schema.py`.

## Step 2 — Load CSVs into the typed tables

Use [assets/load_csv_to_supabase.py](assets/load_csv_to_supabase.py). It does **TRUNCATE then `to_sql(..., if_exists="append")`** — *not* `if_exists="replace"`. Replace would drop the table and let pandas re-infer types, throwing away the schema you just defined; truncate-and-append keeps the declared types and just swaps the data. If the table doesn't exist yet, it fails with a clear "run apply_schema.py first" message rather than a cryptic error.

For identifier columns that read as float (Step 1), coerce them to pandas nullable `Int64` before loading (`df[col] = df[col].astype("Int64")`) so they land as clean `bigint`. The template has an `INT_COLS` dict at the top — list those columns there per table.

```
# bash:
SUPABASE_DB_URL=postgresql://...pooler.supabase.com:5432/postgres python load_csv_to_supabase.py data_a.csv table_a
# PowerShell:
$env:SUPABASE_DB_URL = 'postgresql://...pooler.supabase.com:5432/postgres'; python load_csv_to_supabase.py data_a.csv table_a
```

## Step 3 — Point aggregate.py at Supabase

The aggregation logic doesn't change — only where the DataFrames come from. Replace the `pd.read_csv(...)` calls with `pd.read_sql_table("<table>", engine)` where `engine = create_engine(os.environ["SUPABASE_DB_URL"])`. Split the file so the aggregation is a pure function of two DataFrames (`build_dashboard_data(op, pdd)`), with a thin `load_from_supabase()` that fetches them — this lets `update_dashboard.py` reuse the logic without shelling out. See [assets/aggregate_supabase.py](assets/aggregate_supabase.py) for the before/after shape.

If any identifier is emitted in the output (e.g. a top-N list keyed by an ID), cast it to `Int64` right before serializing so the JSON shows clean integers, not `1234.0`.

**Verify offline against known-good numbers.** You usually still have the original CSVs locally. Read them directly and call `build_dashboard_data` on them, then compare a few headline totals to the values already committed in `index.html`. If they match, the port is faithful and you've tested the aggregation without needing the DB live.

## Step 4 — Wire the one-button refresh

[assets/update_dashboard.py](assets/update_dashboard.py) imports the aggregation, gets the fresh data from Supabase, and rewrites the single `const DATA = {...};` line in `index.html` via a regex. Use a replacement *function* (`re.sub(pattern, lambda _: new_line, ...)`), not a plain replacement string — JSON contains backslashes that a string replacement would misinterpret as group references.

[assets/update-dashboard.yml](assets/update-dashboard.yml) is the workflow: `workflow_dispatch` trigger, `permissions: contents: write`, checkout → setup-python → `pip install -r requirements.txt` → run `update_dashboard.py` with `SUPABASE_DB_URL` from secrets → commit and push `index.html` **only if it changed** (`git diff --quiet -- index.html || git commit ...`). A "nothing to commit" run is a success, not a failure — it just means the data was already current.

## Step 5 — Deploy, and hand off the two web-UI steps

Commit everything **except** the workflow file first (see the gotcha below), push, and confirm GitHub Pages updated. Then walk the user through the two things only they can do:

1. **Add the workflow file.** Pushing `.github/workflows/*.yml` requires the `workflow` OAuth scope, which the git credential in use often lacks — the push gets rejected with "refusing to allow an OAuth App to create or update workflow ... without workflow scope". Rather than fight the token, commit the other files without the workflow file (keep it on disk), push those, and have the user add the workflow file through the **GitHub web UI** (Add file → Create new file → paste → commit), which has no such restriction. If a commit already included it, `git reset --soft HEAD~1` then unstage just that file (`git restore --staged .github/...`), recommit, and push.
2. **Register the secret.** Repo → Settings → Secrets and variables → Actions → New repository secret. Name `SUPABASE_DB_URL`, value = the session-pooler connection string with the real password. Explain the split clearly if they're confused about "why GitHub and not Supabase": the *value* comes from Supabase, but the thing that *uses* it is GitHub Actions, so it's stored in GitHub (encrypted, masked in logs).

Then the ongoing refresh is: reload changed CSVs via `load_csv_to_supabase.py`, then Actions tab → "Run workflow". A run takes ~1–2 minutes; Pages reflects it within a few more.

## Security hygiene to state out loud

If a password was typed into the chat/terminal during setup, tell the user plainly: git is clean (verify with `git grep` across history for the project ref / `pooler.supabase` — it should only ever match placeholder docs), but the value was still exposed in the conversation. Recommend one final password reset in Supabase, updating only the GitHub secret value afterward (no reload needed). It's hygiene, not an emergency — say so honestly rather than alarming them.
