# /config/workspace/todo-app/backend/routes/workflow.py
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
# Import joinedload for efficient relationship loading
from sqlalchemy.orm import joinedload, contains_eager # Import contains_eager
# Updated model imports
from models import User, WebsiteAccount, UserWorkflow, UserWorkflowTypeEnum, UserWorkflowStatusEnum # Updated class reference
from app import db, engine, dsar_spec_id
# Removed: from SpiffWorkflow.bpmn.specs.Workflow import WorkflowState
import logging # Import logging

# --- Existing Blueprint Setup ---
workflow_bp = Blueprint('workflow', __name__, url_prefix='/workflows')
logger = logging.getLogger(__name__) # Add logger for this module

# --- create_workflows function (keep as is) ---
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

    # --- Process each account ID ---
    for account_id in website_account_ids:
        if not isinstance(account_id, int):
            errors.append({"account_id": account_id, "error": "ID must be an integer"})
            continue

        account = WebsiteAccount.query.get(account_id)

        if not account:
            errors.append({"account_id": account_id, "error": "Website account not found"})
            continue
        # --- Authorization Check ---
        if account.user_id != current_user.id and current_user.role != 'admin': # Check role
            errors.append({"account_id": account_id, "error": "Forbidden: You do not own this website account"})
            continue
        # --- End Authorization Check ---


        try:
            # --- Step 1: Start the core workflow instance ---
            workflow_instance = engine.start_workflow(dsar_spec_id)
            unique_workflow_id = str(workflow_instance.wf_id) # Get the UUID as string

            # --- Step 2: Create the UserWorkflow record ---
            new_user_workflow = UserWorkflow(
                user_id=account.user_id,
                website_account_id=account.id,
                workflow_id=unique_workflow_id,
                workflow_type=workflow_type_enum,
                workflow_status=UserWorkflowStatusEnum.RUNNING
            )
            db.session.add(new_user_workflow)

            # --- Step 3: Commit the UserWorkflow record ---
            db.session.commit()

            # --- Step 4: Prepare and Run the workflow instance ---
            start_task = workflow_instance.ready_tasks[0]
            # Use the to_dict() method to pass all WebsiteAccount fields
            # Note: This includes id, user_id, website_url, account_name, account_email, compliance_contact
            start_task.data['website_account_info'] = account.to_dict() # Renamed key for clarity
            workflow_instance.run_until_user_input_required()

            # Collect info for the response
            created_workflows_info.append({
                "website_account_id": account.id,
                "user_workflow_id": new_user_workflow.id,
                "workflow_instance_id": unique_workflow_id
            })

        except Exception as e:
            db.session.rollback()
            error_msg = f"Failed to process: {str(e)}"
            errors.append({"account_id": account_id, "error": error_msg})
            logger.error(f"Error processing account {account_id}: {e}", exc_info=True)

    # --- Final Response ---
    status_code = 201
    response_data = {}

    if errors and not created_workflows_info:
        status_code = 500
        response_data = {
            "message": "Failed to create workflows for all specified accounts.",
            "errors": errors
        }
    elif errors:
        status_code = 207
        response_data = {
            "message": f"Successfully created {len(created_workflows_info)} workflow(s), but encountered errors with others.",
            "created_workflows": created_workflows_info,
            "errors": errors
        }
    else:
        response_data = {
            "message": f"Successfully created {len(created_workflows_info)} workflow(s).",
            "created_workflows": created_workflows_info
        }

    return jsonify(response_data), status_code


# --- get_workflows function (keep as is from previous version with scope) ---
@workflow_bp.route('', methods=['GET'])
@jwt_required()
def get_workflows():
    """
    Retrieves workflows based on user role and optional scope.
    - Admins can use '?scope=all' (default) or '?scope=mine'.
    - Non-admins always get only their own workflows.
    Supports pagination via query parameters 'page' and 'per_page'.
    """
    current_user_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_user_username).first()

    if not current_user:
        return jsonify({"message": "Current user not found"}), 404

    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    # Scope parameter
    scope = request.args.get('scope', 'all' if current_user.role == 'admin' else 'mine').lower()

    # Base query
    query = UserWorkflow.query

    # Role-Based Query Modification
    fetch_all_users = False

    if current_user.role == 'admin':
        if scope == 'mine':
            logger.info(f"Admin user {current_user.username} fetching their own workflows (scope=mine).")
            query = query.options(
                joinedload(UserWorkflow.website_account)
            ).filter(
                UserWorkflow.user_id == current_user.id
            )
        else: # Default scope 'all' for admin
            logger.info(f"Admin user {current_user.username} fetching all workflows (scope=all).")
            query = query.options(
                joinedload(UserWorkflow.website_account),
                joinedload(UserWorkflow.user)
            )
            fetch_all_users = True
    else:
        logger.info(f"User {current_user.username} fetching their workflows.")
        query = query.options(
            joinedload(UserWorkflow.website_account)
        ).filter(
            UserWorkflow.user_id == current_user.id
        )

    # Apply ordering and pagination
    paginated_workflows = query.order_by(
        UserWorkflow.created_at.desc()
    ).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Serialize the workflow objects
    workflows_list = []
    for workflow in paginated_workflows.items:
        workflow_data = workflow.to_dict()

        # Add website account data
        if workflow.website_account:
            workflow_data['website_account'] = {
                'id': workflow.website_account.id,
                'website_url': getattr(workflow.website_account, 'website_url', None),
                'account_name': getattr(workflow.website_account, 'account_name', None),
                'account_email': getattr(workflow.website_account, 'account_email', None),
            }
        else:
            workflow_data['website_account'] = None

        # Add user data if fetching all workflows as admin
        if fetch_all_users and workflow.user:
            workflow_data['user'] = {
                'id': workflow.user.id,
                'username': workflow.user.username
            }
        elif fetch_all_users:
             workflow_data['user'] = None

        workflows_list.append(workflow_data)

    # Prepare pagination metadata
    pagination_metadata = {
        'total_pages': paginated_workflows.pages,
        'current_page': paginated_workflows.page,
        'per_page': paginated_workflows.per_page,
        'total_items': paginated_workflows.total,
        'scope': scope if current_user.role == 'admin' else 'mine'
    }

    return jsonify({'workflows': workflows_list, 'pagination': pagination_metadata}), 200


# --- REVERTED update_workflow_status function ---
@workflow_bp.route('/<string:workflow_instance_id>/status', methods=['PATCH'])
@jwt_required()
def update_workflow_status(workflow_instance_id):
    """
    Updates the status of a specific workflow instance.
    If the new status is 'TERMINATED', it also attempts to cancel
    the underlying SpiffWorkflow instance.
    Allows admins to update any workflow.
    Expects a JSON payload:
    {
        "status": "COMPLETED" | "TERMINATED" | ...
    }
    Requires the workflow_instance_id (UUID string) in the URL path.
    """
    current_user_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_user_username).first()

    if not current_user:
        return jsonify({"message": "Current user not found"}), 404

    # Input Validation
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body must be JSON"}), 400

    new_status_str = data.get('status')
    if not new_status_str:
        return jsonify({"message": "'status' is required in the request body"}), 400

    try:
        new_status_enum = UserWorkflowStatusEnum(new_status_str)
    except ValueError:
        valid_statuses = [e.value for e in UserWorkflowStatusEnum]
        return jsonify({"message": f"Invalid 'status'. Must be one of: {valid_statuses}"}), 400

    # Find and Authorize Workflow
    user_workflow = UserWorkflow.query.options(
        joinedload(UserWorkflow.user)
    ).filter(
        UserWorkflow.workflow_id == workflow_instance_id
    ).first()

    if not user_workflow:
        return jsonify({"message": "Workflow record not found for the given instance ID"}), 404

    # Security check
    if user_workflow.user_id != current_user.id and current_user.role != 'admin':
        logger.warning(f"Forbidden: User {current_user.username} attempted to update workflow {workflow_instance_id} owned by user {user_workflow.user_id}.")
        return jsonify({"message": "Forbidden: You do not have permission to update this workflow"}), 403

    # Update Logic
    try:
        # Cancellation Logic
        if new_status_enum == UserWorkflowStatusEnum.TERMINATED:
            logger.info(f"User {current_user.username} attempting to terminate SpiffWorkflow instance: {workflow_instance_id}")
            try:
                instance = engine.get_workflow(workflow_instance_id)

                if instance and instance.workflow:
                    # --- REVERTED CHECK ---
                    # Check if the workflow is already completed.
                    # Note: There's no standard 'is_cancelled()' method. Calling cancel()
                    # on an already cancelled workflow might be safe or might raise an error,
                    # depending on SpiffWorkflow's implementation details.
                    if not instance.workflow.is_completed():
                        instance.workflow.cancel()
                        instance.save() # Persist the change via the engine
                        logger.info(f"Successfully cancelled SpiffWorkflow instance: {workflow_instance_id}")
                    # Removed the explicit check for already cancelled state
                    else:
                         logger.warning(f"SpiffWorkflow instance {workflow_instance_id} is already completed, cannot cancel.")
                         # Optionally prevent setting UserWorkflow status to TERMINATED if already COMPLETED.
                         # return jsonify({"message": "Cannot terminate an already completed workflow"}), 409 # Conflict
                    # --- END REVERTED CHECK ---
                else:
                    logger.error(f"Could not find SpiffWorkflow instance {workflow_instance_id} in engine despite UserWorkflow record existing.")
                    return jsonify({"message": "Internal error: Workflow instance not found in engine."}), 500

            except Exception as cancel_err:
                logger.error(f"Error cancelling SpiffWorkflow instance {workflow_instance_id}: {cancel_err}", exc_info=True)
                db.session.rollback() # Rollback potential engine changes
                return jsonify({"message": f"Failed to cancel the workflow instance: {str(cancel_err)}"}), 500
        # End Cancellation Logic

        # Update the status in the UserWorkflow table
        user_workflow.workflow_status = new_status_enum
        db.session.commit()

        logger.info(f"Successfully updated UserWorkflow {user_workflow.id} status to {new_status_enum.value}")
        # Return the updated workflow details
        response_workflow_data = user_workflow.to_dict()
        if user_workflow.website_account:
             response_workflow_data['website_account'] = { 'id': user_workflow.website_account.id, 'website_url': user_workflow.website_account.website_url }
        if user_workflow.user:
             response_workflow_data['user'] = { 'id': user_workflow.user.id, 'username': user_workflow.user.username }

        return jsonify({
            "message": "Workflow status updated successfully.",
            "workflow": response_workflow_data
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Database commit error during status update for UserWorkflow {user_workflow.id}: {e}", exc_info=True)
        return jsonify({"message": "An internal error occurred while updating the workflow status."}), 500
