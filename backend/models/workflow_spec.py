# /config/workspace/todo-app/backend/models/workflow_spec.py
from app import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Index, ForeignKeyConstraint, PrimaryKeyConstraint
import uuid # Import the uuid module

class WorkflowSpec(db.Model):
    __tablename__ = '_workflow_spec'

    # Use server_default with gen_random_uuid for PostgreSQL
    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=db.text("gen_random_uuid()"))
    serialization = db.Column(JSONB)

    # Relationships
    task_specs = db.relationship('TaskSpec', back_populates='workflow_spec', cascade='all, delete-orphan')
    # Relationships for dependencies
    parent_dependencies = db.relationship(
        'SpecDependency',
        foreign_keys='SpecDependency.child_id',
        back_populates='child_spec',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    child_dependencies = db.relationship(
        'SpecDependency',
        foreign_keys='SpecDependency.parent_id',
        back_populates='parent_spec',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    workflows = db.relationship('Workflow', back_populates='workflow_spec') # Relationship to Workflow

    def __repr__(self):
        return f'<WorkflowSpec {self.id}>'

class TaskSpec(db.Model):
    __tablename__ = '_task_spec'

    # Define a composite primary key or a separate auto-incrementing PK
    # Using a separate PK is often simpler with ORMs
    pk_id = db.Column(db.Integer, primary_key=True) # Added surrogate primary key
    workflow_spec_id = db.Column(UUID(as_uuid=True), db.ForeignKey('_workflow_spec.id', ondelete='CASCADE'), nullable=False, index=True)
    # 'name' is generated in SQLite. In PostgreSQL, this could be a generated column
    # or handled by application logic/triggers. Define as Text here.
    name = db.Column(db.Text, nullable=False, index=True)
    serialization = db.Column(JSONB)

    # Relationship
    workflow_spec = db.relationship('WorkflowSpec', back_populates='task_specs')

    # Add unique constraint if name should be unique per workflow_spec_id
    __table_args__ = (
        db.UniqueConstraint('workflow_spec_id', 'name', name='uq_task_spec_workflow_name'),
        Index('ix_task_spec_workflow_id', 'workflow_spec_id'), # Explicit index matching SQLite
        Index('ix_task_spec_name', 'name'), # Explicit index matching SQLite
    )

    def __repr__(self):
        return f'<TaskSpec {self.name} for WorkflowSpec {self.workflow_spec_id}>'


class SpecDependency(db.Model):
    __tablename__ = '_spec_dependency'

    # Composite primary key
    parent_id = db.Column(UUID(as_uuid=True), db.ForeignKey('_workflow_spec.id', ondelete='CASCADE'), primary_key=True, index=True)
    child_id = db.Column(UUID(as_uuid=True), db.ForeignKey('_workflow_spec.id', ondelete='CASCADE'), primary_key=True, index=True)

    # Relationships
    parent_spec = db.relationship('WorkflowSpec', foreign_keys=[parent_id], back_populates='child_dependencies')
    child_spec = db.relationship('WorkflowSpec', foreign_keys=[child_id], back_populates='parent_dependencies')

    __table_args__ = (
        PrimaryKeyConstraint('parent_id', 'child_id'),
        Index('ix_spec_dependency_parent_id', 'parent_id'), # Explicit index matching SQLite
        Index('ix_spec_dependency_child_id', 'child_id'), # Explicit index matching SQLite
    )

    def __repr__(self):
        return f'<SpecDependency Parent={self.parent_id} Child={self.child_id}>'

