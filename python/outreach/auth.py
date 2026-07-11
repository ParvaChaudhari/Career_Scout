import os
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

def run_auth_flow():
    load_dotenv()
    
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Error: GMAIL_CLIENT_ID or GMAIL_CLIENT_SECRET not found in .env")
        return

    # Construct the client config dict dynamically
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    # The scope required to send/draft emails
    scopes = ["https://www.googleapis.com/auth/gmail.compose"]

    print("Opening browser for authentication...")
    flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
    
    # This opens a local web server and your browser
    creds = flow.run_local_server(port=0)

    print("\n" + "="*50)
    print("SUCCESS! Here is your new Refresh Token:")
    print("="*50)
    print(creds.refresh_token)
    print("="*50 + "\n")
    print("Please copy the string above and paste it as your GMAIL_REFRESH_TOKEN in .env")
