# /config/workspace/todo-app/backend/routes/health.py
from flask import Blueprint, jsonify
import datetime
import logging
import sys
import os
from SpiffWorkflow import TaskState
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec
from SpiffWorkflow.serializer.json import JSONSerializer
from SpiffWorkflow.workflow import Workflow
from SpiffWorkflow.spiff.parser import SpiffBpmnParser
from SpiffWorkflow.spiff.serializer.config import SPIFF_CONFIG
from SpiffWorkflow.bpmn.script_engine import TaskDataEnvironment
from app import db
from workflows.serializer.sql.serializer import (
    SqlSerializer,
)
from workflows.engine import BpmnEngine

# --- Configuration ---
# Assuming BASE_DIR is where your 'workflows' directory resides
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Points to backend/
BPMN_FILE_PATH = os.path.join(BASE_DIR, 'workflows/definitions/simple_python_embed.bpmn')
JSON_FILE_PATH = os.path.join(BASE_DIR, 'workflows/definitions/nuclear.json')

# --- Logging Setup ---
# Use Flask's logger or standard logging
logger = logging.getLogger(__name__)
if not logger.handlers: # Avoid adding multiple handlers if reloaded
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

health_bp = Blueprint('health', __name__, url_prefix='/health')


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
          'datetime': datetime
          })
        engine = BpmnEngine(parser, serializer, script_env)

        # Add the spec using the engine
        spec_id = engine.add_spec('WriteToFileProcess', {BPMN_FILE_PATH}, None)

        # Start a workflow instance
        workflow_instance = engine.start_workflow(spec_id)
        start_task = workflow_instance.ready_tasks[0]
        start_task.data.update(my_input_data)

        cnt = len(workflow_instance.workflow.get_tasks(state=TaskState.READY))
        logger.info(f"We have {cnt} ready tasks.")

        # Run the workflow to completion
        workflow_instance.run_until_user_input_required()

        # --- Check if the workflow actually completed ---
        # Access the underlying SpiffWorkflow object via workflow_instance.workflow
        if workflow_instance.workflow.is_completed():
            logger.info("Workflow instance completed successfully.")
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
