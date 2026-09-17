"""
Scans RSS feeds for newly published articles that match rows marked
"pending" in your Google Sheet, then emails the linked contacts and
marks the row "sent".

Runs unattended via GitHub Actions on a schedule (see
.github/workflows/scan.yml), but you can also run it locally with:
    python scan_and_notify.py

Environment variables required (set as GitHub Actions secrets):
    GOOGLE_SERVICE_ACCOUNT_JSON  - full JSON key for a service account
                                   with access to your Sheet
    SHEET_ID                     - the Google Sheet ID (from its URL)
    GMAIL_CLIENT_ID
    GMAIL_CLIENT_SECRET
    GMAIL_REFRESH_TOKEN
    MAIN_EMAIL                   - your real inbox, used as Reply-To
    SENDER_EMAIL                 - the dedicated Gmail address itself
    DRY_RUN                      - optional, "true" to log matches
                                   without sending or updating the Sheet
"""

import base64
import json
import os
import sys
from datetime import date
from email import charset as email_charset
from email.mime.text import MIMEText

import feedparser
import gspread
import yaml
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build

# Force base64 body encoding for UTF-8 text instead of the default
# quoted-printable, which inserts soft line-wrap characters that some
# email clients don't stitch back together cleanly.
email_charset.add_charset("utf-8", email_charset.SHORTEST, email_charset.BASE64, "utf-8")

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

ARTICLES_TAB = "Articles"
CONTACTS_TAB = "Contacts"

# Articles tab columns
COL_ARTICLE_ID = "article_id"
COL_PUBLICATION = "publication"
COL_KEYWORDS = "match_keywords"
COL_STATUS = "status"
COL_FOUND_URL = "found_url"
COL_SENT_DATE = "sent_date"

# Contacts tab columns
COL_CONTACT_ARTICLE_ID = "article_id"
COL_CONTACT_NAME = "contact_name"
COL_CONTACT_EMAIL = "contact_email"
COL_CUSTOM_NOTE = "custom_note"


def load_sources():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "config", "sources.yaml")) as f:
        cfg = yaml.safe_load(f)
    return {p["name"].strip().lower(): p["rss_url"] for p in cfg["publications"]}


def open_sheet():
    sa_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = ServiceAccountCredentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(os.environ["SHEET_ID"])


def get_gmail_service():
    creds = Credentials(
        None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.send"],
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def send_email(service, to_email, to_name, subject, body_text):
    msg = MIMEText(body_text)
    msg["to"] = to_email
    msg["from"] = os.environ["SENDER_EMAIL"]
    msg["reply-to"] = os.environ["MAIN_EMAIL"]
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    if DRY_RUN:
        print(f"  [DRY RUN] Would send to {to_name} <{to_email}>: {subject}")
        return
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"  Sent to {to_name} <{to_email}>")


def build_email_body(contact_name, publication, article_url, custom_note):
    greeting = f"Hi {contact_name}," if contact_name else "Hi,"
    note_block = f"\n{custom_note}\n" if custom_note else ""
    return (
        f"{greeting}\n\n"
        f"Thanks again for speaking with me. The article is now live on "
        f"{publication}:\n\n{article_url}\n"
        f"{note_block}\n"
        f"Thanks again for your time and insights!\n\n"
        f"Best,\n"
        f"Kari\n"
        f"(P.S. This is an automated email. Replies to this email are sent to my main address.)\n\n"
        f"(I may not be immediately available to respond to your email, but I will get back to you as soon as possible.)\n\n"
    )


def main():
    sources = load_sources()
    sheet = open_sheet()

    articles_ws = sheet.worksheet(ARTICLES_TAB)
    contacts_ws = sheet.worksheet(CONTACTS_TAB)

    articles = articles_ws.get_all_records()
    contacts = contacts_ws.get_all_records()

    pending = [
        (i + 2, row)  # +2: header row + 1-indexing, for later cell updates
        for i, row in enumerate(articles)
        if str(row.get(COL_STATUS, "")).strip().lower() == "pending"
    ]

    if not pending:
        print("No pending articles. Nothing to do.")
        return

    # Only fetch feeds we actually need this run.
    needed_pubs = {row[COL_PUBLICATION].strip().lower() for _, row in pending}
    feed_entries = {}
    for pub in needed_pubs:
        rss_url = sources.get(pub)
        if not rss_url:
            print(f"WARNING: no RSS feed configured for publication '{pub}' — skipping.")
            continue
        parsed = feedparser.parse(rss_url)
        feed_entries[pub] = parsed.entries
        print(f"Fetched {len(parsed.entries)} entries for {pub}")

    gmail_service = None if DRY_RUN else get_gmail_service()

    for row_num, article in pending:
        pub = article[COL_PUBLICATION].strip().lower()
        keywords = [
            k.strip().lower()
            for k in str(article.get(COL_KEYWORDS, "")).split(",")
            if k.strip()
        ]
        if not keywords:
            print(f"Row {row_num}: no match_keywords set, skipping.")
            continue

        entries = feed_entries.get(pub, [])
        match = None
        for entry in entries:
            title = entry.get("title", "").lower()
            if all(kw in title for kw in keywords):
                match = entry
                break

        if not match:
            continue

        article_id = article[COL_ARTICLE_ID]
        article_url = match.get("link", "")
        print(f"MATCH: article_id={article_id} -> {article_url}")

        linked_contacts = [
            c for c in contacts
            if str(c.get(COL_CONTACT_ARTICLE_ID, "")).strip() == str(article_id).strip()
        ]
        if not linked_contacts:
            print(f"  No contacts found for article_id {article_id} — skipping send.")
            continue

        for contact in linked_contacts:
            body = build_email_body(
                contact.get(COL_CONTACT_NAME, ""),
                article[COL_PUBLICATION],
                article_url,
                contact.get(COL_CUSTOM_NOTE, ""),
            )
            subject = f"Your interview is live in {article[COL_PUBLICATION]}"
            send_email(
                gmail_service,
                contact[COL_CONTACT_EMAIL],
                contact.get(COL_CONTACT_NAME, ""),
                subject,
                body,
            )

        if not DRY_RUN:
            header = articles_ws.row_values(1)
            status_col = header.index(COL_STATUS) + 1
            url_col = header.index(COL_FOUND_URL) + 1
            date_col = header.index(COL_SENT_DATE) + 1
            articles_ws.update_cell(row_num, status_col, "sent")
            articles_ws.update_cell(row_num, url_col, article_url)
            articles_ws.update_cell(row_num, date_col, str(date.today()))

    print("Done.")


if __name__ == "__main__":
    main()
