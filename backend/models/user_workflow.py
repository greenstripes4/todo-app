# /config/workspace/todo-app/backend/models/user_workflow.py
import datetime
import enum # Import the enum module
from app import db
from sqlalchemy.orm import relationship
from sqlalchemy import func
# Import User and WebsiteAccount directly for clarity, though models.__init__ handles it
from .user import User
from .website_account import WebsiteAccount
from sqlalchemy.dialects.postgresql import JSONB # Use JSONB for PostgreSQL if applicable, or db.JSON for general use

# Define Enums for type safety
class UserWorkflowTypeEnum(enum.Enum): # Renamed from WorkflowTypeEnum
    DSAR = "DSAR"
    OD3 = "OD3"

class UserWorkflowStatusEnum(enum.Enum): # Renamed from WorkflowStatusEnum
    RUNNING = "Running"
    COMPLETED = "Completed"
    TERMINATED = "Terminated"
    FAILED = "Failed"
    SUSPENDED = "Suspended"
    PENDING = "Pending"
    CANCELLED = "Cancelled"
    DELETED = "Deleted"

class UserWorkflow(db.Model): # Renamed from Workflow
    __tablename__ = 'userworkflows' # Updated table name

    # Primary key (auto-incrementing integer)
    id = db.Column(db.Integer, primary_key=True)

    # Foreign key linking to the User table (who triggered the workflow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Foreign key linking to the WebsiteAccount table (which account the workflow is for)
    website_account_id = db.Column(db.Integer, db.ForeignKey('website_accounts.id'), nullable=False, index=True)

    # Unique identifier for the workflow instance (e.g., could be a UUID string)
    # Consider if this should link to the new Workflow model's ID (UUID)
    workflow_id = db.Column(db.String(128), unique=True, nullable=False, index=True)

    # Type of the workflow using Enum
    workflow_type = db.Column(db.Enum(UserWorkflowTypeEnum), nullable=False) # Updated Enum reference

    # Status of the workflow using Enum
    workflow_status = db.Column(db.Enum(UserWorkflowStatusEnum), nullable=False, default=UserWorkflowStatusEnum.PENDING, index=True) # Updated Enum reference

    # --- New Field ---
    # Stores a list of names for tasks currently in 'STARTED' status for this workflow
    # Use db.JSON for database portability, or JSONB specifically for PostgreSQL advantages
    active_tasks = db.Column(db.JSON, nullable=True, default=lambda: []) # Default to an empty list

    # Timestamp when the workflow record was created
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    # Timestamp when the workflow record was last updated
    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Define the relationship to the User model
    # Updated backref name to 'user_workflows'
    user = relationship('User', backref=db.backref('user_workflows', lazy=True))

    # Define the relationship to the WebsiteAccount model
    # Updated backref name to 'user_workflows'
    website_account = relationship('WebsiteAccount', backref=db.backref('user_workflows', lazy=True))

    def __repr__(self):
        # Helpful representation for debugging, showing the enum value and website account ID
        type_value = self.workflow_type.value if self.workflow_type else 'None'
        status_value = self.workflow_status.value if self.workflow_status else 'None'
        active_tasks_repr = repr(self.active_tasks) # Show the active tasks list
        # Updated class name in the representation string
        return f'<UserWorkflow {self.workflow_id} ({type_value}) for Account {self.website_account_id} - Status: {status_value} - Active Tasks: {active_tasks_repr}>'

    def to_dict(self):
        # Method to serialize the object data to a dictionary
        # Return the enum *value* for JSON compatibility
        return {
            'id': self.id,
            'user_id': self.user_id,
            'website_account_id': self.website_account_id,
            'workflow_id': self.workflow_id,
            'workflow_type': self.workflow_type.value if self.workflow_type else None,
            'workflow_status': self.workflow_status.value if self.workflow_status else None,
            'active_tasks': self.active_tasks, # Include the new field
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
            # Optionally include related object details (be careful of circular references)
            # 'user': self.user.to_dict() if self.user else None,
            # 'website_account': self.website_account.to_dict() if self.website_account else None
        }

