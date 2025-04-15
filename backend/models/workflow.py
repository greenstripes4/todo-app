# /config/workspace/todo-app/backend/models/workflow.py
import datetime
import enum # Import the enum module
from app import db
from sqlalchemy.orm import relationship
from sqlalchemy import func

# Define Enums for type safety
class WorkflowTypeEnum(enum.Enum):
    DSAR = "DSAR"
    OD3 = "OD3"

class WorkflowStatusEnum(enum.Enum):
    RUNNING = "Running"
    COMPLETED = "Completed"
    TERMINATED = "Terminated"
    FAILED = "Failed"
    SUSPENDED = "Suspended"
    PENDING = "Pending"
    CANCELLED = "Cancelled"

class Workflow(db.Model):
    __tablename__ = 'workflows'

    # Primary key (auto-incrementing integer)
    id = db.Column(db.Integer, primary_key=True)

    # Foreign key linking to the User table (who triggered the workflow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Unique identifier for the workflow instance (e.g., could be a UUID string)
    workflow_id = db.Column(db.String(128), unique=True, nullable=False, index=True)

    # Type of the workflow using Enum
    workflow_type = db.Column(db.Enum(WorkflowTypeEnum), nullable=False)

    # Status of the workflow using Enum
    workflow_status = db.Column(db.Enum(WorkflowStatusEnum), nullable=False, default=WorkflowStatusEnum.PENDING, index=True)

    # Timestamp when the workflow record was created
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    # Timestamp when the workflow record was last updated
    updated_at = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Define the relationship to the User model
    user = relationship('User', backref=db.backref('workflows', lazy=True))

    def __repr__(self):
        # Helpful representation for debugging, showing the enum value
        type_value = self.workflow_type.value if self.workflow_type else 'None'
        status_value = self.workflow_status.value if self.workflow_status else 'None'
        return f'<Workflow {self.workflow_id} ({type_value}) - Status: {status_value}>'

    def to_dict(self):
        # Method to serialize the object data to a dictionary
        # Return the enum *value* for JSON compatibility
        return {
            'id': self.id,
            'user_id': self.user_id,
            'workflow_id': self.workflow_id,
            'workflow_type': self.workflow_type.value if self.workflow_type else None,
            'workflow_status': self.workflow_status.value if self.workflow_status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
