# Article Publication Notifier

Automatically emails your sources when an article they contributed to
goes live, by scanning each publication's RSS feed on a schedule.

## How it works

1. You keep a **Google Sheet** with two tabs:
   - `Articles` — one row per upcoming piece, with keywords that will
     appear in its headline once published.
   - `Contacts` — one row per source, linked to an article.
2. Every 30 minutes, a **GitHub Action** runs a script that checks
   each publication's RSS feed for a new entry matching your keywords.
3. When it finds a match, it **emails every linked contact** from a
   dedicated Gmail account, with replies routed to your real inbox,
   and marks the row `sent` so it's never sent twice.

Total cost: $0. GitHub Actions is free for this volume of usage on a
personal account, and Gmail/Sheets are free.

---

## One-time setup

### 1. Create the dedicated Gmail account
Create a new Gmail address just for this, e.g.
`yourname.notifications@gmail.com`. Everything below (steps 2-3) is
done *while logged into this account*, not your main one.

### 2. Enable the Gmail API and get OAuth credentials
1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
   and create a new project.
2. Go to **APIs & Services > Library**, search "Gmail API", enable it.
3. Go to **APIs & Services > OAuth consent screen**. Choose
   "External", fill in the required fields, and add the scope
   `https://www.googleapis.com/auth/gmail.send`. Add the dedicated
   Gmail address as a test user.
4. Go to **APIs & Services > Credentials > Create Credentials >
   OAuth client ID**. Application type: **Desktop app**. Download the
   JSON file, save it as `credentials.json` in the `scripts/` folder.
5. On your own computer (not GitHub): `pip install google-auth-oauthlib`,
   then run `python scripts/get_refresh_token.py`. A browser window
   opens — log in as the dedicated account and approve access. The
   script prints three values: save them, you'll need them in step 5.

### 3. Create a service account for Sheet access
1. In the same Google Cloud project: **APIs & Services > Library**,
   enable the "Google Sheets API".
2. **APIs & Services > Credentials > Create Credentials > Service
   Account**. Give it any name. After creating it, open it, go to
   **Keys > Add Key > Create new key > JSON**, and download it.
3. Note the service account's email address (looks like
   `something@project-id.iam.gserviceaccount.com`) — you'll share
   your Sheet with it in step 4.

### 4. Create the Google Sheet
Create a new Google Sheet with two tabs, named exactly:

**`Articles`** — columns, exactly in this order:
| article_id | publication | match_keywords | status | found_url | sent_date |
|---|---|---|---|---|---|

- `article_id`: any unique short id you make up, e.g. `2026-09-ai-piece`
- `publication`: must match a `name` in `config/sources.yaml`
- `match_keywords`: comma-separated words that will ALL appear in the
  headline once published, e.g. `layoffs, hiring` — pick 2-3
  distinctive words, not generic ones
- `status`: set to `pending` for anything not yet published
- `found_url` / `sent_date`: leave blank, the script fills these in

**`Contacts`** — columns, exactly in this order:
| article_id | contact_name | contact_email | custom_note |
|---|---|---|---|

- `article_id`: matches the row in `Articles`
- `custom_note`: optional — anything extra you want added to that
  one contact's email

Add multiple rows to `Contacts` with the same `article_id` for
multi-source articles.

Then **share the Sheet** with the service account email from step 3
as an **Editor**.

Copy the Sheet's ID from its URL:
`https://docs.google.com/spreadsheets/d/THIS_PART_IS_THE_ID/edit`

### 5. Configure your publications
Edit `config/sources.yaml` and list every publication you write for,
with its RSS feed URL.

### 6. Push this to a GitHub repo, then add secrets
Push this whole folder to a new (can be private) GitHub repo. Then go
to **Settings > Secrets and variables > Actions > New repository
secret** and add each of these:

| Secret name | Value |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | paste the full contents of the service account JSON file from step 3 |
| `SHEET_ID` | the Sheet ID from step 4 |
| `GMAIL_CLIENT_ID` | from step 2 |
| `GMAIL_CLIENT_SECRET` | from step 2 |
| `GMAIL_REFRESH_TOKEN` | from step 2 |
| `SENDER_EMAIL` | your dedicated Gmail address |
| `MAIN_EMAIL` | your real email — replies get routed here |

### 7. Test it before trusting it
Go to the **Actions** tab in your repo, select "Scan for published
articles and notify sources", click **Run workflow**, and set
`dry_run` to `true`. Check the logs — it will print what it *would*
have sent, without sending anything or touching the Sheet. Once the
matches look right, run it again for real (or just wait for the
schedule).

---

## Ongoing use
Whenever you line up an article with sources, just add a row to
`Articles` and matching rows to `Contacts` before or right after
publication. That's the entire manual step — the rest runs itself.

## Notes and limitations
- Matching is keyword-based since the exact headline isn't known in
  advance. Pick distinctive keywords to avoid false matches, and
  check `found_url` after the first few real sends.
- If a publication has no public RSS feed, you'll need another
  detection method (not covered here) — most major outlets do have one.
- GitHub's free tier is more than enough for a 30-minute schedule long-term.
