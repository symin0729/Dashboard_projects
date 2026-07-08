# Design trade-offs behind this pattern

These are the specific choices this skill makes, and when it's actually worth deviating from them. Don't "fix" any of these by default — only change them when the user's situation matches the trigger described.

## Data inlined in `index.html`, not a separate `data.js`

**What we do:** `const DATA = {...}` lives directly inside `index.html`'s `<script>` block.

**Why:** A single file can be opened by double-clicking it, emailed as an attachment, or dragged into any static host — no server needed. Splitting the data into `data.js` and loading it with `<script src="data.js">` breaks the double-click case: some browsers block script loading from `file://` URLs for security reasons, so the page silently shows no data until it's served over http(s).

**When to actually split it out:** If the file is getting unwieldy to diff in git (a multi-hundred-KB JSON blob mixed into the same file as the HTML/CSS/JS makes every data refresh look like it touched the whole file), or if this dashboard will only ever be viewed via a real web server anyway (it's already on GitHub Pages, an intranet, etc.) and local double-click-to-open isn't a real use case for this audience — then splitting into `data.js` is a reasonable, small change. Ask the user which matters more to them before doing it silently.

## Manual data refresh, no pipeline

**What we do:** Refreshing data means a human reruns the aggregation script and pastes the output in. Nothing watches the CSVs or runs on a schedule.

**Why:** These dashboards are typically built for one-off or infrequent data drops (a monthly export, a one-time analysis), handed to a manager who isn't going to maintain a pipeline. Building automation for a refresh that happens a few times a year is more maintenance surface than the problem justifies, and it's one more thing that can silently break.

**When to actually automate it:** If the user says the underlying data changes frequently (daily/weekly) and they specifically want it to update itself, or non-technical teammates need to trigger a refresh without touching a terminal. At that point a GitHub Action that runs the aggregation script on a schedule or on file upload and commits the result is worth the added complexity — but confirm this is genuinely needed before building it, since it also means the raw data now needs to live somewhere the Action can read it (which may reopen the "don't commit raw CSVs" question).

## Standardized index instead of a raw ratio, when magnitudes differ a lot

**What we do:** When the two datasets' totals differ by an order of magnitude or more, express each category as a multiple of the cross-category average rather than a raw side-A/side-B ratio.

**Why:** A raw ratio in that situation is technically a number but not an interpretable one — "0.0012" doesn't tell a sales manager anything, while "1.4x average" does. The standardization doesn't change what's actually being measured, just the units it's presented in.

**When a raw ratio is fine instead:** If the two metrics are already the same order of magnitude and a straightforward ratio or percentage is intuitive on its own (e.g. cost vs. budget, both in dollars, similar scale) — don't over-engineer it into a standardized index just because this skill defaults to one for the mismatched case.

## Categories/entities present in only one dataset are kept, not dropped

**What we do:** A category with data in file A but nothing in file B still gets a row in the output, with the file-B fields set to `null` — it isn't filtered out.

**Why:** "This category has no data on the other side" is itself information the user is very likely looking for (e.g., "we're spending on X but it's not shown to be affecting Y in this data at all"). Silently dropping those rows would make the dashboard's coverage look better than it actually is.

## Commit only the aggregated JSON, never the raw CSVs

**Why:** Source CSVs handed to you for this kind of task are very often internal, proprietary, or personally identifiable data, even when nobody explicitly says so. The aggregated summary is a deliberate, reviewable boundary — a `.gitignore` entry for the raw files makes that boundary structural instead of relying on remembering not to `git add` them.
