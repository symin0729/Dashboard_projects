---
name: dashboard-from-csvs
description: Turn two related CSV files into a single self-contained static HTML dashboard (stat cards, a category filter with chart, a top-N table) and deploy it live on GitHub Pages using the gh CLI — no backend, no build step, no framework. Use this whenever the user has two datasets they want joined on a shared key (an ID, a name, a date) and wants a lightweight shareable dashboard out of it — phrases like "build a dashboard from these two CSVs", "join X and Y and show me a correlation", "make a top-30 list and put it online", "redeploy the dashboard with the new data", or "set up GitHub Pages for this". Also use it when the user is updating an *existing* dashboard built this way (recognizable by an `aggregate.py` that prints JSON plus an `index.html` with a `const DATA = {...}` block) — the refresh workflow (rerun the script, replace the constant, push) is part of this skill too.
---

# Dashboard from two CSVs

## Why this shape

This pattern exists for a specific reason: the audience for these dashboards is usually a manager or a small team, not engineers, and the data behind them is a one-off pairing of two datasets someone was handed, not a live system. Building a backend, a database, or a build pipeline for that is more infrastructure than the problem needs. A single HTML file with the numbers baked in can be opened by anyone, emailed as an attachment, or pushed to GitHub Pages in minutes, and there's nothing to keep running.

The trade-off is that data refreshes are manual (rerun a script, paste new JSON in). That's a feature here, not a corner cut — read [references/design_tradeoffs.md](references/design_tradeoffs.md) before "fixing" this by adding a backend or a build step unless the user has actually outgrown the manual refresh (e.g. they need it updating automatically on a schedule, or non-technical teammates need to trigger a refresh themselves).

## The workflow has two independent halves

1. **Build** — turn the CSVs into a dashboard file. Fully scriptable, no side effects, safe to redo as many times as needed.
2. **Deploy** — get that file onto the internet via GitHub Pages. Touches the user's real GitHub account (auth, a real repo, a real push). Confirm before creating anything, and never assume a repo should be public just because the last one was — ask.

Do the build half completely before touching deploy. If the user only asked for "a dashboard" with no mention of hosting it, stop after the build half and ask whether they want it deployed.

## Step 1 — Understand the join before writing code

Before opening a CSV, get three answers (from the user, or from looking at the headers if that's faster):

- **What's the shared key?** An ID, an email, a name, a date — whatever links a row in file A to a row in file B.
- **What does each side measure?** e.g. "spend" in one file, "outcomes" in the other. The dashboard's whole point is comparing these.
- **Is the join expected to be partial?** Almost always yes for real-world data. Don't assume every row in A has a match in B. Compute the actual overlap (`set(a_keys) & set(b_keys)`) and surface it as a number, not an assumption — the user will want to know whether they're looking at 90% coverage or 20%.

If the two datasets' totals are wildly different in magnitude (a common case: dollars spent vs. dollars of downstream outcome, which can differ by 100x+), a raw ratio between them is meaningless. Standardize instead — pick a baseline (e.g. the combined average across the categories that exist in both datasets) and express each category as an index relative to it (1.0 = average). This is what makes "Category A drives 1.4x the outcome per dollar of Category B" a sentence that means something.

## Step 2 — Write the aggregation script

Before writing any code, confirm `python` actually resolves to a real interpreter with pandas — don't assume it does. On Windows in particular, `python`/`py` on PATH sometimes point at the Microsoft Store stub (a placeholder that isn't a real install), and `import pandas` fails even when a Python folder exists under `AppData\Local\Programs\Python\` if it's a leftover from a previous uninstall. Check with:
```
python --version
python -c "import pandas; print(pandas.__version__)"
```
If either fails, install a real Python (`winget install --id Python.Python.3.12 -e` on Windows, `brew install python` on macOS) and then `python -m pip install pandas`. After installing, a shell/session started *before* the install may still have the old PATH cached — if `python` still doesn't resolve afterward, find the new interpreter's full path (e.g. `AppData\Local\Programs\Python\Python312\python.exe`) and use that directly rather than assuming the install failed.

Use pandas (or an equivalent real CSV parser) — never split on commas by hand. Real-world CSV fields routinely contain commas inside quoted values (company names, addresses), and naive splitting will silently corrupt exactly those rows without erroring. See [references/aggregate_pattern.py](references/aggregate_pattern.py) for an annotated template covering the shape below; adapt the column names and metrics to the actual data.

The script should, in order:
1. Read both CSVs.
2. Normalize any categorical field that has inconsistent casing/formatting before grouping on it (e.g. "ACME INC" vs "Acme Inc." — decide on one canonical form). Skipping this silently splits one real category into two in every downstream aggregate.
3. Compute the join-key overlap between the two datasets.
4. Build an `overall` stats block (row counts, unique-key counts, totals on each side, overlap count/percentage) — this feeds the top-level stat cards.
5. Group each dataset by category, merge the two on the category name, and compute the standardized index from Step 1 for categories present in both. Categories present in only one dataset keep their own-side metrics with the other side `null` — don't drop them, the user usually wants to see "no data on the other side" as a signal in itself.
6. Group by the individual entity (not the category) to build a top-N list sorted by whichever metric matters most, tagging each row with whether it has a match on the other side.
7. Print one JSON object (`{"overall": ..., "categories": [...], "top_n": [...]}`) to stdout — nothing else. This makes the refresh workflow a single pipeable command.

Run it and redirect to confirm it produces valid JSON before moving on:
```
python aggregate.py file_a.csv file_b.csv > /tmp/check.json
```

## Step 3 — Build the dashboard file

Start from [assets/dashboard_template.html](assets/dashboard_template.html) — it has the structure already wired up (stat card grid, a category `<select>` that drives both a detail panel and a Chart.js bar chart, a sortable top-N table) with placeholder text marking every spot that needs the real domain's labels and field names. Load Chart.js from its CDN (`cdn.jsdelivr.net` or `cdnjs.cloudflare.com`) rather than bundling it — there's no build step to bundle it through anyway.

Paste the script's JSON output into the `const DATA = {...}` line. This is the one manual step in the whole pipeline; don't try to automate it away by having the script write into the HTML file directly — keeping the boundary explicit (script outputs data, human embeds it) is what makes it obvious, months later, exactly which numbers are live and where they came from.

Do not commit the raw source CSVs. Add a `.gitignore` with `*.csv` (or whatever the raw filenames are) before the first commit — treat any dataset a user hands you as sensitive by default unless they say otherwise. Only the aggregated JSON, embedded in the HTML, should ever reach the repo.

If the data touches anything with real regulatory weight — payments to professionals, health data, HR/compensation data, anything where a correlation could be misread as a causal or actionable claim — put a plain-language disclaimer near the top of the page saying so, and say so to the user directly rather than silently adding legal-sounding boilerplate they didn't ask for.

## Step 4 — Deploy to GitHub Pages

[scripts/deploy_github_pages.sh](scripts/deploy_github_pages.sh) automates everything below — read it before running it so you know what it's about to do, then run it and follow its prompts. The steps it performs, in case you need to do any of them by hand or explain what's happening:

1. **Check for the `gh` CLI**, install it if missing (`winget install --id GitHub.cli -e` on Windows, `brew install gh` on macOS, or the user's package manager on Linux). This is a real software install — say so before doing it.
2. **Check `gh auth status`.** If not logged in, run `gh auth login --hostname github.com --git-protocol https --web`. This prints a one-time code and a URL — surface both to the user immediately and wait; it requires them to actually complete a browser login, there's no way around that step.
3. **`git init` / commit / `git remote add origin <url>` / `push`** — the user needs to have already created the (empty) GitHub repo and given you its URL, or tell you to create one via `gh repo create`. Confirm the repo name and public/private setting with them; don't default to public.
4. **Enable Pages via the API** (no clicking through Settings needed):
   ```
   gh api repos/<owner>/<repo>/pages -X POST -f "source[branch]=main" -f "source[path]=/"
   ```
5. **Poll the build status** until it's done:
   ```
   gh api repos/<owner>/<repo>/pages/builds/latest --jq .status
   ```
   Repeat every few seconds until this prints `built` (or `errored`, in which case check `gh api repos/<owner>/<repo>/pages` for details).
6. **Report the live URL** — `https://<owner>.github.io/<repo>/` — and actually fetch it (or ask the user to) to confirm it renders before calling the task done. A `built` status means GitHub finished copying files, not that the page is bug-free.

## Step 5 — The refresh workflow (this is the repeatable part)

When the user comes back later with updated CSVs:
1. Rerun `aggregate.py` against the new files.
2. Replace the `const DATA = {...}` line in `index.html` with the new output — nothing else in the file should need to change.
3. Commit and push. GitHub Pages rebuilds automatically; no need to touch the Pages API again.
4. Confirm the live URL reflects the update (Pages builds usually land within a minute or two; `gh api repos/<owner>/<repo>/pages/builds/latest` shows the status if you want to be sure before telling the user it's live).

This is the whole point of keeping the file self-contained: refreshing data is steps 1–3 above and nothing more.
