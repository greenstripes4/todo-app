import os
import datetime
import sqlite3
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# Initialize the Flask application
app = Flask(__name__)

# Configure CORS to accept all domains
CORS(app)

# Fetch database URI from environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

# Fetch JWT secret key from environment variable
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')

# Initialize the SQLAlchemy database extension
db = SQLAlchemy(app)
# Initialize the JWTManager extension
jwt = JWTManager(app)

# Initialize the BpmnEngine with SQLite
from SpiffWorkflow.spiff.parser import SpiffBpmnParser
from SpiffWorkflow.spiff.serializer import DEFAULT_CONFIG
from SpiffWorkflow.bpmn import BpmnWorkflow
from SpiffWorkflow.bpmn.util.subworkflow import BpmnSubWorkflow
from SpiffWorkflow.bpmn.specs import BpmnProcessSpec
from SpiffWorkflow.bpmn.script_engine import TaskDataEnvironment
from workflows.engine import BpmnEngine
from workflows.serializer.sqlite import (
    SqliteSerializer,
    WorkflowConverter,
    SubworkflowConverter,
    WorkflowSpecConverter
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__))) # Points to backend/
BPMN_FILE_PATHS = {os.path.join(BASE_DIR, 'workflows/definitions/dsar.bpmn')}
spiff_dbname = 'spiff.db'

DEFAULT_CONFIG[BpmnWorkflow] = WorkflowConverter
DEFAULT_CONFIG[BpmnSubWorkflow] = SubworkflowConverter
DEFAULT_CONFIG[BpmnProcessSpec] = WorkflowSpecConverter

# Initialize the database schema (important for SQLite)
with sqlite3.connect(spiff_dbname) as spiff_db:
    SqliteSerializer.initialize(spiff_db)

# Configure and create the serializer instance
registry = SqliteSerializer.configure(DEFAULT_CONFIG)
serializer = SqliteSerializer(spiff_dbname, registry=registry)
# --- End SqliteSerializer Setup ---

parser = SpiffBpmnParser()

script_env = TaskDataEnvironment({'datetime': datetime })
engine = BpmnEngine(parser, serializer, script_env)
engine.add_spec('Process_DSAR_Request', BPMN_FILE_PATHS, None)

# Import the User model from the models package
from models.user import User
# Import the WebsiteAccount model
from models.website_account import WebsiteAccount

# Create tables in the database if they don't exist
with app.app_context():
    db.create_all()

    # --- Admin User Creation ---
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        # Create the admin user
        admin_user = User(username='admin', role='admin', status='active')
        admin_user.set_password('admin')
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created.")
        # Re-query admin_user to get the ID after commit
        admin_user = User.query.filter_by(username='admin').first()
    else:
        print("Admin user already exists.")

    # --- Sample Website Account Creation for Admin ---
    # Check if the admin user exists and doesn't already have this specific sample account
    if admin_user:
        sample_account_url = 'https://admin-sample-site.com'
        existing_sample_account = WebsiteAccount.query.filter_by(
            user_id=admin_user.id,
            website_url=sample_account_url
        ).first()

        if not existing_sample_account:
            sample_account = WebsiteAccount(
                user_id=admin_user.id,
                website_url=sample_account_url,
                account_name='Admin Sample Account',
                account_email='admin@sample-site.com',
                compliance_contact='compliance@sample-site.com'
            )
            db.session.add(sample_account)
            db.session.commit()
            print(f"Sample website account created for admin user.")
        else:
            print(f"Sample website account for admin user already exists.")
    else:
        # This case should ideally not happen based on the logic above, but good for safety
        print("Admin user not found, cannot create sample website account.")
    # --- End Sample Website Account Creation ---


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

# Define the root route (just a simple hello message)
@app.route('/')
def hello():
    return jsonify({'message': 'Hello from Flask!'})

# Run the app if the script is executed directly
if __name__ == '__main__':
    # Make sure debug is False in production!
    # Use environment variable for debug flag if possible
    is_debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=is_debug, host='0.0.0.0')
