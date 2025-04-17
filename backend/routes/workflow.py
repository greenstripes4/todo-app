# /config/workspace/todo-app/backend/routes/workflow.py
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
# Import joinedload for efficient relationship loading
from sqlalchemy.orm import joinedload
# Updated model imports
from models import User, WebsiteAccount, UserWorkflow, UserWorkflowTypeEnum, UserWorkflowStatusEnum
from app import db, engine, dsar_spec_id

workflow_bp = Blueprint('workflow', __name__, url_prefix='/workflows')

@workflow_bp.route('', methods=['POST'])
@jwt_required()
def create_workflows():
    """
    Creates new workflow records for specified website accounts.
    Expects a JSON payload:
    {
        "website_account_ids": [1, 2, 3],
        "workflow_type": "DSAR"
    }
    """
    current_user_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_user_username).first()

    if not current_user:
        # Should not happen with @jwt_required, but good practice
        return jsonify({"message": "Current user not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    website_account_ids = data.get('website_account_ids')
    workflow_type_str = data.get('workflow_type')

    # --- Input Validation ---
    if not isinstance(website_account_ids, list) or not website_account_ids:
        return jsonify({"message": "'website_account_ids' must be a non-empty list"}), 400

    if not workflow_type_str:
        return jsonify({"message": "'workflow_type' is required"}), 400

    try:
        # Validate and convert workflow_type string to Enum
        workflow_type_enum = UserWorkflowTypeEnum(workflow_type_str) # Updated Enum reference
    except ValueError:
        valid_types = [e.value for e in UserWorkflowTypeEnum] # Updated Enum reference
        return jsonify({"message": f"Invalid 'workflow_type'. Must be one of: {valid_types}"}), 400

    created_workflows_info = []
    errors = []

    # --- Process each account ID ---
    for account_id in website_account_ids:
        if not isinstance(account_id, int):
            errors.append({"account_id": account_id, "error": "ID must be an integer"})
            continue # Skip to the next ID

        # Find the website account
        account = WebsiteAccount.query.get(account_id)

        # Check if account exists and belongs to the current user
        if not account:
            errors.append({"account_id": account_id, "error": "Website account not found"})
            continue
        if account.user_id != current_user.id:
            # Security check: User can only create workflows for their own accounts
            errors.append({"account_id": account_id, "error": "Forbidden: You do not own this website account"})
            continue

        # Start a workflow instance and run it
        workflow_instance = engine.start_workflow(dsar_spec_id)
        start_task = workflow_instance.ready_tasks[0]
        start_task.data['user_info'] = {'name': account.account_name, 'email': account.account_email}
        workflow_instance.run_until_user_input_required() # Or workflow_instance.complete() if no user tasks
        unique_workflow_id = workflow_instance.wf_id

        # Create the new workflow record
        new_workflow = UserWorkflow( # Updated class reference
            user_id=current_user.id,
            website_account_id=account.id,
            workflow_id=unique_workflow_id,
            workflow_type=workflow_type_enum,
            workflow_status=UserWorkflowStatusEnum.PENDING # Updated Enum reference (Default status)
        )
        db.session.add(new_workflow)
        # We collect info before commit in case the commit fails later
        created_workflows_info.append({
            "website_account_id": account.id,
            "workflow_instance_id": unique_workflow_id # Use the generated unique ID
        })

    # --- Handle potential errors during processing ---
    if errors:
        # If there were errors, we should probably not commit *any* workflows
        # to maintain atomicity, unless partial success is acceptable.
        # For now, let's rollback if any error occurred.
        db.session.rollback()
        return jsonify({
            "message": "Failed to create some or all workflows due to errors.",
            "errors": errors
        }), 400 # Or 422 Unprocessable Entity might be suitable

    # --- Commit and Respond ---
    try:
        db.session.commit()
        return jsonify({
            "message": f"Successfully created {len(created_workflows_info)} workflow(s).",
            "created_workflows": created_workflows_info
        }), 201 # 201 Created status code
    except Exception as e:
        db.session.rollback()
        # Log the exception e
        print(f"Database commit error: {e}") # Replace with proper logging
        return jsonify({"message": "An internal error occurred while saving workflows."}), 500

@workflow_bp.route('', methods=['GET'])
@jwt_required()
def get_workflows():
    """
    Retrieves all workflows created by the currently logged-in user,
    including associated website account details.
    Supports pagination via query parameters 'page' and 'per_page'.
    """
    current_user_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_user_username).first()

    if not current_user:
        # Should not happen with @jwt_required, but good practice
        return jsonify({"message": "Current user not found"}), 404

    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int) # Default 10 per page

    # Query workflows belonging to the current user with pagination
    # Use joinedload to efficiently fetch the related WebsiteAccount
    paginated_workflows = UserWorkflow.query.options( # Updated class reference
        joinedload(UserWorkflow.website_account) # Updated class reference
    ).filter(
        UserWorkflow.user_id == current_user.id # Updated class reference
    ).order_by(
        UserWorkflow.created_at.desc() # Updated class reference
    ).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Serialize the workflow objects, including website account details
    workflows_list = []
    for workflow in paginated_workflows.items:
        workflow_data = workflow.to_dict() # Assuming this returns basic workflow info

        # Add website account data if it exists
        if workflow.website_account:
            # Assuming WebsiteAccount has a to_dict() method or relevant attributes
            # If WebsiteAccount has a to_dict():
            # workflow_data['website_account'] = workflow.website_account.to_dict()

            # Or manually construct the dictionary:
            workflow_data['website_account'] = {
                'id': workflow.website_account.id,
                'website_url': getattr(workflow.website_account, 'website_url', None), # Use getattr for safety if unsure
                'account_name': getattr(workflow.website_account, 'account_name', None),
                'account_email': getattr(workflow.website_account, 'account_email', None),
                # Add any other relevant fields from WebsiteAccount model
            }
        else:
            # Handle cases where the account might somehow be null
            workflow_data['website_account'] = None

        workflows_list.append(workflow_data)


    # Prepare pagination metadata for the response
    pagination_metadata = {
        'total_pages': paginated_workflows.pages,
        'current_page': paginated_workflows.page,
        'per_page': paginated_workflows.per_page,
        'total_items': paginated_workflows.total
    }

    return jsonify({'workflows': workflows_list, 'pagination': pagination_metadata}), 200


# --- NEW ENDPOINT ---
@workflow_bp.route('/<string:workflow_instance_id>/status', methods=['PATCH'])
@jwt_required()
def update_workflow_status(workflow_instance_id):
    """
    Updates the status of a specific workflow instance.
    Expects a JSON payload:
    {
        "status": "COMPLETED"
    }
    Requires the workflow_instance_id (UUID string) in the URL path.
    """
    current_user_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_user_username).first()

    if not current_user:
        return jsonify({"message": "Current user not found"}), 404

    # --- Input Validation ---
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    new_status_str = data.get('status')
    if not new_status_str:
        return jsonify({"message": "'status' is required in the request body"}), 400

    try:
        # Validate and convert status string to Enum
        new_status_enum = UserWorkflowStatusEnum(new_status_str) # Updated Enum reference
    except ValueError:
        valid_statuses = [e.value for e in UserWorkflowStatusEnum] # Updated Enum reference
        return jsonify({"message": f"Invalid 'status'. Must be one of: {valid_statuses}"}), 400

    # --- Find and Authorize Workflow ---
    workflow = UserWorkflow.query.filter_by(workflow_id=workflow_instance_id).first() # Updated class reference

    if not workflow:
        return jsonify({"message": "Workflow not found"}), 404

    # Security check: Ensure the workflow belongs to the current user
    if workflow.user_id != current_user.id:
        return jsonify({"message": "Forbidden: You do not own this workflow"}), 403

    # --- Update and Commit ---
    try:
        workflow.workflow_status = new_status_enum
        db.session.commit()
        return jsonify({
            "message": "Workflow status updated successfully.",
            "workflow": workflow.to_dict() # Return updated workflow details
        }), 200
    except Exception as e:
        db.session.rollback()
        # Log the exception e
        print(f"Database commit error during status update: {e}") # Replace with proper logging
        return jsonify({"message": "An internal error occurred while updating the workflow status."}), 500
