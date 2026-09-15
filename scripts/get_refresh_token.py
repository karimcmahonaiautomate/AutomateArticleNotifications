"""
Run this ONCE, locally on your own computer, logged in as your dedicated
notifications Gmail account (not your main account).

It opens a browser window, asks you to log in and grant permission to
send email, then prints a refresh token. Paste that refresh token into
your GitHub repo secrets as GMAIL_REFRESH_TOKEN.

Setup before running:
1. Go to https://console.cloud.google.com/ and create a new project
   (or reuse one).
2. Enable the "Gmail API" for that project.
3. Go to "APIs & Services" > "Credentials" > "Create Credentials" >
   "OAuth client ID". Choose "Desktop app". Download the JSON file
   and save it in this folder as credentials.json.
4. Make sure your OAuth consent screen has the scope:
   https://www.googleapis.com/auth/gmail.send
5. Run: pip install google-auth-oauthlib
6. Run: python get_refresh_token.py
7. Log in AS THE DEDICATED NOTIFICATIONS ACCOUNT when the browser opens.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def main():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n\n=== SAVE THESE AS GITHUB SECRETS ===")
    print(f"GMAIL_CLIENT_ID={creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET={creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("=====================================\n")
    print("Go to your GitHub repo > Settings > Secrets and variables > Actions")
    print("and add each of the three values above as a separate secret.")

if __name__ == "__main__":
    main()
