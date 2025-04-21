# /config/workspace/todo-app/backend/routes/workflow.py
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
# Import joinedload for efficient relationship loading
from sqlalchemy.orm import joinedload
# Updated model imports
from models import User, WebsiteAccount, UserWorkflow, UserWorkflowTypeEnum, UserWorkflowStatusEnum # Updated class reference
from app import db, engine, dsar_spec_id # Make sure dsar_spec_id is correctly imported/available

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
        workflow_type_enum = UserWorkflowTypeEnum(workflow_type_str) # Updated Enum reference
    except ValueError:
        valid_types = [e.value for e in UserWorkflowTypeEnum] # Updated Enum reference
        return jsonify({"message": f"Invalid 'workflow_type'. Must be one of: {valid_types}"}), 400

    created_workflows_info = []
    errors = []
    workflows_to_commit = [] # Keep track of UserWorkflow objects to commit

    # --- Process each account ID ---
    for account_id in website_account_ids:
        if not isinstance(account_id, int):
            errors.append({"account_id": account_id, "error": "ID must be an integer"})
            continue

        account = WebsiteAccount.query.get(account_id)

        if not account:
            errors.append({"account_id": account_id, "error": "Website account not found"})
            continue
        if account.user_id != current_user.id:
            errors.append({"account_id": account_id, "error": "Forbidden: You do not own this website account"})
            continue

        try:
            # --- Step 1: Start the core workflow instance (creates Workflow & Instance records) ---
            # engine.start_workflow handles the commit for Workflow and Instance records internally
            workflow_instance = engine.start_workflow(dsar_spec_id)
            unique_workflow_id = str(workflow_instance.wf_id) # Get the UUID as string

            # --- Step 2: Create the UserWorkflow record ---
            new_user_workflow = UserWorkflow( # Updated class reference
                user_id=current_user.id,
                website_account_id=account.id,
                workflow_id=unique_workflow_id, # Use the string UUID
                workflow_type=workflow_type_enum,
                # Set initial status, maybe RUNNING if it starts right away? Or keep PENDING?
                # Let's assume it starts running, matching the update_workflow logic
                workflow_status=UserWorkflowStatusEnum.RUNNING # Updated Enum reference
            )
            db.session.add(new_user_workflow)
            workflows_to_commit.append(new_user_workflow) # Add to list for potential rollback

            # --- Step 3: Commit the UserWorkflow record *BEFORE* running tasks ---
            # Commit here ensures the UserWorkflow exists when callbacks fire
            db.session.commit()
            # Note: If engine.start_workflow didn't commit, you'd commit both here.
            # Assuming engine.start_workflow commits its part.

            # --- Step 4: Prepare and Run the workflow instance ---
            # Now it's safe to potentially trigger callbacks
            start_task = workflow_instance.ready_tasks[0]
            start_task.data['user_info'] = {'name': account.account_name, 'email': account.account_email}
            workflow_instance.run_until_user_input_required() # Or complete()

            # Collect info for the response
            created_workflows_info.append({
                "website_account_id": account.id,
                "workflow_instance_id": unique_workflow_id
            })

        except Exception as e:
            # If any error occurs for an account (including workflow start or UserWorkflow creation/commit)
            db.session.rollback() # Rollback the UserWorkflow commit for this specific account
            errors.append({"account_id": account_id, "error": f"Failed to process: {str(e)}"})
            # Log the full error e for debugging
            print(f"Error processing account {account_id}: {e}") # Replace with proper logging
            # Continue to the next account_id

    # --- Final Response ---
    if errors and not created_workflows_info:
        # All failed
        return jsonify({
            "message": "Failed to create workflows for all specified accounts.",
            "errors": errors
        }), 500 # Internal Server Error or 400/422 if input related
    elif errors:
        # Partial success
        return jsonify({
            "message": f"Successfully created {len(created_workflows_info)} workflow(s), but encountered errors with others.",
            "created_workflows": created_workflows_info,
            "errors": errors
        }), 207 # Multi-Status response
    else:
        # All succeeded
        return jsonify({
            "message": f"Successfully created {len(created_workflows_info)} workflow(s).",
            "created_workflows": created_workflows_info
        }), 201 # 201 Created status code


# --- Other routes (get_workflows, update_workflow_status) remain the same ---
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

