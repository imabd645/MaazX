import os
import json
import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

import database as db

# If modifying these scopes, delete the token from the database.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailHandler:
    def __init__(self, credentials_path='credentials.json'):
        self.credentials_path = credentials_path
        self.redirect_uri = 'http://localhost:5000/api/gmail/callback'

    def get_auth_url(self):
        """Generates the Google authorization URL."""
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Missing {self.credentials_path}. Please follow the setup instructions.")
        
        flow = Flow.from_client_secrets_file(
            self.credentials_path,
            scopes=SCOPES,
            redirect_uri=self.redirect_uri
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        
        # PKCE: Save the verifier for the callback
        settings = db.load_settings()
        settings['gmail_code_verifier'] = flow.code_verifier
        db.save_settings(settings)
        
        return auth_url

    def handle_callback(self, code):
        """Exchanges authorization code for tokens and saves to DB."""
        print(f"[Gmail] Callback received with code: {code[:10]}...")
        settings = db.load_settings()
        verifier = settings.get('gmail_code_verifier')
        print(f"[Gmail] Using code_verifier: {verifier[:10]}..." if verifier else "[Gmail] No code_verifier found!")
        
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_path,
                scopes=SCOPES,
                redirect_uri=self.redirect_uri
            )
            flow.fetch_token(code=code, code_verifier=verifier)
            credentials = flow.credentials
            
            token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            settings['gmail_token'] = json.dumps(token_data)
            # Clear verifier after use
            if 'gmail_code_verifier' in settings:
                del settings['gmail_code_verifier']
                
            db.save_settings(settings)
            print("[Gmail] Token saved successfully.")
            return True
        except Exception as e:
            print(f"[Gmail] ERROR in handle_callback: {str(e)}")
            raise e

    def get_service(self):
        """Returns an authorized Gmail API service instance."""
        settings = db.load_settings()
        token_json = settings.get('gmail_token')
        
        if not token_json:
            return None
            
        try:
            token_data = json.loads(token_json)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Update saved token
                token_data['token'] = creds.token
                settings['gmail_token'] = json.dumps(token_data)
                db.save_settings(settings)
                
            return build('gmail', 'v1', credentials=creds)
        except Exception as e:
            print(f"[Gmail] Error building service: {e}")
            return None

    def search_messages(self, query, max_results=10):
        """Search for messages matching the query."""
        service = self.get_service()
        if not service:
            return {"error": "Gmail not authenticated"}
            
        try:
            results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            output = []
            for msg in messages:
                m = service.users().messages().get(userId='me', id=msg['id'], format='minimal').execute()
                snippet = m.get('snippet', '')
                output.append({"id": msg['id'], "snippet": snippet})
            return output
        except Exception as e:
            return {"error": str(e)}

    def read_message(self, message_id):
        """Read a specific message's full content."""
        service = self.get_service()
        if not service:
            return {"error": "Gmail not authenticated"}
            
        try:
            m = service.users().messages().get(userId='me', id=message_id, format='full').execute()
            payload = m.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            snippet = m.get('snippet', '')
            return {
                "id": message_id,
                "from": sender,
                "subject": subject,
                "date": date,
                "snippet": snippet
            }
        except Exception as e:
            return {"error": str(e)}

    def send_email(self, recipient, subject, body):
        """Sends an email using the Gmail API."""
        from core.utils import strip_markdown
        plain_body = strip_markdown(body)
        
        service = self.get_service()
        if not service:
            return f"Error sending email: Gmail not authenticated."

        message = MIMEText(plain_body)
        message['to'] = recipient
        message['subject'] = subject
        create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
        
        try:
            message = (service.users().messages().send(userId="me", body=create_message).execute())
            print(f'[Gmail] Message Id: {message["id"]} sent to {recipient}')
            return f"Email sent successfully to {recipient}. Message ID: {message['id']}"
        except Exception as error:
            print(f'[Gmail] An error occurred: {error}')
            return f"Error sending email: {error}"

gmail_handler = GmailHandler()
