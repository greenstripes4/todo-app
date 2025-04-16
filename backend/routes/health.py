from flask import Blueprint, jsonify
import datetime
import logging
import sys
import os
import sqlite3 # Added for SqliteSerializer
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec
from SpiffWorkflow.serializer.json import JSONSerializer
from SpiffWorkflow.workflow import Workflow
from SpiffWorkflow.spiff.parser import SpiffBpmnParser
from SpiffWorkflow.spiff.serializer.config import SPIFF_CONFIG
from SpiffWorkflow.bpmn import BpmnWorkflow # Added for SqliteSerializer config
from SpiffWorkflow.bpmn.util.subworkflow import BpmnSubWorkflow # Added for SqliteSerializer config
from SpiffWorkflow.bpmn.specs import BpmnProcessSpec # Added for SqliteSerializer config
from SpiffWorkflow.bpmn.script_engine import TaskDataEnvironment
# Remove FileSerializer import if no longer needed elsewhere in the file
# from workflows.serializer.file import FileSerializer
# Add SqliteSerializer imports
from workflows.serializer.sqlite import (
    SqliteSerializer,
    WorkflowConverter,
    SubworkflowConverter,
    WorkflowSpecConverter
)
from workflows.engine import BpmnEngine
from workflows.spiff.curses_handlers import UserTaskHandler, ManualTaskHandler

# --- Configuration ---
# Assuming BASE_DIR is where your 'workflows' directory resides
# Adjust if necessary based on where your Flask app is run from
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Points to backend/
BPMN_FILE_PATH = os.path.join(BASE_DIR, 'workflows/definitions/simple_python_embed.bpmn')
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
    """
    Health Check Endpoint - Basic SpiffWorkflow (JSON)
    Loads and runs a simple JSON-based workflow.
    ---
    tags:
      - Health
    responses:
      200:
        description: Basic workflow check successful.
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
        description: Basic workflow check failed.
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
    """
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
    except FileNotFoundError:
        logger.error(f"ERROR [Health Check - Workflow]: JSON definition file not found at {JSON_FILE_PATH}")
        return jsonify({
            'status': 'error',
            'message': 'Workflow check failed',
            'error': f"File not found: {JSON_FILE_PATH}"
        }), 500
    except Exception as e:
        # Catch any other exceptions during spec loading or workflow execution
        logger.error(f"ERROR [Health Check - Workflow]: Failed to load or run workflow: {e}", exc_info=True) # Log traceback
        return jsonify({
            'status': 'error',
            'message': 'Workflow check failed',
            'error': f"{type(e).__name__}: {str(e)}" # Provide error type and message
        }), 500 # 500 Internal Server Error


@health_bp.route('/bpmn', methods=['GET'])
def bpmn_check():
    """
    Health Check Endpoint - Workflow Engine (using SQLite)
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
    logger.info("Received request to start dummy bpmn workflow (SQLite).")
    logger.info(f"Attempting to load BPMN file: {BPMN_FILE_PATH}")

    # TODO: Use an in-memory SQLite database for the health check 
    # Looking at workflows/serializer/sqlite/serializer.py, the execute method always opens a new connection 
    # using sqlite3.connect(self.dbname, ...). When dbname is ':memory:', this creates a new, empty in-memory database
    # dbname = ':memory:'
    # Or use a temporary file:
    dbname = 'health_check_spiff.db'

    try:
        SPIFF_CONFIG[BpmnWorkflow] = WorkflowConverter
        SPIFF_CONFIG[BpmnSubWorkflow] = SubworkflowConverter
        SPIFF_CONFIG[BpmnProcessSpec] = WorkflowSpecConverter

        # Initialize the database schema (important for SQLite)
        with sqlite3.connect(dbname) as db:
            SqliteSerializer.initialize(db)

        # Configure and create the serializer instance
        registry = SqliteSerializer.configure(SPIFF_CONFIG)
        serializer = SqliteSerializer(dbname, registry=registry)
        # --- End SqliteSerializer Setup ---

        parser = SpiffBpmnParser()

        my_input_data = {
            'user_info': {
                'name': 'John Doe',
                'email': 'johndoe@example.com'
            }
        }

        script_env = TaskDataEnvironment({
          'datetime': datetime
          })
        engine = BpmnEngine(parser, serializer, script_env)

        # Add the spec using the engine
        # The second argument should be a set of file paths
        spec_id = engine.add_spec('WriteToFileProcess', {BPMN_FILE_PATH}, None)

        # Start a workflow instance and run it
        workflow_instance = engine.start_workflow(spec_id)
        start_task = workflow_instance.ready_tasks[0]
        start_task.data.update(my_input_data)
        # start_task.data['user_info'] = {'name': 'Alice', 'email': 'alice@example.com'}
        workflow_instance.run_until_user_input_required() # Or workflow_instance.complete() if no user tasks

        # Return success response
        return jsonify({
            'status': 'ok',
            'message': 'Workflow check successful (SQLite)'
        }), 200

    except FileNotFoundError: # More specific error for the BPMN file itself
        logger.error(f"ERROR [Health Check - BPMN SQLite]: BPMN definition file not found at {BPMN_FILE_PATH}")
        return jsonify({
            'status': 'error',
            'message': 'Workflow check failed (SQLite)',
            'error': f"File not found: {BPMN_FILE_PATH}"
        }), 500
    except Exception as e:
        # Catch any other exceptions during spec loading or workflow execution
        logger.error(f"ERROR [Health Check - BPMN SQLite]: Failed to load or run workflow: {e}", exc_info=True) # Log traceback
        return jsonify({
            'status': 'error',
            'message': 'Workflow check failed (SQLite)',
            'error': f"{type(e).__name__}: {str(e)}" # Provide error type and message
        }), 500 # 500 Internal Server Error
    finally: # Optional cleanup if using a file db
        if dbname != ':memory:' and os.path.exists(dbname):
            try:
                os.remove(dbname)
            except OSError as rm_err:
                logger.error(f"Error removing temporary health check db '{dbname}' in finally block: {rm_err}")

