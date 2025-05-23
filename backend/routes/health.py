# /config/workspace/todo-app/backend/routes/health.py
from flask import Blueprint, jsonify, request # Added request
import datetime
import logging
import sys
import os
import json
from SpiffWorkflow import TaskState
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec
from SpiffWorkflow.serializer.json import JSONSerializer
from SpiffWorkflow.workflow import Workflow
from SpiffWorkflow.specs import SubWorkflow
from SpiffWorkflow.spiff.parser import SpiffBpmnParser
from SpiffWorkflow.spiff.serializer.config import SPIFF_CONFIG
from SpiffWorkflow.bpmn.script_engine import TaskDataEnvironment
from app import db
from workflows.serializer.sql.serializer import (
    SqlSerializer,
)
from workflows.engine import BpmnEngine
from utils.email import GmailUtils # <-- Corrected Import Path

# --- Configuration ---
# Assuming BASE_DIR is where your 'workflows' directory resides
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Points to backend/
BPMN_FILE_PATH = os.path.join(BASE_DIR, 'workflows/definitions/simple_python_embed.bpmn')
JSON_FILE_PATH = os.path.join(BASE_DIR, 'workflows/definitions/nuclear.json')

# --- Logging Setup ---
# Use Flask's logger or standard logging
logger = logging.getLogger(__name__)
# Note: If running within Flask app context, Flask's logger might already be configured.
# This basicConfig is a fallback or for standalone script execution.
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

health_bp = Blueprint('health', __name__, url_prefix='/health')

# --- Existing Functions (hello_world, on_ready_cb, etc.) remain unchanged ---
def hello_world(user_info):
    """
    Writes the string 'hello dsar' to the file /app/result.txt.
    Creates the /app directory if it doesn't exist.
    """
    file_path = '/app/result.txt'
    output_string = 'hello dsar'

    # Write the string to the file
    with open(file_path, 'w') as f:
        f.write(output_string + '\n') # Added newline for clarity in the file
        f.write(f"Hello from {user_info['name']} \n")
        f.write(f"Hello from {user_info['email']} \n")
    logger.info(f"Successfully wrote '{output_string}' to {file_path}")

# Sample event callback from https://github.com/sartography/SpiffWorkflow/blob/main/tests/SpiffWorkflow/core/util.py
def on_ready_cb(workflow, task, taken_path):
    reached_key = "%s_reached" % str(task.task_spec.name)
    n_reached = task.get_data(reached_key, 0) + 1
    task.set_data(**{reached_key:       n_reached,
                     'two':             2,
                     'three':           3,
                     'test_attribute1': 'false',
                     'test_attribute2': 'true'})

    # Collect a list of all data.
    atts = []
    for key, value in list(task.data.items()):
        if key in ['data',
                   'two',
                   'three',
                   'test_attribute1',
                   'test_attribute2']:
            continue
        if key.endswith('reached'):
            continue
        atts.append('='.join((key, str(value))))

    # Collect a list of all task data.
    props = []
    for key, value in list(task.task_spec.data.items()):
        props.append('='.join((key, str(value))))

    # Store the list of data in the workflow.
    atts = ';'.join(atts)
    props = ';'.join(props)
    old = task.get_data('data', '')
    data = task.task_spec.name + ': ' + atts + '/' + props + '\n'
    task.set_data(data=old + data)
    return True

def on_complete_cb(workflow, task, taken_path):
    # Record the path.
    indent = '  ' * task.depth
    taken_path.append('%s%s' % (indent, task.task_spec.name))
    # In workflows that load a subworkflow, the newly loaded children
    # will not have on_ready_cb() assigned. By using this function, we
    # re-assign the function in every step, thus making sure that new
    # children also call on_ready_cb().
    for child in task.children:
        track_task(child.task_spec, taken_path)
    return True

def on_update_cb(workflow, task, taken_path):
    for child in task.children:
        track_task(child.task_spec, taken_path)
    return True

def track_task(task_spec, taken_path):
    # Disconnecting and reconnecting makes absolutely no sense but inexplicably these tests break
    # if just connected based on a check that they're not
    if task_spec.ready_event.is_connected(on_ready_cb):
        task_spec.ready_event.disconnect(on_ready_cb)
    task_spec.ready_event.connect(on_ready_cb, taken_path)
    if task_spec.completed_event.is_connected(on_complete_cb):
        task_spec.completed_event.disconnect(on_complete_cb)
    task_spec.completed_event.connect(on_complete_cb, taken_path)
    if isinstance(task_spec, SubWorkflow):
        if task_spec.update_event.is_connected(on_update_cb):
            task_spec.update_event.disconnect(on_update_cb)
        task_spec.update_event.connect(on_update_cb, taken_path)

def track_workflow(wf_spec, taken_path=None):
    if taken_path is None:
        taken_path = []
    for name in wf_spec.task_specs:
        track_task(wf_spec.task_specs[name], taken_path)
    return taken_path

# --- Existing Health Check Routes ---

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
    Loads, runs, and confirms completion of a dummy BPMN workflow
    to check the workflow engine integration.
    ---
    tags:
      - Health
    responses:
      200:
        description: Workflow engine check successful, workflow completed.
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
                  example: Workflow check successful and completed (SQL)
      500:
        description: Workflow engine check failed or workflow did not complete.
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
                  example: Workflow check failed (SQL)
                error:
                  type: string
                  example: "[Errno 2] No such file or directory: '/path/to/dummy_workflow.bpmn'"
                details:
                  type: string
                  example: "Workflow did not complete successfully." # Added detail for completion failure
    """
    logger.info("Received request to start dummy bpmn workflow (SQL).")
    logger.info(f"Attempting to load BPMN file: {BPMN_FILE_PATH}")

    try:
        registry = SqlSerializer.configure(SPIFF_CONFIG)
        serializer = SqlSerializer(db, registry=registry) # Pass the db object

        parser = SpiffBpmnParser()

        my_input_data = {
            'user_info': {
                'name': 'John Doe',
                'email': 'johndoe@example.com'
            }
        }

        script_env = TaskDataEnvironment({
          'datetime': datetime,
          'hello_world': hello_world
          })
        engine = BpmnEngine(parser, serializer, script_env)

        # Add the spec using the engine
        spec_id = engine.add_spec('WriteToFileProcess', {BPMN_FILE_PATH}, None)

        # Start a workflow instance
        workflow_instance = engine.start_workflow(spec_id)

        # Connect event callbacks
        taken_path = track_workflow(workflow_instance.workflow.spec)

        start_task = workflow_instance.ready_tasks[0]
        start_task.data.update(my_input_data)

        cnt = len(workflow_instance.workflow.get_tasks(state=TaskState.READY))
        logger.info(f"We have {cnt} ready tasks.")

        # Run the workflow to completion
        workflow_instance.run_until_user_input_required()

        # --- Check if the workflow actually completed ---
        # Access the underlying SpiffWorkflow object via workflow_instance.workflow
        if workflow_instance.workflow.is_completed():
            logger.info("Workflow instance completed successfully with the below path and data:")
            logger.info('Workflow Path:\n'.join(taken_path) + '\n')
            logger.info('Workflow Date:\n' + json.dumps(workflow_instance.workflow.get_data('data', '')) + '\n')
            # Return success response
            return jsonify({
                'status': 'ok',
                'message': 'Workflow check successful and completed (SQL)' # Updated message
            }), 200
        else:
            # This might happen if the workflow definition has issues or requires
            # unexpected manual steps not handled here.
            # Get the status from the underlying workflow object
            workflow_status = workflow_instance.workflow.get_status()
            logger.warning(f"Workflow instance did not complete. Status: {workflow_status}")
            return jsonify({
                'status': 'error',
                'message': 'Workflow check successful but workflow did not complete (SQL)',
                'details': f"Workflow status: {workflow_status}" # Use status from workflow object
            }), 500 # Still an issue if it didn't complete as expected

    except FileNotFoundError: # More specific error for the BPMN file itself
        logger.error(f"ERROR [Health Check - BPMN SQLite]: BPMN definition file not found at {BPMN_FILE_PATH}")
        return jsonify({
            'status': 'error',
            'message': 'Workflow check failed (SQL)',
            'error': f"File not found: {BPMN_FILE_PATH}"
        }), 500
    except Exception as e:
        # Catch any other exceptions during spec loading or workflow execution
        logger.error(f"ERROR [Health Check - BPMN SQLite]: Failed to load or run workflow: {e}", exc_info=True) # Log traceback
        return jsonify({
            'status': 'error',
            'message': 'Workflow check failed (SQL)',
            'error': f"{type(e).__name__}: {str(e)}" # Provide error type and message
        }), 500 # 500 Internal Server Error


# --- Email Test Routes ---

# Modified send_test_email to use GET and hardcoded values
@health_bp.route('/send-test-email', methods=['GET']) # Changed to GET
def send_test_email():
    """
    Test Endpoint - Send Email via Gmail API (GET Request)
    Sends a test email with hardcoded content using the configured Gmail account.
    ---
    tags:
      - Email Tests
    responses:
      200:
        description: Email sent successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: Email sent successfully
                message_id:
                  type: string
                  example: 18b9cdef01234567
      400:
        description: Bad Request - Hardcoded recipient email needs to be set.
      500:
        description: Internal Server Error - Failed to initialize Gmail or send email.
    """
    # --- Hardcoded Email Content ---
    # !!! IMPORTANT: Change this to a valid recipient email address you can check !!!
    recipient = "your_test_recipient@example.com"
    subject = "API Test Email (GET)"
    body = "This is a hardcoded test email sent via a GET request from the health check endpoint."
    # -----------------------------

    # Basic check if the placeholder recipient is still there
    if recipient == "your_test_recipient@example.com":
        logger.error("Hardcoded recipient email in /send-test-email needs to be updated.")
        return jsonify({"error": "Please configure the hardcoded recipient email in the route code."}), 400 # Use 400 Bad Request

    logger.info(f"Received GET request to send test email to hardcoded recipient: {recipient}")
    try:
        gmail = GmailUtils() # Instantiates and authenticates
        if not gmail.service:
             logger.error("Failed to initialize Gmail service for sending email.")
             return jsonify({"error": "Failed to initialize Gmail service. Check logs/config."}), 500

        # Use the hardcoded values
        result = gmail.send_email(recipient, subject, body)

        if result and result.get('id'):
            logger.info(f"Successfully sent test email to {recipient}, message ID: {result.get('id')}")
            return jsonify({"message": "Email sent successfully", "message_id": result.get('id')}), 200
        else:
            logger.error(f"Failed to send test email to {recipient}. Gmail API did not return success.")
            return jsonify({"error": "Failed to send email via Gmail API"}), 500
    except Exception as e:
         # Catch potential errors during GmailUtils instantiation or sending
         logger.error(f"Error in /send-test-email endpoint: {e}", exc_info=True)
         return jsonify({"error": "An internal server error occurred while sending email"}), 500


@health_bp.route('/list-unread-emails', methods=['GET']) # Renamed slightly for clarity
def list_unread_emails():
    """
    Test Endpoint - List Unread Emails via Gmail API
    Lists the IDs of unread emails (up to a limit).
    Optional query parameter: ?limit=N (default 5)
    ---
    tags:
      - Email Tests
    parameters:
      - in: query
        name: limit
        schema:
          type: integer
          default: 5
        description: Maximum number of unread email IDs to return.
    responses:
      200:
        description: Successfully retrieved unread email IDs.
        content:
          application/json:
            schema:
              type: object
              properties:
                unread_message_ids:
                  type: array
                  items:
                    type: string
                  example: ["18b9cdef01234567", "18b9cdef89abcdef"]
      500:
        description: Internal Server Error - Failed to initialize Gmail or list emails.
    """
    try:
        limit = request.args.get('limit', 5, type=int) # Get limit from query param, default 5
        logger.info(f"Received request to list unread emails (limit: {limit}).")

        gmail = GmailUtils()
        if not gmail.service:
             logger.error("Failed to initialize Gmail service for listing emails.")
             return jsonify({"error": "Failed to initialize Gmail service. Check logs/config."}), 500

        message_ids = gmail.list_emails(query='is:unread', max_results=limit)

        if message_ids is not None:
            logger.info(f"Found {len(message_ids)} unread email IDs.")
            # You might want to fetch details for each ID here in a real app
            return jsonify({"unread_message_ids": message_ids}), 200
        else:
            logger.error("Failed to list unread emails via Gmail API.")
            return jsonify({"error": "Failed to list emails via Gmail API"}), 500
    except Exception as e:
         # Catch potential errors during GmailUtils instantiation or listing
         logger.error(f"Error in /list-unread-emails endpoint: {e}", exc_info=True)
         return jsonify({"error": "An internal server error occurred while listing emails"}), 500
