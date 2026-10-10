# Demo script (5 minutes)

## Before the demo

- **Use a demo account,** never your personal one. Index only `sample-data/` or a folder of harmless
  files: stock photos, public notes, a public GitHub repo.
- **Close every other tab,** and hide the bookmarks bar and notifications. Don't show `.env`, the
  `credentials/` folder, terminal history with keys, or the Drive account picker if it lists
  private accounts.
- **Warm up:** run one search before the audience joins (the first query loads the models into the
  cache).
- **Have a fallback:**
  - the screenshots in `docs/screenshots/` cover every step;
  - if the network or OAuth fails, demo the local folder only and show
    `docs/screenshots/platforms.png` for the connectors.

## 1. The pitch (30 s)

"My files live on my laptop, in Google Drive and on GitHub, and each search only matches names.
CogniSeek indexes all three and finds files by what they contain, say and show."

## 2. Sign in and onboarding (45 s)

1. Register the demo account.
2. Onboarding step 1: connect the platforms. Point out that the Drive scope is read-only, and
   that the app refuses a token without the Drive box ticked.
3. Step 2: choose the priority platform. The dashboard banner shows it indexing first.

## 3. Indexing Center (45 s)

- Show the running job: files done, per-file errors, cancel.
- When it finishes, open **"Where the time went"**: seconds per stage (download, extract, OCR,
  embed, write).
- The line to say: "This is how I found that CPU OCR was the bottleneck. GPU OCR and a parallel
  pipeline took the benchmark from 347 s to 93 s."

## 4. Search (2 min)

| Query | What to show |
|---|---|
| `java` | Documents and code; the highlighted passage explains *why* each file matched |
| `dog` | Photos found by **what they show**: the file names don't contain "dog" |
| `polar bear cubs` | A visual match, possibly a video frame; open it |
| `river` | Point out the separate **"Possible matches"** list: weaker visual evidence, max 3, never mixed into the results |
| `xqzv` | **Nothing.** "Thresholds are calibrated on a labelled eval set; nonsense went from 61 false positives to 1." |

Optional: a typo, `jva` → java results.

## 5. Under the hood (45 s)

- **Qdrant dashboard:** open **http://localhost:6333/dashboard** (development stack only; in Docker
  it is not published).
  - Show the `cogniseek_v2_*` collections and open **one point from the demo account**: the
    `user_id` payload that every search filters on, and the chunk text.
  - Pick a harmless point (sample notes or a stock photo).
  - Don't scroll through the collections: other users' points are there too.
- **One sentence on security:** per-user isolation in every query, encrypted OAuth tokens,
  revocable JWTs, a strict CSP, and CI with gitleaks, CodeQL and audits.

## 6. Close (15 s)

"470+ backend tests, an end-to-end test of the Docker stack in CI, and every quality and speed
claim is measured. The README links to the evaluation and the performance study."

## If something goes wrong

| Problem | Fallback |
|---|---|
| No network / OAuth fails | Local folder only; show the Platforms screenshot |
| A search is slow the first time | "Models are loading." Repeat the query; warm p50 is about 0.2 s |
| A wrong result shows up | Say so: visual search finds about 70% of relevant images; it's in Known limitations |
| The backend is down | Walk through `docs/screenshots/` in order |

## Privacy checklist

- Demo account only; delete it afterwards (Account → Delete; this also revokes the OAuth grants).
- No personal Drive, no private repositories, no real documents (IDs, invoices).
- Screen sharing: share one window, not the whole screen.
