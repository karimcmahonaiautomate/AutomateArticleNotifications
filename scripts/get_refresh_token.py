"""
Run this locally, logged in as your dedicated notifications Gmail
account (not your main account), whenever GMAIL_REFRESH_TOKEN expires
(Google expires it every ~7 days while the OAuth app is in "Testing"
status).

It opens a browser window, asks you to log in and grant permission to
send email, then automatically pushes the new refresh token into your
GitHub repo's GMAIL_REFRESH_TOKEN secret using the GitHub CLI (gh).
GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET don't change between runs, so
those are only printed, not re-pushed.

One-time setup before first use:
1. Go to https://console.cloud.google.com/ and create a project
   (or reuse one), enable the Gmail API, and create an OAuth client
   (Desktop app type). Download it and save as credentials.json in
   this same folder.
2. Install the GitHub CLI: brew install gh
3. Authenticate it once: gh auth login
4. pip install google-auth-oauthlib

Run it with: python get_refresh_token.py
"""

import subprocess
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
REPO_ROOT = Path(__file__).resolve().parent.parent


def push_secret_to_github(name: str, value: str) -> bool:
    try:
        subprocess.run(
            ["gh", "secret", "set", name, "--body", value],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except FileNotFoundError:
        print("  'gh' command not found — is the GitHub CLI installed? (brew install gh)")
        return False
    except subprocess.CalledProcessError as e:
        print(f"  gh command failed: {e.stderr.strip()}")
        return False


def main():
    creds_path = Path(__file__).resolve().parent / "credentials.json"
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n=== New credentials obtained ===")
    print(f"GMAIL_CLIENT_ID={creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET={creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")

    print("\nPushing new refresh token to GitHub secret GMAIL_REFRESH_TOKEN...")
    ok = push_secret_to_github("GMAIL_REFRESH_TOKEN", creds.refresh_token)

    if ok:
        print("Done — GMAIL_REFRESH_TOKEN updated on GitHub.")
    else:
        print("\nAutomatic push failed. Copy the GMAIL_REFRESH_TOKEN value above")
        print("and paste it manually into: repo > Settings > Secrets and")
        print("variables > Actions > GMAIL_REFRESH_TOKEN > Update.")
        sys.exit(1)


if __name__ == "__main__":
    main()
