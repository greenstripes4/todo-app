# /config/workspace/todo-app/backend/app.py

import os
import datetime
import logging
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# --- Logging Setup ---
# Configure logging BEFORE creating the app instance if possible,
# or at least very early.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Logger for this module (app.py)

# Initialize the Flask application
app = Flask(__name__)

# Configure CORS to accept all domains
CORS(app)

# Configure Database URI and JWT Secret Key from environment variables
# Ensure DATABASE_URL points to your PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/mydatabase') # Added default for safety
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'super-secret-key') # Added default for safety

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- SpiffWorkflow Engine Setup ---
from SpiffWorkflow.spiff.parser import SpiffBpmnParser
from SpiffWorkflow.spiff.serializer import DEFAULT_CONFIG
from SpiffWorkflow.bpmn import BpmnWorkflow
from SpiffWorkflow.bpmn.util.subworkflow import BpmnSubWorkflow
from SpiffWorkflow.bpmn.specs import BpmnProcessSpec
from SpiffWorkflow.bpmn.script_engine import TaskDataEnvironment
from workflows.engine import BpmnEngine
from workflows.serializer.sql.serializer import (
    SqlSerializer,
)

# Import models (ensure these are defined correctly)
from models.user import User
from models.website_account import WebsiteAccount
# Import workflow models to ensure tables are created if needed
from models import workflow_spec, workflow, instance

# --- Import functions for BPMN Script Engine ---
# Import the function from dsar.py
from workflows.scripts.dsar import validate_website_account

# --- End Import functions for BPMN Script Engine ---


# Create tables in the database if they don't exist
# This will create tables defined in ALL imported models associated with 'db'
with app.app_context():
    logger.info("Creating database tables if they don't exist...")
    db.create_all()
    logger.info("Database tables checked/created.")

    # --- Admin User Creation ---
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        logger.info("Admin user not found, creating...")
        # Create the admin user
        admin_user = User(username='admin', role='admin', status='active')
        admin_user.set_password('admin') # Make sure set_password hashes the password
        db.session.add(admin_user)
        try:
            db.session.commit()
            logger.info("Admin user created successfully.")
            # Re-query admin_user to get the ID after commit
            admin_user = User.query.filter_by(username='admin').first()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating admin user: {e}", exc_info=True)
            admin_user = None # Ensure admin_user is None if creation failed
    else:
        logger.info("Admin user already exists.")

    # --- Sample Website Account Creation for Admin ---
    if admin_user:
        sample_account_url = 'https://admin-sample-site.com'
        existing_sample_account = WebsiteAccount.query.filter_by(
            user_id=admin_user.id,
            website_url=sample_account_url
        ).first()

        if not existing_sample_account:
            logger.info(f"Creating sample website account for admin user (ID: {admin_user.id})...")
            sample_account = WebsiteAccount(
                user_id=admin_user.id,
                website_url=sample_account_url,
                account_name='Admin Sample Account',
                account_email='admin@sample-site.com',
                compliance_contact='compliance@sample-site.com'
            )
            db.session.add(sample_account)
            try:
                db.session.commit()
                logger.info(f"Sample website account created for admin user.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating sample website account for admin: {e}", exc_info=True)
        else:
            logger.info(f"Sample website account for admin user already exists.")
    else:
        logger.warning("Admin user not found or creation failed, cannot create sample website account for admin.")
    # --- End Admin Sample Website Account Creation ---

    # --- START: Test User Creation ---
    test_user = User.query.filter_by(username='test').first()
    if not test_user:
        logger.info("Test user not found, creating...")
        # Create the test user
        test_user = User(username='test', role='normal', status='active')
        test_user.set_password('test') # Set password for test user
        db.session.add(test_user)
        try:
            db.session.commit()
            logger.info("Test user created successfully.")
            # Re-query test_user to get the ID after commit
            test_user = User.query.filter_by(username='test').first()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating test user: {e}", exc_info=True)
            test_user = None # Ensure test_user is None if creation failed
    else:
        logger.info("Test user already exists.")

    # --- Sample Website Account Creation for Test User ---
    if test_user:
        test_sample_account_url = 'https://test-sample-site.com'
        existing_test_sample_account = WebsiteAccount.query.filter_by(
            user_id=test_user.id,
            website_url=test_sample_account_url
        ).first()

        if not existing_test_sample_account:
            logger.info(f"Creating sample website account for test user (ID: {test_user.id})...")
            test_sample_account = WebsiteAccount(
                user_id=test_user.id,
                website_url=test_sample_account_url,
                account_name='Test Sample Account',
                account_email='test@sample-site.com',
                compliance_contact='compliance@test-sample-site.com'
            )
            db.session.add(test_sample_account)
            try:
                db.session.commit()
                logger.info(f"Sample website account created for test user.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating sample website account for test user: {e}", exc_info=True)
        else:
            logger.info(f"Sample website account for test user already exists.")
    else:
        logger.warning("Test user not found or creation failed, cannot create sample website account for test user.")
    # --- END: Test User Creation ---


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__))) # Points to backend/
# Define BPMN file paths (adjust if needed)
BPMN_FILE_PATHS = {os.path.join(BASE_DIR, 'workflows/definitions/dsar.bpmn')}

# Configure and create the SqlSerializer instance, passing the db object
# Note: SqlSerializer expects the db object (which provides access to db.session)
registry = SqlSerializer.configure(DEFAULT_CONFIG)
serializer = SqlSerializer(db, registry=registry) # Pass the db object

# Initialize the parser and script environment
parser = SpiffBpmnParser()
# Add the imported function to the script environment
script_env = TaskDataEnvironment({
    'datetime': datetime,
    'validate_website_account': validate_website_account
    })

# Initialize the BpmnEngine with the new serializer
engine = BpmnEngine(parser, serializer, script_env)

logger.info("Loading SpiffWorkflow Spec...")
# Add the workflow specification(s) using the engine
# This will now use SqlSerializer's create_workflow_spec method
# Ensure the spec name 'Process_DSAR_Request' matches the one in your BPMN file
try:
    # It's good practice to add specs within the app context if they interact with the DB immediately
    with app.app_context():
        dsar_spec_id = engine.add_spec('Process_DSAR_Request', BPMN_FILE_PATHS, None)
        logger.info(f"DSAR Workflow Spec added/found with ID: {dsar_spec_id}")
except Exception as e:
    logger.error(f"Error adding workflow spec: {e}", exc_info=True)
    # Decide how to handle this error - maybe exit or log critical failure
# --- End SpiffWorkflow Engine Setup ---

# Import routes from the routes package
from routes.auth import auth_bp
from routes.user import user_bp
from routes.website_account import website_account_bp
from routes.health import health_bp
from routes.workflow import workflow_bp

# Register the blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(website_account_bp)
app.register_blueprint(health_bp)
app.register_blueprint(workflow_bp)
logger.info("Registered Flask blueprints.")

# Define the root route
@app.route('/')
def hello():
    logger.debug("Root route '/' accessed.") # Use debug for frequent access logs
    return jsonify({'message': 'Hello from Flask!'})

# Run the app if the script is executed directly
if __name__ == '__main__':
    # Use environment variable for debug flag
    is_debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.environ.get('HOST', '0.0.0.0') # Use 0.0.0.0 to be accessible externally
    port = int(os.environ.get('PORT', 5000))

    log_level = logging.DEBUG if is_debug else logging.INFO
    logging.getLogger().setLevel(log_level) # Adjust root logger level based on debug flag
    logger.info(f"Starting Flask app on {host}:{port} with debug={is_debug}")

    # Use 0.0.0.0 to be accessible externally (e.g., in Docker)
    app.run(debug=is_debug, host=host, port=port)

