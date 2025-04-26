# /config/workspace/todo-app/backend/test_send_email.py
import logging
import os
import sys

# --- Path Setup ---
# Add the backend directory to the Python path
# This allows the script to find the 'utils' module
BACKEND_DIR = os.path.dirname(__file__)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    # Now we can import from the utils package
    from utils.email import GmailUtils
except ImportError as e:
    print(f"Error importing GmailUtils: {e}")
    print("Please ensure:")
    print("1. This script is in the 'backend' directory.")
    print("2. The 'utils' directory with 'email_utils.py' exists within 'backend'.")
    print("3. You have installed the required packages (google-api-python-client, etc.).")
    sys.exit(1)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Test Configuration ---
TEST_RECIPIENT_EMAIL = "your_test_recipient@example.com"
TEST_SUBJECT = "Standalone Gmail API Test with token generated"
TEST_BODY = """
Hello from the standalone test script!

This email confirms that the GmailUtils.send_email() function is working correctly.

Regards,
Your App
"""

def run_test():
    """
    Instantiates GmailUtils and attempts to send a test email.
    """
    if TEST_RECIPIENT_EMAIL == "your_test_recipient@example.com":
        logger.error("Hardcoded recipient email needs to be updated.")
        return

    logger.info("--- Starting Gmail Send Email Test ---")

    try:
        logger.info("Initializing GmailUtils...")
        # Note: The first time this runs, it might trigger the OAuth browser flow
        # if token.json is missing or invalid.
        gmail_client = GmailUtils()

        if not gmail_client.service:
            logger.error("Failed to initialize Gmail service. Cannot proceed.")
            return

        logger.info("GmailUtils initialized successfully.")
        logger.info(f"Attempting to send email to: {TEST_RECIPIENT_EMAIL}")

        # Call the send_email function
        sent_message = gmail_client.send_email(
            to_email=TEST_RECIPIENT_EMAIL,
            subject=TEST_SUBJECT,
            body_text=TEST_BODY
            # sender_email='me' is the default in GmailUtils
        )

        if sent_message and sent_message.get('id'):
            logger.info(f"SUCCESS: Email sent successfully!")
            logger.info(f"Message ID: {sent_message.get('id')}")
            logger.info(f"Label IDs: {sent_message.get('labelIds')}")
        else:
            logger.error("FAILURE: Sending email failed. Check previous logs for potential API errors.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during the test: {e}", exc_info=True)

    logger.info("--- Gmail Send Email Test Finished ---")

if __name__ == "__main__":
    run_test()
