# /config/workspace/todo-app/backend/workflows/script/dsar.py

import re
from typing import Dict, Any

# A common regex pattern for basic email validation.
# For production, consider using a more robust validation library if needed.
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def validate_website_account(website_account_info: Dict[str, Any]) -> bool:
    """
    Validates the essential fields within the website account information.

    Checks if:
    1.  'account_name' is present and not empty.
    2.  'account_email' is present and matches a valid email format.
    3.  'compliance_contact' is present and matches a valid email format.

    Args:
        website_account_info: A dictionary containing the website account details,
                              typically derived from WebsiteAccount.to_dict().

    Returns:
        True if all validation checks pass, False otherwise. Prints error messages
        for failed checks.
    """
    if not isinstance(website_account_info, dict):
        print("Validation Error: Input 'website_account_info' is not a dictionary.")
        return False

    # 1. Validate account_name
    account_name = website_account_info.get('account_name')
    if not account_name:  # Checks for None, empty string '', etc.
        print("Validation Error: 'account_name' is missing or empty.")
        return False

    # 2. Validate account_email
    account_email = website_account_info.get('account_email')
    if not account_email or not re.match(EMAIL_REGEX, account_email):
        print(f"Validation Error: 'account_email' ('{account_email}') is missing or not a valid email format.")
        return False

    # 3. Validate compliance_contact
    # Note: The WebsiteAccount model allows this field to be nullable.
    # However, the request requires it to be a valid email for this validation step.
    compliance_contact = website_account_info.get('compliance_contact')
    if not compliance_contact or not re.match(EMAIL_REGEX, compliance_contact):
        print(f"Validation Error: 'compliance_contact' ('{compliance_contact}') is missing or not a valid email format.")
        return False

    # If all checks passed
    print("Website account info validation successful.")
    return True

# Example Usage (optional, for testing):
# if __name__ == '__main__':
#     valid_info = {
#         'id': 1, 'user_id': 1, 'website_url': 'http://example.com',
#         'account_name': 'testuser', 'account_email': 'test@example.com',
#         'compliance_contact': 'compliance@example.com'
#     }
#     invalid_name_info = {
#         'id': 2, 'user_id': 1, 'website_url': 'http://example.org',
#         'account_name': '', 'account_email': 'test@example.org',
#         'compliance_contact': 'compliance@example.org'
#     }
#     invalid_email_info = {
#         'id': 3, 'user_id': 1, 'website_url': 'http://example.net',
#         'account_name': 'testuser3', 'account_email': 'test@example', # Invalid email
#         'compliance_contact': 'compliance@example.net'
#     }
#     missing_compliance_info = {
#         'id': 4, 'user_id': 1, 'website_url': 'http://example.co',
#         'account_name': 'testuser4', 'account_email': 'test@example.co',
#         'compliance_contact': None # Missing compliance contact
#     }
#
#     print(f"Valid Info Test: {validate_website_account(valid_info)}")
#     print(f"Invalid Name Test: {validate_website_account(invalid_name_info)}")
#     print(f"Invalid Email Test: {validate_website_account(invalid_email_info)}")
#     print(f"Missing Compliance Test: {validate_website_account(missing_compliance_info)}")

