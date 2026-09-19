# Article Publication Notifier


This is an automated workflow that emails interview sources when the article they contributed to goes live, by scanning each publication's RSS feed on a schedule.

### How it works 

1. The Google Sheet

I maintain a Google Sheet with two tabs:

- Articles - one row per upcoming piece, with keywords that will appear in its headline once published.

- Contacts — one row per source, linked to an article by ID. If multiple contacts are to be included in the same email then this is flagged by the group column.

- Publications - A list of publications that I write for and their RSS feeds.

2. The Script

Every 30 minutes, a **GitHub Action** runs a script that checks each publication's RSS feed for a new entry matching your keywords.

3. The Emails

When a match is found, the script sends an email to the contacts from a dedicated Gmail account, with replies routed to my main email inbox, and marks the row `sent` so it's never sent twice.

I also personally receive a notification that the article has been published 

### What's Involved 

There's some one-time setup involved:

- Creating a dedicated email account (I used Gmail)

- Enabling the Gmail API and getting OAuth credentials for email sending via console.cloud.google.com

- Creating a service account for Google Sheet access via console.cloud.google.com

- Creating a Google Sheet to manage articles 



### Building The Google Sheet 

**`Articles`** — columns, exactly in this order:
| article_id | publication | match_keywords | status | found_url | sent_date |
|---|---|---|---|---|---|

- `article_id`: any unique short id you make up, e.g. `2026-09-ai-piece`
- `publication`: must match a `name` in `config/sources.yaml`
- `match_keywords`: comma-separated words that will ALL appear in the
  headline once published, e.g. `layoffs, hiring` — pick 2-3 distinctive words, not generic ones
- `status`: set to `pending` for anything not yet published
- `found_url` / `sent_date`: leave blank, the script fills these in

**`Contacts`** — columns, exactly in this order:
| article_id | contact_name | contact_email | custom_note | group |
|---|---|---|---|---|

- `article_id`: matches the row in `Articles`
- 'contact_name': first name of source
- 'contact_email' : source's email
- `custom_note`: optional — anything extra you want added to that
  one contact's email
- 'group': optional - article_id if you want multiple sources to all be in the same email otherwise leave blank

Add multiple rows to `Contacts` with the same `article_id` for multi-source articles.


### Keeping the Gmail token alive (while the app is in "Testing" mode) 

Google expires `GMAIL_REFRESH_TOKEN` every ~7 days as long as your OAuth app's publishing status is "Testing" (the normal status for a personal, single-user tool like this — going to "Production" requires domainownership and a public privacy policy, which isn't worth it here).

I setup an automation that simplifies the renewal process with macOS's LaunchAgents running refresh_gmail_token.sh

Every Monday at 9am (only while your Mac is awake and logged in — it won't fire if the machine is asleep or off), a browser tab will pop open asking you to log in as the notifications account and click Allow. That's the only manual step; the new token gets pushed to GitHub automatically right after.

You can also just run `./scripts/refresh_gmail_token.sh` manually any time you see an `invalid_grant` error in the Actions log, without waiting for the schedule.

To remove the schedule later: `launchctl unload ~/Library/LaunchAgents com.articlenotifier.refreshtoken.plist`



### Ongoing use 

Whenever you line up an article with sources, just add a row to `Articles` and matching rows to `Contacts` before or right after publication. That's the entire manual step — the rest runs itself.

Whenever you write for a new publication, just add it to the spreadsheet



### Notes and limitations 

- Matching is keyword-based since the exact headline isn't known in advance. Pick distinctive keywords to avoid false matches, and check `found_url` after the first few real sends.

- If a publication has no public RSS feed, another detection method is needed.

- GitHub's free tier is more than enough for a 30-minute schedule long-term.

