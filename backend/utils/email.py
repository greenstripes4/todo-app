# /config/workspace/todo-app/backend/utils/email.py
import os.path
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---

# Define the scopes required by the application.
# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',      # To send emails
    'https://www.googleapis.com/auth/gmail.readonly'   # To read emails
]

# Define paths relative to this file's location (backend/utils/)
# Adjust CREDENTIALS_PATH if you place credentials.json elsewhere
UTILS_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.dirname(UTILS_DIR)
# Assumes a 'config' directory at the same level as 'routes', 'models', etc.
CONFIG_DIR = os.path.join(BACKEND_DIR, 'config')
CREDENTIALS_PATH = os.path.join(CONFIG_DIR, 'credentials.json')
TOKEN_PATH = os.path.join(CONFIG_DIR, 'token.json')

logger = logging.getLogger(__name__)

class GmailUtils:
    """
    A utility class to interact with the Gmail API for sending and receiving emails.

    Handles OAuth 2.0 authentication and provides simplified methods for
    common email operations.
    """
    def __init__(self):
        """Initializes the GmailUtils class and authenticates the user."""
        self.service = self._authenticate()

    def _authenticate(self):
        """
        Handles the OAuth 2.0 authentication flow for the Gmail API.

        Loads existing credentials or initiates the flow if needed.
        Returns:
            googleapiclient.discovery.Resource: An authorized Gmail API service instance.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first time.
        if os.path.exists(TOKEN_PATH):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            except Exception as e:
                logger.error(f"Error loading token file {TOKEN_PATH}: {e}")
                creds = None # Force re-authentication if token file is corrupted

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Credentials expired, refreshing token...")
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    # If refresh fails, force re-authentication
                    creds = self._run_auth_flow()
            else:
                # Run the full authentication flow
                 creds = self._run_auth_flow()

            # Save the credentials for the next run
            if creds:
                try:
                    with open(TOKEN_PATH, 'w') as token:
                        token.write(creds.to_json())
                    logger.info(f"Credentials saved to {TOKEN_PATH}")
                except Exception as e:
                    logger.error(f"Error saving token file {TOKEN_PATH}: {e}")
            else:
                 logger.error("Failed to obtain valid credentials.")
                 return None # Cannot proceed without credentials

        try:
            service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service built successfully.")
            return service
        except Exception as e:
            logger.error(f"Error building Gmail service: {e}")
            return None

    def _run_auth_flow(self):
        """Runs the installed application flow to get user consent."""
        if not os.path.exists(CREDENTIALS_PATH):
            logger.error(f"Credentials file not found at {CREDENTIALS_PATH}. "
                         "Download it from Google Cloud Console and place it there.")
            return None
        try:
            logger.info("No valid token found, running authentication flow...")
            # Note: InstalledAppFlow is suitable for CLI/Desktop apps.
            # For web servers, you'd typically use google_auth_oauthlib.web.Flow
            # and handle redirects. This example uses InstalledAppFlow for simplicity,
            # which might require running the backend *once* interactively to authorize.
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES, redirect_uri='http://localhost')
            # You might need to adjust the port or use device_flow=True depending on environment
            # creds = flow.run_local_server(port=0)

            # Modify the process for server side script
            auth_url, _ = flow.authorization_url(prompt='consent')  # Get authorization URL
            print(f'Please visit this URL to authorize the application: {auth_url}')
            print('Enter the authorization code from the page:')
            auth_code = input()  # You'll need to manually copy and paste the code
            token = flow.fetch_token(code=auth_code)
            print(f'token:{token}')
            creds = flow.credentials

            logger.info("Authentication flow completed.")
            return creds
        except FileNotFoundError:
             logger.error(f"Credentials file missing at: {CREDENTIALS_PATH}")
             return None
        except Exception as e:
            logger.error(f"Error during authentication flow: {e}")
            return None

    def send_email(self, to_email: str, subject: str, body_text: str, sender_email: str = 'me'):
        """
        Sends an email using the authenticated Gmail account.

        Args:
            to_email (str): The recipient's email address.
            subject (str): The subject of the email.
            body_text (str): The plain text body of the email.
            sender_email (str): The sender's email address ('me' for the authenticated user).

        Returns:
            dict: The sent message resource, or None if an error occurred.
        """
        if not self.service:
            logger.error("Gmail service not available. Cannot send email.")
            return None

        try:
            message = MIMEText(body_text)
            message['to'] = to_email
            message['from'] = sender_email
            message['subject'] = subject

            # Encode the message in base64url format
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {'raw': encoded_message}

            # Send the message using the Gmail API
            send_message = (self.service.users().messages()
                            .send(userId=sender_email, body=create_message).execute())
            logger.info(f"Email sent successfully to {to_email}. Message ID: {send_message['id']}")
            return send_message

        except HttpError as error:
            logger.error(f'An HTTP error occurred while sending email: {error}')
            return None
        except Exception as e:
            logger.error(f'An unexpected error occurred while sending email: {e}')
            return None

    def list_emails(self, query: str = 'is:unread', max_results: int = 10, user_id: str = 'me'):
        """
        Lists emails matching a specific query.

        Args:
            query (str): Gmail search query (e.g., 'is:unread', 'from:example.com').
            max_results (int): Maximum number of emails to return.
            user_id (str): User ID ('me' for the authenticated user).

        Returns:
            list: A list of message IDs matching the query, or None if an error occurs.
        """
        if not self.service:
            logger.error("Gmail service not available. Cannot list emails.")
            return None
        try:
            response = self.service.users().messages().list(
                userId=user_id,
                q=query,
                maxResults=max_results
            ).execute()

            messages = response.get('messages', [])
            message_ids = [msg['id'] for msg in messages]
            logger.info(f"Found {len(message_ids)} emails matching query: '{query}'")
            return message_ids

        except HttpError as error:
            logger.error(f'An HTTP error occurred while listing emails: {error}')
            return None
        except Exception as e:
            logger.error(f'An unexpected error occurred while listing emails: {e}')
            return None

    def get_email_details(self, message_id: str, user_id: str = 'me', format: str = 'metadata'):
        """
        Retrieves details of a specific email.

        Args:
            message_id (str): The ID of the message to retrieve.
            user_id (str): User ID ('me' for the authenticated user).
            format (str): Format of the returned message ('full', 'metadata', 'raw', 'minimal').
                          'metadata' includes headers like From, To, Subject.
                          'full' includes the payload (body).

        Returns:
            dict: The message resource, or None if an error occurred.
        """
        if not self.service:
            logger.error("Gmail service not available. Cannot get email details.")
            return None
        try:
            message = self.service.users().messages().get(
                userId=user_id,
                id=message_id,
                format=format # 'metadata', 'full', 'raw'
            ).execute()
            # logger.debug(f"Retrieved details for message ID: {message_id}") # Use debug for potentially large output
            return message

        except HttpError as error:
            logger.error(f'An HTTP error occurred while getting email details for {message_id}: {error}')
            return None
        except Exception as e:
            logger.error(f'An unexpected error occurred while getting email details for {message_id}: {e}')
            return None

    def parse_email_body(self, message_payload: dict) -> str:
        """
        Parses the body from a message payload.
        Attempts to find plain text first, then HTML.

        Args:
            message_payload (dict): The 'payload' part of a message resource (from get_email_details format='full').

        Returns:
            str: The decoded email body, or an empty string if not found/decodable.
        """
        body = ""
        if not message_payload:
            return body

        mime_type = message_payload.get('mimeType', '')
        # logger.debug(f"Parsing payload with MIME type: {mime_type}")

        if 'parts' in message_payload:
            # Handle multipart messages (common)
            plain_text_part = None
            html_part = None
            for part in message_payload['parts']:
                part_mime_type = part.get('mimeType', '')
                # Recurse if nested multipart
                if 'parts' in part:
                    nested_body = self.parse_email_body(part)
                    if nested_body:
                        return nested_body # Return first found body from nested parts
                elif part_mime_type == 'text/plain' and 'data' in part.get('body', {}):
                    plain_text_part = part
                    # Prefer plain text, decode and return immediately
                    try:
                        body_data = part['body']['data']
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        # logger.debug("Found and decoded plain text body.")
                        return body
                    except Exception as e:
                        logger.warning(f"Could not decode plain text part: {e}")

                elif part_mime_type == 'text/html' and 'data' in part.get('body', {}):
                    html_part = part # Keep track of HTML in case plain text fails

            # If plain text wasn't found or decoded, try HTML
            if html_part:
                 try:
                    body_data = html_part['body']['data']
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                    # logger.debug("Found and decoded HTML body (as fallback).")
                    return body # Return decoded HTML
                 except Exception as e:
                    logger.warning(f"Could not decode HTML part: {e}")

        elif mime_type == 'text/plain' and 'data' in message_payload.get('body', {}):
             # Handle simple plain text message
             try:
                body_data = message_payload['body']['data']
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                # logger.debug("Found and decoded simple plain text body.")
                return body
             except Exception as e:
                logger.warning(f"Could not decode simple plain text body: {e}")

        elif mime_type == 'text/html' and 'data' in message_payload.get('body', {}):
             # Handle simple HTML message (less common for top level)
             try:
                body_data = message_payload['body']['data']
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                # logger.debug("Found and decoded simple HTML body.")
                return body
             except Exception as e:
                logger.warning(f"Could not decode simple HTML body: {e}")

        logger.warning("Could not find a decodable text/plain or text/html body part.")
        return body # Return empty string if nothing suitable found


# --- Example Usage (Optional - for testing) ---
if __name__ == '__main__':
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print("Attempting to initialize GmailUtils...")
    # NOTE: The first time this runs, it will likely open a browser window
    # for you to authorize the application.
    gmail = GmailUtils()

    if gmail.service:
        print("\nGmailUtils initialized successfully.")

        # --- Test Sending ---
        # print("\n--- Testing Send Email ---")
        # recipient = "your_test_recipient@example.com" # CHANGE THIS
        # subject = "Gmail API Test from Utils"
        # body = "Hello from the GmailUtils class!\n\nThis is a test email."
        # sent_message = gmail.send_email(recipient, subject, body)
        # if sent_message:
        #     print(f"Send test successful. Message ID: {sent_message.get('id')}")
        # else:
        #     print("Send test failed.")

        # --- Test Listing ---
        print("\n--- Testing List Emails (Unread) ---")
        unread_ids = gmail.list_emails(query='is:unread', max_results=5)
        if unread_ids is not None:
            print(f"Found {len(unread_ids)} unread email IDs: {unread_ids}")

            # --- Test Getting Details & Parsing ---
            if unread_ids:
                test_id = unread_ids[0]
                print(f"\n--- Testing Get Email Details (Full) for ID: {test_id} ---")
                details = gmail.get_email_details(test_id, format='full')
                if details:
                    # Extract basic info
                    headers = details.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'N/A')
                    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'N/A')
                    print(f"  Subject: {subject}")
                    print(f"  From: {sender}")
                    print(f"  Snippet: {details.get('snippet', 'N/A')}")

                    print(f"\n--- Testing Parse Email Body for ID: {test_id} ---")
                    body_content = gmail.parse_email_body(details.get('payload'))
                    if body_content:
                         print("  Body Found (first 200 chars):")
                         print(body_content[:200] + "...")
                    else:
                         print("  Could not parse body.")
                else:
                    print(f"Failed to get details for message ID: {test_id}")
        else:
            print("Failed to list emails.")

    else:
        print("\nFailed to initialize GmailUtils. Check logs and credentials.")

