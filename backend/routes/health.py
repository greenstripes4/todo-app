from flask import Blueprint, jsonify
import datetime
import logging
import sys
import os
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec
from SpiffWorkflow.serializer.json import JSONSerializer
from SpiffWorkflow.workflow import Workflow
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.spiff.parser import SpiffBpmnParser
from SpiffWorkflow.spiff.specs.defaults import UserTask, ManualTask
from SpiffWorkflow.spiff.serializer.config import SPIFF_CONFIG
from SpiffWorkflow.bpmn.specs.mixins.none_task import NoneTask
from SpiffWorkflow.bpmn.script_engine import TaskDataEnvironment
from workflows.serializer.file import FileSerializer
from workflows.engine import BpmnEngine
from workflows.spiff.curses_handlers import UserTaskHandler, ManualTaskHandler

# --- Configuration ---
# Assuming BASE_DIR is where your 'workflows' directory resides
# Adjust if necessary based on where your Flask app is run from
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Points to backend/
BPMN_FILE_PATH = os.path.join(BASE_DIR, 'workflows/definitions/dummy_workflow.bpmn')
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


@health_bp.route('/bpmn', methods=['GET'])
def bpmn_check():
    """
    Health Check Endpoint - Workflow Engine
    Loads and runs a dummy BPMN workflow to check the workflow engine integration.
    ---
    tags:
      - Health
    responses:
      200:
        description: Workflow engine check successful.
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                message:
                  type: string
                  example: Workflow check successful
      500:
        description: Workflow engine check failed.
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: error
                message:
                  type: string
                  example: Workflow check failed
                error:
                  type: string
                  example: "[Errno 2] No such file or directory: '/path/to/dummy_workflow.bpmn'"
    """
    logger.info("Received request to start dummy bpmn workflow.")
    logger.info(f"Attempting to load BPMN file: {BPMN_FILE_PATH}")

    if not os.path.isfile(BPMN_FILE_PATH):
        logger.error(f"BPMN file not found or is not a file at {BPMN_FILE_PATH}")
        return jsonify({'message': 'Workflow definition file not found on server.'}), 500

    try:
        dirname = 'wfdata'
        FileSerializer.initialize(dirname)
        registry = FileSerializer.configure(SPIFF_CONFIG)
        serializer = FileSerializer(dirname, registry=registry)
        parser = SpiffBpmnParser()
        
        handlers = {
            UserTask: UserTaskHandler,
            ManualTask: ManualTaskHandler,
            NoneTask: ManualTaskHandler,
        }

        script_env = TaskDataEnvironment({'datetime': datetime })
        engine = BpmnEngine(parser, serializer, script_env)

        spec_id = engine.add_spec('minimal_start_end_process', {BPMN_FILE_PATH}, None)
        # spec_id = engine.list_specs()[0]

        engine.start_workflow(spec_id).run_until_user_input_required()
        
        # 4. Return success response
        return jsonify({
            'status': 'ok',
            'message': 'Workflow check successful'
        }), 200

    except Exception as e:
        # Catch any other exceptions during spec loading or workflow execution
        # This could be errors within the BPMN definition or the engine itself
        print(f"ERROR [Health Check]: Failed to load or run workflow: {e}") # Log the error
        # Consider logging the full traceback here in a real application for debugging
        # import traceback
        # print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': 'Workflow check failed',
            'error': f"{type(e).__name__}: {str(e)}" # Provide error type and message
        }), 500 # 500 Internal Server Error

