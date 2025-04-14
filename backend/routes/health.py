from flask import Blueprint, jsonify
import datetime
import logging
import sys
import os
from SpiffWorkflow.workflow import Workflow
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec
from SpiffWorkflow.serializer.json import JSONSerializer

# --- Configuration ---
# Assuming BASE_DIR is where your 'workflows' directory resides
# Adjust if necessary based on where your Flask app is run from
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Points to backend/
JSON_FILE_PATH = os.path.join(BASE_DIR, 'workflows/definitions/nuclear.json')
SCRIPT_MODULE_PARENT = BASE_DIR # Parent directory of the 'workflows' package

# Ensure the script directory's parent is in the Python path for imports
if SCRIPT_MODULE_PARENT not in sys.path:
    sys.path.append(SCRIPT_MODULE_PARENT)
    # print(f"DEBUG: Added {SCRIPT_MODULE_PARENT} to sys.path") # For debugging

# --- Logging Setup ---
# Use Flask's logger or standard logging
logger = logging.getLogger(__name__)
if not logger.handlers: # Avoid adding multiple handlers if reloaded
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

health_bp = Blueprint('health', __name__, url_prefix='/health')

# --- Helper: Ensure __init__.py files exist ---
# Helps Python treat directories as packages.
def ensure_packages_exist():
    """Creates __init__.py files if they don't exist to make dirs packages."""
    try:
        workflows_dir = os.path.join(SCRIPT_MODULE_PARENT, 'workflows')
        scripts_dir = os.path.join(workflows_dir, 'scripts')
        if not os.path.isdir(SCRIPT_MODULE_PARENT):
             logger.warning(f"Parent directory for scripts not found: {SCRIPT_MODULE_PARENT}. Skipping __init__.py creation.")
             return
        os.makedirs(workflows_dir, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)
        if not os.path.exists(os.path.join(workflows_dir, '__init__.py')):
             open(os.path.join(workflows_dir, '__init__.py'), 'a').close()
             logger.debug(f"Created: {os.path.join(workflows_dir, '__init__.py')}")
        if not os.path.exists(os.path.join(scripts_dir, '__init__.py')):
             open(os.path.join(scripts_dir, '__init__.py'), 'a').close()
             logger.debug(f"Created: {os.path.join(scripts_dir, '__init__.py')}")
    except OSError as e:
        logger.error(f"Error ensuring package structure: {e}")

# Run this check once when the module is loaded
ensure_packages_exist()

@health_bp.route('/time', methods=['GET'])
def time_check():
    """
    Health Check Endpoint - Time
    Returns the current server time to indicate the service is running.
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is healthy and running.
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                timestamp:
                  type: string
                  format: date-time
                  example: 2023-10-27T12:00:00.123456
    """
    now = datetime.datetime.now(datetime.timezone.utc) # Use timezone-aware UTC time
    return jsonify({
        'status': 'ok',
        'timestamp': now.isoformat() # ISO 8601 format is standard
    }), 200


@health_bp.route('/workflow', methods=['GET'])
def workflow_check():
    logger.info("Received request to start spiffworkflow workflow.")
    try:
        with open(JSON_FILE_PATH) as fp:
          workflow_json = fp.read()
        serializer = JSONSerializer()
        spec = WorkflowSpec.deserialize(serializer, workflow_json)
        # Create the workflow.
        workflow = Workflow(spec)

        # Execute until all tasks are done or require manual intervention.
        # For the sake of this tutorial, we ignore the "manual" flag on the
        # tasks. In practice, you probably don't want to do that.
        workflow.run_all(halt_on_manual=False)
        return jsonify({
            'status': 'ok',
            'message': 'Workflow check successful'
        }), 200
    except Exception as e:
        # Catch any other exceptions during spec loading or workflow execution
        print(f"ERROR [Health Check]: Failed to load or run workflow: {e}") # Log the error
        # Consider logging the full traceback here in a real application for debugging
        # import traceback
        # print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'Workflow check failed',
            'error': f"{type(e).__name__}: {str(e)}" # Provide error type and message
        }), 500 # 500 Internal Server Error
