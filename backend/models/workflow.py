# /config/workspace/todo-app/backend/models/workflow.py
from app import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Index, UniqueConstraint, PrimaryKeyConstraint, ForeignKeyConstraint
import uuid # Import the uuid module

class Workflow(db.Model):
    __tablename__ = '_workflow'

    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=db.text("gen_random_uuid()"))
    # Ensure workflow_spec_id is not nullable if it's required
    workflow_spec_id = db.Column(UUID(as_uuid=True), db.ForeignKey('_workflow_spec.id'), nullable=False)
    serialization = db.Column(JSONB)

    # Relationships
    workflow_spec = db.relationship('WorkflowSpec', back_populates='workflows')
    tasks = db.relationship('Task', back_populates='workflow', cascade='all, delete-orphan', lazy='dynamic')
    workflow_data = db.relationship('WorkflowData', back_populates='workflow', cascade='all, delete-orphan', lazy='dynamic')
    instance = db.relationship('Instance', back_populates='workflow', uselist=False, cascade='all, delete-orphan') # One-to-one

    def __repr__(self):
        return f'<Workflow {self.id}>'

class Task(db.Model):
    __tablename__ = '_task'

    # 'id' is generated in SQLite. In PostgreSQL, handle via application/trigger
    # or make it the primary key if globally unique. Assuming globally unique UUID.
    # If only unique per workflow, PK should be (workflow_id, id).
    # Let's assume 'id' from serialization is intended to be the unique ID.
    id = db.Column(UUID(as_uuid=True), primary_key=True, index=True) # Made PK, requires app to provide unique UUID
    workflow_id = db.Column(UUID(as_uuid=True), db.ForeignKey('_workflow.id', ondelete='CASCADE'), nullable=False, index=True)
    serialization = db.Column(JSONB)

    # Relationships
    workflow = db.relationship('Workflow', back_populates='tasks')
    task_data = db.relationship('TaskData', back_populates='task', cascade='all, delete-orphan', lazy='dynamic')

    # If 'id' is not the PK, define the intended PK, e.g., a surrogate key or composite key.
    # Example if using surrogate PK:
    # pk_id = db.Column(db.Integer, primary_key=True)
    # id = db.Column(UUID(as_uuid=True), unique=True, index=True) # Keep the UUID field

    __table_args__ = (
        Index('ix_task_workflow_id', 'workflow_id'), # Explicit index matching SQLite
        Index('ix_task_id', 'id'), # Explicit index matching SQLite
        # Add UniqueConstraint if 'id' is not PK but should be unique
        # UniqueConstraint('id', name='uq_task_id'),
    )

    def __repr__(self):
        return f'<Task {self.id} in Workflow {self.workflow_id}>'


class TaskData(db.Model):
    __tablename__ = '_task_data'

    # Composite primary key based on unique constraint in schema
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey('_task.id', ondelete='CASCADE'), primary_key=True, index=True)
    name = db.Column(db.Text, primary_key=True, index=True)

    # workflow_id is useful for partitioning or querying but redundant if task_id is globally unique
    # Kept it as per original schema, ensure it's populated correctly.
    workflow_id = db.Column(UUID(as_uuid=True), db.ForeignKey('_workflow.id', ondelete='CASCADE'), nullable=False)
    value = db.Column(JSONB)
    last_updated = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    # Relationship
    task = db.relationship('Task', back_populates='task_data')

    __table_args__ = (
        PrimaryKeyConstraint('task_id', 'name'),
        # Foreign key constraint explicitly defined for clarity if needed elsewhere
        # ForeignKeyConstraint(['workflow_id'], ['_workflow.id'], ondelete='CASCADE'),
        Index('ix_task_data_task_id', 'task_id'), # Explicit index matching SQLite
        Index('ix_task_data_name', 'name'), # Explicit index matching SQLite
    )

    def __repr__(self):
        return f'<TaskData Name={self.name} for Task {self.task_id}>'


class WorkflowData(db.Model):
    __tablename__ = '_workflow_data'

    # Composite primary key based on unique constraint in schema
    workflow_id = db.Column(UUID(as_uuid=True), db.ForeignKey('_workflow.id', ondelete='CASCADE'), primary_key=True, index=True)
    name = db.Column(db.Text, primary_key=True, index=True) # Index name matches SQLite 'wokflow_data_name' typo fixed

    value = db.Column(JSONB)
    last_updated = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), onupdate=db.func.now())

    # Relationship
    workflow = db.relationship('Workflow', back_populates='workflow_data')

    __table_args__ = (
        PrimaryKeyConstraint('workflow_id', 'name'),
        Index('ix_workflow_data_workflow_id', 'workflow_id'), # Explicit index matching SQLite 'workflow_data_id'
        Index('ix_workflow_data_name', 'name'), # Explicit index matching SQLite 'wokflow_data_name'
    )

    def __repr__(self):
        return f'<WorkflowData Name={self.name} for Workflow {self.workflow_id}>'

