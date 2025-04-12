# /config/workspace/todo-app/backend/routes/website_account.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models.user import User
from models.website_account import WebsiteAccount
from app import db

website_account_bp = Blueprint('website_account', __name__, url_prefix='/website-accounts')

# Helper function to get the current user and their role
def get_current_user_and_role():
    """Retrieves the current user object and their role based on JWT identity and claims."""
    username = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get('role', 'normal') # Default to 'normal' if role claim is missing
    user = User.query.filter_by(username=username).first()
    return user, user_role

# --- Create ---
@website_account_bp.route('', methods=['POST'])
@jwt_required()
def create_website_account():
    """Creates a new website account for the logged-in user."""
    current_user, _ = get_current_user_and_role() # Role not needed here, but use consistent helper
    if not current_user:
        # This case should ideally not happen if @jwt_required works,
        # but it's good practice for robustness.
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    website_url = data.get('website_url')
    account_email = data.get('account_email')
    account_name = data.get('account_name') # Optional
    compliance_contact = data.get('compliance_contact') # Optional

    if not website_url or not account_email:
        return jsonify({'message': 'Website URL and Account Email are required'}), 400

    new_account = WebsiteAccount(
        user_id=current_user.id,
        website_url=website_url,
        account_name=account_name,
        account_email=account_email,
        compliance_contact=compliance_contact
    )

    db.session.add(new_account)
    db.session.commit()

    return jsonify({'message': 'Website account created successfully', 'account': new_account.to_dict()}), 201

# --- Read (List) ---
# Note: This still only lists accounts for the *logged-in* user.
# If admins should see *all* accounts, this endpoint would need modification.
@website_account_bp.route('', methods=['GET'])
@jwt_required()
def get_website_accounts():
    """Retrieves all website accounts for the logged-in user."""
    current_user, _ = get_current_user_and_role()
    if not current_user:
        return jsonify({'message': 'User not found'}), 404

    # Consider adding pagination for large lists
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int) # Default 10 per page

    paginated_accounts = WebsiteAccount.query.filter_by(user_id=current_user.id)\
                                             .paginate(page=page, per_page=per_page, error_out=False)

    accounts_list = [account.to_dict() for account in paginated_accounts.items]

    pagination_metadata = {
        'total_pages': paginated_accounts.pages,
        'current_page': paginated_accounts.page,
        'per_page': paginated_accounts.per_page,
        'total_items': paginated_accounts.total
    }

    return jsonify({'accounts': accounts_list, 'pagination': pagination_metadata}), 200

# --- Read (Detail) ---
@website_account_bp.route('/<int:account_id>', methods=['GET'])
@jwt_required()
def get_website_account_detail(account_id):
    """Retrieves a specific website account by its ID. Accessible by owner or admin."""
    current_user, current_user_role = get_current_user_and_role()
    if not current_user:
        return jsonify({'message': 'User not found'}), 404

    account = WebsiteAccount.query.get(account_id)

    if not account:
        return jsonify({'message': 'Website account not found'}), 404

    # --- Authorization Check ---
    # Allow if the user owns the account OR if the user is an admin
    if account.user_id != current_user.id and current_user_role != 'admin':
        return jsonify({'message': 'Forbidden: You do not have permission to view this account'}), 403
    # --- End Authorization Check ---

    return jsonify(account.to_dict()), 200

# --- Update ---
@website_account_bp.route('/<int:account_id>', methods=['PUT'])
@jwt_required()
def update_website_account(account_id):
    """Updates a specific website account. Accessible by owner or admin."""
    current_user, current_user_role = get_current_user_and_role()
    if not current_user:
        return jsonify({'message': 'User not found'}), 404

    account = WebsiteAccount.query.get(account_id)

    if not account:
        return jsonify({'message': 'Website account not found'}), 404

    # --- Authorization Check ---
    # Allow if the user owns the account OR if the user is an admin
    if account.user_id != current_user.id and current_user_role != 'admin':
        return jsonify({'message': 'Forbidden: You do not have permission to update this account'}), 403
    # --- End Authorization Check ---

    data = request.get_json()

    # Update fields if they are provided in the request data
    account.website_url = data.get('website_url', account.website_url)
    account.account_name = data.get('account_name', account.account_name)
    account.account_email = data.get('account_email', account.account_email)
    account.compliance_contact = data.get('compliance_contact', account.compliance_contact)

    # Validate required fields after potential update
    if not account.website_url or not account.account_email:
         return jsonify({'message': 'Website URL and Account Email cannot be empty'}), 400

    db.session.commit()

    return jsonify({'message': 'Website account updated successfully', 'account': account.to_dict()}), 200

# --- Delete ---
@website_account_bp.route('/<int:account_id>', methods=['DELETE'])
@jwt_required()
def delete_website_account(account_id):
    """Deletes a specific website account. Accessible by owner or admin."""
    current_user, current_user_role = get_current_user_and_role()
    if not current_user:
        return jsonify({'message': 'User not found'}), 404

    account = WebsiteAccount.query.get(account_id)

    if not account:
        return jsonify({'message': 'Website account not found'}), 404

    # --- Authorization Check ---
    # Allow if the user owns the account OR if the user is an admin
    if account.user_id != current_user.id and current_user_role != 'admin':
        return jsonify({'message': 'Forbidden: You do not have permission to delete this account'}), 403
    # --- End Authorization Check ---

    db.session.delete(account)
    db.session.commit()

    return jsonify({'message': 'Website account deleted successfully'}), 200
